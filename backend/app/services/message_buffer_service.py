"""
Message Buffer Service for WhatsApp message aggregation.

Implements debounce pattern to combine consecutive user messages
before processing with LLM, reducing API calls and improving response coherence.

ASYNC VERSION: All Redis operations are non-blocking.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.redis import get_async_redis_client

logger = logging.getLogger(__name__)


class MessageBufferService:
    """
    Manages message buffering in Redis with debounce logic (async).
    """

    def __init__(self, redis_client):
        """Recebe o cliente async já inicializado."""
        self.redis = redis_client

    @classmethod
    async def create(cls) -> "MessageBufferService":
        """Factory method async para criar instância com Redis conectado."""
        redis_client = await get_async_redis_client()
        return cls(redis_client)

    def _get_key(self, phone: str) -> str:
        """Generate Redis key for phone number."""
        return f"whatsapp_buffer:{phone}"

    async def add_message(
        self,
        phone: str,
        message: str,
        company_id: str,
        user_id: str,
        integration: Dict,
        payload: Dict,
    ) -> bool:
        """
        Add message to buffer (async).
        Returns True if this is the first message in buffer.
        """
        key = self._get_key(phone)
        now_iso = datetime.now().isoformat()

        raw_data = await self.redis.get(key)

        if raw_data:
            data = json.loads(raw_data)
            data["messages"].append(message)
            data["last_at"] = now_iso
            data["payload"] = payload
            is_first = False
        else:
            data = {
                "messages": [message],
                "first_at": now_iso,
                "last_at": now_iso,
                "company_id": company_id,
                "user_id": user_id,
                "integration": integration,
                "payload": payload,
            }
            is_first = True

        await self.redis.setex(key, settings.BUFFER_TTL_SECONDS, json.dumps(data))

        msg_count = len(data["messages"])
        logger.debug(f"[BUFFER] Added message for {phone}. Count: {msg_count}")
        return is_first

    async def should_process(self, phone: str) -> bool:
        """
        Check if buffer should be processed (debounce or max wait reached).
        Lógica idêntica à sync, só com await no Redis.
        """
        key = self._get_key(phone)
        raw_data = await self.redis.get(key)

        if not raw_data:
            return False

        data = json.loads(raw_data)

        now = datetime.now()
        first_at = datetime.fromisoformat(data["first_at"])
        last_at = datetime.fromisoformat(data["last_at"])

        seconds_since_last = (now - last_at).total_seconds()
        seconds_since_first = (now - first_at).total_seconds()

        if seconds_since_last >= settings.BUFFER_DEBOUNCE_SECONDS:
            logger.info(
                f"[BUFFER] Trigger DEBOUNCE for {phone} "
                f"({seconds_since_last:.1f}s idle, "
                f"{len(data['messages'])} msgs buffered)"
            )
            return True

        if seconds_since_first >= settings.BUFFER_MAX_WAIT_SECONDS:
            logger.info(
                f"[BUFFER] Trigger MAX_WAIT for {phone} "
                f"({seconds_since_first:.1f}s duration, "
                f"{len(data['messages'])} msgs buffered)"
            )
            return True

        return False

    async def get_and_clear_buffer(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Atomically get buffer and delete from Redis (async).
        Pipeline continua atômico em async.
        """
        key = self._get_key(phone)

        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        raw_data = results[0]

        if not raw_data:
            return None

        buffer_data = json.loads(raw_data)
        logger.info(
            f"[BUFFER] Cleared buffer for {phone}. "
            f"Messages: {len(buffer_data['messages'])}"
        )
        return buffer_data

    def get_combined_message(self, buffer: Dict) -> str:
        """
        Combine buffered messages into single text.
        NÃO precisa ser async (sem I/O).
        """
        messages = buffer.get("messages", [])
        combined = "\n".join(messages)
        return combined


# Singleton será inicializado no startup do FastAPI
# NÃO instanciar aqui porque precisa de await
_buffer_service_instance: Optional[MessageBufferService] = None


async def get_message_buffer_service() -> MessageBufferService:
    """Retorna singleton do MessageBufferService (lazy init async)."""
    global _buffer_service_instance
    if _buffer_service_instance is None:
        _buffer_service_instance = await MessageBufferService.create()
    return _buffer_service_instance
