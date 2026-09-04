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

## 🔴 Por que a conta NÃO depende da junção com a carteira — conserto de 04/09/2026

📊 **Medido: a junção dá ZERO.** Os 40 documentos citados pelos sinistros da
corretora piloto não aparecem entre as 3.861 linhas de carteira do ano — as
apólices sinistradas são de outros exercícios, o que é o normal de um sinistro.
A regra anterior — *"conta só o que junta, e junção vazia sai UNAVAILABLE"* —
fazia **toda** métrica de sinistro sair INDISPONÍVEL na pergunta real.

```
o TOTAL é a população da fonte de sinistros    é o que o dono perguntou
"quantos estão na carteira lida" é BREAKDOWN   informativo, e nunca o denominador
```

⚠️ A junção continua sendo medida e escrita — ela responde *"quantos destes eu
consigo amarrar à carteira que li"*, que é uma pergunta legítima. O que ela
deixou de ser é o **filtro** do total: um sinistro existe quer eu tenha lido a
apólice dele ou não.

🔴 E o zero continua sendo proibido por descarte: população vazia sai
`UNAVAILABLE`. O que mudou é que "não juntou" parou de ser "não existe".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

_DEFINICOES: List[Dict[str, Any]] = []

FIXTURE = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"
INDISPONIVEL = "UNAVAILABLE"

#: Os estados do sinistro, no vocabulário canônico. 🔴 Escritos aqui como
#: constantes e não como literais espalhados: `CLOSED_PAID` e `CLOSED_DENIED`
#: são a diferença entre indenização paga e indenização NEGADA, e comparar com
#: a string errada em um só lugar reintroduz a soma do que ninguém pagou.
ABERTO = "OPEN"
ENCERRADO_PAGO = "CLOSED_PAID"
ENCERRADO_NEGADO = "CLOSED_DENIED"
ENCERRADO = "CLOSED"
NAO_RECONHECIDO = "UNKNOWN"
ENCERRADOS = (ENCERRADO_PAGO, ENCERRADO_NEGADO, ENCERRADO)

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


def _juncao(itens: List[Any], carteira: set) -> Dict[str, Any]:
    """A linha INFORMATIVA da junção com a carteira lida.

    🔴 Ela é um `breakdown`, e não um denominador. 📊 Na corretora piloto a
    interseção é ZERO — as apólices sinistradas são de exercícios anteriores —, e
    usá-la como filtro fazia toda métrica de sinistro sair INDISPONÍVEL numa
    carteira que tem sinistro.
    """
    dentro = len([c for c in itens if getattr(c, "policy_ref", "") in carteira])
    return {"rotulo": "na carteira lida", "sinistros": dentro,
            "fora_da_carteira": len(itens) - dentro,
            "share_pct": (100.0 * dentro / len(itens)) if itens else None}


def _aviso_da_juncao(linha: Dict[str, Any]) -> List[str]:
    fora = linha["fora_da_carteira"]
    if not fora:
        return []
    return [f"{fora} sinistro(s) do período não têm apólice na carteira lida: "
            f"eles CONTAM no total (o sinistro existe), e a linha 'na carteira "
            f"lida' do detalhe diz quantos foi possível amarrar. 🔴 Filtrar o "
            f"total por esta junção transformaria uma leitura incompleta da "
            f"carteira em 'a corretora não tem sinistro'"]


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
        if getattr(c, "status", "") == ABERTO:
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
    abertos = [c for c in do_periodo if getattr(c, "status", "") == ABERTO]
    desconhecidos = [c for c in do_periodo
                     if getattr(c, "status", "") == NAO_RECONHECIDO]
    avisos = [AVISO_DA_BASE]
    if desconhecidos:
        # 🔴 Eles NÃO entram em `abertos` e não podem sumir: um caso que o
        # software não classificou continua sendo um caso do dono.
        avisos.append(
            f"{len(desconhecidos)} sinistro(s) do período com situação NÃO "
            f"RECONHECIDA: eles não entram nesta contagem e também não estão "
            f"encerrados — o total de abertos é um PISO enquanto eles existirem")
    if not abertos:
        # ⚠️ AQUI o zero é legítimo, e é o único lugar deste arquivo onde ele é:
        # houve população, ela foi lida, e nenhum caso está aberto. É uma
        # afirmação sobre a corretora, sustentada por linhas.
        return 0.0, 1.0, [], [
            f"{len(do_periodo)} sinistro(s) no período e nenhum em aberto"
        ] + avisos
    # 🔴 O total é a POPULAÇÃO DA FONTE, e a junção com a carteira é uma linha
    # informativa do detalhe. 📊 A interseção medida na corretora piloto é ZERO
    # (as apólices sinistradas são de outros exercícios): usá-la como filtro
    # devolvia INDISPONÍVEL sobre uma carteira que tem sinistro aberto.
    linha_da_juncao = _juncao(abertos, _carteira(ctx))
    return (float(len(abertos)),
            1.0,
            _por_rotulo(abertos, "insurer") + [linha_da_juncao],
            avisos + _aviso_da_juncao(linha_da_juncao))


_DEFINICOES.append(dict(
    metric_id="claims.open_count", version=1,
    label="Sinistros abertos da carteira", grain="company", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status",),
    formula=_abertos,
    coverage_rule="a contagem é INTEGRAL sobre os sinistros abertos que a fonte "
                  "devolveu no período; quantos deles se amarram à carteira "
                  "lida é uma linha do detalhe, e nunca o denominador",
    forbidden_fallback="⛔ junção vazia NUNCA reduz o total nem vira 0: 'nenhum "
                       "sinistro aberto' é uma afirmação sobre a corretora, e "
                       "'nada juntou' é uma afirmação sobre a leitura da "
                       "carteira — 📊 a interseção medida na fonte piloto é ZERO",
    premissa=AVISO_DA_BASE,
    pergunta_verificada="Quantos sinistros abertos temos na carteira, e em que "
                        "seguradoras eles estão?",
    golden=golden(4.0),
))


# --------------------------------------------------------------------------
# claims.indemnity_paid
# --------------------------------------------------------------------------
def _indenizacao(ctx: Contexto) -> Saida:
    do_periodo = _sinistros(ctx)
    if not do_periodo:
        return _sem_populacao(str(ctx.periodo))
    # 🔴 SÓ `CLOSED_PAID`. 📊 O defeito consertado em 04/09/2026: a régua de
    # situação mandava `negado` e `indeferido` para o mesmo estado que
    # `liquidado`, e esta soma incluía a indenização de sinistros NEGADOS —
    # dinheiro que ninguém pagou, num número que o dono levaria à seguradora.
    pagos = [c for c in do_periodo if getattr(c, "status", "") == ENCERRADO_PAGO]
    negados = [c for c in do_periodo
               if getattr(c, "status", "") == ENCERRADO_NEGADO]
    encerrados_sem_desfecho = [c for c in do_periodo
                               if getattr(c, "status", "") == ENCERRADO]
    avisos = [AVISO_DA_BASE]
    if negados:
        avisos.append(
            f"{len(negados)} sinistro(s) NEGADO(S) no período ficam FORA desta "
            f"soma: a indenização deles existe como valor pedido e não como "
            f"valor pago")
    if encerrados_sem_desfecho:
        avisos.append(
            f"{len(encerrados_sem_desfecho)} sinistro(s) encerrado(s) sem "
            f"rótulo de desfecho legível ficam fora da soma: 'encerrado' não é "
            f"'pago', e somá-los aqui seria afirmar um pagamento")
    encerrados = pagos
    if not encerrados:
        return None, None, [], avisos + [
            "nenhum sinistro ENCERRADO COM PAGAMENTO no período: INDISPONÍVEL, "
            "e não R$ 0,00 de indenização"]
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
    linha_da_juncao = _juncao(encerrados, _carteira(ctx))
    return (total, conhecidos / len(encerrados),
            _por_rotulo(encerrados, "insurer") + [linha_da_juncao],
            avisos + _aviso_da_juncao(linha_da_juncao))


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
    premissa="🔴 ENCERRADO COM DESFECHO DE PAGAMENTO é o mais perto de PAGO que "
             "a fonte expõe: ela devolve "
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
    # 🔴 A concentração é sobre a população da FONTE, e não sobre a interseção
    # com a carteira. 📊 A interseção medida é ZERO na corretora piloto, e a
    # regra antiga devolvia INDISPONÍVEL para uma pergunta que tem resposta.
    avisos = [AVISO_DA_BASE]
    linhas = _por_rotulo(do_periodo, "insurer")
    total = sum(x["sinistros"] for x in linhas)
    maior = linhas[0]["sinistros"] if linhas else 0
    linha_da_juncao = _juncao(do_periodo, _carteira(ctx))
    return (100.0 * maior / total if total else None,
            1.0,
            linhas + [linha_da_juncao],
            avisos + _aviso_da_juncao(linha_da_juncao))


_DEFINICOES.append(dict(
    metric_id="claims.by_insurer", version=1,
    label="Concentração dos sinistros na maior seguradora", grain="insurer",
    unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("claims.status",),
    formula=_por_seguradora,
    coverage_rule="a concentração é INTEGRAL sobre os sinistros que a fonte "
                  "devolveu no período; a linha 'na carteira lida' do detalhe "
                  "diz quantos se amarram à carteira, e não filtra nada",
    forbidden_fallback="⛔ sinistro sem seguradora vira '(não informado)' e "
                       "aparece na tabela; ele nunca é rateado entre as "
                       "conhecidas",
    premissa=AVISO_DA_BASE,
    pergunta_verificada="Que fatia dos meus sinistros está numa seguradora só?",
    golden=golden(40.0),
))
