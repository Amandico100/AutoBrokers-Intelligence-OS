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

    @staticmethod
    def chave(escopo: str, phone: str) -> str:
        """A chave do buffer, com TENANT dentro — SPEC-063 Bloco H.

        Era `whatsapp_buffer:{phone}`. Só o telefone.

        O mesmo segurado pode falar com DUAS corretoras (ele tem seguro de auto
        numa e residencial na outra — é comum). Dentro da janela de 8 a 25
        segundos, as duas conversas caíam na MESMA chave: as mensagens eram
        concatenadas e `data["payload"] = payload` sobrescrevia o payload, então
        o conjunto todo era processado sob a integração da ÚLTIMA mensagem.

        A corretora B recebia a pergunta que o cliente fez para a corretora A, e
        respondia com o agente dela. Vazamento entre corretoras, no caminho mais
        quente do produto.

        `escopo` é o id da integração — o identificador mais específico que o
        webhook tem quando o buffer é escrito. Sem ele, cai em
        `sem-integracao`, que continua isolando por não ser o telefone sozinho.
        """
        esc = str(escopo or "").strip() or "sem-integracao"
        return f"whatsapp_buffer:{esc}:{phone}"

    async def add_message(
        self,
        phone: str,
        message: str,
        company_id: str,
        user_id: str,
        integration: Dict,
        payload: Dict,
        escopo: str = "",
    ) -> bool:
        """
        Add message to buffer (async).
        Returns True if this is the first message in buffer.
        """
        # O escopo vem do chamador; se não vier, o payload carrega o id da
        # integração desde a rota com token (SPEC-017 P1.2).
        # Cadeia do mais específico para o menos: id da integração (rotas com
        # token) → número conectado da corretora (rota legada, que resolve o
        # tenant por ele) → um rótulo fixo. O rótulo fixo NÃO isola, e é por
        # isso que a rota legada tem de morrer (H.2 desta mesma SPEC).
        escopo = str(
            escopo
            or (payload or {}).get("_integration_id")
            or (payload or {}).get("connectedPhone")
            or ""
        ).strip()
        key = self.chave(escopo, phone)
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

    async def should_process(self, key: str) -> bool:
        """
        Check if buffer should be processed (debounce or max wait reached).

        Recebe a CHAVE COMPLETA, não o telefone. O varredor já a tem em mãos —
        remontá-la a partir de `key.split(":")[-1]` era o que amarrava o buffer
        a um formato de chave de uma parte só.
        """
        phone = str(key).rsplit(":", 1)[-1]
        raw_data = await self.redis.get(key)

        if not raw_data:
            return False

        data = json.loads(raw_data)

        now = datetime.now()
        first_at = datetime.fromisoformat(data["first_at"])
        last_at = datetime.fromisoformat(data["last_at"])

        seconds_since_last = (now - last_at).total_seconds()
        seconds_since_first = (now - first_at).total_seconds()

        # PISO de 8s: o env do servidor pode ter valores antigos (3s) que quebram
        # a espera da rajada do cliente. Acima de 8s o env manda; abaixo, não.
        if seconds_since_last >= max(settings.BUFFER_DEBOUNCE_SECONDS, 8):
            logger.info(
                f"[BUFFER] Trigger DEBOUNCE for {phone} "
                f"({seconds_since_last:.1f}s idle, "
                f"{len(data['messages'])} msgs buffered)"
            )
            return True

        if seconds_since_first >= max(settings.BUFFER_MAX_WAIT_SECONDS, 25):
            logger.info(
                f"[BUFFER] Trigger MAX_WAIT for {phone} "
                f"({seconds_since_first:.1f}s duration, "
                f"{len(data['messages'])} msgs buffered)"
            )
            return True

        return False

    async def get_and_clear_buffer(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Atomically get buffer and delete from Redis (async).
        Pipeline continua atômico em async. Recebe a CHAVE COMPLETA.
        """
        phone = str(key).rsplit(":", 1)[-1]

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
