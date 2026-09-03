# -*- coding: utf-8 -*-
"""Porta `BrokerageAnalyticsProvider` — SPEC-094 BLOCO B.

🔴 **ACL PERMANENTE. A InfoCap é o provider piloto, NUNCA a semântica.**

Este docstring é parte do contrato, e a palavra que importa é *permanente*.
A [orientação da AWS sobre Anti-Corruption Layer][acl-aws] recomenda
**descomissionar** a camada quando a migração terminar. A nossa não termina:
não há migração, há **pluralidade de fontes**. Cada corretora traz o sistema de
gestão que já usa, e a inteligência tem de valer para todas. Quem, um dia,
propuser "simplificar removendo o adapter" estará propondo devolver `nosnum` ao
motor de métrica.

[acl-aws]: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/acl.html
Padrão-mãe: https://learn.microsoft.com/azure/architecture/patterns/anti-corruption-layer

## O que atravessa esta porta, e o que NÃO atravessa

```
✅ atravessa   PolicyFact · ProducerAssignmentFact · CommissionFact · RenewalFact
               Money · UNAVAILABLE · Provenance · FactSet         (tudo do CBIM)
⛔ não atravessa   nosnum · val_c · inivig · fimvig · codfil · prod_docs
                   qualquer dict cru do provider
                   `date.today()` — o período vem de QUEM PERGUNTOU
```

🔴 E a fronteira é de MÃO DUPLA. Do lado de dentro, o motor de métrica não pode
falar InfoCap (mutação M1). Do lado de fora, o provider **não pode orquestrar**:

```
grep -rn 'from app[.]comercial[.](metricas|calculos)' -E backend/app/providers/   ->   0
(escrito com classe de caracteres de propósito: o próprio grep não pode casar
 esta linha, ou o guarda acusaria a documentação dele)
```

Um provider que importasse o registry decidiria QUAIS métricas existem — e a
próxima fonte teria de reimplementar a decisão. O provider entrega fatos; o
registry decide o que fazer com eles.

## Por que o `capabilities()` vem antes de tudo

📊 O censo de 03/09/2026 mediu, na CorpAPI: SUPPORTED 9 · PARTIAL 6 · UNKNOWN 3
· UNAVAILABLE 1. Um provider que não declara o que consegue entregar obriga o
motor a **descobrir por ausência** — e ausência lida como zero é o defeito que
esta SPEC existe para matar. `capabilities()` é a pergunta que se faz **antes**
de pedir o dado, e a resposta `UNKNOWN` lê-se *"não verificado"*, jamais
*"indisponível"*.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from app.comercial.cbim import (
    CommissionFact,
    FactSet,
    PolicyFact,
    ProducerAssignmentFact,
    RenewalFact,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BrokerageAnalyticsProvider",
    "FalhaDoProvider",
    "RecusaDeContaCompartilhada",
    "register_brokerage_analytics_provider",
    "resolve_brokerage_analytics_provider",
    "brokerage_analytics_providers",
]


class FalhaDoProvider(RuntimeError):
    """A fonte não respondeu, ou respondeu o que não dá para traduzir.

    Tipo próprio para que o chat consiga dizer *"a InfoCap não respondeu"* em
    vez de `Exception` — a mesma razão de `FalhaDaInfocap` existir na 081.
    """


class RecusaDeContaCompartilhada(FalhaDoProvider):
    """🔴 Duas corretoras ATIVAS na MESMA conta do provider. A leitura para.

    📊 Não é hipótese: o censo de 03/09/2026 mediu que as conexões `connected`
    da **Amandus** e da **Resulta** descriptografam para o mesmo login, o mesmo
    perfil e uma carteira idêntica ao centavo. Os ciphertexts diferem (o IV do
    Fernet muda a cada escrita), então a tabela **não denuncia**.

    Sem esta recusa, um "como estamos?" na Amandus mostraria a carteira da
    Resulta com a marca da Amandus — cross-tenant silencioso, com número certo
    (CLAUDE.md §7 · §10 (4)). A decisão de qual das duas está errada é do
    Founder: **F-094-07**.
    """


@runtime_checkable
class BrokerageAnalyticsProvider(Protocol):
    """O contrato de leitura analítica da carteira de uma corretora.

    Todo método é `async` porque a tool roda no grafo, que é assíncrono, e
    porque a resolução da conexão é uma consulta ao Supabase.

    🔴 `inicio`/`fim` são `date` puros, e não o `Periodo` de `calculos.py`: o
    provider não importa a camada de cálculo (ver o grep no cabeçalho).
    """

    provider_key: str

    async def capabilities(self, *, company_id: str, **kw: Any) -> Dict[str, str]:
        """`capability → SUPPORTED | PARTIAL | UNAVAILABLE | UNKNOWN | DEGRADED`."""
        ...

    async def fatos(self, *, company_id: str, inicio: date, fim: date,
                    **kw: Any) -> FactSet:
        """O lote inteiro de UMA leitura, com `Provenance` e `warnings`.

        É o método que o registry usa. Os quatro abaixo são recortes dele — e
        são recortes do MESMO lote, nunca quatro leituras: quatro leituras
        dariam quatro `correlation_id` e o Evidence Pack deixaria de ter uma
        procedência só.
        """
        ...

    async def policies(self, *, company_id: str, inicio: date, fim: date,
                       time_basis: str, **kw: Any) -> List[PolicyFact]:
        ...

    async def producer_assignments(self, *, company_id: str, inicio: date,
                                   fim: date, **kw: Any) -> List[ProducerAssignmentFact]:
        ...

    async def commissions(self, *, company_id: str, inicio: date, fim: date,
                          **kw: Any) -> List[CommissionFact]:
        ...

    async def renewals(self, *, company_id: str, inicio: date, fim: date,
                       **kw: Any) -> List[RenewalFact]:
        ...


# --------------------------------------------------------------------------
# O registry — o MESMO padrão de `policy_data_provider.py`
# --------------------------------------------------------------------------
#
# 🔴 Mesmo padrão de propósito (CLAUDE.md §5). `policy_data_provider.py:134-149`
# já resolve provider por chave nesta casa; inventar um segundo mecanismo — com
# entry points, com plugins, com auto-descoberta — seria motor paralelo pago em
# depuração, para resolver um problema que ninguém tem.
_REGISTRY: Dict[str, Any] = {}


def register_brokerage_analytics_provider(provider: Any) -> None:
    key = str(getattr(provider, "provider_key", "") or "").strip().lower()
    if not key:
        raise ValueError("BrokerageAnalyticsProvider requires provider_key")
    _REGISTRY[key] = provider


def resolve_brokerage_analytics_provider(provider_key: str = "infocap") -> Optional[Any]:
    return _REGISTRY.get(str(provider_key or "").strip().lower())


def brokerage_analytics_providers() -> Dict[str, Any]:
    """Cópia do registro. Para diagnóstico e para o guarda — nunca para mutar."""
    return dict(_REGISTRY)
