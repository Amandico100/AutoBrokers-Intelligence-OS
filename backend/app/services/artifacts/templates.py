"""Catálogo de templates de peça. SPEC-057 §Bloco C.

Oito tipos, escolhidos pelo que uma corretora brasileira precisa entregar — não
por variedade de vitrine. Cada um declara três coisas:

  forma narrativa   como o documento se organiza (veredito primeiro? precisão
                    primeiro? cronologia?)
  sistema visual    aurora, obsidian ou meridian
  contrato de dado  o que o agente precisa reunir antes de compor

A forma narrativa é o eixo mais importante e o mais fácil de errar. Um
relatório financeiro e um dossiê de pesquisa podem ter os mesmos números e
mesmo assim precisam de estruturas opostas: o primeiro abre pela tabela e
sustenta com texto, o segundo abre pelo argumento e sustenta com tabela.
Tratar os dois como "relatório" é o que produz aquele PDF corporativo genérico
que ninguém lê.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    description: str
    category: str
    narrative_shape: str
    audience: str
    visual_style: str
    page_format: str
    composition: list[dict]
    data_contract: dict = field(default_factory=dict)
    instruction_md: str = ""

    def content_hash(self) -> str:
        base = json.dumps(
            {"c": self.composition, "d": self.data_contract, "v": self.visual_style},
            sort_keys=True, ensure_ascii=False, default=str) + "\n" + self.instruction_md
        return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _campo(tipo: str, descricao: str, obrigatorio: bool = True) -> dict:
    return {"type": tipo, "description": descricao, "required": obrigatorio}


# ==========================================================================
# 1. Panorama executivo
# ==========================================================================

PANORAMA = Template(
    key="executive.panorama",
    name="Panorama da Corretora",
    description="Visão executiva do período: o que aconteceu, o que mudou e o que fazer.",
    category="executive", narrative_shape="verdict_led", audience="internal",
    visual_style="aurora", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Panorama executivo"}},
        {"block": "kpis", "props": {"eyebrow": "Os números do período",
                                    "title": "Como a corretora fechou"}},
        {"block": "verdict", "props": {}},
        {"block": "chart", "props": {"eyebrow": "Evolução",
                                     "title": "Produção mês a mês"}},
        {"block": "split", "props": {
            "sidebar": True,
            "left": [{"block": "ranking", "props": {"eyebrow": "Concentração",
                                                    "title": "Maiores clientes"}}],
            "right": [{"block": "donut", "props": {"eyebrow": "Composição",
                                                   "title": "Por ramo"}}]}},
        {"block": "callout", "props": {}},
        {"block": "actions", "props": {"eyebrow": "Plano",
                                       "title": "O que fazer nas próximas semanas"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "headline": _campo("object", "número de capa: valor, rótulo e variação"),
        "kpis": _campo("array", "4 a 6 indicadores com valor, variação e base de comparação"),
        "verdict": _campo("string", "uma frase que responde 'e daí?'"),
        "trend": _campo("object", "série temporal de produção"),
        "top_clients": _campo("array", "ranking por prêmio"),
        "by_line": _campo("array", "composição por ramo"),
        "actions": _campo("array", "3 a 5 ações com responsável e prazo"),
    },
    instruction_md=(
        "Abra pelo veredito. O executivo lê a capa e o primeiro parágrafo; o "
        "resto é sustentação.\n\n"
        "Toda variação precisa da base de comparação explícita — '+12%' sem "
        "dizer contra o quê é ruído.\n\n"
        "Se a concentração nos cinco maiores clientes passar de 40%, isso é "
        "risco e precisa aparecer como alerta, não como conquista."),
)


# ==========================================================================
# 2. Carteira e comissões
# ==========================================================================

COMISSOES = Template(
    key="financial.commissions",
    name="Carteira e Comissões",
    description="Receita, comissionamento e composição da carteira, com precisão de fechamento.",
    category="financial", narrative_shape="precision_led", audience="internal",
    visual_style="meridian", page_format="a4",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Fechamento financeiro"}},
        {"block": "kpis", "props": {"title": "Receita do período"}},
        {"block": "waterfall", "props": {"eyebrow": "Ponte",
                                         "title": "De onde veio a variação"}},
        {"block": "table", "props": {"eyebrow": "Detalhamento",
                                     "title": "Comissão por seguradora"}},
        {"block": "split", "props": {
            "left": [{"block": "donut", "props": {"title": "Receita por ramo"}}],
            "right": [{"block": "ranking", "props": {"title": "Maiores comissões"}}]}},
        {"block": "callout", "props": {}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "kpis": _campo("array", "receita, comissão média, inadimplência, ticket"),
        "bridge": _campo("array", "passos da ponte: inicial, deltas, final"),
        "by_insurer": _campo("array", "linhas com seguradora, prêmio, comissão, taxa"),
        "by_line": _campo("array", "receita por ramo"),
    },
    instruction_md=(
        "Precisão antes de narrativa. A tabela é o centro; o texto explica o "
        "que a tabela já mostrou.\n\n"
        "Valores sempre com duas casas e alinhados à direita. Total conferido "
        "e visível — tabela financeira sem total é rascunho.\n\n"
        "A ponte existe para responder 'por que mudou', não 'quanto mudou'."),
)


# ==========================================================================
# 3. Produção e funil
# ==========================================================================

FUNIL = Template(
    key="commercial.pipeline",
    name="Produção e Funil",
    description="Onde as oportunidades entram, onde param e onde se perdem.",
    category="commercial", narrative_shape="action_led", audience="internal",
    visual_style="aurora", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Comercial"}},
        {"block": "kpis", "props": {"title": "O funil em números"}},
        {"block": "funnel", "props": {"eyebrow": "Etapas",
                                      "title": "Onde as cotações se perdem"}},
        {"block": "verdict", "props": {}},
        {"block": "split", "props": {
            "left": [{"block": "ranking", "props": {"title": "Conversão por produto"}}],
            "right": [{"block": "ring", "props": {"title": "Meta do mês"}}]}},
        {"block": "chart", "props": {"eyebrow": "Ritmo", "title": "Cotações por semana"}},
        {"block": "actions", "props": {"title": "Onde atacar primeiro"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "funnel": _campo("array", "etapas do funil, do topo à base"),
        "by_product": _campo("array", "taxa de conversão por produto"),
        "goal": _campo("object", "meta e realizado"),
        "weekly": _campo("object", "série semanal"),
    },
    instruction_md=(
        "O funil só serve se mostrar a conversão ENTRE etapas. Volume por "
        "etapa isolado esconde exatamente onde o problema está.\n\n"
        "A ação vem da maior queda percentual, não do maior volume perdido."),
)


# ==========================================================================
# 4. Dossiê de pesquisa
# ==========================================================================

PESQUISA = Template(
    key="research.market_brief",
    name="Dossiê de Pesquisa",
    description="Estudo com argumento, evidência e fonte — mercado, concorrência ou regulação.",
    category="research", narrative_shape="narrative_led", audience="internal",
    visual_style="aurora", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Dossiê"}},
        {"block": "verdict", "props": {}},
        {"block": "prose", "props": {"eyebrow": "Contexto", "title": "O que está em jogo"}},
        {"block": "kpis", "props": {"title": "Números que ancoram a análise"}},
        {"block": "chart", "props": {"eyebrow": "Evidência", "title": "Comportamento no período"}},
        {"block": "prose", "props": {"eyebrow": "Análise", "title": "Leitura"}},
        {"block": "table", "props": {"eyebrow": "Comparação", "title": "Lado a lado"}},
        {"block": "callout", "props": {}},
        {"block": "actions", "props": {"title": "Recomendações"}},
        {"block": "sources", "props": {"title": "Fontes consultadas",
                                       "note": "Toda afirmação numérica deste dossiê "
                                               "vem de uma das fontes acima."}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "thesis": _campo("string", "a tese em uma frase"),
        "context_md": _campo("string", "contexto em prosa"),
        "analysis_md": _campo("string", "análise em prosa"),
        "comparison": _campo("array", "tabela comparativa"),
        "citations": _campo("array", "fontes com URL e data de acesso"),
    },
    instruction_md=(
        "Aqui o texto conduz e o número sustenta — o inverso do executivo.\n\n"
        "Nenhuma afirmação numérica sem fonte na lista final. Se a fonte não "
        "foi lida, a afirmação não entra.\n\n"
        "Separe o que é fato do que é leitura sua. Misturar os dois é o defeito "
        "mais comum em dossiê e o que destrói a confiança quando alguém confere."),
)


# ==========================================================================
# 5. Dossiê do segurado
# ==========================================================================

DOSSIE_CLIENTE = Template(
    key="portfolio.client_dossier",
    name="Dossiê do Segurado",
    description="Tudo sobre um cliente: apólices, coberturas, lacunas e renovações.",
    category="portfolio", narrative_shape="verdict_led", audience="client",
    visual_style="aurora", page_format="a4",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Dossiê do segurado"}},
        {"block": "kpis", "props": {"title": "Resumo da proteção"}},
        {"block": "table", "props": {"eyebrow": "Apólices",
                                     "title": "O que está vigente"}},
        {"block": "callout", "props": {}},
        {"block": "ranking", "props": {"eyebrow": "Exposição",
                                       "title": "Onde está o maior valor segurado"}},
        {"block": "actions", "props": {"title": "Nossas recomendações"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {"disclaimer":
            "Documento informativo. As condições contratuais prevalecem sobre "
            "este resumo."}},
    ],
    data_contract={
        "client": _campo("object", "nome e identificação do segurado"),
        "policies": _campo("array", "apólices vigentes com vigência e IS"),
        "gaps": _campo("array", "lacunas de cobertura identificadas"),
    },
    instruction_md=(
        "Esta peça vai para o CLIENTE. Linguagem sem jargão: 'importância "
        "segurada' vira 'valor protegido' quando o contexto permitir.\n\n"
        "Lacuna de cobertura se apresenta como cuidado, nunca como venda "
        "agressiva — e sempre com o motivo técnico junto.\n\n"
        "O aviso legal no rodapé não é opcional."),
)


# ==========================================================================
# 6. Radar de renovações
# ==========================================================================

RENOVACOES = Template(
    key="renewals.radar",
    name="Radar de Renovações",
    description="O que vence, quando vence e o que fazer antes de vencer.",
    category="renewals", narrative_shape="chronological", audience="internal",
    visual_style="meridian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Renovações"}},
        {"block": "kpis", "props": {"title": "Janela de risco"}},
        {"block": "callout", "props": {}},
        {"block": "table", "props": {"eyebrow": "Agenda",
                                     "title": "Vencimentos ordenados por urgência"}},
        {"block": "stacked", "props": {"eyebrow": "Distribuição",
                                       "title": "Vencimentos por semana e ramo"}},
        {"block": "actions", "props": {"title": "Prioridades desta semana"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "window": _campo("object", "período coberto pelo radar"),
        "renewals": _campo("array", "apólices a vencer com dias restantes"),
        "by_week": _campo("object", "distribuição por semana"),
    },
    instruction_md=(
        "Ordem cronológica, sempre. O que vence antes vem antes — mesmo que "
        "seja menor.\n\n"
        "Prêmio alto com pouco tempo é a combinação que merece destaque "
        "visual; os dois critérios juntos, nunca só o valor."),
)


# ==========================================================================
# 7. Sinistros e seguradoras
# ==========================================================================

SINISTROS = Template(
    key="claims.performance",
    name="Sinistros e Seguradoras",
    description="Como as seguradoras estão respondendo: prazo, deferimento e reclamação.",
    category="claims", narrative_shape="comparative", audience="internal",
    visual_style="meridian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Sinistros"}},
        {"block": "kpis", "props": {"title": "O período em números"}},
        {"block": "table", "props": {"eyebrow": "Comparação",
                                     "title": "Desempenho por seguradora"}},
        {"block": "verdict", "props": {}},
        {"block": "split", "props": {
            "left": [{"block": "ranking", "props": {"title": "Tempo médio de regulação"}}],
            "right": [{"block": "donut", "props": {"title": "Status dos avisos"}}]}},
        {"block": "callout", "props": {}},
        {"block": "actions", "props": {"title": "Encaminhamentos"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "kpis": _campo("array", "avisos, prazo médio, taxa de deferimento"),
        "by_insurer": _campo("array", "seguradora, avisos, prazo, deferimento"),
        "status": _campo("array", "composição por status"),
    },
    instruction_md=(
        "Comparação exige a mesma régua para todos. Se uma seguradora tem "
        "poucos casos, diga o número — média de três sinistros não compara com "
        "média de trezentos, e apresentar as duas lado a lado sem essa ressalva "
        "produz uma conclusão errada com aparência de dado."),
)


# ==========================================================================
# 8. Briefing diário
# ==========================================================================

BRIEFING = Template(
    key="briefing.daily",
    name="Briefing Diário",
    description="Uma tela: o que aconteceu desde ontem e o que precisa de você hoje.",
    category="briefing", narrative_shape="action_led", audience="internal",
    visual_style="obsidian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Briefing"}},
        {"block": "kpis", "props": {"title": "Desde ontem"}},
        {"block": "callout", "props": {}},
        {"block": "actions", "props": {"eyebrow": "Sua fila",
                                       "title": "O que precisa de você hoje"}},
        {"block": "split", "props": {
            "left": [{"block": "chart", "props": {"title": "Atendimentos por hora"}}],
            "right": [{"block": "ring", "props": {"title": "Fila"}}]}},
        {"block": "table", "props": {"eyebrow": "Atenção",
                                     "title": "Conversas paradas há mais de 24h"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "since": _campo("object", "janela do briefing"),
        "queue": _campo("array", "itens que exigem ação humana"),
        "stalled": _campo("array", "conversas paradas"),
    },
    instruction_md=(
        "Briefing é lido em pé, no celular, antes do café. Máximo de uma tela "
        "até a fila de ações.\n\n"
        "Nada de histórico. Só o que mudou desde o último briefing e o que "
        "está esperando por uma pessoa."),
)


CATALOGO: tuple[Template, ...] = (
    PANORAMA, COMISSOES, FUNIL, PESQUISA,
    DOSSIE_CLIENTE, RENOVACOES, SINISTROS, BRIEFING,
)

POR_CHAVE: dict[str, Template] = {t.key: t for t in CATALOGO}


def escolher(categoria: str = "", texto: str = "") -> Template:
    """Escolha determinística do template a partir da intenção.

    Léxico, não embedding: barato, explicável e auditável. Quando não há sinal
    claro, o panorama executivo é o padrão — é o que serve melhor a um pedido
    genérico de 'me faz um relatório'.
    """
    alvo = f"{categoria} {texto}".lower()
    pistas = {
        "financial.commissions": ("comiss", "receita", "faturamento", "financeir", "fechamento"),
        "commercial.pipeline": ("funil", "cotaç", "venda", "convers", "pipeline", "produção comercial"),
        "research.market_brief": ("pesquis", "dossiê de mercado", "estudo", "concorr", "regulaç", "circular"),
        "portfolio.client_dossier": ("dossiê do", "segurado", "cliente ", "apólices do"),
        "renewals.radar": ("renovaç", "vencimento", "a vencer", "renewal"),
        "claims.performance": ("sinistr", "regulaç de sinistro", "aviso de sinistro"),
        "briefing.daily": ("briefing", "resumo do dia", "hoje", "desde ontem"),
        "executive.panorama": ("panorama", "executiv", "visão geral", "resultado"),
    }
    melhor, pontos = PANORAMA, 0
    for chave, termos in pistas.items():
        p = sum(3 if t in alvo else 0 for t in termos)
        if p > pontos:
            melhor, pontos = POR_CHAVE[chave], p
    return melhor
