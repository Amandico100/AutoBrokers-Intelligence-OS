"""
ZApiProvider — primeiro provider de WhatsApp (Z-API).

Segurança:
- DRY_RUN simula envio (sem HTTP).
- Telefone sempre mascarado nos logs.
- NUNCA loga a URL (contém token), o token, o Client-Token ou o corpo de resposta.
"""
import logging
from typing import Any, Dict, Optional

import requests

from app.core.config import settings

from .provider import WhatsAppProvider
from .types import SendResult

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.z-api.io/instances"


def _safe_phone(number: Optional[str]) -> str:
    return f"...{str(number)[-4:]}" if number else "Unknown"


class ZApiProvider(WhatsAppProvider):
    """Provider Z-API (REST)."""

    provider_name = "z-api"

    def _post(
        self,
        endpoint: str,
        to_number: str,
        payload: Dict[str, Any],
        integration: Dict[str, Any],
        force_dry_run: bool = False,
    ) -> SendResult:
        base_url = integration.get("base_url") or DEFAULT_BASE_URL
        instance_id = integration.get("instance_id")
        token = integration.get("token")
        safe = _safe_phone(to_number)

        if not instance_id or not token:
            logger.error(f"[WHATSAPP][z-api] Missing instance_id/token for {safe}")
            return SendResult(success=False, provider=self.provider_name, error="missing_instance_or_token")

        # URL contém token — NUNCA logar.
        url = f"{base_url}/{instance_id}/token/{token}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if integration.get("client_token"):
            headers["Client-Token"] = integration["client_token"]

        # 🧪 DRY_RUN (global OU forçado pela rota): simula envio sem chamar a Z-API.
        if settings.DRY_RUN or force_dry_run:
            logger.info(f"[WHATSAPP][z-api] 🧪 DRY_RUN: simulating {endpoint} to {safe}")
            return SendResult(success=True, provider=self.provider_name, dry_run=True)

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                # Não logar response.text (pode conter eco do payload/identificadores).
                logger.error(f"[WHATSAPP][z-api] HTTP {response.status_code} on {endpoint} to {safe}")
                return SendResult(
                    success=False, provider=self.provider_name, error=f"http_{response.status_code}"
                )

            message_id: Optional[str] = None
            try:
                data = response.json()
                if isinstance(data, dict):
                    message_id = data.get("messageId") or data.get("id") or data.get("zaapId")
            except Exception:
                message_id = None

            logger.info(f"[WHATSAPP][z-api] ✅ {endpoint} sent to {safe}")
            return SendResult(success=True, provider=self.provider_name, message_id=message_id)

        except requests.exceptions.RequestException as e:
            # type(e).__name__ evita vazar URL/credencial em mensagens de erro.
            logger.error(f"[WHATSAPP][z-api] request error on {endpoint} to {safe}: {type(e).__name__}")
            return SendResult(success=False, provider=self.provider_name, error="request_error")

    def send_text(
        self, to_number: str, text: str, integration: Dict[str, Any], force_dry_run: bool = False
    ) -> SendResult:
        return self._post(
            "send-text", to_number, {"phone": to_number, "message": text}, integration, force_dry_run
        )

    def send_audio(
        self, to_number: str, audio_url: str, integration: Dict[str, Any], force_dry_run: bool = False
    ) -> SendResult:
        return self._post(
            "send-audio", to_number, {"phone": to_number, "audio": audio_url}, integration, force_dry_run
        )

    def send_image(
        self,
        to_number: str,
        image_url: str,
        caption: str,
        integration: Dict[str, Any],
        force_dry_run: bool = False,
    ) -> SendResult:
        return self._post(
            "send-image",
            to_number,
            {"phone": to_number, "image": image_url, "caption": caption or ""},
            integration,
            force_dry_run,
        )


_zapi_provider: Optional[ZApiProvider] = None


def get_zapi_provider() -> ZApiProvider:
    global _zapi_provider
    if _zapi_provider is None:
        _zapi_provider = ZApiProvider()
    return _zapi_provider
