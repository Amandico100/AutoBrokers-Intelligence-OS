"""Modo, decomposição e plano. SPEC-060 §7, §11, §12, §13.1.

Planejar antes de gastar
------------------------
§0.1 coloca "planejar fontes e orçamento" antes de "pesquisar" por um motivo
concreto: provider caro chamado sem plano vira dez buscas quase iguais que
trazem as mesmas cinco páginas. O plano é o que transforma uma pergunta em
subperguntas que **não se sobrepõem**, cada uma com a família de fonte certa.

Tudo aqui é puro e determinístico. A LLM pode decompor melhor em casos
difíceis (§13.1 permite), mas a decomposição base não pode DEPENDER dela: uma
pesquisa que falha porque o modelo está fora do ar é uma pesquisa que não
existe. O modelo entra como melhoria, nunca como pré-requisito.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .schemas import (BUSINESS_DISCOVERY, CLAIM_CHECK, DEEP, MONITOR,
                      PERFIL_DO_MODO, QUICK, SITE_AUDIT, VERIFIED,
                      ResearchRequest)

# ---------------------------------------------------------------------------
# Resolução de modo — §7
# ---------------------------------------------------------------------------

# Cada gatilho é uma forma real de pedir. A ordem importa: o primeiro que casa
# vence, e os mais específicos vêm antes.
GATILHOS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (SITE_AUDIT, ("analise meu site", "analisar meu site", "auditoria do site",
                  "seo", "aeo", "aparecer no google", "ranquear",
                  "meu site está", "meu site esta", "otimizar o site",
                  "presença digital", "presenca digital")),
    (BUSINESS_DISCOVERY, ("encontre empresas", "encontrar empresas",
                          "empresas da região", "empresas da regiao",
                          "prospecção", "prospeccao", "lista de empresas",
                          "leads", "empresas de", "potenciais clientes")),
    (MONITOR, ("monitore", "monitorar", "me avise quando", "acompanhe as mudanças",
               "acompanhe as mudancas", "fique de olho", "toda semana verifique",
               "todo dia verifique", "avise se mudar")),
    (CLAIM_CHECK, ("é verdade que", "e verdade que", "confere se", "verifique se",
                   "isso procede", "isso é verdade", "isso e verdade",
                   "checar se", "confirma se")),
    (DEEP, ("dossiê", "dossie", "estudo completo", "análise completa",
            "analise completa", "compare", "comparar", "concorrentes",
            "panorama do mercado", "relatório sobre", "relatorio sobre",
            "pesquisa profunda", "aprofunde")),
    (VERIFIED, ("o que mudou", "mudanças na", "mudancas na", "nova regra",
                "susep", "circular", "resolução", "resolucao", "legislação",
                "legislacao", "regulament", "com fontes", "fontes oficiais",
                "está valendo", "esta valendo")),
)

# Assunto que nunca aceita `quick`: §7.1 é explícita — "não usar para alto
# risco". Uma resposta de uma fonte sobre cobertura é pior que nenhuma.
TERMOS_QUE_EXIGEM_VERIFICACAO = (
    "cobertura", "cobre", "exclusão", "exclusao", "franquia", "carência",
    "carencia", "indeniza", "sinistro", "obrigatório", "obrigatorio",
    "lei ", "susep", "cnsp", "anpd", "lgpd", "vigência", "vigencia",
    "prazo legal", "multa", "regulament", "norma",
)


def resolver_modo(pergunta: str, *, pedido: Optional[str] = None) -> str:
    """Modo a partir do que foi pedido. Puro — §7.

    O piso de segurança vem por último e sobrepõe: mesmo que a frase pareça
    uma pergunta rápida, assunto regulatório sobe para `verified`. Errar para
    mais rigor custa alguns segundos; errar para menos custa credibilidade.
    """
    alvo = f"{pergunta or ''} {pedido or ''}".lower()

    for modo, termos in GATILHOS:
        if any(t in alvo for t in termos):
            if modo == QUICK:
                break
            return modo

    if any(t in alvo for t in TERMOS_QUE_EXIGEM_VERIFICACAO):
        return VERIFIED
    return QUICK


def exige_fonte_oficial(pergunta: str) -> bool:
    alvo = (pergunta or "").lower()
    return any(t in alvo for t in TERMOS_QUE_EXIGEM_VERIFICACAO)


# ---------------------------------------------------------------------------
# Decomposição — §13.1
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "em",
    "no", "na", "nos", "nas", "por", "para", "com", "sem", "que", "qual",
    "quais", "como", "quando", "onde", "e", "ou", "se", "me", "meu", "minha",
    "sobre", "isso", "esse", "essa", "ao", "aos", "à", "às", "pelo", "pela",
    "quero", "preciso", "pode", "poderia", "favor", "por favor",
}

# Termos de seguro que merecem virar subpergunta própria — §13.1 pede a
# dimensão "termos de seguro" explicitamente.
DIMENSOES_DE_SEGURO = {
    "cobertura": "o que exatamente está coberto e o que está excluído",
    "carência": "qual é o prazo de carência",
    "carencia": "qual é o prazo de carência",
    "franquia": "como funciona a franquia",
    "sinistro": "qual é o procedimento de sinistro",
    "vigência": "qual é a vigência e desde quando vale",
    "vigencia": "qual é a vigência e desde quando vale",
    "regulament": "qual norma regula isso e qual órgão publicou",
    "susep": "o que a SUSEP determina sobre isso",
}


def termos_relevantes(pergunta: str, *, maximo: int = 8) -> list[str]:
    palavras = re.findall(r"[\wàáâãéêíóôõúç]+", (pergunta or "").lower())
    vistos: list[str] = []
    for p in palavras:
        if len(p) <= 3 or p in _STOPWORDS or p in vistos:
            continue
        vistos.append(p)
    return vistos[:maximo]


def decompor(pergunta: str, modo: str) -> list[str]:
    """Subperguntas que não se sobrepõem. Puro — §13.1.

    Em `quick` a decomposição é a própria pergunta: decompor uma pergunta
    simples em quatro só multiplica o custo para reencontrar a mesma página.
    """
    base = (pergunta or "").strip()
    if modo in (QUICK, MONITOR):
        return [base]

    subs: list[str] = [base]
    alvo = base.lower()

    for termo, sub in DIMENSOES_DE_SEGURO.items():
        if termo in alvo and sub not in subs:
            subs.append(sub)

    if modo in (VERIFIED, CLAIM_CHECK):
        subs.append(f"fonte oficial sobre {' '.join(termos_relevantes(base, maximo=5))}")
        if "quando" not in alvo and "desde" not in alvo:
            subs.append(f"desde quando vale: {' '.join(termos_relevantes(base, maximo=4))}")

    if modo == DEEP:
        termos = " ".join(termos_relevantes(base, maximo=5))
        subs.extend([
            f"situação atual e números sobre {termos}",
            f"o que mudou recentemente em {termos}",
            f"riscos e limitações relacionados a {termos}",
            f"posições divergentes sobre {termos}",
        ])

    # Dedupe preservando ordem: a pergunta original tem de ser a primeira.
    saida: list[str] = []
    for s in subs:
        limpo = " ".join(s.split())
        if limpo and limpo.lower() not in {x.lower() for x in saida}:
            saida.append(limpo)
    return saida[:8]


def montar_consultas(subquestao: str, *, oficial: bool = False,
                     regiao: str = "Brasil") -> list[str]:
    """Consultas para o provider. §13.4 — filtros, não repetição.

    Duas variações por subpergunta: uma direta e uma ancorada em fonte
    oficial. Mais que isso costuma trazer as mesmas URLs e paga duas vezes.
    """
    base = " ".join((subquestao or "").split())
    if not base:
        return []
    consultas = [base]
    if oficial:
        consultas.append(f"{base} site oficial SUSEP OR gov.br")
    elif regiao and regiao.lower() not in base.lower():
        consultas.append(f"{base} {regiao} seguros")
    return consultas[:2]


# ---------------------------------------------------------------------------
# Plano — §12
# ---------------------------------------------------------------------------


@dataclass
class Plano:
    modo: str
    pergunta: str
    subquestoes: list[str] = field(default_factory=list)
    consultas: list[str] = field(default_factory=list)
    dominios_preferidos: list[str] = field(default_factory=list)
    exige_oficial: bool = False
    min_fontes: int = 1
    max_fontes: int = 3
    max_leituras: int = 3
    max_segundos: int = 60
    gera_artifact: bool = False
    regras_de_parada: dict = field(default_factory=dict)
    regras_de_verificacao: dict = field(default_factory=dict)
    contrato_de_saida: dict = field(default_factory=dict)

    def como_linha(self) -> dict:
        return {
            "subquestions": self.subquestoes,
            "search_strategy": {"consultas": self.consultas,
                                "dominios_preferidos": self.dominios_preferidos},
            "source_strategy": {"exige_oficial": self.exige_oficial,
                                "min_fontes": self.min_fontes,
                                "max_fontes": self.max_fontes},
            "provider_strategy": {"max_leituras": self.max_leituras},
            "stop_rules": self.regras_de_parada,
            "verification_rules": self.regras_de_verificacao,
            "output_contract": self.contrato_de_saida,
        }


# Domínios que valem a pena filtrar quando a pergunta é regulatória.
DOMINIOS_OFICIAIS = ("gov.br", "susep.gov.br", "planalto.gov.br", "in.gov.br")


def planejar(pedido: ResearchRequest) -> Plano:
    """Monta o plano. Puro — §12.1.

    As regras de parada (§12.2) nascem aqui, e não no meio da execução, porque
    é o único momento em que dá para declará-las honestamente: depois que a
    pesquisa começou, é tentador mover o alvo até o resultado parecer bom.
    """
    perfil = PERFIL_DO_MODO.get(pedido.mode, PERFIL_DO_MODO[QUICK])
    oficial = perfil["exige_oficial"] or exige_fonte_oficial(pedido.question)
    subs = decompor(pedido.question, pedido.mode)

    consultas: list[str] = []
    for s in subs:
        consultas.extend(montar_consultas(s, oficial=oficial))
    # Teto de consultas: em `deep` sobrariam dezesseis, e depois da oitava o
    # ganho marginal cai muito enquanto o custo continua linear.
    limite_consultas = {QUICK: 2, VERIFIED: 4, DEEP: 8, CLAIM_CHECK: 4,
                        MONITOR: 2, SITE_AUDIT: 2, BUSINESS_DISCOVERY: 2}
    consultas = consultas[:limite_consultas.get(pedido.mode, 4)]

    return Plano(
        modo=pedido.mode,
        pergunta=pedido.question,
        subquestoes=subs,
        consultas=consultas,
        dominios_preferidos=list(DOMINIOS_OFICIAIS) if oficial else [],
        exige_oficial=oficial,
        min_fontes=perfil["min_fontes"],
        max_fontes=perfil["max_fontes"],
        max_leituras=min(perfil["max_fontes"], 12),
        max_segundos=int(pedido.tempo_maximo_s or perfil["max_segundos"]),
        gera_artifact=perfil["artifact"],
        regras_de_parada={
            "fontes_suficientes": perfil["min_fontes"],
            "cobertura_minima_de_subquestoes": 0.6 if pedido.mode == DEEP else 1.0,
            "ganho_marginal_baixo": "duas leituras seguidas sem claim novo",
            "orcamento": pedido.orcamento_brl,
            "tempo_maximo_s": int(pedido.tempo_maximo_s or perfil["max_segundos"]),
        },
        regras_de_verificacao={
            "exige_fonte_oficial_para_alto_risco": True,
            "minimo_de_fontes_por_claim": 2 if pedido.mode in (VERIFIED, DEEP, CLAIM_CHECK) else 1,
            "snippet_nao_sustenta_alto_risco": True,
        },
        contrato_de_saida={
            "artifact": perfil["artifact"],
            "formatos": pedido.saidas or (["web"] if perfil["artifact"] else []),
            "exige_limitacoes": True,
        },
    )


def deve_parar(*, fontes_lidas: int, claims_novos_seguidos_sem: int,
               subquestoes_cobertas: float, plano: Plano,
               segundos_gastos: float) -> tuple[bool, str]:
    """§12.2 — quando parar. Puro.

    A regra do ganho marginal é a que mais economiza: duas leituras seguidas
    sem produzir claim novo significam que as fontes estão repetindo umas às
    outras, e a terceira quase nunca é diferente.
    """
    if fontes_lidas >= plano.max_fontes:
        return True, "número máximo de fontes do plano atingido"
    if segundos_gastos >= plano.max_segundos:
        return True, "tempo máximo do plano atingido"
    if claims_novos_seguidos_sem >= 2 and fontes_lidas >= plano.min_fontes:
        return True, "as últimas fontes não acrescentaram nada novo"
    cobertura_alvo = float(plano.regras_de_parada.get(
        "cobertura_minima_de_subquestoes", 1.0))
    if subquestoes_cobertas >= cobertura_alvo and fontes_lidas >= plano.min_fontes:
        return True, "as subperguntas do plano foram cobertas"
    return False, ""


def deve_replanejar(*, fontes_encontradas: int, oficiais_encontradas: int,
                    plano: Plano) -> Optional[str]:
    """§12.3 — motivo do replan, ou `None`."""
    if fontes_encontradas == 0:
        return "as consultas não retornaram fonte utilizável"
    if plano.exige_oficial and oficiais_encontradas == 0 and fontes_encontradas >= 3:
        return "nenhuma fonte oficial foi encontrada para um assunto que exige"
    return None
