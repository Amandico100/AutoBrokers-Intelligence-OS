# 38A0 — Auxiliares Runtime Recon

> **Status:** recon read-only concluído · **somente este relatório foi criado** (nenhum código/SQL/migration/runtime alterado).
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main · **Tipo:** auditoria + proposta (sem implementação).

## 1. Resumo executivo
O runtime Smith **já tem tudo o que o primeiro Auxiliar precisa**, exceto a **camada de produto "Auxiliares"** (catálogo + instalação por tenant + execuções). A recomendação (alinhada a ADR-001 §10 e UX-007 §20 Opção A) é **não criar motor novo**: criar 3 tabelas de produto (`auxiliary_templates`, `tenant_auxiliaries`, `auxiliary_runs`) e executar o **Auxiliar de Resumo de Atendimentos** como uma **tarefa de sumarização** que lê `conversations`/`messages` e reusa a lógica que já gera `session_summaries`. Execução **síncrona** no MVP (resumo leva segundos), **read-only**, **sem ação externa**, com custo logado em `token_usage_logs` e histórico em `auxiliary_runs`. Celery/Redis existem e ficam reservados para quando houver execução longa/agendada. **Nada bloqueia o Resumo** (não há ação externa); Vault/HITL só travam Auxiliares que enviam/alteram dados.

## 2. Arquivos e áreas lidas
- **Canon:** `UX-007-auxiliares.md` (completo), `ADR-001-runtime.md` (completo); referência cruzada a PRD-001/ADR-002/ADR-003/ROADMAP-001 e relatórios 37B3/37B4/37B5.
- **Schema:** `backend/supabase/migrations/schema_completo.sql` — inventário de 37 tabelas + DDL de `agents`, `agent_delegations`, `conversations`, `messages`, `conversation_logs`, `session_summaries`, `documents`, `token_usage_logs`, `credit_transactions`, `sanitization_jobs`. Contagem de RLS.
- **Backend:** rotas FastAPI (`backend/app/api/*.py`), serviços (`backend/app/services/*.py`), workers (`backend/app/workers/*.py` — Celery).
- **Frontend:** rotas Next (`app/api/**/route.ts`), Auxiliares do 37B4 (`app/dashboard/auxiliares/*`), padrões 37B3 (`components/patterns`, `components/modules`, `lib/mock/tenant-modules.ts`).
- **Não aberto** (PII/credenciais/bruto): intake, QUARENTENA, ResultVision (apenas conceito, sem cópia).

## 3. Estado atual do runtime
- **Engine:** Next 15 (App Router) + FastAPI + LangGraph; chat via SSE (`/api/chat/stream` → backend `chat.py`). Streaming, agentes, conversas, realtime e voz funcionando (preservados em 37B2).
- **Agentes:** tabela `agents` (multi-tenant, por `company_id`), subagentes via `is_subagent`/`allow_direct_chat` e **`agent_delegations`** (orchestrator→subagent, `task_description`, `max_iterations`, `timeout_seconds`) — base para delegação futura (SubAgentTool).
- **LLM/serviços:** `services/langchain_service.py` (chamada LLM), `services/memory_service.py` (**gera `session_summaries`** — sumarização de sessão já existe), `services/usage_service.py` (registra uso/custo), `services/search_service.py`/`qdrant_service.py`/`document_service.py` (RAG).
- **Async:** **Celery + Redis existem** (`workers/celery_app.py`, `workers/sanitization_tasks.py`, `workers/billing_tasks.py`). Padrão job assíncrono pronto, mas hoje só usado em sanitização/billing.
- **Auth/tenant:** rotas Next usam iron-session (`smith_user_session`) + Supabase **service role**; `company_id` resolvido via `users_v2`. Isolamento de tenant é aplicado **no código** (filtros `eq('company_id', …)`), com **RLS** também presente no banco (78 policies).

## 4. Estado atual do banco/migrations
- **Schema oficial:** `backend/supabase/migrations/schema_completo.sql` (dump pg_dump). É a fonte de verdade do schema; como houve cleanup manual recente (37B2.2), **confirmar o estado real no Supabase** antes de gerar SQL (o dump pode estar levemente atrás de ajustes manuais).
- **37 tabelas.** Relevantes para Auxiliares:
  - `conversations` (id, user_id, session_id, title, company_id, status, channel, agent_id, last_message_at…) — **fonte do Resumo**.
  - `messages` (id, conversation_id, role `user|assistant`, content, type `text|voice`, created_at) — **conteúdo do Resumo**.
  - `conversation_logs` (turno a turno: pergunta/resposta, tokens, rag_chunks, status, error, **`internal_steps` jsonb = traces de subagents**).
  - **`session_summaries`** (summary, **topics[]**, **decisions[]**, **pending_items[]**, messages_count, session_id, company_id, agent_id) — **quase o output exato do Resumo**.
  - `token_usage_logs` (company_id, agent_id, service_type, model_name, input/output_tokens, total_cost_usd, details jsonb, billed) — **custo/tokens**.
  - `credit_transactions` (consumo em BRL por company/agent) — débito de crédito.
  - `sanitization_jobs` (id, company_id, status `pending|…`, progress, error_message, timestamps, **expires_at**) — **molde de tabela "job/run com status"**.
  - `agents`, `agent_delegations`, `documents` (RAG), `agent_http_tools`, `agent_mcp_*` (tools/MCP).
- **NÃO existe** nenhuma tabela de Auxiliares/rotinas/execuções: nada de `auxiliary_*`, `routine_runs`, `task_runs`, `automations`, `executions`, `jobs` (exceto `sanitization_jobs`, específico). **Esta é a lacuna central.**

## 5. Estado atual do frontend de Auxiliares
Criado no 37B4 (mock, sem backend):
- `app/dashboard/auxiliares/page.tsx` — central (cards Meus/Galeria/Execuções + destaque Resumo).
- `app/dashboard/auxiliares/galeria/page.tsx` — `GalleryGrid` dos modelos (Resumo navegável; demais "Em breve").
- `app/dashboard/auxiliares/galeria/resumo-atendimentos/page.tsx` — **`'use client'`**: `DetailShell` (abas Visão geral/Como funciona/Permissões/Execuções) + **`PermissionModal`** no botão "Ativar com segurança".
- `app/dashboard/auxiliares/meus/page.tsx` e `execucoes/page.tsx` — `ModulePlaceholder` (empty states).
- Dados mock em `lib/mock/tenant-modules.ts` (`auxiliaresGaleria`, `resumoPermissions`). Padrões reutilizáveis em `components/patterns` (StatusPill com tons pendente/rodando/concluído/falhou/aprovação já cobríveis).

## 6. O que já existe e pode ser reutilizado
| Necessidade do Auxiliar | Reuso existente |
|---|---|
| Sumarizar conversa | `services/memory_service.py` (já cria `session_summaries`) + `services/langchain_service.py` |
| Output estruturado (resumo+pendências+próximos passos) | shape de `session_summaries` (summary/topics/decisions/pending_items) |
| Custo/tokens | `services/usage_service.py` + `token_usage_logs` (+ `credit_transactions`) |
| Padrão "job com status" | `sanitization_jobs` + `workers/sanitization_tasks.py` (Celery) + rotas `/api/sanitization/*` |
| Execução assíncrona (futuro) | Celery/Redis já configurados |
| UI (galeria/detalhe/modal/status) | `components/patterns` (37B3) + telas 37B4 |
| Auth/tenant | iron-session + `users_v2.company_id` (padrão de `app/api/agents/route.ts`) |
| Delegação futura p/ subagente | `agents` + `agent_delegations` + SubAgentTool |
| Dados de leitura do Resumo | `conversations` + `messages` (sem RAG no MVP) |

## 7. Lacunas críticas
1. **Sem camada de produto de Auxiliares** (catálogo global, instalação por tenant, execuções/histórico).
2. **Sem tabela de execuções** (`auxiliary_runs`) → impossível registrar status/resultado/custo/erro hoje.
3. **Sem endpoint de execução** do Auxiliar (nem Next nem FastAPI).
4. **Frontend é mock** — botões "Ativar/Executar" não chamam nada real; Execuções não lê nada.
5. **Confirmar dados no sandbox** (quantas `conversations`/`messages` o tenant de teste tem) — necessário para o Resumo ter o que resumir.
6. **`session_summaries` é por `session_id`**, não por "run de auxiliar" — serve de inspiração/co-gravação, mas não substitui `auxiliary_runs`.

## 8. Decisão recomendada de arquitetura
**Opção A (camada de produto sobre o motor Smith), confirmada por ADR-001 §10 e UX-007 §20.** Para o **primeiro** Auxiliar (Resumo), nem é preciso criar um `agent`/subagent novo: é uma **tarefa fixa de sumarização** (1 chamada LLM sobre `messages`). 
- **Representação do Auxiliar (resposta à pergunta 2 = combinação c+d):** **template global** (`auxiliary_templates`) **+ instalação por tenant** (`tenant_auxiliaries`) **+ execuções** (`auxiliary_runs`). O `agent_id` fica **opcional** em `tenant_auxiliaries` (nulo no Resumo MVP; usado quando o Auxiliar precisar de tools/RAG/delegação).
- **Execução MVP:** **síncrona** (resumo é rápido). Cria `auxiliary_runs(status=running)` → backend sumariza → atualiza para `completed` com `output`. Celery fica reservado para Auxiliares longos/agendados (já existe).
- **Não fazer agora:** motor paralelo (Opção B, 42/100), prompts soltos sem produto (Opção C, 55/100), scheduler, criação por prompt, conectores reais.

## 9. Modelo de dados proposto (PROPOSTA — sem SQL final)
> 3 tabelas no MVP. Todas com `id uuid pk`, `created_at`/`updated_at timestamptz`, e **RLS por `company_id`** (exceto `auxiliary_templates`, que é global). SQL final será gerado pelo Architect e executado manualmente pelo fundador.

### 9.1 `auxiliary_templates` (catálogo global — Admin)
- **Finalidade:** modelos de Auxiliar publicados pela AutoBrokers.
- **Campos:** `id`, `slug` (único, ex. `resumo-atendimentos`), `name`, `description`, `category` (Análise/Financeiro/Comercial/Documentos…), `risk_level` (`baixo|medio|alto|critico`), `default_permissions jsonb`, `required_connectors text[]`, `kind text` (ex. `summary` — identifica a tarefa executável), `config_schema jsonb` (campos de personalização), `is_published boolean`, `version int`, `created_at`, `updated_at`.
- **Chaves/relações:** sem `company_id` (global). `slug` único.
- **RLS:** leitura para qualquer tenant autenticado (apenas `is_published=true`); escrita só Admin/service role.
- **Índices:** `slug` único; `category`, `is_published`.
- **Riscos:** baixo (dado de catálogo, sem PII).

### 9.2 `tenant_auxiliaries` (instância instalada por corretora)
- **Finalidade:** Auxiliar ativado por uma corretora.
- **Campos:** `id`, `company_id` (fk companies), `template_id` (fk auxiliary_templates), `display_name`, `status` (`draft|needs_config|active|paused|error`), `config jsonb` (personalização), `allowed_sources jsonb` (fontes permitidas), `permissions jsonb` (efetivas), `agent_id uuid null` (fk agents, opcional/futuro), `installed_by uuid` (fk users_v2), `last_run_at`, `next_run_at null` (scheduler futuro), `created_at`, `updated_at`.
- **Chaves/relações:** `company_id`+`template_id` (único recomendado p/ evitar duplicar instalação); `agent_id` opcional.
- **Status possíveis:** ver acima (mapeiam ao StatusPill).
- **RLS:** `company_id = tenant do usuário`.
- **Índices:** `(company_id, template_id)` único; `company_id`; `status`.
- **Riscos:** médio (config/permissões — base de segurança; nunca guardar credencial aqui → isso é Vault/ADR-002).

### 9.3 `auxiliary_runs` (execução individual)
- **Finalidade:** cada execução do Auxiliar (histórico/auditoria).
- **Campos:** `id`, `company_id`, `tenant_auxiliary_id` (fk), `template_slug` (denormalizado p/ histórico), `triggered_by uuid` (fk users_v2), `trigger_type` (`manual|scheduled|delegated`), `status` (`pending|running|completed|failed|awaiting_approval|cancelled`), `input jsonb` (ex. `{ conversation_id }`), `output jsonb` (resultado estruturado: `summary`, `pending[]`, `next_steps[]`, `risks[]`), `error_message text`, `tokens_input int`, `tokens_output int`, `cost_brl numeric(10,4)`, `model_name text`, `conversation_id uuid null` (fk conversations, quando aplicável), `agent_id uuid null`, `started_at`, `finished_at`, `created_at`.
- **Chaves/relações:** `company_id`, `tenant_auxiliary_id`, `conversation_id` opcional, `triggered_by`.
- **Status possíveis:** acima (inclui `awaiting_approval` para Auxiliares futuros com ação externa; **Resumo nunca usa**).
- **RLS:** `company_id = tenant do usuário`.
- **Índices:** `(company_id, created_at desc)` (lista de Execuções), `tenant_auxiliary_id`, `status`, `conversation_id`.
- **Riscos:** **alto-ish (LGPD)** — `output`/`input` derivam de conversas (PII). Escopo estrito por `company_id` + RLS + retenção (considerar `expires_at` como em `sanitization_jobs`).

> **Fora do MVP (fase 2+):** `auxiliary_run_events` (timeline/steps), `auxiliary_approvals` (HITL), `auxiliary_schedules` (cron), `auxiliary_run_outputs` (artefatos grandes/anexos). Não criar agora.

> **Custo:** registrar também em `token_usage_logs` (`service_type='auxiliary_run'`, `details.run_id`) para entrar no billing existente; manter `cost_brl/tokens` denormalizados em `auxiliary_runs` para exibição rápida.

## 10. APIs propostas (PROPOSTA — não criar agora)
Camada **Next route** (auth iron-session + `company_id` via `users_v2` + service role), chamando o **backend FastAPI** para a execução LLM (mantém chave/logging no backend, como o chat). Nomes sugeridos:

| Endpoint | Finalidade | Input | Output | Auth | company_id | Camada |
|---|---|---|---|---|---|---|
| `GET /api/auxiliaries/templates` | lista catálogo publicado | — | templates[] | sessão | implícito | Next (lê Supabase) |
| `GET /api/auxiliaries/installed` | lista instalados do tenant | — | tenant_auxiliaries[] | sessão | filtro | Next |
| `POST /api/auxiliaries/install` | instala template no tenant | `{templateId}` | tenant_auxiliary | sessão | injeta | Next |
| `POST /api/auxiliaries/:id/run` | executa o Auxiliar | `{conversationId}` | run (com output) | sessão | valida posse | Next → **FastAPI** (sumariza) |
| `GET /api/auxiliaries/runs` | histórico de execuções | `?auxiliaryId?` | runs[] | sessão | filtro | Next |
| `GET /api/auxiliaries/runs/:runId` | detalhe da execução | — | run | sessão | valida posse | Next |

- **Backend FastAPI (novo, mínimo):** `POST /auxiliaries/summarize` (ou reusar um service) recebendo `company_id`, `conversation_id` → carrega `messages` (escopadas), chama `langchain_service`/`memory_service`, retorna `{summary, pending[], next_steps[], risks[], usage}` e registra `token_usage_logs`. Alternativa: encapsular em `services/agent_service.py`/novo `auxiliary_service.py`.
- **Riscos:** validar que `conversation_id` pertence ao `company_id` do usuário (anti-IDOR); rate-limit; nunca aceitar `company_id` do cliente.

## 11. Fluxo MVP recomendado
```
Galeria → Resumo de Atendimentos (detalhe)
  → "Ativar com segurança" → PermissionModal (confirma permissões read-only)
     → POST /install → tenant_auxiliaries(status=active)
  → "Executar" → escolher conversa (picker) 
     → POST /:id/run { conversationId }
        → cria auxiliary_runs(running)
        → FastAPI sumariza messages da conversa (escopo company_id)
        → update run(completed, output, tokens, cost) + token_usage_logs
     → UI mostra resultado + aparece em Execuções
```
- **Síncrono** (resumo em segundos). Sem fila no MVP.
- **Read-only, sem envio externo, sem HITL** (não há ação externa).
- **Auditável:** `auxiliary_runs` + `token_usage_logs` + (opcional) `system_logs`.

## 12. UX recomendada (adaptar, não reescrever — usar padrões 37B3/37B4)
- **`resumo-atendimentos`:** "Ativar" chama `/install` via `PermissionModal` (já existe); depois exibe **"Executar"** com **seletor de conversa** (lista de `conversations` do tenant). Resultado renderizado em bloco (summary + pendências + próximos passos) — **sem JSON cru** (UX-007 §22.4). Aba "Execuções" lista runs deste Auxiliar.
- **`meus`:** trocar empty state por lista real de `tenant_auxiliaries` (GalleryCard + StatusPill).
- **`execucoes`:** lista de `auxiliary_runs` (data, auxiliar, status, custo, link p/ detalhe) — detalhe da run reusa `DetailShell`/`DetailSection`.
- **Status → StatusPill (já existe):** `pending`→neutral "Pendente"; `running`→info "Rodando"; `completed`→success "Concluído"; `failed`→danger "Falhou"; `awaiting_approval`→approval "Aguardando aprovação".
- **Claude Routines vibe sem complexidade:** manter camadas (Galeria→Detalhe→Executar→Execução), microcopy simples (UX-007 §23/24), mobile-first.

## 13. Segurança, LGPD e RLS
- **PII:** `messages`/`conversations` contêm conversas reais (PII de clientes). O `output` do Resumo é PII derivada → tratar com o mesmo rigor.
- **Isolamento:** toda query escopada por `company_id` (no servidor, nunca confiar no cliente). **RLS** nas 3 tabelas novas (defense-in-depth; o app usa service role, mas RLS protege acessos diretos).
- **Anti-IDOR:** validar posse de `conversation_id`/`runId`/`auxiliaryId` pelo `company_id` do usuário.
- **Auditoria:** registrar execução (quem/quando/qual auxiliar/resultado/custo) em `auxiliary_runs` (+ `system_logs` para ações sensíveis).
- **Sem ação externa** no Resumo (sem WhatsApp/e-mail/portal). Qualquer Auxiliar com ação externa → **bloqueado até ADR-002 (Vault) + HITL**.
- **Sem intake bruto / sem RAG massivo** no MVP. Retenção: considerar `expires_at` para `auxiliary_runs` (como `sanitization_jobs`).
- **Custo:** logar em `token_usage_logs` e (se aplicável) debitar `company_credits` via `credit_transactions`, reusando `usage_service`.

## 14. Dependências
- **SQL manual (Supabase):** criar `auxiliary_templates`, `tenant_auxiliaries`, `auxiliary_runs` + RLS + índices + **seed do template `resumo-atendimentos`**. Confirmar schema real antes.
- **Backend:** endpoint/serviço de sumarização (reusa `langchain_service`/`memory_service`) + log de custo (`usage_service`).
- **Frontend:** 6 rotas Next (`/api/auxiliaries/*`) + ligar telas do 37B4 (resumo detalhe, meus, execucoes) + seletor de conversa.
- **Dados:** ≥1 conversa com mensagens no tenant sandbox (confirmar/contar).
- **Bloqueado até ADR/Vault/HITL:** conectores reais, ação externa, scheduler, criação por prompt, delegação automática pelo AutoBrokers.

## 15. O que NÃO fazer (nesta fase funcional inicial)
Scheduler, criação por prompt, WhatsApp/e-mail/portal/seguradora real, InfoCap/Quiver/n8n, MCP novo, RAG massivo, ingestão de intake bruto, worker novo sem plano, billing por Auxiliar, ações sem aprovação, motor paralelo, migração de corredores. (ADR-001 §24, UX-007 §28.)

## 16. Riscos P0/P1/P2
- **P0 — Vazamento cross-tenant** do `output`/conversas: mitigar com escopo `company_id` + RLS + anti-IDOR antes de expor qualquer endpoint.
- **P0 — Schema real ≠ dump:** confirmar no Supabase antes do SQL (houve cleanup manual em 37B2.2).
- **P1 — Falta de dados no sandbox:** Resumo sem conversas = sem valor demonstrável; contar/semear antes.
- **P1 — Custo/loop LLM:** limitar tamanho da conversa enviada (janela), logar custo, timeout.
- **P1 — Escopo de produto inflar:** manter 3 tabelas + execução síncrona; não adicionar HITL/scheduler/connectors no primeiro corte.
- **P2 — Duplicar `session_summaries`:** decidir se o Resumo co-grava em `session_summaries` ou só em `auxiliary_runs.output` (recomendo `auxiliary_runs` como canônico; `session_summaries` opcional).
- **P2 — RLS vs service role:** garantir policies mesmo usando service role (defense-in-depth).

## 17. Perguntas para Architect/Fundador
1. **3 tabelas** (`auxiliary_templates`/`tenant_auxiliaries`/`auxiliary_runs`) ou começar com só `auxiliary_runs` + um template "hardcoded" em código? (Recomendo as 3 — vira produto.)
2. Resultado do Resumo: **só em Execuções** (recomendado) ou também **postar no chat** do AutoBrokers?
3. O Resumo deve **co-gravar `session_summaries`** ou apenas `auxiliary_runs.output`?
4. Execução **síncrona** (recomendado) ou já via **Celery** desde o MVP?
5. Fonte do MVP: **uma conversa selecionada** (recomendado) ou **todas as conversas recentes** (mais custo/risco)?
6. Confirma **postura read-only/sem HITL** para o Resumo (já que não há ação externa)?
7. Há conversas suficientes no **tenant sandbox** para testar? (precisa SELECT de contagem — read-only.)
8. "Ativar" deve **instalar** (criar `tenant_auxiliaries`) e "Executar" ser separado, ou **ativar já executa** a primeira vez?

## 18. Próximo batch recomendado
**38A1 — Auxiliares Data Model + SQL manual (proposta executável).** Conteúdo:
1. Confirmar schema real no Supabase (SELECT read-only: existência/contagem de `conversations`/`messages` do tenant + ausência de `auxiliary_*`).
2. Architect gera o **SQL final** (3 tabelas + RLS + índices + seed `resumo-atendimentos`) em `docs/sql/38A1-*.sql` para o fundador rodar manualmente.
3. (Opcional, separado) **38A2 — backend summarize endpoint** e **38A3 — Next API + ligar UI**.
Manter a regra: SQL/back/front em batches pequenos e reversíveis.

## 19. Checklist para SQL manual futuro (Architect gera, fundador roda)
- [ ] SELECT de confirmação: tabelas `auxiliary_*` **não** existem; contar `conversations`/`messages` por `company_id` do sandbox.
- [ ] `CREATE TABLE auxiliary_templates` (global) + índice `slug` único + `is_published`.
- [ ] `CREATE TABLE tenant_auxiliaries` + FK company/template + único `(company_id, template_id)` + RLS por `company_id`.
- [ ] `CREATE TABLE auxiliary_runs` + FKs + índices `(company_id, created_at desc)`/`status`/`conversation_id` + RLS.
- [ ] Policies RLS (select/insert/update) por `company_id`; templates legíveis a todos autenticados (publicados).
- [ ] Seed: 1 row em `auxiliary_templates` (`slug='resumo-atendimentos'`, `kind='summary'`, `risk_level='baixo'`, permissões read-only).
- [ ] (Opcional) `expires_at` em `auxiliary_runs` para retenção.
- [ ] Idempotência (`if not exists`) + nenhum DELETE.

## 20. Checklist para implementação futura
- [ ] **Backend:** serviço/endpoint `summarize` (reusa `langchain_service`/`memory_service`), escopo `company_id`, janela de contexto limitada, log em `token_usage_logs` via `usage_service`.
- [ ] **Next API:** `GET templates`, `GET installed`, `POST install`, `POST :id/run`, `GET runs`, `GET runs/:id` (iron-session + `company_id` + anti-IDOR).
- [ ] **Frontend:** ligar `resumo-atendimentos` (Ativar→install via PermissionModal; Executar→seletor de conversa→run→resultado), `meus` (lista real), `execucoes` (lista de runs + detalhe), StatusPill por status.
- [ ] **Checks:** `npm run typecheck` + `npm run build` verdes; chat intacto; isolamento por tenant testado.
- [ ] **Segurança:** RLS ativa; sem ação externa; auditoria; sem intake bruto.
- [ ] **Demonstração:** executar Resumo sobre uma conversa real do sandbox e ver o resultado em Execuções.
