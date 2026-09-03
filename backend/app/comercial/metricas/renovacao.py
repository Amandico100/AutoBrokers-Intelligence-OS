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
from app.comercial.metricas.registry import (POLICY_VALID_FROM, POLICY_VALID_TO,
                                             Contexto, MetricDefinition, Saida,
                                             registrar)


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
    return total, cobertura, breakdown, avisos


registrar(MetricDefinition(
    metric_id="renewal.exposure", version=1,
    label="Prêmio a vencer na janela", grain="policy", unit="BRL",
    time_basis=POLICY_VALID_TO,
    required_capabilities=("portfolio.renewals",),
    formula=_exposicao,
    coverage_rule="fração dos vencimentos da janela com prêmio legível",
    forbidden_fallback="⛔ nunca comparar esta métrica com produção do mesmo "
                       "período: são duas populações (📊 2,8% de interseção). E "
                       "⛔ faixa vazia é 0, nunca INDISPONÍVEL",
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


registrar(MetricDefinition(
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
))
