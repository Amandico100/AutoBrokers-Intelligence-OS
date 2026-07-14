"""Follow-up proativo pós-acionamento (SPEC-031 Faixa 6).

Sessões em MONITORING ganham timers quando o protocolo é capturado:
- followup_at (~45min): "o prestador já chegou? tá tudo certo?"
- closing_at  (~3h):    encerramento carinhoso do atendimento.

Roda no MESMO APScheduler do buffer (job a cada 60s). Nunca reenvia (flags na
sessão); nunca fala com a seguradora — só com o CLIENTE, pela integração da
corretora. Falhas nunca derrubam o scheduler.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

FOLLOWUP_TEXT = (
    "Oi! Passando pra saber: o prestador já chegou aí? Tá tudo certo? 🙂\n"
    "Se ainda não chegou ou algo estiver estranho, me fala que eu resolvo."
)
CLOSING_TEXT = (
    "Espero que tenha dado tudo certo com o serviço! 🙂\n"
    "Qualquer coisa que precisar, é só me chamar por aqui — estamos sempre à disposição."
)


def _due(ts: str) -> bool:
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= when
    except Exception:  # noqa: BLE001
        return False


async def check_dispatch_followups() -> int:
    """Varre as sessões de dispatch em monitoring e envia follow-ups vencidos."""
    sent = 0
    try:
        from app.core.redis import get_async_redis_client
        from app.services.dispatch_router import save_active_dispatch
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        redis = await get_async_redis_client()
        wa = get_whatsapp_service()
        integrations = get_integration_service()

        async for key in redis.scan_iter(match="dispatch:active:*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            raw = await redis.get(k)
            if not raw:
                continue
            try:
                session = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                continue
            if str(session.get("state") or "") != "monitoring":
                continue
            client_phone = str(session.get("client_phone") or "").strip()
            if not client_phone:
                continue
            todo = None
            if not session.get("followup_sent") and session.get("followup_at") and _due(session["followup_at"]):
                todo = ("followup_sent", FOLLOWUP_TEXT)
            elif not session.get("closing_sent") and session.get("closing_at") and _due(session["closing_at"]):
                todo = ("closing_sent", CLOSING_TEXT)
            if not todo:
                continue
            # dispatch:active:{company}:{insurer_phone}
            parts = k.split(":")
            company_id = parts[2] if len(parts) >= 4 else ""
            insurer_phone = parts[3] if len(parts) >= 4 else ""
            integration = integrations.get_whatsapp_integration(company_id) if company_id else None
            if not integration:
                continue
            try:
                wa.send_message(client_phone, todo[1], integration)
                session[todo[0]] = True
                await save_active_dispatch(company_id, insurer_phone, session)
                sent += 1
                logger.info(f"[FOLLOWUP] {todo[0]} enviado case={session.get('case_id')}")
            except Exception as e:  # noqa: BLE001
                logger.error(f"[FOLLOWUP] envio falhou: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001 — nunca derruba o scheduler
        logger.error(f"[FOLLOWUP] varredura falhou: {type(e).__name__}")
    try:
        from app.core.heartbeat import beat

        await beat("followup", sent)
    except Exception:  # noqa: BLE001
        pass
    return sent
