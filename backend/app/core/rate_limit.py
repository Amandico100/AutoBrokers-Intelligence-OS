"""
Rate Limiting Configuration
Usando slowapi para proteger endpoints críticos contra abuso.
"""

from slowapi import Limiter
from starlette.requests import Request


def get_real_client_ip(request: Request) -> str:
    """
    Extrai o IP real do cliente a partir do header X-Forwarded-For.

    Em produção (Railway/Vercel), o request passa por reverse proxy que injeta:
        X-Forwarded-For: <ip_real_cliente>, <ip_proxy1>, <ip_proxy2>

    Pegamos o primeiro IP da lista (o do cliente original).
    Fallback para request.client.host se o header não existir (dev local).
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Primeiro IP é sempre o do cliente real
        return forwarded.split(",")[0].strip()
    return request.client.host or "127.0.0.1"


# Limiter global - usa IP real do cliente como chave de identificação
limiter = Limiter(key_func=get_real_client_ip)
