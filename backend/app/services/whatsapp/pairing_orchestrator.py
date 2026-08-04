"""Orquestrador transitório de pareamento WhatsApp (SPEC-051).

Uma tentativa é isolada por ``company_id + purpose``, vive no Redis e emite no
máximo um ``/instance/connect``. O Supabase recebe apenas a integração final;
credenciais nunca entram na resposta pública.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

NETWORK_TIMEOUT_SECONDS = 10.0
SETUP_DEADLINE_SECONDS = 30.0
ATTEMPT_TTL_SECONDS = 10 * 60
REDIS_TTL_SECONDS = 12 * 60
PASSKEY_CONFIRMATION_TIMEOUT_SECONDS = 90

PAIRING_STATES = frozenset({
    "idle",
    "preparing_instance",
    "requesting_qr",
    "qr_ready",
    "qr_scanned",
    "authenticating",
    "passkey_required",
    "passkey_challenge",
    "passkey_awaiting_confirmation",
    "passkey_code_available",
    "connecting",
    "connected",
    "already_connected",
    "qr_expired",
    "passkey_expired",
    "passkey_failed",
    "passkey_socket_restarted",
    "re_pair_required",
    "provider_unavailable",
    "db_pool_exhausted",
    "configuration_error",
    "timed_out",
    "recoverable_error",
    "technical_error",
    "cancelled",
})

TERMINAL_STATES = frozenset({
    "connected",
    "already_connected",
    "qr_expired",
    "passkey_expired",
    "passkey_failed",
    "passkey_socket_restarted",
    "re_pair_required",
    "provider_unavailable",
    "db_pool_exhausted",
    "configuration_error",
    "timed_out",
    "recoverable_error",
    "technical_error",
    "cancelled",
})

_NEXT_ACTION = {
    "idle": "start",
    "preparing_instance": "wait",
    "requesting_qr": "wait",
    "qr_ready": "scan_qr",
    "qr_scanned": "wait",
    "authenticating": "wait",
    "passkey_required": "open_passkey",
    "passkey_challenge": "open_passkey",
    "passkey_awaiting_confirmation": "confirm_on_device",
    "passkey_code_available": "confirm_code",
    "connecting": "wait",
    "connected": "done",
    "already_connected": "done",
    "qr_expired": "retry",
    "passkey_expired": "retry",
    "passkey_failed": "contact_support",
    "passkey_socket_restarted": "retry",
    "re_pair_required": "retry",
    "provider_unavailable": "retry",
    "db_pool_exhausted": "contact_support",
    "configuration_error": "contact_support",
    "timed_out": "retry",
    "recoverable_error": "retry",
    "technical_error": "contact_support",
    "cancelled": "retry",
}

_POLL_MS = {
    "preparing_instance": 1200,
    "requesting_qr": 1500,
    "qr_ready": 1800,
    "qr_scanned": 1200,
    "authenticating": 1200,
    "passkey_required": 1800,
    "passkey_challenge": 1800,
    "passkey_awaiting_confirmation": 1800,
    "passkey_code_available": 1800,
    "connecting": 1500,
}

_PUBLIC_FIELDS = frozenset({
    "attempt_id",
    "state",
    "next_action",
    "expires_at",
    "poll_after_ms",
    "support_ref",
    "error",
    "error_code",
    "correlation_id",
    "qr_base64",
    "qr_text",
    "passkey_stage",
    "passkey_open_url",
    "passkey_code",
    "passkey_error",
    "provider_version",
    "pairing_code",
    "instance",
    "created_at",
    "updated_at",
})


class PairingNotFoundError(LookupError):
    pass


class PairingConflictError(RuntimeError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _resolver_agente_de_atendimento(company_id: str) -> Optional[str]:
    """Quem responde o segurado nesta corretora — ou nada, se não houver ninguém.

    SPEC-063 Bloco A. O pareamento de um número de ATENDIMENTO precisa dizer,
    no próprio registro da integração, qual agente responde por ele. Sem isso o
    motor escolhia o agente ativo mais antigo — o copiloto interno.

    Devolve o id do agente de papel `attendance` da corretora, ATIVO OU NÃO.
    O papel é o que importa aqui; ligar e desligar é decisão de outra tela, e
    quem trata o desligado é o portão de silêncio no webhook. Amarrar só o
    ativo faria o pareamento de uma corretora em modo observação nascer sem
    dono — e ela é justamente a que mais precisa do dono certo registrado.

    Falha de leitura devolve `None` e o pareamento segue: um `agent_id` nulo
    faz o webhook calar (fail-closed), enquanto um id errado faria falar.
    """
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        rows = (db.client.table("agents").select("id, is_active")
                .eq("company_id", str(company_id))
                .eq("agent_role", "attendance")
                .order("created_at").limit(1).execute().data or [])
        if not rows:
            logger.warning(
                "[PAREAMENTO] empresa %s nao tem agente de papel 'attendance'. "
                "A integracao nasce SEM dono e o webhook vai calar ate existir um. "
                "Isso e proposital: melhor mudo que respondido pelo agente errado.",
                company_id,
            )
            return None
        if rows[0].get("is_active") is not True:
            logger.info(
                "[PAREAMENTO] empresa %s: agente de atendimento %s amarrado, porem DESLIGADO "
                "— o numero fica em modo observacao ate alguem liga-lo.",
                company_id, rows[0].get("id"),
            )
        return str(rows[0]["id"])
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[PAREAMENTO] nao foi possivel resolver o agente de atendimento de %s (%s) "
            "— gravando sem dono, o que faz o webhook calar.",
            company_id, type(exc).__name__,
        )
        return None


def _human_error(code: Optional[str]) -> Optional[str]:
    messages = {
        "provider_unavailable": "O serviço de conexão está indisponível no momento.",
        "db_pool_exhausted": "O banco de sessões atingiu o limite de conexões.",
        "configuration_error": "A configuração do canal está incompleta.",
        "qr_expired": "O QR code expirou sem alterar o WhatsApp.",
        "passkey_expired": "A confirmação de segurança expirou sem alterar o WhatsApp.",
        "passkey_failed": "A conta não confirmou a chave de acesso.",
        "passkey_socket_restarted": "A confirmação perdeu a validade após uma reconexão segura.",
        "re_pair_required": "A sessão precisa ser pareada novamente.",
        "timed_out": "A tentativa terminou por tempo limite.",
        "technical_error": "O pareamento encontrou um erro técnico.",
    }
    return messages.get(str(code or ""))


def build_pairing_state(
    state: str,
    *,
    attempt_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    expires_at: Optional[str] = None,
    support_ref: Optional[str] = None,
    error_code: Optional[str] = None,
    error: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Cria a forma estável consumida pelo proxy e pelo modal."""
    if state not in PAIRING_STATES:
        state = "technical_error"
        error_code = error_code or "invalid_pairing_state"
    now = _utcnow()
    correlation_id = correlation_id or str(uuid4())
    support_ref = support_ref or f"WA-{correlation_id.replace('-', '')[:10].upper()}"
    out: Dict[str, Any] = {
        "attempt_id": attempt_id,
        "state": state,
        "next_action": _NEXT_ACTION[state],
        "expires_at": expires_at or _iso(now + timedelta(seconds=ATTEMPT_TTL_SECONDS)),
        "poll_after_ms": _POLL_MS.get(state, 0),
        "support_ref": support_ref,
        "error": error or _human_error(error_code or state),
        "error_code": error_code,
        "correlation_id": correlation_id,
        "updated_at": _iso(now),
    }
    out.update(extra)
    return out


def public_pairing_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Allowlist explícita: nenhum segredo pode atravessar a API."""
    return {key: value for key, value in state.items() if key in _PUBLIC_FIELDS and value is not None}


def _safe_passkey_url(value: Any) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
        if (
            parsed.scheme == "https"
            and parsed.hostname == "web.whatsapp.com"
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
        ):
            return raw
    except ValueError:
        pass
    return None


def normalize_provider_state(qr_payload: Dict[str, Any], status_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza todas as variantes conhecidas sem descartar campos passkey."""
    qr_root = qr_payload if isinstance(qr_payload, dict) else {}
    qr = qr_root.get("data") if isinstance(qr_root.get("data"), dict) else qr_root
    status_root = status_payload if isinstance(status_payload, dict) else {}
    status = status_root.get("data") if isinstance(status_root.get("data"), dict) else status_root

    provider_version = (
        qr.get("providerVersion") or qr.get("provider_version")
        or status.get("providerVersion") or status.get("provider_version")
    )
    if bool(status.get("LoggedIn") or status.get("loggedIn")):
        return {"state": "connected", "provider_version": provider_version}

    raw_state = str(qr.get("state") or status.get("state") or "").strip().lower()
    error_code = str(
        qr.get("errorCode") or qr.get("error_code") or status.get("errorCode") or ""
    ).strip().lower()
    known_terminal = {
        "qr_expired", "passkey_expired", "passkey_failed",
        "passkey_socket_restarted", "re_pair_required", "provider_unavailable",
        "db_pool_exhausted", "configuration_error",
    }
    if error_code in known_terminal:
        return {"state": error_code, "error_code": error_code, "provider_version": provider_version}
    if raw_state in known_terminal:
        return {"state": raw_state, "error_code": raw_state, "provider_version": provider_version}

    passkey_stage = str(qr.get("passkeyStage") or qr.get("passkey_stage") or "").strip()
    passkey_error = str(qr.get("passkeyError") or qr.get("passkey_error") or "").strip() or None
    if passkey_stage or qr.get("passkeyOpenUrl") or qr.get("passkey_open_url"):
        stage_states = {
            "challenge": "passkey_challenge",
            "awaiting_confirmation": "passkey_awaiting_confirmation",
            "confirmation": "passkey_code_available",
            "confirmed": "authenticating",
            "error": "passkey_failed",
            "expired": "passkey_expired",
        }
        state = stage_states.get(passkey_stage, raw_state if raw_state in PAIRING_STATES else "passkey_required")
        return {
            "state": state,
            "passkey_stage": passkey_stage or None,
            "passkey_open_url": _safe_passkey_url(qr.get("passkeyOpenUrl") or qr.get("passkey_open_url")),
            "passkey_code": qr.get("passkeyCode") or qr.get("passkey_code"),
            "passkey_error": passkey_error,
            "provider_expires_at": qr.get("expiresAt") or qr.get("expires_at"),
            "provider_version": provider_version,
            "error_code": error_code or ("passkey_failed" if state == "passkey_failed" else None),
        }

    raw_qr = (
        qr.get("QRCode") or qr.get("qrcode") or qr.get("qr")
        or qr.get("base64") or qr.get("qr_base64")
    )
    if raw_qr:
        return {
            "state": "qr_ready",
            "qr_base64": str(raw_qr),
            "qr_text": qr.get("code") or qr.get("qr_text"),
            "provider_expires_at": qr.get("expiresAt") or qr.get("expires_at"),
            "provider_version": provider_version,
        }
    if raw_state in ("qr_scanned", "authenticating", "connecting"):
        return {"state": raw_state, "provider_version": provider_version}
    if bool(status.get("Connected") or status.get("connected")):
        return {"state": "connecting", "provider_version": provider_version}
    return {"state": "requesting_qr", "provider_version": provider_version}


class PairingOrchestrator:
    """Coordena uma única tentativa serial por empresa e função."""

    def __init__(self) -> None:
        self.base_url = (os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
        self.global_key = os.getenv("EVOLUTION_GO_GLOBAL_KEY") or ""
        self.public_backend_url = (
            os.getenv("PUBLIC_BACKEND_URL") or os.getenv("BACKEND_PUBLIC_URL") or ""
        ).rstrip("/")

    @staticmethod
    def _key(company_id: str, purpose: str) -> str:
        return f"whatsapp:pairing:{company_id}:{purpose}"

    @staticmethod
    def _attempt_key(attempt_id: str) -> str:
        return f"whatsapp:pairing:attempt:{attempt_id}"

    @staticmethod
    def _lock_key(company_id: str, purpose: str) -> str:
        return f"whatsapp:pairing:lock:{company_id}:{purpose}"

    @staticmethod
    def _mutation_key(attempt_id: str) -> str:
        return f"whatsapp:pairing:mutation:{attempt_id}"

    async def _redis(self):
        from app.core.redis import get_async_redis_client

        return await get_async_redis_client()

    async def _save(self, state: Dict[str, Any]) -> Dict[str, Any]:
        expected_revision = int(state.get("_revision") or 0)
        candidate = dict(state)
        candidate["_revision"] = expected_revision + 1
        candidate["updated_at"] = _iso(_utcnow())
        redis = await self._redis()
        raw = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
        attempt_key = self._attempt_key(str(state["attempt_id"]))
        scope_key = self._key(str(state["company_id"]), str(state["purpose"]))
        result = await redis.eval(
            """
            local current = redis.call('get', KEYS[1])
            if current then
              local ok, decoded = pcall(cjson.decode, current)
              if ok then
                local revision = tonumber(decoded['_revision'] or 0)
                if revision ~= tonumber(ARGV[3]) then
                  return current
                end
              end
            elseif tonumber(ARGV[3]) ~= 0 then
              return ''
            end
            redis.call('set', KEYS[1], ARGV[1], 'EX', ARGV[2])
            local scoped = redis.call('get', KEYS[2])
            local replace_scope = ARGV[5] == '1'
            if scoped and not replace_scope then
              local scope_ok, scope_decoded = pcall(cjson.decode, scoped)
              replace_scope = scope_ok and scope_decoded['attempt_id'] == ARGV[4]
            end
            if (not scoped) or replace_scope then
              redis.call('set', KEYS[2], ARGV[1], 'EX', ARGV[2])
            end
            return ARGV[1]
            """,
            2,
            attempt_key,
            scope_key,
            raw,
            str(REDIS_TTL_SECONDS),
            str(expected_revision),
            str(state["attempt_id"]),
            "1" if expected_revision == 0 else "0",
        )
        persisted = self._decode(result)
        if not persisted:
            persisted = self._decode(await redis.get(attempt_key)) or candidate
        state.clear()
        state.update(persisted)
        return state

    @staticmethod
    def _decode(raw: Any) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (TypeError, ValueError):
            return None

    async def _load_attempt(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        return self._decode(await (await self._redis()).get(self._attempt_key(attempt_id)))

    async def _release_lock(self, key: str, value: str) -> None:
        redis = await self._redis()
        try:
            await redis.eval(
                "if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",
                1,
                key,
                value,
            )
        except Exception:  # noqa: BLE001 - TTL ainda impede lock órfão
            pass

    def _validate_config(self) -> None:
        if not self.base_url or not self.global_key or not self.public_backend_url:
            raise RuntimeError("configuration_error")

    async def _acquire_mutation(
        self, attempt_id: str, *, wait_seconds: float = 0.0
    ) -> tuple[Optional[str], Optional[str]]:
        """Serialize refresh/cancel so a terminal state cannot be resurrected."""
        redis = await self._redis()
        key = self._mutation_key(attempt_id)
        value = secrets.token_hex(12)
        deadline = asyncio.get_running_loop().time() + max(0.0, wait_seconds)
        while True:
            if await redis.set(key, value, nx=True, ex=35):
                return key, value
            if asyncio.get_running_loop().time() >= deadline:
                return None, None
            await asyncio.sleep(0.05)

    @staticmethod
    def _instance_name(company_id: str, purpose: str) -> str:
        base = str(company_id).replace("-", "")[:10]
        if purpose == "observer":
            return f"ab-obs-{base}-1"
        suffix = "".join(ch for ch in purpose if ch.isalnum())[:10] or "attendance"
        return f"ab-{base}-{suffix}"

    async def _integration(self, company_id: str, purpose: str) -> Optional[Dict[str, Any]]:
        from app.core.database import get_supabase_client
        from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

        db = get_supabase_client()

        def _query() -> list:
            return (
                db.client.table("integrations").select("*")
                .eq("company_id", company_id).eq("provider", "evolution-go")
                .eq("purpose", purpose).eq("is_active", True)
                .order("last_seen_at", desc=True).limit(1).execute().data or []
            )

        rows = await asyncio.to_thread(_query)
        return prepare_integration_for_runtime(rows[0]) if rows else None

    async def _escopo_lembrado(self, company_id: str, purpose: str) -> Optional[Dict[str, Any]]:
        """O que esta corretora JÁ escolheu observar — mesmo com a linha desligada.

        🔴 SPEC-065 — aqui morava a repetição do incidente de 29/07.

        O escopo era herdado de `_integration()`, que filtra `is_active=True`.
        Uma corretora que **desconectou** perdia a memória da própria escolha, e
        o `setdefault` abaixo lhe dava o escopo mais largo que existe.

        📊 Medido em 04/08/2026, e as duas corretoras cairiam em lados opostos
        da MESMA ação:

            AutoFleet   is_active=false  -> sem memória -> volta a ver TUDO
            Resulta     is_active=TRUE   -> preserva    -> segue só seguradora

        A da esquerda é a que a Regina ia parear, no celular dela. A do meio da
        tabela é o incidente de 29/07 outra vez — 630 contatos pessoais.

        Desconectar é uma pausa, não um esquecimento. A escolha de quem pode ser
        gravado pertence à corretora e sobrevive ao botão de desconectar.
        """
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _query() -> list:
            return (
                db.client.table("integrations").select("alert_target, is_active, created_at")
                .eq("company_id", company_id).eq("provider", "evolution-go")
                .eq("purpose", purpose)
                .order("created_at", desc=True).limit(5).execute().data or []
            )

        try:
            linhas = await asyncio.to_thread(_query)
        except Exception:  # noqa: BLE001
            return None
        # A mais recente que REALMENTE declarou um escopo. Linha sem `alert_target`
        # não é memória: é ausência, e ausência não pode sobrescrever escolha.
        for linha in linhas:
            alvo = linha.get("alert_target") or {}
            if isinstance(alvo, dict) and alvo.get("observer_scope"):
                return alvo
        return None

    async def _persist_integration(
        self,
        *,
        company_id: str,
        purpose: str,
        instance: str,
        instance_token: str,
        webhook_hash: str,
        webhook_prefix: str,
        alert_target: Optional[Dict[str, Any]],
    ) -> None:
        from app.core.database import get_supabase_client
        from app.services.whatsapp.integration_secrets import prepare_integration_for_storage

        db = get_supabase_client()
        target = dict(alert_target or {})
        if purpose == "observer":
            # `setdefault`, não atribuição. O Observador NASCE vendo segurado
            # também — é assim que as cartas da AutoFleet se formaram, e o padrão
            # continua esse. Mas quem pediu explicitamente `insurers_only` pediu
            # por um motivo, e um re-pareamento não pode desfazer isso em
            # silêncio: era o que acontecia aqui, e o efeito só apareceria
            # depois, com conversa que ninguém queria gravar já gravada.
            #
            # As duas linhas abaixo já usavam setdefault. Esta era a estranha.
            #
            # SPEC-065 — eu tentei estreitar este padrão em 04/08 e VOLTEI ATRÁS.
            #
            # O argumento para estreitar era bom: 📊 em 29/07 o escopo largo
            # custou 2.556 transcrições e 745 sessões de 630 contatos
            # particulares, capturadas de um celular PESSOAL. E o sistema não tem
            # como saber se o telefone que está sendo pareado é o de trabalho de
            # uma corretora ou o pessoal de alguém — 📊 não existe tabela de
            # segurados com telefone neste banco.
            #
            # Mas o argumento contra é de PRODUTO, e ele é do Founder, não meu:
            # com o estreito, sete dias de observação rendem **zero conversa de
            # atendimento** — e é exatamente delas que saem a curadoria e as
            # cartas. `test_observador_silencio.py` defende isso, e está certo.
            #
            # Estreitar o padrão sozinho seria reduzir escopo em silêncio para
            # comprar segurança (CLAUDE.md §11). O que faço aqui é o que me cabe:
            # **a escolha passa a ser lembrada** (`_escopo_lembrado`, acima), para
            # que ela seja uma decisão e não um acidente de `is_active`.
            #
            # ⚠️ Registrado em P-84: hoje as TRÊS memórias dizem `insurers_only`
            # porque foi assim que a contenção de 29/07 as deixou. Isso é uma
            # emergência virando política sem ninguém ter decidido. Antes de
            # parear, o Founder precisa dizer, por corretora, o que pode gravar.
            target.setdefault("observer_scope", "insurers_and_clients")
            target.setdefault("observer_exclusions", [])
            target.setdefault("internal_numbers", [])
        record = prepare_integration_for_storage({
            "company_id": company_id,
            "identifier": instance,
            "purpose": purpose,
            "provider": "evolution-go",
            "base_url": self.base_url,
            "instance_id": instance,
            "token": instance_token,
            "webhook_token_hash": webhook_hash,
            "webhook_token_prefix": webhook_prefix,
            "alert_target": target or None,
            "channel_status": "connecting",
            "is_active": True,
            # SPEC-063 Bloco A. Aqui estava `None if purpose == "observer" else None`
            # — um ternário que devolve None nos DOIS ramos. Escrito para dizer
            # "observador não tem agente", acabou dizendo "ninguém tem agente".
            #
            # Sem `agent_id`, o webhook chamava o motor sem indicar quem deveria
            # responder, e o seletor pegava o agente ativo mais antigo: o COPILOTO
            # INTERNO, cujo prompt manda entregar CPF sem mascarar. O segurado
            # falaria com o agente errado, no número da corretora.
            #
            # Agora: observador continua sem agente (é mudo por construção), e
            # atendimento recebe o agente de papel `attendance` da própria
            # corretora. Se ele não existir, fica nulo E o pareamento avisa —
            # nulo por ausência é diferente de nulo por desenho.
            "agent_id": _resolver_agente_de_atendimento(company_id) if purpose == "attendance" else None,
            "last_seen_at": _iso(_utcnow()),
        })

        def _upsert() -> None:
            rows = (
                db.client.table("integrations").select("id")
                .eq("company_id", company_id).eq("provider", "evolution-go")
                .eq("instance_id", instance).limit(1).execute().data or []
            )
            if rows:
                db.client.table("integrations").update(record).eq("id", rows[0]["id"]).execute()
            else:
                db.client.table("integrations").insert(record).execute()
            db.client.table("integrations").update({"is_active": False}) \
                .eq("company_id", company_id).eq("provider", "evolution-go") \
                .eq("purpose", purpose).neq("instance_id", instance).execute()
            # O pareamento NÃO mexe no estado do agente de atendimento.
            #
            # Aqui existia um `update({"is_active": False})`. A intenção era
            # boa — garantir silêncio ao parear — e o efeito colateral era
            # grave: **re-parear desligava um agente que estava trabalhando.**
            #
            # E re-parear não é raro. A sessão do WhatsApp cai: telefone
            # desligado, logout, QR vencido, troca de aparelho. A corretora
            # reconecta e, sem nada dizer, o agente que atendia há semanas fica
            # mudo. O painel mostra "Observando em silêncio" e ninguém entende
            # por quê — o clique que faltava é invisível.
            #
            # O silêncio de uma corretora NOVA não depende disto: o agente de
            # atendimento nasce desligado pelo blueprint
            # (`EVEN_ATTENDANCE_BLUEPRINT.default_active = false`) e por gatilho
            # no banco. Quem liga é o botão, e só ele.
            #
            # Decisão do Founder, 27/07/2026: "O AGENTE DE ATENDIMENTO NASCE
            # DESLIGADO. ELE SÓ É LIGADO SE CLICAR NO BOTÃO DEPOIS DE PAREADO."

        await asyncio.to_thread(_upsert)

    async def _mark_connected(
        self, state: Dict[str, Any], status_payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """Marca a linha como conectada — e guarda QUAL telefone conectou.

        SPEC-063. Até 04/08/2026 este update gravava estado e relógio, e
        descartava a identidade. O resultado prático foi o Founder não conseguir
        dizer qual número estava pareado no celular da atendente: a informação
        passava por aqui a cada conexão e nunca era escrita em lugar nenhum.

        `status_payload` é o corpo do `/instance/status`, que o whatsmeow
        preenche com o JID do aparelho depois do pareamento. Quando ele não vem,
        `dados_de_pareamento` devolve `{}` e o update segue sem esses campos —
        preservando o telefone gravado antes. Um refresh silencioso não pode
        apagar o que o pareamento já provou.
        """
        from app.core.database import get_supabase_client
        from app.services.whatsapp.numero_pareado import dados_de_pareamento, mascarar

        db = get_supabase_client()
        agora = _iso(_utcnow())
        campos: Dict[str, Any] = {"channel_status": "connected", "last_seen_at": agora}
        try:
            campos.update(dados_de_pareamento(status_payload or {}, agora))
        except Exception:  # noqa: BLE001 — identidade nunca impede marcar conectado
            pass

        def _update() -> None:
            db.client.table("integrations").update(campos) \
                .eq("company_id", state["company_id"]).eq("purpose", state["purpose"]) \
                .eq("instance_id", state["instance"]).execute()

        await asyncio.to_thread(_update)
        if campos.get("paired_phone_e164"):
            # Mascarado sempre: é a linha de trabalho de uma pessoa real.
            logger.info("[PAIRING] %s pareado em %s", state["purpose"],
                        mascarar(campos["paired_phone_e164"]))

    async def _invalidate_incomplete(self, integration: Optional[Dict[str, Any]]) -> None:
        """Best-effort teardown for an expired/cancelled ceremony.

        This prevents a stale QR or passkey assertion from completing after the
        product has already exposed a terminal state.
        """
        if not integration or not integration.get("token"):
            return
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(NETWORK_TIMEOUT_SECONDS), base_url=self.base_url
            ) as client:
                await client.delete("/instance/logout", headers={"apikey": integration["token"]})
        except Exception:  # noqa: BLE001 - terminal local state remains authoritative
            logger.warning("[PAIRING] provider invalidation failed")

    async def _provider_create(self, client: httpx.AsyncClient, instance: str, token: str) -> None:
        response = await client.post(
            "/instance/create",
            headers={"apikey": self.global_key, "Content-Type": "application/json"},
            json={
                "name": instance,
                "token": token,
                "advancedSettings": {
                    "readMessages": False,
                    "alwaysOnline": False,
                    "rejectCall": False,
                    "ignoreGroups": True,
                    "ignoreStatus": True,
                },
            },
        )
        if response.status_code in (409, 422):
            listing = await client.get("/instance/all", headers={"apikey": self.global_key})
            rows = (listing.json() or {}).get("data", []) if listing.status_code < 400 else []
            ghost = next((row for row in rows if str(row.get("name") or "") == instance), None)
            if ghost and not ghost.get("jid") and ghost.get("id"):
                # Casca vazia: existe no provedor mas nunca chegou a ter telefone.
                # Não dá para conectar, então some e nasce de novo.
                await client.delete(f"/instance/delete/{ghost['id']}", headers={"apikey": self.global_key})
                response = await client.post(
                    "/instance/create",
                    headers={"apikey": self.global_key, "Content-Type": "application/json"},
                    json={
                        "name": instance,
                        "token": token,
                        "advancedSettings": {
                            "readMessages": False, "alwaysOnline": False,
                            "rejectCall": False, "ignoreGroups": True, "ignoreStatus": True,
                        },
                    },
                )
            elif ghost:
                # A instância existe E tem telefone. **Isto não é erro** — é o caso
                # normal de quem já pareou uma vez e quer parear de novo.
                #
                # Tratar como erro criava um beco sem saída, e ele apareceu em
                # 03/08/2026: a tela mostrava "Desconectado" (então não havia botão
                # Desconectar) e todo "Gerar novo QR" morria em
                # `configuration_error` — *"a configuração do canal precisa de
                # ajuste pelo suporte"*. Não havia suporte a chamar: era o próprio
                # código recusando a única saída.
                #
                # Quem decide o que fazer é a linha logo depois desta função, que
                # pergunta o status e já sabe tratar os dois desfechos: LoggedIn
                # verdadeiro vira `already_connected`; falso segue para o QR novo.
                # Aqui basta não atrapalhar.
                logger.info("[PAIRING] instancia %s ja existe com telefone — seguindo para o status", instance)
                return
        if response.status_code >= 400:
            raise RuntimeError(f"provider_http_{response.status_code}")

    async def _prepare_and_connect(
        self,
        state: Dict[str, Any],
        *,
        method: str,
        phone_number: Optional[str],
    ) -> Dict[str, Any]:
        from app.services.whatsapp.channel_security import build_webhook_url, new_webhook_credentials

        company_id, purpose = state["company_id"], state["purpose"]
        integration = await self._integration(company_id, purpose)
        instance = str((integration or {}).get("instance_id") or self._instance_name(company_id, purpose))
        instance_token = str((integration or {}).get("token") or secrets.token_hex(16))
        state["instance"] = instance
        await self._save(state)

        timeout = httpx.Timeout(NETWORK_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout, base_url=self.base_url) as client:
            if not integration:
                await self._provider_create(client, instance, instance_token)

            status_response = await client.get("/instance/status", headers={"apikey": instance_token})
            if integration and status_response.status_code in (401, 404):
                # The database can outlive an unregistered/ghost provider
                # instance. Recreate it once under the same deterministic name
                # instead of trapping the UI in a permanent configuration error.
                await self._provider_create(client, instance, instance_token)
                status_response = await client.get(
                    "/instance/status", headers={"apikey": instance_token}
                )
            if status_response.status_code >= 500:
                raise RuntimeError("provider_unavailable")
            if status_response.status_code >= 400:
                raise RuntimeError(f"provider_http_{status_response.status_code}")
            status_json = status_response.json() if status_response.status_code < 400 and status_response.content else {}
            if bool((status_json.get("data") or {}).get("LoggedIn")):
                state.update(build_pairing_state(
                    "already_connected",
                    attempt_id=state["attempt_id"],
                    correlation_id=state["correlation_id"],
                    expires_at=state["expires_at"],
                    support_ref=state["support_ref"],
                    instance=instance,
                    created_at=state["created_at"],
                ))
                await self._mark_connected(state, status_json)
                return await self._save(state)

            webhook_token, webhook_hash, webhook_prefix = new_webhook_credentials()
            webhook_url = build_webhook_url(self.public_backend_url, "evolution-go", webhook_token)
            await self._persist_integration(
                company_id=company_id,
                purpose=purpose,
                instance=instance,
                instance_token=instance_token,
                webhook_hash=webhook_hash,
                webhook_prefix=webhook_prefix,
                # A memória do escopo NÃO vem de `integration`: aquela busca
                # filtra `is_active=True`, e desconectar apagaria a escolha da
                # corretora. Ver `_escopo_lembrado`.
                alert_target=(await self._escopo_lembrado(company_id, purpose)
                              or (integration or {}).get("alert_target")),
            )

            state.update(build_pairing_state(
                "requesting_qr",
                attempt_id=state["attempt_id"],
                correlation_id=state["correlation_id"],
                expires_at=state["expires_at"],
                support_ref=state["support_ref"],
                instance=instance,
                created_at=state["created_at"],
            ))
            state["_connect_issued"] = True
            await self._save(state)
            response = await client.post(
                "/instance/connect",
                headers={"apikey": instance_token, "Content-Type": "application/json"},
                json={
                    "webhookUrl": webhook_url,
                    "subscribe": ["MESSAGE", "CONNECTION", "HISTORY_SYNC", "QRCODE"],
                    "immediate": True,
                },
            )
            if response.status_code >= 400:
                raise RuntimeError(f"provider_http_{response.status_code}")

            if method == "phone":
                pair_response = await client.post(
                    "/instance/pair",
                    headers={"apikey": instance_token, "Content-Type": "application/json"},
                    json={
                        "phone": phone_number,
                        "subscribe": ["MESSAGE", "CONNECTION", "HISTORY_SYNC", "QRCODE"],
                    },
                )
                if pair_response.status_code >= 400:
                    raise RuntimeError(f"provider_pair_http_{pair_response.status_code}")
                pair_json = pair_response.json() if pair_response.content else {}
                data = pair_json.get("data") if isinstance(pair_json.get("data"), dict) else pair_json
                code = data.get("PairingCode") or data.get("pairingCode") or data.get("pairing_code")
                if code:
                    state["pairing_code"] = str(code)

        return await self._refresh(state)

    async def _refresh(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if state.get("state") in TERMINAL_STATES:
            return state
        expires_at = _parse_iso(state.get("expires_at"))
        if expires_at and _utcnow() >= expires_at:
            await self._invalidate_incomplete(
                await self._integration(state["company_id"], state["purpose"])
            )
            state.update(build_pairing_state(
                "timed_out",
                attempt_id=state["attempt_id"], correlation_id=state["correlation_id"],
                expires_at=state["expires_at"], support_ref=state["support_ref"],
                error_code="timed_out", instance=state.get("instance"),
                created_at=state.get("created_at"),
            ))
            return await self._save(state)

        integration = await self._integration(state["company_id"], state["purpose"])
        if not integration:
            raise RuntimeError("configuration_error")
        token = str(integration.get("token") or "")
        timeout = httpx.Timeout(NETWORK_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout, base_url=self.base_url) as client:
            status_response = await client.get("/instance/status", headers={"apikey": token})
            if status_response.status_code >= 500:
                raise RuntimeError("provider_unavailable")
            if status_response.status_code >= 400:
                raise RuntimeError(f"provider_http_{status_response.status_code}")
            status_json = status_response.json() if status_response.content else {}
            qr_response = await client.get("/instance/qr", headers={"apikey": token})
            qr_json = qr_response.json() if qr_response.status_code < 400 and qr_response.content else {}
            if qr_response.status_code >= 500 or qr_response.status_code == 429:
                raise RuntimeError("provider_unavailable")
            if qr_response.status_code >= 400:
                raise RuntimeError(f"provider_http_{qr_response.status_code}")

        normalized = normalize_provider_state(qr_json, status_json)
        next_state = normalized.pop("state")
        provider_expiry = normalized.pop("provider_expires_at", None)
        if provider_expiry:
            state["provider_expires_at"] = provider_expiry
        if next_state == "passkey_awaiting_confirmation":
            started = _parse_iso(state.get("_passkey_wait_started_at"))
            if not started:
                state["_passkey_wait_started_at"] = _iso(_utcnow())
            elif (_utcnow() - started).total_seconds() > PASSKEY_CONFIRMATION_TIMEOUT_SECONDS:
                next_state = "passkey_failed"
                normalized["error_code"] = "passkey_failed"
                await self._invalidate_incomplete(integration)

        state.update(build_pairing_state(
            next_state,
            attempt_id=state["attempt_id"],
            correlation_id=state["correlation_id"],
            expires_at=provider_expiry or state["expires_at"],
            support_ref=state["support_ref"],
            error_code=normalized.get("error_code"),
            instance=state.get("instance"),
            created_at=state.get("created_at"),
            **{key: value for key, value in normalized.items() if key != "error_code"},
        ))
        if next_state in ("connected", "already_connected"):
            await self._mark_connected(state, status_json)
        return await self._save(state)

    @staticmethod
    def _error_state(code: str) -> str:
        if code in PAIRING_STATES:
            return code
        if "too_many_clients" in code or "pool" in code:
            return "db_pool_exhausted"
        if code.startswith("provider_http_5") or code == "provider_unavailable":
            return "provider_unavailable"
        if code.startswith("provider_http_4") or code.startswith("provider_pair_http_4"):
            return "configuration_error"
        if code == "configuration_error":
            return code
        return "technical_error"

    async def start(
        self,
        company_id: str,
        purpose: str = "observer",
        *,
        correlation_id: Optional[str] = None,
        method: str = "qr",
        phone_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._validate_config()
        company_id = str(company_id or "").strip()
        purpose = str(purpose or "observer").strip().lower()
        method = "phone" if method == "phone" else "qr"
        if not company_id or purpose not in ("observer", "attendance", "dispatch"):
            raise ValueError("invalid_pairing_scope")
        if method == "phone":
            phone_number = "".join(ch for ch in str(phone_number or "") if ch.isdigit())
            if not 10 <= len(phone_number) <= 15:
                raise ValueError("invalid_phone_number")

        redis = await self._redis()
        lock_value = secrets.token_hex(12)
        lock_key = self._lock_key(company_id, purpose)
        acquired = await redis.set(
            lock_key,
            lock_value,
            nx=True,
            ex=int(SETUP_DEADLINE_SECONDS) + 5,
        )
        if not acquired:
            current = self._decode(await redis.get(self._key(company_id, purpose)))
            if current and current.get("state") not in TERMINAL_STATES:
                return public_pairing_state(current)
            raise PairingConflictError("pairing_already_starting")

        # The setup lock protects only concurrent calls. A reload or another
        # browser tab can arrive after it is released, so re-read the active
        # scope while holding the lock before issuing another /instance/connect.
        current = self._decode(await redis.get(self._key(company_id, purpose)))
        if current and current.get("state") not in TERMINAL_STATES:
            await self._release_lock(lock_key, lock_value)
            return public_pairing_state(current)

        attempt_id = str(uuid4())
        correlation_id = correlation_id or str(uuid4())
        now = _utcnow()
        state = build_pairing_state(
            "preparing_instance",
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            expires_at=_iso(now + timedelta(seconds=ATTEMPT_TTL_SECONDS)),
            created_at=_iso(now),
        )
        state.update({"company_id": company_id, "purpose": purpose, "method": method})
        await self._save(state)
        try:
            async with asyncio.timeout(SETUP_DEADLINE_SECONDS):
                state = await self._prepare_and_connect(
                    state, method=method, phone_number=phone_number
                )
        except TimeoutError:
            code = "timed_out"
            state.update(build_pairing_state(
                code, attempt_id=attempt_id, correlation_id=correlation_id,
                expires_at=state["expires_at"], support_ref=state["support_ref"],
                error_code=code, instance=state.get("instance"), created_at=state["created_at"],
            ))
            await self._save(state)
        except (httpx.TimeoutException, httpx.NetworkError):
            code = "provider_unavailable"
            state.update(build_pairing_state(
                code, attempt_id=attempt_id, correlation_id=correlation_id,
                expires_at=state["expires_at"], support_ref=state["support_ref"],
                error_code=code, instance=state.get("instance"), created_at=state["created_at"],
            ))
            await self._save(state)
        except Exception as exc:  # noqa: BLE001
            raw_code = str(exc)[:80]
            code = self._error_state(raw_code)
            logger.warning("[PAIRING] start falhou ref=%s code=%s", state["support_ref"], code)
            state.update(build_pairing_state(
                code, attempt_id=attempt_id, correlation_id=correlation_id,
                expires_at=state["expires_at"], support_ref=state["support_ref"],
                error_code=raw_code, instance=state.get("instance"), created_at=state["created_at"],
            ))
            await self._save(state)
        finally:
            await self._release_lock(lock_key, lock_value)
        return public_pairing_state(state)

    async def get(self, company_id: str, purpose: str, attempt_id: str) -> Dict[str, Any]:
        state = await self._load_attempt(attempt_id)
        if not state or state.get("company_id") != company_id or state.get("purpose") != purpose:
            raise PairingNotFoundError("pairing_not_found")
        if state.get("state") in TERMINAL_STATES:
            return public_pairing_state(state)

        mutation_key, mutation_value = await self._acquire_mutation(attempt_id)
        if not mutation_key or not mutation_value:
            return public_pairing_state(state)
        try:
            # Cancel may have won between the first read and lock acquisition.
            state = await self._load_attempt(attempt_id)
            if not state or state.get("company_id") != company_id or state.get("purpose") != purpose:
                raise PairingNotFoundError("pairing_not_found")
            if state.get("state") in TERMINAL_STATES:
                return public_pairing_state(state)
            try:
                state = await self._refresh(state)
            except (httpx.TimeoutException, httpx.NetworkError):
                state.update(build_pairing_state(
                    "provider_unavailable",
                    attempt_id=state["attempt_id"], correlation_id=state["correlation_id"],
                    expires_at=state["expires_at"], support_ref=state["support_ref"],
                    error_code="provider_unavailable", instance=state.get("instance"),
                    created_at=state.get("created_at"),
                ))
                await self._save(state)
            except Exception as exc:  # noqa: BLE001
                raw_code = str(exc)[:80]
                code = self._error_state(raw_code)
                state.update(build_pairing_state(
                    code,
                    attempt_id=state["attempt_id"], correlation_id=state["correlation_id"],
                    expires_at=state["expires_at"], support_ref=state["support_ref"],
                    error_code=raw_code, instance=state.get("instance"),
                    created_at=state.get("created_at"),
                ))
                await self._save(state)
        finally:
            await self._release_lock(mutation_key, mutation_value)
        return public_pairing_state(state)

    async def retry(self, company_id: str, purpose: str, attempt_id: str, correlation_id: str) -> Dict[str, Any]:
        state = await self._load_attempt(attempt_id)
        if not state or state.get("company_id") != company_id or state.get("purpose") != purpose:
            raise PairingNotFoundError("pairing_not_found")
        if state.get("state") not in TERMINAL_STATES and state.get("state") != "recoverable_error":
            raise PairingConflictError("pairing_still_active")
        return await self.start(
            company_id,
            purpose,
            correlation_id=correlation_id,
            # A retry never reuses a phone number kept in transient state. QR is
            # deterministic and avoids retaining extra PII in Redis.
            method="qr",
        )

    async def cancel(self, company_id: str, purpose: str, attempt_id: str) -> Dict[str, Any]:
        state = await self._load_attempt(attempt_id)
        if not state or state.get("company_id") != company_id or state.get("purpose") != purpose:
            raise PairingNotFoundError("pairing_not_found")
        mutation_key, mutation_value = await self._acquire_mutation(
            attempt_id, wait_seconds=12.0
        )
        if not mutation_key or not mutation_value:
            raise PairingConflictError("pairing_state_busy")
        try:
            state = await self._load_attempt(attempt_id)
            if not state or state.get("company_id") != company_id or state.get("purpose") != purpose:
                raise PairingNotFoundError("pairing_not_found")
            if state.get("state") in ("connected", "already_connected", "cancelled"):
                return public_pairing_state(state)
            integration = await self._integration(company_id, purpose)
            if integration:
                await self._invalidate_incomplete(integration)
            state.update(build_pairing_state(
                "cancelled",
                attempt_id=state["attempt_id"], correlation_id=state["correlation_id"],
                expires_at=state["expires_at"], support_ref=state["support_ref"],
                instance=state.get("instance"), created_at=state.get("created_at"),
            ))
            await self._save(state)
            return public_pairing_state(state)
        finally:
            await self._release_lock(mutation_key, mutation_value)


_orchestrator: Optional[PairingOrchestrator] = None


def get_pairing_orchestrator() -> PairingOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PairingOrchestrator()
    return _orchestrator


__all__ = [
    "PAIRING_STATES",
    "TERMINAL_STATES",
    "PairingConflictError",
    "PairingNotFoundError",
    "PairingOrchestrator",
    "build_pairing_state",
    "get_pairing_orchestrator",
    "normalize_provider_state",
    "public_pairing_state",
]
