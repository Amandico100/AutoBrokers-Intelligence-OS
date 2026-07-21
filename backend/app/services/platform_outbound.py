"""SPEC-045 — Envios de PLATAFORMA a segurados com guardas anti-conflito.

O medo do founder virou três regras determinísticas (custo zero de LLM):

1. FILA DE CORTESIA (outbound): antes de um auxiliar enviar (cobrança,
   campanha, aviso) a um cliente, checa se ele está em ATENDIMENTO ativo
   (acionamento vivo no Redis OU conversa recente aberta). Ocupado = o envio
   espera na fila (retry via scheduler) — nunca atropela o atendimento.
2. REGISTRO (platform_sends): todo envio de plataforma fica registrado.
3. NOTA DE CONTEXTO (inbound): quando o cliente responde, o atendente recebe
   "há X dias este cliente recebeu {cobrança da parcela Y}" — responde sabendo
   do que se trata, sem confusão.

Canal: get_platform_whatsapp_integration (o mesmo caminho do Vigia) — número
dedicado de auxiliares quando existir (purpose=auxiliary), senão o do
atendimento. Corretora pequena com 1 número = suportada com segurança.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_QUEUE_KEY = "platform_queue:{company_id}"
_BUSY_WINDOW_H = 2          # conversa com atividade nas últimas N horas = ocupado
_RETRY_MIN_S = 2 * 3600     # re-tenta a partir de 2h
_MAX_ATTEMPTS = 12          # ~24h de tentativas; depois expira com atividade


def _digits(v: Any) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _phone_variants(phone: str) -> set:
    from app.services.atlas.observer_intake import _br_variants

    return _br_variants(phone)


async def client_busy(company_id: str, phone: str) -> Optional[str]:
    """Cliente em atendimento? Retorna o MOTIVO ('acionamento'|'conversa')
    ou None. Determinístico: Redis (dispatch ativo) + conversations recentes."""
    variants = _phone_variants(phone)
    if not variants:
        return None
    try:  # 1) acionamento vivo com este cliente
        from app.services.dispatch_router import list_active_dispatches

        for s in await list_active_dispatches(str(company_id)):
            if _digits(s.get("client_phone")) in variants and \
                    str(s.get("state") or "") not in ("test_aborted", "insurer_closed"):
                return "acionamento"
    except Exception:  # noqa: BLE001
        pass
    try:  # 2) conversa de atendimento aberta com atividade recente
        from app.core.database import get_supabase_client

        since = (datetime.now(timezone.utc) - timedelta(hours=_BUSY_WINDOW_H)).isoformat()

        def _q() -> list:
            db = get_supabase_client()
            return (db.client.table("conversations")
                    .select("id, user_phone, status, last_message_at")
                    .eq("company_id", str(company_id)).eq("channel", "whatsapp")
                    .neq("status", "closed").gte("last_message_at", since)
                    .limit(50).execute().data or [])

        for c in await asyncio.to_thread(_q):
            if _digits(c.get("user_phone")) in variants:
                return "conversa"
    except Exception:  # noqa: BLE001
        pass
    return None


def _record_send_sync(company_id: str, phone: str, kind: str, summary: str) -> None:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    db.client.table("platform_sends").insert({
        "company_id": str(company_id), "phone": _digits(phone),
        "kind": str(kind or "other")[:40], "summary": str(summary or "")[:300],
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }).execute()


async def record_platform_send(company_id: str, phone: str, kind: str, summary: str) -> None:
    """Registra um envio de plataforma (para a nota de contexto do atendente)."""
    try:
        await asyncio.to_thread(_record_send_sync, company_id, phone, kind, summary)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[PLATFORM SEND] registro falhou: {type(e).__name__}")


async def send_to_client_guarded(company_id: str, phone: str, text: str,
                                 kind: str = "other", summary: str = "") -> Dict[str, Any]:
    """Envio guardado: cliente ocupado → FILA (retry); livre → envia e registra."""
    reason = await client_busy(company_id, phone)
    if reason:
        try:
            from app.core.redis import get_async_redis_client

            r = await get_async_redis_client()
            entry = {"phone": _digits(phone), "text": str(text), "kind": kind,
                     "summary": summary, "attempts": 0,
                     "next_try": (datetime.now(timezone.utc) + timedelta(seconds=_RETRY_MIN_S)).isoformat()}
            await r.rpush(_QUEUE_KEY.format(company_id=company_id), json.dumps(entry, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PLATFORM SEND] fila falhou: {type(e).__name__}")
            return {"ok": False, "queued": False, "reason": reason}
        try:
            from app.services.activity_log import log_activity

            await log_activity(str(company_id), "atendimentos",
                               "Envio adiado — cliente em atendimento",
                               f"{kind}: aguardando o atendimento terminar (fila de cortesia).")
        except Exception:  # noqa: BLE001
            pass
        logger.info(f"[PLATFORM SEND] adiado ({reason}) company={company_id}")
        return {"ok": True, "queued": True, "reason": reason}

    try:
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        integration = get_integration_service().get_platform_whatsapp_integration(str(company_id))
        if not integration:
            return {"ok": False, "queued": False, "reason": "sem_canal"}
        ok = await asyncio.to_thread(get_whatsapp_service().send_message, _digits(phone), text, integration)
        if ok:
            await record_platform_send(company_id, phone, kind, summary or text[:120])
        return {"ok": bool(ok), "queued": False, "reason": None}
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM SEND] envio falhou: {type(e).__name__}")
        return {"ok": False, "queued": False, "reason": "erro_envio"}


async def check_platform_queue() -> int:
    """Task periódica: drena as filas de cortesia (envios adiados). Best-effort;
    entrada vence após _MAX_ATTEMPTS (registra em Atividades e descarta)."""
    sent = 0
    try:
        from app.core.database import get_supabase_client
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()

        def _companies() -> list:
            db = get_supabase_client()
            return [row["id"] for row in (db.client.table("companies").select("id")
                                          .limit(200).execute().data or [])]

        now = datetime.now(timezone.utc)
        for company_id in await asyncio.to_thread(_companies):
            key = _QUEUE_KEY.format(company_id=company_id)
            try:
                size = await r.llen(key)
            except Exception:  # noqa: BLE001
                continue
            for _ in range(min(int(size or 0), 20)):
                raw = await r.lpop(key)
                if not raw:
                    break
                try:
                    entry = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                except Exception:  # noqa: BLE001
                    continue
                try:
                    if str(entry.get("next_try") or "") > now.isoformat():
                        await r.rpush(key, json.dumps(entry, ensure_ascii=False))
                        continue
                    if int(entry.get("attempts") or 0) >= _MAX_ATTEMPTS:
                        from app.services.activity_log import log_activity

                        await log_activity(str(company_id), "atendimentos",
                                           "Envio da fila expirou",
                                           f"{entry.get('kind')}: não foi possível entregar em 24h.")
                        continue
                    if await client_busy(str(company_id), entry.get("phone") or ""):
                        entry["attempts"] = int(entry.get("attempts") or 0) + 1
                        entry["next_try"] = (now + timedelta(seconds=_RETRY_MIN_S)).isoformat()
                        await r.rpush(key, json.dumps(entry, ensure_ascii=False))
                        continue
                    res = await send_to_client_guarded(str(company_id), entry.get("phone") or "",
                                                       entry.get("text") or "", entry.get("kind") or "other",
                                                       entry.get("summary") or "")
                    if res.get("ok") and not res.get("queued"):
                        sent += 1
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[PLATFORM QUEUE] entrada falhou: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM QUEUE] check falhou: {type(e).__name__}")
    return sent


async def context_note_for(company_id: str, phone: str) -> Optional[str]:
    """Nota de contexto p/ o atendente: envios de plataforma recentes (7d) a
    este cliente. None quando não há nada — zero ruído no prompt."""
    try:
        from app.core.database import get_supabase_client

        variants = _phone_variants(phone)
        if not variants:
            return None
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        def _q() -> list:
            db = get_supabase_client()
            return (db.client.table("platform_sends")
                    .select("phone, kind, summary, sent_at").eq("company_id", str(company_id))
                    .gte("sent_at", since).order("sent_at", desc=True).limit(30).execute().data or [])

        hits = [x for x in await asyncio.to_thread(_q) if _digits(x.get("phone")) in variants]
        if not hits:
            return None
        parts = []
        for h in hits[:3]:
            when = str(h.get("sent_at") or "")[:10]
            parts.append(f"{h.get('summary') or h.get('kind')} (em {when})")
        return ("[CONTEXTO DA PLATAFORMA] Este cliente recebeu recentemente da corretora: "
                + "; ".join(parts) + ". Se a mensagem dele for sobre isso, responda com esse contexto.")
    except Exception:  # noqa: BLE001
        return None
