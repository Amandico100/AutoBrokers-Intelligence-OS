# SPEC-090 — RESEARCH PACK
## Fábrica de Inteligência Operacional, Segundo Cérebro, Memory Scoping, Soul, Dreams e Enterprise Context

**Data:** 25/08/2026  
**Baseline:** `19f41eedc5808cf1099ede19d2a88be502854485`  
**SPEC:** `SPEC-090-fabrica-de-inteligencia-operacional.md`  
**Uso:** insumo de pesquisa para o Protocolo AutoBrokers AAA; não carregar inteiro em todo bootstrap.

---

# 1. VEREDITO

O melhor sistema de memória para o AutoBrokers **não é uma biblioteca única**.

É uma arquitetura vertical governada:

```text
PERMISSIONED SOURCES
+
EPISODES
+
TRAJECTORIES
+
TEMPORAL FACTS
+
GLOBAL / COMPANY / USER OWNERSHIP
+
SOURCE ACL
+
PROVENANCE
+
CANDIDATE LIFECYCLE
+
DREAM CONSOLIDATION
+
CONTEXT ASSEMBLY
+
SECOND BRAIN UI
```

As ferramentas externas são benchmarks excelentes.

A autoridade deve continuar AutoBrokers.

---

# 2. ESTADO REAL: A ARQUITETURA CERTA JÁ EXISTE EM ALTO NÍVEL

A SPEC-052 já define:

```text
Global
Brokerage
User
```

e categorias como:

```text
session
semantic user
semantic brokerage
episodic
procedural
preference
performance
agent
```

Ela também determina:

```text
evidence
→ candidate
→ curation
→ publish
```

Portanto:

> **não construir outro cérebro. Completar e consolidar o que já existe.**

---

# 3. SPEC-059: BOA FUNDAÇÃO, NÃO PRODUTO FINAL

A SPEC-059 criou:

```text
company_memories
knowledge_candidates
MemoryFabric
Garimpo v3
Demand Radar
```

O Execution Report também encontrou um exemplo essencial de observabilidade: o trigger de memory summarization estava efetivamente inerte, com ausência de `session_summaries`, embora o código existisse.

Lição:

> memory pipeline precisa de health, não só implementação.

---

# 4. CURRENT USER MEMORY

`MemoryService` atual:

- extrai fatos;
- guarda session summaries;
- consolida poucos fatos;
- injeta fatos recentes + resumos + pending;
- permite filtro opcional por `agent_id`;
- possui TODO para rerank por `current_query`.

É uma boa primeira memória pessoal.

Não é ainda um Personal Graph/Second Brain.

---

# 5. CURRENT COMPANY MEMORY

`company_memories` já possui:

- scope por company;
- candidate/active/conflicted/superseded/revoked;
- evidence;
- confidence;
- trust tier;
- occurrences;
- first/last seen;
- validity;
- human confirmation;
- supersession.

Essa estrutura deve ser preservada e aprofundada.

---

# 6. CURRENT KNOWLEDGE CANDIDATE

`knowledge_candidates` já tem:

- personal/company/global;
- source;
- redacted statement;
- evidence;
- source count;
- confidence;
- trust;
- risk;
- lifecycle;
- dedupe;
- contradiction;
- PII check;
- review;
- published ref.

Isto é uma ótima base para Candidate Factory.

Não criar `_v2`.

---

# 7. CURRENT LIMITS

### Dedupe

Hash de texto normalizado não resolve paráfrases.

### Contradiction

Overlap lexical + negação pega casos óbvios, mas não é semanticamente robusto.

### Source count

Precisa ser auditado para provar independência.

### ACL

Memory/candidate ainda precisa incorporar provenance de source permissions.

### Temporal

Precisa diferenciar quando aprendemos de quando era verdade.

---

# 8. CURRENT GARIMPO

Uma das melhores decisões atuais:

> “o corretor declarou” ≠ “isto é verdade”.

Preservar.

Evoluir para Demand/Intent Intelligence, não um novo Desire Agent.

---

# 9. CURRENT DEMAND RADAR

Bom:

- tenant hash;
- distinct tenant count;
- Auxiliary Requests;
- Capability Gaps;
- Intelligence Signals;
- demand lifecycle.

Aprofundar:

- semantic outcome normalization;
- workflow context;
- avoid overmerge.

---

# 10. CURRENT MEMORIES DASHBOARD

A rota atual agrega manualmente:

- documents;
- global documents;
- user_memories;
- conversations;
- URA maps;
- conduct playbooks;
- knowledge cards.

Ela não projeta de forma completa:

- company_memories;
- knowledge_candidates;
- Intelligence Signals;
- todo Research/SUSEP;
- todos os learning objects.

Isso explica a sensação de memória incompleta.

A correção profunda pertence à SPEC-102.

---

# 11. CURRENT BRAND IDENTITY

A tela atual de Identidade é principalmente:

- logo;
- cores;
- site;
- Instagram;
- LinkedIn;
- Google Business;
- tagline;
- visual style;
- provenance/confidence/human edit.

Isso é **Brand Identity**.

Não é Company Soul completo.

SPEC-098 deve se tornar:

# **Identity Fabric & Company/User Soul**

---

# 12. HERMES — A MELHOR REFERÊNCIA DE CLAREZA ONTOLÓGICA

Hermes separa:

```text
SOUL.md    = quem o agent é
USER.md    = quem o usuário é
MEMORY.md  = o que foi aprendido
AGENTS/... = contexto do projeto
Skills     = como fazer
```

Isso é simples e muito bom.

AutoBrokers deve modelar a separação, mas com:

- DB;
- tenant isolation;
- provenance;
- versions;
- permissions;
- human overrides.

Referências:
- https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what/
- https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/
- https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers/

---

# 13. HERMES — OUTROS PADRÕES ÚTEIS

Current Hermes:

- bounded curated memory;
- user profile separado;
- session search on-demand;
- memory write approval opcional;
- background review pode gerar memory/Skill updates;
- external providers como plugin seam.

Aproveitar:

```text
separação
curadoria
progressive disclosure
provider seam
write gate
```

Não aproveitar:

```text
flat Markdown como truth SaaS
profile-only scope
auto-write irrestrito
```

---

# 14. GLEAN — MELHOR ANALOGIA DE “SEGUNDO CÉREBRO DA EMPRESA”

Glean trabalha com:

```text
Enterprise Graph
+
Personal Graph
```

Enterprise Graph:

- empresa;
- pessoas;
- conteúdo;
- relações;
- processos/contexto.

Personal Graph:

- goals;
- commitments;
- priorities;
- work habits;
- communication/writing styles.

Os dois trabalham juntos.

AutoBrokers pode traduzir para:

```text
Brokerage Context / Company Brain
+
User Work Context / Personal Brain
+
Global Insurance Knowledge
```

Referências:
- https://www.glean.com/enterprise-context/enterprise-graph
- https://www.glean.com/enterprise-context/personal-graph
- https://www.glean.com/ai-agents/agent-governance

Score conceitual:

# **100/100**

---

# 15. MICROSOFT 365 COPILOT — REFERÊNCIA DE PERMISSÃO

Microsoft Copilot usa Microsoft Graph e Semantic Index, mas só entrega conteúdo que o usuário atual já tem permissão para visualizar.

Também mantém ACL para dados de connectors externos.

Regra AutoBrokers:

> **Indexing does not grant access.**

Essa é uma das principais decisões da 090.

Referências:
- https://learn.microsoft.com/en-us/deployoffice/privacy/microsoft-365-copilot
- https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot

Score:

# **100/100 para permission-aware context**

---

# 16. SLACK

Slack não é a melhor referência para taxonomia de memória.

É boa referência para source permissions:

- public channel;
- private channel;
- DM;
- saved personal items.

Ao conectar Slack, o AutoBrokers deve preservar a fronteira.

Slack entra mais profundamente na SPEC-099.

---

# 17. SCOPE ≠ ACL

Talvez o refinamento mais importante desta pesquisa.

Uma informação pode ser:

```text
ownership = COMPANY
```

mas:

```text
visibility = managers
```

ou:

```text
visibility = original_source_acl
```

Separar as duas dimensões evita o falso modelo:

> “se é conhecimento da corretora, todos podem ver.”

---

# 18. MEM0 — SCOPING

Mem0 possui scoping por IDs como:

```text
user_id
agent_id
run_id
app_id
```

É boa referência de entity-scoped memory.

AutoBrokers não deve copiar o significado de `agent_id` como verdade pessoal.

Referência:
- https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-types.mdx

---

# 19. MEM0 PIPELINE

Mem0, no caminho de inferência, recupera memórias relacionadas e decide:

```text
ADD
UPDATE
DELETE/NOOP
```

É um bom benchmark para memory write/reconciliation.

---

# 20. MEM0 DREAM — REFERÊNCIA DIRETA PARA SPEC-106

Lançado em agosto de 2026.

Dream executa background consolidation:

```text
MERGE
SUPERSEDE
SYNTHESIZE
```

Características relevantes:

- mantém history;
- merged memory aponta para replacement;
- outdated facts ficam superseded;
- recurring behavior pode virar higher-order memory;
- synthesis roda fora do request path;
- conditional writes reduzem conflito concorrente.

Referência:
- https://mem0.ai/blog/dream-background-memory-consolidation-for-ai-agents

Nota de inspiração para Dreams AutoBrokers:

# **99/100**

---

# 21. MEM0 MEMORY DECAY

Mem0 também introduziu decay/rerank baseado em recência/uso.

Importante:

> stale memory não é apagada; apenas perde peso.

Útil para 102.

Referência:
- https://mem0.ai/blog/introducing-memory-decay-in-mem0

---

# 22. MEM0 TEMPORAL REASONING

Mem0 adicionou raciocínio sobre quando uma memória era verdadeira.

Útil para:

- mudança de função;
- mudança de preferência;
- insurer procedure;
- process changes.

Referência:
- https://mem0.ai/blog/introducing-temporal-reasoning-in-mem0

---

# 23. MEM0 SECURITY CAUTION

Issues recentes no próprio projeto mostraram problemas de identity-scoping em caminhos de SDK/metadata.

Lição:

> **tenant/user identity authority precisa continuar no AutoBrokers.**

Não terceirizar isolamento para um memory SDK.

---

# 24. LETTA — MEMORY BLOCKS

Letta trata memória como state explícito e pode compartilhar blocos entre agents.

Boa referência para:

- curated blocks;
- shared state;
- manageable memory.

Não é razão para trocar runtime.

---

# 25. LETTA — SLEEP-TIME COMPUTE

Pesquisa de 2025 propõe usar períodos de inatividade para reorganizar/rewrite memory state.

Benefícios:

- trabalho fora do latency path;
- preparação de contexto;
- consolidação;
- processamento de grandes fontes em background.

É uma referência central para 106.

Referência:
- https://www.letta.com/blog/sleep-time-compute/

---

# 26. LANGGRAPH / LANGMEM — REFERÊNCIA NATIVA

LangGraph diferencia:

```text
short-term/thread memory
long-term memory
```

Long-term pode usar namespace hierárquico.

LangMem trabalha com:

```text
semantic
episodic
procedural
```

e exemplos de namespace por organização/usuário/contexto.

Como AutoBrokers já usa LangGraph, isso é particularmente valioso.

Referências:
- https://docs.langchain.com/oss/python/langchain/long-term-memory
- https://docs.langchain.com/oss/python/concepts/memory
- https://github.com/langchain-ai/langmem

Score:

# **99/100 como modelo nativo**

---

# 27. GRAPHITI / ZEP — MELHOR REFERÊNCIA DE TEMPORAL CONTEXT GRAPH

Graphiti modela:

```text
Episodes
Entities
Facts/Relationships
Temporal validity
Provenance
```

Destaques:

- fact validity windows;
- old truth preserved;
- every fact traces to Episode;
- incremental updates;
- hybrid retrieval;
- bi-temporal reasoning.

Referência:
- https://github.com/getzep/graphiti

Score dos conceitos:

# **98/100**

---

# 28. GRAPHITI — CAUTION

Adicionar Graphiti agora implicaria outro graph backend/infra e outra camada de transformação.

Além disso, discussões atuais apontam necessidade de governance extra para:

- PII ingestion;
- fact-level access;
- retrieval audit.

Então:

```text
instalar na 090 = 35/100
benchmark em 102 = 95/100
```

---

# 29. PROPOSTA DE TAXONOMIA FUTURA

Provável modelo de 102:

```text
WORKING
SEMANTIC
EPISODIC
PROCEDURAL
PREFERENCE
IDENTITY
PERFORMANCE
```

Mas nem tudo precisa morar em “memory table”:

- procedural → Skill/Protocol;
- identity → Soul;
- working → Work Run/thread;
- semantic → Memory/Knowledge;
- episodic → Trajectory/Episode.

---

# 30. EPISODE E TRAJECTORY

A principal melhoria sobre memory extraction de chat:

```text
message-level
```

vira:

```text
operation-level
```

Sem outcome, uma resposta humana só prova que foi dita.

Com outcome, podemos saber se:

- seguradora aceitou;
- protocolo veio;
- pagamento recuperou;
- cliente confirmou.

---

# 31. TEMPORALIDADE

Guardar quando descobrimos e quando era verdade:

```text
ingested_at
valid_from
valid_until
invalidated_at
```

Isso vem diretamente da lição de temporal context graphs e Mem0 temporal.

---

# 32. PROVENANCE

Cada derived fact precisa apontar para Episode/source.

Sem provenance, autoevolução vira “a IA acha que aprendeu”.

---

# 33. COMPANY SOUL — 098

A 098 deverá conter:

## Company

- propósito;
- service philosophy;
- value proposition;
- voice;
- terminology;
- values;
- priorities;
- explicit policies;
- forbidden behavior;
- brand identity.

## User

- role;
- responsibilities;
- decision rights;
- goals;
- communication preferences;
- work patterns;
- writing profiles.

Cada campo:

```text
explicit / inferred candidate
source
confidence
human_edited
```

Human edited wins.

---

# 34. DREAMS — 106

A melhor combinação encontrada:

```text
Mem0 Dream
+
Letta Sleep-time
+
AutoBrokers Candidate Governance
```

Fluxo proposto:

```text
NEW ACTIVITY
↓
Dream selection
↓
merge/supersede/reconfirm/synthesize
↓
candidate
↓
risk/scope gates
↓
publish/curate through existing authorities
```

Não “rodar tudo todas as noites”.

Preferir incremental/event-driven + scheduled maintenance.

---

# 35. SECOND BRAIN UI — 102

A futura tela deve ser uma projeção, não fonte de verdade.

Provável Brain Projection Service:

```text
Global
Company
Personal
Experiences
Procedures
Connections
```

Cada item:

```text
canonical_ref
type
layer
safe_title
safe_summary
status
updated
source_ref
detail_route
permission
```

Isso resolve a queixa de clicar e não chegar à memória real.

---

# 36. CURRENT UI PROBLEM

Hoje o Second Brain é visualmente sofisticado, mas o backend de projeção é manual e parcial.

Adicionar mais ifs na UI agora seria dívida.

090 documenta.

102 corrige estruturalmente.

---

# 37. WHY 090 BEFORE 102/106

Se Dreams ou graph memory vier antes de:

- scope;
- provenance;
- ACL;
- Actor/Subject;
- Evidence;
- temporal model;

o sistema vai consolidar lixo com eficiência.

Primeiro Factory.

Depois Memory.

Depois Dreams.

---

# 38. RECOMMENDED SEQUENCE

```text
090 Intelligence Factory
↓
091 Protocol & Process Factory
...
098 Identity Fabric & Soul
099 Channel Fabric
100 Skill/Capability Factory
...
102 Knowledge & Memory Factory / Second Brain
...
105 Trajectory Replay/Fork
106 Dreams
107 Trust Gate
108 MetaHarness
109 Engine
```

---

# 39. FINAL SCORES

| Referência | Ideias | Instalar agora |
|---|---:|---:|
| Glean | **100** | n/a — produto externo |
| Microsoft Copilot permissions | **100** | n/a |
| Hermes ontology | **98** | **20** runtime |
| Mem0 | **98** | **40** |
| Mem0 Dream | **99** | não como authority |
| Letta sleep-time | **96** | **25** runtime |
| LangGraph/LangMem | **99** | já é stack-base |
| Graphiti | **98** | **35** agora / **95** benchmark |
| Slack permission semantics | **95** | entra como connector na 099 |

---

# 40. RESEARCH CONCLUSION

A melhor arquitetura não é “Mem0 + Graphiti + Letta + Hermes”.

É:

```text
AutoBrokers Memory/Intelligence Fabric
        ↑
        ├─ Glean: Enterprise + Personal Graph concept
        ├─ Microsoft: permission-aware grounding
        ├─ Hermes: Soul/User/Memory/Skill separation
        ├─ Mem0: scoped memory + Dream + lifecycle
        ├─ Letta: sleep-time maintenance
        ├─ LangGraph/LangMem: native namespaces/types
        └─ Graphiti: episodes + temporal facts + provenance
```

Tudo modelado para seguros, multitenancy, PII, source-of-truth e governança.

---

# 41. URL INDEX

Hermes  
https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what/  
https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/  
https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers/

Glean  
https://www.glean.com/enterprise-context/enterprise-graph  
https://www.glean.com/enterprise-context/personal-graph  
https://www.glean.com/ai-agents/agent-governance

Microsoft  
https://learn.microsoft.com/en-us/deployoffice/privacy/microsoft-365-copilot  
https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot

Mem0  
https://github.com/mem0ai/mem0  
https://mem0.ai/blog/dream-background-memory-consolidation-for-ai-agents  
https://mem0.ai/blog/introducing-memory-decay-in-mem0  
https://mem0.ai/blog/introducing-temporal-reasoning-in-mem0

Letta  
https://www.letta.com/blog/sleep-time-compute/

LangGraph/LangMem  
https://docs.langchain.com/oss/python/langchain/long-term-memory  
https://docs.langchain.com/oss/python/concepts/memory  
https://github.com/langchain-ai/langmem

Graphiti/Zep  
https://github.com/getzep/graphiti

---

# 42. FINAL RULE

> **Everything can create evidence. Almost nothing should become durable truth immediately.**

Essa é a regra mais importante para construir um Segundo Cérebro que melhora sem virar um cérebro que acumula erro.
