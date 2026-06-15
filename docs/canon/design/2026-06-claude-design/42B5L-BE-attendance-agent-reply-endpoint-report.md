# 42B5L-BE — Attendance Agent Reply Endpoint (Backend / Smith) Report

> **Status:** concluído · `py_compile` verde · Web typecheck verde (não afetado) · `git diff --check` limpo · **só backend Python** (sem SQL/schema/migrations, sem Web/Next funcional, sem RAG ingestion, sem prompts globais do Core, sem Auxiliares/WhatsApp/InfoCap/dispatch/approval/Vault) · sem deploy automático.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `backend/app/api/attendance_agent_reply.py` (**novo**) — endpoint stateless guardrailado.
- `backend/app/main.py` (**alterado**) — registra o router (sem prefixo) → rota `POST /attendance/agent-reply`.
- `docs/canon/design/2026-06-claude-design/42B5L-BE-attendance-agent-reply-endpoint-report.md` (este).

## 2. Endpoint criado
`POST /attendance/agent-reply` — **stateless** e **guardrailado**.
- **Request:** `{ company_id, agent_id, message, context?, guardrails? }` (contrato do batch).
- **Response ok:** `{ ok:true, reply, safe:true, agent_id, mode:"attendance_stateless_reply" }`.
- **Response erro:** `{ ok:false, error:"<safe_error_code>" }` (`empty_message` · `agent_not_found` · `forbidden_company` · `not_attendance_agent` · `reply_unavailable` · `reply_timeout` · `empty_reply`). Validação retorna 4xx (404/403) com corpo `{ok:false,error}`; falha de runtime/LLM retorna **200 {ok:false,error}** para o Web cair no fallback determinístico.

## 3. Usou infraestrutura Smith existente? **Sim.**
- **LLM:** `LLMFactory.create_llm(company_config=agent, agent_data=agent, api_key, company_id, agent_id)` + `get_api_key_for_provider(provider, model)` — a mesma infra do `langchain_service`/grafo. **Não** chamei OpenAI/Anthropic direto/paralelo.
- **Chamada:** uma única `await llm.ainvoke([SystemMessage, ...history, HumanMessage])` (padrão idêntico ao `subagent_tool.py`). **Sem grafo, sem tools, sem RAG, sem memória, sem persistência.**
- O `CostCallbackHandler` embutido em `create_llm` mantém o billing consistente (service_type="chat").

## 4. Garantias (o que o endpoint NÃO faz)
Stateless: **não** persiste mensagem do usuário/assistente; **não** toca `conversations`/`messages`/`attendance_cases`/`corridor_runs`; **não** cria dispatch/approval; **não** aciona WhatsApp/InfoCap/portal; **não** confirma cobertura; **não** usa o Core. Recusa (`403 not_attendance_agent`) qualquer `agent_id` cujo `agent_role != 'attendance'` ou `agent_audience != 'insured_external'` — impede o Core (ou outro papel) de falar com o segurado.

## 5. Guardrails e contexto
- **System prompt curto** (PT) fixa: atendente da corretora p/ o segurado (não Core); curto/WhatsApp; pode responder dúvida geral e voltar ao próximo passo; nunca confirmar cobertura/dizer que acionou/prometer prazo/pedir dado desnecessário/expor CPF/macro_state/slots/diagnostics/inventar apólice; sensível → cautela; não sabe → natural. Incorpora `guardrails.must/never` recebidos.
- **Contexto sanitizado** do request (case_summary, active_question, next_step, policy_verified, coverage_summary, recent_turns) é usado só para situar; instrui "voltar à pergunta atual".

## 6. Validações e segurança
- `agent_id` deve pertencer à mesma `company_id` (senão **403 forbidden_company**).
- `agent_role='attendance'` e `agent_audience='insured_external'` obrigatórios (senão **403 not_attendance_agent**).
- **Defense-in-depth:** mascara sequências longas de dígitos (CPF/CNPJ/apólice → `[omitido]`) na mensagem e no contexto, mesmo o Web já sanitizando.
- **Logs sanitizados:** só `company`, `agent`, `msg_len`, `reply_len` — nunca conteúdo/PII.
- Reply limitado a `MAX_REPLY_LEN` (1200) e timeout de 30s.

## 7. Env nova?
**Não.** Reusa as chaves de provider já existentes via `get_api_key_for_provider` (OPENAI/ANTHROPIC/GOOGLE/OPENROUTER do backend). Nenhuma credencial nova.

## 8. Alterou SQL/schema/RAG/Web/WhatsApp/InfoCap?
**Não.** Apenas backend Python (1 endpoint + 3 linhas de registro). Web inalterado (typecheck verde por garantia). Sem migrations/RAG/prompts do Core/Auxiliares/WhatsApp/InfoCap/dispatch/Vault.

## 9. Checks
| Check | Resultado |
|---|---|
| `python -m py_compile` (endpoint + main) | ✅ OK |
| `npx tsc --noEmit` (Web, não afetado) | ✅ OK |
| `npm run build` | ⏭️ não reexecutado — **nenhum** arquivo TS/Next alterado (estado idêntico ao último build verde) |
| ruff/mypy | ⚠️ binário não disponível neste ambiente (config presente em `backend/ruff.toml`/`pyproject.toml`) |
| `git diff --check` | ✅ limpo |
| SQL/schema/RAG/Web/WhatsApp/InfoCap/dispatch/Vault | ✅ nenhum |

## 10. Como testar (curl)
> Requer backend rodando e um agente com `agent_role='attendance'`, `agent_audience='insured_external'` na empresa.
```bash
curl -s -X POST "$BACKEND_URL/attendance/agent-reply" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "UUID_DA_EMPRESA",
    "agent_id": "UUID_DO_AGENTE_ATTENDANCE",
    "message": "O que significa van nos nomes holandeses?",
    "context": { "active_question": "Para localizar sua apólice, pode me enviar o CPF do segurado?", "next_step": "Aguardar CPF/CNPJ", "policy_verified": false },
    "guardrails": { "audience": "insured_external", "never": ["confirmar cobertura sem evidência"] }
  }'
```
Esperado: `{ ok:true, reply:"...van costuma significar 'de'/'do'... Voltando: preciso do CPF do segurado para localizar a apólice", safe:true, mode:"attendance_stateless_reply" }`.
- Agente não-attendance → `403 not_attendance_agent`.
- Agente de outra empresa → `403 forbidden_company`.
- Falha de LLM/timeout → `200 { ok:false, error:"reply_unavailable|reply_timeout" }`.

## 11. Riscos
- Qualidade da resposta depende do modelo/config do agente de atendimento; guardrails reduzem (não eliminam) risco de off-topic longo — `MAX_REPLY_LEN` + prompt curto mitigam.
- Billing: cada chamada consome créditos (via CostCallback) — esperado; o Web só chamará para off-topic/clarificação.
- ruff/mypy não rodaram aqui (binário ausente); `py_compile` valida sintaxe. Recomenda-se rodar ruff no CI/deploy.

## 12. Próximo batch recomendado
**42B5L-FE** — `lib/attendance/runtime-llm-fallback.ts` + integração gated por env no `runtime/reply` (e gate de identidade): `shouldUseLlmFallback` (só off_topic/clarification, nunca risco/CPF/slot/cobertura/handoff), `buildAttendanceFallbackContext` (sanitizado), `requestAttendanceFallback` → `POST {BACKEND}/attendance/agent-reply` com timeout; em erro/desabilitado → resposta determinística 42B5K; registrar `diagnostics.runtime.llm_fallback`.
