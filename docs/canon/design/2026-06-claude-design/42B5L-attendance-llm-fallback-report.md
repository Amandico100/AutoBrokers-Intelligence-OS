# 42B5L — Attendance Agent LLM Fallback under Runtime Guardrails (BLOQUEADO — REPORT ONLY)

> **Status:** **report-only** — não foi implementado fallback LLM porque **não existe caminho seguro sem gambiarra** dentro do escopo permitido. Nenhum arquivo de código alterado. Sem deploy.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Decisão:** seguir a instrução explícita do batch — "Se não existir caminho seguro para chamar Smith/Attendance Agent sem gambiarras, NÃO criar chamada direta a provedor LLM. Nesse caso, criar apenas relatório explicando o bloqueio e o plano correto."

---

## 1. Foi possível usar Smith/Attendance Agent? **Não (com segurança), ainda não.**

A auditoria encontrou **um** caminho Web→LLM e ele **não serve** para este uso sem violar guardrails/escopo.

### Caminho existente: `POST /api/chat` → backend `/chat`
- `app/api/chat/route.ts` é um **proxy** para `${NEXT_PUBLIC_BACKEND_URL}/chat`.
- `backend/app/api/chat.py::chat_endpoint` aceita `ChatRequest { chatInput, sessionId, companyId, userId, agentId, conversationHistory, options, ... }` e roda o **pipeline completo** do agente (`langchain_service.process_message` → LangGraph + Context Package + RAG + tools + MemoryService).
- Ele **persiste** a mensagem do usuário e a resposta do assistente na conversa localizada por `session_id`, **atualiza a conversa** e usa **memória por sessão**.
- Suporte a Context Package por `agent_role`/`agent_audience` existe (`backend/app/agents/context_package.py`), e o caso de atendimento já tem `assigned_agent_id` (attendance-sandbox) + conversa com `session_id`.

### Por que usar `/chat` agora seria gambiarra/inseguro
1. **Sem injeção de guardrails por chamada.** `ChatRequest` não tem campo para instrução/guardrail por turno ("responda curto, volte à pergunta atual, nunca confirme cobertura, não invente apólice, não exponha macro_state/slots"). Os limites dependeriam só do blueprint do agente — **não verificável/garantível** neste MVP.
2. **Sem contexto sanitizado nem steer-back.** Não há campo para enviar `next_step`/slot atual/`coverage_summary` sanitizado nem para forçar "voltar à pergunta atual". Smuggling disso dentro de `chatInput` **polui a mensagem persistida** e pode **vazar** macro_state/slots/CPF na conversa — proibido.
3. **Conflito de persistência/estado.** `/chat` insere user+assistant e mexe na conversa/memória; o runtime determinístico (42B5C–K.1) **já** controla mensagens, `last_agent_action`, `diagnostics` e `slots`. Chamar `/chat` no meio do turno **duplica mensagens** e desalinha memória/estado.
4. **Pipeline completo (tools/RAG).** Rodar o grafo inteiro para uma pergunta off-topic pode acionar tools/RAG e, sem guardrail por chamada, **arriscar afirmar cobertura/inventar apólice** — exatamente o que o batch proíbe.
5. **Risco de responder como Core.** Se `assigned_agent_id` for nulo, cair no agente default poderia usar o **Core** para falar com o segurado — proibido. (Mitigável, mas reforça que o caminho não é desenhado para isto.)
6. **Billing/efeitos colaterais.** `/chat` faz balance check e consome créditos por turno, fora do controle do runtime.

**Direct provider (OpenAI/Anthropic) no Web:** **proibido pelo batch** e seria motor paralelo. Não feito.

**Conclusão:** o fallback LLM exige um **endpoint dedicado, stateless e guardrailado** no backend (pequeno) — que **não existe** e cujo a criação está **fora do escopo "não alterar backend"** deste batch. Portanto: report-only + plano + pedido de aprovação.

---

## 2. Arquivos alterados
**Nenhum arquivo de código.** Apenas este relatório. A camada determinística do **42B5K** (off-topic re-steer, frustração com inferência, CPF indisponível, clarificação, delay) **permanece como o comportamento seguro atual**.

---

## 3. Plano correto (turnkey para o próximo batch)

### 3.1 Backend — novo endpoint stateless e guardrailado (batch Python — requer aprovação)
`POST /attendance/agent-reply` (NÃO persiste mensagens, NÃO mexe em conversa/memória, NÃO usa tools/dispatch, NÃO é o Core):
```jsonc
// request (tudo sanitizado pelo Next ANTES de enviar)
{
  "company_id": "uuid",
  "agent_id": "uuid|null",        // attendance agent do caso; se null → backend recusa (não usar Core)
  "message": "texto do segurado (sem CPF — Next remove)",
  "context": {
    "case_summary": "string curto, sem PII",
    "active_question": "pergunta atual do agente (ex.: pedir CPF)",
    "next_step": "string",
    "macro_state": "policy_lookup_required|...",
    "status": "policy_check|...",
    "risk_level": "low|...",
    "policy_verified": false,
    "coverage_summary": "string|null (sanitizado)",
    "recent_turns": [{ "role": "user|assistant", "content": "..." }]  // poucos, sanitizados
  },
  "guardrails": {
    "audience": "insured_external",
    "must": ["responder curto/WhatsApp-like","voltar à pergunta atual"],
    "never": ["confirmar cobertura sem evidência","dizer que acionou seguradora/prestador","prometer prazo","pedir dado desnecessário","expor CPF/macro_state/slots","inventar apólice"]
  }
}
// response
{ "ok": true, "reply": "texto curto", "safe": true }
```
- Internamente: usa o **agente de atendimento** (role=attendance, audience=insured_external) em modo "advice/stateless" (sem persistência, sem tools externas), com a instrução de guardrail acima **injetada por chamada**. Recusa se `agent_id` não for um agente `agent_role='attendance'` (impede usar Core).

### 3.2 Next — módulo isolado `lib/attendance/runtime-llm-fallback.ts`
- `shouldUseLlmFallback(route, ctx)` → elegível só para `off_topic_general_question` e `clarification_question` (conversacional puro, **sem** mudança de estado). **Nunca** para risco alto, CPF/CNPJ presente, slot extraível, confirmar cobertura, acionamento, InfoCap, ou caso handoff/closed/cancelled.
- `buildAttendanceFallbackContext(caseRow, run, recentMessages)` → contexto **sanitizado** (remove `insured_document_ref`, secrets, `policy_snapshot` cru; inclui `coverage_summary` saneado).
- `requestAttendanceFallback(...)` → `fetch` server-side para `${ATTENDANCE_AGENT_REPLY_URL}` **gated por env** `ATTENDANCE_LLM_FALLBACK_ENABLED`. Timeout curto. Em erro/timeout/desabilitado → retorna `{available:false}` e o runtime usa a **resposta determinística 42B5K** (requisito #7).

### 3.3 Integração na rota
No branch de recuperação de `runtime/reply` (e no gate de identidade), para `off_topic`/`clarification`: se `shouldUseLlmFallback` e `requestAttendanceFallback` retornar texto → usar como `assistant_message` **mantendo o mesmo estado** (não avança slot, mantém `last_agent_action`/gate). Persistir a mensagem assistant pelo próprio runtime (não pelo backend). Registrar `diagnostics.runtime.llm_fallback = { used, reason, safe:true, provider, at }`. Frustração continua determinística (muda estado por inferência).

### 3.4 Env necessárias (sem valores)
`ATTENDANCE_LLM_FALLBACK_ENABLED` (flag), `ATTENDANCE_AGENT_REPLY_URL` (ou reuso de `NEXT_PUBLIC_BACKEND_URL` + path), timeout. Nenhuma credencial nova no Web (o backend usa as dele).

---

## 4. Guardrails (a aplicar no endpoint quando existir)
você é atendente da corretora para o segurado (não Core) · curto/humano/WhatsApp · pode responder dúvidas gerais simples e voltar ao atendimento · nunca confirmar cobertura sem `coverage_evidence` · nunca dizer que acionou seguradora/prestador · nunca prometer prazo/garantia · não pedir dado desnecessário · não expor CPF/macro_state/slots/diagnostics · não inventar apólice · sensível (jurídico/médico/financeiro alto) → cautela + volta ao atendimento · se não souber, dizer de forma natural e seguir.

## 5. Como evita motor paralelo / Core respondendo o segurado
- O runtime determinístico continua **fonte de verdade** de estado/risco/identidade/apólice/handoff; o LLM só gera **texto** para casos conversacionais e **não altera estado**.
- O endpoint dedicado roda o **agente de atendimento** (não o Core) e **recusa** agent_id que não seja `agent_role='attendance'`.

## 6. Exemplos esperados (quando o endpoint existir)
- "O que significa van nos nomes holandeses?" → "Boa pergunta: em nomes holandeses, 'van' costuma significar 'de'/'do', indicando origem. Voltando: preciso do CPF do segurado para localizar a apólice."
- "Meu CPF está com meu filho, mando depois." → "Sem problema, pode mandar depois. Sem esse dado não valido a apólice agora, mas deixo o atendimento aberto e adianto o possível." *(hoje já coberto deterministicamente pelo 42B5K)*
- "JÁ DISSE QUE É NA COZINHA" → "Você tem razão, já registrei que é na cozinha. Vou seguir sem repetir." *(hoje já coberto deterministicamente)*

## 7. Compatibilidade
Nada mudou → todos os fluxos seguem como no 42B5K.1: greeting/problem/low risk/high risk handoff/CPF capture/policy lookup mock/resume/frustração/CPF indisponível/`policy_evidence_status` satisfied/`safeReplyCase`/Core/Auxiliares/RAG.

## 8. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK (sem mudança de código) |
| `npm run build` | ⏭️ não reexecutado — **nenhum** arquivo TS/Next alterado (apenas este `.md`); estado idêntico ao último build verde (commit 35bfd58) |
| `git diff --check` | ✅ limpo |
| backend/schema/RAG/prompts/WhatsApp/InfoCap/dispatch | ✅ nenhum |
| Core / Auxiliares | ✅ intactos |

## 9. Riscos
- **Risco de não fazer:** off-topic continua respondido de forma honesta porém genérica (sem responder a pergunta em si). Aceitável e seguro até o endpoint existir.
- **Risco de fazer errado (evitado):** usar `/chat`/Core → coverage hallucination, duplicação de mensagens, vazamento de macro_state/CPF, agente errado falando com o segurado.

## 10. Decisão necessária do Founder + próximos passos
1. **Aprovar um batch de backend pequeno** (`42B5L-BE`) para criar `POST /attendance/agent-reply` (stateless, guardrailado, sem persistência/tools, recusa não-attendance) — pré-requisito do fallback LLM seguro.
2. Depois, **`42B5L-FE`**: `lib/attendance/runtime-llm-fallback.ts` + integração gated por env no `runtime/reply` (e gate de identidade), com fallback determinístico em erro.
3. Em paralelo (independente): **42I2** (InfoCap read-only via Vault), **42B7** (golden tests E2E).
