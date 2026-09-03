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

from datetime import date
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
    from datetime import datetime
    return datetime.now()
