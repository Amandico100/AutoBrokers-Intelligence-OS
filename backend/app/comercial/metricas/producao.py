# -*- coding: utf-8 -*-
"""Produção e comissão — as métricas da base `POLICY_VALID_FROM`.

SPEC-094 · BLOCO D. Todas migradas de `app/comercial/calculos.py`, com a
matemática intacta: o que muda é de onde vêm os fatos e o que sai no envelope.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.comercial import calculos as calc
from app.comercial.manifesto import SUPPORTED
from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

#: 🔴 As definições são DADO, e o registry as instala. Não é cerimônia: um
#: `import` do registry aqui criaria uma segunda cópia dele quando alguém
#: carregasse `registry.py` por CAMINHO (que é como um guarda isolado o carrega),
#: e aí haveria duas listas de métricas — uma cheia e uma vazia. `calcular()`
#: diria "métrica desconhecida" sobre uma métrica que existe, e o defeito seria
#: invisível. Aqui não há import: o registry se injeta.
_DEFINICOES: List[Dict[str, Any]] = []

Contexto = Any
Saida = Any


def instalar(reg) -> None:
    """Registra as definições deste arquivo NO registry que chamou."""
    for kw in _DEFINICOES:
        reg.registrar(reg.MetricDefinition(**kw))


# --------------------------------------------------------------------------
def _contagem(ctx: Contexto) -> Saida:
    """Apólices do período. 🔴 **Endosso não é apólice.**

    📊 É a mutação M5, e ela tem número: sem o filtro de tipo de documento a
    fonte devolve 3.272 documentos dos quais só **1.680** são apólice — o resto
    é endosso, proposta e cancelamento. Contá-los dobraria a produção do ano, e
    dobraria em silêncio, porque cada linha parece uma apólice.
    """
    validas = [a for a in ctx.apolices if not a.e_endosso]
    endossos = len(ctx.apolices) - len(validas)
    avisos: List[str] = []
    if endossos:
        avisos.append(f"{endossos} documento(s) de endosso ficaram FORA da contagem "
                      f"de apólices: endosso altera uma apólice, não é uma nova")
    return float(len(validas)), 1.0, [], avisos


_DEFINICOES.append(dict(
    metric_id="production.policy_count", version=1,
    label="Apólices emitidas", grain="policy", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.policies", "portfolio.production"),
    formula=_contagem,
    coverage_rule="1.0 — a contagem usa todas as apólices que a fonte devolveu "
                  "no período; nada é excluído por falta de campo",
    forbidden_fallback="⛔ nunca contar endosso, proposta ou cancelamento como "
                       "apólice para 'fechar' o número",
))


# --------------------------------------------------------------------------
def _premio(ctx: Contexto) -> Saida:
    """Prêmio emitido. Soma só o que a fonte expôs, e diz quanto isso cobre."""
    validas = [a for a in ctx.apolices if not a.e_endosso]
    conhecidas = [a for a in validas if a.premio_conhecido]
    total = sum(a.premio for a in conhecidas)
    cobertura = (len(conhecidas) / len(validas)) if validas else None
    avisos: List[str] = []
    faltando = len(validas) - len(conhecidas)
    if faltando:
        avisos.append(f"{faltando} apólice(s) sem prêmio legível ficaram fora da "
                      f"soma — INDISPONÍVEL, não zero")
    return (total if conhecidas else None), cobertura, [], avisos


_DEFINICOES.append(dict(
    metric_id="production.premium_written", version=1,
    label="Prêmio emitido", grain="policy", unit="BRL",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.production",),
    formula=_premio,
    coverage_rule="fração das apólices do período cujo prêmio a fonte expôs",
    forbidden_fallback="⛔ prêmio ausente nunca entra como 0,00 na soma",
))


# --------------------------------------------------------------------------
def _comissao_apropriada(ctx: Contexto) -> Saida:
    """Comissão APROPRIADA na emissão. ⛔ **Não** é comissão recebida.

    📊 O censo mediu, na fonte piloto, a comissão presente e não-nula em
    1.680/1.680 apólices de 2025 — R$ 1.863.830,79, com 93 apólices de valor
    zero (que são zero de verdade, e entram).

    🔴 A diferença entre APROPRIADA e RECEBIDA não é vocabulário: uma é o que a
    corretora ganhou o direito de receber na emissão, a outra é o que entrou na
    conta. Chamar a primeira de "recebida" é a mutação M8 — e é o tipo de erro
    que só aparece quando o dono compara com o extrato do banco.
    """
    validas = [a for a in ctx.apolices if not a.e_endosso]
    conhecidas = [a for a in validas if a.comissao_conhecida]
    total = sum(a.comissao for a in conhecidas)
    cobertura = (len(conhecidas) / len(validas)) if validas else None
    avisos = ["comissão APROPRIADA na emissão — não é o que entrou em caixa"]
    faltando = len(validas) - len(conhecidas)
    if faltando:
        avisos.append(f"{faltando} apólice(s) sem comissão legível ficaram fora "
                      f"da soma — INDISPONÍVEL, não zero")
    return (total if conhecidas else None), cobertura, [], avisos


_DEFINICOES.append(dict(
    metric_id="commission.broker_accrued", version=1,
    label="Comissão apropriada da corretora", grain="policy", unit="BRL",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("financial.commission_accrued",),
    formula=_comissao_apropriada,
    coverage_rule="fração das apólices do período com comissão legível",
    forbidden_fallback="⛔ nunca apresentar este número como comissão RECEBIDA, "
                       "e nunca somar apólice sem comissão como zero",
))


# --------------------------------------------------------------------------
def _novo_versus_renovacao(ctx: Contexto) -> Saida:
    """Quanto do período é negócio novo e quanto é carteira mantida.

    📊 2025 mediu 717 novo / 963 renovação. A matemática é
    `calculos.novo_versus_renovacao`, chamada de verdade — o valor de destaque
    é a **fração de negócio novo**, que é a pergunta do dono.
    """
    validas = [a for a in ctx.apolices
               if not a.e_endosso and a.comissao_conhecida]
    if not validas:
        return None, None, [], ["nenhuma apólice com comissão legível no período"]
    partes = calc.novo_versus_renovacao(validas)
    novo, renov = partes["novo"], partes["renovacao"]
    total = novo[0] + renov[0]
    breakdown: List[Dict[str, Any]] = [
        {"segmento": "novo", "apolices": novo[0], "comissao": novo[1]},
        {"segmento": "renovacao", "apolices": renov[0], "comissao": renov[1]},
    ]
    cobertura = len(validas) / len([a for a in ctx.apolices if not a.e_endosso])
    # 🔴 O valor é a REPARTIÇÃO, e não uma das metades. "70% é novo" e "30% é
    # renovação" são a mesma frase, e escolher uma delas como o número da métrica
    # obrigaria o modelo a inferir a outra — que é exatamente o que o pacote de
    # evidência existe para não precisar.
    valor = {"NEW": novo[0], "RENEWAL": renov[0],
             "NEW_comissao": novo[1], "RENEWAL_comissao": renov[1],
             "total": total}
    return valor, cobertura, breakdown, []


_DEFINICOES.append(dict(
    metric_id="production.new_vs_renewal", version=1,
    label="Negócio novo × renovação", grain="policy", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.production", "portfolio.renewals"),
    formula=_novo_versus_renovacao,
    coverage_rule="fração das apólices do período com comissão legível — as "
                  "outras não entram em nenhum dos dois lados",
    forbidden_fallback="⛔ apólice sem classificação nunca é jogada em 'novo' "
                       "para os dois lados somarem 100%",
))


# ==========================================================================
# O QUE A FONTE PILOTO NÃO ENTREGA — e a diferença entre os dois motivos
# ==========================================================================
#
# 🔴 As três abaixo existem de propósito, e existem VAZIAS. Uma métrica que
# não aparece deixa o leitor supor que ninguém pensou nela; uma métrica que
# aparece dizendo por que não tem número fecha a pergunta.
#
# 📊 E os motivos são diferentes, o que importa mais que os números:
#
#   received   PARTIAL  — o dado existe no detalhe de UMA apólice por chamada.
#                         Ler a carteira inteira custaria uma requisição por
#                         apólice. Por isso a métrica exige SUPPORTED.
#   reversals  UNKNOWN  — ninguém sondou. NÃO é "a fonte não tem".
#   tax        UNKNOWN  — idem.
def _sem_numero(ctx: Contexto) -> Saida:  # noqa: ARG001
    return None, None, [], []


for _mid, _label, _cap, _aceitos, _porque in (
    ("commission.broker_received", "Comissão recebida",
     "financial.commission_received", (SUPPORTED,),
     "só existe no detalhe de uma apólice por chamada — não há rota de lote"),
    ("commission.reversals", "Estornos de comissão",
     "financial.commission_reversals", (SUPPORTED,),
     "não verificado nesta rodada do censo — não concluir que não existe"),
    ("commission.tax", "Impostos sobre a comissão",
     "financial.commission_tax", (SUPPORTED,),
     "não verificado nesta rodada do censo — não concluir que não existe"),
):
    _DEFINICOES.append(dict(
        metric_id=_mid, version=1, label=_label, grain="policy", unit="BRL",
        time_basis=POLICY_VALID_FROM,
        required_capabilities=(_cap,),
        formula=_sem_numero,
        estados_aceitos=_aceitos,
        coverage_rule="não se aplica: não há número",
        forbidden_fallback=f"⛔ INDISPONÍVEL, nunca 0,00 nem 'igual à apropriada' "
                           f"({_porque})",
    ))
