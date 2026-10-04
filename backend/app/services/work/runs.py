"""Work Run Service — estado durável da execução. SPEC-055 §9, §12, §15, §16, §17 · SPEC-129-A §6.

Autoridade de estado: **Postgres**. Redis é transporte, LangGraph guarda o
estado cognitivo, MinIO guarda bytes. Nada aqui decide fora do banco.

Quatro garantias que este módulo entrega:

1. **Lease** — um run em execução tem dono, token e validade. Se o worker
   morrer, a lease vence e outro worker assume. Sem lease, um restart deixa
   trabalho preso em `running` para sempre.

2. **HITL executável** — aprovação vira estado (`waiting_approval`), com
   fingerprint do que foi mostrado ao humano. Se o conteúdo mudar depois do
   aceite, a aprovação é invalidada.

3. **Retomada** — o run guarda `current_step_key` e o step guarda
   `checkpoint_id`. A retomada parte do último ponto seguro, não do começo.

4. **A ESPERA DURÁVEL (SPEC-129-A)** — um trabalho DORME (`waiting_input` +
   `wake_at` + `wait_for`) sem worker e sem lease, ACORDA sozinho pelo relógio
   (`despertar_vencidos`, no laço de órfãos que já existe), sobrevive a reinício
   e nunca roda duas vezes: TODA escrita de status é um CAS — um UPDATE filtrado
   do PostgREST que devolve a linha ou nada — com `company_id` da linha e
   `runtime_kind='smith'`. Quem perde o CAS não escreve: segue.

🔴 `runtime_kind='smith'` em TODO CAS: só o trabalho que nasceu pela fila é do
Work OS. Os "sem fila" (`acionamento`, `sombra`, `proposta`, `portal` — ver o fim
deste arquivo) nunca têm o STATUS tocado pela lease, pelo despertador, pelo
re-despacho, pelos órfãos nem pelo Reprocessar. 📊 04/10: há 3 `claims.shadow`
`running` SEM lease — sem o filtro, o re-despacho as pegaria e o worker as
mataria como `workflow_desconhecido`.

⚠️ Este módulo só importa biblioteca padrão (o guarda `test_o_run_sem_fila.py`
o carrega pelo caminho, sem o pacote `app`). O registro de workflows chega como
PARÂMETRO (`workflows`), nunca por import.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
import socket
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Optional, Union

logger = logging.getLogger(__name__)

LEASE_DURACAO_SEGUNDOS = 120
HEARTBEAT_INTERVALO_SEGUNDOS = 30
ESTADOS_ATIVOS = ("running", "planning", "cancelling")
ESTADOS_TERMINAIS = ("completed", "failed", "cancelled", "expired")

# ---------------------------------------------------------------------------
# SPEC-129-A §6 — a espera durável
# ---------------------------------------------------------------------------
#: o único `runtime_kind` cujo STATUS o Work OS escreve (os "sem fila" ficam de fora)
RUNTIME_DA_FILA = "smith"
#: os estados em que um run DORME com relógio (`ck_work_runs_espera_tem_relogio`, `_02`)
ESTADOS_DE_ESPERA = ("waiting_input", "retry_scheduled")
#: de onde a lease pode ser tomada (`cancelling` e `waiting_*` NUNCA viram `running`)
ESTADOS_QUE_PEGAM_LEASE = ("queued", "running", "planning")
#: o que o Reprocessar aceita (`retry_scheduled` = antecipar a nova tentativa)
ESTADOS_QUE_SE_REPROCESSAM = ("failed", "cancelled", "paused", "retry_scheduled")
#: relógio "parado": run na fila (ou `running` sem lease) há mais que isto → re-despacho
PARADO_SEGUNDOS = 600
#: relógio "idade" (D-129A-5): padrão quando o workflow não declara `idade_maxima_s`
IDADE_MAXIMA_PADRAO_S = 2 * 3600
#: relógio "espera": o despertador expira o que passou de `wait_for.prazo` + isto
FOLGA_DO_PRAZO_S = 3600
#: o intervalo NORMAL entre despertares (≤ 200 s: três conferências cabem em 10 min)
ESPERA_PADRAO_S = 120
#: os códigos de erro que a espera durável grava (o ROLLBACK da `_01` usa OUTRO código)
CODIGO_EXPIRADO_PELA_IDADE = "expirado_pela_idade"
CODIGO_ESPERA_VENCIDA = "espera_vencida"
CODIGO_EFEITO_INCERTO = "efeito_incerto"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _iso_filtro(dt: datetime) -> str:
    """O instante dentro de um `or_(...)` do PostgREST: UTC com `Z`.

    ⚠️ Num `or_` o valor viaja DENTRO da expressão; o `+00:00` do `isoformat()`
    seria lido como espaço se alguém montasse a URL à mão. `Z` não tem esse risco.
    """
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _ler_ts(valor: Any) -> Optional[datetime]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def worker_id() -> str:
    """Identidade estável o suficiente para diagnosticar quem segurou a lease."""
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


class Esperando:
    """Sentinela: o handler DORMIU (ou esperou um humano). `_processar` NÃO conclui.

    📊 O defeito que ela fecha (SPEC-129-A §0, problema 2): `workflows.py`
    gravava `waiting_approval` e o worker, logo em seguida, concluía por cima —
    o run virava `completed` com o portal ainda trabalhando.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - diagnóstico
        return "ESPERANDO"


#: a instância única que um handler devolve (o `dormir` a devolve pronta)
ESPERANDO = Esperando()


class EfeitoIncerto(Exception):
    """Um passo de efeito EXTERNO foi interrompido no meio: pode ter acontecido.

    D-129A-4: não se repete. O worker grava `failed` com `error_code='efeito_incerto'`
    ("reconcilie antes"), e o Reprocessar recusa esse run (409) — repetir por conta
    própria é exatamente o que produz cobrança e mensagem em dobro.
    """


#: o que o parâmetro `workflows` aceita: {chave: handler | idade_s | None} ou só as chaves
Workflows = Union[Mapping, Iterable[str], None]


def _politica_do_workflow(workflows: Workflows, chave: Optional[str]) -> tuple[bool, int, Optional[Callable]]:
    """`(registrado, idade_maxima_s, ao_desistir)` de um workflow.

    O registro é o da SPEC-055/056 (`workflows.py`) — ele chega aqui como DADO:
      · `{chave: handler}` — `handler.idade_maxima_s` (D-129A-5) e `handler.ao_desistir`
        (`ao_desistir(db, run, motivo)`: o que o workflow faz quando o Work OS desiste
        dele — a ponte da cobrança grava o aviso legível e fecha o `routine_runs`)
      · `{chave: segundos}` ou um iterável de chaves (idade padrão, sem gancho)
    """
    if not chave or workflows is None:
        return False, IDADE_MAXIMA_PADRAO_S, None
    if isinstance(workflows, Mapping):
        if chave not in workflows:
            return False, IDADE_MAXIMA_PADRAO_S, None
        valor = workflows.get(chave)
        if isinstance(valor, bool):
            return True, IDADE_MAXIMA_PADRAO_S, None
        if isinstance(valor, (int, float)):
            return True, int(valor) if valor > 0 else IDADE_MAXIMA_PADRAO_S, None
        idade = getattr(valor, "idade_maxima_s", None)
        gancho = getattr(valor, "ao_desistir", None)
        idade = int(idade) if isinstance(idade, (int, float)) and not isinstance(idade, bool) and idade > 0 \
            else IDADE_MAXIMA_PADRAO_S
        return True, idade, gancho if callable(gancho) else None
    try:
        return chave in set(workflows), IDADE_MAXIMA_PADRAO_S, None
    except TypeError:
        return False, IDADE_MAXIMA_PADRAO_S, None


def _so_escalares_curtos(d: Any) -> dict:
    """`wait_for` guarda ids, estados e números — nunca texto livre, nunca objeto aninhado."""
    saida: dict = {}
    for k, v in (d or {}).items() if isinstance(d, dict) else ():
        if v is None or isinstance(v, (bool, int, float)):
            saida[str(k)] = v
        elif isinstance(v, str) and len(v) <= 120:
            saida[str(k)] = v
    return saida


class WorkRunService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def criar(
        self,
        *,
        company_id: str,
        source_type: str,
        outcome_type: str,
        outcome_title: str,
        workflow_key: str,
        idempotency_key: str,
        input_payload: Optional[dict] = None,
        requester_user_id: Optional[str] = None,
        source_id: Optional[str] = None,
        priority: int = 50,
        risk_level: str = "low",
        correlation_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        cost_budget_brl: Optional[float] = None,
    ) -> dict:
        """Cria o run e a linha de outbox na MESMA transação (RPC).

        Chamar duas vezes com a mesma `idempotency_key` devolve o run
        existente com `reused=True` — não cria duplicata.
        """
        res = self.db.rpc("work_run_create", {
            "p_company_id": company_id,
            "p_source_type": source_type,
            "p_outcome_type": outcome_type,
            "p_outcome_title": outcome_title,
            "p_workflow_key": workflow_key,
            "p_idempotency_key": idempotency_key,
            "p_input_payload": input_payload or {},
            "p_input_fingerprint": None,
            "p_requester_user_id": requester_user_id,
            "p_source_id": source_id,
            "p_priority": priority,
            "p_risk_level": risk_level,
            "p_correlation_id": correlation_id,
            "p_parent_run_id": parent_run_id,
            "p_cost_budget_brl": cost_budget_brl,
            "p_workflow_version": "1.0.0",
        }).execute()

        linha = (res.data or [{}])[0] if isinstance(res.data, list) else (res.data or {})
        if linha.get("reused"):
            logger.info("[WorkRun] pedido idempotente reaproveitou run %s", linha.get("run_id"))
        return linha

    # ------------------------------------------------------------------
    # Leituras de apoio (sempre com `runtime_kind='smith'`)
    # ------------------------------------------------------------------

    def _linha_da_fila(self, run_id: str, company_id: Optional[str], colunas: str) -> Optional[dict]:
        """A linha de um run DA FILA. `None` se não existe, não é `smith` ou é de outra corretora."""
        try:
            q = (self.db.table("work_runs").select(colunas)
                 .eq("id", run_id).eq("runtime_kind", RUNTIME_DA_FILA))
            if company_id:
                q = q.eq("company_id", str(company_id))
            res = q.limit(1).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] falha ao ler run %s: %s", run_id, type(exc).__name__)
            return None
        dados = getattr(res, "data", None) if res is not None else None
        if isinstance(dados, list):
            return dados[0] if dados else None
        return dados or None

    def _empresa_do_run(self, run_id: str) -> Optional[str]:
        linha = self._linha_da_fila(run_id, None, "company_id")
        return str(linha["company_id"]) if linha and linha.get("company_id") else None

    def _enfileirar(self, run: dict, tipo: str, extra: Optional[dict] = None) -> bool:
        """A linha do outbox — SEMPRE depois do CAS. Morrer entre os dois: o re-despacho cura."""
        try:
            self.db.table("work_queue_outbox").insert({
                "company_id": run["company_id"],
                "work_run_id": run["id"],
                "event_kind": tipo,
                "payload_minimal": {"run_id": run["id"], "company_id": run["company_id"],
                                    "workflow_key": run.get("workflow_key"), **(extra or {})},
            }).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] outbox '%s' de %s não gravado: %s", tipo, run.get("id"),
                         type(exc).__name__)
            return False

    # ------------------------------------------------------------------
    # Lease
    # ------------------------------------------------------------------

    def adquirir_lease(self, run_id: str, owner: str, company_id: Optional[str] = None) -> Optional[dict]:
        """Toma a lease do run. `None` quando outro worker já a tem (ou o run não pode rodar).

        🔴 CAS (SPEC-129-A §6): `queued`, ou `running`/`planning` com a lease nula ou
        vencida → `running`. Um UPDATE filtrado do PostgREST: dois workers
        competindo, UM recebe a linha e o outro recebe nada — e segue.
        `cancelling`, `waiting_*`, `retry_scheduled` e terminais NUNCA viram `running`.

        📊 Antes: lia e gravava sem condição (`.eq("id")` só) — dois processos
        assumiam o mesmo run, e um `waiting_approval` virava `running`.
        """
        linha = self._linha_da_fila(run_id, company_id, "id, company_id, status, started_at")
        if not linha or linha.get("status") not in ESTADOS_QUE_PEGAM_LEASE:
            return None

        agora = _agora()
        token = str(uuid.uuid4())
        expira = agora + timedelta(seconds=LEASE_DURACAO_SEGUNDOS)
        empresa = str(linha["company_id"])
        try:
            upd = (
                self.db.table("work_runs")
                .update({
                    "lease_owner": owner,
                    "lease_token": token,
                    "lease_expires_at": _iso(expira),
                    "heartbeat_at": _iso(agora),
                    "status": "running",
                    "started_at": linha.get("started_at") or _iso(agora),
                })
                .eq("id", run_id)
                .eq("company_id", empresa)
                .eq("runtime_kind", RUNTIME_DA_FILA)
                .in_("status", list(ESTADOS_QUE_PEGAM_LEASE))
                .or_(f"lease_expires_at.is.null,lease_expires_at.lt.{_iso_filtro(agora)}")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] falha ao adquirir lease de %s: %s", run_id, type(exc).__name__)
            return None
        if not (upd and upd.data):
            return None  # outro worker ganhou: segue

        self.evento(empresa, run_id, "run.leased",
                    f"Trabalho assumido pelo processador {owner}", actor_type="worker", actor_id=owner)
        return {"run_id": run_id, "company_id": empresa, "lease_token": token,
                "expires_at": _iso(expira)}

    def heartbeat(self, run_id: str, lease_token: str) -> bool:
        """Renova a lease. `False` quando o token não é mais o dono."""
        expira = _agora() + timedelta(seconds=LEASE_DURACAO_SEGUNDOS)
        try:
            res = (
                self.db.table("work_runs")
                .update({"heartbeat_at": _iso(_agora()), "lease_expires_at": _iso(expira)})
                .eq("id", run_id)
                .eq("runtime_kind", RUNTIME_DA_FILA)
                .eq("lease_token", lease_token)
                .execute()
            )
            return bool(res.data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] heartbeat falhou para %s: %s", run_id, type(exc).__name__)
            return False

    def liberar_lease(self, run_id: str, lease_token: str) -> None:
        try:
            self.db.table("work_runs").update({
                "lease_owner": None, "lease_token": None, "lease_expires_at": None,
            }).eq("id", run_id).eq("runtime_kind", RUNTIME_DA_FILA).eq("lease_token", lease_token).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] falha ao liberar lease: %s", type(exc).__name__)

    def recuperar_orfaos(self, limite: int = 50) -> list[dict]:
        """Runs ativos com lease vencida — worker morreu no meio.

        **Não reexecuta nada aqui.** Devolve para a fila (CAS + outbox); a idempotência
        dos passos é que impede repetição. Recuperar é diferente de repetir.
        `cancelling` órfão não volta para a fila: o cancelamento pedido vence → `cancelled`.
        """
        agora = _agora()
        try:
            res = (
                self.db.table("work_runs")
                .select("id, company_id, status, lease_owner, workflow_key, current_step_key")
                .eq("runtime_kind", RUNTIME_DA_FILA)
                .in_("status", list(ESTADOS_ATIVOS))
                .lt("lease_expires_at", _iso(agora))
                .limit(limite)
                .execute()
            )
            orfaos = res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] falha ao varrer órfãos: %s", type(exc).__name__)
            return []

        recuperados: list[dict] = []
        for run in orfaos:
            try:
                vencida = (lambda q, _a=_iso(agora): q.lt("lease_expires_at", _a))
                if run.get("status") == "cancelling":
                    if self._transicionar(run["id"], "cancelled", {
                        "cancelled_at": _iso(agora), "finished_at": _iso(agora),
                        "lease_owner": None, "lease_token": None, "lease_expires_at": None,
                    }, de="cancelling", company_id=run["company_id"], filtro=vencida):
                        self.evento(run["company_id"], run["id"], "run.cancelled",
                                    "Trabalho cancelado: o processador parou de responder depois do pedido "
                                    "de cancelamento. Etapas já concluídas foram preservadas.")
                    continue

                if not self._transicionar(run["id"], "queued", {
                    "lease_owner": None, "lease_token": None, "lease_expires_at": None,
                    "queued_at": _iso(agora),
                }, de=("running", "planning"), company_id=run["company_id"], filtro=vencida):
                    continue
                self._enfileirar(run, "run.recovered", {"retomar_de": run.get("current_step_key")})
                self.evento(run["company_id"], run["id"], "worker.recovered",
                            "Trabalho recuperado: o processador anterior parou de responder. "
                            "Retomando do último ponto seguro.", actor_type="system")
                logger.warning("[WorkRun] run %s recuperado (dono anterior: %s)",
                               run["id"], run.get("lease_owner"))
                recuperados.append(run)
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] falha ao recuperar %s: %s", run["id"], type(exc).__name__)

        return recuperados

    # ------------------------------------------------------------------
    # A espera durável — SPEC-129-A §6
    # ------------------------------------------------------------------

    def dormir(self, run_id: str, *, lease_token: str, acordar_em_s: Optional[float] = None,
               wait_for: Optional[dict] = None, company_id: Optional[str] = None) -> Esperando:
        """O handler DORME: CAS `running`(meu token) → `waiting_input` + `wake_at` + `wait_for`.

        Dormindo, o run NÃO tem dono (a lease é limpa): nenhum worker o segura,
        nenhum reinício o perde. Quem o acorda é o relógio (`despertar_vencidos`).

        `wait_for` (`{"tipo","ref","prazo"|"prazo_s","passo",…}`, só escalares curtos):
          · mesmo `ref` da espera anterior → `prazo` e `acordou` são PRESERVADOS
            (o prazo é absoluto, gravado no 1º dormir — §6, relógio "espera")
          · `prazo_s` vira `prazo` absoluto no 1º dormir
          · `intervalo_s` = o intervalo deste sono; `acordou` só o despertador incrementa
        O `wake_at` nunca passa do `prazo` — o handler precisa acordar a tempo de falhar.

        Devolve SEMPRE `ESPERANDO`: se o CAS perdeu (outro dono, cancelado), o run
        não é mais deste handler — e quem não é dono não conclui nada.
        """
        empresa = str(company_id) if company_id else self._empresa_do_run(run_id)
        if not empresa:
            logger.error("[WorkRun] dormir: run %s não é da fila (ou não existe)", run_id)
            return ESPERANDO
        agora = _agora()
        segundos = max(1, int(acordar_em_s if acordar_em_s is not None else ESPERA_PADRAO_S))

        anterior = (self._linha_da_fila(run_id, empresa, "wait_for") or {}).get("wait_for")
        anterior = anterior if isinstance(anterior, dict) else {}
        pedido = dict(wait_for or {})
        prazo_s = pedido.pop("prazo_s", None)
        novo = _so_escalares_curtos(pedido)
        mesma_espera = bool(anterior) and anterior.get("ref") == novo.get("ref") \
            and anterior.get("tipo") == novo.get("tipo")
        if mesma_espera:
            if anterior.get("prazo"):
                novo["prazo"] = anterior["prazo"]
            novo["acordou"] = int(anterior.get("acordou") or 0)
        else:
            novo["acordou"] = 0
            if not novo.get("prazo") and isinstance(prazo_s, (int, float)) and prazo_s > 0:
                novo["prazo"] = _iso(agora + timedelta(seconds=float(prazo_s)))
        novo["intervalo_s"] = segundos

        acorda = agora + timedelta(seconds=segundos)
        prazo = _ler_ts(novo.get("prazo"))
        if prazo is not None and acorda > prazo:
            acorda = max(prazo, agora + timedelta(seconds=1))

        ok = self._transicionar(run_id, "waiting_input", {
            "wake_at": _iso(acorda),
            "wait_for": novo,
            "lease_owner": None, "lease_token": None, "lease_expires_at": None,
        }, de="running", lease_token=lease_token, company_id=empresa)
        if ok:
            minutos = max(1, round(segundos / 60))
            self.evento(empresa, run_id, "run.waiting",
                        f"Aguardando ({novo.get('tipo') or 'resposta'}): confiro de novo em "
                        f"{minutos} min.",
                        severity="info" if not mesma_espera else "debug",
                        payload={"ref": novo.get("ref"), "acordou": novo.get("acordou"),
                                 "intervalo_s": segundos})
        else:
            logger.warning("[WorkRun] dormir: run %s não era mais deste dono (CAS perdido)", run_id)
        return ESPERANDO

    def despertar_vencidos(self, workflows: Workflows, limite: int = 50) -> list[dict]:
        """O DESPERTADOR: `waiting_input`/`retry_scheduled` com `wake_at ≤ agora` → `queued` + outbox `run.woken`.

        Só `smith`, só workflow REGISTRADO (o resto fica como está). Antes de acordar:
          · espera com `wait_for.prazo` vencido há mais de 1 h → `expired` (`espera_vencida`)
          · sem `wait_for` e idade (`agora − requested_at`) acima do limite do workflow
            → `expired` (`expirado_pela_idade`). Run com `wait_for` NUNCA expira pela idade.
        `wait_for.acordou` += 1 a cada despertar de `waiting_input` (e não é apagado ao concluir).
        """
        agora = _agora()
        try:
            res = (
                self.db.table("work_runs")
                .select("id, company_id, status, workflow_key, wake_at, wait_for, requested_at")
                .eq("runtime_kind", RUNTIME_DA_FILA)
                .in_("status", list(ESTADOS_DE_ESPERA))
                .lte("wake_at", _iso(agora))
                .order("wake_at")
                .limit(limite)
                .execute()
            )
            vencidos = res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] despertador: falha ao ler: %s", type(exc).__name__)
            return []

        acordados: list[dict] = []
        for run in vencidos:
            try:
                registrado, idade_max, gancho = _politica_do_workflow(workflows, run.get("workflow_key"))
                if not registrado:
                    continue
                if self._expirar_se_passou(run, idade_max, gancho, agora):
                    continue
                espera = run.get("wait_for") if isinstance(run.get("wait_for"), dict) else None
                campos: dict = {"queued_at": _iso(agora), "wake_at": None}
                if espera is not None and run.get("status") == "waiting_input":
                    campos["wait_for"] = {**espera, "acordou": int(espera.get("acordou") or 0) + 1}
                if not self._transicionar(run["id"], "queued", campos, de=run["status"],
                                          company_id=run["company_id"],
                                          filtro=lambda q, _a=_iso(agora): q.lte("wake_at", _a)):
                    continue
                self._enfileirar(run, "run.woken",
                                 {"acordou": (campos.get("wait_for") or {}).get("acordou")})
                self.evento(run["company_id"], run["id"], "run.woken",
                            "Hora de conferir de novo: o trabalho voltou para a fila.",
                            severity="debug")
                acordados.append(run)
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] despertador: falha em %s: %s", run.get("id"), type(exc).__name__)
        return acordados

    def redespachar_parados(self, workflows: Workflows, limite: int = 50) -> list[dict]:
        """O RE-DESPACHO: o Postgres cura a mensagem que o Redis perdeu.

        📊 04/10: 21 runs `queued` com outbox `published` e nenhum `run.leased` — a
        mensagem sumiu entre a fila e a lease. Relógio "parado" (> 10 min):
          · `queued` sem lease, por `queued_at` (o despertar e a recuperação o regravam)
          · `running` SEM lease, por `coalesce(heartbeat_at, started_at)`
        → nova linha de outbox `run.redriven` (CAS regrava o relógio: dois varredores, um envia).
        Antes: idade acima do limite e sem `wait_for` → `expired` (`expirado_pela_idade`).
        Só `smith`, só workflow registrado. Outbox em dobro é inofensivo: uma lease ganha.
        """
        agora = _agora()
        corte = agora - timedelta(seconds=PARADO_SEGUNDOS)
        c = _iso_filtro(corte)
        colunas = "id, company_id, status, workflow_key, wait_for, requested_at, queued_at"
        parado_na_fila = f"queued_at.lt.{c},and(queued_at.is.null,requested_at.lt.{c})"
        parado_rodando = (f"heartbeat_at.lt.{c},and(heartbeat_at.is.null,started_at.lt.{c}),"
                          f"and(heartbeat_at.is.null,started_at.is.null,requested_at.lt.{c})")
        candidatos: list[dict] = []
        for status, expressao in (("queued", parado_na_fila), ("running", parado_rodando)):
            try:
                res = (
                    self.db.table("work_runs").select(colunas)
                    .eq("runtime_kind", RUNTIME_DA_FILA)
                    .eq("status", status)
                    .is_("lease_owner", "null")
                    .or_(expressao)
                    .limit(limite)
                    .execute()
                )
                candidatos += [(r, expressao) for r in (res.data or [])]
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] re-despacho: falha ao ler %s: %s", status, type(exc).__name__)

        enviados: list[dict] = []
        for run, expressao in candidatos:
            try:
                registrado, idade_max, gancho = _politica_do_workflow(workflows, run.get("workflow_key"))
                if not registrado:
                    continue
                if run.get("status") == "queued" and self._expirar_se_passou(run, idade_max, gancho, agora):
                    continue

                def ainda_parado(q, _e=expressao):
                    return q.is_("lease_owner", "null").or_(_e)

                if not self._transicionar(run["id"], "queued", {"queued_at": _iso(agora)},
                                          de=run["status"], company_id=run["company_id"],
                                          filtro=ainda_parado):
                    continue
                self._enfileirar(run, "run.redriven")
                self.evento(run["company_id"], run["id"], "run.redriven",
                            "O trabalho estava parado na fila há mais de 10 minutos e foi reenviado.",
                            severity="warning")
                enviados.append(run)
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] re-despacho: falha em %s: %s", run.get("id"), type(exc).__name__)
        return enviados

    def _expirar_se_passou(self, run: dict, idade_max: int, gancho: Optional[Callable],
                           agora: datetime) -> bool:
        """Os dois relógios que encerram sem rodar. `True` = expirou (ou tentou: não acorde)."""
        espera = run.get("wait_for") if isinstance(run.get("wait_for"), dict) else None
        if espera:
            prazo = _ler_ts(espera.get("prazo"))
            if prazo is None or agora <= prazo + timedelta(seconds=FOLGA_DO_PRAZO_S):
                return False
            codigo = CODIGO_ESPERA_VENCIDA
            mensagem = ("A espera passou do prazo sem resposta (prazo "
                        f"{prazo.strftime('%d/%m %H:%M')} UTC). O trabalho foi encerrado sem repetir nada.")
        else:
            pedido = _ler_ts(run.get("requested_at"))
            if pedido is None or (agora - pedido).total_seconds() <= idade_max:
                return False
            codigo = CODIGO_EXPIRADO_PELA_IDADE
            horas = idade_max / 3600
            mensagem = (f"Expirou sem rodar: passou de {horas:g} h desde o pedido. "
                        "A próxima janela faz o trabalho; nada foi repetido.")
        if self._transicionar(run["id"], "expired", {
            "finished_at": _iso(agora), "error_code": codigo, "error_message": mensagem,
            "wake_at": None,
        }, de=run["status"], company_id=run["company_id"],
                filtro=lambda q: q.is_("lease_owner", "null")):
            self.evento(run["company_id"], run["id"], "run.expired", mensagem, severity="warning",
                        payload={"motivo": codigo})
            self._chamar_gancho(gancho, run, mensagem)
        return True

    def _chamar_gancho(self, gancho: Optional[Callable], run: dict, motivo: str) -> None:
        """`ao_desistir(db, run, motivo)` do workflow. Nunca derruba o laço."""
        if not gancho:
            return
        try:
            gancho(self.db, dict(run), motivo)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] gancho ao_desistir de %s falhou: %s", run.get("id"),
                           type(exc).__name__)

    def despertar_por_aprovacao(self, run_id: str, company_id: str, decisao: str) -> bool:
        """A decisão humana acorda o run NA HORA (D-129A-2), pelo mesmo caminho do despertador.

        `approved`/`approved_with_edit` → `queued` + outbox `run.woken` ·
        `rejected` → `cancelled` · `expired` → `expired`. Só de `waiting_approval`.
        """
        agora = _agora()
        if decisao in ("approved", "approved_with_edit"):
            linha = self._linha_da_fila(run_id, company_id, "id, company_id, workflow_key")
            if not linha:
                return False
            ok = self._transicionar(run_id, "queued", {"queued_at": _iso(agora)},
                                    de="waiting_approval", company_id=company_id)
            if ok:
                self._enfileirar(linha, "run.woken", {"motivo": "aprovacao"})
                self.evento(company_id, run_id, "run.woken",
                            "Aprovado: o trabalho voltou para a fila.", actor_type="user")
            return ok
        if decisao == "rejected":
            ok = self._transicionar(run_id, "cancelled", {
                "cancelled_at": _iso(agora), "finished_at": _iso(agora),
            }, de="waiting_approval", company_id=company_id)
            if ok:
                self.evento(company_id, run_id, "run.cancelled",
                            "Recusado: o trabalho foi encerrado sem executar a ação.", actor_type="user")
            return ok
        if decisao == "expired":
            mensagem = "A aprovação expirou sem decisão: o trabalho foi encerrado sem executar a ação."
            ok = self._transicionar(run_id, "expired", {
                "finished_at": _iso(agora), "error_code": "aprovacao_expirada", "error_message": mensagem,
            }, de="waiting_approval", company_id=company_id)
            if ok:
                self.evento(company_id, run_id, "run.expired", mensagem, severity="warning")
            return ok
        raise ValueError(f"decisão inválida: {decisao}")

    def reprocessar(self, run_id: str, company_id: str, ator: Optional[str] = None, *,
                    workflows: Workflows = None) -> dict:
        """Recoloca na fila o que PAROU — CAS + outbox `run.retried` (o run RODA de novo).

        📊 Antes (`api/work_runs.py:213`): só mudava para `queued`, sem outbox → preso.
        Devolve `{"ok": True, "status": "queued", "mensagem"}` ou
        `{"ok": False, "http": 404|409, "codigo", "mensagem"}` (mensagem em português, para a tela):
          · 404 `nao_encontrado` — não existe NESTA corretora
          · 409 `sem_fila` — não roda pela fila (acionamento, sombra, proposta, portal)
          · 409 `sem_executor` — nenhum workflow registrado sabe rodá-lo
          · 409 `efeito_incerto` — um efeito externo pode ter acontecido: reconcilie antes
          · 409 `estado` — só `failed`, `cancelled`, `paused`, `retry_scheduled` (este, antecipa)
        `workflows=None` → o registro de `workflows.py` (import tardio: este módulo é stdlib).
        """
        try:
            res = (self.db.table("work_runs")
                   .select("id, company_id, status, runtime_kind, workflow_key, error_code")
                   .eq("id", run_id).eq("company_id", str(company_id)).limit(1).execute())
            dados = res.data if res is not None else None
            linha = (dados[0] if dados else None) if isinstance(dados, list) else dados
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] reprocessar: falha ao ler %s: %s", run_id, type(exc).__name__)
            return {"ok": False, "http": 500, "codigo": "leitura",
                    "mensagem": "Não consegui ler este trabalho agora. Tente de novo em instantes."}
        if not linha:
            return {"ok": False, "http": 404, "codigo": "nao_encontrado",
                    "mensagem": "Trabalho não encontrado."}
        if linha.get("runtime_kind") != RUNTIME_DA_FILA:
            return {"ok": False, "http": 409, "codigo": "sem_fila",
                    "mensagem": ("Este trabalho não roda pela fila: ele é acompanhado pela conversa ou "
                                 "pelo portal. Não dá para reprocessá-lo daqui.")}
        if workflows is None:
            try:
                from app.services.work.workflows import resolver_workflow, workflows_registrados

                workflows = {k: resolver_workflow(k) for k in workflows_registrados()}
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] reprocessar: registro indisponível: %s", type(exc).__name__)
                workflows = {}
        registrado, _idade, _gancho = _politica_do_workflow(workflows, linha.get("workflow_key"))
        if not registrado:
            return {"ok": False, "http": 409, "codigo": "sem_executor",
                    "mensagem": (f"Nenhum executor sabe rodar este tipo de trabalho "
                                 f"({linha.get('workflow_key')}). Reprocessar não adiantaria.")}
        if linha.get("error_code") == CODIGO_EFEITO_INCERTO:
            return {"ok": False, "http": 409, "codigo": CODIGO_EFEITO_INCERTO,
                    "mensagem": ("Uma etapa com efeito externo foi interrompida no meio e PODE ter "
                                 "acontecido (mensagem, cobrança ou pedido no portal). Confira e "
                                 "reconcilie antes: reprocessar poderia fazer duas vezes.")}
        status = str(linha.get("status") or "")
        if status not in ESTADOS_QUE_SE_REPROCESSAM:
            return {"ok": False, "http": 409, "codigo": "estado",
                    "mensagem": (f"Este trabalho está '{status}' — só dá para reprocessar o que já "
                                 "parou. Cancele antes, se for o caso.")}

        agora = _agora()
        ok = self._transicionar(run_id, "queued", {
            "queued_at": _iso(agora), "next_attempt_at": _iso(agora),
            "error_code": None, "error_message": None, "finished_at": None,
            "lease_owner": None, "lease_token": None, "lease_expires_at": None,
            "cancel_requested_at": None, "cancelled_at": None,
            "wake_at": None, "wait_for": None,
        }, de=status, company_id=str(company_id))
        if not ok:
            return {"ok": False, "http": 409, "codigo": "concorrencia",
                    "mensagem": "O trabalho mudou de estado agora mesmo. Atualize a tela e tente de novo."}
        self._enfileirar(linha, "run.retried")
        self.evento(str(company_id), run_id, "run.retried",
                    "Trabalho recolocado na fila por um operador", actor_type="user", actor_id=ator)
        return {"ok": True, "status": "queued",
                "mensagem": "Trabalho recolocado na fila. As etapas já concluídas são preservadas."}

    # ------------------------------------------------------------------
    # Transições
    # ------------------------------------------------------------------

    def marcar_progresso(self, run_id: str, company_id: str, step_key: str, percent: int) -> None:
        try:
            self.db.table("work_runs").update({
                "current_step_key": step_key,
                "progress_percent": max(0, min(100, int(percent))),
            }).eq("id", run_id).eq("company_id", str(company_id)).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] progresso não gravado: %s", type(exc).__name__)

    def concluir(self, run_id: str, company_id: str, resumo: str, resultado: Optional[dict] = None,
                 *, lease_token: Optional[str] = None) -> bool:
        """`running`(meu token) → `completed`. O `run.succeeded` só sai se o CAS ganhou.

        ⚠️ `wait_for` NÃO é apagado: ele é a história da espera (quantas vezes acordou).
        Sem `lease_token`: o caminho dos "sem fila", que fecham o PRÓPRIO run (ver
        `_fechar_sem_fila`). O worker SEMPRE passa o token.
        """
        campos = {
            "result_summary": resumo,
            "result_payload": resultado or {},
            "progress_percent": 100,
            "finished_at": _iso(_agora()),
            "lease_owner": None, "lease_token": None, "lease_expires_at": None,
        }
        if lease_token is None:
            ok = self._fechar_sem_fila(run_id, company_id, "completed", campos)
        else:
            campos["wake_at"] = None
            ok = self._transicionar(run_id, "completed", campos, de="running",
                                    lease_token=lease_token, company_id=company_id)
        if ok:
            self.evento(company_id, run_id, "run.succeeded", resumo or "Trabalho concluído")
        return ok

    def falhar(self, run_id: str, company_id: str, codigo: str, mensagem_humana: str,
               retryable: bool = False, proxima_tentativa_em: Optional[int] = None,
               *, lease_token: Optional[str] = None) -> bool:
        """`running`(meu token) → `failed`, ou → `retry_scheduled` com `wake_at` (o despertador o relê).

        📊 Antes: `retry_scheduled` gravava só `next_attempt_at`, que NINGUÉM relia —
        "tentar de novo" nunca voltava (SPEC-129-A §0, problema 1).
        """
        agora = _agora()
        sem_lease = {"lease_owner": None, "lease_token": None, "lease_expires_at": None}
        if retryable and proxima_tentativa_em:
            volta = agora + timedelta(seconds=int(proxima_tentativa_em))
            campos = {"error_code": codigo, "error_message": mensagem_humana,
                      "next_attempt_at": _iso(volta), **sem_lease}
            if lease_token is None:
                ok = self._fechar_sem_fila(run_id, company_id, "retry_scheduled", campos)
            else:
                campos["wake_at"] = _iso(volta)
                ok = self._transicionar(run_id, "retry_scheduled", campos, de=("running", "cancelling"),
                                        lease_token=lease_token, company_id=company_id)
            if ok:
                self.evento(company_id, run_id, "step.retry_scheduled",
                            f"Nova tentativa agendada: {mensagem_humana}")
            return ok

        campos = {"error_code": codigo, "error_message": mensagem_humana,
                  "finished_at": _iso(agora), **sem_lease}
        if lease_token is None:
            ok = self._fechar_sem_fila(run_id, company_id, "failed", campos)
        else:
            campos["wake_at"] = None
            ok = self._transicionar(run_id, "failed", campos, de=("running", "cancelling"),
                                    lease_token=lease_token, company_id=company_id)
        if ok:
            self.evento(company_id, run_id, "run.failed", mensagem_humana, severity="error")
        return ok

    def _fechar_sem_fila(self, run_id: str, company_id: str, novo_status: str, campos: dict) -> bool:
        """O dono de um run "sem fila" (o portal da SPEC-EXTRA-001.10, `portal_tool.fechar_work_run`)
        fecha o PRÓPRIO run — comportamento de hoje, agora com `company_id` (CLAUDE.md §7).

        ⚠️ Não é CAS do Work OS: o run "sem fila" não tem lease nem fila; quem o
        leva é o seu dono, mensagem por mensagem. Um run `smith` NÃO se fecha por
        aqui: o worker sempre passa o `lease_token`.
        """
        try:
            (self.db.table("work_runs").update({**campos, "status": novo_status})
             .eq("id", run_id).eq("company_id", str(company_id)).execute())
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] transição para %s falhou: %s", novo_status, type(exc).__name__)
            return False

    def solicitar_cancelamento(self, run_id: str, company_id: str, ator: Optional[str] = None) -> Optional[str]:
        """Cancelar. Devolve o status que ficou (`cancelled` · `cancelling`) ou `None`.

        · DORMINDO ou na fila (`waiting_*`, `retry_scheduled`, `queued`, sem lease):
          `cancelled` NA HORA — não há dono para avisar; o despertador não o reabre.
        · RODANDO: pedido cooperativo (`cancelling`); o worker observa entre etapas.
          Ação externa já confirmada **não** é desfeita — SPEC-053 §10.7.
        · "sem fila": o comportamento de hoje (`cancelling`), só com o `company_id`.
        """
        agora = _agora()
        try:
            res = (self.db.table("work_runs").select("id, status, runtime_kind")
                   .eq("id", run_id).eq("company_id", str(company_id)).limit(1).execute())
            dados = res.data if res is not None else None
            linha = (dados[0] if dados else None) if isinstance(dados, list) else dados
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] cancelar: falha ao ler %s: %s", run_id, type(exc).__name__)
            return None
        if not linha:
            return None

        if linha.get("runtime_kind") != RUNTIME_DA_FILA:
            try:
                (self.db.table("work_runs")
                 .update({"status": "cancelling", "cancel_requested_at": _iso(agora)})
                 .eq("id", run_id).eq("company_id", str(company_id))
                 .eq("runtime_kind", str(linha.get("runtime_kind"))).execute())
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] transição para cancelling falhou: %s", type(exc).__name__)
                return None
            self.evento(company_id, run_id, "run.cancel_requested",
                        "Cancelamento solicitado. Etapas já concluídas não são desfeitas.",
                        actor_type="user", actor_id=ator)
            return "cancelling"

        if self._transicionar(run_id, "cancelled", {
            "cancel_requested_at": _iso(agora), "cancelled_at": _iso(agora), "finished_at": _iso(agora),
            "wake_at": None,
        }, de=("queued",) + ESTADOS_DE_ESPERA + ("waiting_approval",), company_id=company_id,
                filtro=lambda q: q.is_("lease_owner", "null")):
            self.evento(company_id, run_id, "run.cancelled",
                        "Trabalho cancelado. Etapas já concluídas foram preservadas.",
                        actor_type="user", actor_id=ator)
            return "cancelled"

        if self._transicionar(run_id, "cancelling", {"cancel_requested_at": _iso(agora)},
                              de=("running", "planning"), company_id=company_id):
            self.evento(company_id, run_id, "run.cancel_requested",
                        "Cancelamento solicitado. Etapas já concluídas não são desfeitas.",
                        actor_type="user", actor_id=ator)
            return "cancelling"
        return None

    def cancelamento_pedido(self, run_id: str) -> bool:
        try:
            res = (self.db.table("work_runs").select("cancel_requested_at, status")
                   .eq("id", run_id).maybe_single().execute())
            d = (res.data if res is not None else None) or {}
            return bool(d.get("cancel_requested_at")) or d.get("status") == "cancelling"
        except Exception:  # noqa: BLE001
            return False

    def _transicionar(self, run_id: str, novo_status: str, campos: dict, *,
                      de: Union[str, Iterable[str]], lease_token: Optional[str] = None,
                      company_id: Optional[str] = None,
                      filtro: Optional[Callable[[Any], Any]] = None) -> bool:
        """🔴 O CAS (SPEC-129-A §6, D-129A-3). `True` = a linha mudou; `False` = perdeu (ou falhou).

        UPDATE filtrado do PostgREST, que devolve a linha ou nada:
            id · company_id DA LINHA · runtime_kind='smith' · status ∈ `de`
            [· lease_token = o meu] [· `filtro` extra: relógios, lease nula]
        Perdeu → evento `run.cas_perdido` e NADA é escrito. 📊 Antes: `.eq("id")`
        sozinho — o worker concluía por cima de `waiting_approval`, e o erro do banco
        era engolido em silêncio.
        """
        empresa = str(company_id) if company_id else self._empresa_do_run(run_id)
        if not empresa:
            logger.error("[WorkRun] transição para %s recusada: run %s não é da fila", novo_status, run_id)
            return False
        estados = [de] if isinstance(de, str) else list(de)
        patch = {**campos, "status": novo_status}
        try:
            q = (self.db.table("work_runs").update(patch)
                 .eq("id", run_id)
                 .eq("company_id", empresa)
                 .eq("runtime_kind", RUNTIME_DA_FILA))
            q = q.eq("status", estados[0]) if len(estados) == 1 else q.in_("status", estados)
            if lease_token is not None:
                q = q.eq("lease_token", lease_token)
            if filtro is not None:
                q = filtro(q)
            res = q.execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] transição %s → %s falhou: %s", "|".join(estados), novo_status,
                         type(exc).__name__)
            return False
        if res is not None and res.data:
            return True
        self.evento(empresa, run_id, "run.cas_perdido",
                    f"Transição para '{novo_status}' não aplicada: o trabalho já não estava em "
                    f"{'/'.join(estados)} (outro processo chegou antes).",
                    severity="debug", payload={"de": estados, "para": novo_status})
        return False

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def evento(self, company_id: str, run_id: str, tipo: str, mensagem: str, *,
               step_id: Optional[str] = None, actor_type: str = "system",
               actor_id: Optional[str] = None, severity: str = "info",
               payload: Optional[dict] = None) -> None:
        try:
            self.db.table("work_events").insert({
                "company_id": company_id,
                "work_run_id": run_id,
                "work_step_id": step_id,
                "event_type": tipo,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "severity": severity,
                "message_human": mensagem,
                "payload_redacted": payload or {},
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] evento '%s' não registrado: %s", tipo, type(exc).__name__)


def linha_company(linha: dict) -> str:
    return linha.get("company_id") or ""


# ---------------------------------------------------------------------------
# O REGISTRO SEM FILA — SPEC-093-B BLOCO 0-bis ②
# ---------------------------------------------------------------------------
#
# POR QUE EXISTE UM SEGUNDO CAMINHO DE CRIAÇÃO, SE `criar()` JÁ CRIA
# ------------------------------------------------------------------
# `criar()` chama o RPC `work_run_create`, e o RPC grava, na MESMA transação,
# uma linha em `work_queue_outbox`. O OutboxDispatcher publica no Redis Stream,
# o Smith Worker consome e procura o handler do `workflow_key` — não acha, e
# marca o run como `failed`.
#
# Isso é o comportamento certo para trabalho que o worker executa. É o
# comportamento ERRADO para trabalho que o worker NÃO executa:
#
#   `acionamento.seguradora`  quem executa é o inbound do WhatsApp, mensagem
#                             por mensagem, ao longo de horas
#   `claims.shadow`           ninguém executa: é observação, e ela só termina
#                             quando a conversa termina
#
# Nos dois casos o run está VIVO enquanto o worker o marcaria `failed` — um
# espelho durável que mente, que é pior do que não existir.
#
# Por isso este caminho grava direto na tabela: mesma tabela, mesmo enum de
# status, mesma linha do tempo em `work_events`, mesmos checkpoints em
# `work_steps`. O que ele não tem é FILA — de propósito.
#
# ⚠️ E não há conflito com a maquinaria da fila. Até 04/10 a proteção era
# ACIDENTAL: `recuperar_orfaos()` filtra `lease_expires_at < agora`, e um run sem
# lease tem esse campo NULO. 🔴 Desde a SPEC-129-A ela é DECLARADA: lease,
# órfãos, despertador, re-despacho, Reprocessar e aprovação só leem e só escrevem
# `runtime_kind='smith'` — o re-despacho pega justamente `running` SEM lease, e
# sem esse filtro pegaria a sombra (`test_o_run_sem_fila.py` prova pelo motor).
#
# 🔴 ESTE HELPER É A ÚNICA CÓPIA. Ele nasceu extraído de
# `dispatch_router.py:515-548`, que era o único lugar do produto que sabia
# gravar `conversation_id` num run (📊 os 4 runs com conversa eram dele). O
# BLOCO A da SPEC-093-B precisava do mesmo INSERT e CLAUDE.md §5 proíbe a
# segunda cópia: consolidar, não duplicar.


async def _talvez_await(resultado: Any) -> Any:
    """O mesmo código serve cliente async e cliente síncrono.

    `runs.py` é um módulo síncrono e o `dispatch_router` usa o cliente async.
    Em vez de duas versões do mesmo INSERT — que é exatamente o que este helper
    existe para impedir — o resultado é aguardado só quando é aguardável.
    """
    if inspect.isawaitable(resultado):
        return await resultado
    return resultado


async def criar_registro_sem_fila(
    db: Any,
    *,
    company_id: str,
    workflow_key: str,
    outcome_type: str,
    outcome_title: str,
    source_type: str,
    source_id: Optional[str],
    conversation_id: Optional[str],
    runtime_kind: str,
    status: str,
    risk_level: str,
    idempotency_key: str,
    input_payload: dict,
    correlation_id: Optional[str] = None,
    workflow_version: str = "1.0.0",
    current_step_key: Optional[str] = None,
    progress_percent: Optional[int] = None,
    requester_user_id: Optional[str] = None,
    requester_agent_id: Optional[str] = None,
) -> dict:
    """Grava um `work_run` **sem enfileirar no outbox**. Devolve a linha.

    Devolve sempre um dicionário com pelo menos `id` e `reused`:

    ``{"id": "...", "reused": False, ...a linha gravada}``   nasceu agora
    ``{"id": "...", "reused": True}``                        já existia

    🔴 **Idempotência é do par `(company_id, idempotency_key)`, nunca da chave
    sozinha:** a mesma chave em duas corretoras são dois trabalhos, e um SELECT
    sem `company_id` devolveria o run da outra casa (CLAUDE.md §7 — o backend
    roda com service role, então o filtro no código é a proteção real).

    ⚠️ `thread_id` **não é parâmetro**: há CHECK no banco
    (`ck_work_runs_thread_format`) exigindo `'work:' || company_id || ':' || id`.
    Quem monta é este helper, para que nenhum chamador possa errá-lo.

    ⚠️ `source_type` também tem CHECK (`ck_work_runs_source`) e só aceita
    `chat | routine | auxiliary | portal | api | admin | system | retry |
    child_run`. Não há valor "sombra" nem "acionamento" ali — o que distingue o
    caminho é `runtime_kind`, que é livre.

    ⛔ `correlation_id` e `progress_percent` são NOT NULL **com default** no
    banco. Mandá-los como `None` é um INSERT recusado, não uma coluna nula — por
    isso a chave só entra na linha quando tem valor.

    ⚠️ Este helper **não** engole exceção de INSERT: quem chama decide se a
    falha derruba o trabalho ou só o espelho.
    """
    # 🔴 SPEC-098 R8 — SEM CORRETORA NÃO SE GRAVA. LEVANTA.
    #
    # ⚠️ `str(None)` é `"None"`: sem esta linha, um `company_id=None` virava a
    # STRING `"None"` e seguia para o INSERT, para o `thread_id`
    # (`work:None:<uuid>`) e para o `select` de idempotência. O banco recusaria
    # o uuid — mas só depois de o trabalho inteiro achar que tinha corretora, e
    # a mensagem de erro falaria de sintaxe de uuid, não de tenant faltando.
    #
    # 🔴 É a mesma lei do LangMem (SPEC-098 §3): *falha dura sem company*. Um
    # run sem corretora não é um run degradado — é um run que ninguém consegue
    # ler de volta, porque toda leitura do produto filtra por `company_id` (§7).
    if not company_id or not str(company_id).strip() or str(company_id).strip() == "None":
        raise ValueError(
            "work_run sem company_id: todo trabalho é DE UMA corretora "
            "(CLAUDE.md §7 · SPEC-098 R8)"
        )

    cli = getattr(db, "client", db)
    empresa = str(company_id)

    achado = await _talvez_await(
        cli.table("work_runs").select("id")
        .eq("company_id", empresa).eq("idempotency_key", idempotency_key)
        .limit(1).execute()
    )
    existente = (getattr(achado, "data", None) or [])
    if existente:
        return {"id": str(existente[0]["id"]), "reused": True}

    run_id = str(uuid.uuid4())
    entrada = input_payload or {}
    agora = _iso(_agora())
    linha: dict = {
        "id": run_id,
        "company_id": empresa,
        "source_type": source_type,
        "source_id": source_id,
        "outcome_type": outcome_type,
        "outcome_title": outcome_title,
        "status": status,
        "risk_level": risk_level,
        "runtime_kind": runtime_kind,
        "workflow_key": workflow_key,
        "workflow_version": workflow_version,
        "thread_id": f"work:{empresa}:{run_id}",
        "input_payload": entrada,
        "input_fingerprint": hashlib.sha256(
            json.dumps(entrada, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "idempotency_key": idempotency_key,
        "queued_at": agora,
        "started_at": agora,
        "conversation_id": conversation_id,
    }
    if current_step_key is not None:
        linha["current_step_key"] = current_step_key
    if progress_percent is not None:
        linha["progress_percent"] = progress_percent
    if correlation_id is not None:
        linha["correlation_id"] = correlation_id

    # 🔴 SPEC-098 R8 — O ATOR VIAJA COM O TRABALHO.
    #
    # 📊 Medido em 06/09/2026: `work_runs` = 3.796 linhas, `requester_user_id`
    # preenchido em **0**, `requester_agent_id` em **0**. As colunas existem
    # desde a SPEC-055 e nunca tiveram escritor: reconstruir *"quem pediu este
    # trabalho"* era impossível para 100% do acervo.
    #
    # ⚠️ **A chave só entra na linha quando tem valor**, como `correlation_id`
    # logo acima: mandar `None` explícito num INSERT do PostgREST é diferente de
    # omitir, e a coluna tem default. Quem não conhece o ator não inventa um.
    #
    # ⛔ **Isto é AUDITORIA, não autorização** (D-098-04). Um `requester_user_id`
    # gravado prova quem PEDIU; não prova que essa pessoa ainda pode. Quem
    # autoriza é a revalidação no instante do efeito
    # (`platform_outbound.send_to_client_guarded` → `vinculo_vigente`, R9).
    if requester_user_id:
        linha["requester_user_id"] = str(requester_user_id)
    if requester_agent_id:
        linha["requester_agent_id"] = str(requester_agent_id)

    await _talvez_await(cli.table("work_runs").insert(linha).execute())
    return {**linha, "reused": False}
