# RAG0.1 — Supabase Live Database Audit for Knowledge OS

**Status:** auditoria live Supabase concluída como complemento do RAG0  
**Data:** 2026-06-18  
**Projeto Supabase auditado:** `AutoBrokers Intelligence OS`  
**Project ref:** `dcajcvlzcjbmyapmklil`  
**Região:** `us-east-2`  
**Database:** PostgreSQL 17.6.1  
**Escopo:** schema, tabelas, RLS, RAG, memória, runtime, attendance, segurança e riscos para Knowledge OS.

---

## 1. Decisão executiva

O Supabase real confirma que o AutoBrokers Intelligence OS já possui uma fundação forte para RAG, memória, agentes, attendance runtime, corredores, dispatch, auxiliares, conectores, auditoria e custos.

A conclusão anterior do RAG0 continua válida: **não criar RAG paralelo**. O runtime atual deve continuar baseado em Smith: `public.documents` + MinIO + Qdrant + SearchService + Rerank + MemoryService.

Mas a auditoria live mudou uma parte importante do diagnóstico: o schema `rag.*` que aparecia no snapshot antigo **não existe no Supabase live atual**. No projeto ativo, existem apenas os schemas `public`, `storage` e `vault`. Portanto, qualquer plano de usar `rag.*` como camada de staging/curadoria deve ser tratado como decisão futura/migration, não como estrutura já disponível.

---

## 2. Projetos Supabase encontrados

| Nome | Ref | Status | Uso recomendado |
|---|---|---:|---|
| AutoBrokers - Resulta | `hcifbnlnrlabfmhexoie` | active healthy | Projeto antigo/Resulta; não auditado nesta execução |
| AutoBrokers Intelligence OS | `dcajcvlzcjbmyapmklil` | active healthy | Projeto atual do Smith/AutoBrokers auditado |
| Salomao | `vlxfafqzqbumwgimysad` | inactive | Fora de escopo |
| SCANNER FACE | `kbchncbuvqkukouffbed` | inactive | Fora de escopo |

Decisão: toda evolução RAG/Knowledge OS deve mirar o projeto `AutoBrokers Intelligence OS`, salvo quando o CEO pedir comparação com o projeto antigo `AutoBrokers - Resulta`.

---

## 3. Estrutura real de schemas

Schemas relevantes existentes no projeto live:

```txt
public
storage
vault
```

Ausente no projeto live:

```txt
rag
```

Impacto:

- O snapshot antigo mencionava `rag.sources`, `rag.documents`, `rag.chunks`, `rag.ingestion_jobs`, `rag.feedback`, `rag.exemplars`, etc.
- No projeto live, essas tabelas não existem.
- A camada canônica atual de documentos é `public.documents`.
- A camada de memória atual é `public.user_memories`, `public.session_summaries`, `public.memory_settings` e `public.memory_processing_locks`.
- Se quisermos uma camada `rag.*`, ela precisa nascer em RAG1/RAG2 como migration controlada, e não como runtime paralelo.

---

## 4. Inventário resumido de tabelas principais e volumes

| Tabela | Linhas | Papel no Knowledge OS |
|---|---:|---|
| `public.companies` | 2 | tenants/corretoras |
| `public.agents` | 4 | agentes Core/Attendance/Subagents |
| `public.documents` | 1 | registry atual do RAG Smith |
| `public.memory_settings` | 3 | configuração de memória por agente |
| `public.user_memories` | 0 | memória factual/perfil usuário |
| `public.session_summaries` | 0 | resumos episódicos de sessão |
| `public.conversations` | 99 | conversas web/runtime |
| `public.messages` | 655 | mensagens brutas da conversa |
| `public.conversation_logs` | 142 | logs de LLM/RAG/retrieval |
| `public.token_usage_logs` | 293 | custos/tokens/cache |
| `public.sanitization_jobs` | 0 | sanitização de documentos |
| `public.attendance_cases` | 52 | casos de atendimento operacional |
| `public.corridor_templates` | 2 | templates de corredores |
| `public.corridor_runs` | 50 | execuções de corredores |
| `public.dispatch_packets` | 7 | pacotes de dispatch/acionamento |
| `public.approval_requests` | 5 | aprovações/HITL |
| `public.auxiliary_templates` | 5 | templates de auxiliares |
| `public.tenant_auxiliaries` | 5 | auxiliares instalados por tenant |
| `public.tenant_connections` | 6 | conectores por tenant |

Leitura estratégica: a base real já tem operação suficiente para o Knowledge OS se conectar com runtime, cases, corredores, dispatch, aprovações e auxiliares. O RAG documental ainda está praticamente vazio, com apenas 1 documento de teste.

---

## 5. Agentes reais encontrados

| Agente | Slug | Role | Audience | Retrieval | Web | Docs |
|---|---|---|---|---|---:|---:|
| AutoBrokers Sandbox | `jarvys-sandbox` | `core` | `broker_internal` | semantic | false | 1 |
| Silvinha Atendimento Sandbox | `attendance-sandbox` | `attendance` | `insured_external` | semantic | false | 0 |
| TESTE Runtime Smith Agent | `teste-runtime-smith-agent-nmfi` | null | null | semantic | true | 0 |
| TESTE Runtime Smith Agent | `teste-runtime-smith-agent-nmfi-rxvt` | null | null | semantic | true | 0 |

Confirmação importante:

- `AutoBrokers Sandbox` já está marcado como `core` + `broker_internal`.
- `Silvinha Atendimento Sandbox` já está marcada como `attendance` + `insured_external`.
- Os dois agentes de teste não têm `agent_role` nem `agent_audience`; devem ser classificados ou arquivados antes de uso real.

---

## 6. Documento RAG real encontrado

| Arquivo | Tipo | Status | Chunks | Modo | Estratégia | Scope | Curation | Visibility | Agente |
|---|---|---|---:|---|---|---|---|---|---|
| `CONTEUDO RAG TESTE.txt` | txt | completed | 1 | semantic | semantic | agent | published | tenant | AutoBrokers Sandbox |

Leitura:

- O RAG real ainda está em estágio de teste.
- O documento atual já confirma que `scope`, `curation_status`, `visibility`, `version`, `source_kind`, `metadata`, `valid_from`, `valid_until` existem em `public.documents`.
- O alerta de drift do RAG0 precisa ser corrigido: no Supabase live, os campos principais de governance **já existem**.
- Ainda faltam campos explícitos como `audience`, `sensitivity`, `provenance`, `source_type` padronizado e `approval_status` dedicado.

---

## 7. `public.documents` — avaliação de maturidade

Campos positivos já presentes:

```txt
company_id
agent_id
file_name
file_type
file_size
minio_path
qdrant_collection
status
chunks_count
ingestion_mode
ingestion_strategy
quality_score
scope
knowledge_class
namespace
version
curation_status
visibility
source_kind
source_ref
source_hash
valid_from
valid_until
owner_kind
metadata
```

Lacunas para RAG1:

```txt
audience
sensitivity
provenance
review_status / approval_status
approved_by
approved_at
last_reviewed_at
usage_policy
insurer_key
line_kind
macro_service
corridor_key
subcorridor_key
source_type padronizado, se source_kind não for suficiente
```

Decisão recomendada:

- Não criar outra tabela de documentos agora.
- Evoluir `public.documents` com campos mínimos de governança.
- Usar `metadata` temporariamente para extras, mas não deixar política crítica só dentro de JSON.

---

## 8. Memória real no Supabase

Tabelas existentes:

### `public.memory_settings`

Possui 3 linhas e configura:

- modo de sumarização web;
- thresholds web;
- modo de sumarização WhatsApp;
- sliding window WhatsApp;
- threshold WhatsApp;
- extração de perfil;
- extração de resumo de sessão;
- modelo de memória;
- debounce;
- vínculo por `agent_id`.

### `public.user_memories`

Existe, mas está vazia.

Campos centrais:

```txt
user_id
company_id
agent_id
profile
facts
facts_metadata
facts_count
last_extraction_at
last_consolidation_at
```

### `public.session_summaries`

Existe, mas está vazia.

Campos centrais:

```txt
session_id
user_id
company_id
agent_id
summary
channel
messages_count
topics
decisions
pending_items
```

### `public.memory_processing_locks`

Existe, mas está vazia e **não possui primary key**, embora tenha `id` UUID. Advisor marcou como problema de performance/modelagem.

Leitura estratégica:

- A arquitetura de memória existe.
- Ela ainda não está sendo populada no projeto live ou ainda não foi ativada nas conversas atuais.
- Antes de tentar deixar agentes “muito inteligentes”, precisamos ligar e testar a memória real no runtime.

---

## 9. Runtime/Attendance/Corredores/Action Engine no banco

A estrutura operacional está mais madura que o RAG documental:

### `attendance_cases`

Tem 52 registros e suporta:

- status do caso;
- prioridade;
- canal;
- dados do segurado;
- intent;
- insurer/line/macro_service;
- corridor/subcorridor;
- policy source;
- policy snapshot;
- coverage evidence;
- verification status;
- risk level;
- handoff;
- summary e next step.

Isto confirma que a fonte de verdade operacional para cobertura/acionamento **não deve ser o RAG**, mas sim `attendance_cases`, policy snapshot, coverage evidence e readiness.

### `corridor_templates`

Tem 2 registros e suporta:

- global/tenant;
- corridor/subcorridor;
- insurer;
- line_kind;
- macro_service;
- status documental;
- status operacional;
- readiness;
- required slots;
- guardrails;
- golden tests.

### `corridor_runs`

Tem 50 registros e mantém:

- fase;
- status;
- slots;
- diagnostics;
- next_step;
- last_agent_action.

### `dispatch_packets`

Tem 7 registros e suporta:

- status;
- canal;
- provider;
- idempotency_key;
- payload;
- missing_data;
- approval_request;
- execution_result.

### `approval_requests`

Tem 5 registros e representa HITL/approvals.

Leitura estratégica:

- O banco já suporta autonomia controlada.
- Agentes podem “pensar livremente” no nível de raciocínio, mas ações externas precisam passar por readiness, dispatch packet, approval e audit trail.
- Isso não é “podar a LLM”; é separar cognição de side effect.

---

## 10. Segurança/RLS — achados críticos

O Supabase Advisor de segurança apontou problemas que impactam diretamente RAG/Memory.

### P0/P1 — Tabelas de memória sem policies

Tabelas com RLS ligado, mas sem policies:

```txt
public.memory_settings
public.session_summaries
public.user_memories
```

Impacto:

- Via client/RLS, essas tabelas podem ficar inacessíveis ou mal controladas.
- Via service role/backend, o sistema funciona, mas precisa enforcement no backend.
- Para produto SaaS multi-tenant, memória precisa política explícita por `company_id`, `agent_id`, `user_id` e role.

### P0/P1 — `messages` com SELECT anon amplo

Existe policy:

```txt
Allow realtime subscriptions on messages — role anon — SELECT — true
```

Impacto:

- Advisor também apontou múltiplas policies permissivas para anon em `messages`.
- Como `messages` tem conversas potencialmente sensíveis, isso precisa revisão imediata.
- Realtime precisa ser seguro por canal/conversa/tenant, não broad select.

### P1 — Storage buckets públicos permitem listagem

Buckets com alerta:

```txt
avatars
chat-media
voice-messages
```

Impacto:

- `chat-media` e `voice-messages` podem conter mídia sensível de conversas.
- Public bucket não deveria permitir listagem ampla.
- Para AutoBrokers, mídia de atendimento deve ser privada, assinada ou expirar.

### P1 — SECURITY DEFINER exposto para anon/authenticated

Funções expostas:

```txt
check_and_increment_rate_limit
create_user_account
debit_company_balance
get_token_usage_by_company
get_token_usage_report
get_user_for_login
```

Impacto:

- Algumas podem ser intencionais, mas precisam revisão.
- `debit_company_balance` e relatórios de uso/custo não deveriam ser chamáveis publicamente sem controle forte.

### P2 — search_path mutable em funções

Várias funções não fixam `search_path`. Deve ser corrigido para reduzir risco de hijacking/ambiguidade.

---

## 11. Performance/modelagem — achados relevantes

Supabase Advisor apontou:

- FKs sem índice em tabelas operacionais.
- Policies com `auth.uid()`/`auth.jwt()` recalculado por linha, que devem usar `(select auth.uid())` ou equivalente.
- `memory_processing_locks` sem primary key.
- Índices duplicados em algumas tabelas, incluindo `public.documents` (`idx_documents_ingestion_strategy` e `idx_documents_strategy`).
- Muitos índices ainda não usados, provavelmente porque o projeto está em sandbox/MVP.

Não remover índices agora. Primeiro o produto precisa gerar uso real. Corrigir apenas duplicatas claras e PK ausente se não houver risco.

---

## 12. Como liberar inteligência sem virar caos

A exigência do Founder é correta: os agentes não podem ser capados, engessados ou reduzidos a fluxos burros. O caminho técnico não é tirar governança. O caminho é separar quatro camadas:

```txt
1. Cognição livre da LLM
   - interpretar, comparar, deduzir, propor, planejar, argumentar, explicar.

2. Contexto correto
   - RAG curado, memória, dados estruturados, web search, tools autorizadas.

3. Ação controlada
   - Action Engine, Dispatch Packet, Portal Skills, approvals, idempotência.

4. Auditoria e segurança
   - provenance, traces, evals, PII controls, tenant isolation.
```

Assim o agente pensa com liberdade, mas não vaza dados, não promete cobertura e não aciona seguradora sem readiness.

---

## 13. Estrutura recomendada de conhecimento a partir do Supabase real

### Core/Jarvys Sandbox — `AutoBrokers Sandbox`

Status atual: já é `core` + `broker_internal`.

Deve receber primeiro:

- AutoBrokers Canon Pack;
- Insurance Fundamentals;
- Compliance/LGPD;
- Portal Browser Knowledge Pack;
- Rafael Tenant Starter Pack interno;
- Sales/Renewal Starter Pack;
- docs de arquitetura do Smith/AutoBrokers.

Pode ter web search ativável depois, mas com política de uso e logs.

### Silvinha Attendance Sandbox

Status atual: `attendance` + `insured_external`.

Deve receber somente:

- Attendance Safe Communication Pack;
- FAQ pública/sanitizada;
- procedimentos de assistência/sinistro seguros;
- Allianz Residential Starter Pack seguro;
- templates de linguagem com segurado;
- status do próprio caso via dados estruturados.

Não deve receber:

- gestão;
- financeiro;
- comissão;
- estratégia;
- credenciais;
- conversas brutas;
- dados de outros clientes.

### Auxiliares

Já existem `auxiliary_templates` e `tenant_auxiliaries`. Devem receber knowledge por função, não tudo:

- follow-up;
- resumo;
- cobrança;
- renovação;
- sinistro;
- auditoria;
- comercial.

### Attendance Runtime

Deve usar dados estruturados primeiro:

```txt
attendance_cases
policy_snapshot
coverage_evidence
corridor_templates
corridor_runs
dispatch_packets
approval_requests
```

RAG entra como apoio contextual, não fonte final de cobertura.

---

## 14. Prioridades atualizadas do RAG1 após Supabase live

### RAG1A — Segurança antes de ingestão

1. Revisar `messages` anon SELECT broad.
2. Criar policies para `memory_settings`, `user_memories`, `session_summaries`.
3. Revisar buckets `chat-media` e `voice-messages`.
4. Revisar funções SECURITY DEFINER expostas.
5. Corrigir `memory_processing_locks` sem primary key ou confirmar motivo.

### RAG1B — Governance fields no `public.documents`

Já existem muitos campos, mas faltam os mais críticos para audiência/sensibilidade:

```sql
-- ideia, não executar sem revisão
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS audience text,
ADD COLUMN IF NOT EXISTS sensitivity text,
ADD COLUMN IF NOT EXISTS provenance jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS approved_by uuid,
ADD COLUMN IF NOT EXISTS approved_at timestamptz,
ADD COLUMN IF NOT EXISTS last_reviewed_at timestamptz,
ADD COLUMN IF NOT EXISTS usage_policy jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS insurer_key text,
ADD COLUMN IF NOT EXISTS line_kind text,
ADD COLUMN IF NOT EXISTS macro_service text,
ADD COLUMN IF NOT EXISTS corridor_key text,
ADD COLUMN IF NOT EXISTS subcorridor_key text;
```

### RAG1C — Admin UX

A UI de upload deve exigir:

```txt
scope
audience
sensitivity
curation_status
visibility
source_kind/source_type
agent linkage opcional conforme scope
provenance
valid_until quando fonte externa
```

E deve bloquear:

```txt
Attendance + broker_internal
Attendance + confidential/restricted
published sem approval
global sem Admin Master/Founder
conversation bruto sem sanitização
```

### RAG1D — Runtime retrieval policy

Implementar filtros rígidos:

```txt
Core/Jarvys:
company_id + broker_internal + allowed global + allowed tenant

Attendance:
company_id + insured_external + own case evidence + corridor safe docs

Auxiliar:
company_id + função + audience correta + permission scope
```

---

## 15. Perguntas abertas após Supabase live

1. O projeto antigo `AutoBrokers - Resulta` deve ser auditado também para comparar dados operacionais reais antigos com o novo `AutoBrokers Intelligence OS`?
2. Devemos criar `rag.*` como camada oficial de curadoria/staging ou manter tudo em `public.documents` + metadata por enquanto?
3. O documento atual `CONTEUDO RAG TESTE.txt` pode ser removido depois dos testes ou deve ficar como golden smoke test?
4. Quer que a gente corrija primeiro RLS/memory/security antes de mexer na UI RAG?
5. A memória factual deve ser por `agent_id` sempre ou algumas preferências do dono/corretor devem ser globais dentro do tenant?
6. O bucket `voice-messages` pode ser privado agora ou existe dependência de URL pública no frontend atual?
7. O bucket `chat-media` pode ser privado agora ou existe dependência de leitura pública?
8. O Founder quer habilitar web search para Core/Jarvys desde o início ou apenas depois de RAG2?
9. Silvinha deve permanecer sem web search, correto?
10. Os dois agentes `TESTE Runtime Smith Agent` devem ser arquivados, classificados como subagent real ou apagados depois de backup?

---

## 16. Conclusão

O Supabase live mostra que o AutoBrokers já tem uma arquitetura rica o suficiente para criar agentes muito inteligentes: agentes configuráveis, RAG documental, memória, logs, custos, attendance runtime, corredores, dispatch, approvals, auxiliares, conectores e vault audit.

O gargalo não é criar mais infraestrutura. O gargalo é governança e ativação correta:

```txt
1. Segurança/RLS/mídia/memória.
2. Escopo/audiência/sensibilidade em documents.
3. Admin UX de curadoria.
4. Packs pequenos e avaliados.
5. Runtime retrieval com filtros.
6. Evals/provenance.
7. Agentic Harvest com review humano.
```

Próxima execução recomendada: **RAG1A — Security & Memory RLS hardening**, seguida por **RAG1B — Documents Governance Fields**.
