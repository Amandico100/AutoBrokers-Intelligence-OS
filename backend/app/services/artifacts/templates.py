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


# ==========================================================================
# 9 a 12. Peças do Intelligence Fabric — SPEC-059 §17.1
# ==========================================================================
#
# O briefing diário já existia como `briefing.daily`. A SPEC-059 nomeia a peça
# como `briefing.daily_operational` e acrescenta outras quatro. A chave antiga
# **não é removida**: peças já publicadas apontam para ela, e chave de template
# é referência de artefato, não rótulo de menu.

BRIEFING_OPERACIONAL = Template(
    key="briefing.daily_operational",
    name="Briefing Diário Operacional",
    description="O que precisa de você hoje, o que já foi resolvido e o que dá para delegar.",
    category="briefing", narrative_shape="action_led", audience="internal",
    visual_style="obsidian", page_format="web",
    composition=BRIEFING.composition,
    data_contract={
        "headline": _campo("string", "uma frase que resume o dia"),
        "sections": _campo("array", "seções do Briefing Spec, já priorizadas"),
        "missing_data": _campo("array", "o que não pôde ser afirmado no período", False),
    },
    instruction_md=(
        "Briefing é lido em pé, no celular, antes do café. Máximo de uma tela "
        "até a fila de ações.\n\n"
        "Seção sem item não vira texto. 'Nenhum risco identificado' ocupa espaço "
        "e ensina o leitor a pular seções.\n\n"
        "Todo número vem de um Finding já gravado. Esta peça não calcula nada."),
)

BRIEFING_EXECUTIVO = Template(
    key="briefing.weekly_executive",
    name="Briefing Executivo Semanal",
    description="Visão gerencial da semana: mudanças, gargalos, resultados e decisões.",
    category="briefing", narrative_shape="verdict_led", audience="internal",
    visual_style="aurora", page_format="a4",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Briefing executivo"}},
        {"block": "kpis", "props": {"title": "A semana em números"}},
        {"block": "verdict", "props": {}},
        {"block": "actions", "props": {"eyebrow": "Decisões",
                                       "title": "O que depende de você"}},
        {"block": "callout", "props": {}},
        {"block": "table", "props": {"eyebrow": "Entregue",
                                     "title": "O que ficou pronto"}},
        {"block": "prose", "props": {"eyebrow": "Transparência",
                                     "title": "O que ainda não dá para afirmar"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "headline": _campo("string", "a frase que resume a semana"),
        "executive_summary": _campo("string", "resumo executivo em uma frase"),
        "sections": _campo("array", "seções do Briefing Spec"),
        "missing_data": _campo("array", "limitações declaradas", False),
    },
    instruction_md=(
        "Abra pelo veredito: o gestor lê a capa e o primeiro parágrafo.\n\n"
        "Indicador sem período e sem fonte não entra. 'Melhorou' sem base de "
        "comparação é ruído com aparência de dado.\n\n"
        "Quando não houve amostra suficiente, diga isso. 'A qualidade permaneceu "
        "estável' sem conversas auditadas é uma afirmação falsa."),
)

ALERTA_CRITICO = Template(
    key="briefing.critical_alert_detail",
    name="Detalhe de Alerta Crítico",
    description="O que aconteceu, a evidência, o impacto e a ação — em uma página.",
    category="briefing", narrative_shape="verdict_led", audience="internal",
    visual_style="obsidian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Alerta"}},
        {"block": "callout", "props": {"tone": "negative"}},
        {"block": "table", "props": {"eyebrow": "Evidência",
                                     "title": "O que sustenta esta conclusão"}},
        {"block": "actions", "props": {"title": "O que fazer agora"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "fato": _campo("string", "o fato observado, com número e período"),
        "evidencias": _campo("array", "fontes com tier de confiança"),
        "acoes": _campo("array", "o que fazer, em ordem"),
    },
    instruction_md=(
        "Alerta crítico exige evidência Tier 0, 1 ou 2. Inferência de modelo "
        "não sustenta alerta — se a única base é hipótese, isto não é alerta.\n\n"
        "Separe o fato da leitura em blocos distintos. Misturar os dois é o que "
        "destrói a confiança quando alguém confere."),
)

DOSSIE_OPORTUNIDADE = Template(
    key="briefing.opportunity_dossier",
    name="Dossiê de Oportunidade",
    description="Uma oportunidade detectada: evidência, impacto, custo e o que fazer.",
    category="briefing", narrative_shape="narrative_led", audience="internal",
    visual_style="aurora", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Oportunidade"}},
        {"block": "verdict", "props": {}},
        {"block": "kpis", "props": {"title": "O tamanho disso"}},
        {"block": "prose", "props": {"eyebrow": "Por que agora",
                                     "title": "O que mudou"}},
        {"block": "actions", "props": {"title": "Como aproveitar"}},
        {"block": "callout", "props": {}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "tese": _campo("string", "a oportunidade em uma frase"),
        "evidencias": _campo("array", "o que sustenta"),
        "custo": _campo("object", "faixa estimada, marcada como estimativa", False),
    },
    instruction_md=(
        "Oportunidade sem número verificável é conversa de vendedor. Se o "
        "impacto não pode ser calculado, diga que é estimativa e mostre o "
        "método.\n\n"
        "Nunca prometa resultado garantido — no máximo uma frase comercial leve."),
)

RADAR_DE_DEMANDA = Template(
    key="briefing.demand_radar_admin",
    name="Radar de Demanda",
    description="O que várias corretoras querem delegar — agregado e anônimo.",
    category="briefing", narrative_shape="comparative", audience="internal",
    visual_style="meridian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Radar de demanda"}},
        {"block": "kpis", "props": {"title": "O funil de demanda"}},
        {"block": "ranking", "props": {"eyebrow": "Prioridade",
                                       "title": "O que mais pedem"}},
        {"block": "table", "props": {"eyebrow": "Detalhe",
                                     "title": "Necessidades por status"}},
        {"block": "callout", "props": {}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "clusters": _campo("array", "necessidades com contagem de corretoras"),
        "gaps": _campo("array", "lacunas de capacidade abertas", False),
    },
    instruction_md=(
        "Esta peça é de PLATAFORMA e sai anonimizada. Nenhum nome de corretora, "
        "nenhuma citação literal, nenhum dado de segurado.\n\n"
        "Ordene por número de corretoras distintas, não por número de pedidos: "
        "dez pedidos de uma corretora são um caso; um pedido de dez corretoras "
        "é um produto."),
)


# ==========================================================================
# 14 a 19. Peças de pesquisa — SPEC-060 §27.1
# ==========================================================================
#
# O `research.market_brief` acima continua sendo o dossiê narrativo. O que
# entra aqui são as SEIS formas que a pesquisa produz e que o dossiê não
# atende, porque a forma narrativa é outra:
#
#   evidence pack     a fonte é o assunto, não o pano de fundo
#   matriz            comparação lado a lado é o argumento inteiro
#   auditoria         lista priorizada de conserto, não análise
#   radar regulatório cronologia — o que mudou e desde quando vale
#   planilha          dado operacional para trabalhar, não para ler
#   mudança           antes e depois de UMA página
#
# Forçar qualquer uma delas dentro do dossiê produz aquele documento que tem
# tudo e não responde nada.


EVIDENCE_PACK = Template(
    key="research.evidence_pack",
    name="Pacote de Evidências",
    description="Cada afirmação com a fonte que a sustenta, o trecho citado e a data.",
    category="research", narrative_shape="precision_led", audience="internal",
    visual_style="obsidian", page_format="a4",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Evidências"}},
        {"block": "callout", "props": {}},
        {"block": "table", "props": {"eyebrow": "Afirmação por afirmação",
                                     "title": "O que foi verificado"}},
        {"block": "prose", "props": {"eyebrow": "Limites",
                                     "title": "O que este pacote NÃO prova"}},
        {"block": "sources", "props": {"title": "Fontes",
                                       "note": "Cada linha acima aponta para uma "
                                               "destas fontes, com a data em que "
                                               "foi lida."}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "claims": _campo("array", "afirmações com status, confiança e citações"),
        "contradictions": _campo("array", "onde as fontes discordam", False),
        "limitations": _campo("array", "o que não foi possível verificar"),
    },
    instruction_md=(
        "Esta peça existe para ser CONFERIDA. Quem a recebe vai clicar nas "
        "fontes — escreva pensando nisso.\n\n"
        "Afirmação sem citação não entra, mesmo que pareça óbvia. Afirmação "
        "contraditada entra, marcada como contraditada, com as duas fontes: "
        "esconder a divergência é o pior serviço possível.\n\n"
        "A seção de limites é obrigatória e não é formalidade. 'Não foi "
        "possível ler a íntegra da circular' é mais útil ao corretor do que "
        "um parágrafo confiante escrito a partir do resumo."),
)


MATRIZ_CONCORRENTES = Template(
    key="research.competitor_matrix",
    name="Comparativo de Concorrentes",
    description="Corretoras da região lado a lado: presença, produtos e posicionamento.",
    category="research", narrative_shape="comparative", audience="internal",
    visual_style="meridian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Comparativo"}},
        {"block": "verdict", "props": {}},
        {"block": "table", "props": {"eyebrow": "Lado a lado",
                                     "title": "Como cada uma se apresenta"}},
        {"block": "ranking", "props": {"eyebrow": "Presença",
                                       "title": "Quem aparece mais"}},
        {"block": "prose", "props": {"eyebrow": "Leitura",
                                     "title": "O que isso significa para você"}},
        {"block": "actions", "props": {"title": "Onde dá para se diferenciar"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "competitors": _campo("array", "concorrentes com atributos comparados"),
        "dimensions": _campo("array", "as dimensões de comparação"),
        "opportunities": _campo("array", "lacunas observadas", False),
    },
    instruction_md=(
        "Compare o que é PÚBLICO e observável: site, produtos anunciados, "
        "canais, avaliações públicas. Nada de estimar faturamento, carteira ou "
        "comissão de terceiro — é invenção com aparência de dado.\n\n"
        "Célula sem informação fica vazia e declarada como 'não informado'. "
        "Preencher com suposição arruína a matriz inteira, porque o leitor não "
        "tem como saber quais células são reais.\n\n"
        "A conclusão é sobre O QUE FAZER, não sobre quem é melhor."),
)


AUDITORIA_SITE = Template(
    key="research.site_audit",
    name="Diagnóstico do Site",
    description="O que impede o site da corretora de ser encontrado e entendido.",
    category="research", narrative_shape="precision_led", audience="internal",
    visual_style="obsidian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Diagnóstico"}},
        {"block": "kpis", "props": {"title": "O estado atual"}},
        {"block": "ranking", "props": {"eyebrow": "Prioridade",
                                       "title": "Consertar nesta ordem"}},
        {"block": "table", "props": {"eyebrow": "Página por página",
                                     "title": "O que foi encontrado"}},
        {"block": "callout", "props": {}},
        {"block": "actions", "props": {"title": "O que fazer primeiro"}},
        {"block": "footer", "props": {"disclaimer":
            "Diagnóstico técnico do que está publicado. Buscadores decidem "
            "posicionamento por critérios próprios — nenhuma correção aqui "
            "garante posição."}},
    ],
    data_contract={
        "pages": _campo("array", "páginas analisadas com achados"),
        "findings": _campo("array", "achados ordenados por impacto e esforço"),
        "quick_wins": _campo("array", "correções de esforço baixo", False),
    },
    instruction_md=(
        "Ordene por IMPACTO sobre ESFORÇO. O corretor não vai fazer trinta "
        "correções — vai fazer três. Diga quais três.\n\n"
        "Escreva o achado no que ele custa, não no jargão: 'quem procura seguro "
        "na sua cidade não encontra seu telefone' vale mais que 'ausência de "
        "marcação LocalBusiness'. O termo técnico pode vir depois, entre "
        "parênteses, para quem for executar.\n\n"
        "NUNCA prometa posição no Google. O rodapé diz isso e o texto não pode "
        "contradizê-lo."),
)


RADAR_REGULATORIO = Template(
    key="research.regulatory_radar",
    name="Radar Regulatório",
    description="O que mudou na regulação do seguro, desde quando vale e o que exige ação.",
    category="research", narrative_shape="chronological", audience="internal",
    visual_style="obsidian", page_format="a4",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Radar regulatório"}},
        {"block": "callout", "props": {}},
        {"block": "table", "props": {"eyebrow": "Linha do tempo",
                                     "title": "O que mudou e quando passa a valer"}},
        {"block": "prose", "props": {"eyebrow": "Impacto",
                                     "title": "O que muda na sua operação"}},
        {"block": "actions", "props": {"title": "O que precisa ser feito"}},
        {"block": "sources", "props": {"title": "Publicações oficiais",
                                       "note": "Somente SUSEP, CNSP, DOU e "
                                               "legislação. Notícia sobre a norma "
                                               "não substitui a norma."}},
        {"block": "footer", "props": {"disclaimer":
            "Resumo informativo. O texto oficial publicado prevalece."}},
    ],
    data_contract={
        "changes": _campo("array", "mudanças com data de publicação e vigência"),
        "impact_md": _campo("string", "impacto operacional em prosa"),
        "deadlines": _campo("array", "prazos com data", False),
    },
    instruction_md=(
        "Aqui a fonte oficial é OBRIGATÓRIA. Nenhuma mudança normativa entra "
        "apoiada só em imprensa — §16.4 recusa o claim, e esta peça também.\n\n"
        "Separe sempre DATA DE PUBLICAÇÃO de DATA DE VIGÊNCIA. Confundir as "
        "duas faz a corretora agir cedo demais ou tarde demais, e as duas doem.\n\n"
        "Se algo ainda está em consulta pública, diga que é proposta. Tratar "
        "minuta como norma vigente é o erro mais caro deste documento."),
)


PLANILHA_EMPRESAS = Template(
    key="research.company_list",
    name="Lista de Empresas",
    description="Empresas do segmento e da região, com o motivo de cada uma estar na lista.",
    category="research", narrative_shape="precision_led", audience="internal",
    visual_style="meridian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Prospecção"}},
        {"block": "kpis", "props": {"title": "O que a busca encontrou"}},
        {"block": "callout", "props": {}},
        {"block": "table", "props": {"eyebrow": "As empresas",
                                     "title": "Ordenadas por aderência"}},
        {"block": "prose", "props": {"eyebrow": "Como usar",
                                     "title": "O que fazer com esta lista"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {"disclaimer":
            "Dados de cadastro público de estabelecimentos. Confirme antes de "
            "abordar: registro público envelhece."}},
    ],
    data_contract={
        "companies": _campo("array", "empresas com fit, motivo e dados públicos"),
        "criteria": _campo("array", "os critérios usados no fit"),
        "excluded": _campo("array", "quantas foram descartadas e por quê", False),
    },
    instruction_md=(
        "Toda linha carrega o MOTIVO de estar ali. Score sem motivo é palpite "
        "com número, e o corretor não tem como discordar de um palpite.\n\n"
        "Somente dado público de estabelecimento: nome, endereço, telefone "
        "comercial, site, segmento. Nenhum dado pessoal de sócio, nenhuma "
        "inferência sobre renda, porte financeiro ou perfil de risco.\n\n"
        "Esta peça ENTREGA A LISTA. Ela não aborda ninguém: qualquer contato "
        "sai pelo caminho normal, com a aprovação que ele exige."),
)


RELATORIO_DE_MUDANCA = Template(
    key="research.change_report",
    name="O Que Mudou",
    description="Antes e depois de uma página acompanhada, e por que isso importa.",
    category="research", narrative_shape="chronological", audience="internal",
    visual_style="obsidian", page_format="web",
    composition=[
        {"block": "cover", "props": {"eyebrow": "Mudança detectada"}},
        {"block": "verdict", "props": {}},
        {"block": "split", "props": {"eyebrow": "Comparação",
                                     "title": "Antes e depois"}},
        {"block": "prose", "props": {"eyebrow": "Leitura",
                                     "title": "O que isso significa"}},
        {"block": "actions", "props": {"title": "O que fazer"}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ],
    data_contract={
        "monitor": _campo("object", "o que está sendo acompanhado e desde quando"),
        "before": _campo("string", "trecho anterior"),
        "after": _campo("string", "trecho atual"),
        "why_it_matters": _campo("string", "por que a mudança importa"),
    },
    instruction_md=(
        "Mostre o TRECHO que mudou, não a página inteira. A página inteira "
        "obriga o leitor a procurar a diferença, e ele não vai.\n\n"
        "Se a mudança for cosmética — data de atualização, contador, banner — "
        "esta peça não deveria existir. Ela só é composta quando a mudança é "
        "relevante; ver §18.3.\n\n"
        "Diga a data das duas leituras. 'Mudou' sem quando é inútil para quem "
        "precisa avisar um cliente."),
)


CATALOGO: tuple[Template, ...] = (
    PANORAMA, COMISSOES, FUNIL, PESQUISA,
    DOSSIE_CLIENTE, RENOVACOES, SINISTROS, BRIEFING,
    BRIEFING_OPERACIONAL, BRIEFING_EXECUTIVO, ALERTA_CRITICO,
    DOSSIE_OPORTUNIDADE, RADAR_DE_DEMANDA,
    EVIDENCE_PACK, MATRIZ_CONCORRENTES, AUDITORIA_SITE,
    RADAR_REGULATORIO, PLANILHA_EMPRESAS, RELATORIO_DE_MUDANCA,
)

POR_CHAVE: dict[str, Template] = {t.key: t for t in CATALOGO}


def escolher(categoria: str = "", texto: str = "") -> Template:
    """Escolha determinística do template a partir da intenção.

    Léxico, não embedding: barato, explicável e auditável. Quando não há sinal
    claro, o panorama executivo é o padrão — é o que serve melhor a um pedido
    genérico de 'me faz um relatório'.
    """
    alvo = f"{categoria} {texto}".lower()
    # As peças de pesquisa da SPEC-060 são mais específicas que o dossiê e
    # vêm ANTES dele: "comparativo de concorrentes" e "o que a SUSEP mudou"
    # antes caíam no dossiê genérico porque era o único que existia. Por isso
    # `concorr` e `regulaç` saíram das pistas do `market_brief` — deixá-las nos
    # dois criaria empate, e empate aqui é decidido por ordem de dicionário,
    # que é o tipo de comportamento que ninguém consegue explicar depois.
    pistas = {
        "financial.commissions": ("comiss", "receita", "faturamento", "financeir", "fechamento"),
        "commercial.pipeline": ("funil", "cotaç", "venda", "convers", "pipeline", "produção comercial"),
        "research.evidence_pack": ("evidência", "evidencia", "comprov", "é verdade",
                                   "checagem", "verificar se", "fact"),
        "research.competitor_matrix": ("concorr", "comparativo de corretora",
                                       "quem mais atua", "competidor"),
        "research.site_audit": ("meu site", "nosso site", "seo", "aeo",
                                "ser encontrado", "auditoria de site"),
        "research.regulatory_radar": ("regulaç", "susep", "cnsp", "circular",
                                      "resolução", "norma", "legislaç"),
        "research.company_list": ("lista de empresas", "prospecç", "empresas de",
                                  "encontrar empresas", "potenciais clientes"),
        "research.change_report": ("o que mudou", "mudança na página", "monitor",
                                   "acompanhar a página"),
        "research.market_brief": ("pesquis", "dossiê de mercado", "estudo", "mercado de"),
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
