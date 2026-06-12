# 42A0 — Agent Intelligence Runtime Recon (READ-ONLY)

> **Status:** recon concluído · **READ-ONLY** (nenhum código/schema/SQL/rota/UI alterado, sem deploy) · alinhado a SPEC-004.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Escopo:** mapear como o runtime Smith atual monta a inteligência dos agentes, para implementar a SPEC-004 sem criar motor paralelo nem duplicar estrutura.

---

## 1. Executive summary

O Smith já tem **a maior parte da espinha dorsal** que a SPEC-004 precisa: montagem de contexto em camadas (`_build_initial_state`), prompt por agente (`agents.agent_system_prompt`), RAG por agente/tenant (estabilizado nos 41C.1.x), memória governada (4 tabelas ativas), tools (HTTP/MCP/UCP/SubAgent) e gates de ação sensível (Vault + HITL `approval_requests`). **Não há motor paralelo** — há um único caminho de chat (`graph.py` → `nodes.py`) e um único RAG (`SearchService`/`QdrantService`).

O que **falta** para a SPEC-004 é majoritariamente **declarativo e organizacional**, não um novo motor:
- O `agents` não tem campos de **papel/fronteira** (`role`, `audience`, `mission`, `non_goals`, `scope`, `*_policy`). Hoje tudo isso vive (implícito) dentro do texto livre de `agent_system_prompt`.
- **Attendance Agent** e **Corredores** **não existem em runtime** — só placeholders de UI (`/dashboard/atendimentos/*`). Precisam ser construídos depois (estruturados, **não** como RAG).
- Auxiliares não declaram `requires_knowledge/requires_memory/requires_tools/risk_level/side_effects`.
- O chat principal (broker) e o atendimento (segurado) já estão **separados por rota**, mas o Core ainda não tem blueprint que afirme "eu sou o Core, não atendo segurado".

**Recomendação central:** introduzir um **Context Package** declarativo (papel + política de contexto por tipo de agente) **por cima** do `_build_initial_state` existente, sem reescrever o runtime; começar pelos blueprints (Core, Attendance) e pelo contrato de Auxiliar — tudo incremental e compatível com Smith.

---

## 2. Mapa do runtime atual

Fluxo único do chat (broker → resposta):

1. **UI tenant** `app/dashboard/chat/page.tsx` → `selectedAgentId` (default: primeiro agente; seletor oculto) → `POST /api/chat/stream`.
2. **Proxy Next** `app/api/chat/stream/route.ts` → FastAPI `/chat/stream`.
3. **Construção do grafo** `backend/app/agents/graph.py::create_agent_graph` → compila LangGraph com checkpointer Postgres assíncrono.
4. **Montagem de estado** `backend/app/agents/graph.py::_build_initial_state` (~L406) → `initial_state, config, agent_data`.
5. **Nós** `backend/app/agents/nodes.py`: **agent node** (~L213, monta SystemMessage e chama o LLM), **tool node** (executa tools, estende `rag_chunks`), **log node** (~L559, grava `conversation_logs`).
6. **Persistência**: `conversation_logs` (turno a turno), memória assíncrona (`session_summaries`, `user_memories`).

Não há segundo runtime, segundo retriever, nem segundo pipeline de embeddings. `langchain_service.search_documents/get_rag_context` é **legado/dead** (sem callers no chat).

---

## 3. Mapa do Agent Prompt / Blueprint atual

**Tabela `agents`** (`backend/supabase/migrations/schema_completo.sql` L444–481; modelo `backend/app/models/agent.py`; service `backend/app/services/agent_service.py`). Colunas relevantes:

| Campo | Linha | Papel SPEC-004 |
|---|---|---|
| `agent_system_prompt text` | 459 | Blueprint/identidade (texto livre — sem estrutura) |
| `llm_provider/model/temperature/...` | 450–458 | Config LLM |
| `reasoning_effort`, `verbosity` | 470–471 | Config LLM avançada |
| `retrieval_mode` (`semantic`/`filesystem`) | 477 | Política de RAG (parcial) |
| `is_hyde_enabled` | 472 | Estratégia de retrieval |
| `is_subagent` | 475 | Esconde widget/WhatsApp/canais públicos |
| `allow_direct_chat` | 476 | Subagent aparece no chat de teste |
| `allow_web_search`, `allow_vision`, `vision_model` | 462–464 | Capacidades |
| `tools_config jsonb` | 466 | Config de tools (chave genérica) |
| `security_settings jsonb` | 474 | Jailbreak/NSFW/PII/URL/secret-keys |
| `widget_config jsonb` | 473 | Widget público |

**SubAgent**: `is_subagent` muda o comportamento de exposição; orquestração via tabela `agent_delegations` (orchestrator_id → subagent_id, task_description, max_context_chars, timeout, max_iterations). Expansão de prompt de subagentes ocorre em `_build_initial_state` (`expand_subagent_variables`).

**Como o prompt é aplicado:** `agent_system_prompt` → `base_instructions` → `build_composite_prompt(base_instructions)` = `static_prompt` (cacheável) → combinado com `dynamic_context` em `nodes.py`.

**Campos já disponíveis para SPEC-004:** `tools_config`, `security_settings`, `widget_config` (jsonb genéricos). **Não há** `config` de memória no `agents` (memória é tabela à parte — ver §6).

---

## 4. Mapa do Context Assembly atual

`backend/app/agents/graph.py::_build_initial_state` (L406–645) monta, na ordem:

1. **Agente** (`AgentService.get_agent_by_id`) → `real_agent_data`, `system_prompt_source = agent_system_prompt`.
2. **Memória** (`MemoryService.build_memory_context_async(user_id, company_id, current_query, agent_id, …)`) → `memory_context`.
3. **base_instructions** = `agent_system_prompt` (ou `company_config.agent_instructions` ou fallback).
4. **HTTP tools** (`agent_http_tools`) → `expand_http_tool_variables`.
5. **MCP tools** (`mcp_gateway_service.get_agent_mcp_tools`) → `expand_mcp_tool_variables`.
6. **SubAgent delegations** (`agent_delegations` + `agents`) → `expand_subagent_variables`.
7. **UCP** (`ucp_connections`) → bloco de e-commerce.
8. `static_prompt = build_composite_prompt(base_instructions)` (cacheável).
9. `dynamic_context` (NÃO cacheado): **memória** + **modo web** + **RAG prefetch** (bloco "📚 CONTEXTO RECUPERADO", 41C.1.2).
10. `composite_prompt = static_prompt + dynamic_context`; `messages = [SystemMessage(composite_prompt), HumanMessage(user_message)]`.
11. `initial_state` carrega `static_prompt`, `dynamic_context`, `system_prompt`, `rag_context`, `rag_chunks` (+ métricas RAG), `agent_data`, `company_config`, etc.

**Diferença OpenAI × Anthropic** (`nodes.py` agent node, L213–255): para **Anthropic**, monta `content_blocks` com `static_prompt` (bloco com `cache_control`) + `dynamic_context` (bloco dinâmico) → aproveita prompt caching. Para os demais, usa um único `SystemMessage(system_prompt)`. Em ambos, a injeção de RAG/memória (que está em `dynamic_context`) chega ao LLM.

**Onde entram os dados:** RAG chunks → `dynamic_context` (prefetch) e/ou tool node; memórias → `dynamic_context`; conversa/sessão/usuário/empresa → `initial_state` + `config.thread_id = company_id:session_id` (checkpointer).

> A ordem real do Smith **já se aproxima** da "Ordem base" da SPEC-004 §4.3 (system → blueprint → memória → RAG). O que falta é **perfil do tenant**, **estado de workflow/corredor** e **contrato de saída** explícitos.

---

## 5. Mapa do RAG atual

- Entrada no chat por **dois pontos** (ambos `agent_id`-scoped, `include_global=False`): **prefetch** em `_build_initial_state` (41C.1.2) e **tool** `backend/app/agents/tools/knowledge_base.py` (`knowledge_base_search`).
- `SearchService.smart_search(company_id, query, agent_id, is_hyde_enabled, include_global=False)` → `_execute_search` → `qdrant.search_similar(agent_id, include_tenant_wide=True, top_k=20)` na coleção `company_{company_id}` → rerank (Cohere, opcional) → `_format_response`.
- **Robustez (41C.1.3/41C.1.4/41C.1.5):** lexical rescue quando o reranker descarta chunk relevante; fallback de score (`rerank → qdrant → 0`) + `score_source`/`reranker_available`; health/debug (`/rag-health`, `/rag-debug`) + checklist de aceitação.
- **Isolamento:** company_id pela **coleção**; agent_id por **filtro de payload**; tenant-wide via `include_tenant_wide=True`. `include_global` **default False** e **nenhum caller** passa True (callers: `documents.py` rag-debug e `graph.py` prefetch, ambos `False`).
- **Risco de contexto excessivo:** o prefetch injeta o `content` recuperado **inteiro** no `dynamic_context` a cada turno que dispara `should_prefetch_rag`. Para o Core (perguntas amplas) isso pode inflar tokens — a SPEC-004 §7.1 pede para **não** carregar documentos desnecessários. Tratar com política de RAG por papel (Core mais seletivo).
- **Compatível com SPEC-003/004:** escopos `tenant`/`agent` ativos; `global` dormente até 41C.2C.

---

## 6. Mapa da memória atual

**Tabelas (ativas):** `conversation_logs` (turno: pergunta/resposta/tokens/`rag_chunks`/`rag_chunks_count`/`search_strategy`/`retrieval_score`/`internal_steps`), `session_summaries` (summary/topics/decisions/pending_items), `user_memories` (perfil/fatos), `memory_settings` (por empresa/agente; modos de sumarização inclusive WhatsApp), `memory_processing_locks`.

**Uso real no runtime:** `MemoryService.build_memory_context_async(...)` é chamado em `_build_initial_state` e injeta o contexto em `dynamic_context`. Ou seja, **há memória real no prompt hoje** (perfil + fatos + resumos), não apenas persistência.

**SubAgent:** traços ficam em `conversation_logs.internal_steps` — **não** há tabela de "run" formal.

**Gaps p/ Context Package (SPEC-004 §4.6/§9.3):** não existem `brokerage_memory`, `case_memory`, `operational_memory`, `routine_memory`, `skill_evidence`, `global_learning_candidate`. Memória é hoje **user/session-scoped**; falta memória de **caso** e de **corretora**. Autoaprendizado é explicitamente **futuro governado** (não implementar agora).

---

## 7. Mapa de tools / MCP / HTTP tools

- **Registro/expansão** em `_build_initial_state`: HTTP (`agent_http_tools` ativos) → `expand_http_tool_variables`; MCP (`mcp_gateway_service.get_agent_mcp_tools`) → `expand_mcp_tool_variables`; UCP (`ucp_connections`) → bloco commerce; SubAgent (`agent_delegations`).
- **Config por agente:** `agents.tools_config jsonb` (chave genérica) + tabelas dedicadas (`agent_http_tools`, `ucp_connections`, `agent_delegations`).
- **UI:** `components/admin/AgentConfigModal.tsx` expõe abas **Memory / MCP / UCP / SubAgent / Widget**, `security_settings`, HTTP tools (CRUD) e WhatsApp por agente.
- **Gate de ação sensível:** ações externas passam por **Vault** (credenciais) + **HITL** `approval_requests` (ex.: `whatsapp_send_message_dry_run`, `risk_level='medium'`). O draft de WhatsApp é **draft-only + dry-run** (sem envio real).
- **Gap SPEC-004:** o **AutoBrokers Core** ainda não tem uma **tool policy** que impeça execução sensível direta — hoje depende do prompt + do gate por ação. Falta declarar, no blueprint, "Core analisa/coordena, não executa".

---

## 8. Mapa de Auxiliares

- **Tabelas (manuais, fora do dump):** `auxiliary_templates` (catálogo global), `tenant_auxiliaries` (instalação por empresa), `auxiliary_runs` (histórico).
- **Runtime declarado em JSON:** `auxiliary_templates.default_config.runtime` e `tenant_auxiliaries.config.runtime`. `RuntimeKind` ∈ `smith_agent_blueprint | specific_executor | workflow | none` (`lib/admin/auxiliary-runtime.ts` L18; `KNOWN_EXECUTORS = ['resumo-atendimentos','follow-up-whatsapp']` L28).
- **Dispatch:** `specific_executor` → executor Python dedicado (`backend/app/api/auxiliaries.py`: `resumo-atendimentos`, `follow-up-whatsapp draft`); `smith_agent_blueprint` → cria/vincula um `agents` via **factory** (`lib/admin/agent-blueprints.ts` + rota `app/api/admin/auxiliaries/templates/[templateId]/install/route.ts::resolveRuntimeBinding`), gravando `agent_id` em `tenant_auxiliaries.config.runtime`; `workflow` → reservado (corredor futuro).
- **Sanitização:** `FORBIDDEN_SECRET_KEYS` impede vazar `llm_api_key`/tokens no blueprint.
- **Gaps SPEC-004 §3.3/§11.2:** auxiliares **não declaram** `goal/audience/inputs/outputs/requires_knowledge/requires_memory/requires_tools/requires_approval/side_effects/risk_level`. Hoje só `requires_human_approval`/`uses_external_actions` (flags de template) + gate por ação. Falta o **Auxiliary Blueprint Contract** (42A5).

---

## 9. Mapa de Admin Global

- **Criar agente por empresa:** `app/admin/agent/page.tsx` → `components/admin/AgentConfigModal.tsx` → `POST/PATCH /api/admin/proxy/agents/…`. Expõe identidade, LLM, system prompt, capacidades, retrieval/HyDE, security, WhatsApp, subagent, widget, HTTP/MCP/UCP.
- **Criar template global de auxiliar:** `app/admin/auxiliares/page.tsx` (form de template: name/slug/category/execution_mode/trigger_type/system_prompt/default_config/permissions/flags).
- **Publicar Agent existente como Auxiliar:** botão "Publicar Agent existente" → `POST /api/admin/auxiliaries/templates/from-agent` (extrai blueprint sanitizado do agente).
- **Conhecimento por agente:** `components/admin/DocumentManagementModal.tsx` (upload + lista + chunks), **separado** do `AgentConfigModal`.
- **Risco de confusão (SPEC-004):** "criar agent da empresa" e "criar template global" compartilham a forma de blueprint → a UI futura precisa deixar claro **escopo** (company vs global) e **papel** (Core/Attendance/Auxiliar/SubAgent). Hoje não há campo `role`/`audience` para orientar isso.

---

## 10. Mapa de Tenant Dashboard

- **Chat principal (broker):** `app/dashboard/chat/page.tsx` → `/api/chat/stream`. Agente ativo = `selectedAgentId` (default primeiro agente; seletor **oculto** por padrão; persiste por conversa via `agent_id`).
- **Auxiliares:** `app/dashboard/auxiliares/{page,meus,galeria,execucoes}` (+ galeria do follow-up-whatsapp). Consomem `/api/auxiliaries/*`.
- **Atendimento (segurado):** `app/dashboard/atendimentos/{page,fila,casos,conversas,segurados}` — **placeholders** (`ModulePlaceholder`), sem backend/tabela/runtime.
- **Separação Core × segurado:** já existe por **rota** (chat broker vs atendimentos). O risco não é de rota, e sim de **comportamento**: sem blueprint de papel, o Core pode "agir como atendente". Resolver no blueprint (42A3/42A4).
- **Onde encaixar "Context/Knowledge por agente" no futuro:** aba dedicada no `AgentConfigModal` (ao lado de Memory/MCP/...) reusando `DocumentManagementModal` + uma futura visão de Context Package (papel, políticas, escopos de RAG/memória).

---

## 11. Mapa de Atendimento / Corredores atuais

**Ausente em runtime.** Não existem tabelas `corredores/corridor_phases/corridor_slots/attendance_cases/case_runs/insurer_whatsapp_*`, nem state machine, nem código de fase/slot. Há apenas:
- **UI placeholder** `/dashboard/atendimentos/*`.
- **Canal** WhatsApp (`integrations` com `agent_id`, buffer/debounce) — canal, não workflow.
- **Traços** de subagente em `conversation_logs.internal_steps`.
- **Delegação** `agent_delegations` (orchestrator→subagent).

**Onde acoplar corredores sem motor paralelo (futuro):** como **conhecimento estruturado** (SPEC-004 §4.5/§10) + estado de caso em tabela própria, **consumido dentro** do `_build_initial_state` (injetar "active workflow/corridor state" no `dynamic_context`) e do tool node — **reusando** LangGraph, memória e `agent_delegations`. **Por enquanto é spec/documento** (roadmap SPEC-004 Fase 6).

---

## 12. Gaps para implementar SPEC-004

1. **Campos de papel/fronteira no `agents`** (ou em jsonb): `role`, `audience`, `mission`, `non_goals`, `scope`, `decision_boundaries`, `memory_policy`, `rag_policy`, `handoff_policy`, `corridor_binding`. Hoje implícitos no texto do prompt.
2. **Context Package declarativo** por tipo de agente (Core/Attendance/Auxiliar/SubAgent) — o `_build_initial_state` monta contexto, mas não conhece "papel".
3. **Blueprint do AutoBrokers Core** e **do Attendance** (separar comportamento broker × segurado).
4. **Auxiliary Blueprint Contract** (`requires_knowledge/memory/tools`, `side_effects`, `risk_level`).
5. **Corredores** (schema estruturado + estado de caso) e **case/brokerage memory**.
6. **Política de RAG por papel** (Core seletivo p/ evitar context bloat; Attendance focado no caso).
7. **Tool policy explícita** ("Core não executa ação sensível direta").
8. **Tenant profile** e **output contract** explícitos no Context Assembly.

---

## 13. O que já existe no Smith e deve ser preservado

- `_build_initial_state` (montagem em camadas) e o split static/dynamic (cache Anthropic).
- RAG do Smith: `SearchService`/`QdrantService`, coleção `company_{company_id}`, isolamento agent_id + tenant-wide, lexical rescue, fallback de score, health/debug (41C.1.x).
- Memória: `conversation_logs`, `session_summaries`, `user_memories`, `memory_settings` + `MemoryService`.
- Tools: HTTP/MCP/UCP/SubAgent + `agent_delegations`; Vault + HITL `approval_requests`.
- Auxiliares: factory `smith_agent_blueprint` + executores `specific_executor` + sanitização de segredos.
- Admin: `AgentConfigModal`, `DocumentManagementModal`, publicação de agente como template.
- Separação de rotas broker × atendimento.

---

## 14. O que não existe e precisa ser criado depois

- Campos de blueprint (`role/audience/mission/...`) — **estruturados**, não no texto livre.
- Context Package por papel (representação + injeção no runtime existente).
- Blueprints Core e Attendance; Auxiliary Blueprint Contract.
- Corredores (schema + estado de caso) e memórias de caso/corretora.
- Tabela de "run" formal de subagente/auxiliar (hoje parcial).
- Coleção/curadoria global (41C.2C) — fora deste batch.

---

## 15. O que nunca deve ser duplicado

- **Não** criar segundo runtime de chat (usar `graph.py`/`nodes.py`).
- **Não** criar segundo RAG/retriever/embeddings/coleção (usar `SearchService`/Qdrant Smith).
- **Não** criar segunda camada de memória (usar as 4 tabelas + `MemoryService`).
- **Não** transformar **corredor** em RAG (é estruturado).
- **Não** transformar **memória** em conhecimento global automático.
- **Não** duplicar prompt do agente (uma fonte: `agent_system_prompt` + Context Package por cima).
- **Não** recriar gate de ação (usar Vault + HITL existentes).

---

## 16. Recomendação para Context Package mínimo

Uma estrutura **declarativa** (sem novo motor), montada antes de `composite_prompt` e injetada via `dynamic_context`/`static_prompt`:

```
ContextPackage = {
  role: "core" | "attendance" | "auxiliary" | "subagent",
  audience: "corretor_operador" | "segurado" | "sistema",
  identity_blueprint: <derivado de agent_system_prompt + role>,
  tenant_profile: <empresa: nome, módulos, conectores ativos>,   # novo, leve
  user_session: <user/session/conversation>,                     # já existe
  workflow_state: <corredor ativo/fase/slots | null>,            # futuro
  memory: <build_memory_context_async>,                          # já existe
  rag_policy: { scopes: [agent, tenant], include_global: false, selective: role=="core" },
  tools_policy: { allowed: [...], sensitive_requires_hitl: true },
  output_contract: <formato esperado por papel>                  # novo, leve
}
```

Implementação sugerida: um helper `build_context_package(agent_data, …)` que **alimenta** o `_build_initial_state` atual (não o substitui). Fonte de `role/audience`: primeiro via `tools_config`/jsonb (sem migração), depois coluna dedicada quando aprovado por SPEC.

---

## 17. Recomendação para AutoBrokers Core Blueprint v1

Blueprint (texto canônico + campos) para o chat principal interno ("Jarvys" da corretora):
- **role:** core · **audience:** corretor/gestor/operador interno.
- **mission:** conselheiro operacional/analista/coordenador de auxiliares.
- **non_goals:** não é atendente de segurado; não executa ação sensível direta; não decide cobertura; não é fonte única de regra de seguradora.
- **reasoning:** raciocinar, fazer boas perguntas, separar fato de hipótese, sugerir próximos passos, reconhecer incerteza.
- **rag_policy:** tenant-wide + global curado (quando ligado), **seletivo** (evitar context bloat do prefetch).
- **memory_policy:** usa user/brokerage memory; não promove aprendizado.
- **tools_policy:** pode coordenar/preparar; ação sensível → HITL.
- **output:** análise + recomendação + próximos passos; nunca fingir que executou.
- **goldens** (SPEC-004 §13.2): diferencia auxiliar×atendimento; responde por RAG local; não inventa; sugere auxiliar; não vaza de outro agente; não confunde segurado com corretor.

Pode começar como **documento** e depois virar seed em `agent_system_prompt` + `role=core`.

---

## 18. Recomendação para Attendance Blueprint v1

Blueprint separado do Core, para o segurado/cliente:
- **role:** attendance · **audience:** segurado.
- **mission:** acolher, identificar, coletar dados, consultar apólice/base, seguir corredor, humanizar, preparar acionamento, escalar.
- **non_goals:** não promete cobertura; não aprova/nega sinistro sozinho; não envia acionamento sem gate; não inventa regra de seguradora; não usa conhecimento global como regra específica do caso.
- **context:** identidade de atendimento, canal, estado do caso, corredor/fase/slots, apólice, dossiê de seguradora, RAG agent/tenant, políticas de handoff/HITL.
- **goldens:** acolhe, pede dados mínimos, não promete cobertura, segue fase, escala quando necessário.

Depende de **corredores** (estruturados) — por isso entra após o schema de corredor (spec primeiro).

---

## 19. Recomendação para Auxiliary Blueprint Contract

Padronizar o `default_config.runtime` + um bloco de contrato (SPEC-004 §11.2), sem schema novo agora (cabe em jsonb):
```
{
  "slug": "...", "name": "...", "kind": "specific_executor|smith_agent_blueprint|workflow",
  "goal": "...", "audience": "operador_interno",
  "inputs": [], "outputs": [],
  "requires_knowledge": [], "requires_memory": [], "requires_tools": [],
  "requires_approval": false, "side_effects": "none|draft|external",
  "risk_level": "low|medium|high"
}
```
Aplicar primeiro aos auxiliares existentes (`resumo-atendimentos` = read-only/low; `follow-up-whatsapp` = draft + approval/medium). Validação no install + exibição na UI (Galeria/Meus).

---

## 20. Próximos batches sugeridos

Alinhado ao roadmap da SPEC-004 §15:
- **42A2 — Context Assembly Design Report:** desenhar o Context Package (§16) e como injetá-lo no `_build_initial_state` sem quebrar Smith. *(Recomendado como próximo — destrava Core e Attendance.)*
- **42A3 — AutoBrokers Core Blueprint v1** (doc → seed): §17.
- **42A4 — Attendance Boundary Blueprint v1:** §18 (após esboço de corredor).
- **42A5 — Auxiliary Blueprint Contract:** §19.
- **41C.2C — Global Knowledge Collection + Curated Ingestion:** só após Context Assembly claro e gate de aceitação 41C.1.5 validado.
- **42B — Attendance/Corredores:** schema estruturado de corredor + estado de caso (spec antes de runtime).

**Riscos a vigiar continuamente:** duplicidade de estrutura; prompt/RAG/memória paralelos; corredor implementado como texto solto; tool sensível sem gate; conhecimento global vazando; dado de tenant entrando em global; chat principal confundindo operador interno com segurado.

---

> **READ-ONLY:** este batch não alterou `app/`, `backend/`, `lib/`, schema, SQL ou rotas — apenas criou este relatório. Sem deploy.
