# -*- coding: utf-8 -*-
"""CBIM — o modelo canônico da corretagem. **Nenhum provider entra aqui.**

SPEC-094 · BLOCO A. Peça **pura**: `dataclasses`, `datetime`, `decimal`,
`hashlib`, `typing` — e `evidence_pack`, que também é puro. Não importa
`fonte_infocap`, não importa `app.providers`, não importa Supabase, não sabe
o que é `nosnum`.

## Por que ele existe

📊 SPEC-094 §1.3: `calculos.py` — a camada que a 081 declara "pura" — usa
`nosnum` 7 vezes e `inivig` 1 vez. São nomes de campo da InfoCap dentro do
motor de cálculo. Enquanto for assim, trocar de provider é reescrever a
matemática, e a matemática é a única coisa que não deveria mudar.

O CBIM é o vocabulário que fica quando se tira a InfoCap da frente:

```
PolicyFact              uma apólice, com a vigência e o dinheiro dela
ProducerAssignmentFact  quem vendeu, e com que participação
CommissionFact          o que a corretora apropria, e o que ela repassa
RenewalFact             o que vence, e quando
```

## As três regras que este módulo existe para impor

**1. `UNAVAILABLE` nunca é `0`.** Um prêmio que a fonte não expõe é
indisponível. Zero é uma afirmação sobre o negócio — 📊 e a InfoCap devolve
`val_c: None` em 3.536/3.536 linhas de `/renovacoes`
(`infocap-golden-controls.json`). Somar isso como zero produziria "a corretora
não ganhou nada nas renovações", que é falso e soa verdadeiro.

**2. Dinheiro é `Decimal`, nunca `float`.** 📊 O controle-ouro de 2025 é
R$ 1.863.830,79 sobre 1.680 parcelas. Soma de `float` acumula resíduo binário
e a paridade com a 081 passa a depender de tolerância; com `Decimal` ela é
exata.

**3. `policy_ref` é OPACO.** Ninguém o parseia — nem aqui, nem em
`calculos.py`, nem em `metricas/`. Ele só serve como chave de join, e a regra
que o mantém honesto é uma só:

> 🔴 **A MESMA função gera as DUAS pontas do join.** Se um lado chamar
> `policy_ref(...)` e o outro usar o identificador cru do provider, o join
> devolve vazio em silêncio — e um relatório com zero linhas parece um período
> sem movimento.

## O que ficou FORA da v1, com contrato escrito (SPEC-094 §6)

```
ClaimSignalFact   📊 /sinistros tem 5.729 registros na Resulta e nenhum leitor.
                  O gatilho da pendência P-094-SINISTROS já foi atingido.
InteractionFact   📊 /atendimentos devolve a lista na chave `tarefas`, e nenhum
                  conjunto de parâmetros medido passou de 15 registros.
CashflowFact      📊 UNAVAILABLE MEDIDO: /fluxo_caixa e /contas_pagar não
                  existem no Gateway. Não é "ainda não olhamos".
PolicyMovementFact  endosso existe como documento, mas sem data de movimento.
QuoteFact         📊 /cotacoes é classe 200 com 30 campos — e devolveu 7
                  registros. Serve para funil atual, não para série.
```
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from app.comercial.evidence_pack import UNAVAILABLE, ref_de_produtor

__all__ = [
    "UNAVAILABLE", "Money", "Provenance",
    "PolicyFact", "ProducerAssignmentFact", "CommissionFact", "RenewalFact",
    "policy_ref", "producer_ref", "interpretar_dinheiro", "somar_dinheiro",
    "NEW", "RENEWAL", "ENDORSEMENT", "UNKNOWN", "KINDS",
    "MOEDA_PADRAO", "PROVIDER_PILOTO",
]

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
MOEDA_PADRAO = "BRL"

#: 🔴 O provider PILOTO. Ele é o valor DEFAULT de um campo de dado — nunca um
#: `if` no motor. Quem escrever `if provider_key == ...` numa métrica está
#: reintroduzindo o acoplamento que esta SPEC existe para tirar (mutação M1).
PROVIDER_PILOTO = "infocap"

#: O tipo do documento, em vocabulário de negócio.
#:
#: 🔴 `ENDORSEMENT` existe para que a contagem de apólices consiga EXCLUÍ-LO.
#: 📊 Sem o filtro `tipo_doc=A` a InfoCap devolve 3.272 documentos dos quais só
#: 1.680 são apólice — contar os outros dobraria a produção do ano
#: (`fonte_infocap.py:39-44`). É a mutação M5.
NEW = "NEW"
RENEWAL = "RENEWAL"
ENDORSEMENT = "ENDORSEMENT"
UNKNOWN = "UNKNOWN"
KINDS = (NEW, RENEWAL, ENDORSEMENT, UNKNOWN)


# --------------------------------------------------------------------------
# Dinheiro
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Money:
    """Um valor monetário. `Decimal`, sempre, e com a moeda ao lado.

    A moeda ao lado não é cerimônia: é o que impede somar comissão com prêmio
    de uma apólice em outra moeda quando a segunda corretora chegar. Somar
    moedas diferentes levanta — em silêncio seria pior.
    """

    amount: Decimal
    currency: str = MOEDA_PADRAO

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    @classmethod
    def zero(cls, currency: str = MOEDA_PADRAO) -> "Money":
        return cls(Decimal("0"), currency)

    def __add__(self, outro: "Money") -> "Money":
        if not isinstance(outro, Money):
            raise TypeError("Money só soma com Money")
        if outro.currency != self.currency:
            raise ValueError(
                f"moedas diferentes não somam: {self.currency} + {outro.currency}")
        return Money(self.amount + outro.amount, self.currency)

    def __sub__(self, outro: "Money") -> "Money":
        if not isinstance(outro, Money):
            raise TypeError("Money só subtrai de Money")
        if outro.currency != self.currency:
            raise ValueError(
                f"moedas diferentes não subtraem: {self.currency} - {outro.currency}")
        return Money(self.amount - outro.amount, self.currency)

    @property
    def como_float(self) -> float:
        """Para quem só sabe ler `float` — a serialização e os gráficos.

        ⚠️ Nunca use isto para SOMAR. Somar em `float` é o que o `Decimal`
        está aqui para evitar; converter no fim é conversão, converter no meio
        é o defeito de volta.
        """
        return float(self.amount)

    def serializar(self) -> Dict[str, Any]:
        return {"amount": str(self.amount), "currency": self.currency}


Dinheiro = Union[Money, str]   # Money | UNAVAILABLE


def interpretar_dinheiro(v: Any, currency: str = MOEDA_PADRAO) -> Optional[Money]:
    """O valor cru vira `Money` — ou **`None`**, quando é ilegível.

    🔴 `None` aqui significa **"não deu para ler"**, e é o ÚNICO lugar do CBIM
    onde `None` é uma resposta legítima. Quem chama — e o único chamador
    autorizado é o adapter, na fronteira — traduz esse `None` em `UNAVAILABLE`
    **mais um warning com o `correlation_id`** (SPEC-094 BLOCO B, ref ②).

    Isto NÃO é o `_num()` de `fonte_infocap.py:514-530`. 📊 Aquele devolve
    `0.0` para `None`, para `""` e para qualquer coisa não conversível — e é
    exatamente o defeito da §1.5. Aqui não existe zero de consolação.

    Aceita o que a InfoCap devolve de fato: número, string ISO (`"1299.09"`) e
    string com vírgula decimal (`"1.299,09"`).
    """
    if v is None:
        return None
    if isinstance(v, Money):
        return v
    if isinstance(v, Decimal):
        return Money(v, currency)
    if isinstance(v, bool):          # `True` não é dinheiro. `bool` é `int`.
        return None
    if isinstance(v, (int, float)):
        try:
            return Money(Decimal(str(v)), currency)
        except (InvalidOperation, ValueError):
            return None
    texto = str(v).strip()
    if not texto:
        return None
    # "1.299,09" → "1299.09". 🔴 A regra é "existe vírgula? então ela é o
    # separador DECIMAL, e o ponto é milhar" — e não a de
    # `fonte_infocap._num:526-528`, que exige `count(".") != 1` e por isso
    # devolve `0.0` justamente para `"1.299,09"`, a forma mais comum de
    # dinheiro escrito em português. 📊 Conferido no gate A: `_num("1.299,09")`
    # → 0.0 · `interpretar_dinheiro("1.299,09")` → Decimal("1299.09").
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Money(Decimal(texto), currency)
    except (InvalidOperation, ValueError):
        return None


def somar_dinheiro(valores: Iterable[Any],
                   currency: str = MOEDA_PADRAO) -> Tuple[Money, int, int]:
    """Soma o que é `Money` e **conta o que não era**. `(total, conhecidos, total_de_itens)`.

    🔴 Devolve as três coisas de propósito. Um total sem o denominador não
    permite dizer *"isto cobre 80,6% do período"* — e uma soma parcial
    apresentada como total é a forma mais cara de mentir com número certo
    (SPEC-081, `Cobertura`).
    """
    total = Money.zero(currency)
    conhecidos = 0
    itens = 0
    for v in valores:
        itens += 1
        if isinstance(v, Money):
            total = total + v
            conhecidos += 1
    return total, conhecidos, itens


# --------------------------------------------------------------------------
# As referências opacas
# --------------------------------------------------------------------------
def policy_ref(company_id: str, provider_key: str, source_ref: str) -> str:
    """`sha256(company_id + provider_key + source_ref)[:16]` — e nada mais.

    Três propriedades, e cada uma paga uma dívida medida:

    ```
    OPACA      o motor de métrica nunca lê `nosnum`; a 081 lia (§1.3)
    POR TENANT o `company_id` no meio impede que duas corretoras com o mesmo
               número de apólice se cruzem — 🔴 e 📊 a Amandus e a Resulta
               apontam para a MESMA conta CorpAPI (F-094-07): sem o
               `company_id`, os dois acervos colidiriam byte a byte
    POR PROVIDER  a mesma apólice lida por dois providers dá refs diferentes,
               e é isso que se quer: são dois fatos, com duas procedências
    ```

    🔴 Estável entre CONEXÕES do mesmo tenant: a corretora que reconecta a
    InfoCap não vê a carteira inteira virar "apólices novas".
    """
    semente = f"{company_id or ''}|{provider_key or ''}|{str(source_ref or '').strip()}"
    return hashlib.sha256(semente.encode("utf-8")).hexdigest()[:16]


def producer_ref(company_id: str, label: str) -> str:
    """A referência opaca do produtor — a MESMA função do `evidence_pack`.

    🔴 Reexportada, não reimplementada (CLAUDE.md §5). Duas funções de hash
    para a mesma coisa divergiriam no primeiro `.strip()` que uma ganhasse e a
    outra não, e o ranking do chat deixaria de casar com o do Artifact sem
    ninguém ver.
    """
    return ref_de_produtor(company_id, label)


# --------------------------------------------------------------------------
# Procedência — a infraestrutura mora AQUI, não dentro do fato
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Provenance:
    """De onde este lote de fatos veio. **Nunca** carrega credencial.

    🔴 `account_fingerprint` é `sha256(login)[:12]` — presença, nunca o valor
    (CLAUDE.md §13.3). Ele existe por um motivo medido: 📊 as conexões
    `connected` da Amandus e da Resulta descriptografam para o MESMO login e
    devolvem carteira idêntica ao centavo (censo §1.11, P1 cross-tenant). Os
    ciphertexts diferem — o IV do Fernet muda a cada escrita — então a tabela
    não denuncia. O fingerprint denuncia.
    """

    connection_id: str
    correlation_id: str
    fetched_at: datetime
    fingerprint: str = ""
    account_fingerprint: str = ""

    def serializar(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "correlation_id": self.correlation_id,
            "fetched_at": (self.fetched_at.isoformat(timespec="seconds")
                           if isinstance(self.fetched_at, (date, datetime))
                           else str(self.fetched_at or "")),
            "fingerprint": self.fingerprint,
            "account_fingerprint": self.account_fingerprint,
        }


# --------------------------------------------------------------------------
# Os fatos
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PolicyFact:
    """Uma apólice, no vocabulário da corretagem.

    `valid_from` e `valid_to` não são detalhe de cadastro: são as DUAS bases
    temporais que existem nesta fonte, e a métrica declara qual usa.
    📊 O censo mediu: `/documentos_bi` filtra `inivig` (1.680/1.680 dentro da
    janela; só 106 têm `fimvig` dentro dela) e `/renovacoes` filtra `fimvig`
    (3.536/3.536). São duas populações quase disjuntas — 📊 interseção de 2,8%
    — e somar as duas como se fossem a mesma é a mutação M6.
    """

    policy_ref: str
    source_ref: str
    insurer: str = ""
    branch: str = ""
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    premium: Dinheiro = UNAVAILABLE
    kind: str = UNKNOWN
    status: str = ""
    provider_key: str = PROVIDER_PILOTO

    @property
    def e_endosso(self) -> bool:
        """📊 A mutação M5 mora aqui: endosso NÃO é apólice na contagem."""
        return self.kind == ENDORSEMENT

    @property
    def e_renovacao(self) -> bool:
        return self.kind == RENEWAL


@dataclass(frozen=True)
class ProducerAssignmentFact:
    """Quem vendeu esta apólice, e com que participação.

    🔴 `producer_label` é a ÚNICA coisa deste módulo que o chat não pode ver.
    Ele existe porque o Artifact do tenant PRECISA escrever o nome — é o
    conteúdo da corretora, dentro da corretora. O que não pode é o nome viajar
    na string do modelo, no log, no teste, na fixture ou no relatório
    (SPEC-094 §2).

    🔴 `order` e `share` vêm do provider e NÃO decidem nada sozinhos.
    📊 O censo mediu, na mesma apólice, `ordem 1 = 4%` e `ordem 2 = 15%`: o
    produtor de ordem 1 **não** é o de maior repasse. Somar só a ordem 1
    subestima o repasse, e é por isso que `repasse.producer_accrued` soma
    TODOS os assignments.
    """

    policy_ref: str
    producer_ref: str
    producer_label: str = ""
    role_source: str = ""
    share: Optional[float] = None
    order: Optional[int] = None


@dataclass(frozen=True)
class CommissionFact:
    """O dinheiro da corretora nesta apólice.

    ```
    broker_commission_accrued  o que ela APROPRIOU na emissão
    producer_repasse           o que sai como repasse ao produtor (APROPRIADO)
    received                   🔴 UNAVAILABLE, e não por preguiça
    ```

    📊 `received` é `UNAVAILABLE` **medido**: `/parcelas`, `/comissao`,
    `/comissoes`, `/titulos` e `/contas_receber` são todos 403-SigV4 — a rota
    não existe no Gateway. A única evidência de recebimento é o array
    `parcelas[]` de `/documento`, que custa **uma chamada por apólice**
    (censo, `financial.commission_received` = PARTIAL).

    🔴 Apropriado **não** é recebido, e o Artifact tem de dizer isso com todas
    as letras. Chamar accrued de "recebida" é a mutação M8.
    """

    policy_ref: str
    broker_commission_accrued: Dinheiro = UNAVAILABLE
    producer_repasse: Dinheiro = UNAVAILABLE
    received: Dinheiro = UNAVAILABLE
    provider_key: str = PROVIDER_PILOTO


@dataclass(frozen=True)
class RenewalFact:
    """Uma apólice a vencer. A base temporal é `POLICY_VALID_TO`, sempre.

    📊 `dias_a_vencer` pode ser negativo (medido: 2.594 negativos em 3.536
    linhas de 2025). A API devolve vencidas dentro da janela; quem calcula
    decide se as quer, e declara.
    """

    policy_ref: str
    valid_to: Optional[date] = None
    producer_ref: str = ""
    status_source: str = ""
    dias_a_vencer: Optional[int] = None
    premium: Dinheiro = UNAVAILABLE
    insurer: str = ""
    branch: str = ""


# --------------------------------------------------------------------------
# O lote — o que o adapter devolve e o registry consome
# --------------------------------------------------------------------------
@dataclass
class FactSet:
    """Os fatos de UMA leitura, com a procedência que os produziu.

    Não é tabela nem cache: é o resultado de uma chamada, em memória, com os
    `warnings` que a tradução gerou. Um lote sem `provenance` não deveria
    existir — é como se saber o número sem saber de onde ele veio.
    """

    company_id: str = ""
    provider_key: str = PROVIDER_PILOTO
    policies: List[PolicyFact] = field(default_factory=list)
    assignments: List[ProducerAssignmentFact] = field(default_factory=list)
    commissions: List[CommissionFact] = field(default_factory=list)
    renewals: List[RenewalFact] = field(default_factory=list)
    provenance: Optional[Provenance] = None
    warnings: List[str] = field(default_factory=list)

    def comissao_por_apolice(self) -> Dict[str, CommissionFact]:
        return {c.policy_ref: c for c in self.commissions}

    def assignments_por_apolice(self) -> Dict[str, List[ProducerAssignmentFact]]:
        saida: Dict[str, List[ProducerAssignmentFact]] = {}
        for a in self.assignments:
            saida.setdefault(a.policy_ref, []).append(a)
        return saida
