"""Cofre Fernet do portal-worker: cifra storage_state e senhas de portal.
Chave em PORTAL_VAULT_KEY (env, NUNCA no repo/log/LLM). SPEC-020 regra dura.

🔑 Duas chaves (SPEC-129-B U5, P-182): `PORTAL_VAULT_KEY` é a ATUAL — toda cifra nova sai nela;
`PORTAL_VAULT_KEY_ANTERIOR` (opcional) só DECIFRA o que foi cifrado antes da troca. É o
`MultiFernet` da biblioteca (https://cryptography.io/en/latest/fernet/#cryptography.fernet.MultiFernet):
cifra com a 1ª, decifra com qualquer uma. Sem a anterior, o comportamento é IDÊNTICO ao de antes
(um Fernet só). O gêmeo do smith-api (`app/services/portal_vault.py`) lê as MESMAS duas variáveis.
⛔ O valor das chaves nunca aparece em exceção nem em log — só o NOME da variável.
"""
from __future__ import annotations

import os

ENV_ATUAL = "PORTAL_VAULT_KEY"
ENV_ANTERIOR = "PORTAL_VAULT_KEY_ANTERIOR"


def _fernet():
    from cryptography.fernet import Fernet, MultiFernet

    key = os.getenv(ENV_ATUAL, "")
    if not key:
        raise RuntimeError("PORTAL_VAULT_KEY ausente — configure no serviço portal-worker")
    atual = Fernet(key.encode() if isinstance(key, str) else key)
    anterior = (os.getenv(ENV_ANTERIOR, "") or "").strip()
    if not anterior:
        return atual
    try:
        velha = Fernet(anterior.encode())
    except Exception:  # noqa: BLE001 — chave anterior malformada: nunca derruba a atual, nunca mostra o valor
        raise RuntimeError("PORTAL_VAULT_KEY_ANTERIOR malformada — corrija ou remova a variável") from None
    return MultiFernet([atual, velha])


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt((plaintext or "").encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt((token or "").encode()).decode()
