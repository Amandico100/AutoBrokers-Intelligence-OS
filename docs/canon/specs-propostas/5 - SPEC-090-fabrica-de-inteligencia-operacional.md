# SPEC-090 — A FÁBRICA DE INTELIGÊNCIA OPERACIONAL
## Da operação bruta ao conhecimento governado — Trajectories, Scope Resolver, Evidence, Candidates e Learning Dividend

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento e revisão pelo Protocolo AutoBrokers AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline observado:** `19f41eedc5808cf1099ede19d2a88be502854485` (`main`)  
**Branch sugerida na execução:** `feat/spec090-intelligence-factory`  
**Autoridade cognitiva superior:** SPEC-052  
**Autoridades preservadas:** Smith, Work Runs, Capability Registry, Skill Registry, Tool Gateway, Vault, Supabase, Qdrant como índice derivado, MinIO, MemoryService/MemoryFabric, Intelligence Fabric, Atlas e Candidate gates existentes  
**Depende conceitualmente de:** SPEC-052, 053, 055, 056, 058, 059, 060, 067, 083–085 e Candidates 086–089  
**Prepara diretamente:** SPEC-091, 093, 098, 099, 100, 102, 103, 105, 106, 107, 108 e 109  
**Research Pack:** `SPEC-090-fabrica-de-inteligencia-operacional-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **Quando uma corretora conecta sua operação ao AutoBrokers, cada conversa, atendimento, documento, sinal, correção humana, sucesso e falha pode virar evidência estruturada; a evidência pode virar aprendizado candidato; e somente depois de escopo, permissão, deduplicação, temporalidade, confiança, curadoria e gates esse aprendizado passa a fortalecer memória, Atlas, protocolos, Skills, Auxiliares ou conhecimento global.**

```text
RAW OPERATION
    ↓
SOURCE + IDENTITY + PERMISSION
    ↓
ACTOR / SUBJECT CLASSIFICATION
    ↓
EPISODE
    ↓
TRAJECTORY + OUTCOME
    ↓
OBSERVATIONS / FACTS / SIGNALS
    ↓
SCOPE RESOLVER
    ↓
NOVELTY + DEDUPE + CONTRADICTION + TEMPORALITY
    ↓
INTELLIGENCE CANDIDATE
    ↓
CANDIDATE ROUTER
    ├─ Route Candidate ............ SPEC-087
    ├─ Process/Protocol Candidate . SPEC-091
    ├─ Claim Learning Candidate ... SPEC-093
    ├─ Company Memory Candidate ... SPEC-102
    ├─ User Memory Candidate ...... SPEC-102
    ├─ Global Knowledge Candidate . SPEC-102 / Publisher canônico
    ├─ Skill/Capability Gap ....... SPEC-100
    └─ Auxiliary/Demand Candidate . SPEC-103
```

**Nunca:**

```text
CONVERSA BRUTA
→ LLM
→ VERDADE
```

---

# 0.1 A GRANDE IDEIA

O produto não deve simplesmente “ter memória”. Deve ter uma **máquina de inteligência**.

```text
MEMÓRIA SIMPLES
“guardar alguma coisa para lembrar depois”

VERSUS

INTELLIGENCE FACTORY
“observar a operação, entender o que aconteceu,
saber quem disse, para quem vale, quando era verdade,
o que deu certo, o que é novo, o que contradiz,
qual risco existe e onde esse aprendizado pertence”
```

---

# 0.2 DOIS ATIVOS DIFERENTES

## A — Segundo Cérebro privado da corretora

O AutoBrokers passa a compreender:

- como aquela corretora trabalha;
- quem faz o quê;
- regras internas;
- objetivos;
- preferências organizacionais;
- processos;
- carteira e operação;
- ferramentas;
- decisões e pendências;
- relacionamentos e contexto histórico.

Tudo `tenant-scoped` e permission-aware.

## B — Learning Dividend da rede

Somente padrões de seguro que podem ser abstraídos com segurança geram candidatos globais:

- mudança real de URA;
- procedimento observado e confirmado;
- novos apelidos usados por segurados;
- padrão de operação de seguradora;
- nova lacuna de capacidade;
- padrão recorrente que sustenta nova Skill;
- aprendizado de sinistro em shadow;
- conhecimento regulatório de fonte oficial.

> **A rede ensina sem virar vazamento de dados.**

---

# 0.3 FRONTEIRAS COM AS PRÓXIMAS SPECS

## SPEC-090 — agora

Constrói:

```text
capturar
→ classificar
→ Episode
→ Trajectory
→ Evidence
→ Scope
→ Candidate
→ Router
```

## SPEC-098 — Identity Fabric & Company/User Soul

Cuidará de:

- identidade explícita da corretora;
- identidade operacional;
- voz institucional;
- valores;
- prioridades;
- políticas declaradas;
- identidade de trabalho do usuário;
- preferências;
- direitos decisórios;
- human override.

A 090 pode produzir `IDENTITY_CANDIDATE`, mas **nunca altera Soul diretamente**.

## SPEC-099 — Channel Fabric

Slack, Teams, e-mail, WhatsApp e similares serão fontes/canais permissionados. A 090 preserva sua identidade e ACL.

## SPEC-102 — Knowledge & Memory Factory / Second Brain

Fará o aprofundamento completo de:

- memória semântica;
- episódica;
- temporal;
- procedural;
- Company Memory;
- User Memory;
- entity/context graph;
- retrieval/rerank;
- lifecycle;
- Memories Dashboard;
- navegação até a fonte;
- benchmark Mem0/Graphiti/Letta/LangMem.

## SPEC-106 — Dreams

Fará a consolidação em background:

```text
MERGE
SUPERSEDE
SYNTHESIZE
RECONFIRM
DECAY / RERANK SIGNAL
PATTERN DISCOVERY
GAP DISCOVERY
```

A 090 entrega a matéria-prima limpa e governada.

---

# 1. POR QUE ESTA SPEC EXISTE

O AutoBrokers já tem:

- MemoryService;
- MemoryFabric;
- `user_memories`;
- `session_summaries`;
- `company_memories`;
- `knowledge_candidates`;
- Knowledge Cards;
- Garimpo v3;
- Demand Radar;
- Intelligence Signals;
- Findings/Recommendations/Outcomes;
- Atlas/Tecelão/Sentinela;
- route drift;
- Auxiliary Factory;
- Capability Gaps;
- Research Intelligence;
- Work Runs.

Não falta uma nova biblioteca.

Falta **uma única esteira que transforme operação em inteligência**.

A execução da SPEC-059 já provou o risco de “ter código” sem “ter sistema”: o gatilho de memória ficou inerte por longo período sem que a UI mostrasse claramente o problema. A 090 exige observabilidade ponta a ponta.

---

# 2. ONTOLOGIA: NÃO CONFUNDIR MAIS

## 2.1 Raw Record

Registro original: mensagem, e-mail, row, documento, webhook, tela URA, evento de Work Run.

Não é memória nem conhecimento.

## 2.2 Episode

Unidade contextual de experiência: conversa, atendimento, reunião, thread, interação com seguradora, Work Run.

Preserva:

```text
quando
quem
onde
fonte
ordem
provenance
```

## 2.3 Trajectory

Sequência orientada a resultado:

```text
estado inicial
→ ação
→ resposta
→ decisão
→ ...
→ outcome
```

## 2.4 Observation

Algo observado.

> “A URA pediu placa antes de endereço.”

Observação não é regra universal.

## 2.5 Fact / Claim Candidate

Proposição derivada de evidência.

## 2.6 Memory

Contexto durável ligado a uma entidade/escopo.

## 2.7 Knowledge

Informação de domínio reutilizável e governada.

## 2.8 Procedure / Skill

“Como fazer”. Não é memória.

## 2.9 Soul / Identity

“Quem somos / como queremos agir”. Não é inferência automática.

## 2.10 Working Context

O que entra no prompt agora. É composição, não storage.

---

# 3. O MODELO DE ESCOPO DEFINITIVO

## 3.1 Camadas semânticas da UX

Continuam:

```text
GLOBAL AUTOBROKERS
CORRETORA
PESSOAL
```

## 3.2 Ownership técnico

Internamente:

```text
CASE / SESSION
USER
COMPANY
PLATFORM / GLOBAL
```

`CASE/SESSION` é estágio transitório/episódico, não uma quarta memória principal de produto.

## 3.3 ACL/Visibility é dimensão independente

```text
scope_owner = COMPANY
```

não significa:

```text
visibility = ALL_COMPANY_USERS
```

Uma memória pode pertencer à empresa e vir de:

- canal privado de diretoria;
- e-mail individual;
- pasta restrita;
- grupo financeiro.

Portanto precisa de política própria de acesso.

---

# 4. PRINCÍPIO PERMISSION-AWARE

> **Conectar uma fonte ao AutoBrokers não aumenta a permissão do usuário.**

Se Maria não tinha acesso a `#diretoria-private`, não passa a ter porque o AutoBrokers indexou.

Vale para:

- Slack;
- Teams;
- Drive;
- SharePoint;
- e-mail;
- Notion;
- CRM;
- pastas privadas;
- futuros connectors.

Todo conteúdo permissionado deve preservar referência de ACL/proveniência suficiente para revalidação no retrieval.

Exemplo conceitual:

```json
{
  "source_system": "slack",
  "source_object_id": "...",
  "source_visibility": "private_channel",
  "source_acl_ref": "...",
  "source_acl_version": "...",
  "permission_snapshot_hash": "...",
  "observed_at": "..."
}
```

**Snapshot histórico é audit. Permissão atual é o que autoriza retrieval.**

---

# 5. PIPELINE CANÔNICO

```text
INGEST
  ↓
HYGIENE / PERMISSION
  ↓
CLASSIFY SOURCE
  ↓
CLASSIFY ACTOR
  ↓
CLASSIFY SUBJECT
  ↓
GROUP INTO EPISODE
  ↓
BUILD TRAJECTORY
  ↓
DETECT OUTCOME
  ↓
EXTRACT OBSERVATIONS
  ↓
SCOPE RESOLVER
  ↓
TRUST / PII / ACL GATE
  ↓
NOVELTY
  ↓
DEDUP / CORRELATE
  ↓
TEMPORAL / CONTRADICTION
  ↓
CANDIDATE
  ↓
CANDIDATE ROUTER
```

A resposta ao usuário/segurado não espera a parte pesada dessa pipeline.

---

# 6. SOURCE ENVELOPE

WhatsApp, Slack, Teams, e-mail, InfoCap etc. usam adapters, mas entregam envelope comum:

```json
{
  "event_id": "...",
  "source_kind": "whatsapp",
  "source_ref": "...",
  "company_id": "...",
  "actor_hint": "...",
  "occurred_at": "...",
  "ingested_at": "...",
  "payload_ref": "...",
  "permission_ref": "...",
  "dedupe_key": "..."
}
```

Taxonomia inicial de source:

```text
conversation
whatsapp
email
slack
teams
drive
sharepoint
notion
crm
infocap
quiver
segfy
susep
web
document
insurer_portal
insurer_whatsapp
work_run
artifact
human_feedback
system_event
```

Extensível por registry; não lista eterna em prompt.

---

# 7. ACTOR E SUBJECT

## Actor

Quem produziu aquela evidência:

```text
BROKER_USER
BROKER_EMPLOYEE
BROKER_OWNER
INSURED
INSURER_BOT
INSURER_HUMAN
INSURER_SYSTEM
AUTOBROKERS_AGENT
EXTERNAL_PROVIDER
UNKNOWN
```

## Subject

Sobre quem/o que a informação fala:

```text
user
company
insured
insurer
policy
process
service
route
claim
regulation
tool
system
```

> **Quem falou e de quem o fato trata são dimensões diferentes.**

Classificação deve ser deterministic-first: metadata, JID, connection identity, user IDs, insurer registry, domains e session markers antes de LLM.

`UNKNOWN` é estado legítimo. Não adivinhar identidade para completar pipeline.

---

# 8. TRAJECTORY V1

A 090 cria contrato mínimo, não todo Replay/Fork da 105:

```json
{
  "trajectory_id": "...",
  "company_id": "...",
  "trajectory_kind": "insurer_assistance",
  "subject_refs": [],
  "actor_refs": [],
  "episode_refs": [],
  "started_at": "...",
  "ended_at": "...",
  "initial_state": {},
  "steps": [],
  "outcome": {},
  "evidence_refs": [],
  "quality_flags": []
}
```

Outcome importa porque:

```text
“humano respondeu X”
```

é fraco.

```text
“humano respondeu X
→ seguradora aceitou
→ protocolo chegou”
```

é evidência operacional forte.

Tipos iniciais:

```text
resolved
failed
abandoned
handoff
customer_confirmed
insurer_confirmed
protocol_received
payment_recovered
renewal_closed
claim_advanced
unknown
```

`conversation closed` não equivale a `resolved`.

---

# 9. TRUST TIER

Preservar filosofia atual e torná-la Evidence-driven.

```text
T0  fonte oficial/autoritativa estruturada
T1  outcome transacional confirmado
T2  observação repetida consistente
T3  fonte identificada confiável
T4  declaração humana
T5  inferência do modelo
```

Tier 5 pode gerar investigação/candidato.

Tier 5 não pode:

- virar verdade;
- publicar global;
- mudar Soul;
- alterar rota;
- promover memória organizacional.

Resposta humana também não é Ground Truth por definição.

---

# 10. SCOPE RESOLVER

Objeto lógico central da SPEC.

Recebe:

- source;
- actor;
- subjects;
- claim;
- evidence;
- permissions;
- repeatability;
- sensitivity;
- temporal class;
- outcome.

Retorna:

```text
CASE_ONLY
USER_CANDIDATE
COMPANY_CANDIDATE
GLOBAL_CANDIDATE
IDENTITY_CANDIDATE
PROCESS_CANDIDATE
ROUTE_CANDIDATE
CLAIM_LEARNING
SKILL_GAP
AUXILIARY_DEMAND
DISCARD
QUARANTINE
```

Cada decisão carrega:

```text
scope_policy_version
reason_code
```

Reason codes, por exemplo:

```text
PERSONAL_PREFERENCE
COMPANY_POLICY
INSURER_REUSABLE_PATTERN
CASE_EPHEMERAL
SENSITIVE_PII
SOURCE_ACL_TOO_NARROW
INSUFFICIENT_EVIDENCE
```

---

# 11. NÃO EXISTE ESCADA AUTOMÁTICA USER → COMPANY → GLOBAL

A direção correta:

```text
RAW TENANT EVIDENCE
        ↓
ABSTRACT
REDACT
VALIDATE
        ↓
GLOBAL CANDIDATE
```

Global recebe **novo objeto abstrato**, não row privada “promovida”.

### USER → COMPANY

Só se subject for organizacional, houver evidência/confirmacão e não for preferência pessoal.

### COMPANY → GLOBAL

Nunca raw. Requer:

- domínio de seguro reutilizável;
- nenhum identificador de tenant;
- nenhuma PII;
- nenhuma estratégia exclusiva da corretora;
- evidência suficiente;
- abstração;
- provenance;
- risk gate.

---

# 12. LEARNING DIVIDEND

Pode globalizar, via candidate governado:

```text
seguradora
ramo
serviço
procedimento
mudança
vocabulário
dor recorrente
capability gap
```

Não pode globalizar:

```text
faturamento da Resulta
vendedor da AutoFleet
clientes
comissões privadas
leads
conversa privada
estratégia comercial tenant
```

Cross-tenant confirmation pode aumentar confiança usando contagens anônimas, não identidade tenant.

Separar:

```text
occurrence_count
episode_count
independent_source_count
tenant_count_anonymized
```

100 mensagens na mesma conversa não são 100 fontes.

---

# 13. NOVELTY, DEDUPE E CONTRADIÇÃO

Antes de candidate:

> **isso aumenta o que já sabemos?**

Comparar contra:

- published knowledge;
- company/user memory;
- candidates;
- routes;
- protocols;
- Skills/capabilities;
- demand clusters.

Hash exato atual continua fast path.

Adicionar semantic neighborhood.

Mas semantic similarity nunca pode fundir opostos:

```text
“Porto envia boleto pelo WhatsApp”
“Porto NÃO envia boleto pelo WhatsApp”
```

Pipeline:

```text
similaridade
→ claim/polarity
→ merge/refine/contradiction
```

Relações mínimas:

```text
supports
contradicts
supersedes
refines
duplicates
derived_from
```

Não precisa graph DB na 090.


---

# 14. TEMPORALIDADE

Cada claim relevante deve distinguir, quando aplicável:

```text
observed_at
ingested_at
event_time
valid_from
valid_until
last_confirmed_at
invalidated_at
```

## 14.1 Bi-temporal principle

```text
WHEN WE LEARNED IT
```

é diferente de:

```text
WHEN IT WAS TRUE
```

Exemplo:

- documento descoberto em 25/08;
- diz que mudança entrou em vigor em 10/08.

```text
ingested_at = 25/08
valid_from  = 10/08
```

## 14.2 História não é apagada

Mudou a verdade:

```text
old → superseded
new → current/candidate
```

com link e auditoria.

Não DELETE para “limpar”.

## 14.3 Memory decay não é delete

SPEC-102 pode usar recency/usefulness para ranking, mas fatos antigos continuam recuperáveis quando realmente relevantes.

---

# 15. PERMISSION GATE

## 15.1 Ingestion permission ≠ persistence permission

Uma conexão pode permitir ler conteúdo para uma tarefa atual sem autorizar:

```text
persist semantic memory
```

Source policy deve conseguir expressar:

```text
can_use_for_current_task
can_index
can_form_memory
can_form_company_memory
can_form_global_candidate
retention_class
```

## 15.2 Private source

DM, private Slack, e-mail, restricted folder ou role-limited system:

não amplia para company/global por padrão.

## 15.3 Retrieval futuro

SPEC-102 Context Assembly deverá revalidar:

```text
memory ownership
+
current user
+
role
+
current source ACL
+
policy
```

Historical permission snapshot serve para audit, não para conceder acesso.

---

# 16. PII / SECRET / SENSITIVE GATE

Antes de qualquer candidato global:

```text
PII scan
secret scan
tenant identifier scan
broker identity scan
customer identity scan
```

Falhou:

```text
QUARANTINE
```

Não “corrigir depois que já entrou no índice global”.

## 16.1 Customer PII

Segurado não deve virar perfil semântico livre.

Dados do segurado continuam nos sistemas/case/source-of-truth apropriados.

> **User Memory é memória do usuário do AutoBrokers, não CRM dos segurados.**

---

# 17. SOURCE OF TRUTH VS MEMORY

Estado mutável deve continuar vivo na fonte:

```text
InfoCap
Quiver
Segfy
API
CRM
```

Exemplos:

- status atual da apólice;
- saldo;
- parcela;
- comissão atual;
- produção do mês;
- vigência atual.

Memória guarda:

- preferência;
- regra organizacional;
- padrão;
- decisão;
- contexto;
- relacionamento;
- experiência relevante.

Regra de futura recuperação:

```text
LIVE AUTHORITATIVE DATA
>
MEMORY
```

quando o assunto é estado mutável.

---

# 18. CURRENT USER MEMORY — DÍVIDA FORMAL PARA 102

Hoje o `MemoryService` possui uma boa base histórica, mas limitada:

- fatos em lista;
- consolidação pequena;
- summaries recentes;
- pending items;
- opcional `agent_id`;
- recuperação principalmente por recência;
- `current_query` ainda não governa rerank completo.

A 090 não reescreve isso.

Mas congela:

> **A identidade/memória pessoal canônica pertence a `company + user`; `agent_id` não pode fragmentar “quem o usuário é” em verdades paralelas.**

Agents podem ter:

```text
working_state
role_hints
curated_refs
learning_signals
```

não uma quarta verdade pessoal.

---

# 19. COMPANY MEMORY

`company_memories` já é excelente fundação:

- candidate/active/conflicted/superseded/revoked;
- evidence;
- confidence;
- trust;
- occurrences;
- confirmation;
- validity;
- supersession.

A 090 deve reutilizar e preparar evolução.

Default para observação não comprovada:

```text
candidate
```

Não `active`.

---

# 20. GLOBAL KNOWLEDGE CANDIDATE

Reutilizar `knowledge_candidates`.

Não criar `knowledge_candidates_v2`.

Ela já traz:

- scope;
- source;
- evidence;
- source count;
- confidence;
- trust;
- risk;
- lifecycle;
- dedupe;
- contradiction;
- PII;
- human review;
- publication ref.

Warm-up deve medir lacunas:

- dedupe só lexical/exato?
- source count realmente independente?
- temporalidade?
- actor/subject?
- ACL?
- audit lineage global sem tenant leak?
- candidate_type expressivo?

Expand-first.

---

# 21. INTELLIGENCE CANDIDATE ENVELOPE

É contrato, não necessariamente nova tabela.

```json
{
  "candidate_kind": "knowledge",
  "source_episode_refs": [],
  "trajectory_ref": null,
  "company_id": "...",

  "subject": {
    "type": "insurer_procedure",
    "refs": []
  },

  "claim": "...",

  "scope_decision": {
    "target": "GLOBAL_CANDIDATE",
    "reason": "INSURER_REUSABLE_PATTERN",
    "version": "..."
  },

  "permission": {},
  "evidence_refs": [],
  "trust": {},
  "temporal": {},
  "novelty": {},
  "risk": {},
  "pii": {},

  "target_adapter": "knowledge_candidate"
}
```

---

# 22. CANDIDATE ROUTER

Não publica. Encaminha à autoridade correta.

```text
route
→ 087

protocol/process
→ 091

claim
→ 093 shadow

company/user/global memory
→ current Memory/Candidate path + 102

skill/capability
→ Capability Gap + 100

auxiliary demand
→ Auxiliary Request / Demand Radar + 103
```

Não criar mega authority para todos os candidates.

---

# 23. GARIMPO / “O AGENTE QUE ENTENDE O QUE AS CORRETORAS QUEREM”

Não criar outro Agent.

A função correta é consolidar:

```text
Garimpo
+
Intelligence Signals
+
Auxiliary Requests
+
Capability Gaps
+
Demand Clusters
+
Outcomes
+
usage
+
qualitative feedback
```

em:

# **Demand & Intent Intelligence**

Hoje o Garimpo já separa “o corretor declarou” de “isto é verdade”. Preservar.

Aprofundar candidate com:

- normalized outcome;
- affected workflow;
- recurrence;
- user role;
- company context;
- current workaround;
- estimated time pain;
- capability gap;
- automation suitability.

---

# 24. DEMAND CLUSTERING

Demand Radar atual possui ideia boa:

> muitas corretoras pesam mais que muitos pedidos de uma única corretora.

Preservar tenant hashing.

Investigar:

```text
exact fingerprint
+
semantic outcome clustering
+
workflow/entity normalization
```

Sem juntar outcomes parecidos mas operacionalmente diferentes.

Um pedido:

> “receba toda segunda minhas renovações críticas”

não é automaticamente “nova feature”.

Pode mapear para:

```text
Outcome
→ existing Skill
→ Routine
```

Factory posterior decide.

---

# 25. CAPABILITY GAP

Quando algo não pode ser entregue hoje, registrar estruturado:

```text
missing_data
missing_connector
missing_tool
missing_skill
missing_permission
missing_provider
missing_workflow
```

Isso vira ativo estratégico para SPEC-100/103.

---

# 26. PROCESS DISCOVERY / AUTOMATION MINING

Trajectories repetidas podem produzir:

```text
PROCESS_CANDIDATE
```

Exemplo:

```text
recebe planilha
→ filtra vencidos
→ pede boleto
→ manda WhatsApp
→ registra resultado
```

Sinais:

- frequência;
- duração;
- número de ferramentas;
- repetição;
- retrabalho;
- falhas;
- manual handoffs.

Podem gerar:

```text
AUTOMATION_OPPORTUNITY
```

Nunca criar Auxiliar sozinho.

---

# 27. CLAIMS LEARNING

Quando sinistro vai para humano:

capturar em shadow:

- contexto;
- pedido;
- documentos;
- o que humano perguntou;
- o que seguradora exigiu;
- passos;
- outcome.

Encaminhar para SPEC-093.

Não automatizar sinistro aqui.

---

# 28. ROUTE / ASSISTANCE LEARNING

Mudanças de URA, labels, botões e outcomes:

encaminhar 087.

Nunca publicar rota na 090.

---

# 29. VOCABULARY / ALIASES

Pode aprender candidatos como:

```text
“furou pneu”
“socorro pneu”
“pneu rasgou”
“estepe”
```

→ service alias candidate.

Exige:

- mapping do serviço;
- evidência;
- dedupe;
- zero PII.

---

# 30. RESEARCH / SUSEP

Pesquisa oficial entra com provenance forte:

- URL/source;
- publication date;
- effective date;
- authority;
- fetched_at;
- risk;
- version.

Mesmo fonte oficial não pula lifecycle de candidate em matéria de alto risco.

---

# 31. DOCUMENTOS

Upload não vira memória automaticamente.

Documento permanece fonte.

Pode gerar:

- facts;
- entities;
- candidates;
- citations.

Raw file continua authoritative source.

---

# 32. HISTORICAL BACKFILL

Nova corretora:

```text
SOURCE DISCOVERY
↓
DATA INVENTORY
↓
PERMISSION INVENTORY
↓
SAMPLE / CLASSIFICATION
↓
BACKFILL PLAN
↓
BATCHED INGESTION
↓
EPISODES / TRAJECTORIES
↓
CANDIDATES
↓
REPORT
```

Separado de live processing.

Work Run obrigatório para backfill relevante.

---

# 33. LIVE INCREMENTAL

Por source/partition:

```text
last_source_cursor
last_event_time
last_ingested_id
last_successful_batch
```

Não revarrer toda base toda noite.

Raw event dedupe por source identity/version.

Reprocessar:

```text
1 logical Episode
```

---

# 34. HOT / WARM / COLD PATH

```text
HOT
capture
light classify
queue

WARM
Episode
Trajectory
Candidate
dedupe

COLD
Dreams
deep consolidation
synthesis
```

Hot path não atrasa:

- chat principal;
- atendimento;
- WhatsApp.

---

# 35. COST TIERING

```text
deterministic/rules
→ embedding/small classifier
→ balanced model
→ strong model only ambiguity/high risk/high value
```

Modelo forte para:

- subtle contradiction;
- scope ambiguity;
- trajectory synthesis complexa;
- high-risk claims;
- abstraction global.

Não para cada “oi”.

---

# 36. PROVENANCE

Todo derived object responde:

```text
de onde veio?
qual Episode?
qual raw source?
quem disse?
sobre quem?
quando?
qual outcome?
qual transformer?
qual model?
qual rule/prompt version?
```

Sem armazenar chain-of-thought.

Derivation lineage:

```text
raw
→ episode
→ observation
→ candidate
→ published
```

reconstruível.

---

# 37. EVIDENCE PACK

```json
{
  "source_kind": "...",
  "source_ref": "...",
  "episode_ref": "...",
  "trajectory_ref": "...",
  "actor_ref": "...",
  "observed_at": "...",
  "event_time": "...",
  "trust_tier": 2,
  "outcome_ref": "...",
  "permission_ref": "...",
  "redaction": {}
}
```

Evidence append-only/versioned.

Score pode recalcular; história não.

---

# 38. IDENTITY SIGNALS → 098

Exemplos observáveis:

```text
“sempre chamamos clientes de associados”
“não usamos emojis”
“estorno precisa do gerente”
```

A 090 cria candidate.

098 decide se pertence a:

- Soul;
- policy;
- user preference;
- company operating identity.

Human edit/explicit identity terá prioridade.

Não inferir personalidade por amostra fraca.

---

# 39. DREAMS HANDOFF → 106

Dreams deve consumir:

- new/changed memories;
- trajectories;
- candidates;
- contradictions;
- usage;
- retrieval misses;
- outcomes.

E fazer:

```text
MERGE
SUPERSEDE
SYNTHESIZE
RECONFIRM
DECAY/RERANK SIGNAL
PATTERN DISCOVERY
GAP DISCOVERY
```

Dreams não pode:

- publicar global sozinho;
- alterar Soul sozinho;
- publicar rota;
- broadening ACL;
- mover tenant raw para global;
- auto-publicar Skill high-risk.

---

# 40. SECOND BRAIN HANDOFF → 102

SPEC-102 deve construir uma projeção coerente:

```text
GLOBAL
  insurance knowledge
  insurer knowledge
  regulation
  routes/procedures
  playbooks

COMPANY
  documents
  company memories
  processes
  goals
  operational context

PERSONAL
  preferences
  commitments
  recent work
  personal memory

EXPERIENCES
  trajectories/episodes

CONNECTIONS
  live systems
```

A 090 não cria novo graph DB.

---

# 41. DÍVIDA DA TELA MEMÓRIAS — REGISTRADA

Current dashboard hoje não projeta de forma completa:

- `company_memories`;
- `knowledge_candidates`;
- Intelligence Signals;
- todo universo SUSEP/Research;
- candidates vs published;
- canonical source navigation.

SPEC-102 será obrigada a corrigir:

- completude;
- contagens;
- paginação sem silent caps;
- source/provenance;
- click → detalhe real;
- scroll/highlight;
- “perguntar sobre isso” por canonical ref;
- permissions;
- no raw global leakage.

Não fazer patch cosmético isolado agora.

---

# 42. EXTERNAL MEMORY/GRAPH PROVIDERS — DECISÃO

## Mem0

Usar como benchmark para:

- scopes;
- lifecycle;
- Dream;
- temporal reasoning;
- merge/supersede/synthesis;
- decay;
- token-efficient retrieval.

**Não substituir Memory Fabric agora.**

## Graphiti/Zep

Benchmark para:

- Episodes;
- temporal facts;
- provenance;
- relationships;
- bi-temporal model;
- incremental graph.

**Não instalar graph DB na 090.**

## Letta

Benchmark para:

- explicit memory blocks;
- shared memory;
- sleep-time/background cognition.

## Hermes

Benchmark ontológico:

```text
SOUL
USER
MEMORY
PROJECT CONTEXT
SKILL
```

Não usar flat Markdown como authority SaaS.

## Glean

Principal analogia empresarial:

```text
Enterprise Graph
+
Personal Graph
+
Connectors
+
Permissions
```

## Microsoft 365 Copilot

Principal referência de:

```text
permission-aware grounding
```

## LangGraph/LangMem

Referência nativa para:

- thread memory vs long-term;
- semantic/episodic/procedural;
- hierarchical namespace.

---

# 43. MEMORY NAMESPACE — PREPARAÇÃO PARA 102

Conceitualmente:

```text
(scope_kind, company_id, subject_type, subject_id, memory_kind)
```

Mas Supabase continua authority.

Não congelar storage final na 090 sem benchmark.

---

# 44. MEMORY TYPES — PREPARAÇÃO PARA 102

Provável taxonomia:

```text
WORKING
SEMANTIC
EPISODIC
PROCEDURAL
PREFERENCE
IDENTITY
PERFORMANCE
```

Porém:

- procedural pode viver em Skills/Protocols;
- identity em 098;
- working em thread/Work Run.

“Memory Fabric” coordena referências; não precisa armazenar tudo na mesma tabela.

---

# 45. USER CORRECTION

“Isso está errado” não vira apenas mais um fato.

Cria:

```text
CORRECTION EVIDENCE
```

e conduz:

- conflict;
- supersede;
- re-evaluate scope;
- possible negative learning.

---

# 46. NEGATIVE LEARNING

Falha também é evidência:

- tool fails;
- route dead;
- wrong memory;
- user correction;
- artifact missing field.

Candidate pode ser:

> “não faça X”.

---

# 47. POSITIVE LEARNING

Só com outcome adequado.

Não usar:

```text
“obrigado”
conversation length
chat closed
```

como sucesso universal.

---

# 48. SYNTHETIC/TEST DATA

Technical/test tenants devem ser marcados.

Por default:

```text
ZERO GLOBAL LEARNING
```

a partir deles.

Synthetic eval pode testar pipeline, nunca ensinar produção sem curadoria explícita.

---

# 49. CANDIDATE REVIEW UX

Mostrar:

```text
claim
target scope
reason
sources
independent source count
tenant count anonymized
outcome strength
conflicts
risk
PII
validity
suggested destination
```

Ações:

```text
APPROVE
REJECT
MERGE
SUPERSEDE
REQUEST_EVIDENCE
CHANGE_SCOPE
CHANGE_TARGET
```

Tudo auditado.

---

# 50. GOVERNANÇA POR RISCO

Founder não pode revisar tudo.

Preparar future policy:

```text
LOW PRIVATE
→ potential auto-promotion only with strong proof (102)

GLOBAL / MEDIUM+
→ curation

HIGH / CRITICAL
→ authorized human + source requirements
```

A 090 **não** cria novo auto-publisher.

Global publisher existente continua único.

---

# 51. OBSERVABILIDADE DA FACTORY

Funnel real:

```text
RAW
↓
CLASSIFIED
↓
EPISODES
↓
TRAJECTORIES
↓
CANDIDATES
↓
ROUTED
↓
APPROVED/PUBLISHED
```

Métricas:

```text
actor_classification_accuracy
scope_precision
scope_leak_rate
candidate_precision
novelty_precision
duplicate_rate
contradiction_detect_rate
false_contradiction_rate
pii_block_rate
source_acl_violation_rate
```

Negócio:

```text
new answerable questions
new proven routes
new protocols
new aliases
new capability gaps
new automation opportunities
time saved
```

A métrica principal:

> **quantas capacidades úteis e confiáveis nasceram?**

Não “quantas memórias foram criadas”.

---

# 52. LEARNING DIVIDEND METRIC

Agregado:

```text
N tenants contribuíram evidência segura
X global candidates
Y melhorias aprovadas
Z operações beneficiadas
```

Nunca revelar os tenants contribuintes.

---

# 53. FACTORY HEALTH

Admin deve detectar:

- capture stopped;
- classifier unhealthy;
- queue stuck;
- contradiction spike;
- PII spike;
- candidate drought;
- cost anomaly;
- source permission failures.

Não repetir o histórico de Memory Pipeline inerte silenciosamente.

---

# 54. SECURITY INVARIANTS

1. Confidence does not grant permission.
2. Recency does not guarantee truth.
3. Frequency from same source does not mean independence.
4. Private data does not become company-wide by indexing.
5. Company data does not become global raw.
6. LLM output is inference, not evidence.
7. Qdrant is derived, not authority.
8. Current mutable facts prefer source-of-truth.
9. User memory is not customer CRM.
10. Agent memory is not fourth truth.


---

# 55. BLOCO 0 — FORENSE READ-ONLY OBRIGATÓRIA

Antes de alterar qualquer linha:

1. registrar HEAD e branch;
2. medir schema vivo;
3. inventariar todas as tabelas/serviços de memória e inteligência;
4. contar `user_memories` por tenant/agent;
5. contar `session_summaries`;
6. contar `company_memories` por status;
7. contar `knowledge_candidates` por scope/status/type;
8. contar `knowledge_cards`;
9. contar Intelligence Signals;
10. contar Findings/Recommendations/Outcomes;
11. contar Auxiliary Requests;
12. contar Capability Gaps;
13. contar Demand Clusters;
14. mapear Atlas/observed sessions;
15. mapear route drift;
16. mapear Research/SUSEP;
17. mapear atual Memories API/UI;
18. mapear Context Assembly e injeção de memória;
19. mapear Smith Worker e jobs de memória;
20. identificar tenants técnicos/teste;
21. mapear redaction/PII;
22. mapear RLS;
23. mapear metadata de permissões de connectors;
24. medir candidatos produzidos nos últimos 7/30 dias;
25. medir idade da fila;
26. medir quantos candidates têm `source_count > 1`;
27. provar se fontes são independentes;
28. medir current contradiction detector;
29. medir current dedupe;
30. medir latency/cost da memory pipeline.

### Hipóteses a refutar

- [ ] Global/Company/User estão plenamente implementados hoje.
- [ ] `company_memories` aparece no Segundo Cérebro.
- [ ] User Memory não está fragmentada por `agent_id`.
- [ ] `current_query` realmente reranqueia memória pessoal.
- [ ] `source_count` significa fontes independentes.
- [ ] Candidate global preserva audit lineage sem expor tenant.
- [ ] Contradição atual é semanticamente robusta.
- [ ] Dedupe atual pega paráfrases.
- [ ] Source ACL acompanha memória derivada.
- [ ] Private connector content nunca broadens.
- [ ] InfoCap live state não vira stale memory.
- [ ] Demand clustering não funde outcomes diferentes.
- [ ] Tenant técnico não ensina global.
- [ ] Todas as fontes de aprendizado passam por Candidate canônico.

O executor deve **medir**, não assumir.

---

# 56. BLOCO A — UNIFIED LEARNING EVENT ENVELOPE

Objetivo:

unificar a entrada sem criar outro event bus.

Antes, verificar Intelligence Events/Outbox e reusar se suficiente.

Contrato lógico mínimo:

```text
event identity
source identity
company
actor hint
time
payload ref
permission ref
dedupe
```

### Gate A

O mesmo evento entregue 3 vezes:

```text
1 logical event
```

### Controle

Três eventos diferentes do mesmo objeto:

```text
3 versions/events
```

quando realmente representam mudança.

---

# 57. BLOCO B — SOURCE / ACTOR / SUBJECT CLASSIFICATION

Implementar deterministic-first.

Criar gold corpus real/anônimo com:

- segurado;
- funcionário;
- dono;
- seguradora bot;
- seguradora humano;
- sistema;
- Core;
- unknown.

### Gate B

`UNKNOWN` não é erro.

Uma classificação incerta não pode promover candidato amplo.

---

# 58. BLOCO C — PERMISSION & HYGIENE ENVELOPE

Preservar:

- source visibility;
- ACL ref;
- source owner;
- retention class;
- PII/secret state.

### Gate C

Conteúdo de private source:

- pode ser usado pelo usuário autorizado;
- não aparece para usuário não autorizado;
- não produz company-wide/global candidate sem policy.

---

# 59. BLOCO D — EPISODE BUILDER

Agrupar raw events em Episode sem perder ordem/proveniência.

Possíveis chaves:

- conversation/thread;
- dispatch session;
- Work Run;
- case;
- meeting;
- email thread.

### Gate D

Uma conversa reprocessada não cria Episode duplicado.

---

# 60. BLOCO E — TRAJECTORY V1 + OUTCOME

Criar Trajectory somente quando existe trabalho/caso significativo.

Não gerar Trajectory para todo small talk.

### Gate E

Um acionamento de assistência real/teste controlado é reconstruído:

```text
pedido
→ etapas
→ resultado
```

e outcome não é inferido por “conversa fechada”.

---

# 61. BLOCO F — OBSERVATION EXTRACTOR

Extrair:

- fato;
- pergunta recorrente;
- alteração;
- procedimento;
- problema;
- preferência;
- policy;
- demand;
- outcome signal.

Cada observation:

- source refs;
- actor;
- subject;
- timestamp;
- trust.

### Gate F

LLM-only observation é marcado inference.

---

# 62. BLOCO G — SCOPE RESOLVER

Implementar policy versionada.

Goldens mínimos:

```text
“prefiro respostas curtas”
→ USER_CANDIDATE

“nossa corretora exige revisão do gerente”
→ COMPANY_CANDIDATE

“a Allianz agora exige campo X”
→ ROUTE/GLOBAL CANDIDATE com evidence

“cliente João tem CPF...”
→ CASE/PROTECTED

“quero integrar Pipedrive”
→ AUXILIARY_DEMAND / CAPABILITY GAP

“a SUSEP publicou norma”
→ GLOBAL CANDIDATE com high-risk gate
```

### Gate G

Mudar uma frase pessoal não pode contaminar company/global.

---

# 63. BLOCO H — NOVELTY / DEDUPE / CONTRADICTION

Pipeline:

```text
exact hash
→ subject filter
→ semantic neighborhood
→ temporal compatibility
→ claim polarity/entailment
→ decision
```

Outputs:

```text
NEW
DUPLICATE
REFINEMENT
SUPPORT
CONTRADICTION
SUPERSESSION
```

### Gate H

100 paráfrases não geram 100 candidates.

### Controle

Duas regras parecidas mas distintas não são fundidas.

---

# 64. BLOCO I — CANDIDATE ROUTER

Adapters para autoridades existentes.

O router só pode:

```text
propor
```

Nunca:

```text
publicar
ativar
alterar rota
alterar Soul
```

### Gate I

Mutation que chama publisher direto deve falhar.

---

# 65. BLOCO J — GARIMPO / DEMAND & INTENT INTELLIGENCE

Consolidar, não substituir:

- Garimpo v3;
- Intelligence Signals;
- Auxiliary Requests;
- Capability Gaps;
- Demand Radar.

Adicionar normalização de Outcome e contexto.

### Gate J

O mesmo pedido expresso em chat + Slack + dashboard:

```text
1 normalized demand
+
3 evidence refs
```

quando realmente equivalente.

---

# 66. BLOCO K — HISTORICAL BACKFILL

Work Run durável:

- inventory;
- batches;
- watermark;
- pause/resume;
- retry;
- cost;
- progress.

Não competir com live traffic.

### Gate K

Kill/restart no meio:

- retoma;
- não duplica;
- não perde cursor.

---

# 67. BLOCO L — LIVE INCREMENTAL

Evento entra após operação.

Heavy processing fora do request path.

### Gate L

Baseline TTFT/chat e attendance não regressa além do orçamento definido no warm-up.

---

# 68. BLOCO M — INTELLIGENCE FACTORY OBSERVABILITY

Surface mínima no Admin/Control Plane.

Mostrar:

- source health;
- funnel;
- batches;
- candidate queue;
- conflicts;
- quarantines;
- cost;
- learning dividend;
- demand/gaps.

Não criar nova “Central” paralela se Admin atual comporta.

---

# 69. BLOCO N — CANARY

Pilotos autorizados conforme estado vivo.

Technical/test tenants:

```text
global_learning=false
```

por default.

### Gate N

- zero cross-tenant;
- zero PII global;
- zero broad permission;
- zero direct publish.

---

# 70. FAILURE POLICY

## Classifier falhou

```text
UNKNOWN
```

ou retry.

Nunca guess.

## Permission desconhecida

```text
deny broader persistence
```

## Candidate Router falhou

```text
pending/error
```

Nunca publish.

## Temporalidade ambígua

```text
unknown validity
```

não inventar `valid_from`.

---

# 71. BACKPRESSURE E PRIORIDADE

Queues lógicas:

```text
LIVE HIGH VALUE
LIVE NORMAL
BACKFILL
DEEP CONSOLIDATION
```

Limites:

- batch;
- concurrency;
- provider;
- tenant;
- budget.

Uma corretora com 10 anos de WhatsApp não pode derrubar atendimento atual.

---

# 72. COST ATTRIBUTION

Atribuir quando possível:

```text
tenant
source
batch
transformer
model
candidate type
```

Global cross-tenant aggregation pode ser platform-funded.

---

# 73. NO MAGIC MODEL

Toda etapa LLM tem:

- model class;
- version;
- prompt/rule version;
- inputs refs;
- output ref;
- cost.

Sem chain-of-thought.

---

# 74. CANDIDATE QUALITY SCORE

Score diagnóstico:

```text
evidence_strength
independence
authority
outcome_strength
recency
novelty
consistency
```

Risk gate é separado.

> Score alto não compensa blocker de risco/permissão.

---

# 75. CANDIDATE LIFECYCLE

Mínimo conceitual:

```text
draft
pending_review
approved
rejected
published
conflicted
superseded
merged
stale_needs_revalidation
quarantined
```

Não obrigar tudo na mesma tabela se target-specific lifecycle já existe.

---

# 76. REVALIDATION

Candidate velho:

não aprovar por tempo.

Pode:

- pedir nova evidência;
- reexecutar source check;
- arquivar.

High-risk candidate pendente deve ficar visível.

---

# 77. USER / HUMAN CORRECTION

Correção explícita tem alta relevância, mas ainda depende de scope.

Fluxo:

```text
correction
→ evidence
→ contradiction/supersession
→ review if needed
```

Não simplesmente “novo prevalece” sem lineage.

---

# 78. SOURCE UPDATE

Se fonte oficial muda:

gerar evento.

Pode invalidar:

- memory;
- candidate;
- knowledge;
- protocol;
- route.

Router chama autoridade correta.

---

# 79. “DREAMS READY” FLAGS

A 090 deve deixar campos/sinais suficientes para 106 selecionar candidatos a consolidação:

```text
new_since_last_dream
contradicted
frequently_retrieved
stale
high_recurrence
high_value_trajectory
retrieval_miss
```

Não implementar Dream engine.

---

# 80. “SECOND BRAIN READY” REFERENCES

Todo item projetável na futura UI deve conseguir produzir:

```text
canonical_ref
type
scope
safe_title
safe_summary
status
updated_at
source_ref
detail_route
permission_policy
```

A 090 pode definir adapter contract, mas 102 implementa Brain Projection Service.

---

# 81. RED TEAM

Missão:

> **Fazer erro humano, dado privado, dado velho, inferência de LLM ou dado de teste virar “verdade global” sem o sistema perceber.**

Ataques obrigatórios:

1. private Slack channel;
2. DM;
3. private e-mail;
4. user preference;
5. broker employee wrong answer;
6. insurer human typo;
7. tenant name in candidate;
8. CPF/phone;
9. secret/token;
10. stale policy;
11. opposite paraphrases;
12. duplicate backfill;
13. same source repeated 50 times;
14. technical tenant;
15. synthetic test;
16. “obrigado” treated success;
17. chat closed treated success;
18. model hallucination;
19. ACL removed after ingestion;
20. global lineage leaks tenant;
21. source_count inflation;
22. timestamp out of order;
23. current live InfoCap value copied to long-term memory;
24. Agent-private memory used as user truth.

---

# 82. MUTATIONS OBRIGATÓRIAS

## M1
Remover company/user scope de personal candidate.

**Tem de falhar.**

## M2
USER auto-promote para COMPANY.

**Falhar.**

## M3
COMPANY raw vira GLOBAL.

**Falhar.**

## M4
Remover PII gate.

**Falhar.**

## M5
Remover permission ref em private source.

**Falhar.**

## M6
Usar `occurrence_count` como fontes independentes.

**Falhar.**

## M7
Semantic similarity funde negação com afirmação.

**Falhar.**

## M8
Tenant técnico contribui global.

**Falhar.**

## M9
Backfill duas vezes duplica candidate.

**Falhar.**

## M10
Inference recebe Trust Tier 2.

**Falhar.**

## M11
Conversation closed = success.

**Falhar.**

## M12
Candidate Router publica.

**Falhar.**

## M13
ACL histórico concede acesso atual.

**Falhar.**

## M14
User memória de Agent A diverge de Agent B e ambos viram “verdade do usuário”.

**Falhar.**

---

# 83. TEST MATRIX — SCOPE

| Entrada | Target esperado |
|---|---|
| preferência pessoal explícita | USER |
| policy da corretora confirmada | COMPANY |
| procedure de seguradora comprovado | GLOBAL/ROUTE candidate |
| PII de cliente | CASE/protected |
| desejo de Pipedrive | DEMAND/GAP |
| norma SUSEP | GLOBAL candidate high-risk |
| inference sem fonte | investigate/candidate only |

---

# 84. TEST MATRIX — TEMPORAL

- current fact;
- superseded fact;
- future-effective regulation;
- ambiguous date;
- out-of-order ingestion;
- reconfirmation;
- old source discovered today;
- expired-but-historically-needed fact.

---

# 85. TEST MATRIX — PERMISSION

- public company channel;
- private channel;
- DM;
- restricted Drive file;
- ACL removed;
- role changed;
- connector revoked;
- user deleted;
- source copied to another system with different ACL.

---

# 86. TEST MATRIX — DEDUPE

- exact;
- paraphrase;
- more-specific refinement;
- contradiction;
- same fact multiple tenants;
- same source replay;
- truly independent sources.

---

# 87. TEST MATRIX — OUTCOME

- protocol success;
- insurer confirmation;
- customer confirmation;
- human says resolved but evidence missing;
- abandoned;
- handoff;
- timeout;
- closed/unknown.

---

# 88. SCALE / PERFORMANCE

Simular ao menos ordem de grandeza:

```text
100k messages
10k episodes
1k candidates
```

Proibido O(n²) global.

Semantic comparison usa neighborhood filtrado:

- scope;
- subject;
- category;
- insurer;
- ramo/service;
- temporal window.

---

# 89. SECURITY — NO RAW GLOBAL VECTOR

Não colocar transcript tenant bruto em collection global “para comparar depois”.

Global recebe abstraction sanitizada.

---

# 90. SECURITY — TENANT HASH

Cross-tenant counts:

salted hash.

Salt não pode ter insecure production default.

---

# 91. AUDIT EVENTS

Mínimo:

```text
intelligence.raw.accepted
intelligence.episode.created
intelligence.trajectory.completed
intelligence.candidate.proposed
intelligence.candidate.merged
intelligence.candidate.conflicted
intelligence.candidate.routed
intelligence.candidate.rejected
intelligence.scope.denied
intelligence.permission.denied
intelligence.pii.quarantined
```

---

# 92. DEFINITION OF DONE

A SPEC-090 fecha somente quando:

- [ ] estado atual medido e reportado;
- [ ] current HEAD registrado;
- [ ] test/technical tenants identificados;
- [ ] Global/Company/User preservados;
- [ ] Case/Session transit scope modelado;
- [ ] ownership separado de visibility/ACL;
- [ ] source permission lineage preservada;
- [ ] current ACL revalidation contract existe;
- [ ] raw ≠ Episode;
- [ ] Episode contract existe;
- [ ] Trajectory V1 existe;
- [ ] Outcome taxonomy existe;
- [ ] actor classifier existe;
- [ ] subject classifier existe;
- [ ] deterministic-first comprovado;
- [ ] UNKNOWN válido;
- [ ] Trust Tiers formalizados;
- [ ] resposta humana não vira Ground Truth;
- [ ] Scope Resolver versionado;
- [ ] reason codes;
- [ ] USER não promove COMPANY automaticamente;
- [ ] COMPANY raw não promove GLOBAL;
- [ ] Global candidate é abstração sanitizada;
- [ ] occurrence/source/tenant counts distintos;
- [ ] exact dedupe preservado;
- [ ] semantic dedupe seguro;
- [ ] contradiction antes de merge;
- [ ] temporal fields disponíveis;
- [ ] supersede preserva história;
- [ ] PII gate;
- [ ] secret gate;
- [ ] source ACL gate;
- [ ] retention class;
- [ ] Customer PII não vira user memory;
- [ ] current live data prefere source-of-truth;
- [ ] `knowledge_candidates` reutilizado/evoluído;
- [ ] nenhuma tabela `_v2` sem blocker;
- [ ] Intelligence Candidate Envelope;
- [ ] Candidate Router;
- [ ] nenhum mega registry concorrente;
- [ ] Garimpo preservado;
- [ ] Demand Intelligence aprofundado;
- [ ] Capability Gap estruturado;
- [ ] Process Candidate;
- [ ] Automation Opportunity;
- [ ] Claims routed 093;
- [ ] Routes routed 087;
- [ ] Skill gaps routed 100;
- [ ] Aux demand routed 103;
- [ ] historical backfill separado;
- [ ] live incremental separado;
- [ ] watermark;
- [ ] idempotency;
- [ ] hot/warm/cold path;
- [ ] chat/attendance latency preservada;
- [ ] Factory funnel;
- [ ] Factory health;
- [ ] no silent zero;
- [ ] Identity/Soul handoff 098 documentado;
- [ ] Channel ACL handoff 099 documentado;
- [ ] Memory/Second Brain handoff 102 documentado;
- [ ] Dreams handoff 106 documentado;
- [ ] Memories UI gaps formalizados;
- [ ] no Graphiti/Mem0/Letta authority install;
- [ ] M1–M14 red;
- [ ] scope goldens green;
- [ ] permission goldens green;
- [ ] temporal goldens green;
- [ ] zero cross-tenant leak;
- [ ] zero PII global leak;
- [ ] zero test tenant global learning;
- [ ] cost measured;
- [ ] execution report completo.

---

# 93. NOTAS DE IMPACTO

| Área | Nota |
|---|---:|
| Inteligência acumulativa | **100/100** |
| Moat de rede | **100/100** |
| Segurança multi-tenant | **100/100** |
| Segundo cérebro da corretora — fundação | **98/100** |
| Evolução do Atlas | **99/100** |
| Descoberta de processos | **99/100** |
| Produto/demanda | **97/100** |
| Claims future | **95/100** |
| Dreams — fundação | **99/100** |
| Soul — fundação | **94/100** |
| UX Memórias nesta SPEC | **70/100** — 102 resolve profundamente |

---

# 94. MUDANÇA NO NEGÓCIO

Antes:

```text
cada corretora é um cliente usando software
```

Depois:

```text
cada corretora produz experiência operacional
↓
a experiência vira evidência governada
↓
a evidência fortalece capacidades privadas
e, quando seguro, capacidades globais
```

O moat não é:

> “temos mais mensagens.”

É:

> **“temos mais trajetórias reais, outcomes comprovados, evidência governada e uma máquina capaz de transformar experiência em capacidades reutilizáveis.”**

---

# 95. CICLO FINAL QUE ESTA SPEC COMEÇA A MATERIALIZAR

```text
OPERAÇÃO
↓
TRAJECTORY
↓
LEARNING SIGNAL
↓
DREAMS
↓
KNOWLEDGE / SKILL / ROUTE CANDIDATE
↓
PROTOCOL FACTORY
↓
AAA EVAL
↓
PUBLICAÇÃO
↓
METAHARNESS
↓
OPERAÇÃO MELHOR
```

A 090 é o começo disciplinado desse ciclo.

---

# 96. REFERÊNCIAS INTERNAS OBRIGATÓRIAS

- SPEC-052 — Cérebro Cognitivo Unificado;
- SPEC-053 — Work OS;
- SPEC-055 — Work Runs;
- SPEC-056 — Skill Registry & Tool Gateway;
- SPEC-058 — Auxiliary Factory;
- SPEC-059 + Execution Report;
- SPEC-060 — Research Intelligence;
- SPEC-067 — Descobridor;
- Candidates 086–089;
- `backend/app/services/memory_service.py`;
- `backend/app/services/memory_fabric.py`;
- `backend/app/services/intelligence/knowledge_candidate_adapter.py`;
- `backend/app/services/intelligence/garimpo_v3.py`;
- `backend/app/services/intelligence/demand_cluster_service.py`;
- `backend/supabase/migrations/20260726_02_spec059_memory_fabric.sql`;
- `app/api/dashboard/memorias/route.ts`;
- `components/memorias/CerebroDeMemorias.tsx`;
- Brand Identity current code;
- Context Assembly atual;
- Atlas observed-session pipeline;
- Research/SUSEP;
- live schema.

---

# 97. REFERÊNCIAS EXTERNAS OBRIGATÓRIAS NO AQUECIMENTO AAA

- Glean Enterprise Graph / Personal Graph;
- Microsoft 365 Copilot / Semantic Index;
- Slack permission model;
- Hermes SOUL / USER / MEMORY;
- Mem0 Memory + Dream + Temporal + Decay;
- Letta Memory Blocks + Sleep-time Compute;
- LangGraph/LangMem namespaces + semantic/episodic/procedural memory;
- Graphiti/Zep temporal context graph + provenance.

Usá-las como benchmark/padrão, não como justificativa automática para instalar dependência.

---

# 98. COMANDO FINAL AO EXECUTOR

Não construa uma máquina que “guarda mais”.

Construa uma máquina que **sabe por que pode lembrar**.

Para qualquer aprendizado, o AutoBrokers precisa responder:

```text
o que observamos?
em qual operação?
quem disse?
sobre quem era?
qual outcome houve?
qual fonte?
quando era verdade?
qual permissão existia?
para quem vale?
é novo?
já sabemos?
contradiz algo?
qual confiança?
qual risco?
contém PII?
qual candidate deve nascer?
quem pode aprovar?
onde ele deve viver?
```

Se uma resposta necessária para segurança/verdade estiver desconhecida:

> **UNKNOWN/CANDIDATE é melhor que certeza inventada.**

Essa é a Fábrica de Inteligência do AutoBrokers.
