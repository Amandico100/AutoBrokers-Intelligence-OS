"""Contrato das journeys do portal-worker (SPEC-020).

Journey = função async `run(page, params, evidence) -> JourneyResult`, código
versionado por portal. O worker só executa a journey determinística; a DECISÃO
de negócio fica no Smith (cérebro único, regra inviolável).

O registro é um MAPA, não um if/elif
====================================
Ele já foi uma cadeia de `if key == ...` com 4 entradas. Para 4 servia; para os
17 portais da tabela `portals` seriam ~34 blocos, e cada seguradora nova tocaria
o mesmo trecho — conflito de merge garantido e um lugar a mais para esquecer.

O mapa preserva o que motivava o if/elif: **o import continua tardio.** Só o
módulo da journey pedida é carregado, e o worker não puxa Playwright à toa.

Por que o mapa mora aqui, no código, e NÃO numa tabela
------------------------------------------------------
Uma linha de banco apontando para um símbolo Python permitiria o banco nomear
uma função que **não existe na imagem que está no ar** — e o portal-worker é um
serviço separado no EasyPanel, que desalinha de banco por desenho. Seria a
falha da CLAUDE.md §9.1 na veia: tudo verde, e o serviço devolvendo erro em
produção. Mapa no mesmo commit da journey nunca desalinha.

CAPACIDADE, não trabalho
------------------------
O nome depois do ponto é o que o robô SABE FAZER naquele portal, não para que
estamos usando. `cobranca_sweep` é herança da SPEC-023 e continua valendo por
compatibilidade; journeys novas nascem com nome de capacidade
(`listar_parcelas_em_atraso`), porque o mesmo portal vai servir renovação,
cotação e relatório depois — e um nome de trabalho num lugar de capacidade é
como a bagunça volta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

VALID_STATUS = ("done", "needs_human", "failed")


@dataclass
class JourneyResult:
    status: str  # done | needs_human | failed
    captured: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    message: str = ""


# portal_key.journey -> (módulo, função). UMA linha por capacidade.
JOURNEYS: Dict[str, Tuple[str, str]] = {
    "allianz_corretor.login_check": (
        "portal_worker.journeys.allianz_corretor", "login_check"),
    "allianz_corretor.cobranca_sweep": (
        "portal_worker.journeys.allianz_corretor", "cobranca_sweep"),
    "hdi_corretor.login_check": (
        "portal_worker.journeys.hdi_corretor", "login_check"),
    "hdi_corretor.cobranca_sweep": (
        "portal_worker.journeys.hdi_corretor", "cobranca_sweep"),
    "tokiomarine_corretor.login_check": (
        "portal_worker.journeys.tokio_corretor", "login_check"),
    "tokiomarine_corretor.cobranca_sweep": (
        "portal_worker.journeys.tokio_corretor", "cobranca_sweep"),
    "yelum_corretor.login_check": (
        "portal_worker.journeys.yelum_corretor", "login_check"),
    "yelum_corretor.cobranca_sweep": (
        "portal_worker.journeys.yelum_corretor", "cobranca_sweep"),
    "mapfre_corretor.login_check": (
        "portal_worker.journeys.mapfre_corretor", "login_check"),
    "mapfre_corretor.cobranca_sweep": (
        "portal_worker.journeys.mapfre_corretor", "cobranca_sweep"),
    "vidros_lanternas.login_check": (
        "portal_worker.journeys.vidros_lanternas", "login_check"),
    "vidros_lanternas.abrir_atendimento": (
        "portal_worker.journeys.vidros_lanternas", "abrir_atendimento"),
}

# A journey que o Auxiliar de Cobrança pede a cada portal.
JOURNEY_COBRANCA = "cobranca_sweep"


def get_journey(portal_key: str, journey: str) -> Optional[Callable[..., Awaitable["JourneyResult"]]]:
    """Resolve a journey por 'portal_key.journey' (import tardio: só carrega o
    módulo pedido, para não puxar Playwright quando não precisa)."""
    alvo = JOURNEYS.get(f"{str(portal_key or '').strip()}.{str(journey or '').strip()}")
    if not alvo:
        return None
    modulo, funcao = alvo
    try:
        return getattr(import_module(modulo), funcao)
    except (ImportError, AttributeError):
        # Mapa aponta para código que não existe nesta imagem. Devolver None faz
        # o worker gravar 'journey desconhecida' com o nome no erro — diagnóstico
        # legível — em vez de derrubar o processo inteiro do poll.
        return None


def portais_com_cobranca() -> List[str]:
    """Portais que o Cobrador SABE varrer, em ordem estável.

    É a fonte única para o serviço e para a tela: portal conectado que não está
    aqui não é varrido em silêncio — ele aparece no relatório como *ainda não
    automatizado*. Seguradora não cai por esquecimento; cai por estar escrito.
    """
    sufixo = f".{JOURNEY_COBRANCA}"
    return sorted(k[: -len(sufixo)] for k in JOURNEYS if k.endswith(sufixo))


def tem_cobranca(portal_key: str) -> bool:
    return f"{str(portal_key or '').strip()}.{JOURNEY_COBRANCA}" in JOURNEYS
