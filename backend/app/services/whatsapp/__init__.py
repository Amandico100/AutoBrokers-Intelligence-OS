"""
WhatsApp provider layer (Caminho C — 39A4.1).

Fornece:
- WhatsAppProvider: interface de provider.
- ZApiProvider: primeiro provider (Z-API), com DRY_RUN e logs sem segredo.
- integration_secrets: criptografia/decriptação de token/client_token (reuso do EncryptionService).

NÃO envia mensagem real fora do fluxo existente. NÃO loga token/URL com token.
"""
from .provider import WhatsAppProvider
from .types import SendResult
from .zapi_provider import ZApiProvider, get_zapi_provider
from .integration_secrets import (
    decrypt_integration_secret,
    encrypt_integration_secret,
    prepare_integration_for_runtime,
    prepare_integration_for_storage,
)

__all__ = [
    "WhatsAppProvider",
    "SendResult",
    "ZApiProvider",
    "get_zapi_provider",
    "encrypt_integration_secret",
    "decrypt_integration_secret",
    "prepare_integration_for_storage",
    "prepare_integration_for_runtime",
]
