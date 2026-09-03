# SPEC-094 — EXECUTIVE INTELLIGENCE 360
## O Pulso 360 da Corretora nasce de uma camada canônica que entende InfoCap hoje — e Quiver, Segfy e qualquer sistema amanhã

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento/refutação pelo Protocolo AutoBrokers AAA v9; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline de `main` confirmado na redação:** `b8ef4e5103efe474071b640376ac0619a0faf8ee`  
**Branch sugerida:** `feat/spec094-executive-intelligence-360`  
**Origem funcional:** evolução direta da SPEC-081; NÃO é um novo Report Engine  
**Autoridades superiores:** SPEC-052, SPEC-053, SPEC-055, SPEC-056, SPEC-057, SPEC-060, SPEC-081, `PolicyDataProvider` da SPEC-016, Candidate SPEC-090, Candidate SPEC-091 e Protocolo AutoBrokers AAA v9  
**Prepara diretamente:** SPEC-095 Artifact & Delivery Hub Completion; SPEC-098 Scope/Company Soul; SPEC-101 Connector & Management-System Adapter Factory; SPEC-108 MetaHarness; SPEC-109 AutoBrokers Engine  
**Research Pack:** `SPEC-094-executive-intelligence-360-RESEARCH-PACK.md`

---

# LEGENDA DE VERDADE

- 🔒 **frozen** — decisão de produto/arquitetura que o executor não pode alterar sem voltar ao Founder.
- 📊 **measured** — medido/reproduzido no produto/repo/API.
- 🔎 **repo observed** — observado no código/documentação atual.
- 🌐 **external** — fonte externa pesquisada.
- 💭 **hypothesis** — hipótese a validar no warm-up.

---

# 0. RESULTADO EM UMA FRASE

> **O dono da corretora pergunta “como estamos?” e recebe um veredito executivo reproduzível, com produção, comissão, contribuição pós-repasse, pessoas/canais, concentração, renovações, projeção, riscos, oportunidades e qualidade dos dados — calculados uma única vez sobre um modelo canônico que funciona independentemente de a origem ser InfoCap, Quiver, Segfy ou outro sistema de gestão.**

```text
CORRETOR
   ↓
"Como estamos este trimestre?"
   ↓
AUTOBROKERS CORE
   ↓
EXECUTIVE QUERY PLAN
   ↓
PROVIDER RESOLVER
   ↓
CAPABILITY MANIFEST
   ↓
PROVIDER ADAPTER
   ↓
CANONICAL BROKERAGE INTELLIGENCE MODEL
   ↓
METRIC REGISTRY
   ↓
DETERMINISTIC METRIC ENGINE
   ↓
EXECUTIVE EVIDENCE PACK
   ↓
FINDINGS + VEREDITO
   ↓
CHAT + ARTIFACT
```

---

# 0.1 BIG IDEA

A SPEC-081 provou um princípio correto:

> **o modelo escolhe O QUE fazer; o código FAZ.**

A SPEC-094 sobe o nível:

```text
SPEC-081
"faça um Raio-X / Radar"

SPEC-094
"entenda a corretora executivamente"
```

A mudança principal não é visual. É arquitetural:

> **uma métrica da corretora não pode pertencer à InfoCap. Ela pertence ao domínio de corretagem.**

---

# 0.2 A FRASE QUE CONGELA A ARQUITETURA

🔒

> **InfoCap é uma fonte. Quiver é uma fonte. Segfy é uma fonte. Nenhuma delas é a semântica do AutoBrokers.**

```text
provider field
≠
business metric
```

Exemplo:

```text
InfoCap: val_c
Quiver: campo futuro ainda desconhecido
Segfy: campo futuro ainda desconhecido
```

Depois de PROVADO o significado, todos podem mapear para:

```text
broker_commission_accrued
```

E a métrica é escrita UMA VEZ:

```text
commission.broker_accrued
```

---

# 0.3 EXIGÊNCIA DO FOUNDER — AUDITORIA TOTAL DA INFOCAP

🔒 **HARD GATE.**

A SPEC não fecha reutilizando apenas os endpoints já usados pela 081.

Antes de congelar o modelo canônico e o catálogo final de métricas, a execução deve realizar um:

# **CENSO COMPLETO DA CORPAPI/INFOCAP DISPONÍVEL ÀS CORRETORAS PILOTO**

Objetivo:

```text
descobrir sistematicamente tudo que a API realmente entrega,
o que cada campo significa,
como os datasets se relacionam,
quais limites/anomalias existem,
e quais capacidades executivas podem ser alimentadas
```

Entregáveis obrigatórios:

```text
docs/canon/providers/infocap/
  INFOCAP-CORPAPI-CENSUS-v2.md
  infocap-capability-manifest.json
  infocap-field-dictionary.json
  infocap-golden-controls.json
  infocap-schema-fingerprints.json
```

Os nomes físicos podem ser ajustados ao padrão do repo. A função desses artefatos não pode desaparecer.

---

# 0.4 POR QUE O CENSO É NÃO NEGOCIÁVEL

📊 A SPEC-081 já demonstrou o custo de assumir sem medir.

A primeira versão assumiu em `/renovacoes` campos que não existiam:

```text
indireto
nome_produtor
val_c
```

📊 Também confundiu populações de `INIVIG` e `FIMVIG`; a interseção real medida era apenas 2,8%.

📊 O teste atual da fonte comercial toca a rede de propósito porque uma fixture construída a partir da interpretação errada poderia ficar verde contra uma API imaginária.

> **Provider semantics são evidência, não suposição.**

---

# 0.5 O CANON ATUAL JÁ TEM CONTRADIÇÃO

🔎 O mapa antigo da CorpAPI interpreta determinados 403 como falta de permissão.

🔎 `backend/app/comercial/fonte_infocap.py`, após medição posterior, registra que ao menos um padrão de 403/SigV4 significava **rota inexistente** e que a conclusão anterior estava errada.

O Censo v2 deve:

1. medir;
2. distinguir classes de erro;
3. documentar evidence;
4. superseder/corrigir conhecimento antigo;
5. impedir duas verdades contraditórias no Canon/RAG.

---

# 0.6 EXIGÊNCIA DO FOUNDER — ZERO CEGUEIRA PARA QUIVER/SEGFY

🔒 **HARD INVARIANT.**

É proibido terminar com arquitetura do tipo:

```python
if provider == "infocap":
    calcular_comissao(...)
elif provider == "quiver":
    calcular_comissao_quiver(...)
elif provider == "segfy":
    calcular_comissao_segfy(...)
```

O desenho obrigatório:

```text
InfoCap raw ──→ InfoCap Adapter ───┐
Quiver raw ───→ Quiver Adapter ────┼─→ CBIM
Segfy raw ────→ Segfy Adapter ─────┤
Outro raw ────→ Outro Adapter ─────┘
                                   ↓
                             Metric Engine
```

---

# 0.7 O QUE PODE VARIAR POR PROVIDER

Pode variar:

- autenticação;
- transporte;
- endpoints;
- paginação;
- campos;
- granularidade;
- códigos;
- status;
- datas;
- filtros;
- limites;
- rate limit;
- API/WebService/export autorizado.

Não pode variar:

- fórmula canônica;
- semântica da métrica;
- Evidence Pack;
- UX do Executive Intelligence;
- resultado para o mesmo fato canônico.

---

# 0.8 NÃO INVENTAR QUIVER OU SEGFY

Hoje ainda não temos os contratos reais de acesso.

A SPEC deve:

- preparar o contrato;
- criar Provider Admission Gate;
- criar um Reference Provider somente para testes;
- provar que o Metric Engine não depende da InfoCap.

A SPEC não deve:

- inventar endpoints Quiver;
- inventar campos Segfy;
- criar adapters de produção com base em páginas públicas;
- chamar mapping hipotético de integração pronta.

Quando houver acesso:

```text
MEASURE → MAP → CERTIFY → ACTIVATE
```

---

# 0.9 EVIDÊNCIA EXTERNA DE DOMÍNIO COMUM

🌐 Quiver publicamente trabalha com apólices, comissões, renovações, cancelamentos, contas a pagar/receber, fluxo de caixa, rentabilidade por produto/vendedor e integrações.

🌐 Segfy publicamente possui produção, mix de carteira, renovação, comissão recebida/não recebida, pagamento de comissão, análise financeira, sinistros e filtros por seguradora/produtor/ramo.

Isso prova a existência de semântica de domínio comum.

Não prova schema de API.

---

# 0.10 PADRÃO TÉCNICO ADOTADO

Usar os princípios de:

- **Anti-Corruption Layer / Adapter Layer** para traduzir providers na borda;
- **Semantic Layer** para definir métricas uma vez.

Não instalar Azure/dbt por isso.

Absorver o padrão.

---

# 1. RESULTADO DE NEGÓCIO

O dono deve conseguir perguntar:

```text
Como estamos?
Como estamos contra o trimestre passado?
Quem está acelerando?
Quem está caindo?
Qual canal gera mais valor?
Onde o repasse está alto?
Onde estou concentrado demais?
O que vence em 15/30/60/90 dias?
Quanto de produção/comissão está em jogo?
Se o ritmo continuar, onde fechamos?
Qual número ainda não é confiável?
```

E receber:

```text
VEREDITO + EVIDENCE + DRILLDOWN + ARTIFACT
```

---

# 1.1 O PRODUTO NÃO É “UM RELATÓRIO”

🔒

`Pulso 360 da Corretora` é experiência/output.

A arquitetura é:

# **Executive Intelligence Engine**

Consumidores:

- Core Chat;
- Pulso 360;
- Briefing;
- Auxiliares;
- dashboards;
- reuniões executivas;
- AutoBrokers Engine/API.

---

# 2. POR QUE AGORA

1. SPEC-081 já provou integração + cálculo + Artifact.
2. A fonte atual está InfoCap-specific.
3. A próxima corretora pode usar outro sistema.
4. Mais métricas sobre `nosnum/val_c` multiplicariam dívida.
5. Quiver/Segfy têm domínios equivalentes com semântica própria.
6. É hora de estabilizar o modelo de negócio.

---

# 3. ESTADO ATUAL

## 3.1 O QUE ESTÁ CERTO

🔎 `backend/app/comercial/calculos.py` usa majoritariamente funções puras.

Preservar.

## 3.2 O ACOPLAMENTO

🔎 `fonte_infocap.py` produz:

```text
Apolice
ProdutorDaApolice
Vencimento
```

com semântica direta da InfoCap.

🔎 `relatorios_comerciais.py` resolve `FonteInfocap`.

Foi correto para velocidade da 081, não é arquitetura final.

## 3.3 LATÊNCIA MEDIDA

📊 No código:

```text
Raio-X anual cold .... ~53 s
Radar 90 dias ........ ~8 s
```

## 3.4 COBERTURA MEDIDA

📊 Calibração 2025:

```text
1.680 apólices
80,6% com produtor
86,2% da comissão atribuída
```

Coverage continua first-class.

---

# 4. DECISÃO CENTRAL

Criar:

# **Canonical Brokerage Intelligence Model — CBIM**

O Metric Engine fala CBIM.

Nunca fala provider.

---

# 5. O QUE O CBIM NÃO É

Não é:

- ERP;
- data warehouse inteiro;
- cópia permanente do sistema;
- nova fonte da verdade;
- novo RAG.

É:

```text
contrato canônico de leitura analítica
```

---

# 6. PRINCÍPIO DO CBIM

🔒

> **Se a definição de um field depende do nome do sistema, ainda estamos no adapter.**

Dentro do CBIM:

```text
policy_ref
broker_commission_accrued
producer_repasse_accrued
```

e não:

```text
nosnum
val_c
val_r
```

---

# 7. GRANULARIDADE PRIMEIRO

Distinguir:

```text
POLICY
POLICY_MOVEMENT
COMMISSION_EVENT
PRODUCER_ASSIGNMENT
RENEWAL
QUOTE
CLAIM
INTERACTION
CASHFLOW_EVENT
```

Não contar endosso + proposta + apólice como três apólices.

---

# 8. CANONICAL FACTS

## 8.1 PolicyFact

```text
provider_key
source_policy_ref
canonical_policy_ref
human_policy_number
customer_ref
insurer_ref
branch_ref
business_type
status
issue_date?
valid_from
valid_to
premium_gross?
premium_net?
currency
previous_policy_ref?
is_cancelled?
source_refs
```

## 8.2 PolicyMovementFact

```text
movement_type
policy_ref
effective_date
premium_delta?
commission_delta?
source_ref
```

## 8.3 ProducerAssignmentFact

```text
policy_ref
source_actor_ref
canonical_actor_ref?
source_role
canonical_role?
assignment_order?
commission_share_amount?
commission_share_pct?
effective_from?
effective_to?
source_ref
```

## 8.4 CommissionFact

```text
broker_commission_accrued
broker_commission_received
commission_base
commission_tax
commission_reversal
accrual_date
receipt_date
status
source_ref
```

## 8.5 ProducerPayoutFact

```text
producer_ref
policy_ref
repasse_accrued
repasse_paid
repasse_pct
accrual_date
payment_date
source_ref
```

## 8.6 RenewalFact

```text
policy_ref
expiry_date
renewal_status?
previous_policy_ref?
renewed_policy_ref?
premium_at_expiry?
commission_at_expiry?
producer_ref?
days_to_expiry
source_ref
```

## 8.7 QuoteFact

```text
quote_ref
customer_ref
created_at
updated_at
status
insurer_ref?
branch_ref?
producer_ref?
quoted_premium?
won_policy_ref?
source_ref
```

## 8.8 ClaimSignalFact

Somente quando disponível/governado:

```text
policy_ref
claim_ref
claim_status
reported_at?
source_ref
```

SPEC-093 continua autoridade de Claims Learning.

## 8.9 InteractionFact

```text
customer_ref
actor_ref
interaction_type
created_at
status
source_ref
```

## 8.10 CashflowFact

Somente com evidence real:

```text
amount
direction
category
due_at
settled_at
status
source_ref
```

---

# 9. DIMENSIONS

```text
Insurer
Branch/ProductLine
Producer/Actor
Customer
Company
Team
Period
```

Customer PII não precisa ir ao Executive Evidence Pack agregado.


---

# 10. PROVIDER ADAPTER CONTRACT

Criar uma porta de leitura analítica.

Nome físico é hipótese; opções aceitáveis:

```text
BrokerageAnalyticsProvider
PortfolioAnalyticsProvider
BrokerageDataProvider
```

O warm-up escolhe a que melhor se encaixar em `backend/app/providers/`.

Contrato conceitual:

```python
class BrokerageAnalyticsProvider(Protocol):
    provider_key: str

    async def capabilities(company_id) -> ProviderCapabilityManifest:
        ...

    async def production(company_id, period) -> list[PolicyFact]:
        ...

    async def producer_assignments(company_id, period) -> list[ProducerAssignmentFact]:
        ...

    async def commissions(company_id, period) -> list[CommissionFact]:
        ...

    async def renewals(company_id, period) -> list[RenewalFact]:
        ...

    async def quotes(company_id, period) -> list[QuoteFact]:
        ...
```

O adapter pode otimizar/batch internamente. O contrato é semântico, não prescrição de chamadas HTTP.

---

# 11. NÃO DUPLICAR `PolicyDataProvider`

🔎 Já existe:

```text
backend/app/providers/policy_data_provider.py
```

e ele registra literalmente que InfoCap é provider piloto, nunca a arquitetura, e que Quiver/Segfy futuros devem entrar sem tocar a inteligência.

Preservar.

Separação:

```text
PolicyDataProvider
→ lookup/detail individual operacional

BrokerageAnalyticsProvider
→ leitura agregada/portfolio analytics
```

SPEC-101 depois pode industrializar registry/factory.

---

# 12. PROVIDER RESOLVER

🔒 Não resolver provider pelo nome da corretora.

Hoje a 081 faz um caminho legado:

```text
company name → slug → CORP_INFOCAP_{SLUG}_*
```

O próprio código chama isso de dívida.

Destino:

```text
company_id
→ tenant_connections / Vault
→ management-system connection
→ provider_key
→ adapter
```

Compatibilidade legacy pode existir temporariamente somente com:

- feature flag;
- telemetry;
- teste;
- remoção registrada para SPEC-101.

---

# 13. PROVIDER CAPABILITY MANIFEST

Cada conexão deve declarar o que realmente fornece.

Estados:

```text
SUPPORTED
PARTIAL
UNAVAILABLE
UNKNOWN
DEGRADED
```

Capabilities iniciais:

```text
portfolio.policies
portfolio.production
portfolio.policy_status
portfolio.cancellations
portfolio.renewals
commercial.producers
commercial.producer_assignments
commercial.quotes
financial.commission_accrued
financial.commission_received
financial.commission_reversals
financial.commission_tax
financial.producer_repasse_accrued
financial.producer_repasse_paid
financial.receivables
financial.cashflow
claims.status
crm.interactions
contacts.customer
```

---

# 14. REGRA DE CAPABILITY

🔒

> **Dado ausente não vira zero.**

Se provider não oferece `commission_received`:

```text
commission.broker_received = UNAVAILABLE
```

Não:

```text
0
```

---

# 15. FIELD AVAILABILITY / COVERAGE

Cada canonical field/capability pode carregar:

```text
available
coverage_pct
semantics_verified
freshness
warnings
source_refs
```

Exemplo:

```text
producer assignments = PARTIAL
coverage = 80.6%
```

O relatório mostra.

---

# 16. METRIC REGISTRY

Criar catálogo versionado de métricas.

Cada definição:

```text
metric_id
semantic_version
label
description
grain
formula
time_basis
required_fields
required_capabilities
optional_dimensions
unit
currency_semantics
coverage_rule
confidence_rule
allowed_fallback
forbidden_fallback
controls
```

---

# 17. REGRA DO METRIC REGISTRY

🔒

> **Fórmula não conhece provider.**

Teste estático/adversarial:

dentro do módulo do Metric Engine / metric definitions, provider-specific conditionals são proibidos.

Strings como:

```text
infocap
quiver
segfy
```

não podem controlar fórmula.

---

# 18. METRIC TIME BASIS

A SPEC-081 provou que isso é crítico.

Bases canônicas:

```text
POLICY_ISSUE_DATE
POLICY_VALID_FROM
POLICY_VALID_TO
MOVEMENT_EFFECTIVE_DATE
COMMISSION_ACCRUAL_DATE
COMMISSION_RECEIPT_DATE
PRODUCER_PAYOUT_DATE
QUOTE_CREATED_DATE
QUOTE_CLOSED_DATE
CLAIM_REPORTED_DATE
CASHFLOW_DUE_DATE
CASHFLOW_SETTLED_DATE
```

---

# 19. HARD RULE — NÃO MISTURAR BASES TEMPORAIS

🔒

Não comparar:

```text
produção por início de vigência
```

com:

```text
renovação por fim de vigência
```

como se fossem a mesma população.

Toda métrica transporta `time_basis`.

---

# 20. METRIC RESULT ENVELOPE

Exemplo conceitual:

```json
{
  "metric_id": "commission.broker_accrued",
  "semantic_version": "1",
  "value": 1863831.0,
  "unit": "BRL",
  "period": {
    "start": "2025-01-01",
    "end": "2025-12-31"
  },
  "time_basis": "POLICY_VALID_FROM",
  "coverage": 1.0,
  "confidence": "HIGH",
  "provider_key": "infocap",
  "source_refs": ["snapshot:..."],
  "warnings": []
}
```

Provider é provenance, não lógica.

---

# 21. METRICS CORE V1

## 21.1 `production.policy_count`

Count distinct canonical policy grain.

Não documentos.

## 21.2 `production.premium_written`

Soma do prêmio semanticamente definido.

Gross/net são métricas diferentes se ambos existirem.

## 21.3 `commission.broker_accrued`

Comissão comercial gerada/accrued.

Não chamar de caixa recebido.

## 21.4 `commission.broker_received`

Somente com settlement evidence.

## 21.5 `repasse.producer_accrued`

Repasse comprometido/gerado.

## 21.6 `repasse.producer_paid`

Somente com pagamento real.

## 21.7 `contribution.after_repasse_accrual`

```text
broker_commission_accrued
-
producer_repasse_accrued
```

Nome visível:

# **Contribuição pós-repasse**

🔒 Nunca “lucro”.

## 21.8 `production.new_vs_renewal`

Quantidade, prêmio e comissão.

## 21.9 `mix.insurer`

Quantidade/premium/commission.

## 21.10 `mix.branch`

Quantidade/premium/commission.

## 21.11 `producer.performance`

- policies;
- premium;
- commission;
- repasse;
- contribution;
- ticket.

## 21.12 `producer.momentum`

30/60/90 dias e comparação.

## 21.13 `renewal.exposure`

15/30/60/90 dias.

## 21.14 `projection.run_rate`

Projeção determinística, premissas explícitas.

## 21.15 `data.coverage`

Coverage por métrica/dimensão.

---

# 22. METRICS CONDICIONAIS DESCOBERTAS PELO CENSO

O Censo da InfoCap pode revelar mais.

Quiver/Segfy podem oferecer capacidades adicionais.

Possíveis métricas condicionais:

```text
quote.pipeline
quote.conversion
policy.cancellation_rate
renewal.retention_rate
commission.receivable
commission.reconciliation
commission.tax
cashflow.forecast
producer.payout_due
claims.incidence
claims.operational_burden
customer.cross_sell_gap
interaction.followup_gap
```

🔒 Capability + fields + semântica precisam ser provados.

---

# 23. PRODUCER IDENTITY MAP

Uma fonte pode chamar tudo de “produtor”, mas representar:

- employee;
- executive;
- closer;
- partner;
- indicator;
- real estate agency;
- channel;
- affiliate;
- other.

Criar mapping tenant-owned:

```text
source_actor_ref
→ canonical_actor_ref
→ actor_type
→ user_id?
→ team_id?
```

`actor_type` inicial:

```text
employee
partner
channel
indicator
producer
other
unknown
```

---

# 24. NÃO CLASSIFICAR PESSOA SÓ PELO NOME

Nome contendo:

```text
- INDICADOR
```

pode gerar suggestion.

Não authoritative mapping automático.

Autoridade:

- semântica do source;
- configuração;
- human confirmation;
- futura Identity Fabric.

---

# 25. POR QUE O IDENTITY MAP É NECESSÁRIO

Sem ele:

```text
"seu funcionário Marcos..."
```

pode ser mentira.

Enquanto `actor_type=unknown`, usar:

```text
produtor/canal
```

sem inventar vínculo trabalhista.

---

# 26. EXECUTIVE QUERY PLAN

LLM pode interpretar:

```text
period
comparison
dimensions
metric families
drilldown
```

Não calcula.

Exemplo:

```json
{
  "period": "2026-Q3-to-date",
  "compare": "previous_equal_period",
  "views": [
    "executive",
    "producer_momentum",
    "renewal_exposure",
    "concentration"
  ]
}
```

---

# 27. O PRINCÍPIO DA 081 SOBE DE NÍVEL

🔒

```text
LLM chooses WHAT
deterministic engine computes
LLM explains/prioritizes
```

Toda frase numérica do narrador precisa apontar para metric/evidence refs.

---

# 28. EXECUTIVE EVIDENCE PACK

Antes do veredito:

```text
period
comparison period
provider capabilities
metric results
dimensions
coverage
data freshness
warnings
source snapshots
deterministic findings
```

O narrador recebe isso.

Não raw portfolio inteiro sem necessidade.

---

# 29. EXECUTIVE VERDICT

Objetivo: leitura em ~30 segundos.

Estrutura:

```text
1. SITUAÇÃO
2. MOVIMENTO
3. DINHEIRO
4. RISCO
5. PRIORIDADE
```

Cada afirmação importante aponta para evidence.

---

# 30. VEREDITO NÃO É OPINIÃO LIVRE

Pode:

- sintetizar;
- priorizar;
- explicar;
- contextualizar.

Não pode:

- inventar causalidade;
- chamar contribuição de lucro;
- chamar accrued de recebido;
- chamar correlação de causa;
- chamar partner de funcionário sem map;
- esconder coverage;
- omitir warning material.

---

# 31. FINDING OBJECT

Antes do texto:

```json
{
  "finding_id": "...",
  "type": "producer_deceleration",
  "severity": "attention",
  "metric_refs": ["..."],
  "evidence_refs": ["..."],
  "statement": "...",
  "recommended_question": "..."
}
```

Finding deve ser evidence-backed.

---

# 32. PRODUCER MOMENTUM

Comparar:

```text
30d vs previous 30d
60d vs previous 60d
90d vs previous 90d
```

Quando houver histórico:

```text
same period YoY
```

Mostrar:

- policies;
- premium;
- commission;
- contribution;
- ticket;
- mix change.

---

# 33. MOMENTUM NÃO É RANKING SIMPLES

Quadrantes conceituais:

```text
HIGH VALUE + ACCELERATING
HIGH VALUE + DECELERATING
LOW VALUE + ACCELERATING
LOW VALUE + DECELERATING
```

Visual só se ficar claro.

---

# 34. CONTRIBUTION AFTER REPASSE

Se temos accrued:

```text
commission accrued - repasse accrued
= contribution after repasse accrual
```

Nunca:

```text
profit
net margin
cash
final result
```

---

# 35. ECONOMIC SIGNALS

Por actor/insurer/branch/new-renewal:

```text
commission / premium
repasse / commission
contribution / premium
commission per policy
premium per policy
```

Sempre com coverage.

---

# 36. CONCENTRATION

Calcular shares e opcional HHI por:

- insurer;
- branch;
- actor/channel.

Jargon não precisa aparecer.

UI pode dizer:

```text
"42% da comissão depende de duas seguradoras."
```

---

# 37. RENEWAL EXPOSURE

Janelas:

```text
0–15
16–30
31–60
61–90
```

Por:

- policy count;
- premium at expiry;
- historical commission associated;
- actor/channel;
- insurer;
- branch.

🔒 Não chamar comissão histórica da apólice de “comissão futura garantida”.

---

# 38. RENEWAL RISK

Se houver activity/status evidence:

```text
engaged
no_activity
waiting_customer
quoted
renewed
lost
unknown
```

Sem evidence:

não inferir “órfã”.

---

# 39. PROJECTION

V1 é determinística.

Regras:

- somente períodos completos apropriados;
- run-rate;
- método/premissa visível;
- comparação histórica;
- não chamar extrapolação de “previsão de IA”.

Future predictive model só após backtest.

---

# 40. PROJEÇÃO É TIME-BASIS AWARE

Série de commission accrued não prevê cash received sem settlement model.

---

# 41. DATA CONFIDENCE PANEL

Toda peça mostra:

```text
provider
last refresh
period
metric coverage
actor coverage
commission coverage
missing capabilities
warnings
```

---

# 42. COVERAGE É DADO DE PRIMEIRA CLASSE

O padrão da 081 permanece.

Exemplo:

```text
1.354 / 1.680 policies têm producer mapping
86.2% da comissão está atribuída
```

---

# 43. SOURCE / PROVENANCE

Cada extração gera metadata:

```text
company_id
provider_key
connection_id
dataset
query description
period
extracted_at
schema_fingerprint
row_count
coverage
```

Sem credenciais.

---

# 44. PROVIDER SCHEMA FINGERPRINT

Para cada endpoint/dataset:

```text
field names
observed types
nullability sample
nested shape
response envelope
```

Hash/version.

Mudou:

```text
SCHEMA_DRIFT
```

---

# 45. SCHEMA DRIFT BEHAVIOR

Required field desapareceu:

```text
metric = DEGRADED / UNAVAILABLE
```

Não silent zero.

Diferenciar:

```text
individual null value
```

de:

```text
required field vanished from schema
```

---

# 46. INFOCAP CENSUS — FONTES DA AUDITORIA

Usar:

1. Postman/docs reais disponíveis;
2. código atual;
3. Canon atual;
4. chamadas read-only;
5. telas/relatórios para cross-check;
6. network read-only se necessário/autorizado;
7. histórico de medições.

Não brute-force destrutivo.

Não writes.

---

# 47. INFOCAP CENSUS — PARA CADA ENDPOINT

Registrar:

```text
method
path
purpose
auth
permission behavior
params
required/optional
time/date basis
filters
pagination
sort
range limits
rate/concurrency
response envelope
field dictionary
types
nulls
identity keys
relation keys
money semantics
sign semantics
status semantics
cancel semantics
freshness
row count
latency
HTTP errors
filial/tenant behavior
PII sensitivity
anomalies
UI equivalent
golden controls
CBIM mapping
capabilities
```

---

# 48. INFOCAP CENSUS — TODOS OS FIELDS

🔒 Todos os fields observáveis nos endpoints/datasets descobertos.

Cada field:

```text
field_name
sample_type
nullable
redacted_sample
meaning
meaning_confidence
fact/dimension
sensitivity
canonical_mapping?
unused_reason?
```

Não limitar ao relatório atual.

---

# 49. INFOCAP CENSUS — PERMISSIONS

Se login traz flags:

```text
capture
map
verify
```

Não assumir significado sem evidence.

---

# 50. INFOCAP CENSUS — ERROR TAXONOMY

Distinguir:

- auth failure;
- permission;
- route missing;
- invalid params;
- no rows;
- oversized range;
- gateway timeout;
- provider instability;
- rate limit.

A antiga ambiguidade 403 vira teste obrigatório.

---

# 51. INFOCAP CENSUS — GOLDEN CONTROLS

Para datasets importantes, usar períodos fechados.

Cross-check:

```text
API
vs
InfoCap own UI/report
```

Controles:

```text
policy count
premium
commission
producer coverage
top actors
renewal counts
```

Tolerância explícita.

---

# 52. INFOCAP CENSUS — DISCOVERY OUTPUT

Classificar:

```text
CURRENTLY_USED
AVAILABLE_UNUSED
PARTIAL
UNAVAILABLE
UNKNOWN
DEPRECATED/BROKEN
```

E gerar:

```text
METRIC OPPORTUNITY BACKLOG
```

---

# 53. PROVIDER ADMISSION GATE — QUIVER/SEGFY/FUTUROS

Nenhum provider é suportado até cumprir:

1. auth/connection measured;
2. capability census;
3. field dictionary;
4. canonical mapping;
5. real redacted fixture/golden sample;
6. vendor report cross-check;
7. adapter contract tests;
8. metric parity tests;
9. missing capability behavior;
10. schema drift detection;
11. security/ACL test;
12. latency benchmark;
13. canary tenant;
14. execution report.

---

# 54. PROVIDER PARITY PRINCIPLE

🔒

Mesmo fato econômico canônico → mesmo resultado.

Se três adapters representam semanticamente:

```text
10 policies
R$ 100k premium
R$ 15k commission accrued
R$ 3k repasse accrued
```

o engine produz em todos:

```text
contribution after repasse = R$ 12k
```

---

# 55. REFERENCE PROVIDER

Como Quiver/Segfy reais não estão acessíveis agora:

criar somente em teste:

```text
ReferenceAnalyticsProvider
```

Ele retorna CBIM diretamente.

Prova que Metric Engine roda sem importar InfoCap.

Não simula campos de Quiver/Segfy.

---

# 56. PROVIDER ADDITION TEST

Ao adicionar provider futuro, não deve ser necessário alterar:

```text
metric definitions
metric formulas
Executive Evidence Pack schema
Executive Verdict contract
Artifact composition semantics
```

Exceto para nova capability universal explicitamente adicionada.

---

# 57. METRIC SEMANTIC EQUIVALENCE

“Produção” em dois sistemas só é equivalente depois de responder:

```text
qual grain?
qual date basis?
inclui endosso?
inclui cancelado?
qual prêmio?
qual comissão?
qual status?
```

Nome de relatório não prova equivalência.

---

# 58. COMMISSION SEMANTICS

Separar:

```text
accrued
received
reversed
tax
producer payout accrued
producer payout paid
```

Nunca mapear received→accrued por conveniência.

---

# 59. PREMIUM SEMANTICS

Possíveis:

```text
gross
net
liquid
total
issued
movement delta
```

Audit primeiro.

---

# 60. NEW VS RENEWAL

CBIM:

```text
NEW
RENEWAL
ENDORSEMENT
OTHER
UNKNOWN
```

InfoCap mapping atual pode usar `nosnum_ren` somente no adapter.

Segfy publicamente diferencia Nova/Endosso/Renovação em seus relatórios, mas API mapping futuro precisa ser medido.

---

# 61. UNKNOWN IS VALID

Se adapter não prova business type:

```text
UNKNOWN
```

Não NEW por default.

---

# 62. EXECUTIVE PULSE — SEÇÕES DEFAULT

1. Executive Verdict
2. Current vs Previous
3. People & Channels Momentum
4. Economics After Repasse
5. Insurer/Branch Mix & Concentration
6. Renewal Exposure
7. Projection
8. Data Confidence & Sources

---

# 63. NÃO VIRAR PAINEL POLUÍDO

Regra:

```text
verdict first
evidence second
```

Cada seção responde uma pergunta.

---

# 64. DEFAULT PERIOD

Se user diz:

```text
"Como estamos?"
```

Default recomendado:

```text
year-to-date
vs equal period previous year
```

e, se útil:

```text
recent equal-window comparison
```

Warm-up deve validar UX com `entender_periodo`.

---

# 65. FOLLOW-UP CONTEXT

```text
"E só a Porto?"
```

Reusar period + snapshot/evidence quando válido.

Não reconsultar tudo.

---

# 66. CHAT TOOLING

Preferir tool de domínio:

```text
executive_intelligence
```

com query plan estruturado.

Evitar tool explosion.

---

# 67. ARTIFACT

Reusar `ArtifactService`.

Não criar renderer.

Payload guarda:

- metric IDs/versions;
- period;
- evidence summary/ref;
- coverage;
- provider provenance;
- generated_at.

---

# 68. CHAT E ARTIFACT DEVEM BATER

🔒 Mesmo Evidence Pack.

Nunca duas consultas independentes produzindo números divergentes para a mesma entrega.

---

# 69. OPTIONAL EXECUTIVE NARRATOR

No máximo uma chamada curta quando necessário.

Input:

```text
Executive Evidence Pack
```

Output:

```text
verdict
priorities
plain-language explanation
```

Número sem metric ref é inválido.

---

# 70. FALLBACK SEM LLM

Se model indisponível:

- deterministic summary;
- metrics;
- Artifact.

A inteligência numérica continua funcionando.


---

# 71. MODEL ROUTING E CUSTO

O caminho numérico é determinístico.

LLM só entra em:

1. interpretação da intenção, se necessária;
2. explicação/priorização do Evidence Pack.

Target:

```text
data extraction ........ provider cost / API only
metric calculation ..... deterministic
finding generation ..... deterministic-first
narration .............. 0–1 short LLM call
```

## 71.1 Regra de custo

Não mandar milhares de apólices para modelo.

O modelo recebe:

```text
aggregates
findings
coverage
warnings
evidence refs
```

## 71.2 Cost observability

Registrar:

```text
provider_requests
provider_latency
rows_read
cache_hit
metric_compute_ms
LLM_input_tokens
LLM_output_tokens
LLM_cost
artifact_render_ms
total_cost
```

por request/work run.

---

# 72. SNAPSHOT / CACHE ARCHITECTURE

A 081 provou que leitura cold pode ser lenta.

A 094 deve separar:

```text
SOURCE SNAPSHOT
METRIC RESULT CACHE
ARTIFACT
```

## 72.1 Source Snapshot

Uma captura lógica da leitura utilizada para uma análise.

Metadata:

```text
snapshot_id
company_id
provider_key
connection_id
period
datasets
schema_fingerprints
extracted_at
source_as_of?
row_counts
coverage
```

Não precisa guardar raw payload inteiro permanentemente.

## 72.2 Metric Result Cache

Chave:

```text
company
provider connection/version
period
metric semantic version
filters
source snapshot/version
```

Evita cache stale invisível.

## 72.3 Artifact

Resultado de apresentação.

Não é cache de dados.

---

# 73. NÃO CRIAR DATA WAREHOUSE RAW POR PADRÃO

🔒

A SPEC não autoriza copiar toda a InfoCap/Quiver/Segfy para Supabase “porque um dia pode ser útil”.

Persistência só quando há motivo:

- performance comprovada;
- histórico que provider não oferece;
- replay/audit;
- Work Run durável;
- trend analysis;
- source snapshot necessário.

E sempre com:

```text
tenant scope
retention
provenance
refresh
delete/rebuild semantics
```

---

# 74. HISTÓRICO ANALÍTICO

Para trend/momentum, o provider pode permitir consulta histórica diretamente.

Preferência inicial:

```text
query provider historical range
```

Quando não for suficiente, snapshot canônico agregado pode ser persistido.

Não persistir PII só para fazer série mensal.

---

# 75. PERFORMANCE TARGETS

Targets devem ser calibrados no warm-up, mas a experiência desejada:

```text
warm executive answer ........ <= 5 s p95
cold common period ............ <= 15 s p95
artifact after evidence ....... <= 8 s p95
follow-up on same snapshot .... <= 3 s p95
```

Se provider real impossibilitar:

- responder progresso truthful;
- usar Work Run quando realmente longo;
- não fingir instantaneidade.

---

# 76. PERFORMANCE BUDGET POR ETAPA

Instrumentar:

```text
provider resolve
capability load
source extraction
canonical mapping
metric compute
finding generation
narration
artifact render
```

O maior componente vira alvo de otimização.

Não otimizar LLM se 90% do tempo está na API.

---

# 77. CONCURRENCY / RATE LIMIT

Cada adapter conhece limites do provider.

Core não decide:

```text
10 parallel requests
```

genericamente.

Adapter controla:

- chunking;
- concurrency;
- retry;
- pagination;
- backoff.

---

# 78. TENANCY

Todo request precisa de:

```text
company_id
```

resolvido no servidor.

Nunca aceitar provider credential/tenant pela instrução do modelo.

Cache/snapshot sempre carregam company + connection.

---

# 79. ACL / ROLES

Executive Intelligence pode expor:

- comissão;
- repasse;
- performance individual;
- dados financeiros.

Portanto:

```text
owner/admin/manager
```

podem ter visões diferentes de:

```text
producer/user
```

A SPEC deve medir roles reais existentes antes de criar regra.

Não assumir que todo membro da corretora vê comissão de todos.

---

# 80. PRODUCER SELF-VIEW

Se produto permitir no futuro:

```text
producer sees own metrics
manager sees team
owner sees brokerage
```

mas só depois de Scope/Identity Fabric.

Não expandir ACL nesta SPEC além do necessário.

---

# 81. PII

Executive aggregates devem minimizar PII.

Default Evidence Pack agregado:

- sem CPF;
- sem telefone;
- sem endereço;
- sem detalhes de apólice individuais desnecessários.

Drilldown pode usar dados autorizados quando pedido.

---

# 82. EGRESS / MODEL PRIVACY

Narrator recebe:

```text
aggregated metrics
actor display names only if necessary/authorized
```

Não carteira raw.

Se BYOK/External Harness futuro:

as mesmas egress policies valem.

---

# 83. MEMORY / RAG

🔒 Métricas executivas não viram RAG por padrão.

Não indexar:

```text
"comissão de agosto = X"
```

como memória sem temporal semantics.

O Core pode manter thread/context do Evidence Pack.

Knowledge durável pode receber apenas:

- semantic definitions;
- approved company goals/preferences;
- validated process knowledge.

---

# 84. FINDINGS → LEARNING

Um Finding de uma execução não vira Memory automaticamente.

Exemplo:

```text
"Porto caiu 18% este mês"
```

é temporal fact do snapshot.

Pode alimentar:

```text
monitor
trend
routine
```

não RAG eterno.

---

# 85. WORK RUNS

Usar Work Run para:

- Censo InfoCap;
- provider admission;
- large historical backfill;
- heavy Executive 360;
- scheduled executive review.

Query comum quente pode ser síncrona.

---

# 86. FAILURE MODEL

Falhas possíveis:

```text
NO_PROVIDER_CONNECTION
PROVIDER_AUTH_FAILED
PROVIDER_PERMISSION_MISSING
PROVIDER_SCHEMA_DRIFT
PROVIDER_TIMEOUT
PROVIDER_RATE_LIMIT
CAPABILITY_UNAVAILABLE
CAPABILITY_PARTIAL
CANONICAL_MAPPING_FAILED
METRIC_INPUT_INCOMPLETE
METRIC_DEGRADED
ARTIFACT_RENDER_FAILED
NARRATION_FAILED
```

Cada uma com linguagem humana.

---

# 87. PARTIAL SUCCESS

Se produção existe e comissão não:

não derrubar tudo.

Responder:

```text
"Consigo analisar produção e renovação.
Comissão não está disponível nesta conexão."
```

Artifact marca unavailable.

---

# 88. PROVIDER FAILURE NÃO PODE VIRAR NÚMERO ZERO

Mutation obrigatória:

provider retorna 500 em commission dataset.

Esperado:

```text
commission metrics = unavailable/degraded
```

Nunca:

```text
R$ 0
```

---

# 89. RETRIES

Adapter-level.

Retry apenas erro transitório.

Não retry:

- 400 invalid request;
- unsupported route;
- semantic mapping failure.

Retry:

- timeout;
- 429;
- 5xx quando provider semantics indicam transient.

---

# 90. FALLBACK DATA

Fallback só pode usar snapshot anterior se:

1. explicitamente marcado stale;
2. data/hora visível;
3. query semantics compatível;
4. user não foi levado a crer que é live.

Exemplo:

```text
"Última leitura válida: 24/08 às 18:00."
```

---

# 91. OBSERVABILITY

Dashboard/Admin metrics:

```text
executive_queries_total
executive_query_success
executive_partial_success
provider_latency
provider_errors_by_type
provider_capability_availability
schema_drift_events
metric_unavailable
metric_degraded
metric_coverage
snapshot_age
artifact_success
narration_success
cost_per_query
```

---

# 92. PROVIDER HEALTH

Por tenant/conexão:

```text
connected
auth ok
last successful read
capabilities
schema status
latency
last error
```

Não só “verde porque login funciona”.

---

# 93. DATA QUALITY SIGNALS

Detectar:

- duplicate policies;
- impossible dates;
- commission > unreasonable bounds;
- negative values;
- unknown insurer;
- unknown branch;
- producer assignment duplicates;
- missing identity refs;
- unexpected enum/status.

Não “corrigir” silenciosamente.

---

# 94. SOURCE DRIFT MONITOR

Cada provider admission cria baseline.

Depois comparar fingerprints.

Drift classes:

```text
ADDITIVE_SAFE
TYPE_CHANGED
FIELD_REMOVED
ENVELOPE_CHANGED
SEMANTICS_SUSPECTED
```

---

# 95. SEMANTIC DRIFT NÃO É SÓ SCHEMA

Mesmo field pode manter nome e mudar significado.

Controles de negócio ajudam:

```text
policy count
premium total
commission total
top insurer
```

Desvio abrupto dispara investigation.

---

# 96. CUTOVER DA SPEC-081

Não apagar tudo e reescrever.

Sequência:

```text
existing FonteInfocap
        ↓
InfoCap Analytics Adapter
        ↓
CBIM
        ↓
existing pure calculations adapted
        ↓
Metric Registry
        ↓
existing Raio-X/Radar consume new engine
        ↓
new Executive 360
```

---

# 97. STRANGLER PATTERN INTERNO

Durante cutover:

```text
legacy 081 result
vs
new 094 result
```

em shadow compare.

Só muda authority quando golden metrics batem.

---

# 98. PARITY GATE COM 081

Para 2025 calibration atual:

dentro da tolerância definida:

```text
policy count
commission total
new/renewal
producer coverage
commission attributed
top producer order
renewal radar controls
```

Novo engine não pode “melhorar arquitetura” quebrando números já provados.

---

# 99. LEGACY TOOL COMPATIBILITY

As ferramentas existentes:

```text
raio_x_comercial
radar_renovacoes
```

podem continuar como aliases/wrappers.

Por dentro:

```text
Executive Intelligence Engine
```

Não obrigar o prompt atual a mudar de uma vez.

---

# 100. ZERO NOVO REPORT ENGINE

🔒

Não criar:

```text
ExecutiveReportService
```

se ele apenas duplicar `ArtifactService`.

Responsabilidades:

```text
Executive Intelligence = dados/métricas/findings
ArtifactService = apresentação/render/publicação
```

---

# 101. INFOCAP AUDIT NÃO É “UMA TAREFA DE DOCUMENTAÇÃO”

É produto/infra.

O resultado deve alimentar código:

```text
Capability Manifest
Field Mappings
Schema Fingerprints
Golden Controls
Tests
Metric Opportunities
```

Não PDF morto.

---

# 102. AUDIT RE-RUN

Criar protocolo que permita repetir:

```text
provider audit
```

quando API muda.

SPEC-101 depois generaliza.

Para 094, InfoCap é first implementation.

---

# 103. IMPLEMENTATION BLOCK 0 — FORENSE + INFOCAP CENSUS

Antes de editar engine:

1. registrar HEAD;
2. ler SPEC-081 e errata;
3. ler `fonte_infocap.py`;
4. ler `calculos.py`;
5. ler live test;
6. ler `PolicyDataProvider`;
7. listar todos os usos InfoCap no repo;
8. localizar docs/Postman disponíveis;
9. inventariar endpoints conhecidos;
10. fazer chamadas read-only controladas;
11. enumerar response fields;
12. mapear relations;
13. medir date bases;
14. medir money semantics;
15. medir error semantics;
16. medir pagination/range;
17. medir concurrency/rate behavior com prudência;
18. cross-check UI/report;
19. criar Golden Controls;
20. corrigir Canon contraditório;
21. produzir Censo;
22. produzir Capability Manifest;
23. só então congelar CBIM mapping v1.

### Gate 0

Nenhum código de métrica novo antes do relatório do Censo existir.

---

# 104. IMPLEMENTATION BLOCK A — CBIM

Criar dataclasses/models/contracts canônicos.

### Gate A

Test fixture CBIM roda sem importar InfoCap.

---

# 105. IMPLEMENTATION BLOCK B — ANALYTICS PROVIDER PORT

Criar registry/resolver + InfoCap adapter.

### Gate B

Provider-specific fields terminam na borda.

---

# 106. IMPLEMENTATION BLOCK C — CAPABILITY MANIFEST

Implementar capability states.

### Gate C

Capability ausente != zero.

---

# 107. IMPLEMENTATION BLOCK D — METRIC REGISTRY

Migrar/refatorar cálculos 081 para métricas versionadas.

### Gate D

Metric modules não contêm provider-specific branching.

---

# 108. IMPLEMENTATION BLOCK E — PRODUCER IDENTITY MAP

Criar estrutura mínima e mapping.

### Gate E

Unknown actor type não vira employee.

---

# 109. IMPLEMENTATION BLOCK F — EXECUTIVE EVIDENCE PACK

Compor metrics/findings/coverage/provenance.

### Gate F

Mesmo pack alimenta chat e Artifact.

---

# 110. IMPLEMENTATION BLOCK G — EXECUTIVE QUERY TOOL

Tool única/compacta.

### Gate G

LLM não calcula números.

---

# 111. IMPLEMENTATION BLOCK H — PULSO 360 ARTIFACT

Usar ArtifactService.

### Gate H

Não criar renderer/report engine paralelo.

---

# 112. IMPLEMENTATION BLOCK I — LEGACY 081 CUTOVER

Wrappers antigos passam a novo engine.

### Gate I

Parity controls verdes.

---

# 113. IMPLEMENTATION BLOCK J — REFERENCE PROVIDER

Test-only.

### Gate J

Todo core Executive 360 funciona com provider não-InfoCap.

---

# 114. IMPLEMENTATION BLOCK K — CANARY

Piloto primeiro na Resulta e/ou tenant autorizado.

### Gate K

- números batem com InfoCap;
- coverage visível;
- sem regressão 081;
- latency/cost medidos.

---

# 115. TEST MATRIX — PROVIDER INDEPENDENCE

1. InfoCap fixture → CBIM.
2. Reference provider → mesmo CBIM.
3. Same CBIM → same metrics.
4. Missing commission capability → unavailable.
5. Partial producer mapping → correct coverage.
6. Schema drift → degraded, no zero.
7. Unknown business_type → unknown.
8. No provider connection → clear failure.
9. Provider timeout → partial/fallback policy.
10. Metrics core imports no InfoCap module.

---

# 116. TEST MATRIX — MONEY

- positive commission;
- negative reversal;
- zero legitimate commission;
- missing commission;
- accrued but not received;
- received with date;
- repasse accrued;
- repasse paid;
- commission tax;
- contribution after repasse;
- currency mismatch.

---

# 117. TEST MATRIX — GRAIN

- policy;
- proposal;
- endorsement;
- cancellation;
- duplicate raw row;
- multi-producer assignment;
- renewal chain;
- policy spanning calendar years.

---

# 118. TEST MATRIX — TIME

- valid_from period;
- valid_to period;
- commission accrual;
- receipt;
- producer payout;
- current partial month;
- leap year;
- inverted dates;
- provider timezone.

---

# 119. TEST MATRIX — PRODUCER IDENTITY

- employee known;
- partner;
- indicator;
- channel/company;
- source name contains misleading role;
- unknown;
- same person with aliases;
- same display name for different source IDs.

---

# 120. TEST MATRIX — EXECUTIVE NARRATIVE

Narrator must not:

- invent numbers;
- invent causal explanation;
- call accrued received;
- call contribution profit;
- call partner employee;
- hide low coverage;
- hide stale snapshot.

---

# 121. TEST MATRIX — INFOCAP CENSUS

For every critical endpoint:

- expected route;
- invalid params control;
- empty period;
- known nonempty period;
- schema fingerprint;
- latency;
- field dictionary completeness;
- UI/report cross-check;
- error class.

---

# 122. RED TEAM MISSION

> **Fazer o Pulso 360 mostrar um número executivo convincente e errado enquanto todos os testes superficiais parecem verdes.**

Ataques:

1. `val_c` vem None;
2. field desaparece;
3. commission received confundida com accrued;
4. endosso contado como policy;
5. renewal population uses wrong date;
6. producer count metadata contradicts array;
7. same policy duplicated across yearly slices;
8. provider returns stale data;
9. cache leaks cross-tenant;
10. actor alias splits one producer into two;
11. two actors same name merge;
12. repasse negative/reversal;
13. month in progress extrapolated incorrectly;
14. provider 500 interpreted empty;
15. 403 route-missing interpreted permission;
16. permission denied interpreted missing route;
17. Quiver future adapter needs formula-specific code;
18. capability unavailable becomes zero;
19. partial coverage omitted;
20. narrator says “lucro”;
21. narrator says “recebido” for accrued;
22. previous period length mismatched;
23. provider changes gross→net premium semantics with same type;
24. raw PII sent to narrator.

---

# 123. MUTATIONS OBRIGATÓRIAS

## M1
Dentro de metric engine:

```python
if provider == "infocap":
```

**FAIL.**

## M2
`commission_received` unavailable → `0`.

**FAIL.**

## M3
`actor_type=unknown` → `"employee"`.

**FAIL.**

## M4
Remove required source field, `_num(None)` makes metric zero.

**FAIL.**

## M5
Count proposals as policies.

**FAIL.**

## M6
Compare INIVIG population to FIMVIG as same basis.

**FAIL.**

## M7
Call contribution “lucro”.

**FAIL.**

## M8
Call accrued commission “recebida”.

**FAIL.**

## M9
Use historical commission as guaranteed future renewal commission.

**FAIL.**

## M10
Chat and Artifact use independent queries.

**FAIL.**

## M11
Cache key loses company_id.

**FAIL.**

## M12
Reference provider removed and engine imports FonteInfocap directly.

**FAIL.**

## M13
Quiver/Segfy production adapter fabricated without measured access.

**FAIL.**

## M14
Schema drift produces silent metric.

**FAIL.**

## M15
Coverage field omitted from partial metric.

**FAIL.**

## M16
Narrator gets raw CPF/customer portfolio.

**FAIL.**

## M17
A new provider requires modifying commission formula.

**FAIL.**

## M18
InfoCap Censo only documents fields used in current reports.

**FAIL.**

---

# 124. E2E SCENARIOS

## E2E-1 — “Como estamos?”
- resolve tenant/provider;
- load capabilities;
- query;
- canonicalize;
- compute;
- compare;
- build Evidence Pack;
- narrate;
- render Artifact;
- numbers match.

## E2E-2 — “E só a Porto?”
- reuses context/snapshot;
- filters dimension;
- recomputes deterministic metrics;
- no unrelated re-fetch.

## E2E-3 — missing finance capability
- production answer succeeds;
- commission section says unavailable;
- no R$0 fiction.

## E2E-4 — schema drift
- provider health degrades;
- impacted metric blocked;
- unaffected metrics survive.

## E2E-5 — Reference Provider
- no InfoCap import;
- same metric semantics;
- Artifact works.

---

# 125. BASELINE / CONTROL

Before changes capture:

- current SPEC-081 live calibration;
- current tool outputs;
- current Artifact;
- latency cold/warm;
- current test suite.

After changes, repeat.

No “green because tests changed”.

---

# 126. SLO / ACCEPTANCE TARGETS

Initial acceptance:

```text
metric parity vs golden controls ........ >= defined tolerances
cross-provider canonical parity ......... 100% for reference facts
provider-specific formula branches ...... 0
silent zero on unavailable data ......... 0
cross-tenant leaks ....................... 0
money terminology violations ............ 0
material coverage omissions ............. 0
```

---

# 127. SECURITY GATES

- credentials only Vault/authorized legacy path;
- no secrets in Censo;
- redacted field samples;
- tenant isolation;
- read-only audit;
- no arbitrary provider URL from LLM;
- allowlisted provider adapters;
- no write APIs in analytics provider;
- provenance retained.

---

# 128. ROLLBACK

Feature flag:

```text
executive_intelligence_v2
```

or existing feature-flag mechanism.

Rollback:

- old 081 wrappers can fall back to current path temporarily;
- new Executive 360 disabled;
- no source data altered;
- no destructive provider writes.

---

# 129. CUTOVER EXIT

Legacy direct `FonteInfocap` use in **commercial report tools** can be removed only when:

- parity passes;
- canary passes;
- all current 081 functionality is preserved;
- rollback path proven.

`FonteInfocap` may survive inside InfoCap adapter implementation.

---

# 130. NO BIG-BANG CONNECTOR REWRITE

Do not rewrite operational InfoCap lookup used by Attendance.

This SPEC touches aggregate intelligence.

Individual policy path remains authority of `PolicyDataProvider`.

---

# 131. REJECTED ALTERNATIVE — “FAZER SÓ INFOCAP AGORA E ARRUMAR DEPOIS”

🚫 Rejected.

Why:

- next provider duplicates formulas;
- semantic differences get hidden;
- current code already demonstrates provider coupling debt;
- reports become marketplace-limited.

---

# 132. REJECTED ALTERNATIVE — “CRIAR UMA TABELA UNIVERSAL COM 200 COLUNAS”

🚫 Rejected.

Why:

- provider schemas leak into core;
- sparse/null swamp;
- grains mixed;
- semantics ambiguous.

Use domain facts + capability manifest.

---

# 133. REJECTED ALTERNATIVE — “JSON GENÉRICO E LLM DESCOBRE”

🚫 Rejected.

Why:

- no deterministic metric semantics;
- weak tests;
- money errors;
- provider changes invisible.

LLM is not schema adapter.

---

# 134. REJECTED ALTERNATIVE — “UM REPORT ENGINE POR PROVIDER”

🚫 Rejected.

This violates the entire purpose.

---

# 135. REJECTED ALTERNATIVE — “WAREHOUSE EVERYTHING”

🚫 Not default.

A future warehouse can exist if measured need proves it.

But the first abstraction is semantic, not storage.

---

# 136. REJECTED ALTERNATIVE — “USAR QUIVER/SEGFY PUBLIC DOCS COMO API SPEC”

🚫 Rejected.

Public product/help pages prove business concepts only.

Real integration waits for real access.

---

# 137. REJECTED ALTERNATIVE — “COMISSÃO MENOS REPASSE = LUCRO”

🚫 Rejected.

Term:

```text
Contribuição pós-repasse
```

until full cost/tax/accounting evidence exists.

---

# 138. WARM-UP — PERGUNTAS QUE O EXECUTOR DEVE RESPONDER

1. Quais datasets InfoCap realmente existem hoje?
2. Qual fonte prova cada endpoint?
3. Qual erro significa rota inexistente vs permission?
4. Qual grain de cada endpoint?
5. Qual date basis de cada dataset?
6. Quais money fields existem?
7. Accrued vs received está distinguível?
8. Quais identities cruzam datasets?
9. Quais fields são PII?
10. Quais endpoints já usados não têm golden control?
11. Quais relatórios da UI permitem cross-check?
12. O que a SPEC-081 hoje calcula corretamente?
13. O que pode ser reutilizado sem adaptação?
14. Onde o código ainda conhece `nosnum`, `val_c`, `prod_docs`?
15. Qual é o menor Provider port coerente com `PolicyDataProvider`?
16. Como provider é resolvido por tenant hoje?
17. Qual caminho Vault existe de fato?
18. Qual capability é parcial?
19. Quais métricas ficam indisponíveis se faltarem certos fields?
20. O que ainda não sabemos sobre Quiver/Segfy?
21. Como garantir que não inventaremos esse desconhecido?
22. O Reference Provider prova independência?
23. Como um novo provider entra sem tocar fórmula?
24. Como drift é detectado?
25. Qual número da UI da InfoCap prova cada golden metric?
26. O que você ainda NÃO entendeu?

Resposta “nada” à última pergunta reprova warm-up.

---

# 139. DEFINITION OF DONE

A SPEC-094 só fecha quando:

## Auditoria InfoCap
- [ ] Censo completo realizado;
- [ ] fontes do Censo registradas;
- [ ] todos endpoints/datasets descobertos classificados;
- [ ] todos fields observados catalogados;
- [ ] identity/relation keys mapeados;
- [ ] money semantics mapeadas;
- [ ] date basis mapeado;
- [ ] permissions/errors distinguidos;
- [ ] 403 ambiguity testada;
- [ ] pagination/range limits medidos;
- [ ] latency registrada;
- [ ] Golden Controls criados;
- [ ] UI/API cross-check feito;
- [ ] Canon contraditório corrigido/superseded;
- [ ] Capability Manifest InfoCap criado;
- [ ] schema fingerprints criados;
- [ ] metric opportunities catalogadas.

## Provider neutrality
- [ ] aggregate provider port existe;
- [ ] `PolicyDataProvider` preservado;
- [ ] provider resolver tenant-aware;
- [ ] CBIM existe;
- [ ] facts/grains explícitos;
- [ ] InfoCap adapter traduz para CBIM;
- [ ] Reference Provider test-only existe;
- [ ] core metric engine roda sem InfoCap;
- [ ] zero provider branch em fórmulas;
- [ ] capability unavailable != zero;
- [ ] Provider Admission Gate documentado/testado;
- [ ] future Quiver/Segfy schemas NÃO foram inventados.

## Metrics
- [ ] Metric Registry versionado;
- [ ] time basis explícito;
- [ ] policy count;
- [ ] premium;
- [ ] commission accrued;
- [ ] commission received only when supported;
- [ ] repasse accrued;
- [ ] repasse paid only when supported;
- [ ] contribution after repasse;
- [ ] new vs renewal;
- [ ] insurer mix;
- [ ] branch mix;
- [ ] producer performance;
- [ ] producer momentum;
- [ ] renewal exposure;
- [ ] projection;
- [ ] data coverage;
- [ ] conditional metrics only when capability proven.

## Identity
- [ ] Producer Identity Map;
- [ ] actor_type unknown supported;
- [ ] no employment inference from name.

## Experience
- [ ] Executive Query Plan;
- [ ] Executive Evidence Pack;
- [ ] deterministic findings;
- [ ] Executive Verdict;
- [ ] Pulso 360 Artifact;
- [ ] chat/artifact same evidence;
- [ ] LLM-free fallback;
- [ ] follow-up reuses snapshot where valid;
- [ ] Data Confidence section.

## Safety/quality
- [ ] PII minimized;
- [ ] ACL respected;
- [ ] cache tenant-safe;
- [ ] schema drift blocks affected metric;
- [ ] partial success supported;
- [ ] stale fallback labeled;
- [ ] observability;
- [ ] latency/cost measured;
- [ ] rollback proven;
- [ ] 081 parity controls pass;
- [ ] red team complete;
- [ ] M1–M18 red;
- [ ] no money terminology violation;
- [ ] no silent zero;
- [ ] no cross-tenant leak;
- [ ] execution report.

---

# 140. O QUE NÃO É DEFINITION OF DONE

Não precisa:

- Quiver production adapter;
- Segfy production adapter;
- warehouse enterprise;
- predictive ML forecasting;
- full DRE;
- cash accounting without data;
- autonomous business decisions;
- new renderer;
- new Artifact engine;
- new RAG;
- full SPEC-101 connector factory.

---

# 141. DEFERRED CONSCIOUSLY

## SPEC-095
Artifact & Delivery Hub Completion.

## SPEC-098
Identity/Scope/Company Soul amplia actor/team mapping.

## SPEC-101
Industrializa provider/connector creation, auth, health, schemas, Vault.

## SPEC-105
Trajectory/replay for analytics Work Runs where useful.

## SPEC-108
MetaHarness adds systematic metric/provider quality monitoring.

## SPEC-109
Executive Intelligence becomes headless Engine action.

---

# 142. SUCCESS METRICS

Produto:

```text
executive queries/week
repeat use
artifact opens
follow-up questions
time-to-insight
```

Data:

```text
metric coverage
provider coverage
producer identity coverage
schema drift detection time
golden parity
```

Engineering:

```text
provider-specific formula branches = 0
new provider metric-engine changes = 0
```

Business:

```text
decisions/findings acted on
renewal exposure surfaced
concentration risks surfaced
producer momentum surfaced
```

Não atribuir receita incremental sem causal measurement.

---

# 143. SCORE

| Dimensão | Nota |
|---|---:|
| Valor executivo para corretora | **100/100** |
| Reutilização do que já existe | **98/100** |
| Preparação multi-provider | **100/100** |
| Redução de dívida InfoCap-only | **100/100** |
| Qualidade/honestidade dos números | **100/100** |
| Escalabilidade Quiver/Segfy | **100/100** |
| Complexidade de implementação | **82/100** |
| Prioridade agora | **100/100** |

---

# 144. POR QUE ESTA SPEC É MAIOR QUE UM “RELATÓRIO 360”

Sem CBIM:

```text
InfoCap report
Quiver report
Segfy report
```

virariam três produtos.

Com CBIM:

```text
InfoCap ─┐
Quiver ──┼→ AutoBrokers Intelligence
Segfy ───┘
```

A corretora muda de sistema.

O AutoBrokers continua entendendo o negócio.

---

# 145. O MOAT

O ativo não é:

```text
saber chamar /documentos_bi
```

O ativo é:

```text
saber o que uma corretora significa economicamente
```

e conseguir traduzir sistemas diferentes para essa mesma inteligência.

---

# 146. SOURCE INDEX INTERNO

Obrigatório no warm-up:

- SPEC-081;
- `backend/app/comercial/fonte_infocap.py`;
- `backend/app/comercial/calculos.py`;
- `backend/app/agents/tools/relatorios_comerciais.py`;
- `backend/tests/test_a_fonte_comercial_bate_com_a_infocap.py`;
- `backend/app/providers/policy_data_provider.py`;
- `docs/canon/INFOCAP-CORPAPI-MAPA.md`;
- SPEC-065;
- Vault/tenant_connections authority;
- ArtifactService;
- Provider/Capability Registry;
- Protocolo AAA v9.

---

# 147. SOURCE INDEX EXTERNO

Research Pack detalha:

- Quiver;
- Segfy;
- Microsoft Anti-Corruption Layer;
- AWS Prescriptive Guidance ACL;
- dbt Semantic Layer.

Essas fontes inspiram o padrão, não substituem medição do provider real.

---

# 148. COMANDO FINAL AO EXECUTOR

Não construa:

> “o melhor relatório da InfoCap”.

Construa:

> **a semântica executiva da corretora, e faça a InfoCap ser apenas o primeiro tradutor.**

Primeiro:

```text
AUDITE A FONTE
```

Depois:

```text
TRADUZA PARA O DOMÍNIO
```

Depois:

```text
CALCULE UMA VEZ
```

Depois:

```text
EXPLIQUE COM EVIDÊNCIA
```

---

# 149. LEI FINAL

> **Se trocar InfoCap por Quiver ou Segfy exigir reescrever a matemática da corretora, a SPEC-094 falhou.**

O provider conhece o sistema.

O CBIM conhece a corretora.

O Metric Engine conhece a matemática.

O Executive Intelligence conhece o que importa.

Essa é a separação que transforma um relatório em infraestrutura.
