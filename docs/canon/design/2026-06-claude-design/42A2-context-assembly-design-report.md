# 42A2 — Context Assembly Design Report (READ-ONLY)

> **Status:** design canônico · **READ-ONLY** (nenhum código/schema/SQL/RAG/memória/prompt de produção alterado, sem deploy) · alinhado a SPEC-004, SPEC-003, SPEC-002, ADR-002, ADR-003.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Escopo:** desenhar o **Context Package** — a camada declarativa que organiza o que o Smith já monta hoje em `_build_initial_state`, sem criar motor novo, sem prompt gigante, sem misturar papéis.

---

## 1. Executive summary

**Context Assembly** é a etapa em que o sistema decide *o que entra no prompt do LLM a cada turno*. Hoje o Smith já faz isso em `backend/app/agents/graph.py::_build_initial_state` (prompt do agente + memória + tools + RAG), mas **não sabe formalmente qual é o papel do agente**: se é AutoBrokers Core (corretor), Attendance (segurado), Auxiliar, SubAgent ou Corredor. Esse "papel" está implícito no texto livre de `agent_system_prompt`.

Isso é o próximo passo **antes** do Core Blueprint porque, sem uma camada declarativa de papel/fronteira:
- o Core pode agir como atendente de segurado (e vice-versa);
- Auxiliar/SubAgent viram "agente principal" sem contrato;
- RAG demais entra no prompt (context bloat);
- memória errada contamina a resposta;
- ações sensíveis ficam sem fronteira declarativa;
- fica difícil **testar** comportamento (golden tests).

**Não devemos criar novo motor:** o 42A0 provou que o Smith já tem chat único, RAG, memória, tools e gates Vault/HITL. O Context Package **organiza** o que existe — ele é montado **antes** do `composite_prompt`, alimentando o `_build_initial_state` atual.

**Não devemos criar prompt gigante:** repetir o "cérebro antigo solto" seria ingovernável e impossível de testar. Em vez disso, separamos **Blueprint** (comportamento), **RAG** (conhecimento textual), **Memória** (contexto vivo) e **Workflow/Corredor** (processo estruturado). Cada camada tem responsabilidade única; nenhuma substitui a outra.

**Tese central:** introduzir um `ContextPackage` declarativo (papel, audiência, missão, não-fazer, políticas de RAG/memória/tools/handoff/aprovação, contrato de saída) que o runtime monta por tipo de agente — preservando 100% do Smith.

---

## 2. Estado atual do Smith (como o contexto é montado hoje)

Função central: `backend/app/agents/graph.py::_build_initial_state` (~L406). Ordem real:

1. **Carrega o agente** — `AgentService.get_agent_by_id` → `real_agent_data`; `system_prompt_source = agent_system_prompt`.
2. **Memória** — `MemoryService.build_memory_context_async(user_id, company_id, current_query, agent_id, …)` (`backend/app/services/memory_service.py`) → `memory_context` (perfil + fatos + resumos de sessão).
3. **base_instructions** = `agent_system_prompt` (fallback `company_config.agent_instructions`).
4. **Tools expandidas no prompt:** HTTP (`agent_http_tools` → `expand_http_tool_variables`); MCP (`mcp_gateway_service.get_agent_mcp_tools` → `expand_mcp_tool_variables`); SubAgent (`agent_delegations` → `expand_subagent_variables`); UCP (`ucp_connections` → bloco commerce).
5. **`static_prompt`** = `build_composite_prompt(base_instructions)` (parte **cacheável**).
6. **`dynamic_context`** (NÃO cacheado): memória + modo web + **RAG prefetch** (bloco "📚 CONTEXTO RECUPERADO DA BASE DE CONHECIMENTO", 41C.1.2).
7. **`composite_prompt`** = `static_prompt + dynamic_context`; `messages = [SystemMessage(composite_prompt), HumanMessage(user_message)]`.
8. **`initial_state`** carrega `static_prompt`, `dynamic_context`, `system_prompt`, `rag_context`, `rag_chunks` (+ métricas), `agent_data`, `company_config`, `thread_id = company_id:session_id`.

Nós (`backend/app/agents/nodes.py`):
- **agent node** (~L213): para **Anthropic**, monta `content_blocks` com `static_prompt` (bloco `cache_control`) + `dynamic_context` (bloco dinâmico); para os demais, `SystemMessage(system_prompt)`. Chama o LLM.
- **tool node**: executa tools; **estende `rag_chunks`** (preserva o prefetch).
- **log node** (~L559): grava `conversation_logs` (`rag_chunks_count`, `search_strategy`, `retrieval_score`, `internal_steps`).

RAG: `SearchService.smart_search(company_id, query, agent_id, is_hyde_enabled, include_global=False)` → `qdrant.search_similar(agent_id, include_tenant_wide=True)` na coleção `company_{company_id}` → rerank → lexical rescue (41C.1.3) → fallback de score (41C.1.4).

> **Conclusão:** a ordem do Smith já é parecida com SPEC-004 §4.3 (system → blueprint → memória → RAG). Falta **papel**, **tenant profile**, **workflow/case state** e **output contract** explícitos.

---

## 3. Problema atual (riscos de continuar só com `agent_system_prompt` livre)

| Risco | Sintoma | Causa |
|---|---|---|
| **Core vira atendente de segurado** | Responde "olá, sou o assistente da seguradora…" para o corretor | Sem `role`/`audience` declarados |
| **Attendance vira consultor interno** | Fala de KPIs/gestão para o segurado | Mesma ausência de papel |
| **Auxiliar/SubAgent como produto principal** | SubAgent aparece como agente de chat | `is_subagent` é só visual; falta contrato |
| **RAG demais no prompt** | Tokens inflados; resposta diluída | Prefetch injeta `content` inteiro todo turno (41C.1.2), sem política por papel |
| **Memória errada** | Mistura fato de outro contexto | Sem política de memória por papel/caso |
| **Tool sensível sem fronteira** | LLM "promete" ação externa | Gate existe por ação (Vault/HITL), mas não declarado no blueprint |
| **Difícil testar** | Não dá para criar golden por papel | Comportamento implícito em prosa |

A SPEC-004 §6.3 exige "inteligência máxima sem engessamento" **e** §2.4 exige separar prompt/RAG/memória/workflow. Texto livre não consegue garantir os dois.

---

## 4. Definição do Context Package

Estrutura **declarativa** (conceitual), montada **antes** do `composite_prompt`, alimentando o `_build_initial_state` atual. Não é tabela nova agora (ver §12); é um contrato.

```ts
ContextPackage = {
  role,              // "core" | "attendance" | "auxiliary" | "subagent" | "corridor"
  audience,          // "corretor_operador" | "segurado" | "sistema" | "orquestrador"
  identity_blueprint,// derivado de agent_system_prompt + role (quem é, voz, estilo)
  mission,           // objetivo central do agente
  non_goals,         // o que NÃO deve fazer (fronteiras)
  tenant_profile,    // empresa: nome, módulos ativos, conectores, seguradoras ativas
  user_session,      // user/session/conversation (papel do usuário, permissões)
  workflow_state,    // corredor ativo / fase / slots (null para Core simples)
  memory_policy,     // quais memórias pode usar e como
  rag_policy,        // escopos de RAG, include_global, seletividade
  tools_policy,      // tools visíveis + quais exigem gate
  handoff_policy,    // quando escalar para humano/outro agente
  approval_policy,   // o que exige HITL (por risk_level)
  output_contract,   // formato esperado de resposta por papel
  observability      // o que logar (sem PII/segredo)
}
```

**Mapa "já existe no Smith" × "criar depois":**

| Campo | Hoje no Smith | Status |
|---|---|---|
| `identity_blueprint` | `agents.agent_system_prompt` | ✅ existe (texto livre) |
| `role`, `audience` | — | ⛔ criar (jsonb/coluna futura) |
| `mission`, `non_goals` | implícito no prompt | ⛔ estruturar |
| `tenant_profile` | `company_config` (parcial) | 🟡 parcial — enriquecer |
| `user_session` | `user_id`/`session_id`/`conversation` | ✅ existe |
| `workflow_state` | — (corredores ausentes) | ⛔ criar (42B) |
| `memory_policy` | `memory_settings` + `MemoryService` | 🟡 existe motor; falta política por papel |
| `rag_policy` | `retrieval_mode`, `is_hyde_enabled`, `include_global=False` | 🟡 existe base; falta seletividade por papel |
| `tools_policy` | `tools_config`, `agent_http_tools`, MCP/UCP | 🟡 existe registro; falta policy declarativa |
| `handoff_policy` | `human_handoff` tool + `agent_delegations` | 🟡 parcial |
| `approval_policy` | Vault + HITL `approval_requests` (ADR-002) | ✅ existe motor; declarar por papel |
| `output_contract` | — | ⛔ criar |
| `observability` | `conversation_logs` | ✅ existe |

> O Context Package é **majoritariamente organização** do que já existe + 4 campos genuinamente novos (`role`, `audience`, `workflow_state`, `output_contract`).

---

## 5. Papéis oficiais

### 5.1 AutoBrokers Core (chat interno da corretora — "Jarvys dos seguros")
- **Audiência:** corretor/gestor/operador interno. **Nome fixo** (ADR-003 §4.1).
- **É:** conselheiro operacional, analista, coordenador de auxiliares, estrategista, secretário inteligente.
- **Não é / non_goals:** atendente de segurado; executor irrestrito; não promete cobertura; não decide cobertura; não envia ação sensível sem aprovação; não é fonte única de regra de seguradora.

### 5.2 Attendance Agent (atendimento ao segurado)
- **Audiência:** segurado/cliente final (WhatsApp/canal). **Personalizável** pela corretora (nome/tom/avatar — ADR-003 §4.2).
- **É:** acolhe, identifica, coleta dados, consulta apólice/base, segue corredor, humaniza, prepara acionamento, escala.
- **Non_goals (ADR-003 §48):** não promete cobertura; não aprova/nega sinistro sozinho; não finge ação ("já acionei"); não expõe dados a pessoa não autorizada; não inventa regra de seguradora; não usa conhecimento global como regra específica do caso.

### 5.3 Auxiliar (capacidade instalável)
- **Tipos (`lib/admin/auxiliary-runtime.ts`):** `specific_executor`, `smith_agent_blueprint`, `workflow`, `none`.
- **Contrato (a padronizar em 42A5):** `goal/audience/inputs/outputs/requires_knowledge/requires_memory/requires_tools/requires_approval/side_effects/risk_level`.

### 5.4 SubAgent (especialista técnico)
- Chamado por Core/Auxiliar/Corredor via `agent_delegations`. `is_subagent=true` esconde canais públicos.
- **Non_goals:** não é produto primário; escopo estreito; não recebe contexto amplo por padrão (SPEC-004 §7.4).

### 5.5 Corredor / Workflow (processo estruturado)
- **Estrutura (ADR-003 §18 / SPEC-004 §10.2):** seguradora, ramo, canal, serviço, fases, slots, entry/exit, dispatch packet, handoff, HITL, fallback, golden tests.
- **NÃO é RAG textual solto** nem prompt solto. É **conhecimento estruturado** (SPEC-004 §4.5). Ausente em runtime hoje (42A0) → construir em 42B.

---

## 6. Políticas de RAG por papel

Encaixe **no `SearchService.smart_search` atual** (sem novo retriever); a política decide *parâmetros e seletividade*, não um motor novo.

| Papel | Escopos | include_global | Seletividade |
|---|---|---|---|
| **Core** | tenant-wide + (global curado quando ligado) | off agora | **Seletivo** — só prefetch quando a pergunta for de conhecimento; evitar injetar `content` inteiro toda hora (anti context-bloat) |
| **Attendance** | agent (do caso) + tenant + dossiê da seguradora | off | Focado em apólice/seguradora/corredor do caso |
| **Auxiliar** | conforme `requires_knowledge` | off | Limitado ao declarado |
| **SubAgent** | agent-scoped técnico | off | Estreito ao escopo da delegação |
| **Corredor** | dossiês/regras **estruturadas** + RAG só para explicação | off | Usa estrutura, não texto solto |

**Encaixe técnico:** hoje o prefetch (41C.1.2) usa `should_prefetch_rag(user_message)` e injeta o resultado em `dynamic_context`. A `rag_policy` por papel ajustaria: (a) **quando** prefetch dispara (Core mais conservador), (b) `include_tenant_wide` (já True), (c) `include_global` (segue False até 41C.2C), (d) tamanho do bloco injetado. **Regra Vault (ADR-002 §15):** "busca sem permissão é bloqueada; documento sem classificação não entra em uso operacional" — a `rag_policy` deve respeitar permissão/escopo, nunca vazar entre tenant/agent/global.

---

## 7. Políticas de memória por papel

| Tipo de memória | Existe no Smith? | Uso por papel |
|---|---|---|
| **session memory** (curto prazo) | ✅ `conversation_logs` + checkpointer | Todos |
| **session_summary** | ✅ `session_summaries` | Core/Attendance |
| **user memory** | ✅ `user_memories` | Core (perfil do operador) |
| **brokerage memory** (fatos da corretora) | ⛔ não existe | Core (futuro) |
| **case memory** (estado/histórico de caso) | ⛔ não existe | Attendance/Corredor (futuro, 42B) |
| **operational memory** (gargalos/padrões) | ⛔ não existe | Core (futuro) |
| **routine/auxiliary memory** | 🟡 `auxiliary_runs` (parcial) | Auxiliar |
| **global_learning_candidate** | ⛔ não existe | Curadoria (futuro) |

**Regra dura (SPEC-004 §9.2 / ADR-002):** autoaprendizado **não** é automático. Promoção de memória local → conhecimento global exige pipeline curado (observação → sugestão → evidência → revisão humana → sandbox → eval → aprovação → versionamento → rollback). Memória **nunca** vira conhecimento global automaticamente; memória **não** guarda segredo/token/PII desnecessária.

Hoje `MemoryService.build_memory_context_async` injeta user/session memory no `dynamic_context`. A `memory_policy` por papel definiria *quais* memórias entram (Core não precisa de case memory; Attendance precisa).

---

## 8. Políticas de tools / MCP / Vault / HITL

Base canônica: **ADR-002** (risk levels) + motor existente (Vault + HITL `approval_requests`).

| Papel | Pode | Exige gate (HITL) |
|---|---|---|
| **Core** | preparar, coordenar, sugerir, rascunhar, acionar auxiliares | **Toda ação externa sensível** (não executa direto) |
| **Attendance** | coletar dados, consultar apólice, **preparar** acionamento | Acionamento real / envio externo → HITL |
| **Auxiliar** | conforme `requires_tools` + `side_effects` declarados | Se `side_effects=external` → aprovação |
| **SubAgent** | tool técnica limitada à delegação | Não acessa tool sensível sem delegação explícita |
| **Corredor** | preparar dispatch packet | Acionamento → HITL (ADR-003 §21) |

**Risk levels (ADR-002 §11):** `low` (executa com log) · `medium` (gera resultado; ação externa → aprovação) · `high` (ação externa exige aprovação) · `critical` (bloqueado por padrão no MVP; só com HITL+logs+rollback). **Vault** é fonte oficial de credenciais; segredo nunca entra em prompt/memória/RAG/log (ADR-002 §18). **WhatsApp legado por agente** (campo do `AgentConfigModal`) **não** é o caminho oficial — o oficial é conector via Vault + HITL (ex.: follow-up dry-run já implementado).

---

## 9. Contrato de output por papel

| Papel | `output_contract` |
|---|---|
| **Core** | Análise → recomendação → **próximos passos** → perguntas inteligentes quando faltar dado. Nunca fingir que executou. |
| **Attendance** | Acolhimento → confirmação do entendido → coleta mínima → orientação **segura** (sem promessa) → handoff quando necessário. |
| **Auxiliar** | Resultado **estruturado** + evidências + ação sugerida + custo/run. Sem side-effect indevido. |
| **SubAgent** | Resposta **técnica para o orquestrador** (não copy final para cliente). |
| **Corredor** | Estado + fase + slots preenchidos/faltantes + próximos passos + bloqueios. |

O `output_contract` também é a base dos **golden tests** (SPEC-004 §13.2) — testável por papel.

---

## 10. Como evitar agente burro / engessado

- O **LLM continua raciocinando** — o blueprint **orienta**, não aprisiona (SPEC-004 §6.3).
- **RAG fornece fatos**, não substitui raciocínio; chunk é evidência, não roteiro.
- **Corredores estruturam processo**, mas o agente pode reformular perguntas, humanizar, adaptar sequência quando permitido (ADR-003 deixa o agente "entender antes de acionar").
- **Memória melhora continuidade**, não vira verdade absoluta.
- **Core pode pensar estrategicamente** dentro de limites seguros (non_goals + approval_policy).
- Anti-engessamento = limites **declarativos** (o que não fazer) em vez de scripts fixos. Inteligência por **composição** (LLM + blueprint + contexto + RAG + memória + tools), não por improviso nem por prompt gigante.

---

## 11. Como aproveitar o cérebro antigo sem contaminar o runtime

Regra de curadoria (ADR-002 §14 / ADR-003 §6): **nenhuma fonte entra crua**. Cada item do Agent OS/ResultVision vira **uma de três coisas**:

| Fonte legada | Vira | Camada |
|---|---|---|
| `00_CONSTITUICAO` (princípios/voz/guardrails) | **Blueprint/guardrail config** | Prompt/Blueprint |
| `01_ORQUESTRADOR` (core/handoff) | **Blueprint do Core + handoff_policy** | Prompt/Blueprint |
| `02_RUNTIME_CONVERSACIONAL` | **Comportamento conversacional** | Blueprint |
| `04_CONVERSA_COM_CLIENTE` (copy/humanização) | **Attendance blueprint + templates** | Blueprint/estruturado |
| `07_CORREDORES` (fases/slots/regras) | **Corredor estruturado** | Structured Knowledge (não RAG) |
| `17_INTELIGENCIA_OPERACIONAL` (memory fabric) | **Design de memória** | Memória (sem autoaprendizado agora) |
| Condições gerais/dossiês/playbooks longos | **RAG curado** | RAG (41C.2C) |

**Proibido:** copiar bruto; jogar tudo no RAG; misturar atendimento de segurado com Core interno; ingerir intake bruto (PII) no RAG (ADR-002 §13).

---

## 12. Recomendação de armazenamento inicial (sem migration agora)

1. **Fase doc/seed (agora):** o Context Package e os papéis vivem como **documentação canônica + seed de blueprint** (em `agent_system_prompt` quando for comportamento). Sem schema novo.
2. **Fase jsonb experimental (quando implementar 42A6):** `role`/`audience`/`*_policy` podem ser **prototipados** dentro de `agents.tools_config` ou de uma chave dedicada em jsonb **somente leitura no runtime**, sem migração — desde que: não guarde segredo, não altere comportamento de produção sem flag, e seja claramente marcado experimental.
3. **Quando migration é necessária:** ao promover `role`/`audience` a coluna de primeira classe (filtros, índices, UI dedicada), aí sim propor migração **controlada pelo Architect** (com auditoria de schema — ADR-002 §40 "auditar antes de criar migrations"). **Este batch não cria SQL.**

> Recomendação prática: começar como **doc/seed**; só ir para jsonb experimental no 42A6; coluna dedicada só com SPEC/migração aprovada.

---

## 13. Proposta de ordem de montagem de contexto

Ordem recomendada (SPEC-004 §4.3) × ordem atual do `_build_initial_state`:

| # | Ordem recomendada | Hoje no `_build_initial_state` | Encaixe |
|---|---|---|---|
| 1 | System/global safety invariants | parcial (security_settings por ação) | adicionar bloco fixo no `static_prompt` |
| 2 | **Role blueprint** | `agent_system_prompt` (sem papel) | injetar `role/mission/non_goals` no `static_prompt` |
| 3 | **Tenant profile** | `company_config` (parcial) | enriquecer e injetar (cacheável) |
| 4 | User/session | `user_id`/`session_id` | já existe |
| 5 | **Workflow/case state** | ausente | injetar no `dynamic_context` (futuro 42B) |
| 6 | Memory | `MemoryService` → `dynamic_context` | já existe; aplicar `memory_policy` |
| 7 | **RAG seletivo** | prefetch (41C.1.2) → `dynamic_context` | aplicar `rag_policy` por papel |
| 8 | Tools available | HTTP/MCP/UCP/SubAgent expand | já existe; aplicar `tools_policy` |
| 9 | Approval/handoff policy | Vault/HITL por ação | declarar no blueprint |
| 10 | **Output contract** | ausente | injetar no `static_prompt` |

**Princípio de cache (nodes.py Anthropic):** o que é estável por agente (role, mission, non_goals, tenant_profile, output_contract) vai no **`static_prompt`** (cacheável); o que muda por turno (memory, RAG, workflow_state) vai no **`dynamic_context`**. Isso preserva o ganho de prompt caching e evita context bloat.

---

## 14. Regras de não-duplicação

- **Não** criar novo RAG/retriever/embeddings/coleção — usar `SearchService`/Qdrant Smith.
- **Não** criar nova camada de memória — usar `conversation_logs`/`session_summaries`/`user_memories`/`memory_settings`.
- **Não** criar novo runtime de chat — usar `graph.py`/`nodes.py`.
- **Não** criar tabela nova sem SPEC/auditoria (ADR-002 §40).
- **Não** transformar corredor em prompt/RAG solto — é estruturado.
- **Não** injetar o cérebro inteiro no prompt — blueprint enxuto + RAG curado.
- **Não** deixar conhecimento global misturar dado de tenant — isolamento absoluto (ADR-002 §17).
- **Não** duplicar o prompt do agente — uma fonte (`agent_system_prompt`) + Context Package por cima.

---

## 15. Plano de implementação em batches

| Batch | Objetivo | Depende de |
|---|---|---|
| **42A3 — AutoBrokers Core Blueprint v1** | Blueprint/prompt do chat principal (role=core), doc → seed | 42A2 (este) |
| **42A4 — Attendance Boundary Blueprint v1** | Blueprint de atendimento separado do Core | 42A3 + esboço de corredor |
| **42A5 — Auxiliary Blueprint Contract** | Padronizar `requires_knowledge/memory/tools`, `side_effects`, `risk_level` | 42A2 |
| **42A6 — Context Package Minimal Implementation** | Implementar `role/audience/policies` (jsonb experimental) no `_build_initial_state`, sem quebrar Smith | 42A3/42A4/42A5 |
| **41C.2C — Global Knowledge Collection** | Coleção `autobrokers_global` + ingestão curada; ligar `include_global` por config | 42A2 + gate 41C.1.5 |
| **42B — Corredores/Attendance Runtime** | Schema estruturado de corredor + estado de caso (spec antes de runtime) | 42A4 + ADR-003 |

**Dependência-chave:** Core e Attendance blueprints (42A3/42A4) **antes** da implementação do Context Package (42A6); global (41C.2C) **depois** de saber quem usa o quê.

---

## 16. Critérios de aceite (design pronto)

- Core sabe que fala com **corretor**; Attendance sabe que fala com **segurado**.
- Auxiliar tem **contrato** (entrada/saída/knowledge/memory/tools/risco/aprovação).
- SubAgent **não** aparece como produto principal.
- RAG **não vaza** entre tenant/agent/global; `include_global` segue off até 41C.2C.
- Memória **não** vira conhecimento global automático.
- Ação sensível **exige HITL** (por risk_level).
- **Sem motor paralelo**; **sem prompt gigante**.
- Ordem de montagem mapeada ao `_build_initial_state` sem quebrar cache/Smith.

---

## 17. Perguntas pendentes (para implementação futura)

1. **`role`/`audience`:** começar em `tools_config` (jsonb) ou já propor coluna dedicada com migração controlada? (Recomendo jsonb experimental no 42A6.)
2. **Core é um agente "fixo" por empresa** (seed automático ao criar a corretora) ou um agente marcado `role=core`? (ADR-003 diz nome fixo "AutoBrokers".)
3. **Tenant profile:** quais campos mínimos (módulos ativos, conectores, seguradoras) e de onde puxar sem custo alto por turno?
4. **`should_prefetch_rag` por papel:** Core deve ter limiar mais conservador — qual heurística inicial?
5. **Workflow_state:** formato mínimo do estado de caso para o 42B (alinhar com ADR-003 §44-46).

---

## 18. Recomendação final

Executar **42A3 — AutoBrokers Core Blueprint v1** como próximo batch. Razão: com o Context Package desenhado (este relatório), o Core é o papel de maior valor imediato (chat interno do corretor) e o que mais sofre hoje com a ausência de fronteira declarativa. O 42A3 deve ser **documento → seed** (blueprint canônico em `agent_system_prompt` + `role=core` conceitual), sem implementar o Context Package inteiro ainda (isso é 42A6). Atendimento (42A4) e global (41C.2C) vêm depois, conforme as dependências da §15.

---

> **READ-ONLY:** este batch não alterou `app/`, `backend/`, `lib/`, schema, SQL, RAG, memória ou prompts de produção — apenas criou este relatório de design. Sem deploy.
