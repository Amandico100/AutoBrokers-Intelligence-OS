"""Gera o Visual Acceptance Pack da SPEC-057 com a marca real de uma corretora.

    python backend/tools/gerar_visual_acceptance_pack.py

Usa a Resulta Seguros como cobaia porque ela é o caso real mais próximo: logo
PNG com transparência, duas cores, site em WordPress. Se a peça fica boa com
essa marca, fica boa com quase qualquer corretora — e se algum passo depender
de dado que a Resulta não tem, o defeito aparece aqui e não no cliente.
"""

from __future__ import annotations

import base64
import importlib.util
import os
import sys
import types
from datetime import datetime, timezone

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAIDA = os.path.abspath(os.path.join(RAIZ, "..", "docs", "canon", "visual-acceptance"))

# Monta a hierarquia real de pacotes sem executar os `__init__.py`, que puxam
# FastAPI e o resto do app. Os módulos usam import relativo entre si
# (`..brand.system`), então a árvore precisa existir de verdade — pacote
# sintético raso quebra o `..`.
for nome in ("app", "app.services", "app.services.brand", "app.services.artifacts"):
    if nome not in sys.modules:
        pkg = types.ModuleType(nome)
        pkg.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = pkg


def _mod(caminho_pontos: str):
    arquivo = os.path.join(RAIZ, *caminho_pontos.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(caminho_pontos, arquivo)
    m = importlib.util.module_from_spec(spec)
    m.__package__ = caminho_pontos.rsplit(".", 1)[0]
    sys.modules[caminho_pontos] = m
    spec.loader.exec_module(m)
    return m


color = _mod("app.services.brand.color")
extract = _mod("app.services.brand.extract")
system = _mod("app.services.brand.system")

charts = _mod("app.services.artifacts.charts")
blocks = _mod("app.services.artifacts.blocks")
styles = _mod("app.services.artifacts.styles")
render = _mod("app.services.artifacts.render")
templates = _mod("app.services.artifacts.templates")


# --------------------------------------------------------------------------
# Marca real
# --------------------------------------------------------------------------

LOGO_LOCAL = os.path.join(os.path.dirname(__file__), "_resulta_logo.png")


def carregar_marca() -> dict:
    dados = None
    if os.path.exists(LOGO_LOCAL):
        dados = open(LOGO_LOCAL, "rb").read()

    if dados:
        a = extract.analisar_logo(dados)
        primaria, acento = a.primary, a.accent
        logo = {"data_uri": "data:image/png;base64," + base64.b64encode(dados).decode(),
                "width": a.width, "height": a.height}
        print(f"  logo: {a.width}x{a.height}  {primaria} / {acento}  "
              f"confianca={a.confidence}")
    else:
        # Valores medidos do logo real, para o pack rodar mesmo sem o arquivo.
        primaria, acento, logo = "#1D5579", "#EE7501", None
        print("  logo ausente — usando as cores medidas do arquivo original")

    sistema = system.build_design_system(
        primaria, acento,
        typography={"body": "'Montserrat', " + styles.SANS,
                    "display": "'Montserrat', " + styles.SANS,
                    "source": "Google Fonts declarada no site"})

    return {
        "name": "Resulta Seguros",
        "legal_name": "Resulta Corretora de Seguros Ltda.",
        "tagline": "Proteção e tranquilidade através de soluções eficientes",
        "palette": sistema,
        "typography": sistema["typography"],
        "logo": logo,
        "susep_code": "20.2185.4",
        "contact": {"phones": ["(48) 3364-6664"], "city": "Florianópolis - SC"},
        "is_fallback": False,
    }


AGORA = datetime(2026, 7, 25, tzinfo=timezone.utc)

FONTES = [
    {"label": "Carteira", "detail": "base de apólices da corretora",
     "as_of": "2026-07-25", "as_of_label": "25/07/2026 06:00"},
    {"label": "Comissões", "detail": "extratos conciliados das seguradoras",
     "as_of": "2026-06-30", "as_of_label": "fechamento de junho"},
    {"label": "Atendimento", "detail": "conversas registradas no WhatsApp",
     "as_of": "2026-07-25", "as_of_label": "25/07/2026 07:40"},
]

MESES = ["ago", "set", "out", "nov", "dez", "jan", "fev", "mar", "abr", "mai", "jun", "jul"]


# --------------------------------------------------------------------------
# Dados de amostra — realistas para uma corretora média em SC
# --------------------------------------------------------------------------

def dados_panorama() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Panorama executivo", "period": "Julho de 2026",
            "title": "A carteira cresceu, mas a renovação de frota está travando",
            "subtitle": "Resultado consolidado do mês, com comparação contra junho "
                        "e contra o mesmo mês do ano passado.",
            "verdict": "Produção 12,4% acima de junho, puxada por auto e residencial. "
                       "O ponto de atenção é frota: 6 apólices vencem em 30 dias e "
                       "nenhuma teve contato registrado.",
            "headline_label": "Prêmio emitido no mês", "headline_value": "R$ 1.284.700",
            "headline_delta": 12.4, "headline_better": "up"}},
        {"block": "kpis", "props": {
            "eyebrow": "Os números do período", "title": "Como a corretora fechou",
            "items": [
                {"label": "Prêmio emitido", "value": "R$ 1,28 mi", "delta": 12.4,
                 "since": "vs. junho", "spark": [880, 910, 985, 940, 1030, 1142, 1284]},
                {"label": "Comissão", "value": "R$ 231,2", "unit": "mil", "delta": 9.8,
                 "since": "vs. junho", "spark": [162, 168, 179, 171, 188, 210, 231]},
                {"label": "Apólices vigentes", "value": "2.847", "delta": 3.1,
                 "since": "vs. junho"},
                {"label": "Ticket médio", "value": "R$ 4.512", "delta": -2.3,
                 "since": "vs. junho", "better": "up"},
                {"label": "Sinistralidade", "value": "38,4", "unit": "%", "delta": -4.1,
                 "since": "vs. junho", "better": "down"},
                {"label": "Renovação", "value": "87,2", "unit": "%", "delta": 1.4,
                 "since": "vs. junho"},
            ]}},
        {"block": "verdict", "props": {
            "text": "O crescimento veio de auto e residencial, ramos de ticket menor "
                    "e renovação mais previsível — o que explica o ticket médio cair "
                    "2,3% mesmo com a produção subindo.",
            "note": "A queda no ticket não é deterioração de carteira; é mudança de "
                    "composição. Vale acompanhar mais dois meses antes de agir."}},
        {"block": "chart", "props": {
            "eyebrow": "Evolução", "title": "Produção mês a mês",
            "lede": "Prêmio emitido nos últimos doze meses, em milhares de reais.",
            "value_type": "short", "labels": MESES,
            "series": [
                {"name": "2026", "values": [742, 768, 810, 795, 858, 902, 874, 940,
                                            985, 1030, 1142, 1284]},
                {"name": "2025", "values": [688, 702, 731, 719, 764, 798, 776, 812,
                                            841, 869, 918, 1004]},
            ]}},
        {"block": "split", "props": {
            "sidebar": True,
            "left": [{"block": "ranking", "props": {
                "eyebrow": "Concentração", "title": "Maiores clientes por prêmio",
                "value_type": "currency_short", "highlight": 3,
                "items": [
                    {"rotulo": "Transportadora Sul Log", "valor": 184300, "nota": "frota · 42 veículos"},
                    {"rotulo": "Condomínio Ilha Bela", "valor": 96800, "nota": "condomínio"},
                    {"rotulo": "Metalúrgica Campeche", "valor": 78400, "nota": "empresarial"},
                    {"rotulo": "Rede Farmácias Ativa", "valor": 61200, "nota": "empresarial"},
                    {"rotulo": "Construtora Norte", "valor": 54900, "nota": "riscos de engenharia"},
                    {"rotulo": "Colégio São Marcos", "valor": 43100, "nota": "patrimonial"},
                    {"rotulo": "Frigorífico Trindade", "valor": 38700, "nota": "frota · 11 veículos"},
                ]}}],
            "right": [{"block": "donut", "props": {
                "eyebrow": "Composição", "title": "Prêmio por ramo",
                "value_type": "currency_short",
                "center_value": "R$ 1,28 mi", "center_label": "no mês",
                "slices": [
                    {"rotulo": "Auto", "valor": 462000},
                    {"rotulo": "Frota", "valor": 289000},
                    {"rotulo": "Empresarial", "valor": 198000},
                    {"rotulo": "Residencial", "valor": 141000},
                    {"rotulo": "Vida e previdência", "valor": 108000},
                    {"rotulo": "Demais ramos", "valor": 86700},
                ]}}]}},
        {"block": "callout", "props": {
            "tone": "warning", "title": "Concentração acima do limite prudencial",
            "text": "Os **cinco maiores clientes** respondem por **37,1%** do prêmio "
                    "do mês. Acima de 40% a carteira fica exposta à saída de um único "
                    "cliente. A Transportadora Sul Log sozinha é 14,3%."}},
        {"block": "actions", "props": {
            "eyebrow": "Plano", "title": "O que fazer nas próximas semanas",
            "items": [
                {"title": "Abrir renovação das 6 apólices de frota",
                 "detail": "Vencem entre 12 e 28 de agosto e nenhuma teve contato "
                           "registrado. Juntas somam R$ 312 mil em prêmio.",
                 "owner": "Comercial", "due": "até 02/08", "impact": "R$ 312 mil"},
                {"title": "Revisar cobertura da Sul Log antes da renovação",
                 "detail": "A frota cresceu de 34 para 42 veículos desde a última "
                           "vigência; 8 veículos podem estar sem cobertura.",
                 "owner": "Técnico", "due": "até 08/08", "impact": "risco"},
                {"title": "Campanha de residencial na base de auto",
                 "detail": "1.104 clientes de auto sem residencial. Foi o ramo que "
                           "mais cresceu no mês, com o menor custo de aquisição.",
                 "owner": "Marketing", "due": "até 15/08", "impact": "R$ 90 mil est."},
            ]}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ]


def dados_comissoes() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Fechamento financeiro", "period": "Junho de 2026",
            "title": "Comissão de junho: R$ 210,4 mil",
            "subtitle": "Receita conciliada com os extratos das seguradoras. "
                        "Diferenças em aberto estão listadas no fim.",
            "headline_label": "Comissão líquida", "headline_value": "R$ 210.412,80",
            "headline_delta": 11.7}},
        {"block": "kpis", "props": {
            "title": "Receita do período",
            "items": [
                {"label": "Prêmio intermediado", "value": "R$ 1,14 mi", "delta": 10.9,
                 "since": "vs. maio"},
                {"label": "Comissão líquida", "value": "R$ 210,4 mil", "delta": 11.7,
                 "since": "vs. maio"},
                {"label": "Taxa média", "value": "18,4", "unit": "%", "delta": 0.7,
                 "since": "vs. maio"},
                {"label": "A receber", "value": "R$ 47,8 mil", "delta": -18.2,
                 "since": "vs. maio", "better": "down"},
            ]}},
        {"block": "waterfall", "props": {
            "eyebrow": "Ponte", "title": "De onde veio a variação",
            "lede": "Decomposição da diferença entre maio e junho.",
            "value_type": "currency_short",
            "steps": [
                {"rotulo": "Maio", "valor": 188350, "tipo": "inicial"},
                {"rotulo": "Novas", "valor": 31200, "tipo": "delta"},
                {"rotulo": "Renovações", "valor": 14800, "tipo": "delta"},
                {"rotulo": "Endossos", "valor": 4900, "tipo": "delta"},
                {"rotulo": "Cancelamentos", "valor": -19100, "tipo": "delta"},
                {"rotulo": "Ajuste taxa", "valor": -9737, "tipo": "delta"},
                {"rotulo": "Junho", "valor": 210413, "tipo": "final"},
            ]}},
        {"block": "table", "props": {
            "eyebrow": "Detalhamento", "title": "Comissão por seguradora",
            "columns": [
                {"key": "seg", "label": "Seguradora"},
                {"key": "apol", "label": "Apólices", "align": "right"},
                {"key": "premio", "label": "Prêmio", "align": "right", "format": "currency"},
                {"key": "taxa", "label": "Taxa", "align": "right", "format": "percent"},
                {"key": "com", "label": "Comissão", "align": "right", "format": "currency"},
                {"key": "st", "label": "Conciliação", "pill": True},
            ],
            "rows": [
                {"seg": "Porto Seguro", "apol": 412, "premio": 386400.0, "taxa": 19.2,
                 "com": 74188.8, "st": "conferido", "st_tone": "positive"},
                {"seg": "Allianz", "apol": 218, "premio": 241900.0, "taxa": 18.5,
                 "com": 44751.5, "st": "conferido", "st_tone": "positive"},
                {"seg": "Bradesco Seguros", "apol": 187, "premio": 198300.0, "taxa": 17.8,
                 "com": 35297.4, "st": "conferido", "st_tone": "positive"},
                {"seg": "SulAmérica", "apol": 143, "premio": 154700.0, "taxa": 18.0,
                 "com": 27846.0, "st": "3 divergências", "st_tone": "warning"},
                {"seg": "Tokio Marine", "apol": 96, "premio": 87200.0, "taxa": 17.5,
                 "com": 15260.0, "st": "conferido", "st_tone": "positive"},
                {"seg": "HDI", "apol": 61, "premio": 52400.0, "taxa": 16.9,
                 "com": 8855.6, "st": "conferido", "st_tone": "positive"},
                {"seg": "Demais", "apol": 38, "premio": 22900.0, "taxa": 18.4,
                 "com": 4213.5, "st": "conferido", "st_tone": "positive"},
            ],
            "total": {"seg": "Total", "apol": 1155, "premio": 1143800.0,
                      "taxa": None, "com": 210412.8, "st": ""}}},
        {"block": "split", "props": {
            "left": [{"block": "donut", "props": {
                "title": "Receita por ramo", "value_type": "currency_short",
                "center_value": "R$ 210 mil", "center_label": "comissão",
                "slices": [
                    {"rotulo": "Auto", "valor": 82400},
                    {"rotulo": "Frota", "valor": 51200},
                    {"rotulo": "Empresarial", "valor": 34800},
                    {"rotulo": "Residencial", "valor": 22100},
                    {"rotulo": "Demais", "valor": 19912},
                ]}}],
            "right": [{"block": "ranking", "props": {
                "title": "Maiores comissões unitárias", "value_type": "currency",
                "highlight": 2, "max": 6,
                "items": [
                    {"rotulo": "Sul Log — frota", "valor": 34417.0},
                    {"rotulo": "Ilha Bela — condomínio", "valor": 17424.0},
                    {"rotulo": "Metalúrgica Campeche", "valor": 13877.0},
                    {"rotulo": "Rede Ativa", "valor": 10404.0},
                    {"rotulo": "Construtora Norte", "valor": 9333.0},
                    {"rotulo": "Colégio São Marcos", "valor": 7327.0},
                ]}}]}},
        {"block": "callout", "props": {
            "tone": "warning", "title": "3 divergências em aberto na SulAmérica",
            "text": "Somam **R$ 4.128,90** entre o extrato e o esperado pela carteira. "
                    "Todas em apólices de auto com endosso em junho — o padrão sugere "
                    "recálculo de comissão sobre endosso, não erro de lançamento."}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ]


def dados_briefing() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Briefing", "period": "Sexta, 25 de julho",
            "title": "4 coisas precisam de você hoje",
            "verdict": "Uma renovação de R$ 84 mil vence segunda e o cliente não "
                       "respondeu duas tentativas. É a mais urgente.",
            "headline_label": "Aguardando pessoa", "headline_value": "4"}},
        {"block": "kpis", "props": {
            "title": "Desde ontem",
            "items": [
                {"label": "Atendimentos", "value": "38", "delta": 8.6, "since": "vs. ontem"},
                {"label": "Resolvidos pelo agente", "value": "31", "delta": 12.0,
                 "since": "vs. ontem"},
                {"label": "Escalados", "value": "4", "delta": -20.0,
                 "since": "vs. ontem", "better": "down"},
                {"label": "Tempo de resposta", "value": "1m42", "delta": -14.3,
                 "since": "vs. ontem", "better": "down"},
            ]}},
        {"block": "callout", "props": {
            "tone": "negative", "title": "Renovação em risco",
            "text": "**Metalúrgica Campeche** — apólice empresarial de R$ 84.200 vence "
                    "**segunda, 28/07**. Duas tentativas de contato sem resposta "
                    "desde 21/07."}},
        {"block": "actions", "props": {
            "eyebrow": "Sua fila", "title": "O que precisa de você hoje",
            "items": [
                {"title": "Ligar para Metalúrgica Campeche",
                 "detail": "Renovação vence em 3 dias, sem resposta no WhatsApp.",
                 "owner": "Comercial", "due": "hoje", "impact": "R$ 84,2 mil"},
                {"title": "Aprovar envio de proposta — Construtora Norte",
                 "detail": "O agente montou a proposta de riscos de engenharia e "
                           "está aguardando aprovação para enviar.",
                 "owner": "Você", "due": "hoje"},
                {"title": "Sinistro Sul Log: seguradora pediu documento",
                 "detail": "A Porto pediu boletim de ocorrência do veículo placa "
                           "MKJ-4471. Prazo de 5 dias corridos termina 29/07.",
                 "owner": "Sinistros", "due": "até 29/07"},
                {"title": "Conferir 3 divergências de comissão — SulAmérica",
                 "detail": "R$ 4.128,90 em aberto no fechamento de junho.",
                 "owner": "Financeiro", "due": "esta semana"},
            ]}},
        {"block": "split", "props": {
            "left": [{"block": "chart", "props": {
                "title": "Atendimentos por hora", "area": True, "value_type": "number",
                "labels": ["8h", "9h", "10h", "11h", "12h", "13h", "14h", "15h",
                           "16h", "17h", "18h"],
                "series": [{"name": "Hoje", "values": [2, 5, 7, 6, 3, 2, 5, 8, 6, 4, 1]}]}}],
            "right": [{"block": "ring", "props": {
                "title": "Resolução",
                "items": [{"label": "Sem humano", "value": 81.6}]}}]}},
        {"block": "table", "props": {
            "eyebrow": "Atenção", "title": "Conversas paradas há mais de 24h",
            "columns": [
                {"key": "cli", "label": "Cliente"},
                {"key": "as", "label": "Assunto"},
                {"key": "h", "label": "Parada há", "align": "right"},
                {"key": "st", "label": "Situação", "pill": True},
            ],
            "rows": [
                {"cli": "Metalúrgica Campeche", "as": "Renovação empresarial",
                 "h": "4 dias", "st": "sem resposta", "st_tone": "negative"},
                {"cli": "João Batista Ferreira", "as": "2ª via de apólice",
                 "h": "2 dias", "st": "aguardando cliente", "st_tone": "warning"},
                {"cli": "Condomínio Ilha Bela", "as": "Inclusão de cobertura",
                 "h": "31 horas", "st": "com o técnico", "st_tone": "info"},
            ]}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ]


def dados_funil() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Comercial", "period": "Julho de 2026",
            "title": "A perda está na cotação, não na prospecção",
            "subtitle": "Funil completo do mês, da oportunidade à apólice emitida.",
            "verdict": "Entram oportunidades suficientes. De cada 10 que chegam à "
                       "cotação, 4 nunca recebem proposta — é aí que o mês se perde.",
            "headline_label": "Convertido em apólice", "headline_value": "19,4%",
            "headline_delta": 2.8}},
        {"block": "kpis", "props": {
            "title": "O funil em números",
            "items": [
                {"label": "Oportunidades", "value": "412", "delta": 14.1, "since": "vs. junho"},
                {"label": "Cotações feitas", "value": "268", "delta": 9.4, "since": "vs. junho"},
                {"label": "Apólices emitidas", "value": "80", "delta": 18.5, "since": "vs. junho"},
                {"label": "Ciclo médio", "value": "11", "unit": "dias", "delta": -8.3,
                 "since": "vs. junho", "better": "down"},
            ]}},
        {"block": "funnel", "props": {
            "eyebrow": "Etapas", "title": "Onde as cotações se perdem",
            "lede": "A conversão entre etapas importa mais que o volume de cada uma.",
            "stages": [
                {"rotulo": "Oportunidades recebidas", "valor": 412},
                {"rotulo": "Contato feito", "valor": 361},
                {"rotulo": "Cotação solicitada", "valor": 268},
                {"rotulo": "Proposta enviada", "valor": 162},
                {"rotulo": "Proposta aceita", "valor": 94},
                {"rotulo": "Apólice emitida", "valor": 80},
            ]}},
        {"block": "verdict", "props": {
            "text": "A maior queda é de cotação para proposta: 39,6% das cotações não "
                    "viram proposta enviada. É o dobro da perda de qualquer outra etapa.",
            "note": "Em volume absoluto a maior perda é entre oportunidade e cotação "
                    "(144). Mas essa é filtragem natural de lead frio. A perda entre "
                    "cotação e proposta é trabalho já feito que não foi entregue."}},
        {"block": "split", "props": {
            "left": [{"block": "ranking", "props": {
                "title": "Conversão por produto", "value_type": "percent",
                "highlight": 2, "max": 7,
                "items": [
                    {"rotulo": "Residencial", "valor": 34.2, "nota": "62 emitidas"},
                    {"rotulo": "Auto", "valor": 27.8, "nota": "104 emitidas"},
                    {"rotulo": "Vida", "valor": 21.4, "nota": "18 emitidas"},
                    {"rotulo": "Empresarial", "valor": 14.6, "nota": "11 emitidas"},
                    {"rotulo": "Condomínio", "valor": 12.1, "nota": "4 emitidas"},
                    {"rotulo": "Frota", "valor": 9.7, "nota": "3 emitidas"},
                    {"rotulo": "Riscos de engenharia", "valor": 6.2, "nota": "1 emitida"},
                ]}}],
            "right": [{"block": "ring", "props": {
                "title": "Meta do mês",
                "items": [{"label": "80 de 95 apólices", "value": 84.2}]}}]}},
        {"block": "chart", "props": {
            "eyebrow": "Ritmo", "title": "Cotações por semana",
            "value_type": "number",
            "labels": ["S1", "S2", "S3", "S4"],
            "series": [
                {"name": "Julho", "values": [58, 74, 71, 65]},
                {"name": "Junho", "values": [61, 63, 58, 63]},
            ]}},
        {"block": "actions", "props": {
            "title": "Onde atacar primeiro",
            "items": [
                {"title": "Prazo máximo de 48h entre cotação e proposta",
                 "detail": "106 cotações do mês nunca viraram proposta. Metade delas "
                           "está parada há mais de 5 dias.",
                 "owner": "Comercial", "due": "esta semana", "impact": "maior perda"},
                {"title": "Dobrar esforço em residencial",
                 "detail": "Maior taxa de conversão (34,2%) e menor ciclo. É onde cada "
                           "hora de trabalho rende mais.",
                 "owner": "Comercial", "due": "agosto", "impact": "melhor retorno"},
                {"title": "Revisar abordagem de frota",
                 "detail": "9,7% de conversão com o maior ticket da casa. Ou o preço "
                           "está fora, ou a proposta não está chegando pronta.",
                 "owner": "Técnico", "due": "até 15/08"},
            ]}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ]


def dados_renovacoes() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Renovações", "period": "Próximos 60 dias",
            "title": "R$ 892 mil vencem até setembro",
            "subtitle": "Apólices ordenadas por urgência, não por valor.",
            "verdict": "9 apólices vencem nos próximos 15 dias e 4 delas ainda não "
                       "tiveram contato. Juntas somam R$ 218 mil.",
            "headline_label": "Prêmio a renovar", "headline_value": "R$ 892.400"}},
        {"block": "kpis", "props": {
            "title": "Janela de risco",
            "items": [
                {"label": "A vencer em 15 dias", "value": "9", "since": "R$ 218,4 mil"},
                {"label": "A vencer em 30 dias", "value": "24", "since": "R$ 431,7 mil"},
                {"label": "Sem contato", "value": "11", "since": "R$ 294,2 mil"},
                {"label": "Renovação histórica", "value": "87,2", "unit": "%",
                 "delta": 1.4, "since": "vs. ano passado"},
            ]}},
        {"block": "callout", "props": {
            "tone": "negative", "title": "4 apólices críticas sem contato",
            "text": "Vencem em menos de 15 dias e não têm nenhum registro de contato. "
                    "**R$ 218.400** em prêmio. A mais urgente vence em **3 dias**."}},
        {"block": "table", "props": {
            "eyebrow": "Agenda", "title": "Vencimentos ordenados por urgência",
            "columns": [
                {"key": "cli", "label": "Cliente"},
                {"key": "ramo", "label": "Ramo"},
                {"key": "venc", "label": "Vence em", "align": "right"},
                {"key": "premio", "label": "Prêmio", "align": "right", "format": "currency"},
                {"key": "st", "label": "Contato", "pill": True},
            ],
            "rows": [
                {"cli": "Metalúrgica Campeche", "ramo": "Empresarial", "venc": "3 dias",
                 "premio": 84200.0, "st": "sem resposta", "st_tone": "negative"},
                {"cli": "Transportadora Sul Log", "ramo": "Frota", "venc": "8 dias",
                 "premio": 62400.0, "st": "sem contato", "st_tone": "negative"},
                {"cli": "Colégio São Marcos", "ramo": "Patrimonial", "venc": "11 dias",
                 "premio": 43100.0, "st": "sem contato", "st_tone": "negative"},
                {"cli": "Frigorífico Trindade", "ramo": "Frota", "venc": "14 dias",
                 "premio": 28700.0, "st": "sem contato", "st_tone": "negative"},
                {"cli": "Condomínio Ilha Bela", "ramo": "Condomínio", "venc": "17 dias",
                 "premio": 96800.0, "st": "em negociação", "st_tone": "info"},
                {"cli": "Rede Farmácias Ativa", "ramo": "Empresarial", "venc": "22 dias",
                 "premio": 61200.0, "st": "proposta enviada", "st_tone": "positive"},
                {"cli": "Construtora Norte", "ramo": "Eng. risco", "venc": "26 dias",
                 "premio": 54900.0, "st": "em negociação", "st_tone": "info"},
                {"cli": "Auto Peças Kobrasol", "ramo": "Empresarial", "venc": "31 dias",
                 "premio": 22400.0, "st": "proposta enviada", "st_tone": "positive"},
            ],
            "total": {"cli": "8 de 24 apólices", "ramo": "", "venc": "",
                      "premio": 453700.0, "st": ""}}},
        {"block": "stacked", "props": {
            "eyebrow": "Distribuição", "title": "Vencimentos por semana e ramo",
            "value_type": "currency_short",
            "categories": ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6",
                           "Sem 7", "Sem 8"],
            "series": [
                {"name": "Frota", "values": [62400, 28700, 0, 41200, 0, 33800, 0, 18900]},
                {"name": "Empresarial", "values": [84200, 0, 61200, 22400, 38600, 0, 29100, 0]},
                {"name": "Condomínio", "values": [0, 96800, 0, 0, 44200, 0, 0, 31700]},
                {"name": "Demais", "values": [43100, 0, 54900, 19800, 0, 26400, 41300, 38300]},
            ]}},
        {"block": "actions", "props": {
            "title": "Prioridades desta semana",
            "items": [
                {"title": "Metalúrgica Campeche — ligar hoje",
                 "detail": "Vence em 3 dias, duas tentativas de WhatsApp sem resposta "
                           "desde 21/07. Telefone fixo ainda não foi tentado.",
                 "owner": "Comercial", "due": "hoje", "impact": "R$ 84,2 mil"},
                {"title": "Sul Log — revisar frota antes de cotar",
                 "detail": "A frota passou de 34 para 42 veículos. Renovar na condição "
                           "antiga deixaria 8 veículos descobertos.",
                 "owner": "Técnico", "due": "até 29/07", "impact": "R$ 62,4 mil"},
                {"title": "Abrir contato com Colégio e Frigorífico",
                 "detail": "Vencem em 11 e 14 dias, nenhum contato registrado.",
                 "owner": "Comercial", "due": "até 30/07", "impact": "R$ 71,8 mil"},
            ]}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ]


def dados_dossie() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Dossiê do segurado", "period": "Julho de 2026",
            "title": "Transportadora Sul Log",
            "subtitle": "Resumo da sua proteção atual e os pontos que merecem atenção.",
            "verdict": "Sua frota cresceu de 34 para 42 veículos desde a última "
                       "renovação. Oito veículos ainda não constam na apólice.",
            "headline_label": "Valor total protegido", "headline_value": "R$ 8,4 milhões"}},
        {"block": "kpis", "props": {
            "title": "Resumo da proteção",
            "items": [
                {"label": "Apólices ativas", "value": "4"},
                {"label": "Veículos cobertos", "value": "34", "since": "de 42 na frota"},
                {"label": "Valor protegido", "value": "R$ 8,4", "unit": "mi"},
                {"label": "Próximo vencimento", "value": "8", "unit": "dias"},
            ]}},
        {"block": "table", "props": {
            "eyebrow": "Apólices", "title": "O que está vigente hoje",
            "columns": [
                {"key": "ramo", "label": "Proteção"},
                {"key": "seg", "label": "Seguradora"},
                {"key": "vig", "label": "Vigência"},
                {"key": "is", "label": "Valor protegido", "align": "right",
                 "format": "currency"},
                {"key": "st", "label": "Situação", "pill": True},
            ],
            "rows": [
                {"ramo": "Frota — 34 veículos", "seg": "Porto Seguro",
                 "vig": "02/08/25 a 02/08/26", "is": 6200000.0,
                 "st": "vence em 8 dias", "st_tone": "warning"},
                {"ramo": "Responsabilidade civil", "seg": "Allianz",
                 "vig": "15/03/26 a 15/03/27", "is": 1500000.0,
                 "st": "vigente", "st_tone": "positive"},
                {"ramo": "Patrimonial — sede", "seg": "Bradesco Seguros",
                 "vig": "10/11/25 a 10/11/26", "is": 620000.0,
                 "st": "vigente", "st_tone": "positive"},
                {"ramo": "Vida em grupo — 28 vidas", "seg": "SulAmérica",
                 "vig": "01/01/26 a 01/01/27", "is": 84000.0,
                 "st": "vigente", "st_tone": "positive"},
            ]}},
        {"block": "callout", "props": {
            "tone": "warning", "title": "8 veículos fora da apólice",
            "text": "Comparando a relação de veículos que vocês nos enviaram em junho "
                    "com a apólice vigente, **8 veículos** adquiridos após agosto de "
                    "2025 não foram incluídos. Em caso de sinistro com qualquer um "
                    "deles, **não haveria cobertura**.\n\n"
                    "Podemos incluí-los por endosso antes da renovação, sem esperar o "
                    "vencimento."}},
        {"block": "ranking", "props": {
            "eyebrow": "Exposição", "title": "Onde está o maior valor protegido",
            "value_type": "currency_short", "highlight": 1, "max": 5,
            "items": [
                {"rotulo": "Frota de veículos", "valor": 6200000, "nota": "74% do total"},
                {"rotulo": "Responsabilidade civil", "valor": 1500000, "nota": "18%"},
                {"rotulo": "Sede e equipamentos", "valor": 620000, "nota": "7%"},
                {"rotulo": "Vida em grupo", "valor": 84000, "nota": "1%"},
            ]}},
        {"block": "actions", "props": {
            "title": "Nossas recomendações",
            "items": [
                {"title": "Incluir os 8 veículos por endosso",
                 "detail": "Podemos fazer antes da renovação. O custo proporcional "
                           "até 02/08 é baixo e elimina o risco imediato.",
                 "owner": "Resulta Seguros", "due": "esta semana"},
                {"title": "Reavaliar o limite de responsabilidade civil",
                 "detail": "R$ 1,5 milhão foi contratado quando a frota tinha 22 "
                           "veículos. Com 42, sugerimos revisar o limite.",
                 "owner": "Resulta Seguros", "due": "na renovação"},
                {"title": "Considerar cobertura de carga",
                 "detail": "A frota está protegida, mas a carga transportada não. "
                           "É a lacuna mais comum em transportadoras.",
                 "owner": "Resulta Seguros", "due": "a conversar"},
            ]}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {"disclaimer":
            "Documento informativo. As condições contratuais das apólices "
            "prevalecem sobre este resumo."}},
    ]


def dados_sinistros() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Sinistros", "period": "1º semestre de 2026",
            "title": "A Porto regula em metade do tempo da HDI",
            "subtitle": "Desempenho das seguradoras parceiras em prazo, deferimento "
                        "e reclamação, no semestre.",
            "verdict": "Prazo médio geral caiu de 18 para 14 dias. A diferença entre "
                       "a melhor e a pior seguradora é de 19 dias.",
            "headline_label": "Prazo médio de regulação", "headline_value": "14 dias",
            "headline_delta": -22.2, "headline_better": "down"}},
        {"block": "kpis", "props": {
            "title": "O período em números",
            "items": [
                {"label": "Avisos de sinistro", "value": "147", "delta": 6.5,
                 "since": "vs. 2º sem/25"},
                {"label": "Prazo médio", "value": "14", "unit": "dias", "delta": -22.2,
                 "since": "vs. 2º sem/25", "better": "down"},
                {"label": "Taxa de deferimento", "value": "91,2", "unit": "%",
                 "delta": 3.4, "since": "vs. 2º sem/25"},
                {"label": "Reclamações", "value": "6", "delta": -40.0,
                 "since": "vs. 2º sem/25", "better": "down"},
            ]}},
        {"block": "table", "props": {
            "eyebrow": "Comparação", "title": "Desempenho por seguradora",
            "lede": "Seguradoras com menos de 10 avisos aparecem, mas a média delas "
                    "não é comparável — o número de casos está sempre visível.",
            "columns": [
                {"key": "seg", "label": "Seguradora"},
                {"key": "n", "label": "Avisos", "align": "right"},
                {"key": "prazo", "label": "Prazo médio", "align": "right"},
                {"key": "def", "label": "Deferimento", "align": "right", "format": "percent"},
                {"key": "rec", "label": "Reclamações", "align": "right"},
                {"key": "st", "label": "Leitura", "pill": True},
            ],
            "rows": [
                {"seg": "Porto Seguro", "n": 58, "prazo": "9 dias", "def": 94.8,
                 "rec": 1, "st": "referência", "st_tone": "positive"},
                {"seg": "Allianz", "n": 31, "prazo": "12 dias", "def": 93.5,
                 "rec": 1, "st": "bom", "st_tone": "positive"},
                {"seg": "Bradesco Seguros", "n": 24, "prazo": "15 dias", "def": 91.7,
                 "rec": 1, "st": "na média", "st_tone": "info"},
                {"seg": "SulAmérica", "n": 19, "prazo": "17 dias", "def": 89.5,
                 "rec": 2, "st": "atenção", "st_tone": "warning"},
                {"seg": "Tokio Marine", "n": 11, "prazo": "21 dias", "def": 81.8,
                 "rec": 1, "st": "atenção", "st_tone": "warning"},
                {"seg": "HDI", "n": 4, "prazo": "28 dias", "def": 75.0,
                 "rec": 0, "st": "poucos casos", "st_tone": "info"},
            ],
            "total": {"seg": "Total", "n": 147, "prazo": "14 dias", "def": 91.2,
                      "rec": 6, "st": ""}}},
        {"block": "verdict", "props": {
            "text": "A HDI aparece com o pior prazo do quadro, mas são só 4 casos. "
                    "Com essa amostra, a diferença para a Tokio Marine não é "
                    "estatisticamente distinguível.",
            "note": "Comparar média de 4 casos com média de 58 sem essa ressalva "
                    "produziria uma conclusão errada com aparência de dado. As duas "
                    "seguradoras com amostra pequena entram no quadro marcadas."}},
        {"block": "split", "props": {
            "left": [{"block": "ranking", "props": {
                "title": "Prazo médio de regulação", "value_type": "number",
                "highlight": 0, "max": 6,
                "items": [
                    {"rotulo": "HDI", "valor": 28, "nota": "4 casos · amostra pequena"},
                    {"rotulo": "Tokio Marine", "valor": 21, "nota": "11 casos"},
                    {"rotulo": "SulAmérica", "valor": 17, "nota": "19 casos"},
                    {"rotulo": "Bradesco", "valor": 15, "nota": "24 casos"},
                    {"rotulo": "Allianz", "valor": 12, "nota": "31 casos"},
                    {"rotulo": "Porto Seguro", "valor": 9, "nota": "58 casos"},
                ]}}],
            "right": [{"block": "donut", "props": {
                "title": "Status dos avisos", "value_type": "number",
                "center_value": "147", "center_label": "avisos",
                "slices": [
                    {"rotulo": "Pagos", "valor": 118},
                    {"rotulo": "Em regulação", "valor": 16},
                    {"rotulo": "Negados", "valor": 9},
                    {"rotulo": "Em recurso", "valor": 4},
                ]}}]}},
        {"block": "callout", "props": {
            "tone": "info", "title": "Munição para a próxima negociação",
            "text": "A Porto responde por **39% dos avisos** e tem o melhor prazo do "
                    "quadro. É argumento concreto para negociar comissão na renovação "
                    "do acordo comercial — e para justificar ao cliente por que ela é "
                    "a primeira indicação em auto."}},
        {"block": "actions", "props": {
            "title": "Encaminhamentos",
            "items": [
                {"title": "Levar o quadro à reunião com a SulAmérica",
                 "detail": "17 dias de prazo e 2 das 6 reclamações do semestre. É a "
                           "única com volume relevante e desempenho abaixo da média.",
                 "owner": "Direção", "due": "agosto"},
                {"title": "Acompanhar os 4 recursos em aberto",
                 "detail": "Todos com mais de 30 dias desde a negativa.",
                 "owner": "Sinistros", "due": "esta semana"},
            ]}},
        {"block": "sources", "props": {}},
        {"block": "footer", "props": {}},
    ]


def dados_pesquisa() -> list[dict]:
    return [
        {"block": "cover", "props": {
            "eyebrow": "Dossiê de pesquisa", "period": "Julho de 2026",
            "title": "Seguro paramétrico chega ao agro em SC",
            "subtitle": "O que muda para corretoras de médio porte no Sul, e o que "
                        "fazer nos próximos seis meses.",
            "verdict": "Ainda é nicho, mas o produto resolve a objeção mais antiga do "
                       "agro: o tempo de regulação."}},
        {"block": "verdict", "props": {
            "text": "Paramétrico não substitui o seguro agrícola tradicional — "
                    "compete com a ausência de seguro, que hoje é a situação da "
                    "maioria dos pequenos produtores.",
            "note": "É a distinção que muda a abordagem comercial: não é troca de "
                    "produto, é mercado novo."}},
        {"block": "prose", "props": {
            "eyebrow": "Contexto", "title": "O que está em jogo",
            "text": "No seguro agrícola tradicional, a indenização depende de perícia "
                    "em campo. Entre o evento e o pagamento passam-se, em média, **45 "
                    "a 90 dias** — prazo que, para um produtor descapitalizado, chega "
                    "depois de a decisão de replantio já ter sido tomada.\n\n"
                    "O seguro paramétrico paga por **gatilho medido**, não por perda "
                    "verificada. Se o índice pluviométrico da região ficar abaixo do "
                    "contratado por N dias, a indenização é liberada — sem perícia, "
                    "sem contestação de valor. O produtor recebe em dias.\n\n"
                    "A contrapartida é o *risco de base*: pode haver perda real sem "
                    "gatilho disparado, e gatilho disparado sem perda real. É o ponto "
                    "que precisa ser explicado na venda, sob pena de o produto "
                    "queimar na primeira safra ruim."}},
        {"block": "kpis", "props": {
            "title": "Números que ancoram a análise",
            "items": [
                {"label": "Área agrícola segurada em SC", "value": "23,4", "unit": "%",
                 "since": "estimativa 2025"},
                {"label": "Prazo tradicional", "value": "45–90", "unit": "dias"},
                {"label": "Prazo paramétrico", "value": "3–10", "unit": "dias"},
                {"label": "Produtores sem seguro", "value": "76,6", "unit": "%",
                 "since": "o mercado real"},
            ]}},
        {"block": "chart", "props": {
            "eyebrow": "Evidência", "title": "Prêmio de seguro rural em SC",
            "lede": "Série em milhões de reais. A subvenção federal explica os degraus.",
            "value_type": "short",
            "labels": ["2019", "2020", "2021", "2022", "2023", "2024", "2025"],
            "series": [{"name": "Prêmio rural", "values": [184, 211, 268, 241, 297, 334, 388]}]}},
        {"block": "prose", "props": {
            "eyebrow": "Análise", "title": "Leitura",
            "text": "Três coisas favorecem a entrada agora.\n\n"
                    "**A distribuição mudou.** Os produtos paramétricos que chegaram "
                    "ao Brasil nos últimos dois anos são desenhados para venda "
                    "digital, com apólice curta e contratação em minutos. Isso "
                    "elimina a barreira que sempre travou o agro para corretora de "
                    "médio porte: o custo de atender um ticket pequeno.\n\n"
                    "**O ticket é compatível com o pequeno produtor.** É o que "
                    "transforma os 76,6% sem seguro de estatística em mercado.\n\n"
                    "**A objeção é conhecida e endereçável.** Risco de base explicado "
                    "antes da venda vira característica; explicado depois do sinistro "
                    "vira processo. Isso é material de treinamento, não de produto — "
                    "e é onde uma corretora se diferencia."}},
        {"block": "table", "props": {
            "eyebrow": "Comparação", "title": "Lado a lado",
            "columns": [
                {"key": "d", "label": "Dimensão"},
                {"key": "t", "label": "Tradicional"},
                {"key": "p", "label": "Paramétrico"},
            ],
            "rows": [
                {"d": "Base da indenização", "t": "Perda verificada em perícia",
                 "p": "Índice medido por estação/satélite"},
                {"d": "Prazo até o pagamento", "t": "45 a 90 dias", "p": "3 a 10 dias"},
                {"d": "Contestação de valor", "t": "Comum", "p": "Não se aplica"},
                {"d": "Risco de base", "t": "Não existe", "p": "Existe e precisa ser explicado"},
                {"d": "Custo de distribuição", "t": "Alto", "p": "Baixo — venda digital"},
                {"d": "Subvenção federal", "t": "Sim (PSR)", "p": "Parcial, depende do produto"},
            ]}},
        {"block": "callout", "props": {
            "tone": "warning", "title": "O que ainda não sabemos",
            "text": "Não encontramos série histórica pública de sinistralidade de "
                    "paramétrico no Brasil com mais de três safras. Toda projeção de "
                    "resultado neste dossiê é **hipótese**, não evidência — e está "
                    "marcada como tal no texto."}},
        {"block": "actions", "props": {
            "title": "Recomendações",
            "items": [
                {"title": "Conversar com duas seguradoras que já operam o produto",
                 "detail": "Entender condição de comissionamento e material de apoio "
                           "antes de qualquer compromisso comercial.",
                 "owner": "Direção", "due": "agosto"},
                {"title": "Mapear a base atual de clientes com atividade rural",
                 "detail": "É o teste mais barato: se não houver massa na carteira, "
                           "o produto exige prospecção nova e muda o cálculo.",
                 "owner": "Comercial", "due": "até 20/08"},
                {"title": "Não vender antes de treinar risco de base",
                 "detail": "É a única recomendação com caráter de restrição. Venda "
                           "sem essa explicação gera passivo na primeira safra ruim.",
                 "owner": "Direção", "due": "pré-requisito"},
            ]}},
        {"block": "sources", "props": {
            "title": "Fontes consultadas",
            "note": "Este dossiê é uma demonstração do formato. Numa execução real, "
                    "cada fonte abaixo traz URL e data de acesso, e nenhuma afirmação "
                    "numérica entra sem constar desta lista.",
            "items": [
                {"label": "Estrutura", "detail": "amostra do template de pesquisa",
                 "as_of_label": "demonstração"},
            ]}},
        {"block": "footer", "props": {}},
    ]


AMOSTRAS = [
    ("executive.panorama", "Panorama da Corretora", dados_panorama, "aurora"),
    ("financial.commissions", "Carteira e Comissões", dados_comissoes, "meridian"),
    ("briefing.daily", "Briefing Diário", dados_briefing, "obsidian"),
    ("commercial.pipeline", "Produção e Funil", dados_funil, "aurora"),
    ("renewals.radar", "Radar de Renovações", dados_renovacoes, "meridian"),
    ("portfolio.client_dossier", "Dossiê do Segurado", dados_dossie, "aurora"),
    ("claims.performance", "Sinistros e Seguradoras", dados_sinistros, "meridian"),
    ("research.market_brief", "Dossiê de Pesquisa", dados_pesquisa, "aurora"),
]


def main() -> int:
    print("=" * 68)
    print("SPEC-057 — VISUAL ACCEPTANCE PACK")
    print("=" * 68)
    os.makedirs(SAIDA, exist_ok=True)

    marca = carregar_marca()
    print(f"  marca: {marca['name']}  {marca['palette']['primary']} / "
          f"{marca['palette']['accent']}")
    falhas = [x for m in ("light", "dark") for x in marca["palette"]["audit"][m]
              if not x["passa"]]
    print(f"  contraste: {22 - len(falhas)}/22 pares OK")
    print()

    for chave, titulo, gerador, estilo in AMOSTRAS:
        tpl = templates.POR_CHAVE[chave]
        html, diag = render.render_html(
            brand=marca, composition=gerador(), visual_style=estilo,
            title=f"{titulo} · {marca['name']}", data_sources=FONTES,
            generated_at=AGORA)

        nome = chave.replace(".", "-") + ".html"
        with open(os.path.join(SAIDA, nome), "w", encoding="utf-8") as f:
            f.write(html)

        # Variante para publicação em hospedeiro que embrulha o conteúdo num
        # esqueleto próprio: mesmo CSS e mesmo corpo, sem <html>/<head>/<body>.
        # Duas árvores de documento aninhadas quebram o layout de formas que só
        # aparecem no navegador do destinatário.
        corpo, _ = render.render_html(
            brand=marca, composition=gerador(), visual_style=estilo,
            title=titulo, data_sources=FONTES, generated_at=AGORA,
            embed_fragment=True)
        variaveis = system.to_css_variables(
            marca["palette"], styles.tema_do_estilo(estilo))
        fragmento = (f"<style>\n{variaveis}\n{styles.css_do_estilo(estilo)}\n</style>\n"
                     f'<main class="ab-doc">\n{corpo}\n</main>')
        with open(os.path.join(SAIDA, nome.replace(".html", ".artifact.html")),
                  "w", encoding="utf-8") as f:
            f.write(fragmento)

        aviso = ""
        if diag["desconhecidos"]:
            aviso += f"  BLOCOS DESCONHECIDOS: {diag['desconhecidos']}"
        if diag["falhas"]:
            aviso += f"  FALHAS: {diag['falhas']}"
        print(f"  {estilo:9s} {nome:34s} {len(html)/1024:6.1f} KB  "
              f"{diag['blocos']} blocos{aviso}")

    print()
    print(f"  saida: {SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
