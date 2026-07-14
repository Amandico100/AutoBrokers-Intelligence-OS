"""
Buffer Processor - Periodic task to check and process WhatsApp message buffers.
ASYNC VERSION: Redis operations are non-blocking.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.redis import get_async_redis_client
from app.services.message_buffer_service import get_message_buffer_service

logger = logging.getLogger(__name__)

logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

scheduler = AsyncIOScheduler()


async def check_buffers():
    """
    Periodic job - scans Redis for ready buffers (async, non-blocking).
    """
    redis = await get_async_redis_client()
    buffer_service = await get_message_buffer_service()

    from app.api.webhook import process_whatsapp_message_background

    try:
        cursor = 0
        processed_count = 0

        while True:
            cursor, keys = await redis.scan(
                cursor=cursor, match="whatsapp_buffer:*", count=100
            )

            for key in keys:
                phone = key.split(":")[-1]

                if await buffer_service.should_process(phone):
                    buffer = await buffer_service.get_and_clear_buffer(phone)

                    if buffer:
                        combined_msg = buffer_service.get_combined_message(buffer)
                        msg_count = len(buffer["messages"])

                        logger.info(
                            f"[BUFFER] Processing buffer for {phone}: {msg_count} messages"
                        )

                        await process_whatsapp_message_background(
                            payload_dict=buffer["payload"],
                            combined_message=combined_msg,
                            buffered_messages=list(buffer.get("messages") or []),
                        )

                        logger.info(
                            f"[BUFFER] ✅ Processed {phone}: combined {msg_count} msgs"
                        )
                        processed_count += 1

            if cursor == 0:
                break

    except Exception as e:
        logger.error(f"[BUFFER] ❌ Error in check_buffers: {e}", exc_info=True)


def start_buffer_scheduler():
    """Start the APScheduler for buffer processing."""
    if not scheduler.running:
        scheduler.add_job(
            check_buffers,
            "interval",
            seconds=1,
            id="whatsapp_buffer_check",
            max_instances=10,
        )
        # Follow-up pós-acionamento (SPEC-031 Faixa 6): "o guincho chegou?" e
        # encerramento carinhoso — varre sessões monitoring a cada 60s.
        from app.tasks.dispatch_followup import check_dispatch_followups

        scheduler.add_job(
            check_dispatch_followups,
            "interval",
            seconds=60,
            id="dispatch_followup_check",
            max_instances=1,
        )
        # VIGIA + SENTINELA (SPEC-034 Onda 1): vigilância de desfecho e
        # recuperação de travas nos acionamentos — varredura a cada 20s.
        from app.tasks.dispatch_watchdog import check_dispatch_watchdog

        scheduler.add_job(
            check_dispatch_watchdog,
            "interval",
            seconds=20,
            id="dispatch_watchdog_check",
            max_instances=1,
        )
        # GARIMPO (SPEC-034 Onda 3): minera desejos/dores dos corretores 1x/dia
        # (marcador em Redis; captura determinística, custo zero de LLM).
        from app.services.broker_insights import check_garimpo

        scheduler.add_job(
            check_garimpo,
            "interval",
            seconds=3600,
            id="garimpo_check",
            max_instances=1,
        )
        # AUDITOR + overlays do ALFAIATE (SPEC-034 Onda 4): scorecards 1x/dia
        # (marcador Redis) e cache de overlays atualizado a cada varredura.
        from app.services.conversation_auditor import check_auditor

        scheduler.add_job(
            check_auditor,
            "interval",
            seconds=1800,
            id="auditor_check",
            max_instances=1,
        )
        # IA DE SUGESTÕES (SPEC-034 Onda 5): auxiliar global ON por padrão —
        # 1 msg/semana por corretora (segunda, horário comercial, marcador Redis).
        from app.services.proactive_suggestions import check_suggestions

        scheduler.add_job(
            check_suggestions,
            "interval",
            seconds=1800,
            id="sugestoes_check",
            max_instances=1,
        )
        scheduler.start()
        logger.info("✅ [BUFFER SCHEDULER] Started (interval: 1s, max_instances: 10)")
    else:
        logger.warning("[BUFFER SCHEDULER] Already running")


def shutdown_buffer_scheduler():
    """Shutdown the APScheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("🛑 [BUFFER SCHEDULER] Stopped")
    else:
        logger.warning("[BUFFER SCHEDULER] Not running")
