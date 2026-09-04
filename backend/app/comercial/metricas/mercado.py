# -*- coding: utf-8 -*-
"""Carteira × mercado — SPEC-094.1 · BLOCO B. **O cruzamento que só nós fazemos.**

A estatística oficial do mercado segurador brasileiro é pública, mensal por
seguradora e por ramo, e ninguém a cruza com a carteira de UMA corretora. Estas
quatro definições fazem isso — e a única coisa que elas sabem sobre a fonte é
que ela chega como um **feixe de plataforma** em `contexto.mercado`.

```
sinistralidade = sinistro ocorrido ÷ prêmio ganho
```

🔴 **As duas pontas do MESMO regime de competência.** O prêmio já *ganho* no mês
contra o sinistro *ocorrido* no mês. ⛔ Misturar com prêmio de emissão ou
sinistro pago é o erro clássico, e ele **não trava**: devolve um número
plausível e errado (CLAUDE.md §9.5). Quem faz esse recorte é o ingestor, na
fronteira; aqui só chega o par certo.

## Três coisas que estas métricas recusam a fazer

```
⛔ adivinhar a entidade      seguradora fora do mapa sai UNAVAILABLE, nunca 0 (M2)
⛔ esconder a defasagem      📊 a base fecha três meses atrás; o ponteiro diz qual mês
⛔ zerar o estorno           📊 sinistro ocorrido pode ser NEGATIVO (estorno de
                            provisão): −53.790,44 numa célula medida. O sinal
                            sobrevive, e a célula sai marcada
```

## Por que o destaque é a entidade de MAIOR PRÊMIO, e não a média

💭 A média do mercado inteiro responde a uma pergunta que ninguém faz. A
pergunta do dono é *"a **minha** seguradora está sinistrando mais que o
mercado?"* — então o valor de destaque é o da entidade que pesa mais, e as
outras vão no detalhamento, com o número de cada uma. Quando a carteira tem
entidades mapeadas, o recorte é o **delas**: é a comparação que ele pediu.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

_DEFINICOES: List[Dict[str, Any]] = []

FIXTURE = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"
INDISPONIVEL = "UNAVAILABLE"
DESCONHECIDA = "UNKNOWN"

#: 💭 Quantos trimestres a tendência lê. Três é o que separa oscilação de
#: movimento sem virar série histórica dentro de um relatório executivo.
TRIMESTRES = 3

#: 💭 O sinal da tendência. Abaixo deste movimento em pontos de razão, "estável".
LIMIAR_DE_MOVIMENTO = 0.01

Contexto = Any
Saida = Any


def golden(esperado):
    return {"fixture": FIXTURE, "esperado": esperado}


def instalar(reg) -> None:
    for kw in _DEFINICOES:
        reg.registrar(reg.MetricDefinition(**kw))


# --------------------------------------------------------------------------
# A leitura do feixe de plataforma
# --------------------------------------------------------------------------
def _competencias(inicio: date, fim: date) -> List[str]:
    """As competências `AAAAMM` do período, inclusive.

    🔴 Competência é MÊS CONTÁBIL, e não data: `202606` é junho inteiro. Uma
    comparação com a carteira tem de ser mês fechado contra mês fechado.
    """
    saida = []
    ano, mes = inicio.year, inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        saida.append("%04d%02d" % (ano, mes))
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1
    return saida


def _agregar(celulas: List[Any]) -> Tuple[float, float, bool]:
    premio = sum(float(getattr(c, "premio_ganho", 0.0) or 0.0) for c in celulas)
    sinistro = sum(float(getattr(c, "sinistro_ocorrido", 0.0) or 0.0)
                   for c in celulas)
    estorno = any(bool(getattr(c, "estorno", False)) for c in celulas)
    return premio, sinistro, estorno


def _entidades_da_carteira(ctx: Contexto, feixe: Any) -> Tuple[set, int, set]:
    """`(coentis mapeados, quantas seguradoras não mapearam, nomes crus)`.

    ⚠️ O nome da seguradora vem da carteira, e o mapa é revisado por gente. O
    que não casa **não vira palpite**: ele volta contado, para que a cobertura
    consiga dizer quanto do cruzamento ficou de fora.
    """
    nomes = {str(getattr(a, "seguradora", "") or "").strip()
             for a in ctx.apolices if str(getattr(a, "seguradora", "") or "").strip()}
    mapeados, sem_mapa = set(), set()
    for nome in nomes:
        coenti = feixe.coenti_de(nome) if hasattr(feixe, "coenti_de") else DESCONHECIDA
        if coenti and coenti != DESCONHECIDA:
            mapeados.add(coenti)
        else:
            sem_mapa.add(nome)
    return mapeados, len(sem_mapa), nomes


def _celulas_do_periodo(ctx: Contexto, feixe: Any,
                        competencias: Optional[List[str]] = None) -> List[Any]:
    alvo = set(competencias or _competencias(ctx.inicio, ctx.fim))
    return [c for c in list(getattr(feixe, "facts", ()) or ())
            if str(getattr(c, "damesano", "") or "").strip() in alvo]


def _sem_feixe() -> Saida:
    return None, None, [], [
        "o censo do mercado ainda não foi lido nesta rodada: INDISPONÍVEL. 🔴 "
        "Isto é uma afirmação sobre NÓS — a Rotina semanal — e nunca sobre a "
        "sinistralidade de seguradora nenhuma"]


def _defasagem(feixe: Any) -> List[str]:
    fechamento = str(getattr(feixe, "competencia_final", "") or "").strip()
    if not fechamento:
        return []
    return [f"a base pública fecha em {fechamento}: o número do mercado é do "
            f"mês fechado, e não do mês corrente — comparar com a carteira de "
            f"hoje compara períodos diferentes"]


# --------------------------------------------------------------------------
# market.loss_ratio
# --------------------------------------------------------------------------
def _sinistralidade_do_mercado(ctx: Contexto) -> Saida:
    feixe = getattr(ctx, "mercado", None)
    if feixe is None or not list(getattr(feixe, "facts", ()) or ()):
        return _sem_feixe()
    competencias = _competencias(ctx.inicio, ctx.fim)
    celulas = _celulas_do_periodo(ctx, feixe, competencias)
    if not celulas:
        return None, None, [], [
            f"o censo do mercado não tem célula nas competências do período "
            f"({competencias[0]}–{competencias[-1]}): INDISPONÍVEL, e não "
            f"sinistralidade zero"] + _defasagem(feixe)

    mapeados, _sem, _nomes = _entidades_da_carteira(ctx, feixe)
    avisos = list(_defasagem(feixe))
    if mapeados:
        recorte = [c for c in celulas
                   if str(getattr(c, "coenti", "") or "").strip() in mapeados]
        if recorte:
            celulas = recorte
            avisos.append(
                f"recortado nas {len(mapeados)} seguradora(s) da carteira que "
                f"casaram com o mapa — é a comparação que o dono pediu")

    baldes: Dict[Tuple[str, str], List[Any]] = {}
    for c in celulas:
        chave = (str(getattr(c, "coenti", "") or "").strip(),
                 str(getattr(c, "coramo", "") or "").strip()[:2])
        baldes.setdefault(chave, []).append(c)

    linhas = []
    for (coenti, grupo), itens in baldes.items():
        premio, sinistro, estorno = _agregar(itens)
        linhas.append({
            "rotulo": f"{coenti}·{grupo}", "coenti": coenti,
            "grupo_de_ramo": grupo, "competencias": len({
                str(getattr(c, "damesano", "")) for c in itens}),
            "premio_ganho": premio, "sinistro_ocorrido": sinistro,
            "sinistralidade": (sinistro / premio) if premio else None,
            "estorno": estorno})
    linhas.sort(key=lambda x: -x["premio_ganho"])
    destaque = next((x for x in linhas if x["sinistralidade"] is not None), None)
    if destaque is None:
        return None, None, linhas, avisos + [
            "nenhuma célula do período tem prêmio ganho: INDISPONÍVEL — uma "
            "divisão por zero não é uma sinistralidade de 0%"]
    if destaque["estorno"]:
        avisos.append(
            "há ESTORNO de provisão nas células desta entidade (sinistro "
            "ocorrido negativo): o valor foi preservado, e a sinistralidade do "
            "mês sai menor por um lançamento contábil, não por menos sinistro")
    vistas = len({str(getattr(c, "damesano", "")) for c in celulas})
    return (destaque["sinistralidade"], vistas / len(competencias), linhas,
            avisos + [f"destaque: a entidade de maior prêmio ganho no período "
                      f"({destaque['rotulo']})"])


_DEFINICOES.append(dict(
    metric_id="market.loss_ratio", version=1,
    label="Sinistralidade do mercado, por seguradora e ramo", grain="insurer",
    unit="ratio",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=(),
    formula=_sinistralidade_do_mercado,
    coverage_rule="fração das competências do período que existem na base "
                  "pública — ela fecha meses atrás, e o que falta é defasagem "
                  "da fonte, não ausência de sinistro",
    forbidden_fallback="⛔ competência ausente NUNCA entra como zero: prêmio zero "
                       "e sinistro zero num mês que a base não publicou "
                       "derrubaria a sinistralidade média com dado que não "
                       "existe",
    premissa="🔴 sinistro OCORRIDO ÷ prêmio GANHO — as duas pontas do mesmo "
             "regime de competência. Prêmio de emissão e sinistro pago dariam "
             "um número plausível e errado",
    pergunta_verificada="Qual é a sinistralidade do mercado nas seguradoras com "
                        "que eu trabalho?",
    golden=golden(INDISPONIVEL),
))


# --------------------------------------------------------------------------
# claims.loss_ratio_portfolio
# --------------------------------------------------------------------------
def _sinistralidade_da_carteira(ctx: Contexto) -> Saida:
    fatos = getattr(ctx, "fatos", None)
    carteira = {p.policy_ref for p in list(getattr(fatos, "policies", ()) or ())
                if getattr(p, "policy_ref", "")}
    sinistros = [c for c in list(getattr(fatos, "claims", ()) or ())
                 if getattr(c, "occurred_at", None) is not None
                 and ctx.inicio <= c.occurred_at <= ctx.fim
                 and getattr(c, "policy_ref", "") in carteira]
    premio = 0.0
    premio_por_seguradora: Dict[str, float] = {}
    for a in ctx.apolices:
        if not a.premio_conhecido or a.e_endosso:
            continue
        premio += a.premio
        rotulo = str(getattr(a, "seguradora", "") or "").strip() or "(não informado)"
        premio_por_seguradora[rotulo] = premio_por_seguradora.get(rotulo, 0.0) + a.premio
    if not premio:
        return None, None, [], [
            "nenhum prêmio legível na carteira do período: INDISPONÍVEL — sem "
            "denominador não há sinistralidade, e zero no denominador não é "
            "zero por cento"]
    if not sinistros:
        return None, None, [], [
            "nenhum sinistro da carteira com ocorrência no período: "
            "INDISPONÍVEL. 🔴 'Sinistralidade zero' seria a melhor notícia "
            "possível, e ela não foi medida"]
    indenizacao = 0.0
    conhecidos = 0
    por_seguradora: Dict[str, Dict[str, Any]] = {}
    for c in sinistros:
        quantia = getattr(getattr(c, "indemnity", None), "amount", None)
        rotulo = str(getattr(c, "insurer", "") or "").strip() or "(não informado)"
        balde = por_seguradora.setdefault(
            rotulo, {"rotulo": rotulo, "sinistros": 0, "indenizacao": 0.0,
                     "premio_da_carteira": premio_por_seguradora.get(rotulo, 0.0)})
        balde["sinistros"] += 1
        if quantia is None:
            continue
        indenizacao += float(quantia)
        conhecidos += 1
        balde["indenizacao"] += float(quantia)
    for balde in por_seguradora.values():
        base = balde["premio_da_carteira"]
        balde["sinistralidade"] = (balde["indenizacao"] / base) if base else None
    if not conhecidos:
        return None, 0.0, [], [
            "nenhum sinistro do período tem indenização legível: INDISPONÍVEL, "
            "e nunca zero"]

    # 🔴 A cobertura desta métrica é sobre o MAPA, e não sobre o dado: ela diz
    # que fração do PRÊMIO está em seguradoras que o cruzamento com o mercado
    # consegue alcançar. Um número de carteira perfeito sobre seguradoras que
    # não mapeiam é um número que não se pode comparar com nada.
    feixe = getattr(ctx, "mercado", None)
    mapeado = 0.0
    if feixe is not None and hasattr(feixe, "coenti_de"):
        for rotulo, valor in premio_por_seguradora.items():
            if feixe.coenti_de(rotulo) != DESCONHECIDA:
                mapeado += valor
    avisos = [f"{conhecidos} de {len(sinistros)} sinistro(s) com indenização "
              f"legível sobre R$ {premio:,.2f} de prêmio da carteira"]
    if feixe is None:
        avisos.append(
            "o censo do mercado não veio nesta rodada: a cobertura do MAPA não "
            "pôde ser medida, e a comparação com o mercado fica indisponível")
    elif not mapeado:
        avisos.append(
            "🔴 NENHUMA seguradora da carteira casou com o mapa de entidades: o "
            "número da carteira está certo e não há com o que compará-lo "
            "(P-094.1-SIGLA-SEGURADORA)")
    return (indenizacao / premio,
            (mapeado / premio) if feixe is not None else None,
            sorted(por_seguradora.values(),
                   key=lambda x: -x["indenizacao"]),
            avisos)


_DEFINICOES.append(dict(
    metric_id="claims.loss_ratio_portfolio", version=1,
    label="Sinistralidade da carteira da corretora", grain="company",
    unit="ratio",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status", "portfolio.policies"),
    formula=_sinistralidade_da_carteira,
    coverage_rule="fração do PRÊMIO do período que está em seguradoras casadas "
                  "com o mapa de entidades — é ela que diz quanto da carteira "
                  "consegue ser comparado com o mercado",
    forbidden_fallback="⛔ sinistro sem indenização legível não entra como zero, "
                       "e prêmio ausente não vira denominador 1",
    premissa="⚠️ a indenização da carteira é a REGISTRADA pela corretora e o "
             "prêmio é o da emissão: as duas pontas não têm o mesmo regime de "
             "competência do mercado. É uma aproximação declarada, e não a "
             "mesma conta que o regulador publica",
    pergunta_verificada="Qual é a sinistralidade da minha carteira no período?",
    golden=golden(0.1724137931034483),
))


# --------------------------------------------------------------------------
# claims.loss_ratio_vs_market — a DERIVED, com as duas fontes declaradas
# --------------------------------------------------------------------------
def _carteira_contra_mercado(ctx: Contexto) -> Saida:
    feixe = getattr(ctx, "mercado", None)
    if feixe is None or not list(getattr(feixe, "facts", ()) or ()):
        return _sem_feixe()
    fatos = getattr(ctx, "fatos", None)
    carteira = {p.policy_ref for p in list(getattr(fatos, "policies", ()) or ())
                if getattr(p, "policy_ref", "")}
    sinistros = [c for c in list(getattr(fatos, "claims", ()) or ())
                 if getattr(c, "occurred_at", None) is not None
                 and ctx.inicio <= c.occurred_at <= ctx.fim
                 and getattr(c, "policy_ref", "") in carteira]

    premio_por_seguradora: Dict[str, float] = {}
    for a in ctx.apolices:
        if not a.premio_conhecido or a.e_endosso:
            continue
        rotulo = str(getattr(a, "seguradora", "") or "").strip()
        if rotulo:
            premio_por_seguradora[rotulo] = (
                premio_por_seguradora.get(rotulo, 0.0) + a.premio)
    indenizacao_por_seguradora: Dict[str, float] = {}
    for c in sinistros:
        quantia = getattr(getattr(c, "indemnity", None), "amount", None)
        rotulo = str(getattr(c, "insurer", "") or "").strip()
        if rotulo and quantia is not None:
            indenizacao_por_seguradora[rotulo] = (
                indenizacao_por_seguradora.get(rotulo, 0.0) + float(quantia))

    competencias = _competencias(ctx.inicio, ctx.fim)
    celulas = _celulas_do_periodo(ctx, feixe, competencias)
    mercado_por_coenti: Dict[str, List[Any]] = {}
    for c in celulas:
        mercado_por_coenti.setdefault(
            str(getattr(c, "coenti", "") or "").strip(), []).append(c)

    linhas = []
    sem_mapa: List[str] = []
    sem_mercado: List[str] = []
    for rotulo, premio in premio_por_seguradora.items():
        coenti = feixe.coenti_de(rotulo)
        if coenti == DESCONHECIDA:
            sem_mapa.append(rotulo)
            continue
        itens = mercado_por_coenti.get(coenti) or []
        if not itens:
            sem_mercado.append(f"{rotulo}·{coenti}")
            continue
        premio_mercado, sinistro_mercado, estorno = _agregar(itens)
        if not premio_mercado or not premio:
            continue
        minha = indenizacao_por_seguradora.get(rotulo, 0.0) / premio
        dele = sinistro_mercado / premio_mercado
        linhas.append({"rotulo": rotulo, "coenti": coenti,
                       "premio_da_carteira": premio,
                       "sinistralidade_da_carteira": minha,
                       "sinistralidade_do_mercado": dele,
                       "diferenca": minha - dele, "estorno": estorno})

    avisos = list(_defasagem(feixe))
    if sem_mapa:
        avisos.append(
            f"{len(sem_mapa)} seguradora(s) da carteira sem entidade no mapa: "
            f"elas ficam FORA da comparação, e NUNCA entram como zero (M2) — "
            f"'sinistra 0% acima do mercado' é uma frase de negociação de "
            f"reajuste, e seria falsa (P-094.1-SIGLA-SEGURADORA)")
    if sem_mercado:
        avisos.append(
            f"{len(sem_mercado)} seguradora(s) mapeada(s) sem célula na base "
            f"pública nas competências do período: fora da comparação")
    if not linhas:
        return None, 0.0, [], avisos + [
            "🔴 nenhuma seguradora da carteira pôde ser comparada com o "
            "mercado: INDISPONÍVEL. As duas fontes existem e não se encontram — "
            "e isto é uma afirmação sobre o MAPA, não sobre a corretora"]
    linhas.sort(key=lambda x: -x["premio_da_carteira"])
    destaque = linhas[0]
    cobertura = (sum(x["premio_da_carteira"] for x in linhas)
                 / sum(premio_por_seguradora.values())
                 if premio_por_seguradora else None)
    return (destaque["diferenca"], cobertura, linhas,
            avisos + [f"destaque: {destaque['rotulo']}, a seguradora de maior "
                      f"prêmio na carteira — diferença em pontos de razão entre "
                      f"a sinistralidade DA CARTEIRA e a DO MERCADO"])


_DEFINICOES.append(dict(
    metric_id="claims.loss_ratio_vs_market", version=1,
    label="A sinistralidade da carteira contra a do mercado, por seguradora",
    grain="insurer", unit="ratio",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status", "portfolio.policies"),
    formula=_carteira_contra_mercado,
    coverage_rule="DERIVED de DUAS fontes: a carteira da corretora (sinistro e "
                  "prêmio lidos do sistema de gestão) e o mercado (a estatística "
                  "pública por entidade, mês e ramo). A cobertura é a fração do "
                  "prêmio da carteira cuja seguradora casou com uma entidade do "
                  "mercado",
    forbidden_fallback="⛔ seguradora fora do mapa sai INDISPONÍVEL, NUNCA zero "
                       "(M2): um '0% acima do mercado' inventado vira argumento "
                       "numa negociação de reajuste",
    premissa="⚠️ as duas pontas não têm o mesmo regime: a carteira traz prêmio "
             "de emissão e indenização registrada; o mercado traz prêmio ganho "
             "e sinistro ocorrido. A diferença é indicativa, e a peça tem de "
             "dizer isso ao lado do número",
    pergunta_verificada="A minha seguradora está sinistrando mais que o mercado?",
    golden=golden(INDISPONIVEL),
))


# --------------------------------------------------------------------------
# market.loss_ratio_trend
# --------------------------------------------------------------------------
def _trimestres_ate(fim: date, quantos: int = TRIMESTRES) -> List[Tuple[str, List[str]]]:
    """Os `quantos` trimestres que terminam no trimestre de `fim`, do mais
    antigo para o mais novo. Cada um com as três competências dele."""
    tri = (fim.month - 1) // 3
    ano = fim.year
    janelas = []
    for _ in range(quantos):
        primeiro = tri * 3 + 1
        janelas.append((f"{ano}Q{tri + 1}",
                        ["%04d%02d" % (ano, primeiro + i) for i in range(3)]))
        tri -= 1
        if tri < 0:
            ano, tri = ano - 1, 3
    return list(reversed(janelas))


def _tendencia(ctx: Contexto) -> Saida:
    feixe = getattr(ctx, "mercado", None)
    if feixe is None or not list(getattr(feixe, "facts", ()) or ()):
        return _sem_feixe()
    mapeados, _sem, _nomes = _entidades_da_carteira(ctx, feixe)
    linhas = []
    for rotulo, competencias in _trimestres_ate(ctx.fim):
        celulas = _celulas_do_periodo(ctx, feixe, competencias)
        if mapeados:
            recorte = [c for c in celulas
                       if str(getattr(c, "coenti", "") or "").strip() in mapeados]
            if recorte:
                celulas = recorte
        premio, sinistro, estorno = _agregar(celulas)
        linhas.append({"rotulo": rotulo, "competencias_com_dado": len({
            str(getattr(c, "damesano", "")) for c in celulas}),
            "premio_ganho": premio, "sinistro_ocorrido": sinistro,
            "sinistralidade": (sinistro / premio) if premio else None,
            "estorno": estorno})
    medidos = [x for x in linhas if x["sinistralidade"] is not None]
    if len(medidos) < 2:
        return None, None, linhas, _defasagem(feixe) + [
            f"só {len(medidos)} trimestre(s) com prêmio na base: INDISPONÍVEL. "
            f"🔴 Uma tendência com um ponto é uma reta inventada"]
    delta = medidos[-1]["sinistralidade"] - medidos[0]["sinistralidade"]
    if delta > LIMIAR_DE_MOVIMENTO:
        sinal = "▲"
    elif delta < -LIMIAR_DE_MOVIMENTO:
        sinal = "▼"
    else:
        sinal = "="
    for i, x in enumerate(linhas):
        anterior = linhas[i - 1]["sinistralidade"] if i else None
        if x["sinistralidade"] is None or anterior is None:
            x["sinal"] = "="
            continue
        passo = x["sinistralidade"] - anterior
        x["sinal"] = ("▲" if passo > LIMIAR_DE_MOVIMENTO
                      else "▼" if passo < -LIMIAR_DE_MOVIMENTO else "=")
    return (delta, len(medidos) / len(linhas), linhas,
            _defasagem(feixe) + [
                f"{sinal} {medidos[0]['rotulo']} → {medidos[-1]['rotulo']}: "
                f"variação de {delta:+.4f} em pontos de razão",
                "⚠️ três trimestres mostram MOVIMENTO, e não causa: um estorno "
                "de provisão num deles muda o desenho sem que nada tenha "
                "acontecido com os sinistros"])


_DEFINICOES.append(dict(
    metric_id="market.loss_ratio_trend", version=1,
    label="Tendência da sinistralidade do mercado em 3 trimestres",
    grain="quarter", unit="ratio",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=(),
    formula=_tendencia,
    coverage_rule="fração dos 3 trimestres que têm prêmio ganho na base "
                  "pública — trimestre sem dado fica sem ponto, e não vira zero",
    forbidden_fallback="⛔ trimestre ausente NUNCA entra como sinistralidade 0: "
                       "isso desenharia uma queda que não houve, que é "
                       "exatamente a frase que o dono levaria para a negociação",
    premissa="💭 o sinal ▲▼= usa um limiar de 0,01 em pontos de razão: abaixo "
             "disso é oscilação de competência, e chamar de tendência seria "
             "prometer movimento onde há ruído",
    pergunta_verificada="A sinistralidade do mercado está subindo ou caindo nos "
                        "últimos três trimestres?",
    golden=golden(INDISPONIVEL),
))
