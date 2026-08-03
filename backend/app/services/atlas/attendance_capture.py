"""SPEC-040 Onda 1 — Espelho de Atendimento: borda de captura da Parte 1.

Segundo destino do Observador: as conversas de TRABALHO da equipe da corretora
com os SEGURADOS dela (Parte 1 do atendimento), no numero corporativo
autorizado. Regras inegociaveis:

1. So captura em integracao purpose='observer' com observer_scope=
   'insurers_and_clients' (ligado explicitamente no pareamento/onboarding).
   Default de toda integracao existente = 'insurers_only' (nada muda p/ elas).
2. PII vive AQUI (attendance_transcripts, RLS service-only) e SO aqui.
   NUNCA vai ao RAG. A destilacao (Onda 3) produz playbooks de conduta e
   knowledge cards SEM nenhum dado pessoal.
3. Midia: so METADADOS (mimetype/filename/caption) — nunca bytes/base64.
4. MUDO por construcao: este modulo nao importa nenhum cliente de envio.
5. Retencao: o cru expira (env ATTENDANCE_RETENTION_DAYS, default 90 dias,
   contado da INGESTAO — historico importado hoje vale 90 dias a partir de
   hoje). O purge roda 1x/dia no APScheduler. O destilado e permanente.

O armazenamento reusa a MESMA mecanica de sessao do Atlas (funcao
parametrizada em observer_intake) — tabela separada, logica unica.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TRANSCRIPTS_TABLE = "attendance_transcripts"
SESSIONS_TABLE = "attendance_sessions"

SCOPE_INSURERS_ONLY = "insurers_only"
SCOPE_FULL = "insurers_and_clients"


def observer_scope(integration: dict) -> str:
    """Escopo de captura da integracao observer. Vive em alert_target
    (jsonb ja existente) para nao exigir migracao de integrations."""
    at = (integration or {}).get("alert_target")
    scope = ""
    if isinstance(at, dict):
        scope = str(at.get("observer_scope") or "").strip().lower()
    return scope if scope in (SCOPE_INSURERS_ONLY, SCOPE_FULL) else SCOPE_INSURERS_ONLY


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def client_chat_allowed(
    integration: dict,
    observer_number: str,
    remote_jid: str,
    counterparty: str,
    alternate_jid: str = "",
) -> bool:
    """Fail-closed boundary for insurer/client observation.

    Only direct WhatsApp chats are eligible. Tenant-owned exclusions live in
    ``integrations.alert_target`` so one brokerage can never alter another
    brokerage's boundary.
    """
    if observer_scope(integration) != SCOPE_FULL:
        return False
    remote = str(remote_jid or "").strip().lower()
    if not remote.endswith(("@s.whatsapp.net", "@lid")):
        return False
    if remote.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):
        return False
    if remote.endswith("@lid"):
        alternate = str(alternate_jid or "").strip().lower()
        if not alternate.endswith("@s.whatsapp.net"):
            return False
        number = _digits(alternate.split("@", 1)[0].split(":", 1)[0])
    else:
        number = _digits(counterparty or remote.split("@", 1)[0].split(":", 1)[0])
    if not number:
        return False
    own = _digits(observer_number)
    if own and number == own:
        return False
    alert_target = (integration or {}).get("alert_target")
    alert_target = alert_target if isinstance(alert_target, dict) else {}
    excluded = {
        _digits(value)
        for field in ("observer_exclusions", "internal_numbers")
        for value in (alert_target.get(field) or [])
        if _digits(value)
    }
    return number not in excluded


async def _beat(actions: int = 1) -> None:
    try:
        from app.core.heartbeat import beat

        await beat("espelho_atendimento", actions)
    except Exception:  # noqa: BLE001
        pass


async def _count_captured(observer_number: str, n: int = 1) -> None:
    """Contador agregado de capturas por numero observado (telemetria)."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.hincrby(f"atlas:attendance:{observer_number}", "captured", n)
    except Exception:  # noqa: BLE001
        pass


async def capture_client_message(integration: dict, counterparty: str,
                                 key: Dict[str, Any], message: Dict[str, Any],
                                 data: Dict[str, Any], *, remote_jid: str = "",
                                 alternate_jid: str = "") -> bool:
    """Captura uma mensagem viva da conversa equipe<->segurado. Retorna True se
    armazenou (o chamador nao conta drop). Nunca lanca — falha = False."""
    try:
        from app.services.atlas.observer_intake import (
            _extract_content, _observer_number_of, _store_event_sync,
        )

        observer_number = _observer_number_of(integration)
        if not client_chat_allowed(
            integration,
            observer_number,
            remote_jid or f"{counterparty}@s.whatsapp.net",
            counterparty,
            alternate_jid,
        ):
            return False

        msg_type, text, interactive, media_meta = _extract_content(message)
        if msg_type == "unknown" and not text and not media_meta and not interactive:
            return False

        from_me = bool(key.get("fromMe"))
        ts = data.get("messageTimestamp")
        wa_ts = None
        if isinstance(ts, (int, float)) and ts > 0:
            wa_ts = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()

        record = {
            "company_id": str(integration.get("company_id") or ""),
            "observer_number": observer_number,
            "counterparty": counterparty,
            "insurer_key": None,
            "direction": "out" if from_me else "in",
            "msg_type": msg_type,
            "text": (text or None),
            "interactive": interactive or None,
            "media_meta": media_meta or None,
            "message_id": str(key.get("id") or "") or None,
            "wa_timestamp": wa_ts,
            "source": "live",
        }
        if media_meta:
            media_meta.update({
                "message_id": record["message_id"],
                "wa_timestamp": wa_ts,
                "company_id": record["company_id"],
                "enrichment_status": "pending",
            })
            record["media_meta"] = media_meta
        await asyncio.to_thread(_store_event_sync, record, TRANSCRIPTS_TABLE, SESSIONS_TABLE)
        if media_meta:
            try:
                from app.services.atlas.observer_media import enqueue_observer_media

                await enqueue_observer_media(integration, TRANSCRIPTS_TABLE, message, record)
            except Exception as exc:  # noqa: BLE001 - fila nunca invalida a captura
                logger.warning(
                    "[ESPELHO ATENDIMENTO] fila de mídia indisponível: %s",
                    type(exc).__name__,
                )
        await _count_captured(record["observer_number"])
        await _beat()
        logger.info(f"[ESPELHO ATENDIMENTO] capturado {record['direction']} tipo={msg_type}")
        return True
    except Exception as e:  # noqa: BLE001 — captura JAMAIS derruba o webhook
        logger.error(f"[ESPELHO ATENDIMENTO] captura falhou: {type(e).__name__}")
        return False


async def capture_channel_message(company_id: str, channel_number: str, counterparty: str,
                                  text: str, direction: str, message_id: Optional[str] = None,
                                  msg_type: str = "text") -> bool:
    """SPEC-045 — captura no NÚMERO DE ATENDIMENTO em MODO OBSERVAÇÃO
    (agente desligado; atendente humana responde pelo celular). Texto já vem
    normalizado do pipeline — sem parse waE2E. Mesmo cofre, mesma sessão de 2h."""
    try:
        from app.services.atlas.observer_intake import _digits, _store_event_sync

        clean = str(text or "").strip()
        if not clean:
            return False
        record = {
            "company_id": str(company_id or ""),
            # SPEC-063 Bloco H — o "número do observador" nunca foi um número.
            #
            # `channel_number` chega como o `identifier` da integração, e no
            # evolution-go isso é o NOME DA INSTÂNCIA (`ab-obs-04b5cdbc04-1`).
            # `_digits` picotava o nome e produzia `045041` — e quando o nome não
            # tinha dígito nenhum, caía no literal `"attendance-channel"`,
            # 📊 que já apareceu numa sessão de produção.
            #
            # A busca da sessão aberta e o índice de deduplicação usam
            # `(observer_number, message_id)` SEM `company_id`. Duas corretoras
            # caindo no mesmo valor teriam as conversas FUNDIDAS.
            #
            # Prefixar com a corretora garante unicidade sem depender da forma do
            # identifier. O valor deixa de fingir que é telefone — e passa a ser
            # o que sempre foi: a identidade do canal daquela corretora.
            "observer_number": f"{str(company_id or 'sem-empresa')[:8]}:"
                               f"{_digits(channel_number) or str(channel_number or 'canal')[:24]}",
            "counterparty": _digits(counterparty) or str(counterparty or "unknown"),
            "insurer_key": None,
            "direction": "out" if direction == "out" else "in",
            "msg_type": msg_type or "text",
            "text": clean,
            "interactive": None,
            "media_meta": None,
            "message_id": str(message_id or "") or None,
            "wa_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "live",
        }
        await asyncio.to_thread(_store_event_sync, record, TRANSCRIPTS_TABLE, SESSIONS_TABLE)
        await _count_captured(record["observer_number"])
        await _beat()
        return True
    except Exception as e:  # noqa: BLE001 — captura JAMAIS derruba o webhook
        logger.error(f"[ESPELHO ATENDIMENTO] captura de canal falhou: {type(e).__name__}")
        return False


_OBS_MODE_TTL_S = 60


async def attendance_agent_active(company_id: str) -> bool:
    """O agente de atendimento desta corretora está LIGADO?

    Pergunta positiva de propósito. `attendance_observation_mode` responde a
    negativa e devolve `False` em dois casos que não são a mesma coisa: agente
    ligado, e agente que nem existe. Para decidir se alguém vai responder, os
    dois casos precisam ser distinguidos — corretora sem agente provisionado não
    pode acabar respondendo por omissão.

    Só devolve `True` com prova: existe a linha e `is_active` é verdadeiro.
    Falha de leitura devolve `False` — não conseguir confirmar que o agente está
    ligado nunca pode virar permissão para falar.
    """
    try:
        from app.core.database import get_supabase_client

        def _query() -> bool:
            db = get_supabase_client()
            rows = (db.client.table("agents").select("id, is_active")
                    .eq("company_id", str(company_id))
                    .eq("agent_role", "attendance").limit(1).execute().data or [])
            return bool(rows) and rows[0].get("is_active") is True

        return await asyncio.to_thread(_query)
    except Exception as exc:  # noqa: BLE001
        logger.error("[Atendimento] não foi possível confirmar se o agente de "
                     "%s está ligado (%s) — assumindo DESLIGADO",
                     company_id, type(exc).__name__)
        return False


async def attendance_observation_mode(company_id: str) -> bool:
    """SPEC-045 — a corretora está em MODO OBSERVAÇÃO? True quando o agente de
    atendimento existe e está DESLIGADO (agents.is_active=false): o número
    continua pareado, a equipe humana atende e o sistema captura; o agente não
    responde ninguém. Cache Redis 60s (o gate roda no caminho quente).
    O OBSERVADOR NUNCA DESLIGA — este modo só governa a RESPOSTA do agente."""
    cache_key = f"attendance:obsmode:{company_id}"
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        cached = await r.get(cache_key)
        if cached is not None:
            val = cached.decode() if isinstance(cached, (bytes, bytearray)) else str(cached)
            return val == "1"
    except Exception:  # noqa: BLE001
        r = None

    def _query() -> bool:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        rows = (db.client.table("agents").select("id, is_active")
                .eq("company_id", str(company_id)).eq("agent_role", "attendance")
                .limit(1).execute().data or [])
        return bool(rows) and rows[0].get("is_active") is False

    try:
        obs = await asyncio.to_thread(_query)
    except Exception as exc:  # noqa: BLE001
        # FAIL-CLOSED no silêncio. Esta linha já devolveu `False` — "na dúvida,
        # responder" — e a dúvida era razoável quando o agente ligado era o
        # normal e a observação, a exceção.
        #
        # Hoje é o contrário. A corretora pareia o WhatsApp REAL dela para o
        # Observador trabalhar em silêncio por dias, com a equipe humana
        # atendendo os segurados como sempre. Nesse mundo, os dois erros
        # possíveis não têm o mesmo tamanho:
        #
        #   responder sem poder  → um segurado real recebe resposta de robô que
        #                          ninguém autorizou, no número da corretora.
        #                          Não se desfaz.
        #   calar sem precisar   → a atendente humana responde, como faz hoje.
        #                          Custa alguns minutos.
        #
        # Não conseguir LER o estado do agente não é permissão para falar.
        logger.error("[Observação] não foi possível ler o estado do agente (%s) "
                     "— assumindo SILÊNCIO para %s", type(exc).__name__, company_id)
        return True
    try:
        if r is not None:
            await r.set(cache_key, "1" if obs else "0", ex=_OBS_MODE_TTL_S)
    except Exception:  # noqa: BLE001
        pass
    return obs


# ------------------------------------------------------------------ #
# Retencao — purge diario do cru (o destilado e permanente)
# ------------------------------------------------------------------ #
def retention_days() -> int:
    try:
        return max(7, int(os.getenv("ATTENDANCE_RETENTION_DAYS", "90")))
    except ValueError:
        return 90


def purge_expired_sync(days: Optional[int] = None) -> int:
    """Apaga transcripts/sessoes com created_at alem da retencao.
    created_at (ingestao), NAO wa_timestamp — historico importado hoje
    conta 90 dias a partir de hoje."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days or retention_days())).isoformat()
    deleted = 0
    for table in (TRANSCRIPTS_TABLE, SESSIONS_TABLE):
        try:
            res = supabase.client.table(table).delete().lt("created_at", cutoff).execute()
            deleted += len(res.data or [])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ESPELHO ATENDIMENTO] purge {table} falhou: {type(e).__name__}")
    return deleted


async def check_attendance_purge() -> int:
    """Task periodica (APScheduler, 1x/dia via marcador Redis)."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        today = datetime.now(timezone.utc).date().isoformat()
        marker = await r.get("attendance:purge:last_run")
        marker = marker.decode() if isinstance(marker, (bytes, bytearray)) else marker
        if marker == today:
            return 0
        await r.set("attendance:purge:last_run", today, ex=3 * 86400)
    except Exception:  # noqa: BLE001
        pass
    try:
        deleted = await asyncio.to_thread(purge_expired_sync, None)
        if deleted:
            logger.info(f"[ESPELHO ATENDIMENTO] purge de retencao: {deleted} registros")
        await _beat(0)  # pulso sem acao: mostra o agente vivo na Central
        return deleted
    except Exception as e:  # noqa: BLE001 — nunca derruba o scheduler
        logger.warning(f"[ESPELHO ATENDIMENTO] purge falhou: {type(e).__name__}")
        return 0
