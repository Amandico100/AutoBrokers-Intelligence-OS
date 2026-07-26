"""Cutover do web search histórico. SPEC-060 §35.

O que existia
-------------
`TavilyService` fazia uma busca básica e devolvia uma **string markdown**
pronta para o prompt: três resultados, sem objeto de fonte, sem tier, sem data
de recuperação, sem citação. `WebSearchTool` colava essa string no contexto.

Por que isso não podia continuar como autoridade
------------------------------------------------
Uma string não vira citação. Sem objeto de fonte não há como dizer *qual*
página sustenta *qual* afirmação — e §16.6 exige exatamente isso. Também não
havia como distinguir a SUSEP de um blog: os três resultados chegavam com o
mesmo peso, e o modelo, sem sinal de autoridade, tratava-os igual.

O que muda, e o que NÃO muda
----------------------------
§35.1: o Tavily **é preservado**. A chave, a conta e a integração continuam —
ele virou adapter homologado dentro do Research Orchestrator, com retorno
estruturado e assíncrono de verdade.

O que sai de cena é a tool antiga como **autoridade soberana** (§35.6): depois
do cutover o grafo não a anexa mais; quem pesquisa é `pesquisar_na_web`, que
passa pelo orquestrador, classifica fonte e devolve claims com citação.

A flag `RESEARCH_CUTOVER` existe para rollback sem deploy, como em SPEC-059.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_JA_AVISADO: set[str] = set()


def cutover_ligado() -> bool:
    """`True` quando o Research Orchestrator é a autoridade da pesquisa."""
    return str(os.getenv("RESEARCH_CUTOVER", "1")).strip().lower() \
        in ("1", "true", "yes", "on")


def _avisar_uma_vez(chave: str, mensagem: str) -> None:
    if chave in _JA_AVISADO:
        return
    _JA_AVISADO.add(chave)
    logger.info("[SPEC-060] %s", mensagem)


def web_search_ainda_e_autoridade() -> bool:
    """A tool antiga deve ser anexada ao grafo?

    Depois do cutover, não. Ela continua no código e continua funcionando —
    o que muda é que o Core não a recebe mais, então nenhuma resposta profunda
    usa o retorno bruto dela como base (§35.6).
    """
    if cutover_ligado():
        _avisar_uma_vez(
            "web_search",
            "`web_search` deixou de ser anexada ao Core: a pesquisa passa pelo "
            "Research Orchestrator, com fonte classificada e citação por "
            "afirmação (SPEC-060 §35.6).")
        return False
    return True


def capability_equivalente(capability: str) -> str:
    """§35.3 — `platform.web.search` vira alias das capacidades granulares.

    O alias é preservado de propósito: releases antigas de Skill declaram a
    capability velha, e quebrá-las no cutover derrubaria trabalho que não tem
    nada a ver com pesquisa.
    """
    return {
        "platform.web.search": "platform.research.search",
        "platform.web.scrape": "platform.research.extract",
    }.get(capability, capability)


def capacidades_ativas(ativas: dict) -> dict:
    """Expande as capabilities antigas para as novas, sem remover as antigas.

    Expand-first aplicado a permissão: quem tinha `platform.web.search` passa
    a ter também `platform.research.search`. Ninguém perde poder no cutover —
    e ninguém ganha o que não tinha.
    """
    if not isinstance(ativas, dict):
        return ativas
    saida = dict(ativas)
    for antiga, nova in (("platform.web.search", "platform.research.search"),
                         ("platform.web.scrape", "platform.research.extract")):
        if antiga in saida and nova not in saida:
            saida[nova] = {**(saida[antiga] or {}), "_alias_de": antiga}
    return saida
