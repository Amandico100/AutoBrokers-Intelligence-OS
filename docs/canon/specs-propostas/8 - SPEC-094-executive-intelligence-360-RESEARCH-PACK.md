# SPEC-094 — RESEARCH PACK
## Executive Intelligence 360 · Provider-Neutral Brokerage Analytics

**Data:** 25/08/2026  
**Repo:** `Amandico100/AutoBrokers-Intelligence-OS`  
**Baseline confirmado:** `b8ef4e5103efe474071b640376ac0619a0faf8ee`  
**SPEC associada:** `SPEC-094-executive-intelligence-360-provider-agnostic.md`

---

# 1. VEREDITO DA PESQUISA

A arquitetura mais forte para a inteligência executiva do AutoBrokers é:

```text
PROVIDER-SPECIFIC SOURCE
        ↓
ANTI-CORRUPTION / ADAPTER LAYER
        ↓
CANONICAL BROKERAGE INTELLIGENCE MODEL
        ↓
SEMANTIC METRIC REGISTRY
        ↓
DETERMINISTIC METRIC ENGINE
        ↓
EXECUTIVE EVIDENCE PACK
        ↓
CHAT / ARTIFACT / AUXILIARY / ENGINE
```

Nota:

```text
InfoCap-only analytics ............ 62/100
Provider-neutral analytics ........ 100/100
Full provider census first ........ 100/100
Fake Quiver/Segfy adapter now ..... 15/100
Reference provider for tests ...... 98/100
```

---

# 2. A DESCOBERTA MAIS IMPORTANTE NO REPO

Já existe um precedente canônico muito forte:

`backend/app/providers/policy_data_provider.py`

O próprio docstring determina:

> “A InfoCap é o provider piloto, NUNCA a arquitetura. Quiver/Segfy futuros entram por esta mesma porta sem tocar a inteligência.”

Isso hoje vale para lookup/detail de apólice individual.

A SPEC-094 estende a mesma filosofia para:

```text
carteira
produção
comissão
repasse
renovação
cotações
analytics
```

Não substituir `PolicyDataProvider`.

Criar um port agregado complementar.

---

# 3. O QUE A SPEC-081 PROVOU

A SPEC-081 produziu valor real:

```text
chat
→ query period
→ InfoCap
→ pure deterministic calculations
→ Artifact
```

Ela também estabeleceu a regra correta:

> **O modelo escolhe O QUE. O código FAZ.**

Essa regra deve ser preservada.

---

# 4. O QUE A SPEC-081 TAMBÉM PROVOU SOBRE RISCO

A SPEC-081 precisou de uma errata extensa porque a investigação inicial assumiu sem medir:

```text
indireto
nome_produtor
val_c em /renovacoes
```

Os três estavam errados para o dataset usado.

Além disso:

```text
/documentos_bi → INIVIG
/renovacoes → FIMVIG
```

e a interseção de “2025 vs 2025” medida foi de apenas 2,8%.

Lição:

> **mesma palavra de negócio não significa mesma população.**

---

# 5. CALIBRAÇÃO REAL DA SPEC-081

Medido em 18/08/2026:

```text
2025
tipo_doc=A
data=INIVIG

policies .................... 1,680
new .........................   717
renewal .....................   963
broker commission total ..... R$ 1,863,831
policies with producer ...... 80.6%
commission attributed ....... 86.2%
distinct producers .......... ~82
```

Esses números são regression controls úteis para 094.

---

# 6. POR QUE O LIVE TEST EXISTE

`backend/tests/test_a_fonte_comercial_bate_com_a_infocap.py` toca a rede deliberadamente.

O comentário é conceitualmente importante:

> uma fixture escrita a partir da mesma interpretação errada poderia ficar verde contra a API imaginária.

Portanto:

```text
unit fixtures
+
live golden controls
```

são necessários.

---

# 7. `fonte_infocap.py` — ACHADOS RELEVANTES

O módulo documenta:

- `/documentos_bi` para produção/comissão;
- `tipo_doc=A`;
- `data=INIVIG`;
- `/renovacoes` para producer mapping / expiry;
- `ordem==1`;
- large ranges 500/502;
- annual chunking;
- partial producer coverage;
- retry;
- cache;
- 404 as empty;
- provider instability.

Também registra a correção de uma crença antiga sobre 403/SigV4:

ao menos nesse caso, 403 indicava rota inexistente, não falta de permissão.

Isso exige auditoria sistemática.

---

# 8. CONTRADIÇÃO CANÔNICA INFOCAP

`docs/canon/INFOCAP-CORPAPI-MAPA.md` mais antigo registra determinadas rotas como 403/permission denied.

`fonte_infocap.py` posterior diz que uma classe de 403/SigV4 é route missing.

Possibilidades:

1. documentos falam de padrões diferentes de 403;
2. provider behavior mudou;
3. uma conclusão antiga estava errada;
4. ambas.

A única solução correta:

# **Censo v2 medido.**

---

# 9. POR QUE AUDITAR “TUDO” E NÃO SÓ O NECESSÁRIO

Se perguntarmos:

```text
“qual endpoint preciso para o Pulso 360?”
```

vamos construir o produto com a visão que já temos.

Se perguntarmos:

```text
“que dados a CorpAPI realmente nos dá?”
```

podemos descobrir capacidades que ainda não imaginamos.

Exemplos possíveis, não assumidos:

- quotes;
- interactions;
- commission settlement;
- producer payouts;
- cancellation;
- receivables;
- claims;
- customer portfolio gaps.

A auditoria descobre; a SPEC não inventa.

---

# 10. DELIVERABLE — INFOCAP API CENSUS

O Censo precisa ser machine-usable, não só texto.

Proposta:

```text
INFOCAP-CORPAPI-CENSUS-v2.md
infocap-capability-manifest.json
infocap-field-dictionary.json
infocap-golden-controls.json
infocap-schema-fingerprints.json
```

---

# 11. CAMPO POR CAMPO

Para cada field observado:

```text
name
type
nullable
redacted sample
meaning
meaning confidence
grain
fact/dimension
sensitivity
relationship key?
canonical mapping?
unused reason?
```

Isso impede que o futuro executor descubra “val_c” de novo do zero.

---

# 12. ENDPOINT POR ENDPOINT

Para cada dataset:

```text
method/path
params
filters
date basis
pagination
range limits
latency
concurrency
envelope
schema
identity
money
status
error semantics
UI equivalent
golden controls
canonical mappings
```

---

# 13. GOLDEN CONTROLS

Provider integration não pode depender apenas de schema.

Um field pode continuar existindo e mudar comportamento.

Controles de negócio ajudam a detectar semantic drift.

Exemplos:

```text
closed period policy count
closed period premium
closed period commission
known producer coverage
known top producer
known renewal count
```

---

# 14. INFOCAP CURRENT COUPLING

Hoje:

```text
RaioXComercialTool
→ FonteInfocap
→ InfoCap dataclasses
→ calculos.py
```

Isso não é “errado” historicamente.

Era uma otimização de entrega da 081.

Agora virou a dívida exata que 094 deve remover.

---

# 15. GOOD NEWS: `calculos.py` IS PURE

A maior parte da matemática da 081 já é function-pure.

Logo, a refatoração não precisa jogar tudo fora.

Boa estratégia:

```text
current pure algorithms
→ canonical facts
→ metric registry
```

---

# 16. WHY `Apolice` IS NOT YET A UNIVERSAL MODEL

Current `Apolice` is useful but includes provider-shaped semantics:

```text
nosnum
inivig
fimvig
val-derived meanings
```

A universal analytical model must expose business names and provenance.

---

# 17. MULTI-PROVIDER PATTERN IN CURRENT REPO

`PolicyDataProvider` already uses:

```text
provider_key
registry
generic policy locator
concrete provider adapter
```

This validates the direction.

The aggregate analytics provider should look architecturally familiar.

---

# 18. QUIVER — PUBLIC DOMAIN CAPABILITIES

Current public Quiver material shows the platform deals with the same fundamental brokerage concepts:

- policy control;
- renewal automation;
- commission management;
- producer payout;
- receivables/payables;
- cash flow;
- profitability by product/seller;
- business intelligence;
- performance by insurer/product/channel/seller/period;
- policy/proposal/commission imports.

This is enough to validate a common domain model.

It is NOT enough to build a Quiver API adapter.

---

# 19. QUIVER — BUSINESS INTELLIGENCE

Quiver publicly describes a 360 management/BI view including:

- ticket;
- cancellation;
- performance;
- renewal analysis;
- product/channel/seller/region/period dimensions;
- cross-area analysis.

This supports the idea that Executive Intelligence should not be InfoCap-specific.

---

# 20. QUIVER — FINANCE

Quiver public materials distinguish:

- commission management;
- producer payouts;
- accounts payable;
- accounts receivable;
- cash flow;
- financial projections.

This reinforces a key CBIM decision:

```text
commission accrued
≠
cash received
≠
producer payout
```

---

# 21. SEGFY — PUBLIC REPORT CATALOG

Segfy’s current help center lists report families:

## Production

- physical/juridical person filters;
- cancelled/refused exclusions;
- received/not received installments;
- producer repasse;
- producer grouping;
- branch;
- company;
- insured.

## Producer commission payment

- paid;
- payable;
- producer + branch;
- reversal;
- payment forecast.

## Brokerage commission

- received with tax;
- received;
- not received;
- producer repasse;
- due date.

## Renewals

- producer;
- company;
- item data;
- coverage.

## Portfolio mix

- totalized/detail;
- type/status;
- cross-sell use.

This is powerful evidence for domain overlap.

---

# 22. SEGFY — MANAGEMENT PRODUCT

Segfy publicly lists:

- automatic proposal/policy search;
- tasks;
- receivables;
- cash flow;
- insured installments;
- invoices;
- statements;
- overdue installments;
- production;
- mix;
- renewals;
- financial analysis;
- commissions;
- producer commission payments;
- quotations.

Again:

same brokerage domain, different provider semantics.

---

# 23. DO NOT REVERSE-ENGINEER API FROM HELP CENTER

The help pages tell us:

```text
the business capability exists
```

They do not tell us:

```text
API path
field names
grain
permission
date semantics
```

Therefore no fake adapter.

---

# 24. PROVIDER ADMISSION IS A PROTOCOL

Future provider onboarding should be:

```text
ACCESS
↓
CENSUS
↓
FIELD DICTIONARY
↓
CANONICAL MAP
↓
GOLDEN CONTROLS
↓
ADAPTER
↓
METRIC PARITY
↓
CANARY
↓
ACTIVE
```

This becomes one of SPEC-101’s core protocols later.

---

# 25. ANTI-CORRUPTION LAYER — MICROSOFT

Microsoft’s current architecture guidance describes an Anti-Corruption Layer as a facade/adapter between systems that do not share semantics.

The layer translates communication so external systems do not constrain the application’s internal design.

That is exactly the AutoBrokers problem:

```text
InfoCap semantics
Quiver semantics
Segfy semantics
```

must not become AutoBrokers semantics.

Reference:
https://learn.microsoft.com/azure/architecture/patterns/anti-corruption-layer

---

# 26. ACL — IMPORTANT MICROSOFT WARNING

The ACL should focus on translation.

Do not put arbitrary business orchestration inside it.

Therefore:

```text
Adapter
= translate provider → CBIM

Metric Engine
= business math
```

This separation is deliberate.

---

# 27. AWS PRESCRIPTIVE GUIDANCE

AWS also describes ACL as a mediation layer translating domain-model semantics between systems, especially when external/legacy model differs.

Reference:
https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/acl.html

Same lesson:

protect core domain.

---

# 28. SEMANTIC LAYER PATTERN — DBT

dbt describes its Semantic Layer as allowing teams to define metrics on existing models and avoid duplicated metric logic, while handling joins centrally.

AutoBrokers does not need to install dbt for this.

The useful principle:

```text
metric definition lives once
```

Reference:
https://docs.getdbt.com/

---

# 29. WHY A METRIC REGISTRY

Without registry:

```text
chat formula
artifact formula
briefing formula
auxiliary formula
dashboard formula
```

eventually diverge.

With registry:

```text
metric_id
→ one semantic definition
→ many consumers
```

---

# 30. METRIC SEMANTIC VERSIONING

A formula can change because:

- better source;
- corrected interpretation;
- changed business definition.

So metric version matters.

Example:

```text
commission.broker_accrued@1
```

An Artifact can later explain which definition generated it.

---

# 31. PROVIDER VERSION VS METRIC VERSION

Separate:

```text
provider adapter/schema version
```

from:

```text
metric semantic version
```

Provider schema can change without metric meaning changing.

Metric meaning can change without provider changing.

---

# 32. TIME BASIS IS PART OF SEMANTICS

The SPEC-081 incident makes this non-negotiable.

A metric is incomplete if it says only:

```text
commission 2025
```

Need:

```text
commission
period
time basis
```

---

# 33. GRAIN IS PART OF SEMANTICS

“Production” can mean:

- policies;
- proposals;
- movements;
- endorsements;
- issued documents.

Count without grain is dangerous.

---

# 34. MONEY IS NOT ONE FIELD

Canonical financial ontology should distinguish at minimum:

```text
premium
broker commission accrued
broker commission received
commission reversal
commission tax
producer payout accrued
producer payout paid
cashflow event
```

Provider mapping can be partial.

---

# 35. `UNKNOWN` / `UNAVAILABLE` ARE FEATURES

A trustworthy executive system must say:

```text
not available
not proven
partial
unknown
```

instead of forcing every card to contain a number.

---

# 36. WHY “ZERO” IS DANGEROUS

These are radically different:

```text
commission_received = R$0
```

and:

```text
provider does not expose commission_received
```

Any engine that conflates them can make catastrophic executive claims.

---

# 37. PRODUCER IDENTITY IS A DOMAIN PROBLEM

Current InfoCap producer labels include terms like:

- EXECUTIVO;
- FECHADOR;
- INDICADOR;
- company/channel-like names.

Therefore a “ranking de funcionários” can be wrong even when arithmetic is perfect.

The identity map is not cosmetic.

---

# 38. PRODUCER IDENTITY — SOURCE VS CANONICAL ROLE

Need:

```text
source role/name
```

and:

```text
canonical actor_type
```

separately.

Mapping may be tenant-specific.

---

# 39. CONTRIBUTION AFTER REPASSE

Formula:

```text
broker commission accrued
-
producer payout accrued
```

is useful.

But it is not:

```text
profit
```

because missing:

- tax;
- payroll;
- OPEX;
- acquisition cost;
- settlement;
- overhead;
- other expenses.

Therefore UI term stays:

**Contribuição pós-repasse.**

---

# 40. CONCENTRATION

Simple share metrics already create executive value.

HHI can be computed internally if useful, but user-facing explanation should stay plain-language.

---

# 41. MOMENTUM

Ranking answers:

```text
who is largest?
```

Momentum answers:

```text
who is changing?
```

Executive intelligence needs both.

---

# 42. PROJECTION

A deterministic run-rate is preferable initially because:

- reproducible;
- cheap;
- explainable;
- easy to backtest.

A sophisticated ML forecast is unjustified without evaluation history.

---

# 43. DATA CONFIDENCE IS A PRODUCT FEATURE

One of the strongest lessons from 081:

partial producer coverage must be printed.

SPEC-094 generalizes that to every metric.

---

# 44. EXECUTIVE EVIDENCE PACK

This avoids the classic failure:

```text
LLM sees raw data
→ tells a compelling story
→ no reproducible calculation
```

Instead:

```text
deterministic metrics/findings
→ evidence pack
→ narrator
```

---

# 45. SAME PACK FOR CHAT AND ARTIFACT

Critical.

Without this:

chat can be calculated at T1, Artifact at T2.

Portfolio changes in between.

User sees two different truths.

Use one evidence snapshot per delivery.

---

# 46. PROVIDER SCHEMA FINGERPRINT

Useful because external APIs are not controlled by us.

Fingerprint can detect:

- field added;
- removed;
- type changed;
- nested envelope changed.

But semantic controls are still required.

---

# 47. SEMANTIC DRIFT

Schema may remain identical while behavior changes.

Golden controls + anomaly monitoring provide a second lens.

---

# 48. STRANGLER CUTOVER

Do not replace SPEC-081 in one jump.

Run:

```text
legacy result
vs
new canonical result
```

until parity.

Then switch wrappers.

This keeps presentation-proven functionality safe.

---

# 49. REFERENCE PROVIDER

A test-only provider returning CBIM directly is especially valuable.

Why?

Because we do not have Quiver/Segfy access yet, but we need to prove:

```text
Executive Intelligence ≠ InfoCap code
```

Reference provider tests architecture without pretending to know external schemas.

---

# 50. THE MOST IMPORTANT FUTURE TEST

When real Quiver support arrives:

> **How many files outside `providers/quiver...` and mapping/config must change?**

Ideal:

very few.

Metric formulas:

zero changes.

---

# 51. PROVIDER PARITY

A semantic conformance corpus can contain canonical scenarios:

```text
Scenario A:
10 policies
premium=100k
commission accrued=15k
repasse accrued=3k

expected:
contribution=12k
```

Every provider adapter must reproduce canonical facts that generate the same expected metrics.

---

# 52. PROVIDER-SPECIFIC CAPABILITIES

Providers may expose unique data.

Do not force lowest common denominator.

Architecture:

```text
common canonical core
+
optional capabilities
```

If Quiver someday exposes high-quality cashflow:

activate cashflow metrics.

InfoCap can still say unavailable.

---

# 53. COMMON CORE ≠ SAME FEATURE SET

Important distinction.

We need:

```text
same formula for same fact
```

not:

```text
all providers must expose everything
```

---

# 54. CAPABILITY MANIFEST AS UX INPUT

If a brokerage connects Provider X:

UI can explain:

```text
Production ........ ready
Renewals .......... ready
Commission accrued  ready
Commission received unavailable
Cashflow ........... unavailable
```

This is more trustworthy than broken cards.

---

# 55. CENSUS AS SALES/ONBOARDING ASSET

Once provider capabilities are known, onboarding can tell the brokerage exactly:

```text
what AutoBrokers can see
what requires extra permission
what this management system cannot supply
```

This later strengthens SPEC-101.

---

# 56. PRIVACY

Aggregated executive analytics should not unnecessarily send customer-level PII to LLMs.

Provider adapters can handle raw data; Evidence Pack should aggregate/minimize.

---

# 57. TENANCY

Caches and snapshots need company and connection identity.

The current `FonteInfocap` code already calls out cross-tenant cache risk and includes brokerage label in the key.

The canonical layer should make this systematic.

---

# 58. NO RAW-WAREHOUSE BY DEFAULT

A universal semantic contract does not require copying every provider’s database.

Start read-through/snapshot/aggregate.

Add persistence when required by:

- performance;
- history;
- replay;
- unavailable historical source.

---

# 59. INFOCAP CENSUS CAN DISCOVER NEW SPEC VALUE

Possible examples:

- pipeline;
- financial settlement;
- customer interactions;
- cancellations.

These should become backlog candidates only after proof.

This protects the roadmap from speculation.

---

# 60. REJECTED — BUILD AGAINST INFOCAP THEN “ABSTRACT” LATER

The common failure:

```text
first provider implementation
becomes accidental domain model
```

We are already at the exact moment to prevent that.

---

# 61. REJECTED — PROVIDER-SPECIFIC REPORTS

Would produce:

```text
InfoCap 360
Quiver 360
Segfy 360
```

and three separate bugs.

---

# 62. REJECTED — LLM NORMALIZES RAW RECORDS

LLM can help during investigation, but runtime financial normalization must be deterministic and tested.

---

# 63. REJECTED — PUBLIC QUIVER/SEGFY SCRAPING AS INTEGRATION

The user explicitly wants future real integrations.

Public pages are not contract-grade source for customer financial analytics.

---

# 64. REJECTED — FULL ACCOUNTING LANGUAGE

Do not say:

```text
lucro
caixa recebido
rentabilidade líquida
```

unless the necessary underlying financial evidence is available.

---

# 65. RESEARCH-BASED SPEC-095 RECOMMENDATION

After Executive Intelligence, the next highest-leverage surface is:

# **SPEC-095 — Artifact & Delivery Hub Completion**

Why:

Executive 360 will create high-value outputs.

If `Entregas` remains weak, the best report becomes hard to:

- find;
- reopen;
- compare;
- share;
- trust;
- deliver.

Therefore 095 should finish the “last mile”.

---

# 66. 095 SHOULD CLOSE SPEC-057 DEBT

Audit:

- tenant artifact listing;
- read/view;
- versions;
- statuses;
- channels;
- share/download;
- delivery status;
- evidence/source display;
- access control;
- navigation/search/filter;
- relation to Work Runs;
- relation to chat.

---

# 67. 095 BIG IDEA

Today:

```text
artifact exists somewhere
```

Future:

```text
everything AutoBrokers delivered
lives in one reliable place
```

---

# 68. FINAL RESEARCH CONCLUSION

The user’s two requested constraints are not edge cases.

They are the architectural center of the SPEC:

1. **InfoCap must be exhaustively understood instead of selectively guessed.**
2. **InfoCap must never become the mental model of the Executive Intelligence Engine.**

The correct abstraction is not:

```text
API abstraction
```

only.

It is:

# **business semantic abstraction.**

---

# 69. SOURCE INDEX — REPO

- `docs/canon/specs/SPEC-081-o-raio-x-comercial-e-o-radar-por-vendedor-no-chat.md`
- `backend/app/comercial/fonte_infocap.py`
- `backend/app/comercial/calculos.py`
- `backend/app/agents/tools/relatorios_comerciais.py`
- `backend/tests/test_a_fonte_comercial_bate_com_a_infocap.py`
- `backend/app/providers/policy_data_provider.py`
- `docs/canon/INFOCAP-CORPAPI-MAPA.md`
- `docs/canon/specs/SPEC-065-carteira-e-dinheiro-visivel.md`

---

# 70. SOURCE INDEX — EXTERNAL

## Quiver

https://solucoesparacorretoras.quiver.net.br/relatorios-financeiros-para-corretoras/

https://solucoesparacorretoras.quiver.net.br/solucao-para-gestao-de-corretoras/

https://solucoesparacorretoras.quiver.net.br/business-intelligence-analise/

https://www.quiver.net.br/solucoes-em-multicalculo/

## Segfy

https://ajuda.segfy.com/knowledge/relat%C3%B3rios

https://www.segfy.com/gestao/

https://ajuda.segfy.com/knowledge/relat%C3%B3rios-como-utilizar-o-relat%C3%B3rio-de-or%C3%A7amentos

## Architecture

https://learn.microsoft.com/azure/architecture/patterns/anti-corruption-layer

https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/acl.html

https://docs.getdbt.com/

---

# 71. FINAL RULE

> **A provider adapter translates the system. The CBIM describes the brokerage. The Metric Registry defines the math. Executive Intelligence explains what matters.**

No provider gets to redefine the brokerage.
