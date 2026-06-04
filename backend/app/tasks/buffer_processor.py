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
