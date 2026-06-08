"""Interface base de provider de WhatsApp (provider-agnostic)."""
from abc import ABC, abstractmethod
from typing import Any, Dict

from .types import SendResult


class WhatsAppProvider(ABC):
    """
    Interface oficial de provider de WhatsApp.

    A integração runtime (dict) traz token/client_token JÁ DESCRIPTOGRAFADOS em memória
    (ver integration_secrets.prepare_integration_for_runtime). Providers nunca logam segredo.
    """

    provider_name: str = "base"

    @abstractmethod
    def send_text(self, to_number: str, text: str, integration: Dict[str, Any]) -> SendResult:
        ...

    @abstractmethod
    def send_audio(self, to_number: str, audio_url: str, integration: Dict[str, Any]) -> SendResult:
        ...

    @abstractmethod
    def send_image(
        self, to_number: str, image_url: str, caption: str, integration: Dict[str, Any]
    ) -> SendResult:
        ...

    def validate_config(self, integration: Dict[str, Any]) -> bool:
        """Config mínima para enviar (sem expor valores)."""
        return bool(integration.get("instance_id") and integration.get("token"))


# Nota: EvolutionProvider é fase futura — implementar atrás desta mesma interface.
