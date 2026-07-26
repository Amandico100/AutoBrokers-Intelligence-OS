"""Política e classificação de fontes. SPEC-060 §8 e §18.1.

O princípio de §8.1 em uma frase: **nem toda fonte pública tem a mesma
autoridade**. Um PDF da SUSEP e um post de fórum são os dois "públicos", e
tratá-los igual é como um sistema de pesquisa erra de forma mais cara.

O que é hardcoded aqui, e o que não é
-------------------------------------
§18.1 é explícita: *"Não hardcodar conclusões. Hardcodar políticas e
identidades de fonte."*

Então aqui ficam **identidades** — quem é a SUSEP, o que é o Planalto — e as
**regras** de uso. O que a SUSEP diz nunca é hardcoded: isso vem do documento,
com data, e é conferível.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .schemas import (TIER_COMUNIDADE, TIER_ESPECIALIZADA, TIER_IMPRENSA,
                      TIER_NAO_VERIFICADO, TIER_OFICIAL, TIER_PRIMARIA)
from .urls import dominio, dominio_raiz, e_do_dominio


@dataclass(frozen=True)
class PoliticaDeFonte:
    """Uma política declarada — §8.4."""

    policy_key: str
    domain_pattern: str
    name: str
    trust_tier: int
    category: str = "geral"
    official: bool = False
    country: Optional[str] = "BR"
    language: Optional[str] = "pt"
    allowed_methods: tuple[str, ...] = ("direct_fetch", "provider_extract")
    retention_class: str = "standard"
    cache_seconds: int = 86_400
    citation_required: bool = True
    commercial_use: bool = False
    pii_policy: str = "nunca"
    paywall: bool = False
    notes: str = ""

    def como_linha(self) -> dict:
        return {
            "policy_key": self.policy_key, "domain_pattern": self.domain_pattern,
            "name": self.name, "trust_tier": self.trust_tier,
            "category": self.category, "official": self.official,
            "country": self.country, "language": self.language,
            "allowed_methods": list(self.allowed_methods),
            "retention_class": self.retention_class,
            "cache_seconds": self.cache_seconds,
            "citation_required": self.citation_required,
            "commercial_use": self.commercial_use,
            "pii_policy": self.pii_policy, "paywall": self.paywall,
            "notes": self.notes, "status": "active",
        }


# ---------------------------------------------------------------------------
# Catálogo inicial — §18.1
# ---------------------------------------------------------------------------
#
# Cache longo nos oficiais é intencional: legislação e circular não mudam de
# hora em hora, e reler a cada consulta gasta crédito sem ganhar atualidade.
# Quem detecta mudança é o monitor, não a releitura cega.

CATALOGO: tuple[PoliticaDeFonte, ...] = (
    PoliticaDeFonte("gov.susep", "susep.gov.br", "SUSEP", TIER_OFICIAL,
                    "regulador", official=True, cache_seconds=21_600,
                    retention_class="long",
                    notes="Autoridade sobre seguros no Brasil. Prevalece em cobertura e regulação."),
    PoliticaDeFonte("gov.cnsp", "cnsp.gov.br", "CNSP", TIER_OFICIAL,
                    "regulador", official=True, cache_seconds=21_600,
                    retention_class="long"),
    PoliticaDeFonte("gov.planalto", "planalto.gov.br", "Planalto — legislação",
                    TIER_OFICIAL, "legislacao", official=True,
                    cache_seconds=86_400, retention_class="long",
                    notes="Texto de lei. Vigência é o que importa, não a data da página."),
    PoliticaDeFonte("gov.in", "in.gov.br", "Diário Oficial da União",
                    TIER_OFICIAL, "diario_oficial", official=True,
                    cache_seconds=3_600, retention_class="long"),
    PoliticaDeFonte("gov.anpd", "gov.br/anpd", "ANPD", TIER_OFICIAL,
                    "regulador", official=True, retention_class="long"),
    PoliticaDeFonte("gov.receita", "gov.br/receitafederal", "Receita Federal",
                    TIER_OFICIAL, "regulador", official=True),
    PoliticaDeFonte("gov.bcb", "bcb.gov.br", "Banco Central", TIER_OFICIAL,
                    "regulador", official=True),
    PoliticaDeFonte("gov.br", "gov.br", "Portal do governo federal",
                    TIER_OFICIAL, "governo", official=True),

    PoliticaDeFonte("setorial.cnseg", "cnseg.org.br", "CNseg",
                    TIER_ESPECIALIZADA, "setorial"),
    PoliticaDeFonte("setorial.fenacor", "fenacor.org.br", "Fenacor",
                    TIER_ESPECIALIZADA, "setorial"),
    PoliticaDeFonte("setorial.sincor", "sincor.org.br", "Sincor",
                    TIER_ESPECIALIZADA, "setorial"),
    PoliticaDeFonte("setorial.cvg", "cvgrj.com.br", "Clube de Vida em Grupo",
                    TIER_ESPECIALIZADA, "setorial"),
)

# Seguradoras: o site oficial é fonte PRIMÁRIA (Tier 1), não oficial no
# sentido regulatório. A distinção importa — a seguradora é autoridade sobre o
# próprio produto, não sobre a norma que a regula.
SEGURADORAS = (
    ("porto", "portoseguro.com.br", "Porto Seguro"),
    ("bradesco", "bradescoseguros.com.br", "Bradesco Seguros"),
    ("mapfre", "mapfre.com.br", "Mapfre"),
    ("allianz", "allianz.com.br", "Allianz"),
    ("azul", "azulseguros.com.br", "Azul Seguros"),
    ("itau", "itau.com.br", "Itaú Seguros"),
    ("suhai", "suhaiseguradora.com", "Suhai"),
    ("hdi", "hdi.com.br", "HDI Seguros"),
    ("tokio", "tokiomarine.com.br", "Tokio Marine"),
    ("sompo", "sompo.com.br", "Sompo Seguros"),
    ("liberty", "libertyseguros.com.br", "Liberty"),
    ("zurich", "zurich.com.br", "Zurich"),
    ("yelum", "yelumseguradora.com.br", "Yelum"),
    ("alfa", "alfaseguradora.com.br", "Alfa Seguradora"),
)

CATALOGO_SEGURADORAS: tuple[PoliticaDeFonte, ...] = tuple(
    PoliticaDeFonte(f"seguradora.{chave}", padrao, nome, TIER_PRIMARIA,
                    "seguradora", official=False, cache_seconds=43_200,
                    notes="Autoridade sobre o próprio produto, não sobre a norma.")
    for chave, padrao, nome in SEGURADORAS
)

# Domínios que nunca sustentam claim. Não é lista de "sites ruins" — é a
# constatação de que conteúdo sem origem identificável não pode ser citado.
DOMINIOS_NAO_VERIFICADOS = (
    "blogspot.com", "wordpress.com", "medium.com", "wixsite.com",
    "pinterest.com", "quora.com", "answers.yahoo.com",
)

DOMINIOS_DE_COMUNIDADE = (
    "reddit.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
    "linkedin.com", "youtube.com", "tiktok.com", "reclameaqui.com.br",
)

DOMINIOS_DE_IMPRENSA = (
    "globo.com", "uol.com.br", "folha.uol.com.br", "estadao.com.br",
    "valor.globo.com", "infomoney.com.br", "exame.com", "cnnbrasil.com.br",
    "revistaapolice.com.br", "sonhoseguro.com.br", "cqcs.com.br",
    "segs.com.br", "insurancenews.com.br",
)


def todas_as_politicas() -> tuple[PoliticaDeFonte, ...]:
    return CATALOGO + CATALOGO_SEGURADORAS


def politica_para(url: str) -> Optional[PoliticaDeFonte]:
    """A política mais específica que casa com a URL.

    Mais específica primeiro: `gov.br` casaria com `susep.gov.br`, e usar a
    genérica faria a SUSEP perder a identidade de regulador de seguros.
    """
    candidatas = [p for p in todas_as_politicas()
                  if e_do_dominio(url, p.domain_pattern)]
    if not candidatas:
        return None
    return max(candidatas, key=lambda p: len(p.domain_pattern))


def classificar(url: str, *, titulo: str = "",
                dica_de_tier: Optional[int] = None) -> tuple[int, bool]:
    """(tier, oficial) para uma URL. Puro — §8.2.

    A ordem das checagens é a hierarquia: política declarada vence heurística,
    e heurística vence o padrão. O padrão é Tier 3 (imprensa), **não** Tier 0:
    assumir autoridade na dúvida é o erro que faz um blog sustentar uma
    afirmação sobre a lei.
    """
    politica = politica_para(url)
    if politica:
        return politica.trust_tier, politica.official

    host = dominio(url)
    raiz = dominio_raiz(url)
    if not host:
        return TIER_NAO_VERIFICADO, False

    # `.gov.br` e `.leg.br` são identidade de origem, não opinião sobre o
    # conteúdo: qualquer página nesses domínios é publicação oficial.
    if host.endswith(".gov.br") or host == "gov.br" or host.endswith(".leg.br"):
        return TIER_OFICIAL, True
    if host.endswith(".jus.br"):
        return TIER_OFICIAL, True
    if host.endswith(".edu.br") or host.endswith(".edu"):
        return TIER_ESPECIALIZADA, False
    if any(raiz == d or host.endswith("." + d) for d in DOMINIOS_NAO_VERIFICADOS):
        return TIER_NAO_VERIFICADO, False
    if any(raiz == d or host.endswith("." + d) for d in DOMINIOS_DE_COMUNIDADE):
        return TIER_COMUNIDADE, False
    if any(raiz == d or host.endswith("." + d) for d in DOMINIOS_DE_IMPRENSA):
        return TIER_IMPRENSA, False
    if host.endswith(".org.br") or host.endswith(".org"):
        return TIER_ESPECIALIZADA, False

    if dica_de_tier is not None:
        return int(dica_de_tier), False
    return TIER_IMPRENSA, False


# ---------------------------------------------------------------------------
# Permissões de uso
# ---------------------------------------------------------------------------


@dataclass
class Permissao:
    permitido: bool
    metodo: str = "direct_fetch"
    motivo: str = ""
    cache_seconds: int = 86_400
    retention_class: str = "short"


def pode_adquirir(url: str, metodo: str = "direct_fetch") -> Permissao:
    """A fonte pode ser lida por este método? — §14.1 e §34.2.

    Não substitui o Egress Guard, que decide o que pode ser ACESSADO em rede.
    Aqui a pergunta é outra: se pode, *deve*, e sob quais condições.
    """
    from .urls import normalizar

    if not normalizar(url):
        return Permissao(False, metodo, "endereço não utilizável para pesquisa")

    politica = politica_para(url)
    if politica is None:
        # Sem política declarada, o padrão é o mais conservador que ainda
        # serve: leitura de conteúdo público, cache curto, retenção curta.
        return Permissao(True, metodo, "sem política declarada — padrão conservador",
                         cache_seconds=21_600, retention_class="short")

    if metodo not in politica.allowed_methods and metodo != "direct_fetch":
        return Permissao(False, metodo,
                         f"a política de {politica.name} não permite {metodo}")
    if politica.paywall and metodo in ("crawl", "provider_crawl"):
        return Permissao(False, metodo,
                         "conteúdo atrás de paywall — não se contorna acesso pago")
    return Permissao(True, metodo, f"política {politica.policy_key}",
                     cache_seconds=politica.cache_seconds,
                     retention_class=politica.retention_class)


def exige_citacao(url: str) -> bool:
    p = politica_para(url)
    return p.citation_required if p else True


def cache_permitido(url: str) -> int:
    p = politica_para(url)
    return p.cache_seconds if p else 21_600


def rotulo_da_fonte(url: str) -> str:
    """Nome legível para aparecer na citação, sem expor caminho interno."""
    p = politica_para(url)
    if p:
        return p.name
    return dominio_raiz(url) or "fonte"
