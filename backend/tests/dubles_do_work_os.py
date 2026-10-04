# -*- coding: utf-8 -*-
"""SPEC-129-A F0 — OS DUBLÊS DA BORDA do Work OS (banco, Redis Streams, portal-worker, relógio).

🔴 CLAUDE.md §9.4: o teste atravessa o MOTOR real; o dublê fica SÓ na borda. Este arquivo não
reimplementa nada do motor (`SmithWorker`, `OutboxDispatcher`, `WorkQueue`, `WorkRunService`,
`executar_passo`, `PortalExecutionGateway`): ele é o mundo de fora em que o motor roda.

    BancoEmMemoria   o PostgREST: filtros com a semântica do SQL (NULL não casa nem negado), UPDATE
                     que devolve SÓ as linhas que casaram (é o que um CAS lê: "a linha ou nada"),
                     `maybe_single()` que devolve None sem linha (postgrest 0.18), projeção de colunas,
                     e AS TRAVAS do banco real: colunas (PGRST204), ENUMs de status, NOT NULL,
                     `uq_work_runs_company_idempotency`, `uq_work_steps_run_key`, as FKs "mesma
                     corretora", `ck_work_runs_lease_coerente`, `trg_work_runs_company_imutavel`,
                     `idx_portal_jobs_pedido_vivo` e os 2 CHECKs da `_02` (SPEC-129-A §6):
                     `ck_work_runs_wake_so_da_fila` e `ck_work_runs_espera_tem_relogio`.
                     RPC `work_run_create` com o MESMO corpo da função do banco (run + outbox + 2 eventos).
    RedisStreams     XADD / XREADGROUP / XAUTOCLAIM / XACK com PEL e tempo ocioso pelo relógio falso;
                     sabe PERDER mensagem (C5: "o Redis descarta").
    PortalWorkerDuble o portal-worker: pega o job (`queued`→`running`) e o termina quando o teste manda.
    Relogio          o tempo do mundo: `datetime.now()` dos módulos do motor anda quando o teste manda.
    Processo         um processo do worker: a visão do banco + a do Redis. `morrer()` corta TUDO o que
                     ele faria depois (é assim que se simula `kill -9`: nada do `finally` chega ao mundo).

📊 O esquema (`ESQUEMA`) é o retrato do banco real em 04/10/2026 (information_schema, só leitura,
projeto `dcajcvlzcjbmyapmklil`) + as 2 colunas da `_02` (`wake_at`, `wait_for`). O teste do fio confere
o retrato contra o banco vivo a cada rodada: se o banco mudar, o dublê acusa que envelheceu.
"""
from __future__ import annotations

import asyncio
import contextlib
import copy
import datetime as _modulo_datetime
import json
import re
import sys
import threading
import time
import types
import uuid
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import Any, Callable, Optional

_DATETIME_REAL = _modulo_datetime.datetime

try:  # a mesma classe de erro que o supabase-py levanta — o motor a trata como trataria a real
    from postgrest.exceptions import APIError as _APIError
except Exception:  # noqa: BLE001
    class _APIError(Exception):  # type: ignore[no-redef]
        def __init__(self, erro: dict):
            self.code = erro.get("code")
            self.message = erro.get("message")
            self.details = erro.get("details")
            self.hint = erro.get("hint")
            super().__init__(str(erro))


def erro_do_banco(codigo: str, mensagem: str, detalhe: Optional[str] = None) -> Exception:
    return _APIError({"code": codigo, "message": mensagem, "details": detalhe, "hint": None})


class MorteDoProcesso(BaseException):
    """O processo do worker MORREU (kill -9 / reinício do contêiner).

    É `BaseException` de propósito: o motor tem `except Exception` em todo canto (e deve ter). Uma
    morte não é exceção tratável — nada do que o processo faria depois chega ao banco nem ao Redis."""


class FimDaVolta(BaseException):
    """Encerra UMA volta de um laço real do worker (ver `uma_volta`)."""


# ═════════════════════════════════════════════════════════════════════════════
# O RELÓGIO
# ═════════════════════════════════════════════════════════════════════════════
class _MetaDatetime(type):
    def __instancecheck__(cls, obj):  # um datetime real continua sendo "um datetime"
        return isinstance(obj, _DATETIME_REAL)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, _DATETIME_REAL)


class Relogio:
    """O tempo do mundo. `instalar()` troca `datetime` no módulo `datetime` e em todo módulo `app.*`
    carregado que o importou pelo nome — `datetime.now(...)` do motor passa a ler `agora()`.

    ⚠️ `datetime.now()` sem fuso devolve o instante em UTC sem fuso (o motor sempre pede `timezone.utc`).
    Desinstalado, a classe trocada volta a devolver o tempo real (módulo importado DURANTE o teste
    guarda a classe; ela não pode congelar o tempo dele para sempre)."""

    def __init__(self, inicio: Optional[_DATETIME_REAL] = None):
        base = inicio or _DATETIME_REAL.now(timezone.utc).replace(microsecond=0)
        self._t = base if base.tzinfo else base.replace(tzinfo=timezone.utc)
        self.inicio = self._t
        self.ativo = False
        self._trocas: list = []
        relogio = self

        class DatetimeDoRelogio(_DATETIME_REAL, metaclass=_MetaDatetime):
            @classmethod
            def now(cls, tz=None):
                if not relogio.ativo:
                    return _DATETIME_REAL.now(tz)
                t = relogio.agora()
                return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)

            @classmethod
            def utcnow(cls):
                if not relogio.ativo:
                    return _DATETIME_REAL.now(timezone.utc).replace(tzinfo=None)
                return relogio.agora().replace(tzinfo=None)

        self.classe = DatetimeDoRelogio

    def agora(self) -> _DATETIME_REAL:
        return self._t

    def iso(self) -> str:
        return self._t.isoformat()

    def segundos(self) -> float:
        """Segundos desde o início do mundo (para a linha do tempo dos cenários)."""
        return (self._t - self.inicio).total_seconds()

    def avancar(self, segundos: float) -> None:
        self._t = self._t + timedelta(seconds=segundos)

    def _trocar(self, mod: Any) -> None:
        if getattr(mod, "datetime", None) is _DATETIME_REAL:
            self._trocas.append((mod, "datetime", _DATETIME_REAL))
            setattr(mod, "datetime", self.classe)

    def instalar(self) -> "Relogio":
        self.ativo = True
        self._trocar(_modulo_datetime)
        for nome, mod in list(sys.modules.items()):
            if mod is not None and (nome == "app" or nome.startswith("app.")
                                    or nome.startswith("portal_worker")):
                self._trocar(mod)
        return self

    def cobrir(self, *mods: Any) -> None:
        """Módulos carregados DEPOIS do `instalar()` (ex.: o código de 04/10 lido do git)."""
        for mod in mods:
            self._trocar(mod)

    def desinstalar(self) -> None:
        for mod, nome, original in reversed(self._trocas):
            setattr(mod, nome, original)
        self._trocas.clear()
        self.ativo = False


# ═════════════════════════════════════════════════════════════════════════════
# O ESQUEMA — 📊 retrato do banco real (04/10/2026) + a `_02` da SPEC-129-A
# coluna: (tipo, aceita_nulo, default)   default: 'UUID' | 'NOW' | 'SERIAL' | 'JSON:<literal>' | valor
# ═════════════════════════════════════════════════════════════════════════════
ESQUEMA: dict[str, dict[str, tuple]] = {
    "work_runs": {
        "id": ("uuid", False, 'UUID'),
        "company_id": ("uuid", False, None),
        "requester_user_id": ("uuid", True, None),
        "requester_agent_id": ("uuid", True, None),
        "parent_run_id": ("uuid", True, None),
        "correlation_id": ("uuid", False, 'UUID'),
        "source_type": ("text", False, None),
        "source_id": ("text", True, None),
        "outcome_type": ("text", False, None),
        "outcome_title": ("text", False, None),
        "outcome_description": ("text", True, None),
        "status": ("enum", False, 'draft'),
        "priority": ("int", False, 50),
        "risk_level": ("text", False, 'low'),
        "visibility": ("text", False, 'company'),
        "owner_user_id": ("uuid", True, None),
        "runtime_kind": ("text", False, 'smith'),
        "workflow_key": ("text", False, None),
        "workflow_version": ("text", False, '1.0.0'),
        "thread_id": ("text", False, None),
        "graph_version": ("text", False, '1'),
        "input_payload": ("jsonb", False, 'JSON:{}'),
        "input_fingerprint": ("text", False, None),
        "result_summary": ("text", True, None),
        "result_payload": ("jsonb", False, 'JSON:{}'),
        "error_code": ("text", True, None),
        "error_message": ("text", True, None),
        "progress_percent": ("int", False, 0),
        "current_step_key": ("text", True, None),
        "idempotency_key": ("text", False, None),
        "cost_budget_brl": ("num", True, None),
        "cost_actual_brl": ("num", False, 0),
        "currency": ("text", False, 'BRL'),
        "requested_at": ("ts", False, 'NOW'),
        "queued_at": ("ts", True, None),
        "started_at": ("ts", True, None),
        "paused_at": ("ts", True, None),
        "finished_at": ("ts", True, None),
        "cancel_requested_at": ("ts", True, None),
        "cancelled_at": ("ts", True, None),
        "next_attempt_at": ("ts", True, None),
        "lease_owner": ("text", True, None),
        "lease_token": ("uuid", True, None),
        "lease_expires_at": ("ts", True, None),
        "heartbeat_at": ("ts", True, None),
        "created_at": ("ts", False, 'NOW'),
        "updated_at": ("ts", False, 'NOW'),
        "skill_release_id": ("uuid", True, None),
        "capability_pack_release_id": ("uuid", True, None),
        "unblock_state": ("text", True, None),
        "conversation_id": ("uuid", True, None),
        # 🔴 SPEC-129-A `_02` (ainda NÃO no banco em 04/10): a espera durável
        "wake_at": ("ts", True, None),
        "wait_for": ("jsonb", True, None),
    },
    "work_steps": {
        "id": ("uuid", False, 'UUID'),
        "work_run_id": ("uuid", False, None),
        "company_id": ("uuid", False, None),
        "step_key": ("text", False, None),
        "ordinal": ("int", False, None),
        "name": ("text", False, None),
        "step_type": ("text", False, None),
        "status": ("enum", False, 'pending'),
        "risk_level": ("text", False, 'low'),
        "capability_key": ("text", True, None),
        "tool_name": ("text", True, None),
        "input_summary": ("jsonb", False, 'JSON:{}'),
        "output_summary": ("jsonb", False, 'JSON:{}'),
        "checkpoint_id": ("text", True, None),
        "approval_request_id": ("uuid", True, None),
        "idempotency_key": ("text", False, None),
        "attempt_count": ("int", False, 0),
        "max_attempts": ("int", False, 1),
        "timeout_seconds": ("int", True, None),
        "started_at": ("ts", True, None),
        "finished_at": ("ts", True, None),
        "created_at": ("ts", False, 'NOW'),
        "updated_at": ("ts", False, 'NOW'),
        "skill_release_id": ("uuid", True, None),
        "tool_release_id": ("uuid", True, None),
        "output_redacted": ("jsonb", True, None),
    },
    "work_attempts": {
        "id": ("uuid", False, 'UUID'),
        "company_id": ("uuid", False, None),
        "work_run_id": ("uuid", False, None),
        "work_step_id": ("uuid", False, None),
        "attempt_number": ("int", False, None),
        "worker_id": ("text", True, None),
        "lease_token": ("uuid", True, None),
        "status": ("text", False, 'running'),
        "started_at": ("ts", False, 'NOW'),
        "finished_at": ("ts", True, None),
        "error_class": ("text", True, None),
        "error_code": ("text", True, None),
        "error_message_redacted": ("text", True, None),
        "retryable": ("bool", True, None),
        "retry_after": ("ts", True, None),
        "metrics": ("jsonb", False, 'JSON:{}'),
        "trace_id": ("text", True, None),
        "created_at": ("ts", False, 'NOW'),
    },
    "work_queue_outbox": {
        "id": ("uuid", False, 'UUID'),
        "company_id": ("uuid", False, None),
        "work_run_id": ("uuid", False, None),
        "event_kind": ("text", False, None),
        "payload_minimal": ("jsonb", False, 'JSON:{}'),
        "status": ("text", False, 'pending'),
        "attempts": ("int", False, 0),
        "next_attempt_at": ("ts", False, 'NOW'),
        "published_at": ("ts", True, None),
        "redis_entry_id": ("text", True, None),
        "last_error": ("text", True, None),
        "created_at": ("ts", False, 'NOW'),
        "updated_at": ("ts", False, 'NOW'),
    },
    "work_events": {
        "id": ("int", False, 'SERIAL'),
        "company_id": ("uuid", False, None),
        "work_run_id": ("uuid", True, None),
        "work_step_id": ("uuid", True, None),
        "attempt_id": ("uuid", True, None),
        "event_type": ("text", False, None),
        "actor_type": ("text", False, 'system'),
        "actor_id": ("text", True, None),
        "severity": ("text", False, 'info'),
        "message_human": ("text", False, None),
        "payload_redacted": ("jsonb", False, 'JSON:{}'),
        "created_at": ("ts", False, 'NOW'),
    },
    "portal_jobs": {
        "id": ("uuid", False, 'UUID'),
        "company_id": ("uuid", False, None),
        "portal_key": ("text", False, None),
        "journey": ("text", False, None),
        "account_id": ("uuid", True, None),
        "params": ("jsonb", False, 'JSON:{}'),
        "status": ("text", False, 'queued'),
        "evidence": ("jsonb", False, 'JSON:{}'),
        "screenshots": ("jsonb", False, 'JSON:[]'),
        "error": ("text", True, None),
        "attempts": ("int", False, 0),
        "created_at": ("ts", False, 'NOW'),
        "started_at": ("ts", True, None),
        "finished_at": ("ts", True, None),
        "idempotency_key": ("text", True, None),
        "session_id": ("text", True, None),
        "agent_id": ("uuid", True, None),
        "work_run_id": ("uuid", True, None),
        "work_step_id": ("uuid", True, None),
        "tool_invocation_id": ("uuid", True, None),
        "operation_key": ("text", True, None),
        "priority": ("int", False, 100),
        "available_at": ("ts", True, None),
    },
    "portal_accounts": {
        "id": ("uuid", False, 'UUID'),
        "company_id": ("uuid", False, None),
        "portal_key": ("text", False, None),
        "account_label": ("text", False, 'principal'),
        "username": ("text", True, None),
        "secret_encrypted": ("text", True, None),
        "health": ("text", False, 'unknown'),
        "created_at": ("ts", False, 'NOW'),
        "updated_at": ("ts", False, 'NOW'),
    },
    "companies": {
        "id": ("uuid", False, 'UUID'),
    },
}
#: as colunas que a SPEC-129-A `_02` acrescenta (o banco vivo ainda não as tem antes do APPLY)
COLUNAS_DA_02 = {"work_runs": {"wake_at", "wait_for"}}

#: 📊 `pg_enum` em 04/10/2026
ENUMS = {
    ("work_runs", "status"): ("draft", "queued", "planning", "running", "waiting_approval",
                              "waiting_input", "paused", "retry_scheduled", "cancelling",
                              "cancelled", "failed", "completed", "expired"),
    ("work_steps", "status"): ("pending", "running", "waiting_approval", "waiting_input",
                               "succeeded", "failed", "skipped", "cancelled"),
}
ESTADOS_TERMINAIS_DO_RUN = ("completed", "failed", "cancelled", "expired")


# ═════════════════════════════════════════════════════════════════════════════
# Valores
# ═════════════════════════════════════════════════════════════════════════════
def _tipo(tabela: str, coluna: str) -> Optional[str]:
    return (ESQUEMA.get(tabela) or {}).get(coluna, (None,))[0]


def _para_ts(v: Any) -> Optional[_DATETIME_REAL]:
    if v is None:
        return None
    if isinstance(v, _DATETIME_REAL):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip().replace("Z", "+00:00").replace(" ", "T", 1)
    try:
        d = _DATETIME_REAL.fromisoformat(s)
    except ValueError:
        raise erro_do_banco("22007", f'invalid input syntax for type timestamp with time zone: "{v}"')
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _coagir(tabela: str, coluna: str, v: Any) -> Any:
    """O valor como o Postgres o compararia (tipo da coluna)."""
    if v is None:
        return None
    tipo = _tipo(tabela, coluna)
    if tipo == "ts":
        return _para_ts(v)
    if tipo == "int":
        try:
            return int(v)
        except (TypeError, ValueError):
            raise erro_do_banco("22P02", f'invalid input syntax for type integer: "{v}"')
    if tipo == "num":
        return float(v)
    if tipo == "bool":
        return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "t", "1")
    if tipo == "uuid":
        try:
            return str(uuid.UUID(str(v)))
        except ValueError:
            raise erro_do_banco("22P02", f'invalid input syntax for type uuid: "{v}"')
    if tipo == "jsonb":
        return v
    return str(v)


def _normalizar_para_gravar(tabela: str, coluna: str, v: Any) -> Any:
    """Como o banco devolveria o valor gravado (ISO para timestamp, uuid minúsculo)."""
    if v is None:
        return None
    tipo = _tipo(tabela, coluna)
    if tipo == "ts":
        return _para_ts(v).isoformat()
    if tipo == "uuid":
        return _coagir(tabela, coluna, v)
    if tipo == "int":
        return _coagir(tabela, coluna, v)
    if tipo == "num":
        return float(v)
    if tipo == "bool":
        return _coagir(tabela, coluna, v)
    if tipo == "enum":
        lista = ENUMS.get((tabela, coluna))
        if lista and str(v) not in lista:
            raise erro_do_banco("22P02", f'invalid input value for enum {tabela}_{coluna}: "{v}"')
        return str(v)
    return v


def _pelo_fio(payload: Any) -> Any:
    """O supabase-py serializa o corpo em JSON: o que não serializa, não chega ao banco."""
    try:
        return json.loads(json.dumps(payload))
    except TypeError as exc:
        raise TypeError(f"corpo do PostgREST não serializa em JSON: {exc}") from exc


# ═════════════════════════════════════════════════════════════════════════════
# Filtros — a semântica do PostgREST/SQL
# ═════════════════════════════════════════════════════════════════════════════
@dataclass
class Filtro:
    op: str            # eq neq gt gte lt lte in is like ilike
    coluna: str
    valor: Any
    negado: bool = False


@dataclass
class Grupo:
    tipo: str          # "or" | "and"
    itens: list
    negado: bool = False


def _dividir_no_topo(texto: str) -> list[str]:
    partes, nivel, atual, aspas = [], 0, [], False
    for ch in texto:
        if ch == '"':
            aspas = not aspas
        if not aspas and ch == "(":
            nivel += 1
        elif not aspas and ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0 and not aspas:
            partes.append("".join(atual))
            atual = []
        else:
            atual.append(ch)
    if atual:
        partes.append("".join(atual))
    return [p.strip() for p in partes if p.strip()]


def _parse_logico(texto: str) -> list:
    """`a.is.null,a.lt.2026-…,and(b.eq.1,c.neq.2)` → [Filtro|Grupo]."""
    itens = []
    for parte in _dividir_no_topo(texto):
        negado = False
        p = parte
        if p.startswith("not.") and (p[4:].startswith("and(") or p[4:].startswith("or(")):
            negado, p = True, p[4:]
        if p.startswith("and(") or p.startswith("or("):
            tipo = "and" if p.startswith("and(") else "or"
            dentro = p[len(tipo) + 1:-1]
            itens.append(Grupo(tipo, _parse_logico(dentro), negado))
            continue
        coluna, _, resto = p.partition(".")
        neg = False
        if resto.startswith("not."):
            neg, resto = True, resto[4:]
        op, _, valor = resto.partition(".")
        if op == "in":
            valor = [v.strip().strip('"') for v in valor.strip("()").split(",") if v.strip()]
        elif isinstance(valor, str) and valor.startswith('"') and valor.endswith('"'):
            valor = valor[1:-1]
        itens.append(Filtro(op, coluna, valor, neg))
    return itens


def _casa_filtro(tabela: str, linha: dict, f: Filtro) -> bool:
    if f.coluna not in linha and tabela in ESQUEMA:
        raise erro_do_banco("42703", f"column {tabela}.{f.coluna} does not exist")
    x = linha.get(f.coluna)
    if f.op == "is":
        v = f.valor
        if v is None or str(v).lower() == "null":
            r = x is None
        else:
            r = x is not None and bool(x) == (str(v).lower() == "true")
        return (not r) if f.negado else r
    if x is None:  # NULL op valor = NULL; NOT NULL = NULL → a linha NÃO casa, negada ou não
        return False
    xv = _coagir(tabela, f.coluna, x)
    if f.op == "in":
        r = xv in [_coagir(tabela, f.coluna, v) for v in (f.valor or [])]
    elif f.op in ("like", "ilike"):
        rx = "^" + re.escape(str(f.valor)).replace("%", ".*").replace(r"\*", ".*") + "$"
        r = re.match(rx, str(xv), re.I if f.op == "ilike" else 0) is not None
    else:
        v = _coagir(tabela, f.coluna, f.valor)
        if v is None:
            return False
        r = {"eq": xv == v, "neq": xv != v, "gt": xv > v, "gte": xv >= v,
             "lt": xv < v, "lte": xv <= v}.get(f.op)
        if r is None:
            raise erro_do_banco("PGRST100", f"operador desconhecido no dublê: {f.op}")
    return (not r) if f.negado else r


def _casa(tabela: str, linha: dict, itens: list, tipo: str = "and") -> bool:
    resultados = []
    for it in itens:
        if isinstance(it, Grupo):
            r = _casa(tabela, linha, it.itens, it.tipo)
            r = (not r) if it.negado else r
        else:
            r = _casa_filtro(tabela, linha, it)
        resultados.append(r)
    return all(resultados) if tipo == "and" else any(resultados)


# ═════════════════════════════════════════════════════════════════════════════
# O registro das escritas (para as auditorias: "nenhuma escrita cruza company_id")
# ═════════════════════════════════════════════════════════════════════════════
@dataclass
class Escrita:
    dono: str
    tabela: str
    op: str                      # insert | update | delete | upsert | rpc
    filtros: list
    payload: Any
    antes: list = field(default_factory=list)
    depois: list = field(default_factory=list)
    instante: Optional[str] = None

    def filtros_eq(self) -> dict:
        """Os `eq` de topo, não negados (o que um CAS declara)."""
        return {f.coluna: f.valor for f in self.filtros
                if isinstance(f, Filtro) and f.op == "eq" and not f.negado}


class _Resposta:
    def __init__(self, data: Any, count: Optional[int] = None):
        self.data = data
        self.count = count


# ═════════════════════════════════════════════════════════════════════════════
# O banco
# ═════════════════════════════════════════════════════════════════════════════
class BancoEmMemoria:
    def __init__(self, relogio: Relogio):
        self.relogio = relogio
        self.tabelas: dict[str, list[dict]] = {}
        self.escritas: list[Escrita] = []
        self.lock = threading.RLock()
        self._serial = 0
        self._ganchos: list[tuple[str, str, Callable]] = []
        self.rpcs: dict[str, Callable] = {
            "work_run_create": self._rpc_work_run_create,
            "work_steps_mascarar_vencidos": lambda dono, p: 0,
        }

    # -- acesso direto do TESTE (não passa pelo motor) -------------------
    def linhas(self, tabela: str) -> list[dict]:
        return self.tabelas.setdefault(tabela, [])

    def run(self, run_id: str) -> dict:
        return next((r for r in self.linhas("work_runs") if r["id"] == run_id), {})

    def semear(self, tabela: str, linha: dict) -> dict:
        with self.lock:
            return self._inserir("semeadura", tabela, [linha])[0]

    def ao_gravar(self, tabela: str, op: str, gancho: Callable[["Escrita"], None]) -> None:
        """Depois de a escrita ENTRAR no banco, chama `gancho(escrita)` — ele pode matar o processo."""
        self._ganchos.append((tabela, op, gancho))

    def visao(self, dono: str) -> "VisaoDoBanco":
        return VisaoDoBanco(self, dono)

    # -- defaults e travas ------------------------------------------------
    def _defaults(self, tabela: str, linha: dict) -> dict:
        esquema = ESQUEMA.get(tabela)
        nova = dict(linha)
        if not esquema:
            nova.setdefault("id", str(uuid.uuid4()))
            nova.setdefault("created_at", self.relogio.iso())
            return nova
        desconhecidas = sorted(set(nova) - set(esquema))
        if desconhecidas:
            raise erro_do_banco("PGRST204", f"Could not find the '{desconhecidas[0]}' column of "
                                             f"'{tabela}' in the schema cache")
        for col, (_t, _nulo, dflt) in esquema.items():
            if col in nova:
                continue
            if dflt == "UUID":
                nova[col] = str(uuid.uuid4())
            elif dflt == "NOW":
                nova[col] = self.relogio.iso()
            elif dflt == "SERIAL":
                self._serial += 1
                nova[col] = self._serial
            elif isinstance(dflt, str) and dflt.startswith("JSON:"):
                nova[col] = json.loads(dflt[5:])
            else:
                nova[col] = dflt
        return nova

    def _normalizar(self, tabela: str, linha: dict) -> dict:
        if tabela not in ESQUEMA:
            return linha
        return {c: _normalizar_para_gravar(tabela, c, v) for c, v in linha.items()}

    def _unico(self, tabela: str, nome: str, cols: tuple, nova: dict, ignorar: Optional[dict],
               onde: Optional[Callable[[dict], bool]] = None) -> None:
        if any(nova.get(c) is None for c in cols) or (onde and not onde(nova)):
            return
        chave = tuple(_coagir(tabela, c, nova.get(c)) for c in cols)
        for r in self.linhas(tabela):
            if r is ignorar or (onde and not onde(r)):
                continue
            if tuple(_coagir(tabela, c, r.get(c)) for c in cols) == chave:
                raise erro_do_banco("23505", f'duplicate key value violates unique constraint "{nome}"',
                                    f"Key ({', '.join(cols)})=({', '.join(map(str, chave))}) already exists.")

    def _fk(self, tabela: str, nome: str, pares: tuple, ref: str, nova: dict) -> None:
        if any(nova.get(c) is None for c, _ in pares):
            return
        for r in self.linhas(ref):
            if all(_coagir(tabela, c, nova.get(c)) == _coagir(ref, rc, r.get(rc)) for c, rc in pares):
                return
        raise erro_do_banco("23503", f'insert or update on table "{tabela}" violates foreign key '
                                     f'constraint "{nome}"')

    def _check(self, nome: str, ok: bool) -> None:
        if not ok:
            raise erro_do_banco("23514", f'new row violates check constraint "{nome}"')

    def _travas(self, tabela: str, nova: dict, velha: Optional[dict]) -> None:
        esquema = ESQUEMA.get(tabela)
        if not esquema:
            return
        for col, (_t, nulo, _d) in esquema.items():
            if not nulo and nova.get(col) is None:
                raise erro_do_banco("23502", f'null value in column "{col}" of relation "{tabela}" '
                                             f"violates not-null constraint")
        if tabela != "companies" and "company_id" in esquema:
            self._fk(tabela, f"{tabela}_company_id_fkey", (("company_id", "id"),), "companies", nova)
        if tabela == "work_runs":
            if velha is not None and _coagir(tabela, "company_id", velha["company_id"]) != \
                    _coagir(tabela, "company_id", nova["company_id"]):
                raise erro_do_banco("P0001", "trg_work_runs_company_imutavel: company_id não muda")
            self._unico(tabela, "uq_work_runs_company_idempotency", ("company_id", "idempotency_key"),
                        nova, velha)
            self._unico(tabela, "uq_work_runs_thread", ("thread_id",), nova, velha)
            self._unico(tabela, "work_runs_pkey", ("id",), nova, velha)
            self._check("ck_work_runs_thread_format",
                        nova["thread_id"] == f"work:{nova['company_id']}:{nova['id']}")
            lease = [nova.get(c) for c in ("lease_owner", "lease_token", "lease_expires_at")]
            self._check("ck_work_runs_lease_coerente",
                        all(v is None for v in lease) or all(v is not None for v in lease))
            self._check("ck_work_runs_progress", 0 <= int(nova["progress_percent"]) <= 100)
            self._check("ck_work_runs_risk", nova["risk_level"] in ("low", "medium", "high", "critical"))
            self._check("ck_work_runs_source", nova["source_type"] in (
                "chat", "routine", "auxiliary", "portal", "api", "admin", "system", "retry", "child_run"))
            # 🔴 SPEC-129-A `_02`
            self._check("ck_work_runs_wake_so_da_fila",
                        nova.get("wake_at") is None or nova["runtime_kind"] == "smith")
            self._check("ck_work_runs_espera_tem_relogio",
                        nova["runtime_kind"] != "smith"
                        or nova["status"] not in ("waiting_input", "retry_scheduled")
                        or nova.get("wake_at") is not None)
        elif tabela == "work_steps":
            self._unico(tabela, "uq_work_steps_run_key", ("work_run_id", "step_key"), nova, velha)
            self._unico(tabela, "uq_work_steps_company_idempotency", ("company_id", "idempotency_key"),
                        nova, velha)
            self._fk(tabela, "fk_work_steps_run_same_company",
                     (("work_run_id", "id"), ("company_id", "company_id")), "work_runs", nova)
            self._check("ck_work_steps_attempts",
                        int(nova["attempt_count"]) >= 0 and int(nova["max_attempts"]) >= 1)
        elif tabela == "work_attempts":
            self._unico(tabela, "uq_work_attempts_step_number", ("work_step_id", "attempt_number"),
                        nova, velha)
            self._fk(tabela, "fk_work_attempts_step_same_company",
                     (("work_step_id", "id"), ("company_id", "company_id")), "work_steps", nova)
            self._check("ck_work_attempts_number", int(nova["attempt_number"]) >= 1)
        elif tabela == "work_queue_outbox":
            self._fk(tabela, "fk_work_outbox_run_same_company",
                     (("work_run_id", "id"), ("company_id", "company_id")), "work_runs", nova)
            self._check("ck_work_outbox_status",
                        nova["status"] in ("pending", "published", "failed", "abandoned"))
        elif tabela == "work_events":
            if velha is not None:
                raise erro_do_banco("P0001", "trg_work_events_no_update: a linha do tempo não se reescreve")
            self._fk(tabela, "fk_work_events_run_same_company",
                     (("work_run_id", "id"), ("company_id", "company_id")), "work_runs", nova)
            self._check("ck_work_events_actor", nova["actor_type"] in (
                "system", "worker", "user", "agent", "admin", "provider"))
            self._check("ck_work_events_severity", nova["severity"] in (
                "debug", "info", "warning", "error", "critical"))
        elif tabela == "portal_jobs":
            self._unico(tabela, "idx_portal_jobs_pedido_vivo", ("company_id", "idempotency_key"), nova,
                        velha, onde=lambda r: r.get("status") != "failed")
            self._fk(tabela, "fk_portal_jobs_account_same_company",
                     (("account_id", "id"), ("company_id", "company_id")), "portal_accounts", nova)
        elif tabela == "portal_accounts":
            self._unico(tabela, "portal_accounts_company_id_portal_key_account_label_key",
                        ("company_id", "portal_key", "account_label"), nova, velha)

    # -- as quatro operações (chamadas SOB o lock) -------------------------
    def _inserir(self, dono: str, tabela: str, linhas: list[dict]) -> list[dict]:
        novas = []
        for linha in linhas:
            nova = self._normalizar(tabela, self._defaults(tabela, _pelo_fio(linha)))
            self._travas(tabela, nova, None)
            for ja in novas:  # duas linhas do MESMO insert também colidem
                if tabela == "work_steps" and (ja["work_run_id"], ja["step_key"]) == \
                        (nova["work_run_id"], nova["step_key"]):
                    raise erro_do_banco("23505", 'duplicate key value violates unique constraint '
                                                 '"uq_work_steps_run_key"')
            novas.append(nova)
        self.linhas(tabela).extend(novas)
        self._registrar(Escrita(dono, tabela, "insert", [], linhas, [], copy.deepcopy(novas)))
        return copy.deepcopy(novas)

    def _atualizar(self, dono: str, tabela: str, filtros: list, patch: dict) -> list[dict]:
        patch = _pelo_fio(patch)
        if tabela in ESQUEMA:
            desconhecidas = sorted(set(patch) - set(ESQUEMA[tabela]))
            if desconhecidas:
                raise erro_do_banco("PGRST204", f"Could not find the '{desconhecidas[0]}' column of "
                                                 f"'{tabela}' in the schema cache")
        alvo = [r for r in self.linhas(tabela) if _casa(tabela, r, filtros)]
        antes = copy.deepcopy(alvo)
        novas = []
        for r in alvo:  # confere TODAS antes de gravar qualquer uma (o UPDATE é atômico)
            nova = {**r, **self._normalizar(tabela, patch)}
            self._travas(tabela, nova, r)
            novas.append(nova)
        for r, nova in zip(alvo, novas):
            r.clear()
            r.update(nova)
        self._registrar(Escrita(dono, tabela, "update", filtros, patch, antes, copy.deepcopy(alvo)))
        return copy.deepcopy(alvo)

    def _apagar(self, dono: str, tabela: str, filtros: list) -> list[dict]:
        alvo = [r for r in self.linhas(tabela) if _casa(tabela, r, filtros)]
        self.tabelas[tabela] = [r for r in self.linhas(tabela) if all(r is not a for a in alvo)]
        self._registrar(Escrita(dono, tabela, "delete", filtros, None, copy.deepcopy(alvo), []))
        return copy.deepcopy(alvo)

    def _registrar(self, escrita: Escrita) -> None:
        escrita.instante = self.relogio.iso()
        self.escritas.append(escrita)

    def _depois_de_gravar(self, escrita: Escrita) -> None:
        for tabela, op, gancho in list(self._ganchos):
            if tabela == escrita.tabela and op == escrita.op:
                gancho(escrita)

    # -- RPC: o MESMO corpo de `public.work_run_create` (📊 pg_get_functiondef, 04/10) --------
    def _rpc_work_run_create(self, dono: str, p: dict) -> list[dict]:
        cid, chave = p["p_company_id"], p["p_idempotency_key"]
        existente = next((r for r in self.linhas("work_runs")
                          if r["company_id"] == _coagir("work_runs", "company_id", cid)
                          and r["idempotency_key"] == chave), None)
        if existente:
            return [{"run_id": existente["id"], "thread_id": existente["thread_id"],
                     "status": existente["status"], "reused": True}]
        rid = str(uuid.uuid4())
        entrada = p.get("p_input_payload") or {}
        import hashlib

        fp = p.get("p_input_fingerprint") or hashlib.sha256(
            json.dumps(entrada, sort_keys=True).encode()).hexdigest()
        linha = {
            "id": rid, "company_id": cid, "requester_user_id": p.get("p_requester_user_id"),
            "parent_run_id": p.get("p_parent_run_id"),
            "correlation_id": p.get("p_correlation_id") or str(uuid.uuid4()),
            "source_type": p["p_source_type"], "source_id": p.get("p_source_id"),
            "outcome_type": p["p_outcome_type"], "outcome_title": p["p_outcome_title"],
            "status": "queued", "priority": p.get("p_priority", 50),
            "risk_level": p.get("p_risk_level", "low"), "workflow_key": p["p_workflow_key"],
            "workflow_version": p.get("p_workflow_version", "1.0.0"),
            "thread_id": f"work:{cid}:{rid}", "input_payload": entrada, "input_fingerprint": fp,
            "idempotency_key": chave, "cost_budget_brl": p.get("p_cost_budget_brl"),
            "queued_at": self.relogio.iso(),
        }
        self._inserir(dono, "work_runs", [linha])
        self._inserir(dono, "work_queue_outbox", [{
            "company_id": cid, "work_run_id": rid, "event_kind": "run.queued",
            "payload_minimal": {"run_id": rid, "company_id": cid, "priority": p.get("p_priority", 50),
                                "workflow_key": p["p_workflow_key"]}}])
        self._inserir(dono, "work_events", [{
            "company_id": cid, "work_run_id": rid, "event_type": "run.created", "actor_type": "system",
            "message_human": "Trabalho criado: " + p["p_outcome_title"],
            "payload_redacted": {"source_type": p["p_source_type"], "workflow_key": p["p_workflow_key"]}}])
        self._inserir(dono, "work_events", [{
            "company_id": cid, "work_run_id": rid, "event_type": "run.queued", "actor_type": "system",
            "message_human": "Trabalho entrou na fila"}])
        return [{"run_id": rid, "thread_id": f"work:{cid}:{rid}", "status": "queued", "reused": False}]


class VisaoDoBanco:
    """O cliente supabase de UM processo. `client` aponta para si (o motor faz `getattr(db, "client", db)`)."""

    def __init__(self, banco: BancoEmMemoria, dono: str):
        self.banco = banco
        self.dono = dono
        self.morto = False

    @property
    def client(self) -> "VisaoDoBanco":
        return self

    def conferir_vivo(self) -> None:
        if self.morto:
            raise MorteDoProcesso(f"o processo {self.dono} morreu")

    def table(self, nome: str) -> "Consulta":
        self.conferir_vivo()
        return Consulta(self, nome)

    from_ = table

    def schema(self, *_a, **_k) -> "VisaoDoBanco":
        return self

    def rpc(self, nome: str, params: Optional[dict] = None) -> "_ChamadaRPC":
        self.conferir_vivo()
        return _ChamadaRPC(self, nome, params or {})


class _ChamadaRPC:
    def __init__(self, visao: VisaoDoBanco, nome: str, params: dict):
        self.visao, self.nome, self.params = visao, nome, params

    def execute(self) -> _Resposta:
        self.visao.conferir_vivo()
        b = self.visao.banco
        fn = b.rpcs.get(self.nome)
        if fn is None:
            raise erro_do_banco("PGRST202", f"Could not find the function public.{self.nome} in the "
                                             f"schema cache")
        with b.lock:
            dados = fn(self.visao.dono, _pelo_fio(self.params))
            b._registrar(Escrita(self.visao.dono, f"rpc:{self.nome}", "rpc", [], self.params, [],
                                 copy.deepcopy(dados) if isinstance(dados, list) else []))
        return _Resposta(dados)


class _Negacao:
    def __init__(self, consulta: "Consulta"):
        self._c = consulta

    def __getattr__(self, nome):
        metodo = getattr(self._c, nome)

        def negado(*a, **k):
            self._c._negar_proximo = True
            return metodo(*a, **k)
        return negado


class Consulta:
    """O construtor de consulta do postgrest-py, na parte que o motor usa."""

    def __init__(self, visao: VisaoDoBanco, tabela: str):
        self.visao, self.tabela = visao, tabela
        self.op = "select"
        self.payload: Any = None
        self.filtros: list = []
        self.colunas: Optional[list[str]] = None
        self.ordem: list[tuple[str, bool]] = []
        self.lim: Optional[int] = None
        self.offset = 0
        self.unico: Optional[str] = None       # "maybe" | "single"
        self.contar = False
        self.upsert_conflito: Optional[str] = None
        self.ignorar_duplicadas = False
        self._negar_proximo = False

    # -- operação --------------------------------------------------------
    def select(self, colunas: str = "*", *_, count: Optional[str] = None, **__) -> "Consulta":
        self.op = "select" if self.op == "select" else self.op
        cols = [c.strip() for c in (colunas or "*").split(",") if c.strip()]
        self.colunas = None if "*" in cols else cols
        self.contar = bool(count)
        return self

    def insert(self, linhas: Any, **_k) -> "Consulta":
        self.op, self.payload = "insert", linhas
        return self

    def update(self, patch: dict, **_k) -> "Consulta":
        self.op, self.payload = "update", patch
        return self

    def upsert(self, linhas: Any, *, on_conflict: str = "", ignore_duplicates: bool = False,
               **_k) -> "Consulta":
        self.op, self.payload = "upsert", linhas
        self.upsert_conflito, self.ignorar_duplicadas = on_conflict, ignore_duplicates
        return self

    def delete(self, **_k) -> "Consulta":
        self.op = "delete"
        return self

    # -- filtros ---------------------------------------------------------
    def _f(self, op: str, coluna: str, valor: Any) -> "Consulta":
        self.filtros.append(Filtro(op, coluna, valor, self._negar_proximo))
        self._negar_proximo = False
        return self

    def eq(self, c, v): return self._f("eq", c, v)
    def neq(self, c, v): return self._f("neq", c, v)
    def gt(self, c, v): return self._f("gt", c, v)
    def gte(self, c, v): return self._f("gte", c, v)
    def lt(self, c, v): return self._f("lt", c, v)
    def lte(self, c, v): return self._f("lte", c, v)
    def like(self, c, v): return self._f("like", c, v)
    def ilike(self, c, v): return self._f("ilike", c, v)
    def in_(self, c, v): return self._f("in", c, list(v))
    def is_(self, c, v): return self._f("is", c, v)

    def filter(self, coluna: str, operador: str, valor: Any) -> "Consulta":
        neg = operador.startswith("not.")
        op = operador[4:] if neg else operador
        if op == "in" and isinstance(valor, str):
            valor = [v.strip().strip('"') for v in valor.strip("()").split(",") if v.strip()]
        self._negar_proximo = neg
        return self._f(op, coluna, valor)

    def match(self, d: dict) -> "Consulta":
        for c, v in d.items():
            self.eq(c, v)
        return self

    def or_(self, expressao: str, *_a, **_k) -> "Consulta":
        self.filtros.append(Grupo("or", _parse_logico(expressao), self._negar_proximo))
        self._negar_proximo = False
        return self

    @property
    def not_(self) -> _Negacao:
        return _Negacao(self)

    # -- forma -----------------------------------------------------------
    def order(self, coluna: str, *, desc: bool = False, **_k) -> "Consulta":
        self.ordem.append((coluna, desc))
        return self

    def limit(self, n: int, **_k) -> "Consulta":
        self.lim = int(n)
        return self

    def range(self, inicio: int, fim: int, **_k) -> "Consulta":
        self.offset, self.lim = int(inicio), int(fim) - int(inicio) + 1
        return self

    def maybe_single(self) -> "Consulta":
        self.unico = "maybe"
        return self

    def single(self) -> "Consulta":
        self.unico = "single"
        return self

    # -- execução --------------------------------------------------------
    def _ordenar(self, linhas: list[dict]) -> list[dict]:
        for coluna, desc in reversed(self.ordem):
            com = [r for r in linhas if r.get(coluna) is not None]
            sem = [r for r in linhas if r.get(coluna) is None]
            com.sort(key=lambda r: _coagir(self.tabela, coluna, r.get(coluna)), reverse=desc)
            linhas = (sem + com) if desc else (com + sem)  # NULLS FIRST no desc, LAST no asc
        return linhas

    def _projetar(self, linha: dict) -> dict:
        if self.colunas is None:
            return copy.deepcopy(linha)
        saida = {}
        for c in self.colunas:
            nome = c.split(":")[-1].strip()
            if "(" in nome:
                continue
            if nome not in linha and self.tabela in ESQUEMA:
                raise erro_do_banco("42703", f"column {self.tabela}.{nome} does not exist")
            saida[nome] = copy.deepcopy(linha.get(nome))
        return saida

    def execute(self) -> Optional[_Resposta]:
        v = self.visao
        v.conferir_vivo()
        b = v.banco
        escrita = None
        with b.lock:
            if self.op == "select":
                linhas = [r for r in b.linhas(self.tabela) if _casa(self.tabela, r, self.filtros)]
                total = len(linhas)
                linhas = self._ordenar(linhas)[self.offset:]
                if self.lim is not None:
                    linhas = linhas[:self.lim]
                dados = [self._projetar(r) for r in linhas]
                if self.unico == "maybe":
                    if not dados:
                        return None   # 📊 postgrest 0.18: maybe_single sem linha devolve None
                    if len(dados) > 1:
                        raise erro_do_banco("PGRST116", "JSON object requested, multiple rows returned")
                    return _Resposta(dados[0], total if self.contar else None)
                if self.unico == "single":
                    if len(dados) != 1:
                        raise erro_do_banco("PGRST116", "JSON object requested, multiple (or no) rows "
                                                        "returned", "The result contains 0 rows")
                    return _Resposta(dados[0], total if self.contar else None)
                return _Resposta(dados, total if self.contar else None)
            if self.op == "insert":
                linhas = self.payload if isinstance(self.payload, list) else [self.payload]
                dados = b._inserir(v.dono, self.tabela, linhas)
            elif self.op == "update":
                dados = b._atualizar(v.dono, self.tabela, self.filtros, self.payload)
            elif self.op == "delete":
                dados = b._apagar(v.dono, self.tabela, self.filtros)
            elif self.op == "upsert":
                dados = self._upsert(b)
            else:
                raise erro_do_banco("PGRST000", f"operação desconhecida no dublê: {self.op}")
            escrita = b.escritas[-1]
            dados = [self._projetar(r) for r in dados] if self.colunas else dados
        b._depois_de_gravar(escrita)   # FORA do lock: o gancho pode matar o processo
        v.conferir_vivo()
        if self.unico in ("maybe", "single"):
            return _Resposta(dados[0] if dados else None)
        return _Resposta(dados)

    def _upsert(self, b: BancoEmMemoria) -> list[dict]:
        linhas = self.payload if isinstance(self.payload, list) else [self.payload]
        cols = [c.strip() for c in (self.upsert_conflito or "id").split(",") if c.strip()]
        saida = []
        for linha in linhas:
            existente = next((r for r in b.linhas(self.tabela)
                              if all(_coagir(self.tabela, c, r.get(c)) == _coagir(self.tabela, c, linha.get(c))
                                     for c in cols)), None)
            if existente is None:
                saida += b._inserir(self.visao.dono, self.tabela, [linha])
            elif not self.ignorar_duplicadas:
                saida += b._atualizar(self.visao.dono, self.tabela,
                                      [Filtro("eq", c, linha.get(c)) for c in cols], linha)
        return saida


# ═════════════════════════════════════════════════════════════════════════════
# O Redis Streams
# ═════════════════════════════════════════════════════════════════════════════
class RedisStreams:
    """Um stream, um ou mais grupos, PEL por grupo, ocioso medido pelo relógio do mundo."""

    def __init__(self, relogio: Relogio):
        self.relogio = relogio
        self.entradas: dict[str, list[tuple[str, dict]]] = {}
        self.grupos: dict[tuple[str, str], dict] = {}
        self._seq = 0
        self._perder: list[Callable[[dict], bool]] = []
        self.perdidas: list[dict] = []
        self.publicadas: list[dict] = []

    def visao(self, dono: str) -> "VisaoDoRedis":
        return VisaoDoRedis(self, dono)

    def perder_proxima(self, criterio: Callable[[dict], bool]) -> None:
        """C5: a PRÓXIMA mensagem que casar com `criterio(payload)` some — o XADD responde um id,
        mas nenhum consumidor jamais a recebe (stream aparado, failover, Redis reiniciado)."""
        self._perder.append(criterio)

    def _ms(self) -> int:
        return int(self.relogio.agora().timestamp() * 1000)

    def mensagens_para(self, run_id: str) -> list[dict]:
        return [p for p in self.publicadas if p.get("work_run_id") == run_id]


class VisaoDoRedis:
    def __init__(self, redis: RedisStreams, dono: str):
        self.r, self.dono = redis, dono
        self.morto = False
        self.ciclos_vazios = 0   # leituras vazias seguidas (o laço de consumo está ocioso)

    def _vivo(self) -> None:
        if self.morto:
            raise MorteDoProcesso(f"o processo {self.dono} morreu")

    async def xgroup_create(self, stream, grupo, id="0", mkstream=True, **_k):
        self._vivo()
        if (stream, grupo) in self.r.grupos:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.r.entradas.setdefault(stream, [])
        self.r.grupos[(stream, grupo)] = {"ultimo": -1, "pel": {}}
        return True

    async def xadd(self, stream, campos, maxlen=None, approximate=True, **_k):
        self._vivo()
        self.r._seq += 1
        eid = f"{self.r._ms()}-{self.r._seq}"
        try:
            payload = json.loads(campos.get("payload") or "{}")
        except Exception:  # noqa: BLE001
            payload = {}
        for i, criterio in enumerate(list(self.r._perder)):
            if criterio(payload):
                self.r._perder.pop(i)
                self.r.perdidas.append(payload)
                return eid
        self.r.entradas.setdefault(stream, []).append((eid, dict(campos)))
        self.r.publicadas.append(payload)
        return eid

    async def xreadgroup(self, grupo, consumidor, streams, count=1, block=None, **_k):
        self._vivo()
        saida = []
        for stream, _desde in streams.items():
            g = self.r.grupos[(stream, grupo)]
            todas = self.r.entradas.get(stream, [])
            novas = todas[g["ultimo"] + 1: g["ultimo"] + 1 + (count or 1)]
            if novas:
                g["ultimo"] += len(novas)
                for eid, _c in novas:
                    g["pel"][eid] = {"consumidor": consumidor, "entregue_ms": self.r._ms(), "vezes": 1}
                saida.append([stream, [(eid, dict(c)) for eid, c in novas]])
        if not saida:
            await asyncio.sleep(0.002)   # o BLOCK do XREADGROUP, sem prender o laço
            return []
        self.ciclos_vazios = 0
        return saida

    async def xautoclaim(self, stream, grupo, consumidor, min_idle_time=0, start_id="0-0",
                         count=10, **_k):
        self._vivo()
        g = self.r.grupos[(stream, grupo)]
        agora = self.r._ms()
        existentes = dict(self.r.entradas.get(stream, []))
        pegas, apagadas = [], []
        for eid, info in list(g["pel"].items()):
            if len(pegas) >= count:
                break
            if agora - info["entregue_ms"] < min_idle_time:
                continue
            if eid not in existentes:
                apagadas.append(eid)
                g["pel"].pop(eid, None)
                continue
            info.update(consumidor=consumidor, entregue_ms=agora, vezes=info["vezes"] + 1)
            pegas.append((eid, dict(existentes[eid])))
        if pegas:
            self.ciclos_vazios = 0
        else:
            self.ciclos_vazios += 1
        return ["0-0", pegas, apagadas]

    async def xack(self, stream, grupo, *ids):
        self._vivo()
        g = self.r.grupos.get((stream, grupo)) or {"pel": {}}
        n = 0
        for eid in ids:
            if g["pel"].pop(eid, None) is not None:
                n += 1
        return n

    async def xlen(self, stream):
        self._vivo()
        return len(self.r.entradas.get(stream, []))

    async def xpending(self, stream, grupo):
        self._vivo()
        return {"pending": len((self.r.grupos.get((stream, grupo)) or {"pel": {}})["pel"])}


# ═════════════════════════════════════════════════════════════════════════════
# O portal-worker (outro processo, outro contêiner: aqui, só o efeito dele no banco)
# ═════════════════════════════════════════════════════════════════════════════
class PortalWorkerDuble:
    def __init__(self, banco: BancoEmMemoria):
        self.banco = banco
        self._visao = banco.visao("portal-worker")

    def pegar(self) -> int:
        """Pega os jobs `queued` (como o `poll_loop`): → `running`."""
        n = 0
        for job in [j for j in self.banco.linhas("portal_jobs") if j.get("status") == "queued"]:
            self._visao.table("portal_jobs").update({
                "status": "running", "started_at": self.banco.relogio.iso(),
                "attempts": int(job.get("attempts") or 0) + 1}).eq("id", job["id"]).execute()
            n += 1
        return n

    def terminar(self, job_id: str, *, status: str = "done", evidence: Optional[dict] = None,
                 error: Optional[str] = None) -> None:
        job = next(j for j in self.banco.linhas("portal_jobs") if j["id"] == job_id)
        self._visao.table("portal_jobs").update({
            "status": status, "finished_at": self.banco.relogio.iso(), "error": error,
            "evidence": {**(job.get("evidence") or {}), **(evidence or {})}}).eq("id", job_id).execute()


# ═════════════════════════════════════════════════════════════════════════════
# O mundo e os processos
# ═════════════════════════════════════════════════════════════════════════════
class Processo:
    """Um processo do Work OS (um contêiner do smith-worker, ou a API): seus dois clientes."""

    def __init__(self, mundo: "Mundo", nome: str):
        self.mundo, self.nome = mundo, nome
        self.db = mundo.banco.visao(nome)
        self.redis = mundo.redis.visao(nome)
        self.worker: Any = None

    @property
    def morto(self) -> bool:
        return self.db.morto

    def morrer(self) -> None:
        self.db.morto = True
        self.redis.morto = True


class Mundo:
    def __init__(self, *, empresas: tuple = (), relogio: Optional[Relogio] = None):
        self.relogio = relogio or Relogio()
        self.banco = BancoEmMemoria(self.relogio)
        self.redis = RedisStreams(self.relogio)
        self.portal = PortalWorkerDuble(self.banco)
        for e in empresas:
            self.banco.semear("companies", {"id": e})

    def processo(self, nome: str) -> Processo:
        return Processo(self, nome)


_NADA = object()


@contextlib.contextmanager
def _clientes_do_processo(processo: Processo):
    """Durante o `iniciar()` REAL do worker, `get_supabase_client()` e `get_async_redis_client()`
    devolvem os clientes DESTE processo. Os módulos reais não são tocados: só a entrada em `sys.modules`."""
    db_mod = types.ModuleType("app.core.database")
    db_mod.get_supabase_client = lambda: processo.db

    async def _redis():
        return processo.redis

    redis_mod = types.ModuleType("app.core.redis")
    redis_mod.get_async_redis_client = _redis
    trocas = {"app.core.database": db_mod, "app.core.redis": redis_mod}
    antes = {n: sys.modules.get(n, _NADA) for n in trocas}
    sys.modules.update(trocas)
    try:
        yield
    finally:
        for n, m in antes.items():
            if m is _NADA:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = m


async def ligar_worker(processo: Processo, modulo_do_worker: Any) -> Any:
    """Um `SmithWorker` REAL, iniciado pelo `iniciar()` REAL, com os clientes deste processo."""
    w = modulo_do_worker.SmithWorker()
    with _clientes_do_processo(processo):
        await w.iniciar()
    processo.worker = w
    return w


async def uma_volta(worker: Any, laco: str) -> None:
    """Roda UMA volta de um laço REAL do worker (`_laco_orfaos`, `_laco_dispatcher`, …).

    O `_dormir` do worker é trocado: a 1ª chamada volta na hora, a 2ª encerra o laço. Laço que dorme
    antes do corpo (`_laco_orfaos`) roda o corpo uma vez; laço que dorme depois (`_laco_dispatcher`),
    duas — inofensivo: a segunda não tem o que publicar."""
    chamadas = {"n": 0}

    async def _dormir(_segundos: float) -> None:
        chamadas["n"] += 1
        if chamadas["n"] >= 2:
            raise FimDaVolta()
        await asyncio.sleep(0)

    worker._dormir = _dormir
    try:
        await getattr(worker, laco)()
    except FimDaVolta:
        pass
    finally:
        try:
            del worker._dormir
        except AttributeError:
            pass


async def consumir(worker: Any, processo: Processo, *, teto_s: float = 30.0) -> list:
    """Roda o `_laco_consumo` REAL até a fila ficar ociosa e nenhum run estar em voo.

    Devolve as exceções que mataram tarefas (ex.: `MorteDoProcesso`)."""
    mortes: list = []
    tarefa = asyncio.create_task(worker._laco_consumo())
    inicio = time.monotonic()
    marca = None
    try:
        while time.monotonic() - inicio < teto_s:
            await asyncio.sleep(0.003)
            em_voo = list(worker._em_execucao.values())
            if em_voo:
                res = await asyncio.gather(*em_voo, return_exceptions=True)
                mortes += [r for r in res if isinstance(r, BaseException)]
                marca = None
                continue
            if tarefa.done():
                break
            if marca is None:
                marca = processo.redis.ciclos_vazios
            elif processo.redis.ciclos_vazios >= marca + 2:
                break
        else:
            raise AssertionError(f"o laço de consumo não ficou ocioso em {teto_s}s")
    finally:
        worker.parar.set()
        try:
            await asyncio.wait_for(tarefa, timeout=5)
        except MorteDoProcesso as exc:
            mortes.append(exc)
        except (asyncio.TimeoutError, FimDaVolta):
            tarefa.cancel()
        worker.parar.clear()
    return mortes


async def ciclo(worker: Any, processo: Processo) -> list:
    """Um ciclo do worker: órfãos/despertador → dispatcher → consumo. Devolve as mortes."""
    if processo.morto:
        return []
    mortes: list = []
    for laco in ("_laco_orfaos", "_laco_dispatcher"):
        try:
            await uma_volta(worker, laco)
        except MorteDoProcesso as exc:
            mortes.append(exc)
            return mortes
    mortes += await consumir(worker, processo)
    return mortes


class MedidorDoLaco:
    """Um ticker de 100 ms no event loop: o maior atraso é quanto o laço ficou PRESO (G6)."""

    def __init__(self) -> None:
        self.maior_atraso_s = 0.0
        self._tarefa: Optional[asyncio.Task] = None

    async def _tic(self) -> None:
        laco = asyncio.get_running_loop()
        while True:
            t = laco.time()
            await asyncio.sleep(0.1)
            self.maior_atraso_s = max(self.maior_atraso_s, laco.time() - t - 0.1)

    async def __aenter__(self) -> "MedidorDoLaco":
        self._tarefa = asyncio.create_task(self._tic())
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, *_exc) -> None:
        if self._tarefa:
            self._tarefa.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tarefa
