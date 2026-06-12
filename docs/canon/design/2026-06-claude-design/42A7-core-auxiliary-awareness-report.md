# 42A7 — Core Auxiliary Awareness Report

> **Status:** concluído · py_compile verde · `git diff --check` limpo · **sem RAG/Qdrant/MinIO/upload, sem WhatsApp/executores, sem schema/SQL/migration, sem prompt de produção no banco**.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que foi implementado
O **AutoBrokers Core** passa a enxergar os **Auxiliares instalados** da corretora e seus contratos (42A5), de forma compacta e segura, dentro do Context Assembly. Assim o Core sabe responder "quais auxiliares eu tenho", "esse exige aprovação?", "qual usar para follow-up?", "envia mensagem real?", "quais têm risco alto?", sem fingir execução e sem motor novo.

Novo helper: `backend/app/agents/auxiliary_context.py`
- `should_load_auxiliary_context(agent_data, user_message)` — só `agent_role='core'` (e, se definido, `agent_audience='broker_internal'`) **e** mensagem com intenção sobre auxiliares/automação/capacidades.
- `load_tenant_auxiliaries_for_context(client, company_id)` — lê `tenant_auxiliaries` ativos (campos seguros); `[]` em erro/vazio.
- `normalize_auxiliary_contract_for_context(row)` — extrai apenas campos seguros do `config.contract` (42A5) ou infere o mínimo.
- `render_auxiliary_context_block(rows)` — monta o bloco `[AVAILABLE AUXILIARIES]` compacto (≤8 itens) + instruções.

## 2. Onde entra no Context Assembly
Em `backend/app/agents/graph.py::_build_initial_state`, **depois** do Context Package (que é estático) e **depois** do RAG prefetch, **antes** de `composite_prompt = static_prompt + dynamic_context`. O bloco é anexado ao **`dynamic_context`** (não cacheado) — escolha deliberada: a lista de Auxiliares instalados pode mudar a qualquer momento, então **não** deve entrar no `static_prompt` cacheado (evita cache stale). Usa o `supabase_client` já disponível na função (mesmo padrão sync dos blocos HTTP/MCP/UCP existentes).

## 3. Por que não é motor paralelo
Não há novo grafo, retriever, store, tabela ou serviço. É apenas uma **leitura** de `tenant_auxiliaries` (tabela existente) + um **texto curto** anexado ao `dynamic_context` que o Smith já monta. Reusa `get_agent_field` do 42A6. Todo o runtime (LLM, nós, RAG, memória, tools) é o mesmo.

## 4. Como preserva o Smith
- **RAG/Qdrant/MinIO/upload/ingestão:** intocados. `include_global` inalterado.
- **WhatsApp e executores** (`resumo-atendimentos`, `follow-up-whatsapp`, dry-run, `approval_requests`, billing): intocados.
- **Schema/SQL/migration/prompt no banco:** nada. O bloco é runtime-only.
- Agentes **não-Core** ou sem trigger: comportamento idêntico ao anterior.

## 5. Como evita context bloat
- Só carrega para o **Core** e só quando a mensagem tem intenção (keywords/perguntas amplas) — saudações não disparam.
- **≤ 8** Auxiliares; uma linha curta por item; `goal`/`when_to_use` truncados (≤90 chars); sem `config`/`default_config`/`system_prompt`/`permissions`/`input_schema`/`output_schema` inteiros.
- Vai no `dynamic_context` (não infla o prompt cacheado).

## 6. Como sanitiza
Lê **apenas** campos whitelisted do contrato (`auxiliary_type`, `side_effects`, `risk_level`, `approval_policy.required`, `requires_tools[type]`, `requires_knowledge[scope/required]`, `goal`, `when_to_use`). Nunca inclui token/api_key/secret/password/credential/cookie/authorization, conexões, payload de execução, nem dado de cliente/segurado. Validado por teste: chave `secret` no contrato **não** aparece no bloco.

## 7. Como o Core deve usar
Instruções injetadas no bloco: pode **sugerir** auxiliares quando relevante; **não** afirmar que executou sem run/tool confirmando; **ação externa exige aprovação humana**; se faltar conector/tool, **explicar o que configurar**. Isso casa com o Core Blueprint (42A3A): preparar/coordenar, nunca executar sensível direto.

## 8. Observabilidade (logs seguros)
`[AuxContext] loaded count=N company=...`, `[AuxContext] skipped reason=not_core_or_no_trigger | no_active_auxiliaries | empty_block`, `[AuxContext] error ignored type=...`. Nunca loga conteúdo/config/prompt/token.

## 9. Reuso do contrato (sem importar TS)
O backend não importa `lib/auxiliaries/contract.ts`. A normalização Python é **semanticamente compatível**: lê o `config.contract` já normalizado pelo 42A5 (gravado no install) e, quando ausente (instalações legadas), infere o mínimo de forma genérica (slug com "whatsapp" → approval/medium/whatsapp; runtime agent → agent_based; senão read_only/low). Sem hardcode de empresa.

## 10. Limitações
- Inferência mínima para Auxiliares legados sem `config.contract` (até serem reinstalados/atualizados pelo 42A5).
- Keywords como "atendimento"/"mensagem" são amplas — podem disparar a leitura em conversas correlatas; o custo é uma query leve + bloco curto.
- O bloco **informa** o Core; **não** executa Auxiliares (execução continua via as rotas/HITL existentes).

## 11. Checks
| Check | Resultado |
|---|---|
| `python -m py_compile` (graph, context_package, auxiliary_context, models/agent, agent_service) | ✅ OK |
| teste isolado (gating core/greeting/non-core/broad + render + sanitização + vazio) | ✅ correto; secret não vaza |
| `git diff --check` | ✅ limpo |
| SearchService/Qdrant/MinIO/upload/RAG/ingestão alterados | ✅ nenhum |
| WhatsApp/executores/approval/billing alterados | ✅ nenhum |
| SQL/migration/schema/prompt no banco | ✅ nenhum |
| `include_global=True` novo / segredo no output | ✅ nenhum |

## 12. Testes esperados (pós-deploy API)
No chat RAFAEL + AutoBrokers Sandbox:
1. "Quais auxiliares eu tenho disponíveis?" → lista Resumo de Atendimentos e Follow-up WhatsApp (se instalados), com explicação curta.
2. "O Follow-up WhatsApp envia mensagem real?" → diz que gera rascunho/aprovação (dry-run); envio real exige aprovação/conector.
3. "Qual auxiliar devo usar para resumir atendimentos?" → sugere Resumo de Atendimentos.
4. "Mande follow-up para clientes que não responderam." → não finge envio; sugere o Auxiliar para gerar rascunho + aprovação.
5. "Qual é a palavra-chave de validação do RAG local da RAFAEL SEGUROS?" → continua **NEVOA-791** (RAG inalterado).
Logs: `[AuxContext] loaded count=...` para o Sandbox; `skipped reason=not_core_or_no_trigger` para agentes sem papel/sem trigger.

## 13. Deploy recomendado
- **API apenas** (backend Python: graph + novo auxiliary_context). Sem Web, sem SQL/migration, sem reupload.

## 14. Próximo batch recomendado
- **41C.2C — Global Knowledge Collection + Curated Ingestion** (agora que Core conhece papéis e auxiliares), **ou** **42A4 — Attendance Boundary Blueprint v1**. Depois, **42B — Atendimento/Corredores**.
