# -*- coding: utf-8 -*-
"""Carteira: cancelamento, cross-sell e pendência de emissão — SPEC-094.1 · BLOCO A.

## A armadilha que esta peça existe para não cair — e ela é medida

📊 O censo v2.1 §A7: a rota que traz os cancelamentos, chamada com o parâmetro
"cancelado", devolveu **3.861 linhas** em 2025 — **3.536 com o campo em `F` e
325 com o campo em `T`**. O parâmetro **INCLUI** os cancelados; ele não filtra.

```
taxa de cancelamento 2025 = 325 / 3.861 = 8,4%      📊 medido, corretora piloto
```

⛔ Quem tratar a chamada como recorte publica **a carteira inteira como
cancelada** — e o número **responde**, não trava. É o CLAUDE.md §9.5 em estado
puro: o passo que trava é barulhento; o que responde errado chega ao dono.

🔴 A fórmula daqui **nunca vê a chamada**: ela conta o campo `status` de cada
apólice, que o adapter escreveu com a única função que decide isso
(`status_de_apolice`). É essa separação que faz a armadilha ser impossível
daqui de dentro — e é por isso que a mutação do guarda tem de atacar a
fronteira, e não a fórmula.

## E o cross-sell conta RAMO, não apólice

🔴 Um cliente com três apólices do mesmo ramo tem **um** produto. Contar
apólices infla o cross-sell da corretora inteira e transforma a lista de
oportunidades numa lista de clientes que já compraram.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

_DEFINICOES: List[Dict[str, Any]] = []

FIXTURE = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"
INDISPONIVEL = "UNAVAILABLE"

#: 💭 Quantas linhas de ramo ausente vão ao pacote. Cinco cabem numa frase de
#: recomendação; o resto seria lista para ninguém ler.
TETO_DE_RAMOS = 5

Contexto = Any
Saida = Any


def golden(esperado):
    return {"fixture": FIXTURE, "esperado": esperado}


def instalar(reg) -> None:
    for kw in _DEFINICOES:
        reg.registrar(reg.MetricDefinition(**kw))


def _apolices_do_feixe(ctx: Contexto) -> List[Any]:
    """As apólices CRUAS do período — com `status`, que a visão não projeta."""
    fatos = getattr(ctx, "fatos", None)
    saida = []
    for p in list(getattr(fatos, "policies", ()) or ()):
        quando = getattr(p, "valid_from", None)
        if quando is not None and ctx.inicio <= quando <= ctx.fim:
            saida.append(p)
    return saida


# --------------------------------------------------------------------------
# portfolio.cancellation_rate
# --------------------------------------------------------------------------
def _cancelamento(ctx: Contexto) -> Saida:
    apolices = _apolices_do_feixe(ctx)
    if not apolices:
        return None, None, [], [
            "nenhuma apólice com início de vigência no período: INDISPONÍVEL, "
            "e não 0% de cancelamento"]
    canceladas = [p for p in apolices if getattr(p, "status", "") == "CANCELLED"]
    conhecidas = [p for p in apolices
                  if str(getattr(p, "status", "") or "").strip()]
    if not conhecidas:
        return None, 0.0, [], [
            "nenhuma apólice do período tem estado legível: INDISPONÍVEL. 🔴 "
            "'0% de cancelamento' seria a melhor notícia possível, afirmada "
            "sobre um campo em branco"]
    por_seguradora: Dict[str, Dict[str, Any]] = {}
    for p in apolices:
        rotulo = str(getattr(p, "insurer", "") or "").strip() or "(não informado)"
        balde = por_seguradora.setdefault(
            rotulo, {"rotulo": rotulo, "apolices": 0, "canceladas": 0})
        balde["apolices"] += 1
        if getattr(p, "status", "") == "CANCELLED":
            balde["canceladas"] += 1
    for balde in por_seguradora.values():
        balde["taxa_pct"] = (100.0 * balde["canceladas"] / balde["apolices"]
                             if balde["apolices"] else None)
    linhas = sorted(por_seguradora.values(),
                    key=lambda x: (-(x["canceladas"]), x["rotulo"]))
    return (100.0 * len(canceladas) / len(apolices),
            len(conhecidas) / len(apolices),
            linhas,
            [f"{len(canceladas)} cancelada(s) em {len(apolices)} apólice(s) do "
             f"período — a população INCLUI as canceladas, que é a única forma "
             f"de a taxa existir"])


_DEFINICOES.append(dict(
    metric_id="portfolio.cancellation_rate", version=1,
    label="Taxa de cancelamento da carteira", grain="company", unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.cancellations",),
    formula=_cancelamento,
    coverage_rule="fração das apólices do período cujo estado (ativa ou "
                  "cancelada) veio legível da fonte",
    forbidden_fallback="⛔ estado em branco NUNCA conta como ativa: isso baixaria "
                       "a taxa de cancelamento com o dado que falta, que é a "
                       "direção mais confortável de errar",
    premissa="🔴 a taxa é `canceladas ÷ (canceladas + ativas)` sobre a MESMA "
             "população. A fonte devolve as duas juntas quando se pede para "
             "incluir as canceladas — e quem ler esse pedido como um recorte "
             "publica a carteira inteira como cancelada",
    pergunta_verificada="Que porcentagem da carteira do período foi cancelada, "
                        "e em que seguradoras?",
    golden=golden(16.666666666666668),
))


# --------------------------------------------------------------------------
# customer.single_product_share
# --------------------------------------------------------------------------
def _um_produto_so(ctx: Contexto) -> Saida:
    fatos = getattr(ctx, "fatos", None)
    clientes = list(getattr(fatos, "customers", ()) or ())
    if not clientes:
        return None, None, [], [
            "nenhuma ligação cliente↔apólice foi lida: INDISPONÍVEL. 🔴 Sem "
            "ela não há como dizer quem tem um produto só, e '0% de "
            "monoproduto' seria a afirmação mais otimista possível sobre uma "
            "leitura que não houve"]
    com_ramo = [c for c in clientes if getattr(c, "branches", ())]
    if not com_ramo:
        return None, 0.0, [], [
            "nenhum cliente tem ramo legível: INDISPONÍVEL, e não zero"]
    de_um = [c for c in com_ramo if len(
        {str(b or "").strip().upper() for b in c.branches if str(b or "").strip()}) <= 1]

    # 🔴 O que FALTA a quem tem um produto só — é isto que vira trabalho.
    # ⚠️ O universo de ramos é o da PRÓPRIA carteira, e não uma lista fixa de
    # produtos: oferecer o que a corretora não vende é gerar tarefa impossível.
    universo: Dict[str, int] = {}
    for c in com_ramo:
        for b in c.branches:
            rotulo = str(b or "").strip().upper()
            if rotulo:
                universo[rotulo] = universo.get(rotulo, 0) + 1
    ausentes: Dict[str, int] = {}
    for c in de_um:
        tem = {str(b or "").strip().upper() for b in c.branches}
        for ramo in universo:
            if ramo not in tem:
                ausentes[ramo] = ausentes.get(ramo, 0) + 1
    linhas = [{"rotulo": ramo, "clientes_sem_ele": n,
               "share_pct": 100.0 * n / len(de_um) if de_um else None}
              for ramo, n in sorted(ausentes.items(),
                                    key=lambda x: (-x[1], x[0]))[:TETO_DE_RAMOS]]
    return (100.0 * len(de_um) / len(com_ramo),
            len(com_ramo) / len(clientes),
            linhas,
            [f"{len(de_um)} de {len(com_ramo)} cliente(s) com um produto só — "
             f"produto é RAMO DISTINTO, e não apólice: três apólices do mesmo "
             f"ramo continuam sendo um produto"])


_DEFINICOES.append(dict(
    metric_id="customer.single_product_share", version=1,
    label="Clientes com um produto só", grain="customer", unit="pct",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("contacts.customer",),
    formula=_um_produto_so,
    coverage_rule="fração dos clientes lidos que têm ao menos um ramo legível — "
                  "quem não tem ramo não é 'monoproduto', é ilegível",
    forbidden_fallback="⛔ cliente sem ramo legível NUNCA entra como monoproduto: "
                       "ele infla a lista de oportunidade com trabalho que não "
                       "existe",
    premissa="🔴 a referência do cliente é opaca (hash): o cross-sell não precisa "
             "saber quem é o cliente, e o nome não atravessa a fronteira",
    pergunta_verificada="Quantos clientes têm um produto só, e qual ramo falta a "
                        "eles?",
    golden=golden(66.66666666666667),
))


# --------------------------------------------------------------------------
# issuance.pending — INDISPONÍVEL por CUSTO, e o custo está medido
# --------------------------------------------------------------------------
def _pendencia_de_emissao(ctx: Contexto) -> Saida:
    """🔴 Sempre `None`, e o motivo é um NÚMERO, não uma opinião.

    📊 O campo de acompanhamento existe numa rota só, e ela responde **uma
    apólice por chamada**. As rotas em lote não o trazem. Com as 1.680 apólices
    do controle-ouro, a pendência de emissão custaria 1.680 requisições por
    pergunta — e a pergunta é feita numa conversa.

    ⚠️ E o lote nem tenta: o adapter deixa a rota FORA do mapa de rotas lidas.
    "Não perguntei" não pode virar "perguntei e não veio nada" — a segunda
    autorizaria uma afirmação sobre o período.
    """
    apolices = _apolices_do_feixe(ctx)
    return None, None, [], [
        "pendência de emissão INDISPONÍVEL por CUSTO medido: o campo de "
        "acompanhamento só existe na rota de UMA apólice por chamada, e a rota "
        "em lote não o traz (P-094.1-ISSUANCE). "
        f"({len(apolices)} apólice(s) no período — nenhuma consultada)",
        "🔴 isto é uma afirmação sobre a FONTE. 'Zero pendências de emissão' "
        "seria uma afirmação sobre a corretora, e ela não foi medida",
    ]


_DEFINICOES.append(dict(
    metric_id="issuance.pending", version=1,
    label="Apólices com emissão pendente", grain="policy", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("portfolio.policy_status",),
    formula=_pendencia_de_emissao,
    coverage_rule="não há cobertura a declarar: nenhuma apólice foi consultada "
                  "individualmente, e é da consulta individual que o campo vem",
    forbidden_fallback="⛔ NUNCA devolver 0: 'nenhuma emissão pendente' é a "
                       "melhor notícia que esta métrica poderia dar, e ela seria "
                       "inventada",
    premissa="📊 P-094.1-ISSUANCE: a rota existe e o campo existe; o que falta é "
             "uma leitura em LOTE. Não é 'ainda não olhamos'",
    pergunta_verificada="Quantas apólices estão com a emissão pendente na "
                        "seguradora?",
    golden=golden(INDISPONIVEL),
))
