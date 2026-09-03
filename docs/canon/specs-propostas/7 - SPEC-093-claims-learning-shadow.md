# SPEC-093 — CLAIMS LEARNING SHADOW
## O AutoBrokers aprende sinistros com o trabalho humano antes de tentar automatizá-los

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento e revisão pelo Protocolo AutoBrokers AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline de repositório observado:** `19f41eedc5808cf1099ede19d2a88be502854485` (`main`)  
**Branch sugerida:** `feat/spec093-claims-learning-shadow`  
**Autoridades superiores:** SPEC-052, SPEC-053, SPEC-055, SPEC-056, SPEC-059, SPEC-063, Candidate 086, Candidate 090, Candidate 091 e `PROTOCOLO-AUTOBROKERS-AAA.md` v9  
**Autoridades preservadas:** Smith, Work Runs, Attendance/Handoff, Ficha do Atendimento, fontes de verdade da corretora/seguradora, Intelligence Factory, Trajectory/Evidence, Candidate Router, Memory/Knowledge governance, Skill Registry, Tool Gateway, Vault e Atlas  
**Prepara:** futuras Claims Skills/Protocols/Auxiliaries e eventual autonomia delimitada; SPEC-100, 102, 105, 106, 107 e 108  
**Research Pack:** `SPEC-093-claims-learning-shadow-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **Todo sinistro que hoje passa pelas mãos de uma pessoa pode se tornar uma experiência estruturada e auditável: o AutoBrokers observa o que aconteceu, preserva as fontes, reconstrói a trajetória, identifica documentos, perguntas, decisões, esperas, exceções e resultado, e transforma padrões repetidos em candidatos governados — sem abrir, negar, liquidar, negociar ou encerrar sinistro por conta própria.**

```text
SEGURADO / CORRETOR INICIA SINISTRO
        ↓
AUTOBROKERS FAZ INTAKE SEGURO
        ↓
HANDOFF HUMANO COM DOSSIÊ
        ↓
HUMANO CONTINUA DONO DO CASO
        ↓
CLAIMS SHADOW OBSERVA
        ↓
EPISODE + TRAJECTORY + EVIDENCE
        ↓
CLAIM SHADOW PROFILE
        ↓
OUTCOME + EXCEPTIONS + WAIT STATES
        ↓
PATTERN / PROCESS / KNOWLEDGE / GAP
        ↓
SPEC-090 CANDIDATE ROUTER
        ├─ knowledge candidate
        ├─ process/protocol candidate
        ├─ Skill candidate
        ├─ route/tool/connector gap
        ├─ document-requirement candidate
        └─ autonomy-readiness signal
```

**Nunca:**

```text
HUMANO FEZ X
→ MODELO “APRENDEU”
→ PRÓXIMO SINISTRO FAZ X SOZINHO
```

---

# 0.1 A GRANDE IDEIA

Hoje sinistro é corretamente tratado como um domínio em que o AutoBrokers inicia com cuidado e passa para o humano.

O erro seria concluir:

> “então sinistro fica parado até termos coragem de automatizar.”

A decisão correta é:

> **o humano continua operando; o AutoBrokers transforma cada operação humana em evidência para aprender como sinistros realmente funcionam.**

Isso cria:

```text
TRAJETÓRIAS REAIS
+
OUTCOMES REAIS
+
EXCEÇÕES REAIS
+
DOCUMENTOS REAIS
+
VARIAÇÕES POR SEGURADORA
+
CONHECIMENTO TÁCITO HUMANO
```

---

# 0.2 POR QUE “SHADOW”

Shadow significa:

```text
OBSERVA
ESTRUTURA
COMPARA
APRENDE
MEDE
```

Não significa:

```text
DECIDE COBERTURA
ABRE SINISTRO
NEGA SINISTRO
DEFINE CULPA
ALTERA RESERVA
NEGOCIA INDENIZAÇÃO
AUTORIZA PAGAMENTO
ENVIA ACORDO
FECHA SINISTRO
```

A V1 não recebe ferramenta de escrita de sinistro.

Se algum caminho existente permite side effect, o Shadow não recebe essa capability.

---

# 0.3 A AUTORIDADE OPERACIONAL CONTINUA HUMANA

```text
HUMANO
= owner da condução e decisão

AUTOBROKERS
= intake + evidence + shadow + assistive intelligence
```

Eventual automação será futura decisão por microprocesso e risco, não promoção automática da 093.

---

# 0.4 NÃO CRIAR CLAIMS CORE PARALELO

A distinção:

```text
CLAIMS CORE
move e registra o sinistro

CLAIMS INTELLIGENCE
entende evidência e ajuda o handler
```

Nesta SPEC, AutoBrokers é:

```text
INTELLIGENCE OVERLAY
```

Não vamos recriar o sistema da corretora ou da seguradora.

Se já existe sistema de sinistros, ele continua source-of-truth. Se não existe, o warm-up mede onde o humano registra hoje.

---

# 0.5 NÃO DUPLICAR A SPEC-090

A 090 já cria:

```text
Raw Event
Episode
Trajectory
Outcome
Evidence
Scope Resolver
Candidate Router
```

A 093 é especialização de domínio:

```text
Claim Episode
= Episode + claim semantics

Claim Trajectory
= Trajectory + claim profile

Claim Evidence
= Evidence + claim taxonomy
```

Proibido criar por hábito:

- `claim_events_v2`;
- outro Claim Trajectory authority;
- outro Learning Fabric;
- outro Candidate Router;
- outro Memory Provider.

Uma projeção/materialized view específica só pode nascer depois de necessidade real de consulta/performance.

---

# 0.6 DREAMS — DECISÃO CONGELADA PARA A SPEC-106

A SPEC-106 não criará:

```text
Dream Agent
Dream Brain
Dream Memory
Dream RAG
Dream Candidate DB
```

Ela será uma fase do MESMO ciclo:

```text
TRAJECTORIES
+
CLAIM SHADOW PROFILES
+
MEMORIES
+
KNOWLEDGE
+
PROTOCOL EXECUTION RECORDS
+
CANDIDATES
        ↓
SPEC-106 DREAMS
        ↓
MERGE / SUPERSEDE / SYNTHESIZE / RECONFIRM
        ↓
NOVOS CANDIDATES
        ↓
MESMAS AUTORIDADES
```

Para Claims:

```text
Claim Trajectory
→ Dreams
→ Claim Process Candidate
→ SPEC-091/100
```

ou:

```text
Claim Trajectory
→ Dreams
→ Knowledge Candidate
→ SPEC-102
```

Nunca:

```text
Dreams → comportamento live de sinistro
```

sem Protocol/Skill/AAA/publisher correspondente.

---

# 1. ESTADO ATUAL CONFIRMADO

## 1.1 O atendente já sabe iniciar o sinistro

O prompt atual manda:

- tratar colisão/roubo/incêndio com calma;
- entender o que houve;
- quando;
- onde;
- vítimas;
- terceiros;
- fotos quando possível;
- segurança/emergência primeiro;
- depois passar para equipe de sinistros;
- entregar dossiê completo;
- evitar que o cliente repita tudo.

Preservar.

## 1.2 Handoff já existe

Há hoje:

- Human Handoff Tool;
- estados de atendimento;
- destinos de suporte;
- watchdog;
- Ficha do Atendimento;
- dossiê;
- `claimed_by`;
- timeline;
- anexos;
- resumo destilado.

A 093 conecta **aprendizado** ao handoff. Não cria outro handoff.

## 1.3 A Ficha do Atendimento é base

Ela já agrega:

```text
conversa
mensagens
anexos
dispatch
espelho da seguradora
attendance_sessions
InfoCap read-only
dossiê
timeline
apólice
```

Não reimplementar.

## 1.4 InfoCap não pode ser presumida como Claims Core

No mapa canônico medido em julho de 2026, `/sinistro` estava negado 403 ao perfil disponível.

A execução da 093 testa novamente em modo read-only.

## 1.5 O domínio Claims ainda é superficial

Há referências semânticas a sinistro no backend, mas não há evidência de um lifecycle canônico completo de Claims no AutoBrokers.

A 093 constrói primeiro o contrato de observação.

---

# 2. REFERÊNCIAS EXTERNAS — DIREÇÃO DO MERCADO

## Guidewire
AI no fluxo para resumir, recuperar policy context, recomendar e preparar; humano mantém julgamento em casos complexos.

## Sprout.ai
Claims Decision Intelligence como camada que lê evidência, interpreta contexto, identifica fatos críticos e devolve insight/audit trail ao claims core.

## Snapsheet
Summaries, QA, drafts, recommendations, signals e análise documental integrados ao workflow, com tarefa humana quando oversight é necessário.

## Shift Technology
ARISE descreve níveis explícitos de autonomia e oversight proporcional.

A conclusão para AutoBrokers:

> **começar aprendendo e assistindo; subir autonomia somente por domínio comprovado.**

---

# 3. ESCADA DE AUTONOMIA AUTOBROKERS PARA CLAIMS

## C0 — OBSERVE
Zero decisão; zero side effect. **Obrigatório nesta SPEC.**

## C1 — ASSIST
Read-only:
- resumo;
- timeline;
- checklist evidenciado;
- faltantes;
- policy evidence;
- source links.

A 093 pode ativar C1 onde for seguro.

## C2 — RECOMMEND
Futuro. Sugere próximo passo; humano decide/executa.

## C3 — PREPARE / INITIATE WITH APPROVAL
Futuro. Preenche/prepara; humano autoriza side effect.

## C4 — BOUNDED EXECUTION
Futuro. Straight-through estreito, provado e low-risk.

## C5 — ADVANCED AUTONOMY
Não é objetivo atual.

> **A 093 não promove automaticamente nenhum claim type para C2+.**

---

# 4. CLAIM SHADOW PROFILE — CONTRATO LÓGICO

Extensão da Trajectory da 090:

```json
{
  "schema": "claim_shadow_v1",
  "trajectory_ref": "...",
  "company_id": "...",

  "claim_identity": {
    "source_claim_ref": null,
    "external_protocol": null,
    "identity_confidence": 0.0
  },

  "classification": {
    "line": "auto",
    "claim_type": "collision",
    "coverage_context": null,
    "complexity": "unknown",
    "risk_class": "high"
  },

  "incident": {
    "occurred_at": null,
    "reported_at": null,
    "location_ref": null,
    "victims_reported": null,
    "third_parties_reported": null
  },

  "policy_refs": [],
  "actors": [],

  "documents": {
    "requested": [],
    "received": [],
    "missing": [],
    "source": []
  },

  "human_work": {
    "handler_refs": [],
    "actions": [],
    "decisions": [],
    "handoffs": []
  },

  "external_work": {
    "insurer": null,
    "channel": null,
    "portal": null,
    "events": []
  },

  "waiting": [],

  "outcome": {
    "status": "unknown",
    "source_refs": []
  },

  "evidence_refs": [],
  "quality_flags": [],
  "learning_flags": []
}
```

É projeção derivada, não source-of-truth.

---

# 5. CLAIM IDENTITY

Prioridade:

1. claim number/protocol authoritative;
2. insurer source identifier;
3. internal case id;
4. source links;
5. composite fingerprint com confidence;
6. confirmação humana.

Nunca juntar dois sinistros somente por similaridade semântica.

---

# 6. CLAIM CLASSIFICATION

Taxonomia inicial extensível:

```text
auto_collision
auto_theft
auto_fire
auto_weather
auto_glass_or_repair
property_water
property_fire
property_theft
liability
life
personal_accident
other
unknown
```

Separar explicitamente:

```text
ASSISTANCE_NOT_CLAIM
```

Guincho, bateria e pneu não viram sinistro só porque são seguro.

---

# 7. RISK CLASSIFICATION

## LOW
Organização, indexação, resumo e completeness.

## MEDIUM
Process recommendation, deadline alert, procedure suggestion.

## HIGH
Coverage, liability, fraud, bodily injury, medical, denial, settlement, payment/reserve.

HIGH não recebe autonomia por volume.

---

# 8. FNOL / INTAKE

Normalizar quando cabível:

```text
what happened
incident date/time
location
safety emergency
victims/injuries
third parties
vehicle/property
photos/documents
policy/customer identity
contact
```

Não virar questionário fixo.

---

# 8.1 SAFETY FIRST

Vítimas, incêndio, fumaça ou perigo físico:

```text
segurança/emergência primeiro
```

depois administração.

---

# 9. DOSSIÊ DE HANDOFF

Reusar o contract existente, estendendo se preciso.

Dossiê:

```text
cliente
apólice
ocorrência
quando/onde
vítimas?
terceiros?
dados já coletados
anexos
documentos recebidos
faltantes conhecidos
fontes
estado conhecido
```

Cliente não repete.

---

# 10. HUMAN ACTION LEDGER

Aprender do que humano realmente faz, quando há evidência:

```text
consulted_policy
asked_document
sent_document
called_insurer
opened_portal
submitted_form
received_protocol
requested_inspection
scheduled_vendor
updated_status
asked_clarification
escalated
closed
```

Se não há telemetria:

```text
UNKNOWN
```

Não inferir ação física a partir de texto.

---

# 11. DECISION CHECKPOINTS

Registrar decisões observáveis:

```text
requested_more_docs
accepted_dossier
escalated
chose_channel
requested_inspection
changed_destination
recommended_next_step
```

Não armazenar chain-of-thought.

Razão explícita/documentada pode virar Evidence.

---

# 12. DOCUMENT INTELLIGENCE

Estruturar:

```text
document_type
requested_by
requested_at
received_at
validated?
source
reason_if_known
claim_type
insurer
product
version/effective period
```

## Regra
“Humano pediu X” prova apenas que o humano pediu X.

Não prova requisito universal da seguradora.

---

# 13. POLICY CONTEXT

Pode ligar:

- InfoCap;
- apólice;
- condições;
- endosso.

Guardar evidence de:

```text
coverage
exclusion
franchise
limit
effective version
source page/ref
```

Mas decisão de cobertura permanece humana nesta SPEC.

---

# 14. TEMPORALIDADE REGULATÓRIA

A Lei nº 15.040/2024 entrou em vigor em dezembro de 2025.

A Resolução CNSP nº 496/2026 foi publicada em agosto de 2026 e possui aplicação/transição própria, inclusive regras que passarão a ser obrigatórias para contratos abrangidos a partir de 2027.

Portanto:

> **não hardcode prazo regulatório como verdade universal de todo sinistro.**

Regra operacional regulatória precisa:

```text
source
published_at
effective_from
contract applicability
line/product
validity
```

---

# 15. WAIT STATE MODEL

```text
WAITING_CUSTOMER
WAITING_DOCUMENT
WAITING_INSURER
WAITING_INSPECTION
WAITING_VENDOR
WAITING_INTERNAL
WAITING_DECISION
WAITING_PAYMENT
UNKNOWN
```

Cada espera:

```text
started_at
ended_at
source
reason
next_action_owner
```

---

# 16. POR QUE WAIT STATES IMPORTAM

Decompõem cycle time:

```text
cliente
seguradora
documentos
oficina/perito
interno
decisão
```

Assim o sistema descobre onde trava de verdade.

---

# 17. CLAIM OUTCOME

```text
reported
in_progress
resolved
paid
denied
cancelled
withdrawn
closed
unknown
```

Precisa de source.

`conversation closed` não é `resolved`.

---

# 18. OUTCOME STRENGTH

```text
O0 unknown
O1 human-stated
O2 customer/handler-confirmed
O3 insurer/system status
O4 transaction/document proof
```

---

# 19. CLAIMS EVIDENCE PACK

Deve conseguir reunir:

```text
claim identity
policy refs
incident facts
documents
timeline
human actions
insurer actions
decisions observed
outcome
sources
conflicts
unknowns
```

---

# 20. CLAIM TRAJECTORY

```text
INCIDENT
↓
INTAKE
↓
HANDOFF
↓
HUMAN ACTION
↓
DOCUMENT REQUEST
↓
WAIT
↓
INSURER ACTION
↓
HUMAN DECISION
↓
...
↓
OUTCOME
```

É o principal ativo da SPEC.

---

# 21. O QUE O SHADOW PODE APRENDER

## Process
Passos, branches, esperas e handoffs.

## Documents
O que pedem, quando e de onde vem.

## Insurer behavior
Canal, status, resposta, friction.

## Human work
Perguntas, checks, exceções e workaround.

## Product gaps
Connector, data, tool, permission ou Skill faltante.

## Customer experience
Perguntas repetidas, docs repetidos e pontos de confusão.

---

# 22. O QUE NÃO VIRA GLOBAL DIRETAMENTE

- prontuário/medical data;
- lesão ligada a pessoa;
- claim amount ligado ao cliente;
- CPF;
- placa;
- endereço;
- telefone;
- fotos;
- terceiros;
- negotiation;
- fraud suspicion;
- legal strategy;
- private brokerage policy.

---

# 23. GLOBAL CLAIMS LEARNING

Somente abstração sanitizada.

Exemplo aceitável como **candidate**:

```text
“Insurer X pediu documento Y repetidamente
em claims independentes deste tipo”
```

Nunca raw transcript.

---

# 24. CROSS-TENANT

Aplicar 090:

```text
sanitized abstraction
+
independent source count
+
anonymized tenant count
```

---

# 25. CLAIM PROCESS CANDIDATE

Padrão repetido:

```text
FNOL → docs → portal → inspection → approval
```

gera:

```text
PROCESS_CANDIDATE → SPEC-091
```

---

# 26. CLAIM SKILL CANDIDATE

Microprocesso estável:

```text
“montar dossiê de aviso de sinistro”
```

pode gerar:

```text
SKILL_CANDIDATE → SPEC-100
```

---

# 27. CONNECTOR / CAPABILITY GAP

Exemplos:

```text
InfoCap claims unavailable
claim status source missing
portal read missing
email-only evidence
```

vira Gap governado.

---

# 28. HUMAN WORKAROUND

Exemplo:

```text
tela A → planilha → email → portal
```

é `AUTOMATION_OPPORTUNITY`.

Não é autorização de automação.

---

# 29. CUSTOMER COMMUNICATION LEARNING

Pode detectar:

- perguntas confusas;
- melhor ordem de intake;
- status que reduz cobrança do cliente;
- explicações recorrentes.

Gera Candidate.

Não altera prompt automaticamente.

---

# 30. C1 — OUTPUT IMEDIATO PARA HUMANO

Permitido:

- resumo evidenciado;
- timeline;
- document checklist;
- missing data;
- latest official status;
- source links;
- waiting clock.

Não permitido:

- “negue”;
- “pague”;
- “culpado”;
- “fraude”;
- “acordo recomendado”.

---

# 31. QUALITY OF HUMAN WORK

Foco em processo/case, não ranking punitivo de funcionários.

Pode detectar:

```text
missing step
contradiction
missing document
stale case
```

Não rotular pessoa como “boa/ruim” por inferência.

---

# 32. AUTONOMY READINESS SCORE

Score DIAGNÓSTICO, nunca permissão.

Dimensões:

```text
process consistency
evidence volume
independent case count
outcome reliability
document stability
exception rate
human intervention rate
insurer/channel stability
regulatory stability
reversibility
financial/legal risk
sensitive-data risk
eval performance
drift rate
```

Faixas propostas:

```text
0–39   OBSERVE ONLY
40–59  ASSIST CANDIDATE
60–74  RECOMMEND CANDIDATE
75–89  PREPARE CANDIDATE
90–100 BOUNDED EXECUTION CANDIDATE
```

Mesmo 100/100 exige futura SPEC + AAA + Trust Gate.

Hard blockers são não-compensáveis.

---

# 33. EXEMPLO DE READINESS

```text
AUTO · COLISÃO SEM VÍTIMA · INSURER X

cases observed .......... 143
same core process ........ 91%
documents stable ......... 88%
exception rate ........... 7%
outcome known ............ 94%
human judgment points .... 2
regulatory risk .......... medium
write action ............. required

diagnostic ............... 78/100
hard blocker ............. coverage + submission approval

result:
PREPARE CANDIDATE
NOT AUTONOMY
```

---

# 34. CASO COMPLEXO

```text
AUTO · COLISÃO COM LESÃO

volume ................... alto
process consistency ...... alta

medical/legal risk ....... CRITICAL
liability judgment ....... REQUIRED
settlement ............... POSSIBLE

result:
HUMAN-GOVERNED
```

Volume não remove blocker.

---

# 35. ARISE COMO REFERÊNCIA

A lição do framework ARISE é adotada:

> autonomia deve ter nível explícito e oversight proporcional.

Não copiamos claims de marketing nem métricas do fornecedor como garantia nossa.

---

# 36. CORPUS BUILDER

Localizar histórico autorizado em:

- conversations/messages;
- attendance sessions;
- attachments;
- handoffs;
- InfoCap atendimentos;
- claims system, se existir;
- email/docs, se conectados.

Não usar palavra `sinistro` como detector único.

---

# 37. GOLD CORPUS

Rotular:

```text
claim
assistance
policy_question
billing
renewal
other
```

Claims:

```text
claim_type
risk
stage
outcome_known
```

Isso vira eval.

---

# 38. EVENT CAPTURE

Usar envelope 090.

Hot path:

```text
capture + queue
```

Enrichment pesado async.

Não degradar atendimento.

---

# 39. BACKFILL VS LIVE

Historical:

```text
Work Run
```

Live:

```text
incremental
```

Não reprocessar tudo diariamente.

---

# 40. PRIVACY CLASS

Claims são high-sensitivity por default por potencial de:

- saúde;
- acidente;
- documentos;
- terceiros;
- imagens;
- localização;
- valores.

---

# 41. REDACTION / ACL

Antes de candidate global:

- PII;
- vehicle identity;
- medical identity;
- address;
- contact;
- claim number;
- tenant identity.

Company ownership não significa visibility all-company.

---

# 42. FRAUD / LIABILITY / RESERVE / PAYMENT

Pode observar fatos de processo quando autorizado.

Não decide, acusa, recomenda valor ou altera estado.

---

# 43. DEADLINES

Pode capturar prazo vindo de fonte autoritativa.

Pode mostrar a fonte.

Não inventa prazo por “conhecimento geral”.

---

# 44. CLAIMS OPERATIONS ANALYTICS

Mesmo sem autonomia:

```text
volume
claim type
insurer
line
time to first human
time waiting customer
time waiting insurer
time waiting docs
cycle time
handoffs
rework
repeat requests
missing-doc rate
unknown-outcome rate
```

---

# 45. INSURER FRICTION MAP

Por insurer + claim type:

```text
docs requested
extra-doc rate
waiting time
contacts
channel/portal
rework
exceptions
```

Tenant-private primeiro.

Global apenas agregado/sanitizado via 090.

---

# 46. TACIT KNOWLEDGE DISCOVERY

Padrão:

```text
“quando X acontece, handler sempre verifica Y”
```

vira Candidate, não policy automática.

---

# 47. C1 QUALITY SUPPORT

Pode identificar:

- duplicate request;
- missing attachment;
- inconsistent dates;
- stale case;
- no source for status;
- customer waiting.

Sem julgar mérito da indenização.

---

# 48. SUMMARY FORMAT

```text
Incident
Policy
People/third parties
Documents
Actions
Pending
Timeline
Latest official status
Unknowns
```

Cada seção source-backed.

---

# 49. HUMAN FEEDBACK

Permitir:

```text
correto
errado
faltou
não se aplica
```

para summaries/checklists.

Gera evidence/correction.

---

# 50. DREAMS HOOK PARA 106

Cada Claim Trajectory deixa flags:

```text
dream_eligible
novel_pattern
contradiction
repeated_process
high_value_exception
failed_retrieval
human_correction
```

A 106 lê a MESMA estrutura.

Não existe `dream_claims`.

---

# 51. TRAJECTORY/REPLAY PARA 105

Deixar identifiers + evidence suficientes para:

- replay;
- compare;
- audit;
- eval.

105 adiciona Replay/Fork, não 093.

---

# 52. META-HARNESS PARA 108

Instrumentar desde já:

```text
capture rate
summary accuracy
document completeness accuracy
PII leakage
candidate precision
drift
cost
```

---

# 53. TOOL GATE

Shadow profile:

```text
READ
SUMMARIZE
CLASSIFY
EXTRACT
COMPARE
```

Denied:

```text
claim submit
claim update
claim close
payment
settlement
outbound side effect
portal write
```

Hard deny via Capability/Tool Gateway sempre que aplicável.

---

# 54. OPERATOR RESUME PACK

Reusar Candidate 086.

Claim-specific extension:

```text
incident
policy
docs
missing
attachments
latest state
source refs
```

Não criar `Claim Resume Pack v2`.

---

# 55. UI MÍNIMA

Na Ficha/case surface, quando claim:

```text
Resumo do sinistro
Timeline
Documentos
Pendências
Status oficial
Fontes
```

Não criar módulo decorativo gigante.

---

# 56. ADMIN SHADOW VIEW

```text
claims detected
profiles built
unknown classifications
outcome coverage
candidates
PII/ACL blocks
errors
cost
```

---

# 57. VALUE BEFORE AUTONOMY

C0/C1 já entrega:

- menos repetição;
- dossiê melhor;
- documentos organizados;
- cronologia;
- espera mensurável;
- processo visível;
- gaps visíveis.

---

# 58. AUTOMATION READINESS BOARD

Admin-only inicialmente.

Por family/insurer/line/process segment:

```text
cases
consistency
exceptions
outcome confidence
risk blockers
candidate level
```

Rótulo:

```text
READINESS CANDIDATE
```

não “AUTOMATIZE”.

---

# 59. PROCESS / DOCUMENT ENTROPY

Medir variação de caminhos e docs.

Alta entropy:

```text
observe / understand branches
```

antes de automatizar.

---

# 60. HUMAN TOUCH DENSITY

```text
human actions
human decisions
human exceptions
per case
```

Ajuda separar operação repetitiva de julgamento.

---

# 61. FIRST-PASS DOSSIER COMPLETENESS

Métrica prioritária:

> quanto do caso chega completo ao humano na primeira transferência?

---

# 62. SOURCE-OF-TRUTH RULE

Para estado mutável:

```text
claims system / insurer / authoritative source
>
Claim Shadow
```

Shadow não substitui status vivo.

---

# 63. DATA QUALITY

Campos derivados importantes devem carregar:

```text
value
source_ref
confidence
observed_at
```

---

# 64. FIELD CONFLICT

Cliente diz A, humano diz B, sistema diz C:

```text
CONFLICT
```

Não resolver silenciosamente.

---

# 65. NO RETROACTIVE HALLUCINATION

Backfill nunca preenche step ausente porque “normalmente é assim”.

Missing = missing.

---

# 66. MODEL ROUTING

Determinístico primeiro.

Modelo barato/balanced para classificação simples.

Modelo forte para:

- chronology complexa;
- semantic contradiction;
- ambiguous claim type;
- document relation.

---

# 67. EXISTING DOCUMENT PIPELINE

Usar DocumentService/Docling/vision atual.

Não construir OCR separado.

---

# 68. IMAGE DAMAGE / FRAUD AI

São future capability candidates.

Não instalar Tractable-like vision ou fraud engine nesta SPEC.

---

# 69. WORK RUNS

Backfill/deep analysis = Work Run.

Simple incremental enrichment = worker/background.

No Work Run per message.

---

# 70. COST

Medir:

```text
per claim
per enrichment
per model
per tenant
```

O Shadow não pode ser economicamente invisível.


---

# 71. BLOCK 0 — FORENSE READ-ONLY OBRIGATÓRIA

Antes de qualquer edição:

1. registrar HEAD e branch;
2. mapear todos os usos `sinistro/claim`;
3. medir conversas claim-related;
4. medir handoffs por reason;
5. medir destinos humanos de sinistro;
6. medir anexos;
7. medir `attendance_sessions`;
8. medir Ficha do Atendimento;
9. medir contract do dossier;
10. testar InfoCap `/sinistro` novamente, read-only;
11. verificar Quiver/Segfy/outro claims source;
12. descobrir onde handlers registram claim hoje;
13. mapear WhatsApp/e-mail/portal usados;
14. mapear documentos;
15. medir policy lookup;
16. mapear Redaction Service;
17. mapear PII/sensitive-data controls;
18. mapear RLS/ACL;
19. mapear roles/claims team;
20. confirmar contratos de Trajectory da 090 executada;
21. confirmar Protocol/Candidate contracts da 091;
22. medir current regulatory knowledge;
23. coletar amostra real/anônima de claims;
24. identificar tenants técnicos/teste;
25. medir latency/cost atuais.

---

# 72. WARM-UP — AFIRMAÇÕES PARA REFUTAR

## P1 — “AutoBrokers já tem Claims Core completo.”
Provavelmente falsa.

## P2 — “InfoCap `/sinistro` está disponível.”
Era falso em julho. Medir agora.

## P3 — “Todo handoff de sinistro termina com outcome conhecido.”
Provar.

## P4 — “Sinistro e assistência estão perfeitamente separados.”
Provar.

## P5 — “Mensagem humana descreve todas as ações que o humano fez.”
Falsa.

## P6 — “Documento pedido num caso é requisito universal da seguradora.”
Falsa.

## P7 — “30 dias é deadline universal de todo sinistro atual.”
Falsa.

## P8 — “Case closed = claim resolved.”
Falsa.

## P9 — “100 casos iguais autorizam automação.”
Falsa.

## P10 — “Shadow precisa de tool de escrita para aprender.”
Falsa.

## P11 — “Mascarar nome basta para globalizar todo dado de claim.”
Falsa.

## P12 — “Read-only analysis é baixo risco em qualquer conteúdo de claim.”
Falsa: saúde/terceiros/PII podem ser sensíveis.

## P13 — “Score 95/100 autoriza autonomia.”
Falsa.

## P14 — “Dreams pode consolidar Claims e publicar sozinho.”
Falsa.

## P15 — “O que você ainda NÃO entendeu do domínio Claims atual?”
Resposta “nada” reprova.

---

# 73. BLOCO A — CLAIM DETECTOR + GOLD CORPUS

Entregar:

- claim vs assistance detector;
- taxonomy;
- gold corpus;
- classification eval;
- source inventory.

### Gate A

- false positive não causa side effect;
- UNKNOWN é válido;
- precisão/recall medidos;
- claim e assistência não se misturam silenciosamente.

---

# 74. BLOCO B — CLAIM SHADOW PROFILE

Implementar como extensão/projeção da 090.

### Gate B

Um caso real/anônimo precisa reconstruir:

- incident;
- policy refs;
- docs;
- human work;
- external work;
- waits;
- outcome;
- evidence;
- unknowns.

---

# 75. BLOCO C — HANDOFF / DOSSIER INTEGRATION

Reusar o handoff existente.

### Gate C

Humano recebe:

```text
o que sabemos
+
o que falta
+
fontes
```

e o segurado não precisa repetir o que já informou.

---

# 76. BLOCO D — WAIT / OUTCOME / HUMAN ACTION

Capturar timeline operacional.

### Gate D

- closure não vira success;
- action sem evidência fica UNKNOWN;
- waiting owner está explícito.

---

# 77. BLOCO E — LEARNING ROUTER

Detectar e encaminhar:

```text
process
document pattern
knowledge
Skill opportunity
connector gap
capability gap
communication pattern
```

### Gate E

Tudo passa pelo Candidate Router da 090.

Zero direct publish.

---

# 78. BLOCO F — C1 HUMAN ASSIST

Somente evidence-based:

- summary;
- timeline;
- docs;
- missing;
- latest source status;
- source links.

### Gate F

Nenhuma hidden recommendation de cobertura/liability/denial/payment.

---

# 79. BLOCO G — AUTONOMY READINESS ANALYTICS

Criar diagnostic score + hard blockers.

### Gate G

Alterar score para 100 manualmente NÃO habilita nenhuma capability.

---

# 80. BLOCO H — HISTORICAL BACKFILL

Run controlado:

```text
inventory
→ sample
→ classify
→ batch
→ trajectories
→ profiles
→ candidates
→ report
```

### Gate H

- idempotent;
- resumable;
- no duplicates;
- no PII global.

---

# 81. BLOCO I — LIVE SHADOW

Incremental após o atendimento/evento.

### Gate I

- hot path intacto;
- no material TTFT regression;
- error in Shadow cannot stop customer assistance.

---

# 82. BLOCO J — OBSERVABILITY + CANARY

Pilotos autorizados.

Medir:

- capture;
- accuracy;
- unknowns;
- outcome coverage;
- leaks;
- cost.

No autonomy.

---

# 83. RED TEAM — MISSÃO

> **Fazer o AutoBrokers aprender uma regra errada de sinistro, vazar dado sensível ou avançar autonomia sem autorização — enquanto os testes superficiais continuam verdes.**

Ataques obrigatórios:

1. handler humano erra;
2. cliente relata fato incorreto;
3. seguradora muda documento;
4. dois claims do mesmo cliente no mesmo dia;
5. assistência confundida com claim;
6. documento médico em source privado;
7. terceiro com PII;
8. suspeita de fraude;
9. prazo legal velho;
10. regra futura aplicada antes da vigência;
11. case closed interpretado resolved;
12. denial de um caso tratado como regra universal;
13. duplicate backfill;
14. same source contado como independente;
15. LLM inventa step ausente;
16. Shadow recebe write tool;
17. candidate global contém tenant;
18. Dreams publica sozinho;
19. readiness score ativa automação;
20. corpus enviesado por um handler;
21. workaround aprendido como policy;
22. merge errado de claim identity;
23. stale policy memory vence source authoritative;
24. attachment não chegou, mas summary diz recebido;
25. claim de teste/synthetic contamina produção.

---

# 84. MUTATIONS OBRIGATÓRIAS

## M1
Adicionar `portal.execute` ao Shadow.

**FAIL.**

## M2
Resposta do handler recebe Ground Truth automaticamente.

**FAIL.**

## M3
Conversation closed = resolved claim.

**FAIL.**

## M4
Candidate global contém claim/customer identifier.

**FAIL.**

## M5
Claims merge somente por similaridade semântica.

**FAIL.**

## M6
Hardcode de prazo regulatório universal.

**FAIL.**

## M7
Medical data entra em global memory.

**FAIL.**

## M8
Mesma fonte 20 vezes = 20 evidências independentes.

**FAIL.**

## M9
Readiness 95 habilita action.

**FAIL.**

## M10
Dream output publica diretamente.

**FAIL.**

## M11
Claim Shadow cria Candidate Router paralelo.

**FAIL.**

## M12
Claim Shadow cria Trajectory authority paralela.

**FAIL.**

## M13
Backfill inventa step missing baseado em padrão.

**FAIL.**

## M14
Assistance classificada como claim e globalizada.

**FAIL.**

## M15
Derived evidence perde source ACL.

**FAIL.**

## M16
Coverage “provável” vira Coverage Confirmed.

**FAIL.**

## M17
Regulatory candidate sem effective date é aplicado.

**FAIL.**

## M18
Synthetic tenant participa de autonomy readiness de produção.

**FAIL.**

---

# 85. TEST MATRIX — CLAIM VS ASSISTANCE

- colisão;
- furto/roubo;
- incêndio;
- alagamento;
- vidros;
- guincho;
- bateria;
- pneu;
- dúvida de cobertura;
- “bati o carro, isso cobre?” sem aviso de sinistro;
- terceiro entrando em contato;
- evento desconhecido.

---

# 86. TEST MATRIX — DOCUMENTS

- requested + received;
- requested + missing;
- duplicate;
- wrong document;
- document requested by handler only;
- official insurer checklist;
- checklist changed;
- sensitive medical document;
- document expired;
- attachment corrupt/unreadable.

---

# 87. TEST MATRIX — OUTCOME

- insurer protocol;
- paid;
- denied;
- customer withdraws;
- transferred;
- closed unknown;
- stale open;
- handler says done, system disagrees;
- insurer status changes after closure.

---

# 88. TEST MATRIX — TEMPORAL / REGULATORY

- regra vigente;
- regra substituída;
- future-effective regulation;
- transitional contract;
- policy issued before/after rule;
- source with ambiguous effective date;
- official source supersedes old Knowledge Card.

---

# 89. TEST MATRIX — PRIVACY

- customer PII;
- third-party PII;
- health/medical;
- vehicle identifiers;
- address;
- private Drive/email;
- manager-only case;
- global abstraction;
- cross-tenant candidate.

---

# 90. TEST MATRIX — READINESS

- many consistent simple cases;
- many inconsistent cases;
- low sample;
- one handler only;
- one insurer only;
- high risk;
- high score + hard blocker;
- process drift;
- missing outcomes;
- new regulation.

---

# 91. PERFORMANCE / SCALE

Simular e medir corpus representativo:

```text
10k claim-related messages
1k Episodes
hundreds of Claim Trajectories
```

Sem O(n²) global.

Candidate comparison usa relevant neighborhood.

---

# 92. CLAIMS SHADOW OBSERVABILITY

Métricas técnicas:

```text
claims_detected
shadow_profiles_created
profile_completeness
claim_assistance_confusion
unknown_actor_rate
unknown_outcome_rate
evidence_coverage
document_pattern_candidates
process_candidates
connector_gaps
pii_blocks
acl_blocks
candidate_rejections
cost_per_claim
latency_added_to_hot_path
```

---

# 93. QUALITY KPIs

```text
classification_precision
classification_recall
field_extraction_accuracy
timeline_accuracy
document_completeness_precision
outcome_accuracy
source_attribution_accuracy
pii_leak_rate
cross_tenant_leak_rate
```

Leak rates target:

```text
0 tolerated
```

---

# 94. BUSINESS KPIs

Sem autonomia:

```text
time_to_human_handoff
repeat_question_rate
first_pass_dossier_completeness
time_spent_searching_docs
claim_aging_by_wait_owner
rework_rate
unknown_outcome_rate
```

---

# 95. LEARNING KPIs

```text
new_process_candidates
new_document_candidates
new_knowledge_candidates
new_capability_gaps
new_skill_candidates
cases_benefiting_from_learned_checklist
```

Não medir sucesso por número de memories.

---

# 96. SOURCE OF TRUTH VS SHADOW

Sempre:

```text
authoritative current source
>
derived Claim Shadow
```

Se há divergência:

```text
CONFLICT
```

e a divergência vira Signal.

---

# 97. CLAIMS GLOBAL KNOWLEDGE

Regra:

```text
private evidence
→ sanitize
→ abstract
→ candidate
→ governance
```

Nunca:

```text
private evidence
→ global vector
```

---

# 98. CLAIMS MEMORY

Case facts:

```text
CASE / source of truth
```

Company operational patterns:

```text
COMPANY candidate
```

Global insurer patterns:

```text
GLOBAL candidate
```

Personal handler preference:

```text
USER candidate
```

Usar escopo 090/102.

---

# 99. NO AGENT-SPECIFIC CLAIM TRUTH

Um Claims Agent futuro não terá “memória própria” concorrente.

Ele acessa contexto autorizado do mesmo brain.

---

# 100. CLAIMS PROTOCOL FACTORY HANDOFF

Quando process pattern fica forte:

```text
PROCESS_CANDIDATE
→ engineering/domain protocol candidate
→ SPEC-091
```

Exemplo:

```text
claims.prepare-fnol-dossier
```

Ainda não significa publicar Skill.

---

# 101. CLAIMS SKILL FACTORY HANDOFF

Depois da SPEC-100:

```text
validated protocol/process
→ Skill candidate
→ eval
→ release
```

Tool Gateway decide capacidades.

---

# 102. CLAIMS AUXILIARY FUTURE

Não criar “Auxiliar de Sinistros” genérico agora.

No futuro pode haver:

- acompanhamento documental;
- status monitor;
- claims dossier assistant;
- bounded simple-claim worker.

Cada um baseado em evidência.

---

# 103. CLAIMS AUTOMATION FUTURE — OPERATIONAL DESIGN DOMAIN

Qualquer C4 futuro deve definir ODD:

```text
insurer
line
product
claim type
coverage context
value/risk bounds
document completeness
channel
regulatory version
exceptions
```

Fora do ODD:

```text
HUMAN
```

---

# 104. AUTONOMY PROMOTION CONTRACT

Futura SPEC só pode propor C2+ se existir:

- enough verified trajectories;
- outcome coverage;
- process stability;
- eval corpus;
- exception map;
- risk model;
- Trust Gate;
- rollback;
- monitoring;
- human escalation.

---

# 105. NO “SELF-EARNING AUTONOMY”

O sistema não ganha poder porque aprendeu.

Learning e authorization são separados.

```text
LEARNING
≠
PERMISSION
```

---

# 106. REGULATORY / LEGAL CHANGES

Research Intelligence monitora sources.

Claims Shadow consome knowledge publicado.

Não cria outro legal monitor.

---

# 107. 2026 BRAZIL TRANSITION — DESIGN CONSEQUENCE

A regulação atual demonstra por que claims knowledge precisa ser temporal:

```text
a regra pode ser publicada hoje
mas só ser obrigatória para certos contratos amanhã
```

Portanto candidate deve carregar applicability, não só texto.

---

# 108. HUMAN-GOVERNED DESIGN

A direção do mercado que interessa ao AutoBrokers:

```text
AI handles preparation / evidence / repetitive work
human handles judgment / exceptions / empathy / authority
```

Até prova em contrário por microdomain.

---

# 109. CUSTOMER EXPERIENCE

Melhor claims AI não é só “mais rápida”.

Precisa reduzir:

- repeated info;
- uncertainty;
- silent waiting;
- conflicting messages;
- missing documents.

A 093 mede isso.

---

# 110. CLAIM STATUS EXPLANATION

C1 pode explicar:

```text
“aguardando documento X”
```

se source prova.

Não:

```text
“seguradora está atrasada”
```

sem evidence e applicable SLA.

---

# 111. CONTRADICTION DETECTION

Exemplos:

- incident date differs;
- vehicle differs;
- document says one thing, message another;
- handler note conflicts with insurer status.

Output:

```text
CONFLICT
```

Não accusation.

---

# 112. CLAIMS QA SUPPORT

Read-only audit can surface:

```text
missing_source
missing_doc
missing_status
stale_wait
duplicate_request
inconsistent_fact
```

Essa é uma futura base forte para C1.

---

# 113. CLAIMS RESEARCH GAP

Quando procedure unknown:

```text
Research Request
```

via SPEC-060.

Resultado:

```text
Evidence Pack
→ Candidate
```

Não web search livre dentro do Shadow.

---

# 114. CANDIDATE PRIORITY

Priorizar por:

```text
frequency
tenant reach anonymized
impact
confidence
process stability
risk
recency
```

High risk aumenta review priority, não auto-publication.

---

# 115. CLAIMS DREAMS SELECTION

Na 106, selecionar para Dreams:

- repeated patterns;
- contradictions;
- human corrections;
- stale candidates;
- process drift;
- high-value exceptions;
- repeated document requests.

Não rodar “todo claim toda noite”.

---

# 116. CLAIMS DREAMS OUTPUT

A 106 só devolve:

```text
MERGE proposal
SUPERSEDE proposal
SYNTHESIS candidate
RECONFIRM signal
GAP candidate
PROTOCOL candidate
SKILL candidate
```

Tudo volta às autoridades.

---

# 117. CLAIMS DREAMS NON-GOALS

Proibido:

- autoalterar active Skill;
- autoalterar Soul;
- autoalterar route;
- auto-publicar Knowledge;
- autoatribuir capability;
- autoexecutar claim.

---

# 118. CLAIMS + SECOND BRAIN

SPEC-102 poderá mostrar, permission-aware:

```text
company claims patterns
process learnings
published knowledge
experiences
```

Mas case-sensitive PII não vira memória global visual genérica.

---

# 119. CLAIMS + IDENTITY/SOUL

Um padrão de atendimento empático observado não altera Company Soul.

No máximo:

```text
IDENTITY/COMMUNICATION CANDIDATE
→ SPEC-098
```

---

# 120. CLAIMS + CHANNEL FABRIC

SPEC-099 deverá preservar:

- WhatsApp authorship;
- email thread;
- private team channels;
- ACL;
- timestamps.

A 093 consome esse provenance.

---

# 121. CLAIMS + ENGINE

No futuro, AutoBrokers Engine pode expor outcome-oriented actions como:

```text
claims.prepare_case
claims.status_with_evidence
claims.document_gap
```

Antes de:

```text
claims.settle
```

A 093 produz evidence para essa evolução.

---

# 122. CUTOVER / ROLLOUT

Fase 1:

```text
backfill sample
```

Fase 2:

```text
live shadow, hidden
```

Fase 3:

```text
Admin visibility
```

Fase 4:

```text
C1 handler assist
```

Nenhuma fase habilita claims writes.

---

# 123. FAIL-SAFE

Se Shadow falha:

```text
claim handling continues human
```

Esse é um dos maiores benefícios da arquitetura Shadow.

---

# 124. ROLLBACK

Desligar:

- claim detector;
- enrichment;
- C1 surface.

Não precisa migrar claim source-of-truth porque não o substituímos.

---

# 125. SECURITY INVARIANTS

1. Shadow is read-only.
2. Claims source-of-truth stays external/current.
3. PII never global.
4. Health/medical data gets high sensitivity.
5. Global learning is sanitized abstraction.
6. Score does not grant capability.
7. Dreams does not publish.
8. Human statements are evidence, not truth.
9. Closure is not success.
10. Claim and assistance remain distinct.
11. Regulations are temporal.
12. Current ACL is enforced.
13. Tool Gateway remains authority.
14. Work Run remains durable execution authority.
15. Smith remains sole cognitive runtime.

---

# 126. DEFINITION OF DONE

A 093 fecha somente quando:

- [ ] estado real de Claims medido;
- [ ] InfoCap `/sinistro` re-testado read-only;
- [ ] source-of-truth documentado por piloto;
- [ ] claim vs assistance taxonomy;
- [ ] gold corpus;
- [ ] detector medido;
- [ ] handoff humano preservado;
- [ ] Claim Shadow read-only;
- [ ] zero claims write capability;
- [ ] Episode/Trajectory 090 reutilizados;
- [ ] zero second Learning Fabric;
- [ ] Claim Shadow Profile;
- [ ] claim identity strategy;
- [ ] semantic-only merge proibido;
- [ ] risk classification;
- [ ] sensitive-data policy;
- [ ] third-party/medical protection;
- [ ] FNOL normalization;
- [ ] safety-first;
- [ ] dossier reused/enriched;
- [ ] repeat minimization measured;
- [ ] human action ledger evidence-based;
- [ ] action without evidence = UNKNOWN;
- [ ] document model;
- [ ] human-requested != insurer-required;
- [ ] policy evidence;
- [ ] coverage decision human;
- [ ] temporal regulatory model;
- [ ] future rule not applied early;
- [ ] wait states;
- [ ] wait owner;
- [ ] outcome taxonomy;
- [ ] outcome strength;
- [ ] closure != success;
- [ ] Claim Evidence Pack;
- [ ] Process Candidate → 091;
- [ ] Skill Candidate → 100;
- [ ] Knowledge Candidate → 090/102;
- [ ] Gap routing;
- [ ] zero direct publish;
- [ ] global learning sanitized;
- [ ] zero raw cross-tenant;
- [ ] C0 active;
- [ ] C1 only evidence assist;
- [ ] C2+ prohibited;
- [ ] Autonomy Readiness Score;
- [ ] hard blockers;
- [ ] score never authorizes;
- [ ] historical backfill idempotent;
- [ ] live incremental;
- [ ] hot path preserved;
- [ ] observability;
- [ ] Dreams 106 contract frozen;
- [ ] Dreams same architecture, no parallel claim brain;
- [ ] Dreams outputs candidates only;
- [ ] Replay 105 prepared;
- [ ] MetaHarness 108 metrics prepared;
- [ ] Red Team complete;
- [ ] M1–M18 red;
- [ ] zero side effect from Shadow;
- [ ] zero PII global leak;
- [ ] zero cross-tenant leak;
- [ ] execution report.

---

# 127. NÃO É DEFINITION OF DONE

Não precisa para fechar 093:

- autonomous claim opening;
- portal claim writes;
- claim denial;
- settlement;
- reserve;
- fraud adjudication;
- payment;
- autonomous negotiation;
- damage computer vision;
- full Claims Core.

---

# 128. NOTAS

| Área | Nota |
|---|---:|
| Capturar conhecimento tácito | **100/100** |
| Preparar autonomia futura | **100/100** |
| Handoff | **99/100** |
| Corpus real de eval | **100/100** |
| Menos repetição | **97/100** |
| Friction map | **98/100** |
| Document/process discovery | **99/100** |
| Valor sem autonomia | **94/100** |
| Full claims automation agora | **58/100 — NÃO** |
| Claims Learning Shadow agora | **100/100 — SIM** |

---

# 129. POR QUE NÃO AUTOMATIZAR AGORA

Claims reúne:

- cobertura;
- contrato;
- causalidade;
- terceiros;
- responsabilidade;
- fraude;
- saúde;
- valores;
- negociação;
- regulamentação;
- exceções.

A pergunta certa:

> **“para qual microprocesso, em qual seguradora, com qual evidência, risco e ODD o sistema já provou que consegue?”**

A 093 cria os dados para responder.

---

# 130. GANHO PARA A CORRETORA

```text
cliente não repete
↓
handler recebe dossiê
↓
docs ficam organizados
↓
timeline fica clara
↓
esperas ficam mensuráveis
↓
processos repetidos aparecem
↓
gaps aparecem
↓
checklists melhoram
```

---

# 131. GANHO PARA O AUTOBROKERS

Cada sinistro deixa de ser:

```text
“uma conversa que terminou em humano”
```

e passa a ser:

```text
uma Trajectory de alta densidade de conhecimento
```

---

# 132. RELAÇÃO COM O CICLO MAIOR

```text
OPERAÇÃO DE SINISTRO
↓
CLAIM TRAJECTORY
↓
LEARNING SIGNAL
↓
DREAMS 106
↓
PROCESS / KNOWLEDGE / SKILL CANDIDATE
↓
PROTOCOL / SKILL FACTORY
↓
AAA EVAL
↓
PUBLICAÇÃO
↓
METAHARNESS
↓
OPERAÇÃO MELHOR
```

> **Dreams fica dentro do ciclo, não ao lado.**

---

# 133. ORDEM DE AUTONOMIA

Não executar outra “SPEC de automatizar claims” imediatamente após 093.

Deixar o Shadow acumular evidência enquanto outras capacidades de alto valor são construídas.

Quando corpus e readiness existirem, escrever SPEC específica para o primeiro microdomínio elegível.

---

# 134. REFERÊNCIAS INTERNAS OBRIGATÓRIAS

No aquecimento, carregar só o necessário:

- SPEC-052;
- SPEC-053;
- SPEC-055;
- SPEC-056;
- SPEC-059;
- SPEC-063;
- Candidate 086;
- Candidate 090;
- Candidate 091;
- `backend/app/core/prompts.py`;
- handoff tool/watchdog;
- `app/api/dashboard/atendimentos/ficha/[id]/route.ts`;
- attendance sessions/dossier;
- InfoCap connector;
- `INFOCAP-CORPAPI-MAPA.md`;
- Redaction Service;
- roles/RLS;
- Atlas/observed sources;
- Research/SUSEP knowledge;
- `PROTOCOLO-AUTOBROKERS-AAA.md`.

Nunca “leia todo Canon”.

---

# 135. REFERÊNCIAS EXTERNAS

Detalhadas no Research Pack:

- Guidewire ClaimCenter / Insurance AI;
- Sprout.ai Claims Decision Intelligence;
- Snapsheet AI;
- Shift Technology ARISE;
- McKinsey Claims 2030;
- Deloitte Insurance Predictions 2026;
- SUSEP;
- Lei nº 15.040/2024;
- Resolução CNSP nº 496/2026.

---

# 136. HARD QUESTIONS PARA O EXECUTOR

Antes de fechar:

1. Qual é a fonte oficial do status do sinistro nesta corretora?
2. Como sabemos que dois registros representam o mesmo claim?
3. Qual dado veio do cliente, do handler e da seguradora?
4. Qual passo realmente ocorreu e qual foi inferido?
5. Qual informação é temporal?
6. Qual conteúdo é sensível?
7. Quem pode ver?
8. Qual insight pode sair do tenant?
9. Qual insight é apenas candidate?
10. Qual capability o Shadow possui?
11. O que impede side effects de verdade?
12. O que acontece se Shadow morrer?
13. Como sabemos se o dossiê melhorou?
14. Qual outcome realmente ocorreu?
15. O que Dreams poderá fazer com isso?
16. O que Dreams explicitamente não poderá fazer?

---

# 137. DECISÕES CONGELADAS

| Tema | Decisão |
|---|---|
| Human owns claim now | **SIM** |
| Shadow observes | **SIM** |
| C1 assist read-only | **SIM, evidence-based** |
| C2+ now | **NÃO** |
| New Claims Core | **NÃO** |
| New Claim Learning Fabric | **NÃO** |
| Reuse 090 Trajectory | **SIM** |
| Human statement = truth | **NÃO** |
| Coverage decision by Shadow | **NÃO** |
| Global raw claims | **NÃO** |
| Autonomy score = permission | **NÃO** |
| Dream agent/brain | **NÃO** |
| Dreams consumes same structures | **SIM** |
| Dreams outputs candidates | **SIM** |
| Full claims automation now | **NÃO** |
| Learn now | **SIM** |

---

# 138. RESEARCH-DRIVEN STRATEGIC DECISION

O salto correto não é tentar competir agora com um claims platform completo.

É construir uma camada vertical que sabe:

```text
o que aconteceu
o que está faltando
onde está parado
qual evidência existe
o que o humano fez
qual foi o resultado
quais padrões se repetem
```

Isso prepara qualquer automação futura com muito mais segurança.

---

# 139. COMANDO FINAL AO EXECUTOR

Não prove que a IA “sabe regular sinistro”.

Prove primeiro que ela sabe:

```text
OBSERVAR SEM INTERFERIR
ENTENDER SEM INVENTAR
ESTRUTURAR SEM VAZAR
COMPARAR SEM CONFUNDIR
APRENDER SEM PUBLICAR
MEDIR SEM AUTORIZAR
```

Quando isso estiver provado em produção, teremos a base factual para decidir exatamente:

```text
o que automatizar
para quem
em qual seguradora
em qual caso
com quais limites
e com qual risco
```

---

# 140. LEI FINAL

> **Sinistro humano hoje não é oportunidade perdida de automação. É matéria-prima de aprendizado.**

O AutoBrokers não precisa escolher entre:

```text
humano
OU
IA
```

A 093 cria:

```text
HUMANO OPERANDO
+
IA APRENDENDO
+
GOVERNANÇA DECIDINDO
```

Essa é a Claims Learning Shadow.
