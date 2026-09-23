"""
Utils - Funções utilitárias centralizadas
"""

import logging
import os

from app.factories.model_policy import ModeloNaoResolvido

logger = logging.getLogger(__name__)

#: A variável de ambiente dos provedores NATIVOS, quando a linha do catálogo
#: não declara `api_key_env` (as linhas antigas de `llm_pricing` não declaram).
_CHAVE_DO_PROVEDOR_NATIVO = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


class ChaveNaoResolvida(ModeloNaoResolvido, ValueError):
    """Provedor desconhecido ou chave ausente.

    É `ValueError` (o contrato de sempre: os chamadores capturam ValueError) E
    `ModeloNaoResolvido` (o erro do Model Router, SPEC-116): quem pega um ou
    outro continua pegando.
    """


def _catalogo() -> dict:
    try:
        from app.factories.model_policy import catalogo

        return catalogo()
    except Exception as exc:  # noqa: BLE001 — sem catálogo, só os nativos
        logger.warning("[utils] catálogo indisponível (%s)", type(exc).__name__)
        return {}


def get_api_key_for_provider(provider: str = None, model: str = None) -> str:
    """Retorna a API key do ambiente para o provedor (ou o modelo).

    SPEC-116 U5: a variável vem do CATÁLOGO (`llm_pricing.api_key_env`) — um
    provedor novo entra por uma linha do catálogo, não por uma linha aqui.
    ⛔ Provedor desconhecido é ERRO: antes devolvia a chave da OpenAI e o
    pedido saía para o provedor errado (EVIDENCIAS/03 F6).

    Raises:
        ChaveNaoResolvida (ValueError): provedor desconhecido ou variável ausente.
    """
    cat = _catalogo()
    linha = cat.get(model) if model else None

    # Sem provedor: o CATÁLOGO diz de quem é o modelo. Id "provedor/modelo"
    # fora do catálogo é o formato do OpenRouter.
    if not provider and model:
        if linha:
            provider = linha.get("provider")
        elif "/" in model:
            provider = "openrouter"

    provider = str(provider or "").strip().lower()
    if not provider:
        raise ChaveNaoResolvida(f"❌ provedor não identificado para o modelo {model!r}")

    env_var = (linha or {}).get("api_key_env") if (linha or {}).get("provider") == provider else None
    if not env_var:
        env_var = next((l.get("api_key_env") for l in cat.values()
                        if l.get("provider") == provider and l.get("api_key_env")), None)
    if not env_var:
        env_var = _CHAVE_DO_PROVEDOR_NATIVO.get(provider)
    if not env_var:
        raise ChaveNaoResolvida(f"❌ provedor desconhecido '{provider}' — sem chave no catálogo")

    api_key = os.getenv(env_var)
    if not api_key:
        raise ChaveNaoResolvida(f"❌ Variável {env_var} ausente no .env para provider '{provider}'")

    return api_key
