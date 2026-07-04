"""Segurança do canal WhatsApp (SPEC-017 P1.2) — helpers PUROS.

Padrões adotados do V7 (mesma linhagem):
- token de webhook POR INTEGRAÇÃO no path (`/api/v1/webhook/{provider}/{token}`);
- tenant resolvido pelo HASH do token (sha256 + compare_digest), NUNCA pelo
  connectedPhone do corpo (forjável);
- bound de comprimento ANTES de hashear (lixo não gasta CPU);
- dedup de inbound por messageId com namespace por provider.

Sem I/O aqui: quem consulta banco/Redis é o caller (webhook route).
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Optional, Tuple

WEBHOOK_TOKEN_MAX_LEN = 80
WEBHOOK_TOKEN_MIN_LEN = 16
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Namespace de dedup por provider (z-api sem prefixo por compat histórica V7).
DEDUP_NAMESPACES = {"z-api": "", "uazapi": "uazapi:", "evolution": "evolution:"}


def attendant_inbound_allowed(phone: str, allowlist: Optional[str] = "__env__") -> bool:
    """Allowlist de teste do atendente (S17 — piloto em número pessoal).

    Env `ATTENDANT_INBOUND_ALLOWLIST` (números separados por vírgula, qualquer
    formatação). Vazia/ausente = responde a todos (produção). Configurada =
    o agente SÓ responde aos números listados; o resto é ignorado em silêncio.
    """
    import os

    raw = os.getenv("ATTENDANT_INBOUND_ALLOWLIST", "") if allowlist == "__env__" else (allowlist or "")

    def _variants(number: str) -> set:
        """Formas equivalentes de um número BR: com e sem o nono dígito.
        WhatsApp entrega 5547XXXXXXXX p/ contas antigas e 55479XXXXXXXX p/
        novas — a allowlist tem que casar nas duas."""
        d = "".join(ch for ch in str(number or "") if ch.isdigit())
        if not d:
            return set()
        forms = {d}
        if d.startswith("55"):
            rest = d[2:]
            if len(rest) == 11 and rest[2] == "9":  # DDD + 9 + 8 dígitos → sem o 9
                forms.add("55" + rest[:2] + rest[3:])
            elif len(rest) == 10:  # DDD + 8 dígitos → com o 9
                forms.add("55" + rest[:2] + "9" + rest[2:])
        return forms

    entries: set = set()
    for item in str(raw).split(","):
        if item.strip():
            entries |= _variants(item)
    if not entries:
        return True
    return bool(_variants(phone) & entries)


def generate_webhook_token() -> str:
    """Token novo (256 bits, urlsafe) para a URL de webhook da integração."""
    return secrets.token_urlsafe(32)


def webhook_token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def webhook_token_prefix(token: str) -> str:
    """Prefixo NÃO sensível para logs/UI (nunca logar o token cru)."""
    return str(token or "")[:8]


def validate_webhook_token_format(token: Optional[str]) -> bool:
    """Bound de formato/tamanho ANTES de hashear. Fail-closed."""
    text = str(token or "")
    if not (WEBHOOK_TOKEN_MIN_LEN <= len(text) <= WEBHOOK_TOKEN_MAX_LEN):
        return False
    return bool(_TOKEN_RE.match(text))


def webhook_token_matches(path_token: str, stored_hash: Optional[str]) -> bool:
    """Comparação em tempo constante do hash do token do path com o da linha."""
    if not stored_hash:
        return False
    return hmac.compare_digest(webhook_token_hash(path_token), str(stored_hash))


def dedup_key(provider: str, message_id: Optional[str]) -> Optional[str]:
    """Chave Redis de dedup (None = sem messageId, não dedupar)."""
    if not message_id:
        return None
    namespace = DEDUP_NAMESPACES.get(str(provider or "").strip().lower())
    if namespace is None:
        namespace = f"{provider}:"
    return f"wa:dedup:{namespace}{message_id}"


def provider_matches_integration(path_provider: str, integration_provider: Optional[str]) -> bool:
    """Provider do path deve bater com o da integração (evita rota trocada)."""
    path_norm = str(path_provider or "").strip().lower()
    row_norm = str(integration_provider or "z-api").strip().lower()
    aliases = {"evolution-api": "evolution"}
    return aliases.get(path_norm, path_norm) == aliases.get(row_norm, row_norm)


def build_webhook_url(public_base_url: str, provider: str, token: str) -> str:
    base = str(public_base_url or "").rstrip("/")
    return f"{base}/api/v1/webhook/{provider}/{token}"


def new_webhook_credentials() -> Tuple[str, str, str]:
    """(token_plaintext, hash, prefix) — plaintext só vai para a URL, nunca pro banco."""
    token = generate_webhook_token()
    return token, webhook_token_hash(token), webhook_token_prefix(token)
