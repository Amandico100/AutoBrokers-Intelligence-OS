# -*- coding: utf-8 -*-
"""CBIM — o modelo canônico da corretagem. **Nenhum provider entra aqui.**

SPEC-094 · BLOCO A. Peça **pura**: `dataclasses`, `datetime`, `decimal`,
`hashlib`, `typing` — e `evidence_pack`, que também é puro. Não importa
`fonte_infocap`, não importa `app.providers`, não importa Supabase, não sabe
o que é identificador de apólice de sistema de gestão nenhum.

## Por que ele existe

📊 SPEC-094 §1.3: `calculos.py` — a camada que a 081 declara "pura" — usava
o identificador do provider 6 vezes e o nome do campo de vigência 1 vez, como
nomes de atributo. Eram nomes de campo de UM sistema de gestão dentro do motor
de cálculo. Enquanto fosse assim, trocar de provider seria reescrever a
matemática — e a matemática é a única coisa que não deveria mudar.

O CBIM é o vocabulário que fica quando se tira a InfoCap da frente:

```
PolicyFact              uma apólice, com a vigência e o dinheiro dela
ProducerAssignmentFact  quem vendeu, e com que participação
CommissionFact          o que a corretora apropria, e o que ela repassa
RenewalFact             o que vence, e quando
```

## As três regras que este módulo existe para impor

**1. `UNAVAILABLE` nunca é `0`.** Um prêmio que a fonte não expõe é
indisponível. Zero é uma afirmação sobre o negócio — 📊 e o censo do BLOCO 0
mediu a rota de vencimentos devolvendo comissão nula em **3.536 de 3.536**
linhas de 2025 (`infocap-golden-controls.json`). Somar isso como zero produziria
"a corretora não ganhou nada nas renovações", que é falso e soa verdadeiro.

**2. Dinheiro é `Decimal` NA FRONTEIRA e no `Money`.** 📊 O controle-ouro de
2025 é R$ 1.863.830,79 sobre 1.680 parcelas. Soma de `float` acumula resíduo
binário; com `Decimal` a leitura e o `Money` são exatos.

⚠️ E o alcance disso é limitado, de propósito: as **fórmulas** de `metricas/`
somam em `float`, porque a matemática que elas chamam é a de `calculos.py`, que
a 081 usa em produção e que esta SPEC não reescreveu. 📊 O resíduo medido sobre
o controle-ouro é menor que R$ 0,01, e a serialização arredonda em duas casas.
Ver `somar_dinheiro` e a pendência **P-094-DECIMAL-NAS-FORMULAS**.

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
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from app.comercial.evidence_pack import UNAVAILABLE, ref_de_produtor

__all__ = [
    "UNAVAILABLE", "Money", "Provenance",
    "PolicyFact", "ProducerAssignmentFact", "CommissionFact", "RenewalFact",
    "ClaimFact", "QuoteFact", "CustomerPortfolioFact",
    "MarketFact", "MarketFactSet",
    "policy_ref", "producer_ref", "claim_ref", "customer_ref", "quote_ref",
    "interpretar_dinheiro", "somar_dinheiro",
    "NEW", "RENEWAL", "ENDORSEMENT", "UNKNOWN", "KINDS",
    "ACTIVE", "CANCELLED", "STATUS_DE_APOLICE", "status_de_apolice",
    "POP_POLICIES", "POP_CLAIMS", "POP_QUOTES", "POP_CANCELLATIONS",
    "POP_CUSTOMERS", "POP_ISSUANCE", "POPULACOES",
    "CLAIM_OPEN", "CLAIM_CLOSED", "CLAIM_CLOSED_PAID", "CLAIM_CLOSED_DENIED",
    "CLAIM_UNKNOWN", "CLAIM_STATUS", "CLAIM_ENCERRADOS",
    "CLAIM_OCCURRED_DATE",
    "MOEDA_PADRAO", "PROVIDER_PILOTO", "PROVIDER_DE_MERCADO",
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

#: 🔴 SPEC-094.1 · BLOCO A. O ESTADO da apólice, em vocabulário de negócio.
#:
#: 📊 O censo v2.1 mediu a armadilha que este par existe para fechar:
#: `/renovacoes?cancelado=T` **NÃO** devolve só as canceladas — devolve
#: **3.861 linhas = 3.536 com `cancelado='F'` + 325 com `cancelado='T'`**. O
#: parâmetro INCLUI; quem o lê como recorte publica a carteira inteira como
#: cancelada, e o número **responde** (CLAUDE.md §9.5: o passo que responde
#: errado é o silencioso). O estado sai do CAMPO de cada linha, nunca do
#: parâmetro da chamada.
ACTIVE = "ACTIVE"
CANCELLED = "CANCELLED"
STATUS_DE_APOLICE = (ACTIVE, CANCELLED)

#: 🔴 SPEC-094.1, conserto de 04/09/2026. Os NOMES das populacoes que um lote
#: pode carregar — o vocabulario de `FactSet.populacoes_lidas`.
#:
#: ⚠️ Sao nomes do CBIM, e nao rotas: e por isso que uma formula pode perguntar
#: "esta populacao foi lida?" sem aprender o dialeto de fonte nenhuma (M1).
POP_POLICIES = "policies"
POP_CLAIMS = "claims"
POP_QUOTES = "quotes"
POP_CANCELLATIONS = "cancellations"
POP_CUSTOMERS = "customers"
POP_ISSUANCE = "issuance"
POPULACOES = (POP_POLICIES, POP_CLAIMS, POP_QUOTES, POP_CANCELLATIONS,
              POP_CUSTOMERS, POP_ISSUANCE)


def status_de_apolice(cancelada: bool) -> str:
    """`CANCELLED` ou `ACTIVE` — a ÚNICA função que decide isto.

    🔴 Uma função, e não dois literais espalhados, pelo mesmo motivo de
    `policy_ref`: quem escreve as duas pontas de uma comparação tem de ser o
    mesmo código, ou uma ponta ganha um `.upper()` que a outra não tem e a taxa
    de cancelamento cai para zero em silêncio.
    """
    return CANCELLED if cancelada else ACTIVE


#: O estado de um SINISTRO. `CLAIM_UNKNOWN` é resposta legítima: 📊 o censo
#: mediu `situacao` como texto livre da corretora, e traduzir um rótulo que não
#: se conhece para "encerrado" é afirmar que o caso acabou.
#:
#: 🔴 **SPEC-094.1, conserto de 04/09/2026 — encerrado NÃO é uma coisa só.**
#: 📊 A régua anterior tinha três estados e mandava `negado` e `indeferido`
#: para `CLOSED` junto com `liquidado` e `pago`. A consequência não travava:
#: `claims.indemnity_paid` somava a indenização de um sinistro **NEGADO** — um
#: número que o dono levaria para a seguradora, sobre dinheiro que ninguém
#: pagou (CLAUDE.md §9.5). Encerrar e PAGAR são fatos diferentes, e agora têm
#: rótulos diferentes.
CLAIM_OPEN = "OPEN"
CLAIM_CLOSED_PAID = "CLOSED_PAID"
CLAIM_CLOSED_DENIED = "CLOSED_DENIED"
#: ⚠️ Mantido como o rótulo genérico de "encerrado sem saber se pagou" — é o
#: que sai quando só a DATA de encerramento veio, sem rótulo que diga o
#: desfecho. Ele nunca soma indenização.
CLAIM_CLOSED = "CLOSED"
CLAIM_UNKNOWN = "UNKNOWN"
CLAIM_STATUS = (CLAIM_OPEN, CLAIM_CLOSED_PAID, CLAIM_CLOSED_DENIED,
                CLAIM_CLOSED, CLAIM_UNKNOWN)
#: Os três desfechos que fecham o caso. 🔴 Uma tupla, e não três comparações
#: espalhadas: quem contar "encerrados" em dois lugares diverge no dia em que
#: um quarto desfecho nascer.
CLAIM_ENCERRADOS = (CLAIM_CLOSED_PAID, CLAIM_CLOSED_DENIED, CLAIM_CLOSED)

#: 🔴 A base temporal do SINISTRO, escrita como nome — e a dívida que ela
#: carrega, escrita junto.
#:
#: 📊 O censo v2.1 §A3 mediu: `/sinistros` com `tipo_data=oco` prende `datoco`
#: (**42/42** dentro da janela, com o mínimo no primeiro dia dela). A população
#: de sinistros é recortada pela **data de ocorrência** — que não é o início
#: nem o fim de vigência de apólice nenhuma.
#:
#: ⚠️ E o `MetricDefinition.time_basis` **não** consegue declará-la hoje:
#: `evidence_pack.BASES_TEMPORAIS` tem exatamente DUAS entradas e cinco
#: módulos as desempacotam com `A, B = BASES_TEMPORAIS`. Acrescentar a terceira
#: é uma mudança de contrato em seis arquivos, dois deles de outro escritor
#: nesta mesma SPEC. Então as métricas de sinistro declaram a base que o
#: contrato admite, **e escrevem esta no aviso** — e a dívida tem número:
#: **P-094.1-BASE-DE-SINISTRO**. ⛔ O que não se pode é deixar o envelope
#: afirmar, calado, que o recorte foi por vigência.
CLAIM_OCCURRED_DATE = "CLAIM_OCCURRED_DATE"

#: O provider da estatística pública de mercado (SPEC-094.1 · BLOCO B).
#: 🔴 Ele é de PLATAFORMA e não tem `company_id` — ver `MarketFactSet`.
PROVIDER_DE_MERCADO = "susep_ses"


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


def _finito(quantia: Decimal) -> bool:
    """`NaN` e `Infinity` **não são dinheiro**, e o `Decimal` os aceita calado.

    🔴 Esta é a linha que impede o pior dos dois de entrar. 📊 Achado pelo red
    team em 03/09/2026: a fonte devolvendo a string `"NaN"` produzia
    `Decimal("NaN")` sem levantar nada, e a partir dali:

    ```
    NaN entra na soma          e CONTAMINA o total inteiro, sem uma linha de erro
    a manchete vira "R$ nan"   e parece defeito de sistema, não ausência de dado
    46 `NaN` no bloco citável  e `json.dumps` os escreve como JSON inválido
    ```

    ⚠️ `Decimal.is_nan()` e `is_infinite()`, e não `math.isfinite(float(...))`:
    converter para `float` para conferir é reintroduzir o `float` no caminho do
    dinheiro, que é o que este módulo existe para evitar.

    Quem recebe o `None` faz o que faria com qualquer ilegível: `UNAVAILABLE`
    **mais um warning**. Ausência de dado, e nunca zero.
    """
    return not (quantia.is_nan() or quantia.is_infinite())


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
        return v if _finito(v.amount) else None
    if isinstance(v, Decimal):
        return Money(v, currency) if _finito(v) else None
    if isinstance(v, bool):          # `True` não é dinheiro. `bool` é `int`.
        return None
    if isinstance(v, (int, float)):
        try:
            quantia = Decimal(str(v))
        except (InvalidOperation, ValueError):
            return None
        return Money(quantia, currency) if _finito(quantia) else None
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
        quantia = Decimal(texto)
    except (InvalidOperation, ValueError):
        return None
    # 🔴 `Decimal("NaN")` e `Decimal("Infinity")` CONSTROEM sem erro — é aqui
    # que a recusa precisa acontecer, e não no `except`.
    return Money(quantia, currency) if _finito(quantia) else None


def somar_dinheiro(valores: Iterable[Any],
                   currency: str = MOEDA_PADRAO) -> Tuple[Money, int, int]:
    """Soma o que é `Money` e **conta o que não era**. `(total, conhecidos, total_de_itens)`.

    🔴 Devolve as três coisas de propósito. Um total sem o denominador não
    permite dizer *"isto cobre 80,6% do período"* — e uma soma parcial
    apresentada como total é a forma mais cara de mentir com número certo
    (SPEC-081, `Cobertura`).

    🔴 ONDE O `Decimal` VALE, E ONDE ELE NÃO VALE — e a regra 2 do topo deste
    módulo dizia mais do que o produto entrega. Corrigido em 03/09/2026, pela
    lente do dado (CLAUDE.md §12.1: nome que mente sobre o que guarda é causa,
    não sintoma):

    ```
    Decimal   a fronteira (`interpretar_dinheiro`), o `Money` e ESTA soma
    float     as fórmulas de `metricas/`, que somam a projeção `VisaoDeApolice`
    ```

    O motor de métrica projeta o `Money` em `float` (`registry._float`) e as
    fórmulas somam ali — porque a matemática que elas chamam é a de
    `calculos.py`, que a SPEC-081 usa em produção sobre `float` e que esta SPEC
    **não** reescreveu (CLAUDE.md §5: consolidar, não duplicar ao lado).

    ⚠️ O resíduo disso é medido e pequeno: 📊 sobre as 1.680 apólices do
    controle-ouro de 2025 a soma em `float` difere da soma em `Decimal` em menos
    de R$ 0,01, e a serialização arredonda em duas casas antes de o número
    chegar ao modelo (`evidence_pack.CASAS_DO_NUMERO`). O que **não** se pode
    dizer é que o motor inteiro soma em `Decimal` — não somava, e afirmar que
    somava é o defeito que a §12.1 chama de número sem marca.

    A dívida está escrita: **P-094-DECIMAL-NAS-FORMULAS**.
    """
    from decimal import Decimal as _D

    total = Money.zero(currency)
    conhecidos = 0
    itens = 0
    for v in valores:
        itens += 1
        # 🔴 Por FORMA, e não por `isinstance` — ver `metricas/registry._float`:
        # o mesmo módulo carregado duas vezes dá duas classes `Money`, e
        # `isinstance` viraria dinheiro legítimo em INDISPONÍVEL, em silêncio.
        quantia = getattr(v, "amount", None)
        if quantia is None:
            continue
        total = Money(total.amount + _D(str(quantia)), currency)
        conhecidos += 1
    return total, conhecidos, itens


# --------------------------------------------------------------------------
# As referências opacas
# --------------------------------------------------------------------------
def policy_ref(company_id: str, provider_key: str, source_ref: str) -> str:
    """`sha256(company_id + provider_key + source_ref)[:16]` — e nada mais.

    Três propriedades, e cada uma paga uma dívida medida:

    ```
    OPACA      o motor de métrica nunca lê identificador de provider; a 081 lia
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


def _ref_opaca(dominio: str, company_id: str, provider_key: str,
               source_ref: str) -> str:
    """A MESMA construção de `policy_ref`, com o domínio no meio da semente.

    🔴 O domínio existe para que um sinistro e uma apólice com o mesmo número
    cru na mesma corretora **não** colidam. Sem ele, `claim_ref` e `policy_ref`
    de um sistema que numera as duas coisas na mesma série dariam a MESMA
    string — e um join silenciosamente certo casaria as duas metades erradas.
    """
    semente = "%s|%s|%s|%s" % (dominio, company_id or "", provider_key or "",
                               str(source_ref or "").strip())
    return hashlib.sha256(semente.encode("utf-8")).hexdigest()[:16]


def claim_ref(company_id: str, provider_key: str, source_ref: str) -> str:
    """A referência opaca de um SINISTRO. ⛔ Nunca o número da seguradora.

    🔴 📊 O censo v2.1 §A3 mediu, em `/sinistros`: `segurado` e `responsavel`
    são **nome de pessoa**, `placa` é placa de veículo e `numapo` é número de
    apólice. Nenhum deles atravessa esta fronteira — e `numsin`, o número do
    sinistro na seguradora, atravessa só como SEMENTE deste hash. O que o
    motor de métrica vê é uma string de 16 hex, e é tudo o que ele precisa
    para contar e para juntar.
    """
    return _ref_opaca("claim", company_id, provider_key, source_ref)


def customer_ref(company_id: str, provider_key: str, source_ref: str) -> str:
    """A referência opaca de um CLIENTE. ⛔ Nunca o nome, nunca o CPF.

    📊 `/cliente_ligacoes` devolve `cliente` (nome, PII) e `cliente_codigo`. Só
    o código vira semente; o nome fica na fronteira, como o `producer_label`
    fica — a diferença é que o cross-sell não precisa nem do rótulo.
    """
    return _ref_opaca("customer", company_id, provider_key, source_ref)


def quote_ref(company_id: str, provider_key: str, source_ref: str) -> str:
    """A referência opaca de uma COTAÇÃO / negócio em andamento."""
    return _ref_opaca("quote", company_id, provider_key, source_ref)


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
    📊 O censo mediu, na fonte piloto: a rota de produção filtra por INÍCIO de
    vigência (1.680/1.680 dentro da janela; só 106 terminam dentro dela) e a de
    vencimentos filtra por FIM de vigência (3.536/3.536). São duas populações
    quase disjuntas — 📊 interseção de 2,8% — e somar as duas como se fossem a
    mesma é a mutação M6.
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


@dataclass(frozen=True)
class ClaimFact:
    """Um SINISTRO da carteira. 📊 5.729 registros na fonte piloto, zero leitores.

    O contrato inteiro da SPEC-094.1 · BLOCO A, e cada campo com o número que o
    justifica (censo v2.1 §A3, 42 sinistros em 90 dias, 1,10 s):

    ```
    occurred_at   `datoco`   📊 42/42 dentro da janela — é a base do filtro
    reported_at   `datavi`   📊 42/42 preenchidos
    closed_at     `datenc`   📊 9/42 — só os encerrados. `None` não é "hoje"
    indemnity     `valind`   📊 preenchido; ilegível vira UNAVAILABLE, nunca 0
    deductible    `franquia` 📊 preenchido
    ```

    🔴 `status` é `OPEN | CLOSED | UNKNOWN`, e `UNKNOWN` é resposta legítima: o
    campo `situacao` da fonte é texto livre da corretora. Contar um rótulo
    desconhecido como encerrado seria fechar um caso na planilha e não na vida.

    ⛔ `segurado`, `responsavel` e `placa` **não existem aqui**. Eles são
    descartados na fronteira, no adapter — não filtrados depois. O que não entra
    não vaza.
    """

    policy_ref: str
    claim_ref: str
    status: str = CLAIM_UNKNOWN
    occurred_at: Optional[date] = None
    reported_at: Optional[date] = None
    closed_at: Optional[date] = None
    indemnity: Dinheiro = UNAVAILABLE
    deductible: Dinheiro = UNAVAILABLE
    insurer: str = ""
    branch: str = ""
    provider_key: str = PROVIDER_PILOTO

    @property
    def aberto(self) -> bool:
        return self.status == CLAIM_OPEN


@dataclass(frozen=True)
class QuoteFact:
    """Uma cotação / negócio em andamento — o funil.

    🔴 `lost_reason` nasce `UNAVAILABLE` **por capacidade medida, e não por
    preguiça**: 📊 o censo v2.1 §A4 listou as **30 chaves** que
    `/negocios_andamento` devolve e `motivo_perda` **não está entre elas** — ele
    existe só no CORPO do `POST /negocio` da documentação. Não há fonte de
    LEITURA provada. Enquanto não houver, `quotes.lost_reasons@1` responde
    INDISPONÍVEL com o motivo escrito, e nunca "nenhum motivo registrado".

    ⚠️ E o acervo é o segundo achado: 📊 `/negocios_andamento` devolveu **1**
    negócio em 2025 inteiro; `/em_calculo` e `/negocios_finalizados` devolveram
    **404 = vazio**. A corretora piloto não usa o CRM da fonte. O funil sai
    UNAVAILABLE por ACERVO VAZIO — que também não é zero.
    """

    quote_ref: str
    stage: str = ""
    created_at: Optional[date] = None
    closed_at: Optional[date] = None
    expected_premium: Dinheiro = UNAVAILABLE
    branch: str = ""
    lost_reason: str = UNAVAILABLE
    provider_key: str = PROVIDER_PILOTO


@dataclass(frozen=True)
class CustomerPortfolioFact:
    """O que UM cliente tem na corretora — a matéria-prima do cross-sell.

    🔴 `customer_ref` é hash (M16). `policy_refs` e `branches` são o que a
    pergunta *"quantos clientes só têm um produto?"* precisa, e nada além:
    contar produtos por cliente não exige saber quem é o cliente.

    ⚠️ `branches` é o conjunto de ramos DISTINTOS, e a distinção importa: um
    cliente com três apólices do mesmo ramo tem **um** produto, não três. Somar
    apólices em vez de ramos inflaria o cross-sell da corretora inteira.
    """

    customer_ref: str
    policy_refs: Tuple[str, ...] = ()
    branches: Tuple[str, ...] = ()
    provider_key: str = PROVIDER_PILOTO

    @property
    def produtos(self) -> int:
        return len({str(b or "").strip().upper() for b in self.branches
                    if str(b or "").strip()})


# --------------------------------------------------------------------------
# O MERCADO — a estatística pública, que é de TODAS as corretoras
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class MarketFact:
    """Uma célula da estatística oficial: entidade × competência × ramo.

    📊 SUSEP SES, `Ses_seguros.csv`, 1.801.731 linhas, 199501→202606
    (`docs/canon/providers/susep/SES-CENSO.md`). Três convenções medidas que
    quebram quem copiar exemplo de internet, e que o ingestor trata:
    **latin-1**, **decimal por vírgula** e **códigos com padding à direita** nas
    tabelas de domínio.

    ```
    damesano   `AAAAMM` — é COMPETÊNCIA (mês contábil), não data
    coenti     a entidade. 🔴 o mapa nome->coenti é VERSIONADO e revisado por
               gente; nome não é chave (📊 o token "SEGUROS" deu 284 candidatos)
    coramo     o ramo SUSEP. O GRUPO são os DOIS PRIMEIROS dígitos —
               📊 `coramo[1:3]` devolveu ZERO ramos de auto, em silêncio
    ```

    🔴 `sinistro_ocorrido` PODE SER NEGATIVO (estorno de provisão) — 📊 Porto,
    ramo 0520, 202605: −53.790,44. Truncar em zero inventa um sinistro que não
    houve, então o negativo é preservado e `estorno` o sinaliza.

    ⛔ E a sinistralidade é `sinistro_ocorrido / premio_ganho`: as duas pontas
    do MESMO regime de competência. Misturar com `premio_direto` (emissão) ou
    `sinistro_direto` (pago) devolve um número plausível e errado.
    """

    coenti: str
    damesano: str
    coramo: str
    premio_ganho: float = 0.0
    sinistro_ocorrido: float = 0.0
    estorno: bool = False

    @property
    def grupo_de_ramo(self) -> str:
        """📊 Os DOIS primeiros dígitos. `05` = Automóvel."""
        return str(self.coramo or "").strip()[:2]

    @property
    def sinistralidade(self) -> Optional[float]:
        if not self.premio_ganho:
            return None
        return self.sinistro_ocorrido / self.premio_ganho


@dataclass
class MarketFactSet:
    """O feixe de PLATAFORMA. ⛔ **Não tem DONO, e é de propósito.**

    ⚠️ Nenhum campo de tenant entra nesta classe — nem "só para filtrar". O
    guarda lê o texto CRU aqui: citar o nome do campo, ainda que para negá-lo,
    é indistinguível de tê-lo (CLAUDE.md §9.4).

    🔴 A estatística pública é a MESMA para todas as corretoras. Se ela entrasse
    no `FactSet` do tenant, cada casa passaria a ter a sua cópia do mercado — e
    a pergunta seguinte seria por que elas divergem. Um dado sem dono é um dado
    que ninguém consegue duplicar por engano (CLAUDE.md §7, pelo avesso).

    ⚠️ `competencia_final` vai ao pacote porque a DEFASAGEM é da fonte e tem de
    aparecer no ponteiro: 📊 a base fecha em **202606**, e quem lê em setembro
    está comparando com junho. Um cruzamento que esconde a defasagem responde
    certo sobre o mês errado.
    """

    provider_key: str = PROVIDER_DE_MERCADO
    facts: List[MarketFact] = field(default_factory=list)
    competencia_final: str = ""
    fonte: str = ""
    fingerprint: str = ""
    warnings: List[str] = field(default_factory=list)
    #: 🔴 O mapa `seguradora -> coenti` VIAJA COM O FEIXE, e a fórmula nunca vai
    #: buscá-lo. Não é conveniência: é o que impede `metricas/` de importar o
    #: conector — o acoplamento que a mutação M1 existe para pegar. Quem monta o
    #: feixe é quem sabe de onde o mapa veio e como ele foi revisado.
    mapa: Dict[str, str] = field(default_factory=dict)
    #: A função de casamento de nome, quando ela existe. ⚠️ Ela mora no
    #: conector porque o CRITÉRIO é uma medição, e critério medido não se
    #: reescreve em dois lugares.
    resolver: Optional[Any] = None

    def coenti_de(self, nome: Any) -> str:
        """A entidade desta seguradora — ou `"UNKNOWN"`. ⛔ Nunca um palpite.

        🔴 `UNKNOWN` é uma STRING, e não `None`: `None` some numa comparação e
        vira "não filtrou nada"; a palavra atravessa o pacote e chega escrita ao
        leitor. Um cruzamento com entidade desconhecida sai INDISPONÍVEL, nunca
        zero — *"a sua seguradora sinistra 0% acima do mercado"* é uma frase que
        o dono usaria numa negociação de reajuste, e ela seria falsa.
        """
        if callable(self.resolver):
            try:
                return str(self.resolver(nome) or "UNKNOWN")
            except Exception:  # noqa: BLE001
                return "UNKNOWN"
        chave = str(nome or "").strip().lower().replace(" ", "_")
        return str(self.mapa.get(chave) or "UNKNOWN")

    def por_entidade(self, coenti: str) -> List[MarketFact]:
        alvo = str(coenti or "").strip()
        return [f for f in self.facts if str(f.coenti or "").strip() == alvo]


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
    #: 🔴 SPEC-094.1 · BLOCO A. Três populações novas, cada uma com a sua
    #: rota e a sua base temporal. Elas NÃO entram em `policies`: um sinistro
    #: não é uma apólice, e uma cotação não é um documento emitido. Misturá-las
    #: faria a contagem de apólices crescer sozinha.
    claims: List[ClaimFact] = field(default_factory=list)
    quotes: List[QuoteFact] = field(default_factory=list)
    customers: List[CustomerPortfolioFact] = field(default_factory=list)
    #: 🔴 SPEC-094.1, conserto de 04/09/2026 — a POPULAÇÃO DO CANCELAMENTO, e
    #: ela é uma lista PRÓPRIA de propósito.
    #:
    #: 📊 O defeito que ela conserta: a taxa de cancelamento lia `policies`, que
    #: é o lote da produção — lido com o parâmetro `cancelado="F"`, isto é, SEM
    #: nenhuma apólice cancelada dentro. A taxa publicada era **0,0%**, com
    #: confiança alta, sobre uma carteira em que 325 de 3.861 documentos estavam
    #: cancelados (**8,42%**). O número respondia; não travava.
    #:
    #: ⚠️ E ela não pode ser fundida em `policies`: as duas populações têm BASE
    #: TEMPORAL diferente — a produção entra por `POLICY_VALID_FROM` e esta por
    #: `POLICY_VALID_TO` (a rota filtra pelo FIM de vigência). Somá-las faria a
    #: contagem de apólices do período crescer sozinha, e por cima misturaria
    #: dois recortes de tempo na mesma conta.
    cancellations: List[PolicyFact] = field(default_factory=list)
    #: 🔴 SPEC-094.1, conserto de 04/09/2026 — QUAIS POPULACOES FORAM LIDAS.
    #:
    #: 📊 O defeito que ela conserta: uma lista vazia nao consegue dizer se a
    #: fonte foi perguntada. "Nao perguntei" e "perguntei e veio vazio" sao a
    #: diferenca entre INDISPONIVEL e um zero com confianca alta — e sem esta
    #: marca o funil escrevia *"o acervo esta vazio no periodo"* sobre uma rota
    #: que ninguem tinha chamado.
    #:
    #: ⚠️ Os nomes sao os do CBIM (`claims`, `quotes`, `cancellations`,
    #: `customers`, `issuance`), e nunca os da fonte: quem preenche e o adapter,
    #: quem le e a formula, e nenhum dos dois pode aprender o dialeto do outro
    #: (M1). `fingerprints` continua guardando a ROTA, que e outra pergunta.
    populacoes_lidas: Set[str] = field(default_factory=set)
    provenance: Optional[Provenance] = None
    warnings: List[str] = field(default_factory=list)
    #: `rota -> sha256 das chaves ordenadas`, na forma EXATA do censo
    #: (`infocap-schema-fingerprints.json`). 🔴 E o `__combinado__` que a
    #: `Provenance` carrega. E o que permite ao BLOCO C perguntar "o schema
    #: mudou?" a CADA leitura, em vez de esperar um monitor agendado.
    fingerprints: Dict[str, str] = field(default_factory=dict)

    def comissao_por_apolice(self) -> Dict[str, CommissionFact]:
        return {c.policy_ref: c for c in self.commissions}

    def assignments_por_apolice(self) -> Dict[str, List[ProducerAssignmentFact]]:
        saida: Dict[str, List[ProducerAssignmentFact]] = {}
        for a in self.assignments:
            saida.setdefault(a.policy_ref, []).append(a)
        return saida

    def sinistros_por_apolice(self) -> Dict[str, List[ClaimFact]]:
        saida: Dict[str, List[ClaimFact]] = {}
        for c in self.claims:
            saida.setdefault(c.policy_ref, []).append(c)
        return saida
