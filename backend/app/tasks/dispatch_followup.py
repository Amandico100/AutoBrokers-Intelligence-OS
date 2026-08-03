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
            integration = integrations.get_platform_whatsapp_integration(company_id) if company_id else None
            if not integration:
                continue
            try:
                wa.send_message(client_phone, todo[1], integration)
                session[todo[0]] = True

                # A PERGUNTA PASSA A EXISTIR NA CONVERSA.
                #
                # 📊 Ate 03/08 esta mensagem saia e nao deixava rastro nenhum: o
                # cliente respondia "nao chegou ainda" e caia no agente de
                # atendimento, que **nao sabia que uma pergunta tinha sido
                # feita**. A resposta chegava sem contexto e o ciclo nunca
                # fechava.
                #
                # Nao e preciso um agente novo para ler a resposta: basta o
                # agente da entrada SABER o que foi perguntado. `platform_sends`
                # e exatamente a tabela que alimenta a nota de contexto dele.
                try:
                    from app.services.platform_outbound import record_platform_send

                    await record_platform_send(
                        company_id, client_phone,
                        "acionamento_followup" if todo[0] == "followup_sent" else "acionamento_encerramento",
                        todo[1][:180])
                except Exception:  # noqa: BLE001
                    logger.warning("[FOLLOWUP] rastro do envio nao registrado")

                # E entra no transcript, como o Vigia ja faz — sem isto o
                # Espelho, a linha do tempo e o dossie omitem o que foi dito.
                session.setdefault("transcript", []).append(
                    {"direction": "out", "text": f"[AO CLIENTE] {todo[1]}",
                     "at": datetime.now(timezone.utc).isoformat(),
                     "step": todo[0]})

                # E O ENCERRAMENTO PASSA A ENCERRAR.
                #
                # 📊 `closing_sent` so mandava texto: a sessao ficava viva em
                # `monitoring` ate o TTL de 24h. Nada marcava resolvido, nada
                # liberava a corretora, e o Vigia e cego a `monitoring` — uma
                # sessao que silencia para sempre nao era vista por ninguem.
                if todo[0] == "closing_sent":
                    session["state"] = "resolvido"
                    session["resolved_at"] = datetime.now(timezone.utc).isoformat()

                await save_active_dispatch(company_id, insurer_phone, session)
                if todo[0] == "closing_sent":
                    try:
                        from app.services.dispatch_router import clear_active_dispatch

                        await clear_active_dispatch(company_id, insurer_phone)
                    except Exception:  # noqa: BLE001
                        logger.warning("[FOLLOWUP] sessao encerrada nao foi liberada")
                sent += 1
                logger.info(f"[FOLLOWUP] {todo[0]} enviado case={session.get('case_id')}")
                # SPEC-050 (auditoria): a ação vira linha no feed de Atividades.
                try:
                    from app.services.activity_log import log_activity

                    await log_activity(company_id, "acionamentos",
                                       "Cliente acompanhado após o acionamento"
                                       if todo[0] == "followup_sent" else "Atendimento encerrado com carinho",
                                       "Conferimos com o cliente se o prestador chegou e se está tudo certo.")
                except Exception:  # noqa: BLE001
                    pass
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
