# -*- coding: utf-8 -*-
"""O provider de REFERÊNCIA — SPEC-094 BLOCO B/G. ⛔ **Test-only.**

Ele devolve fatos CBIM de fixture e **não importa `fonte_infocap`**. Não é um
mock: é o segundo provider, e existe para responder a uma pergunta que nenhuma
outra prova responde.

## A pergunta que só ele responde

> **A fórmula precisa mudar quando o provider muda?**

É a mutação **M17**. Um registry pode passar em todos os testes, com números
certos, e ainda assim ter a InfoCap costurada por dentro — basta um `if
provider ==`, um campo com nome de provider, uma ordenação que depende de como
`/renovacoes` devolve. Nenhum teste sobre a InfoCap pega isso, porque **todos
eles rodam sobre a InfoCap.**

O guarda roda TODO o registry duas vezes sobre a MESMA fixture: uma traduzida
pelo adapter InfoCap (com o HTTP falso), outra entregue direto por este
provider. Se algum `MetricResult` divergir, a fórmula conhece o provider.

```
fixture sintética  ──►  adapter InfoCap (HTTP falso)  ──►  CBIM  ──┐
                                                                   ├──►  MESMOS MetricResult
fixture sintética  ──►  reference provider (direto)   ──►  CBIM  ──┘
```

⛔ E ele **não se registra** no `_REGISTRY` ao ser importado. O adapter da
InfoCap se registra porque é o provider de produção; este entraria numa lista
que alguém, um dia, iteraria em produção. Quem quiser usá-lo chama
`register_brokerage_analytics_provider(...)` no teste, e o teste desfaz.

⛔ E ele **não tem resolver, não tem credencial e não tem rede**. Se um dia
alguém precisar dele fora de teste, a peça que falta não é este arquivo — é um
adapter de verdade, com acesso medido (M13).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.comercial.cbim import (
    CommissionFact,
    FactSet,
    PolicyFact,
    ProducerAssignmentFact,
    Provenance,
    RenewalFact,
)

PROVIDER_KEY = "referencia"


class ReferenceAnalyticsProvider:
    """Implementa `BrokerageAnalyticsProvider` sobre fatos já canônicos.

    ⚠️ `capabilities()` devolve o que o TESTE mandar — e o default é
    deliberadamente **não** o da InfoCap. Um provider de referência que
    copiasse o manifesto da InfoCap provaria que a InfoCap bate consigo mesma.
    """

    provider_key = PROVIDER_KEY

    def __init__(self, lote: Optional[FactSet] = None,
                 capacidades: Optional[Dict[str, str]] = None) -> None:
        self._lote = lote or FactSet(provider_key=PROVIDER_KEY)
        self._capacidades = dict(capacidades or {})

    # ------------------------------------------------------------------ API
    async def capabilities(self, *, company_id: str = "", **kw: Any) -> Dict[str, str]:
        return dict(self._capacidades)

    async def fatos(self, *, company_id: str, inicio: date, fim: date,
                    **kw: Any) -> FactSet:
        """O lote de fixture, com o `company_id` de quem perguntou.

        🔴 O `company_id` é reescrito no lote porque o isolamento por tenant é
        do CBIM, não do provider: um lote de fixture que ficasse com o
        `company_id` de outra corretora passaria num teste e ensinaria o
        contrário do que a §7 do CLAUDE.md exige.
        """
        lote = FactSet(
            company_id=company_id or self._lote.company_id,
            provider_key=PROVIDER_KEY,
            policies=list(self._lote.policies),
            assignments=list(self._lote.assignments),
            commissions=list(self._lote.commissions),
            renewals=list(self._lote.renewals),
            # SPEC-094.1: as tres populacoes novas viajam junto, ou o provider
            # de referencia deixaria de ser a outra ponta da M17 justamente nas
            # metricas novas — que sao as que ninguem provou ainda.
            claims=list(self._lote.claims),
            quotes=list(self._lote.quotes),
            customers=list(self._lote.customers),
            warnings=list(self._lote.warnings),
            fingerprints=dict(self._lote.fingerprints),
        )
        lote.provenance = self._lote.provenance or Provenance(
            connection_id="", correlation_id="referencia",
            fetched_at=kw.get("fetched_at") or _AGORA(),
            fingerprint="", account_fingerprint="")
        return lote

    async def policies(self, *, company_id: str, inicio: date, fim: date,
                       time_basis: str = "POLICY_VALID_FROM",
                       **kw: Any) -> List[PolicyFact]:
        return (await self.fatos(company_id=company_id, inicio=inicio, fim=fim)).policies

    async def producer_assignments(self, *, company_id: str, inicio: date,
                                   fim: date, **kw: Any) -> List[ProducerAssignmentFact]:
        return (await self.fatos(company_id=company_id, inicio=inicio, fim=fim)).assignments

    async def commissions(self, *, company_id: str, inicio: date, fim: date,
                          **kw: Any) -> List[CommissionFact]:
        return (await self.fatos(company_id=company_id, inicio=inicio, fim=fim)).commissions

    async def renewals(self, *, company_id: str, inicio: date, fim: date,
                       **kw: Any) -> List[RenewalFact]:
        return (await self.fatos(company_id=company_id, inicio=inicio, fim=fim)).renewals

    # ---------------------------------------------------------- SPEC-094.1
    # 🔴 Devolvem o LOTE, como o adapter da fonte piloto devolve. A M17 compara
    # `MetricResult` por `MetricResult` entre os dois caminhos: se as assinaturas
    # divergirem, a comparacao deixa de ser possivel e o guarda vira carimbo.
    async def claims(self, *, company_id: str, inicio: date, fim: date,
                     **kw: Any) -> FactSet:
        return await self.fatos(company_id=company_id, inicio=inicio, fim=fim)

    async def quotes(self, *, company_id: str, inicio: date, fim: date,
                     **kw: Any) -> FactSet:
        return await self.fatos(company_id=company_id, inicio=inicio, fim=fim)

    async def cancellations(self, *, company_id: str, inicio: date, fim: date,
                            **kw: Any) -> FactSet:
        return await self.fatos(company_id=company_id, inicio=inicio, fim=fim)

    async def customer_links(self, *, company_id: str, inicio: date, fim: date,
                             **kw: Any) -> FactSet:
        return await self.fatos(company_id=company_id, inicio=inicio, fim=fim)

    async def issuance_status(self, *, company_id: str, inicio: date, fim: date,
                              **kw: Any) -> FactSet:
        return await self.fatos(company_id=company_id, inicio=inicio, fim=fim)


def _AGORA():
    return datetime.now()


# ==========================================================================
# A CARTEIRA DE FIXTURE — o outro lado da M17
# ==========================================================================
#
# ⛔ Nenhum dado real, nenhum nome de pessoa. `Produtor Sentinela` e
# `Produtor Delta` são SENTINELAS DE VAZAMENTO: se um deles aparecer na string
# que o modelo recebe, o guarda sabe que o rótulo escapou do Artifact.
#
# 🔴 Estes fatos reproduzem, já em CBIM, a MESMA carteira que a fixture da
# `FonteInfocap` descreve em linguagem de provider. Os dois caminhos têm de
# produzir o mesmo `MetricResult` — se não produzirem, a fórmula conhece o
# provider (M17).
_EMPRESA_DE_FIXTURE = "aaaaaaaa-0000-0000-0000-00000000000a"

_APOLICES_DE_FIXTURE = (
    # (ref, seguradora, ramo, inicio, fim, prêmio, comissão, é renovação)
    ("S0001", "PORT", "AUTO", date(2025, 1, 10), date(2026, 1, 10), "4000.0", "800.0", False),
    ("S0002", "PORT", "AUTO", date(2025, 2, 5), date(2026, 2, 5), "6000.0", "1200.0", True),
    ("S0003", "ALLI", "RESI", date(2025, 3, 20), date(2026, 3, 20), "2000.0", "300.0", False),
    ("S0004", "ALLI", "VIND", date(2025, 6, 11), date(2026, 6, 11), "9000.0", "1500.0", True),
    # 🔴 SPEC-094.1: a UNICA cancelada da fixture. `status` nao entra em
    # nenhuma formula da 094 (nem o `montar_contexto` o le), entao a taxa de
    # cancelamento ganha populacao sem mexer em nenhum golden existente.
    ("S0005", "PORT", "RESI", date(2025, 9, 1), date(2026, 9, 1), "1000.0", "150.0", False),
    ("S0006", "TOKI", "AUTO", date(2025, 11, 2), date(2026, 11, 2), "7000.0", "1050.0", True),
)

_PRODUTORES_DE_FIXTURE = (
    ("S0001", "Produtor Sentinela", "200.0", 25.0),
    ("S0002", "Produtor Sentinela", "300.0", 25.0),
    ("S0004", "Produtor Delta", "15.0", 1.0),
    ("S0006", "Produtor Delta", "10.0", 1.0),
)

_VENCIMENTOS_DE_FIXTURE = (
    ("S0101", "PORT", "AUTO", 12, "3000.0", "Produtor Sentinela"),
    ("S0102", "ALLI", "RESI", 45, "1500.0", "Produtor Sentinela"),
    ("S0103", "TOKI", "AUTO", 80, "5000.0", "Produtor Delta"),
    ("S0104", "PORT", "VIND", -5, "900.0", "Produtor Delta"),
)


#: 🔴 SPEC-094.1 · BLOCO A. As tres populacoes novas, na MESMA carteira.
#:
#: ⛔ Nenhum nome, nenhum CPF, nenhuma placa: as referencias sao opacas por
#: construcao (M16), e os sinistros apontam APOLICES da fixture — e um deles
#: nao aponta nenhuma, de proposito. O sinistro orfao e o que prova que a
#: cobertura da metrica mede alguma coisa: sem ele, "cobertura 100%" seria
#: verdade por acidente.
#:
#: (ref do sinistro, apolice da fixture ou "", seguradora, ramo, situacao,
#:  ocorrencia, aviso, encerramento, indenizacao, franquia)
_SINISTROS_DE_FIXTURE = (
    ("SIN01", "S0001", "PORT", "AUTO", "OPEN",
     date(2025, 4, 10), date(2025, 4, 11), None, "1200.0", "500.0"),
    ("SIN02", "S0002", "PORT", "AUTO", "CLOSED",
     date(2025, 5, 2), date(2025, 5, 3), date(2025, 7, 1), "3000.0", "500.0"),
    ("SIN03", "S0004", "ALLI", "VIND", "OPEN",
     date(2025, 8, 15), date(2025, 8, 16), None, None, None),
    ("SIN04", "S0006", "TOKI", "AUTO", "OPEN",
     date(2025, 11, 20), date(2025, 11, 21), None, "800.0", "1000.0"),
    # 🔴 O ORFAO: sinistro sem documento de origem. Ele existe na populacao e
    # NAO entra na juncao com a carteira — e por causa dele a cobertura de
    # `claims.open_count` e 3/4, e nao 1,0.
    ("SIN05", "", "ALLI", "RESI", "OPEN",
     date(2025, 6, 1), date(2025, 6, 2), None, "500.0", "0.0"),
)

#: O funil. 📊 Na corretora piloto ele esta VAZIO (o censo v2.1 §A4 mediu 1
#: negocio em 2025 e 404 nas outras duas rotas) — a fixture tem linhas porque
#: uma formula sem populacao nao consegue provar que faz a conta certa.
#: (ref, etapa, ramo, criado, fechado, premio esperado)
_COTACOES_DE_FIXTURE = (
    ("NEG01", "EM_ANDAMENTO", "AUTO", date(2025, 3, 3), None, "5000.0"),
    ("NEG02", "EM_ANDAMENTO", "RESI", date(2025, 7, 9), None, "1500.0"),
    ("NEG03", "EM_CALCULO", "AUTO", date(2025, 10, 1), None, None),
)

#: A carteira POR CLIENTE. 🔴 O que conta e o ramo DISTINTO: o cliente com duas
#: apolices do mesmo ramo tem UM produto, e contar apolices infla o cross-sell.
#: (ref do cliente, apolices da fixture)
_CLIENTES_DE_FIXTURE = (
    ("CLI01", ("S0001", "S0002")),      # AUTO, AUTO      -> 1 produto
    ("CLI02", ("S0003", "S0005")),      # RESI, RESI      -> 1 produto
    ("CLI03", ("S0004", "S0006")),      # VIND, AUTO      -> 2 produtos
)


def fatos_de_fixture(company_id: str = _EMPRESA_DE_FIXTURE) -> FactSet:
    """A carteira de fixture, já canônica. ⛔ Não passa por adapter nenhum."""
    from decimal import Decimal

    from app.comercial.cbim import (CommissionFact, Money, NEW, PolicyFact,
                                    ProducerAssignmentFact, RENEWAL,
                                    ProducerAssignmentFact as _PA,
                                    RenewalFact, UNAVAILABLE, policy_ref,
                                    producer_ref)

    lote = FactSet(company_id=company_id, provider_key=PROVIDER_KEY)
    acumulado = {}
    for ref, seg, ramo, ini, fim, premio, comissao, renov in _APOLICES_DE_FIXTURE:
        pref = policy_ref(company_id, PROVIDER_KEY, ref)
        lote.policies.append(PolicyFact(
            policy_ref=pref, source_ref=ref, insurer=seg, branch=ramo,
            valid_from=ini, valid_to=fim, premium=Money(Decimal(premio)),
            kind=RENEWAL if renov else NEW,
            # SPEC-094.1: o vocabulario do CBIM nas duas pontas. S0005 e a
            # unica cancelada da fixture, e a taxa de cancelamento ganha
            # populacao sem mexer em golden nenhum -- `status` nao entra em
            # formula alguma da 094 nem em `montar_contexto`.
            status=("CANCELLED" if ref == "S0005" else "ACTIVE"),
            provider_key=PROVIDER_KEY))
        acumulado.setdefault(pref, {})["a"] = Money(Decimal(comissao))
    for ref, rotulo, repasse, pct in _PRODUTORES_DE_FIXTURE:
        pref = policy_ref(company_id, PROVIDER_KEY, ref)
        lote.assignments.append(ProducerAssignmentFact(
            policy_ref=pref, producer_ref=producer_ref(company_id, rotulo),
            producer_label=rotulo, role_source="", share=pct, order=1))
        acumulado.setdefault(pref, {})["r"] = Money(Decimal(repasse))
    for ref, seg, ramo, dias, premio, rotulo in _VENCIMENTOS_DE_FIXTURE:
        lote.renewals.append(RenewalFact(
            policy_ref=policy_ref(company_id, PROVIDER_KEY, ref),
            valid_to=date(2026, 12, 1),
            producer_ref=producer_ref(company_id, rotulo),
            status_source="A", dias_a_vencer=dias,
            premium=Money(Decimal(premio)), insurer=seg, branch=ramo))
    for pref, partes in acumulado.items():
        lote.commissions.append(CommissionFact(
            policy_ref=pref, broker_commission_accrued=partes.get("a", UNAVAILABLE),
            producer_repasse=partes.get("r", UNAVAILABLE), received=UNAVAILABLE,
            provider_key=PROVIDER_KEY))
    # ---------------------------------------------------------- SPEC-094.1
    from app.comercial.cbim import (ClaimFact, CustomerPortfolioFact,
                                    QuoteFact, claim_ref, customer_ref,
                                    quote_ref)

    ramo_da_apolice = {a[0]: a[2] for a in _APOLICES_DE_FIXTURE}

    for ref, doc, seg, ramo, situacao, oco, avi, enc, ind, fra in _SINISTROS_DE_FIXTURE:
        lote.claims.append(ClaimFact(
            policy_ref=(policy_ref(company_id, PROVIDER_KEY, doc) if doc else ""),
            claim_ref=claim_ref(company_id, PROVIDER_KEY, ref),
            status=situacao, occurred_at=oco, reported_at=avi, closed_at=enc,
            indemnity=Money(Decimal(ind)) if ind else UNAVAILABLE,
            deductible=Money(Decimal(fra)) if fra else UNAVAILABLE,
            insurer=seg, branch=ramo, provider_key=PROVIDER_KEY))

    for ref, etapa, ramo, criado, fechado, premio in _COTACOES_DE_FIXTURE:
        lote.quotes.append(QuoteFact(
            quote_ref=quote_ref(company_id, PROVIDER_KEY, ref),
            stage=etapa, created_at=criado, closed_at=fechado,
            expected_premium=Money(Decimal(premio)) if premio else UNAVAILABLE,
            branch=ramo, lost_reason=UNAVAILABLE, provider_key=PROVIDER_KEY))

    for ref, apolices in _CLIENTES_DE_FIXTURE:
        lote.customers.append(CustomerPortfolioFact(
            customer_ref=customer_ref(company_id, PROVIDER_KEY, ref),
            policy_refs=tuple(policy_ref(company_id, PROVIDER_KEY, a)
                              for a in apolices),
            branches=tuple(dict.fromkeys(ramo_da_apolice[a] for a in apolices)),
            provider_key=PROVIDER_KEY))

    lote.provenance = Provenance(connection_id="", correlation_id="fixture",
                                 fetched_at=datetime(2026, 9, 3))
    return lote
