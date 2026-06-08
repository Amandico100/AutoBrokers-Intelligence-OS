"""
Criptografia de segredos de integração (token/client_token) — reuso do EncryptionService.

- Armazenamento: cifrar antes de gravar (Fernet/AES, mesma chave ENCRYPTION_KEY do runtime).
- Runtime: descriptografar em memória apenas, na hora de usar.
- Compatibilidade: se um valor antigo não for cifrado válido, trata como PLAINTEXT legado
  (com warning, SEM logar o valor). Hoje o banco está sem integrações, então o caminho
  normal é tudo cifrado daqui para frente.
"""
import logging
from typing import Any, Dict, Optional

from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)

# Campos sensíveis em public.integrations.
SECRET_FIELDS = ("token", "client_token")


def encrypt_integration_secret(value: Optional[str]) -> Optional[str]:
    """Cifra um segredo. Retorna o próprio valor se vazio/None."""
    if not value:
        return value
    return get_encryption_service().encrypt(value)


def decrypt_integration_secret(value: Optional[str]) -> Optional[str]:
    """
    Descriptografa um segredo. Se não for ciphertext válido, assume PLAINTEXT legado.
    NUNCA loga o valor.
    """
    if not value:
        return value
    try:
        return get_encryption_service().decrypt(value)
    except Exception:
        logger.warning(
            "[INTEGRATION SECRETS] valor não descriptografável; tratando como plaintext legado "
            "(valor NÃO é logado). Recomenda-se recadastrar pela camada segura."
        )
        return value


def prepare_integration_for_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    """Cópia com token/client_token CIFRADOS, pronta para gravar no banco."""
    out = dict(data)
    for field in SECRET_FIELDS:
        if out.get(field):
            out[field] = encrypt_integration_secret(out[field])
    return out


def prepare_integration_for_runtime(
    data: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Cópia com token/client_token DESCRIPTOGRAFADOS em memória, pronta para uso (envio)."""
    if not data:
        return data
    out = dict(data)
    for field in SECRET_FIELDS:
        if out.get(field):
            out[field] = decrypt_integration_secret(out[field])
    return out
