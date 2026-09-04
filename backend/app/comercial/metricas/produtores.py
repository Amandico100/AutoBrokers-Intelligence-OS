# -*- coding: utf-8 -*-
"""Gente e repasse — quem vendeu, quanto saiu, e o que sobrou.

SPEC-094 · BLOCO D.

⛔ **Nenhum nome de pessoa passa por aqui.** O produtor entra e sai como
referência opaca; o rótulo mora no `ProducerAssignmentFact` e é lido pelo
Artifact do tenant, que é onde ele pode estar (SPEC-094 §2). É a mutação M16.

## As três coisas que este arquivo mede, e por que são três

```
producer.performance    quem trouxe quanto            (ranking, base de emissão)
repasse.producer_accrued quanto saiu como repasse     (base de vencimento)
contribution.after_repasse  o que SOBROU              (DERIVED das duas)
```

🔴 A terceira é derivada, e derivada só existe sobre a **interseção** das duas
populações. 📊 A base de emissão e a de vencimento têm 2,8% de interseção
medida — calcular "apropriado menos repasse" sobre populações diferentes daria
um número que parece contribuição e é subtração de coisas distintas.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.comercial import calculos as calc


def _quantia(v):
    """O valor de um `Money`, ou `None`. 🔴 Por FORMA, nunca por `isinstance`.

    A razão está em `registry._float`: o mesmo módulo carregado duas vezes dá
    duas classes, e `isinstance` transformaria dinheiro legítimo em
    INDISPONÍVEL sem uma linha de erro.
    """
    quantia = getattr(v, "amount", None)
    if quantia is None:
        return None
    try:
        return float(quantia)
    except (TypeError, ValueError):
        return None


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

#: 💭 Vinte linhas de ranking cabem numa página e numa conversa.
TETO = 20


# --------------------------------------------------------------------------
def _performance(ctx: Contexto) -> Saida:
    """O ranking por produtor. 🔴 Uma apólice conta UMA vez.

    A matemática é `calculos.ranking_por_produtor`, chamada de verdade. Ela
    agrupa por `rotulo` — que neste caminho é a **referência opaca**, e nunca o
    nome (o motor de cálculo não tem como saber se aquilo é dado de pessoa, e
    não deveria ter).

    📊 E o ranking traz duas colunas que só existem quando alguém cruza dois
    endpoints: o `ticket` (o #1 fez 250 apólices a R$ 1.068; o #2 fez **7** a
    R$ 37.366 — volume e valor são eixos diferentes) e o custo de aquisição,
    que 📊 varia de 0,7% a 38,0% entre canais.
    """
    validas = [a for a in ctx.apolices
               if not a.e_endosso and a.comissao_conhecida]
    todas = [a for a in ctx.apolices if not a.e_endosso]
    if not todas:
        return None, None, [], ["nenhuma apólice no período"]

    # 🔴 O ranking INTEIRO decide o valor; o teto só corta o que vai ao
    # breakdown. Um `value` que contasse as 20 linhas exibidas afirmaria "20
    # produtores" numa corretora com 97 — número certo sobre a lista errada.
    linhas = calc.ranking_por_produtor(validas, ctx.mapa)
    cob = calc.cobertura(validas, ctx.mapa)
    breakdown: List[Dict[str, Any]] = [{
        # ⛔ `producer_ref`, jamais o rótulo.
        "producer_ref": linha.rotulo,
        "apolices": linha.apolices,
        "premio": linha.premio,
        "comissao": linha.comissao,
        "repasse": linha.repasse,
        "ticket": linha.ticket,
        "custo_de_aquisicao_pct": linha.custo_de_aquisicao,
    } for linha in linhas[:TETO]]
    cobertura = (cob.pct_apolices / 100.0) if cob.apolices_total else None
    avisos = [
        f"o ranking cobre {cob.pct_comissao:.1f}% da comissão do período; "
        f"{cob.apolices_total - cob.apolices_com_produtor} apólice(s) não têm "
        f"produtor identificado na fonte"
    ] if cob.apolices_total else []
    return float(len(linhas)), cobertura, breakdown, avisos


_DEFINICOES.append(dict(
    metric_id="producer.performance", version=1,
    label="Produtores com produção atribuída", grain="producer", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("commercial.producer_assignments",
                           "financial.commission_accrued"),
    formula=_performance,
    coverage_rule="fração das apólices do período com produtor identificado — "
                  "📊 remedida POR CORRETORA, nunca constante da fonte",
    forbidden_fallback="⛔ apólice sem produtor nunca é atribuída ao maior nem "
                       "rateada; ela some do ranking E aparece na cobertura",
    pergunta_verificada="Quantos produtores têm produção atribuída no período?",
    golden=golden(2.0),
))


# --------------------------------------------------------------------------
def _cobertura_de_produtor(ctx: Contexto) -> Saida:
    """A cobertura como MÉTRICA — o número que vai impresso na peça.

    ⚠️ Não confundir com o campo `coverage` que TODO envelope carrega para a
    sua própria métrica. Este é o número de que o dono precisa para saber
    quanto do ano o relatório consegue atribuir.

    🔴 E ele é remedido por corretora. 📊 O censo mediu, na mesma fonte, uma
    corretora com 100 apólices em comum entre as duas rotas e outra com **zero**
    — a receita que funciona numa não é constante do provider.
    """
    validas = [a for a in ctx.apolices if not a.e_endosso]
    if not validas:
        return None, None, [], ["nenhuma apólice no período"]
    cob = calc.cobertura(validas, ctx.mapa)
    breakdown = [{
        "apolices_total": cob.apolices_total,
        "apolices_com_produtor": cob.apolices_com_produtor,
        "comissao_total": cob.comissao_total,
        "comissao_atribuida": cob.comissao_atribuida,
        "pct_comissao": cob.pct_comissao,
    }]
    return cob.pct_apolices, (cob.pct_apolices / 100.0), breakdown, []


_DEFINICOES.append(dict(
    metric_id="data.coverage", version=1,
    label="Apólices com produtor identificado", grain="policy", unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("commercial.producer_assignments",),
    formula=_cobertura_de_produtor,
    coverage_rule="a própria métrica É a cobertura; o campo `coverage` repete o "
                  "valor para que o envelope continue autoexplicativo",
    forbidden_fallback="⛔ nunca arredondar para 100% porque 'quase tudo tem'",
    pergunta_verificada="Que fatia das apólices do período tem produtor identificado na fonte?",
    golden=golden(66.66666666666667),
))


# --------------------------------------------------------------------------
def _momentum(ctx: Contexto) -> Saida:
    """30 / 60 / 90 dias, sobre a MESMA base temporal.

    🔴 As três janelas terminam no fim do período pedido e são recortadas
    dentro dele — jamais além. Uma janela que estoure o período compararia
    dados que a leitura não trouxe, e o resultado seria uma queda inventada.
    """
    from datetime import timedelta

    validas = [a for a in ctx.apolices
               if not a.e_endosso and a.comissao_conhecida]
    if not validas:
        return None, None, [], ["nenhuma apólice com comissão legível no período"]

    breakdown: List[Dict[str, Any]] = []
    destaque = None
    for dias in (30, 60, 90):
        fim_a = ctx.fim
        ini_a = max(ctx.inicio, fim_a - timedelta(days=dias - 1))
        fim_b = ini_a - timedelta(days=1)
        ini_b = fim_b - timedelta(days=dias - 1)
        atual = [a for a in validas if a.valid_from and ini_a <= a.valid_from <= fim_a]
        anterior = [a for a in validas if a.valid_from and ini_b <= a.valid_from <= fim_b]
        d = calc.comparar(atual, anterior)
        linha = {
            "janela_dias": dias,
            "apolices_atual": int(d["apolices_atual"]),
            "apolices_anterior": int(d["apolices_anterior"]),
            "comissao_atual": d["comissao_atual"],
            "comissao_anterior": d["comissao_anterior"],
            # ⚠️ `None`, e não `0.0`, quando o período anterior foi zero:
            # "cresceu 0%" e "não havia com o que comparar" são coisas opostas.
            "delta_pct": (d["comissao_delta_pct"] if d["comissao_anterior"] else None),
            "comparavel": bool(d["comissao_anterior"]),
        }
        breakdown.append(linha)
        if dias == 30:
            destaque = linha["delta_pct"]
    cobertura = len(validas) / len([a for a in ctx.apolices if not a.e_endosso])
    avisos = ["a janela anterior é recortada DENTRO do período pedido: o que ela "
              "não alcança sai como não comparável, nunca como queda"]
    return destaque, cobertura, breakdown, avisos


_DEFINICOES.append(dict(
    metric_id="producer.momentum", version=1,
    label="Variação da comissão em 30 dias", grain="period", unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("financial.commission_accrued",),
    formula=_momentum,
    coverage_rule="fração das apólices do período com comissão legível",
    forbidden_fallback="⛔ janela anterior vazia nunca vira '0%' nem '100%'; "
                       "vira `comparavel: false`",
    pergunta_verificada="A comissão dos produtores subiu ou caiu nos últimos 30 dias?",
    golden=golden(INDISPONIVEL),
))


# --------------------------------------------------------------------------
def _repasse(ctx: Contexto) -> Saida:
    """O repasse APROPRIADO aos produtores. 🔴 Soma **todos**, não só o primeiro.

    📊 F-094-02, provado em escala pelo censo: o repasse de cada produtor é a
    comissão da apólice vezes o percentual dele — conferido em **198 de 198**
    linhas, com desvio máximo de R$ 0,01.

    🔴 E o censo derrubou a receita antiga na mesma medição: na mesma apólice, o
    primeiro produtor tinha 4% e o segundo 15%. Somar só o primeiro subestima o
    que sai da corretora — e subestimar o que sai é superestimar o que sobra,
    que é justamente o número que o dono usa para decidir.

    ⚠️ É apropriado, não pago. 📊 O que a fonte declara sobre repasse PAGO veio
    vazio nas três amostras medidas: a rota expõe o formato, não o valor.
    """
    if not ctx.vencimentos:
        return None, None, [], ["nada vence no período"]
    refs = {v.policy_ref for v in ctx.vencimentos}
    valores = [ctx.comissoes[r].producer_repasse for r in refs if r in ctx.comissoes]
    total, conhecidos, itens = 0.0, 0, len(refs)
    for v in valores:
        quantia = _quantia(v)
        if quantia is not None:
            total += quantia
            conhecidos += 1
    cobertura = (conhecidos / itens) if itens else None
    avisos = [f"repasse APROPRIADO (soma de TODOS os produtores da apólice), "
              f"não repasse pago — sobre a população de {POLICY_VALID_TO}, isto "
              f"é, o que VENCE no período (não o que foi emitido nele)"]
    if itens - conhecidos:
        avisos.append(f"{itens - conhecidos} apólice(s) do período sem repasse "
                      f"legível ficaram fora da soma — INDISPONÍVEL, não zero")
    return (total if conhecidos else None), cobertura, [], avisos


_DEFINICOES.append(dict(
    metric_id="repasse.producer_accrued", version=1,
    label="Repasse apropriado aos produtores", grain="policy", unit="BRL",
    time_basis=POLICY_VALID_TO,
    required_capabilities=("financial.producer_repasse_accrued",),
    formula=_repasse,
    coverage_rule="fração das apólices que vencem no período com repasse legível",
    forbidden_fallback="⛔ nunca somar só o produtor de ordem 1 (📊 o censo mediu "
                       "ordem 1 = 4% e ordem 2 = 15% na mesma apólice), e nunca "
                       "tratar repasse ausente como zero",
    pergunta_verificada="Quanto a corretora deve de repasse aos produtores no que vence na janela?",
    golden=golden(525.0),
))


# --------------------------------------------------------------------------
def _contribuicao(ctx: Contexto) -> Saida:
    """DERIVED: apropriado − repasse, **só sobre a interseção**.

    🔴 A interseção é o ponto inteiro desta métrica. A comissão vem da
    população de emissão e o repasse da de vencimento; 📊 elas têm 2,8% de
    interseção medida. Subtrair os dois totais daria um número que parece
    contribuição e é a diferença entre duas carteiras diferentes.

    Então: só entram as apólices que têm **os dois lados conhecidos**, e a
    cobertura declarada é a fração da comissão do período que tem repasse
    conhecido — que é a pergunta honesta *"sobre quanto do meu dinheiro esta
    conta vale?"*.

    ⚠️ Segue a regra do dbt para métricas derivadas (ref ③): ela é composta de
    duas simples e **nunca é reescrita** — se `commission.broker_accrued` mudar
    de fórmula, esta muda junto, de graça.
    """
    validas = [a for a in ctx.apolices
               if not a.e_endosso and a.comissao_conhecida]
    if not validas:
        return None, None, [], ["nenhuma apólice com comissão legível no período"]
    comissao_do_periodo = sum(a.comissao for a in validas)

    apropriado = 0.0
    repassado = 0.0
    na_intersecao = 0
    for a in validas:
        c = ctx.comissoes.get(a.policy_ref)
        quantia = _quantia(getattr(c, "producer_repasse", None)) if c else None
        if quantia is None:
            continue
        apropriado += a.comissao
        repassado += quantia
        na_intersecao += 1

    if not na_intersecao:
        return None, 0.0, [], [
            "nenhuma apólice do período tem os DOIS lados conhecidos "
            "(comissão apropriada e repasse): a contribuição pós-repasse não é "
            "calculável — INDISPONÍVEL, não zero"]

    cobertura = (apropriado / comissao_do_periodo) if comissao_do_periodo else None
    breakdown = [{
        "apolices_na_intersecao": na_intersecao,
        "apolices_do_periodo": len(validas),
        "comissao_na_intersecao": apropriado,
        "repasse_na_intersecao": repassado,
        "comissao_do_periodo": comissao_do_periodo,
        # 🔴 As DUAS bases, no breakdown, com nome. O envelope carrega UMA
        # (`POLICY_VALID_FROM`, a da comissão) porque um envelope só tem uma —
        # e é justamente por isso que a segunda tem de estar escrita em algum
        # lugar que vá ao Artifact.
        "base_da_comissao": POLICY_VALID_FROM,
        "base_do_repasse": POLICY_VALID_TO,
    }]
    # 🔴 O aviso NOMEIA as duas bases. 📊 Achado pela lente do dado, 03/09/2026:
    # o envelope declarava `POLICY_VALID_FROM` e nada dizia que o repasse
    # subtraído vem de `POLICY_VALID_TO`. Quem lesse o envelope concluiria que
    # os dois lados são da mesma população — que é exatamente o erro que a
    # interseção existe para não cometer, agora cometido pelo LEITOR em vez de
    # pelo cálculo.
    avisos = [
        f"as duas pontas vêm de bases temporais DIFERENTES: a comissão de "
        f"{POLICY_VALID_FROM} (o que COMEÇA no período) e o repasse de "
        f"{POLICY_VALID_TO} (o que VENCE no período). O número sai só sobre a "
        f"INTERSEÇÃO das duas: {na_intersecao} de {len(validas)} apólices do "
        f"período têm os dois lados conhecidos"]
    contribuicao = apropriado - repassado
    teto = None
    if contribuicao < 0:
        # 🔴 Contribuição NEGATIVA existe e não é impossível — mas ela não é um
        # resultado que o produto possa apresentar com confiança alta.
        # 📊 Achado pela lente do dado, 03/09/2026: com um `val_r` negativo
        # maior que a comissão, o número saía `HIGH` (a cobertura era 100%) e o
        # cartão dizia que a corretora tinha PERDIDO dinheiro no período. A
        # cobertura mede quantas linhas entraram na conta; ela não sabe que o
        # resultado da conta não se explica pelo negócio.
        from app.comercial.evidence_pack import BAIXA

        teto = BAIXA
        avisos.append(
            "repasse maior que a comissão no período (estorno?): a contribuição "
            "saiu NEGATIVA. O número está somado como a fonte o entregou e não "
            "foi corrigido — confira o estorno antes de decidir por ele")
    return contribuicao, cobertura, breakdown, avisos, teto


_DEFINICOES.append(dict(
    metric_id="contribution.after_repasse", version=1,
    label="Contribuição depois do repasse", grain="policy", unit="BRL",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("financial.commission_accrued",
                           "financial.producer_repasse_accrued"),
    formula=_contribuicao,
    coverage_rule="fração da comissão do período que tem repasse conhecido — "
                  "é ela que diz sobre quanto do dinheiro a conta vale",
    forbidden_fallback="⛔ nunca subtrair o TOTAL de repasse do TOTAL de comissão: "
                       "são populações diferentes (📊 2,8% de interseção). E ⛔ "
                       "nunca chamar este número de LUCRO — não há custo aqui",
    premissa="⚠️ contribuição não é lucro: não entram custo fixo, imposto nem "
             "estorno (📊 os dois últimos não foram verificados no censo)",
    pergunta_verificada="Quanto sobra para a corretora depois de pagar o repasse dos produtores?",
    golden=golden(4025.0),
))
