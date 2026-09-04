# -*- coding: utf-8 -*-
"""Mix e concentração — por seguradora e por ramo.

SPEC-094 · BLOCO D. A matemática é `calculos.por_dimensao`, chamada de verdade
(CLAUDE.md §9.4: o teste do corredor chama o MOTOR).

🔴 O valor de destaque é a **concentração no maior**, não o número de fatias.
A pergunta do dono não é "quantas seguradoras eu tenho"; é *"quanto do meu
resultado depende de uma só?"* — e é essa que decide se ele aceita a próxima
mudança de comissionamento sem discutir.

📊 A normalização de rótulo vem da 081 e é medida: a base tem `Allianz`,
`allianz`, `ALLIANZ` e `Allianz Seguros` contando separado — 56 valores crus
que viram ~30. Uma rosca com a mesma seguradora em quatro fatias não é gráfico,
é defeito.
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

#: Quantas fatias vão ao pacote. 💭 Doze cabem num gráfico e numa frase; o
#: resto entra como "demais" na soma, nunca some.
TETO = 12


def _mix(ctx: Contexto, campo: str) -> Saida:
    validas = [a for a in ctx.apolices
               if not a.e_endosso and a.comissao_conhecida]
    todas = [a for a in ctx.apolices if not a.e_endosso]
    if not validas:
        return None, None, [], ["nenhuma apólice com comissão legível no período"]

    linhas = calc.por_dimensao(validas, campo, campo_valor="comissao")
    total = sum(x[2] for x in linhas)
    breakdown: List[Dict[str, Any]] = [
        {"rotulo": rotulo, "apolices": n, "comissao": valor,
         "share_pct": (100.0 * valor / total) if total else None}
        for rotulo, n, valor in linhas[:TETO]
    ]
    if len(linhas) > TETO:
        resto = linhas[TETO:]
        breakdown.append({
            "rotulo": f"demais ({len(resto)})",
            "apolices": sum(x[1] for x in resto),
            "comissao": sum(x[2] for x in resto),
            "share_pct": (100.0 * sum(x[2] for x in resto) / total) if total else None,
        })
    concentracao = (100.0 * linhas[0][2] / total) if total else None
    cobertura = len(validas) / len(todas) if todas else None
    return concentracao, cobertura, breakdown, [
        f"{len(linhas)} valores distintos depois da normalização de rótulo"]


def _mix_seguradora(ctx: Contexto) -> Saida:
    return _mix(ctx, "seguradora")


def _mix_ramo(ctx: Contexto) -> Saida:
    return _mix(ctx, "ramo")


_DEFINICOES.append(dict(
    metric_id="mix.insurer", version=1,
    label="Concentração na maior seguradora", grain="insurer", unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.policies",),
    formula=_mix_seguradora,
    coverage_rule="fração das apólices do período com comissão legível — o mix "
                  "é sobre a comissão, não sobre a contagem",
    forbidden_fallback="⛔ apólice sem seguradora nunca é distribuída entre as "
                       "conhecidas; ela vira '(não informado)' e aparece",
    pergunta_verificada="Que fatia da comissão do período está na maior seguradora?",
    golden=golden(43.0),
))

_DEFINICOES.append(dict(
    metric_id="mix.branch", version=1,
    label="Concentração no maior ramo", grain="branch", unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.policies",),
    formula=_mix_ramo,
    coverage_rule="fração das apólices do período com comissão legível",
    forbidden_fallback="⛔ ramo ausente vira '(não informado)', nunca é rateado",
    pergunta_verificada="Que fatia da comissão do período está no maior ramo?",
    golden=golden(61.0),
))
