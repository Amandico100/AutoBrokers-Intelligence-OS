"""Leitura profunda da web — SPEC-057 Bloco G.

Firecrawl como capacidade governada e medida. Não substitui a busca que já
existe: acrescenta ler uma página inteira e ler um documento público.
"""

from .firecrawl import (
    FirecrawlClient,
    FirecrawlIndisponivel,
    configurado,
    ler_pagina,
    pesquisar_com_fontes,
)

__all__ = [
    "FirecrawlClient", "FirecrawlIndisponivel", "configurado",
    "ler_pagina", "pesquisar_com_fontes",
]
