# 42A6 — Context Package Runtime Foundation Report

> **Status:** concluído · py_compile verde · `git diff --check` limpo · **sem motor paralelo, sem RAG/Qdrant/MinIO/upload, sem SQL/migration, sem mexer em Supabase/Auxiliares/Vault/WhatsApp/HITL, sem alterar prompt de produção**.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo
Fundação de runtime do **Context Package v1**: o Smith agora **lê** os campos declarativos do agente (`agent_role`, `agent_audience`, `blueprint_version`, `context_package`) e injeta um **bloco compacto** no Context Assembly existente (`_build_initial_state`). É **aditivo e backward-compatible**: agentes sem `context_package` continuam idênticos. Não há engine nova; o bloco apenas complementa o `agent_system_prompt`.

## 2. Arquivos alterados
- `backend/app/models/agent.py` — `AgentBase` ganhou 4 campos **opcionais**: `agent_role`, `agent_audience`, `blueprint_version` (Optional[str]) e `context_package` (Optional[dict]). Necessário porque `AgentService._map_to_response` faz `AgentResponse(**data)` e o Pydantic v2 **descarta** colunas não declaradas — sem isso os novos campos não chegariam ao runtime.
- `backend/app/agents/context_package.py` (**novo**) — helpers puros: `get_agent_field`, `normalize_context_package`, `should_render_context_package`, `render_context_package_block` (+ `_compact_*`).
- `backend/app/agents/graph.py` — em `_build_initial_state`, logo após montar `base_instructions` e **antes** das expansões HTTP/MCP/SubAgent/UCP, injeta o bloco do Context Package (prepend). Try/except que nunca quebra o chat + log seguro.
- `docs/canon/design/2026-06-claude-design/42A6-context-package-runtime-foundation-report.md` (este).

## 3. Onde o Context Package entra no Smith
Ordem em `_build_initial_state` (preservada):
1. Agent load (`AgentService.get_agent_by_id` → `real_agent_data = model_dump()`).
2. **Context Package block** (novo, se existir) → **prepended** a `base_instructions`.
3. `agent_system_prompt` (já era `base_instructions`).
4. Expansões HTTP/MCP/SubAgent/UCP (append a `base_instructions`).
5. `static_prompt = build_composite_prompt(base_instructions)` (**cacheável**).
6. `dynamic_context` (memória + web + **RAG prefetch**) — **inalterado**.
7. `composite_prompt = static_prompt + dynamic_context` — **inalterado**.

Como o bloco é **estável por agente**, ele entra no `static_prompt` (cacheável Anthropic), sem inflar a parte dinâmica nem o RAG.

## 4. Formato do bloco (compacto e seguro)
```
[CONTEXT PACKAGE]
role: core
audience: broker_internal
blueprint_version: core-v1
mission: ...
non_goals: ...
rag_policy: ...
memory_policy: ...
tools_policy: ...
handoff_policy: ...
approval_policy: ...
output_contract: ...
```
Garantias do `render_context_package_block`:
- **Whitelist de chaves de política** (`mission, non_goals, rag_policy, memory_policy, tools_policy, handoff_policy, approval_policy, output_contract`). Qualquer outra chave do `context_package` é **ignorada** → nunca injeta documento/chunk/token/segredo/PII colocado em chave arbitrária.
- **Cap por campo** (400 chars) e **cap total** (2400 chars) → nunca vira prompt gigante.
- Colapsa quebras de linha → bloco tidy.
- **Não substitui** `agent_system_prompt` — só complementa.

## 5. Por que isso NÃO é motor paralelo
Não há novo grafo, retriever, store, tabela ou pipeline. O código apenas **lê campos do agente** (que já vêm do `select("*")` existente) e **prepend** um texto curto na variável `base_instructions` que o Smith já usava. Todo o resto (LLM, nós, tool node, RAG, memória) é o mesmo.

## 6. Como preserva RAG/memória/tools existentes
- **RAG:** `SearchService`/`QdrantService`/ingestão/MinIO/upload **intocados**; prefetch (41C.1.2) e `include_global=False` inalterados. O `rag_policy` do bloco é **texto declarativo** para orientar a LLM — **não** muda parâmetros de busca neste batch.
- **Memória:** `MemoryService` e o `memory_context` no `dynamic_context` inalterados.
- **Tools/MCP/UCP/SubAgent:** expansões inalteradas; **Tool Node** não tocado.
- **Vault/HITL/WhatsApp/Auxiliares:** não tocados.

## 7. Como agentes sem context_package continuam funcionando
`should_render_context_package` retorna `False` quando não há `agent_role`/`agent_audience`/`blueprint_version` nem `context_package` → `render_*` retorna `""` → `base_instructions` permanece **exatamente** como antes. Validado por teste isolado (agente sem cp → bloco vazio; `None` → seguro). Qualquer erro no caminho é engolido (`try/except`) sem quebrar o chat.

## 8. Observabilidade (logs seguros)
`[ContextPackage] present=true role=... audience=... blueprint_version=...` quando aplicado; `present=false` quando não. **Nunca** loga: prompt completo, `context_package` completo, conteúdo de documento, memória, PII ou segredo.

## 9. Checks
| Check | Resultado |
|---|---|
| `python -m py_compile` (graph, nodes, context_package, models/agent, agent_service) | ✅ OK |
| `git diff --check` | ✅ limpo (só avisos CRLF) |
| teste isolado do helper (render/whitelist/backward-compat/None) | ✅ bloco correto; chave não-whitelist **ignorada**; sem cp → vazio |
| alteração em SearchService/Qdrant/MinIO/upload/ingestion | ✅ nenhuma |
| `include_global=True` novo | ✅ nenhum |
| SQL/migration/Supabase | ✅ nenhum |
| segredo/token/PII / cérebro antigo bruto no diff | ✅ nenhum |

## 10. Riscos remanescentes
- **`rag_policy`/`memory_policy` ainda são declarativos** (orientam a LLM), não alteram parâmetros reais de retrieval/memória. A aplicação efetiva (ex.: prefetch seletivo do Core) fica para um batch futuro.
- **Conteúdo do `context_package`** depende de curadoria do Admin: como só renderizamos chaves whitelisted e truncadas, o risco de bloat/vazamento é baixo, mas valores muito longos são truncados (pode perder nuance — por isso o blueprint longo vive em doc, não no campo).
- **Dependência do schema:** os 4 campos precisam existir em `public.agents` (já adicionados manualmente pelo Architect). Se ausentes, `select("*")` simplesmente não os traz e o runtime segue como antes.

## 11. Teste esperado (pós-deploy API)
No **AutoBrokers Sandbox** (RAFAEL), deve responder igual ou melhor:
1. "Você é o atendente do segurado ou o assistente interno da corretora?" → **interno** (Core).
2. "Esse cliente tem cobertura para vazamento?" → não promete; pede apólice/fonte.
3. "Mande WhatsApp para todos que não responderam." → prepara rascunho + pede aprovação (HITL).
4. "Qual é a palavra-chave de validação do RAG local da RAFAEL SEGUROS?" → **NEVOA-791** (RAG inalterado).
5. "Como melhorar a renovação?" → análise + recomendação + próximos passos.
Logs devem mostrar `[ContextPackage] present=true role=core ...` para o Sandbox e `present=false` para agentes sem o pacote.

## 12. Deploy recomendado
- **API apenas** (backend Python: graph, models/agent, novo context_package). Sem Next → sem Web. Sem SQL/migration. Sem reupload.

## 13. Próximo batch recomendado
- **42A5 — Auxiliary Blueprint Contract** (padronizar `requires_knowledge/memory/tools`, `side_effects`, `risk_level`) **ou** evoluir o Context Package para **políticas efetivas** (ex.: `rag_policy` do Core ligando prefetch seletivo) num 42A7.
- Depois: **41C.2C — Global Knowledge Collection** (já com papéis declarados sabendo quem consome o quê).
