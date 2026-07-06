"""Cofre Fernet do portal-worker: cifra storage_state e senhas de portal.
Chave em PORTAL_VAULT_KEY (env, NUNCA no repo/log/LLM). SPEC-020 regra dura."""
from __future__ import annotations

import os


def _fernet():
    from cryptography.fernet import Fernet

    key = os.getenv("PORTAL_VAULT_KEY", "")
    if not key:
        raise RuntimeError("PORTAL_VAULT_KEY ausente — configure no serviço portal-worker")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt((plaintext or "").encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt((token or "").encode()).decode()
