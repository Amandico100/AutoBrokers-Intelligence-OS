# 42B5L-FE — Runtime LLM Fallback Integration for Attendance Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só TS/Next no runtime de atendimento** (sem SQL/schema/migrations, sem backend Python, sem RAG ingestion, sem prompts do Core, sem Auxiliares/WhatsApp/InfoCap/dispatch/approval/Vault) · sem deploy automático.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `lib/attendance/runtime-llm-fallback.ts` (**novo**) — `isAttendanceFallbackEnabled`, `isFallbackKind`, `shouldUseLlmFallback`, `sanitizeAttendanceFallbackText`, `buildAttendanceFallbackContext`, `buildAttendanceFallbackGuardrails`, `requestAttendanceFallback`, `attemptAttendanceLlmFallback`.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — integra o fallback no **gate de identidade** e no **fluxo de slot** (só off-topic/clarificação); `resolveAttendanceAgentId`; captura `recentMessages` para contexto.
- `docs/canon/design/2026-06-claude-design/42B5L-FE-runtime-llm-fallback-integration-report.md` (este).

## 2. Usou o endpoint backend? **Sim**
Consome `POST {BACKEND}/attendance/agent-reply` (42B5L-BE) server-side, com timeout de 10s. Em `ok:true` usa o `reply`; em erro/timeout/`ok:false`/desabilitado → **resposta determinística do 42B5K**.

## 3. Feature flag / env
- **`ATTENDANCE_LLM_FALLBACK_ENABLED`** — precisa ser `"true"` no **Web** para ativar. **Default: desabilitado** (ausente/≠"true" → comportamento idêntico ao 42B5K.1).
- URL do backend: reusa `NEXT_PUBLIC_BACKEND_URL` (ou `ATTENDANCE_AGENT_REPLY_URL`/`BACKEND_URL`) — **nenhuma credencial nova** no Web.

## 4. Quando usa LLM (e quando NUNCA usa)
**Usa** apenas para `off_topic_general_question` e `clarification_question` (conversacional, **sem mudar estado**), e só se: flag ON, há agente de atendimento, caso editável, **sem risco alto**, **sem CPF/CNPJ** (≥8 dígitos bloqueia).
**Nunca usa** para: risco alto/possível, CPF/CNPJ/muitos dígitos, confirmar/decidir cobertura, acionamento, dispatch, InfoCap, mudar status/slots/macro_state, caso handoff/closed/cancelled, ou slot extraível (frustração/correção/slot_answer seguem determinísticos).

## 5. Como escolhe o agent_id (nunca Core)
`resolveAttendanceAgentId`: usa `attendance_cases.assigned_agent_id`; se ausente, busca um agente da mesma `company_id` com `agent_role='attendance'` **e** `agent_audience='insured_external'`. Sem agente de atendimento → fallback determinístico. O backend ainda **revalida** role/audience/empresa (recusa Core/403).

## 6. Sanitização e segurança
- **Nunca** envia `insured_document_ref`/CPF/CNPJ, `policy_snapshot` cru, diagnostics internos, slots brutos ou secrets. Contexto enviado: `case_summary`, `active_question`, `next_step`, `macro_state`, `status`, `risk_level`, `policy_verified`, `coverage_summary` (saneado), `recent_turns` (≤6, saneados).
- `sanitizeAttendanceFallbackText` mascara sequências longas de dígitos e limita tamanho — aplicado à mensagem, ao contexto e à resposta recebida.
- O caso devolvido na resposta continua passando por `safeReplyCase` (sem `insured_document_ref`).

## 7. Estado preservado (não muda por texto LLM)
O fallback só substitui o **texto** da resposta assistant. Mantém `last_agent_action`, `selected_slot`, `next_step`, `macro_state` e o gate ativo (ex.: continua pedindo CPF). Registra `diagnostics.runtime.llm_fallback = { attempted, used, reason, error_code?, safe:true, at }` — sem prompt/contexto bruto/PII.

## 8. Observabilidade
`diagnostics.runtime.llm_fallback` no gate de identidade e no fluxo de slot: `attempted` (tentou), `used` (usou o reply), `reason` (kind/`disabled`/`ineligible`), `error_code` (timeout/fetch_error/not_attendance_agent/…), `at`, `safe:true`.

## 9. Compatibilidade
Com a flag **off** (default), tudo igual ao 42B5K.1. Com a flag **on**: greeting/problem/low risk/high risk handoff/CPF capture/policy lookup/resume/frustração/CPF indisponível/`policy_evidence_status`/`safeReplyCase`/Core/Auxiliares/RAG — preservados; muda só o **texto** de off-topic/clarificação (que passa a responder de fato e voltar ao atendimento).

## 10. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/schema/backend Python/RAG/prompts/Auxiliares/WhatsApp/InfoCap/dispatch/Vault | ✅ nenhum |
| Core | ✅ intacto |
| CPF/secret/PII enviado ao LLM ou logado | ✅ nenhum (sanitizado) |

## 11. Testes manuais (após deploy Web **com** `ATTENDANCE_LLM_FALLBACK_ENABLED=true` + backend 42B5L-BE no ar)
- **A — off-topic no gate de CPF:** "O que significa van nos nomes holandeses?" → responde brevemente e volta ao CPF. (flag off → resposta determinística honesta do 42B5K).
- **B — comparação:** "É tipo da Silva no Brasil?" → responde e volta ao CPF.
- **C — CPF indisponível:** "Meu CPF está com meu filho, posso mandar depois?" → mantém `identity_required`, não avança (determinístico; não é fallback kind).
- **D — frustração:** "JÁ DISSE, É NA COZINHA, QUERO ELETRICISTA" → inferência determinística do 42B5K (sem LLM).
- **E — risco alto:** "Tem cheiro de queimado e faísca" → handoff de segurança (sem LLM).
- **F — Core/Auxiliares/RAG:** intactos (NEVOA-791).
- Conferir `diagnostics.runtime.llm_fallback.used=true` em A/B quando o backend responde; `used=false`+`error_code` em falha (com texto determinístico).

## 12. Riscos
- Requer a flag ligada **e** o backend 42B5L-BE deployado; senão comporta-se como 42B5K.1 (seguro).
- Billing: cada uso consome créditos (só off-topic/clarificação).
- Latência: timeout de 10s; em estouro cai no determinístico.

## 13. Próximo recomendado
**42I2 — InfoCap Connector Read-only (via Vault)** (troca o policy lookup mock por consulta real mantendo contrato/simulador) e **42B7 — Golden tests** do fluxo E2E. Opcional: ligar a flag em staging para validar o fallback com o backend no ar.
