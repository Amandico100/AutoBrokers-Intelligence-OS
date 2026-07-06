"""Cofre Fernet do smith-api para credenciais de portal (SPEC-020).

Cifra a senha do portal antes de gravar em portal_accounts. Usa PORTAL_VAULT_KEY
— a MESMA chave do portal-worker (que decifra na hora de logar no portal). Senha
NUNCA em claro/log/LLM. Multi-tenant: a credencial é escopada por company_id na
tabela; este módulo só cifra/decifra e mascara para exibição.
"""
from __future__ import annotations

import os


def _fernet():
    from cryptography.fernet import Fernet

    key = os.getenv("PORTAL_VAULT_KEY", "")
    if not key:
        raise RuntimeError("PORTAL_VAULT_KEY ausente — configure no smith-api e no portal-worker")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt((plaintext or "").encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt((token or "").encode()).decode()


def mask(value: str) -> str:
    """Máscara para exibir username/login com segurança (nunca a senha)."""
    v = str(value or "")
    if not v:
        return ""
    if len(v) <= 3:
        return v[0] + "••"
    return v[:2] + "•" * max(3, len(v) - 4) + v[-2:]
