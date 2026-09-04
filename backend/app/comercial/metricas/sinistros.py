# -*- coding: utf-8 -*-
"""Sinistros da carteira — SPEC-094.1 · BLOCO A.

📊 A rota existia com 5.729 registros e **nenhum leitor**. O gatilho da
pendência `P-094-SINISTROS` foi atingido na 094; esta é a leitura.

## A base temporal desta população, e a dívida que ela carrega

📊 O censo v2.1 §A3 mediu: a janela da fonte prende a **data de OCORRÊNCIA**
(42/42 dentro dela, com o mínimo exatamente no primeiro dia). Não é início nem
fim de vigência de apólice nenhuma.

🔴 E o envelope **não consegue declarar isso hoje**: o contrato de bases
temporais tem exatamente duas entradas, e cinco módulos as desempacotam em par.
Então cada métrica daqui declara a base que o contrato admite **e escreve a
verdadeira no aviso**, toda vez. A dívida tem número: **P-094.1-BASE-DE-SINISTRO**.
⛔ O que não se pode é deixar o envelope afirmar, calado, que o recorte foi por
vigência.

## Por que a conta é sobre a CARTEIRA, e não sobre o acervo

🔴 A pergunta do dono é *"quantos sinistros abertos **temos**"* — e "temos" é a
carteira. Um sinistro cujo documento não está na carteira lida **existe** e
**não** entra no total: ele entra na **cobertura**, que é o que diz quanto do
acervo a conta alcançou.

⚠️ E quando NENHUM dos sinistros abertos junta com a carteira, o resultado é
`UNAVAILABLE` — nunca `0`. 🔴 Zero abertos é uma afirmação sobre a corretora
("não há sinistro em andamento"); junção vazia é uma afirmação sobre a leitura.
As duas se parecem na tela e são opostas na vida do segurado.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

_DEFINICOES: List[Dict[str, Any]] = []

FIXTURE = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"
INDISPONIVEL = "UNAVAILABLE"

#: 🔴 O aviso da base temporal. Ele vai em TODA métrica deste arquivo, porque a
#: divergência entre o que o envelope declara e o que a população é não pode
#: depender de o leitor lembrar.
AVISO_DA_BASE = (
    "a população de sinistros é recortada pela DATA DE OCORRÊNCIA "
    "(CLAIM_OCCURRED_DATE), e não pela vigência da apólice — o campo "
    "`time_basis` do envelope declara a base que o contrato admite hoje "
    "(P-094.1-BASE-DE-SINISTRO)")

Contexto = Any
Saida = Any


def golden(esperado):
    """`{"fixture": ..., "esperado": ...}` — 📊 medido sobre a fixture, não escrito
    de cabeça. O comando está no relatório do BLOCO A."""
    return {"fixture": FIXTURE, "esperado": esperado}


def instalar(reg) -> None:
    for kw in _DEFINICOES:
        reg.registrar(reg.MetricDefinition(**kw))


# --------------------------------------------------------------------------
# As leituras comuns
# --------------------------------------------------------------------------
def _sinistros(ctx: Contexto) -> List[Any]:
    """Os sinistros cuja OCORRÊNCIA cai no período pedido.

    ⚠️ Lido por atributo do feixe, e não de uma projeção do contexto: o motor
    projeta apólices e vencimentos (as duas bases que ele conhece), e um
    sinistro não é nenhum dos dois.
    """
    fatos = getattr(ctx, "fatos", None)
    saida = []
    for c in list(getattr(fatos, "claims", ()) or ()):
        quando = getattr(c, "occurred_at", None)
        if quando is not None and ctx.inicio <= quando <= ctx.fim:
            saida.append(c)
    return saida


def _carteira(ctx: Contexto) -> set:
    """As `policy_ref` da carteira lida. 🔴 É o universo do join.

    ⚠️ Do feixe inteiro, e não do recorte do período: uma apólice cuja vigência
    começou no ano anterior continua sendo carteira, e o sinistro dela é do
    período tanto quanto o outro.
    """
    fatos = getattr(ctx, "fatos", None)
    return {p.policy_ref for p in list(getattr(fatos, "policies", ()) or ())
            if getattr(p, "policy_ref", "")}


def _sem_populacao(quando: str) -> Saida:
    return None, None, [], [
        f"nenhum sinistro com ocorrência no período: {quando} — INDISPONÍVEL, "
        f"e não zero", AVISO_DA_BASE]


def _por_rotulo(itens: List[Any], campo: str) -> List[Dict[str, Any]]:
    baldes: Dict[str, Dict[str, Any]] = {}
    for c in itens:
        rotulo = str(getattr(c, campo, "") or "").strip() or "(não informado)"
        balde = baldes.setdefault(rotulo, {"rotulo": rotulo, "sinistros": 0,
                                           "abertos": 0, "indenizacao": 0.0,
                                           "indenizacao_conhecida": 0})
        balde["sinistros"] += 1
        if getattr(c, "status", "") == "OPEN":
            balde["abertos"] += 1
        quantia = getattr(getattr(c, "indemnity", None), "amount", None)
        if quantia is not None:
            balde["indenizacao"] += float(quantia)
            balde["indenizacao_conhecida"] += 1
    return sorted(baldes.values(), key=lambda x: (-x["sinistros"], x["rotulo"]))


# --------------------------------------------------------------------------
# claims.open_count
# --------------------------------------------------------------------------
def _abertos(ctx: Contexto) -> Saida:
    do_periodo = _sinistros(ctx)
    if not do_periodo:
        return _sem_populacao(str(ctx.periodo))
    abertos = [c for c in do_periodo if getattr(c, "status", "") == "OPEN"]
    if not abertos:
        # ⚠️ AQUI o zero é legítimo, e é o único lugar deste arquivo onde ele é:
        # houve população, ela foi lida, e nenhum caso está aberto. É uma
        # afirmação sobre a corretora, sustentada por linhas.
        return 0.0, 1.0, [], [
            f"{len(do_periodo)} sinistro(s) no período e nenhum em aberto",
            AVISO_DA_BASE]
    carteira = _carteira(ctx)
    na_carteira = [c for c in abertos if getattr(c, "policy_ref", "") in carteira]
    avisos = [AVISO_DA_BASE]
    orfaos = len(abertos) - len(na_carteira)
    if orfaos:
        avisos.append(
            f"{orfaos} sinistro(s) aberto(s) sem apólice na carteira lida: "
            f"eles existem e ficam FORA do total — a cobertura diz quanto")
    if not na_carteira:
        return None, 0.0, [], avisos + [
            "nenhum dos sinistros abertos juntou com a carteira lida: "
            "INDISPONÍVEL. 🔴 Isto é uma afirmação sobre a LEITURA, e não "
            "sobre a corretora não ter sinistro em andamento"]
    return (float(len(na_carteira)),
            len(na_carteira) / len(abertos),
            _por_rotulo(na_carteira, "insurer"),
            avisos)


_DEFINICOES.append(dict(
    metric_id="claims.open_count", version=1,
    label="Sinistros abertos da carteira", grain="company", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status",),
    formula=_abertos,
    coverage_rule="fração dos sinistros abertos do período cuja apólice está na "
                  "carteira lida — o que não junta fica de fora do total e "
                  "aparece aqui",
    forbidden_fallback="⛔ junção vazia NUNCA vira 0: 'nenhum sinistro aberto' é "
                       "uma afirmação sobre a corretora, e 'nada juntou' é uma "
                       "afirmação sobre a leitura",
    premissa=AVISO_DA_BASE,
    pergunta_verificada="Quantos sinistros abertos temos na carteira, e em que "
                        "seguradoras eles estão?",
    golden=golden(3.0),
))


# --------------------------------------------------------------------------
# claims.indemnity_paid
# --------------------------------------------------------------------------
def _indenizacao(ctx: Contexto) -> Saida:
    do_periodo = _sinistros(ctx)
    if not do_periodo:
        return _sem_populacao(str(ctx.periodo))
    carteira = _carteira(ctx)
    encerrados = [c for c in do_periodo
                  if getattr(c, "status", "") == "CLOSED"
                  and getattr(c, "policy_ref", "") in carteira]
    avisos = [AVISO_DA_BASE]
    if not encerrados:
        return None, None, [], avisos + [
            "nenhum sinistro ENCERRADO no período: INDISPONÍVEL, e não R$ 0,00 "
            "de indenização"]
    total = 0.0
    conhecidos = 0
    for c in encerrados:
        quantia = getattr(getattr(c, "indemnity", None), "amount", None)
        if quantia is None:
            continue
        total += float(quantia)
        conhecidos += 1
    if not conhecidos:
        return None, 0.0, [], avisos + [
            "nenhum dos sinistros encerrados tem indenização legível: "
            "INDISPONÍVEL, e nunca zero"]
    return (total, conhecidos / len(encerrados),
            _por_rotulo(encerrados, "insurer"), avisos)


_DEFINICOES.append(dict(
    metric_id="claims.indemnity_paid", version=1,
    label="Indenização dos sinistros encerrados no período", grain="company",
    unit="BRL",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status",),
    formula=_indenizacao,
    coverage_rule="fração dos sinistros encerrados do período com valor de "
                  "indenização legível",
    forbidden_fallback="⛔ indenização ilegível não entra como zero; ela sai da "
                       "soma e aparece no denominador da cobertura",
    premissa="🔴 ENCERRADO é o mais perto de PAGO que a fonte expõe: ela devolve "
             "o valor da indenização e a data de encerramento, e NÃO a data de "
             "pagamento. Nunca apresentar este número como 'o que a seguradora "
             "já depositou'. " + AVISO_DA_BASE,
    pergunta_verificada="Quanto de indenização os sinistros encerrados no "
                        "período somam?",
    golden=golden(3000.0),
))


# --------------------------------------------------------------------------
# claims.by_insurer
# --------------------------------------------------------------------------
def _por_seguradora(ctx: Contexto) -> Saida:
    do_periodo = _sinistros(ctx)
    if not do_periodo:
        return _sem_populacao(str(ctx.periodo))
    carteira = _carteira(ctx)
    na_carteira = [c for c in do_periodo
                   if getattr(c, "policy_ref", "") in carteira]
    avisos = [AVISO_DA_BASE]
    if not na_carteira:
        return None, 0.0, [], avisos + [
            "nenhum sinistro do período juntou com a carteira lida: "
            "INDISPONÍVEL — a concentração seria sobre uma população que não "
            "é a da corretora"]
    linhas = _por_rotulo(na_carteira, "insurer")
    total = sum(x["sinistros"] for x in linhas)
    maior = linhas[0]["sinistros"] if linhas else 0
    if len(na_carteira) < len(do_periodo):
        avisos.append(
            f"{len(do_periodo) - len(na_carteira)} sinistro(s) fora da carteira "
            f"lida não entram na concentração")
    return (100.0 * maior / total if total else None,
            len(na_carteira) / len(do_periodo),
            linhas, avisos)


_DEFINICOES.append(dict(
    metric_id="claims.by_insurer", version=1,
    label="Concentração dos sinistros na maior seguradora", grain="insurer",
    unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status",),
    formula=_por_seguradora,
    coverage_rule="fração dos sinistros do período cuja apólice está na "
                  "carteira lida",
    forbidden_fallback="⛔ sinistro sem seguradora vira '(não informado)' e "
                       "aparece na tabela; ele nunca é rateado entre as "
                       "conhecidas",
    premissa=AVISO_DA_BASE,
    pergunta_verificada="Que fatia dos meus sinistros está numa seguradora só?",
    golden=golden(50.0),
))
