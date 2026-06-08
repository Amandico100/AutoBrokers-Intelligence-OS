# 38A2 — Auxiliar Resumo de Atendimentos API MVP Report

> **Status:** concluído, **commitado e pushado** · build/typecheck/py_compile verdes · **sem migration/SQL** (tabelas já criadas manualmente no 38A1).
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Primeira camada **funcional** dos Auxiliares: o Auxiliar **Resumo de Atendimentos** agora executa de verdade. **Next** autentica e resolve `company_id` (anti-IDOR); o **backend FastAPI** valida o escopo, lê `messages` da conversa, gera um resumo estruturado via LLM (`gpt-4o-mini`, reuso de `langchain_openai`) e grava a execução em `auxiliary_runs`. Read-only, sem ação externa. UI **não** foi ligada (fica para 38A3). Multi-tenant, sem hardcode de IDs.

## 2. Arquivos alterados
**Backend (novo/alterado):**
- `backend/app/api/auxiliaries.py` (novo) — endpoint `POST /api/auxiliaries/resumo-atendimentos/run` + helpers.
- `backend/app/main.py` (edit) — registra o router (`prefix="/api/auxiliaries"`).
**Next API (novo):**
- `app/api/auxiliaries/templates/route.ts` (GET)
- `app/api/auxiliaries/installed/route.ts` (GET)
- `app/api/auxiliaries/runs/route.ts` (GET)
- `app/api/auxiliaries/runs/[runId]/route.ts` (GET)
- `app/api/auxiliaries/resumo-atendimentos/run/route.ts` (POST → backend)
**Lib (novo):**
- `lib/auxiliaries/server.ts` (server-only: sessão→company + supabase admin)
- `lib/auxiliaries/types.ts` (tipos compartilhados)
- `lib/auxiliaries/api.ts` (helpers de client para o 38A3)
**Docs:** este relatório.
Nenhum arquivo fora das áreas permitidas foi tocado (chat, AppShell, patterns, telas de Auxiliares, migrations, package.json intactos).

## 3. Arquitetura escolhida
**Next = fronteira de auth/tenant; Backend = execução LLM + persistência.**
- Rotas Next de **leitura** (templates/installed/runs/runs[id]) consultam o Supabase com **service role**, escopadas por `company_id` (padrão de `app/api/agents/route.ts`).
- Rota Next de **execução** autentica, deriva `company_id` da sessão e **proxia** para o backend (padrão do chat `app/api/chat/stream/route.ts`), passando `company_id` confiável.
- **Backend FastAPI** (`/api/auxiliaries/resumo-atendimentos/run`) faz a validação de escopo (defesa em profundidade), lê mensagens, chama o LLM e grava em `auxiliary_runs`.

## 4. Por que essa arquitetura foi escolhida
- ADR-001 §10/§21: backend é o runtime de LLM; **não criar caminho de LLM paralelo** no Next. O backend já tem `OPENAI_API_KEY`, `langchain_openai`, `usage_service` e cliente Supabase.
- O proxy do chat **encaminha o body do client sem auth** — inadequado para resolver empresa. Por isso a **auth/company fica no Next** (iron-session + `users_v2`), e só o `company_id` derivado no servidor é enviado ao backend.
- Reuso máximo, zero dependência nova, superfície pequena e reversível.

## 5. Endpoints criados
| Método | Rota | Função |
|---|---|---|
| GET | `/api/auxiliaries/templates` | catálogo ativo (`auxiliary_templates.is_active=true`) |
| GET | `/api/auxiliaries/installed` | instalados da empresa (`tenant_auxiliaries` por `company_id`) |
| GET | `/api/auxiliaries/runs` | execuções da empresa (`auxiliary_runs`, `created_at desc`, limit 50) |
| GET | `/api/auxiliaries/runs/[runId]` | execução específica (escopada por `company_id`, 404 se não for da empresa) |
| POST | `/api/auxiliaries/resumo-atendimentos/run` | executa o Auxiliar (proxy → backend) |
| POST (backend) | `/api/auxiliaries/resumo-atendimentos/run` | execução LLM + persistência |

## 6. Backend/FastAPI criado ou alterado
- `backend/app/api/auxiliaries.py`: `ResumoRunRequest{company_id, user_id?, conversation_id?}`. Fluxo: localizar `tenant_auxiliaries` ativo (`company_id`+`slug='resumo-atendimentos'`+`status='active'`) → escolher/validar conversa → criar `auxiliary_runs(status='running')` → ler `messages` (asc, limit 80) → LLM (`ChatOpenAI` `ainvoke`, JSON mode) → atualizar run `succeeded`/`failed`. Custo via `usage_service.track_cost_sync` (best-effort, `service_type='auxiliary_run'`).
- `backend/app/main.py`: `include_router(auxiliaries_router, prefix="/api/auxiliaries")`.
- Reusos: `get_async_db` (cliente Supabase async), `get_api_key_for_provider`, `get_usage_service`, `langchain_openai.ChatOpenAI`.

## 7. Next API criada ou alterada
5 rotas novas (acima). Leitura via `getSupabaseAdmin()` (service role) sempre filtrando por `company_id`. Execução via `getBackendUrl(req)` (mesmo helper do chat). Helpers em `lib/auxiliaries/server.ts` (`resolveSessionCompany`, `getSupabaseAdmin`).

## 8. Como company_id/user_id são resolvidos
`resolveSessionCompany()`: lê o cookie de sessão (iron-session, `SessionData`), pega `session.userId`, e busca `users_v2.company_id` com service role. **O `company_id` nunca vem do client.** O backend recebe `company_id`/`user_id` já resolvidos e **revalida** o escopo.

## 9. Como anti-IDOR foi garantido
- `company_id` derivado da sessão no Next (não do payload).
- Leituras Next sempre com `.eq('company_id', ctx.companyId)`; `runs/[runId]` exige `id`+`company_id`.
- Backend revalida: `tenant_auxiliaries` por `company_id`; se `conversation_id` vier, exige `conversations.id`+`company_id`; mensagens lidas só da conversa validada.

## 10. Como a conversa é escolhida
- Se `conversation_id` no payload → valida posse (`company_id`) e usa.
- Senão → varre as 20 conversas mais recentes da empresa (`last_message_at desc`) e usa a **primeira com mensagens**. Se nenhuma tiver mensagens → 422 amigável.

## 11. Como o LLM é chamado
`ChatOpenAI(model='gpt-4o-mini', api_key=get_api_key_for_provider('openai',...), temperature=0.2, max_tokens=1200, response_format=json_object)` via `await llm.ainvoke([System, Human])`. Transcrição formatada (`Cliente`/`Atendente/IA`), limitada a 80 mensagens. Prompt pt-BR: não inventar, arrays vazios se não houver, foco em corretora. Sem dependência nova.

## 12. Como o output é salvo
`auxiliary_runs.output` (jsonb): `{summary, topics[], decisions[], pending_items[], next_steps[], confidence}`. Também grava `token_usage` (jsonb), `cost_usd` (via `usage_service.calculate_cost`), `metadata` (provider/model/conversation_id), `finished_at`, `status='succeeded'`. Custo logado também em `token_usage_logs` (`service_type='auxiliary_run'`, best-effort).

## 13. Como erros são tratados
- Sem auth → 401. Sem Auxiliar ativo → 404. Conversa inexistente/sem posse → 404. Sem conversa/sem mensagens → 422. Falha de leitura → 500 + run `failed`. Falha de LLM → 502 + run `failed`. Toda falha pós-criação marca `auxiliary_runs.status='failed'` + `error_message` + `output` vazio. Logging de custo é best-effort (nunca derruba a execução). Mensagens de erro são claras e **não vazam secrets**.

## 14. O que NÃO foi implementado
UI/telas (38A3), scheduler, criação por prompt, HITL/approval, conectores, RAG, envio externo (WhatsApp/email/portal/seguradora), worker/Celery novo, co-gravação em `session_summaries`, débito de crédito (`credit_transactions`). Sem migration/SQL. Sem hardcode de `company_id`/`user_id`.

## 15. Checks executados
| Check | Resultado |
|---|---|
| `python -m py_compile` (auxiliaries.py, main.py) | ✅ OK |
| `npm run typecheck` | ✅ passou |
| `npm run build` (env dummy) | ✅ passou (`✓ 92/92`; 5 rotas `/api/auxiliaries/*` registradas) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |

## 16. Como testar manualmente
Pré-requisito: estar **logado** no app (cookie de sessão) e o backend FastAPI no ar (`NEXT_PUBLIC_API_URL`/`BACKEND_URL` configurados).
1. **Executar:** no navegador (logado), via console/DevTools:
   ```js
   await fetch('/api/auxiliaries/resumo-atendimentos/run', {
     method: 'POST', headers: {'Content-Type':'application/json'},
     body: JSON.stringify({})  // ou { conversation_id: '<uuid da empresa>' }
   }).then(r => r.json())
   ```
   Esperado: `{ success: true, run: { id, status: 'succeeded', output: { summary, topics, ... } } }`.
2. **Listar execuções:** `await fetch('/api/auxiliaries/runs').then(r=>r.json())`.
3. **Detalhe:** `await fetch('/api/auxiliaries/runs/<runId>').then(r=>r.json())`.
4. **Templates/instalados:** `/api/auxiliaries/templates`, `/api/auxiliaries/installed`.
5. **Conferir no Supabase:** `auxiliary_runs` da empresa deve ter a nova linha (`status`, `output`, `token_usage`, `cost_usd`); `token_usage_logs` com `service_type='auxiliary_run'`.
> Teste por curl puro é inviável (precisa do cookie de sessão). Use o navegador autenticado.

## 17. Riscos e limitações
- **Contrato de colunas:** o código grava em `auxiliary_runs` as colunas descritas no prompt do 38A2 (`company_id, tenant_auxiliary_id, run_type, status, input, output, error_message, started_at, finished_at, token_usage, cost_usd, metadata`). Se o schema real divergir de algum nome, é ajuste de 1 linha; leituras usam `select('*')` (resilientes).
- **Trust Next→backend:** segue o modelo do chat (sem segredo interno). O `company_id` é derivado no servidor e revalidado no backend, mas uma chamada direta ao backend com `company_id` arbitrário teria o mesmo risco do chat atual → **P1: adicionar token interno Next↔backend** (hardening futuro, ADR/Vault).
- **Status:** uso `succeeded`/`failed`/`running` (contrato do prompt). Se o CHECK do banco exigir outros valores, ajustar.
- **Sem débito de crédito** ainda (apenas log de custo). **Sem RAG** (só mensagens). **Síncrono** (resumo rápido).

## 18. Próximo batch recomendado: 38A3 UI wiring
Ligar a UI (sem mexer no motor): em `app/dashboard/auxiliares/galeria/resumo-atendimentos` usar `lib/auxiliaries/api.ts` para **Executar** (com seletor de conversa) e exibir o resultado; `meus` lista `installed`; `execucoes` lista `runs` (StatusPill por status) + detalhe da run. Depois: 38A4 (token interno Next↔backend + débito de crédito) e fases de HITL/conectores quando entrar Auxiliar com ação externa.
