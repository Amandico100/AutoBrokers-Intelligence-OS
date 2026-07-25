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


AMOSTRAS = [
    ("executive.panorama", "Panorama da Corretora", dados_panorama, "aurora"),
    ("financial.commissions", "Carteira e Comissões", dados_comissoes, "meridian"),
    ("briefing.daily", "Briefing Diário", dados_briefing, "obsidian"),
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
