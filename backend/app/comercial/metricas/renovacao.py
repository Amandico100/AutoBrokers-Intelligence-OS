# -*- coding: utf-8 -*-
"""Exposição de renovação e projeção — o que vem, e o que viria.

SPEC-094 · BLOCO D.

🔴 `renewal.exposure` é a única métrica da v1 cuja base temporal é o **fim** da
vigência. Isso não é detalhe de implementação: 📊 a população que vence num
período tem 2,8% de interseção com a que começou nele. Comparar a exposição de
um trimestre com a produção do mesmo trimestre é comparar duas carteiras, e é a
mutação M6 — que `comparar()` recusa.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.comercial import calculos as calc
from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

#: 🔴 As definições são DADO, e o registry as instala. Não é cerimônia: um
#: `import` do registry aqui criaria uma segunda cópia dele quando alguém
#: carregasse `registry.py` por CAMINHO (que é como um guarda isolado o carrega),
#: e aí haveria duas listas de métricas — uma cheia e uma vazia. `calcular()`
#: diria "métrica desconhecida" sobre uma métrica que existe, e o defeito seria
#: invisível. Aqui não há import: o registry se injeta.
_DEFINICOES: List[Dict[str, Any]] = []

#: 🔴 SPEC-094.1 · BLOCO D. A fixture e o sentinela vêm do registry por
#: INJEÇÃO, como tudo neste arquivo: um `import` criaria a segunda cópia do
#: registry que o comentário acima explica. Aqui eles são literais, e o guarda
#: do protocolo confere que a `fixture` declarada é uma que existe.
FIXTURE = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"
INDISPONIVEL = "UNAVAILABLE"


def golden(esperado):
    """`{"fixture": ..., "esperado": ...}` — 📊 medido, não estimado.

    Cada `esperado` foi lido de `registry.calcular()` rodando sobre a fixture
    sintética da 094 em 03/09/2026, e não escrito de cabeça. O comando está no
    relatório da SPEC-094.1.
    """
    return {"fixture": FIXTURE, "esperado": esperado}


Contexto = Any
Saida = Any


def instalar(reg) -> None:
    """Registra as definições deste arquivo NO registry que chamou."""
    for kw in _DEFINICOES:
        reg.registrar(reg.MetricDefinition(**kw))


# --------------------------------------------------------------------------
def _exposicao(ctx: Contexto) -> Saida:
    """Quanto prêmio vence na janela, e em que urgência.

    ⚠️ 📊 Vencimento com prazo NEGATIVO existe e é comum: o censo mediu 2.594
    negativos em 3.536 registros de um ano. Eles entram, na faixa "vencidas" —
    esconder o que já passou do prazo seria esconder justamente o que precisa
    de ação hoje.

    🔴 E uma faixa vazia sai como **0**, não como indisponível. As duas coisas
    são diferentes e o produto não pode confundi-las (ref ④): "nada vence entre
    31 e 60 dias" é um fato sobre o negócio; "a fonte não expõe vencimento" é
    um fato sobre a fonte.
    """
    if not ctx.vencimentos:
        return 0.0, 1.0, [], ["nada vence no período — este 0 é um fato sobre a "
                              "carteira, não uma ausência de dado"]
    # 🔴 O número de destaque é QUANTAS apólices vencem, e não quanto prêmio
    # elas somam. A pergunta do dono é "quanto trabalho vem pela frente"; e o
    # dinheiro depende de a fonte expor o prêmio, que 📊 ela nem sempre expõe —
    # uma exposição que virasse R$ 0,00 por falta de campo diria "nada a fazer"
    # sobre 3.536 apólices a vencer.
    conhecidos = [v for v in ctx.vencimentos if v.premio_conhecido]
    faixas = calc.faixas_de_urgencia(conhecidos)
    breakdown: List[Dict[str, Any]] = [
        {"faixa": rotulo, "apolices": n, "premio": valor}
        for rotulo, n, valor in faixas]
    total = sum(v.premio for v in conhecidos)
    cobertura = len(conhecidos) / len(ctx.vencimentos)
    avisos: List[str] = []
    faltando = len(ctx.vencimentos) - len(conhecidos)
    if faltando:
        avisos.append(f"{faltando} vencimento(s) sem prêmio legível ficaram fora "
                      f"da soma — INDISPONÍVEL, não zero")
    vencidas = [v for v in conhecidos if v.dias_a_vencer < 0]
    if vencidas:
        avisos.append(f"{len(vencidas)} apólice(s) da janela JÁ passaram do "
                      f"vencimento e estão contadas na faixa 'vencidas'")
    if total:
        avisos.append("prêmio a vencer na janela: %.2f (o detalhe por faixa de "
                      "urgência está no breakdown)" % total)
    return float(len(ctx.vencimentos)), cobertura, breakdown, avisos


_DEFINICOES.append(dict(
    metric_id="renewal.exposure", version=1,
    label="Apólices a vencer na janela", grain="policy", unit="count",
    time_basis=POLICY_VALID_TO,
    required_capabilities=("portfolio.renewals",),
    formula=_exposicao,
    coverage_rule="fração dos vencimentos da janela com prêmio legível",
    forbidden_fallback="⛔ nunca comparar esta métrica com produção do mesmo "
                       "período: são duas populações (📊 2,8% de interseção). E "
                       "⛔ faixa vazia é 0, nunca INDISPONÍVEL",
    pergunta_verificada="Quantas apólices vencem na janela — quanto está exposto a não renovar?",
    golden=golden(10.0),
))


# --------------------------------------------------------------------------
def _run_rate(ctx: Contexto) -> Saida:
    """Onde o período fecha, se o ritmo dos meses COMPLETOS se mantiver.

    🔴 Descarta o último mês da série. Mês em curso tem produção parcial, e
    projetar a partir dele subestima **sempre** — é o erro clássico de
    dashboard, e ele aparece como "queda" no gráfico todo dia primeiro.

    🔴 E a premissa vai no envelope, escrita. Uma projeção sem premissa é
    adivinhação com cara de número, e é a mutação M9: comissão histórica **não**
    é renovação garantida. Ninguém renovou nada ainda.
    """
    validas = [a for a in ctx.apolices
               if not a.e_endosso and a.comissao_conhecida]
    serie = calc.serie_mensal(validas)
    if len(serie) < 3:
        return None, None, [], [
            "menos de três meses com movimento no período: projeção sobre um ou "
            "dois pontos é adivinhação, e o registry prefere INDISPONÍVEL"]
    projetado = calc.projetar(serie, ctx.meses)
    breakdown: List[Dict[str, Any]] = [
        {"mes": mes, "apolices": n, "comissao": valor} for mes, n, valor in serie]
    cobertura = (len(validas) / len([a for a in ctx.apolices if not a.e_endosso])
                 if ctx.apolices else None)
    return projetado, cobertura, breakdown, [
        f"projeção sobre {len(serie) - 1} mês(es) COMPLETO(s); o último mês da "
        f"série foi descartado por estar em curso"]


_DEFINICOES.append(dict(
    metric_id="projection.run_rate", version=1,
    label="Comissão projetada no ritmo atual", grain="period", unit="BRL",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("financial.commission_accrued",),
    formula=_run_rate,
    coverage_rule="fração das apólices do período com comissão legível",
    forbidden_fallback="⛔ nunca projetar a partir de menos de três meses, e ⛔ "
                       "nunca apresentar a projeção como receita contratada",
    premissa="⚠️ premissa: o ritmo dos meses completos se mantém. Comissão "
             "histórica NÃO é renovação garantida — ninguém renovou nada ainda",
    pergunta_verificada="Se o ritmo atual continuar, quanto de comissão a corretora fecha?",
    golden=golden(18960.0),
))
