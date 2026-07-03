"""
Serviço WhatsApp (shim de compatibilidade) — 39A4.1.

Delega para o ZApiProvider (camada oficial de provider). Mantém a assinatura
send_message/send_audio/send_image usada por backend/app/api/webhook.py.

Segurança: nenhum log de URL/token/Client-Token aqui — toda a chamada Z-API
(e o mascaramento de telefone) vive em app/services/whatsapp/zapi_provider.py.
"""
import logging
from typing import Any, Dict, Optional

from app.services.whatsapp.zapi_provider import get_zapi_provider

logger = logging.getLogger(__name__)


class WhatsappService:
    """Compat: delega o envio Z-API para o ZApiProvider."""

    def __init__(self):
        logger.info("WhatsApp service initialized (delegates to ZApiProvider)")

    def send_message(self, to_number: str, text: str, integration: Dict[str, Any]) -> bool:
        """Envia texto. Retorna True em sucesso; levanta exceção em falha (contrato legado).

        SPEC-017 P1.2: provider != z-api envia pelo seam multi-provider
        (Evolution/uazapi); z-api mantém o caminho legado.
        S17-9: resposta longa vira balões curtos (humanização).
        """
        from app.services.whatsapp.balloons import split_whatsapp_balloons

        balloons = split_whatsapp_balloons(text) or [str(text or "")]
        provider_label = str((integration or {}).get("provider") or "z-api").strip().lower()

        if provider_label not in ("z-api", "zapi", ""):
            from app.services.whatsapp.registry import resolve_provider

            provider = resolve_provider(integration)
            for balloon in balloons:
                result = provider.send_text(to_number, balloon)
                if not getattr(result, "success", False):
                    raise Exception("Failed to send WhatsApp message")
            return True

        for balloon in balloons:
            result = get_zapi_provider().send_text(to_number, balloon, integration)
            if not result.success:
                raise Exception("Failed to send WhatsApp message")
        return True

    def send_audio(self, to_number: str, audio_url: str, integration: Dict[str, Any]) -> bool:
        return get_zapi_provider().send_audio(to_number, audio_url, integration).success

    def send_image(
        self, to_number: str, image_url: str, caption: str, integration: Dict[str, Any]
    ) -> bool:
        return get_zapi_provider().send_image(to_number, image_url, caption, integration).success


# Singleton instance
_whatsapp_service: Optional[WhatsappService] = None


def get_whatsapp_service() -> WhatsappService:
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsappService()
    return _whatsapp_service
