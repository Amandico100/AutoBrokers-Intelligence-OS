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
            kind=RENEWAL if renov else NEW, status="vigente",
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
    lote.provenance = Provenance(connection_id="", correlation_id="fixture",
                                 fetched_at=datetime(2026, 9, 3))
    return lote
