# 42Q0 — Attendance Policy Q&A, Smith Reasoning Layer & Knowledge-Aware Replies Report

> **Status:** concluído · testes offline **257 verdes** (37 policy-qa + 39 intent + 32 selection + 44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `typecheck` EXIT=0 · build verde · **sem schema**, **sem runtime/agent paralelo**, **sem RAG decidindo cobertura**, **sem envio externo**, **sem inventar cobertura**, **sem PII**.
> **Data:** 2026-06-16 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que entrega
O segurado agora pode fazer **perguntas livres** ("tenho cobertura para eletricista?", "minha apólice está ativa?", "por que precisa validar?", "qual a previsão?", "quero falar com humano") **no meio do fluxo**, e o agente responde com inteligência **e limites**, depois **retoma o slot pendente**. O runtime determinístico continua a autoridade de estado; o Evidence Pack / Coverage Readiness é a fonte de verdade operacional.

## 2. Arquivos alterados/criados
- `lib/attendance/policy-qa.ts` (**novo**, puro) — `classifyAttendanceQuestion`, `isAnswerableQuestion`, `buildPolicyQAContext`, `answerPolicyQuestionDeterministic`, `safePolicyQaSummary`.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — interceptação de Q&A (antes da extração de slot), com LLM opcional gated e retomada do slot; handoff em pedido explícito de humano.
- `scripts/policy-qa.test.mjs` (**novo**) + `package.json` (`test:policy-qa`).
- `docs/canon/design/2026-06-claude-design/42Q0-...md` (este).

## 3. LLM/Smith ou determinístico?
**Determinístico é a autoridade** (req 3). `answerPolicyQuestionDeterministic` produz a resposta segura a partir do contexto (sempre). O **LLM** (via caminho existente `runtime-llm-fallback` → backend `/attendance/agent-reply`, **sem motor paralelo**) só é usado **quando `ATTENDANCE_LLM_FALLBACK_ENABLED=true`** e **apenas** para categorias de baixo risco: `policy_status_question`, `process_status_question`, `assistance_question`, `clarification_question` (rephrase/enriquecer). **Nunca** para `policy_coverage_question` nem `dispatch_status_question` (alto risco de inventar cobertura/prazo) — essas ficam **sempre determinísticas**. Se o LLM falhar/estiver off → determinístico. Não criei agente novo nem motor paralelo; reusei o `attemptAttendanceLlmFallback` + guardrails.

## 4. Classificador (`classifyAttendanceQuestion`)
Categorias: `policy_coverage_question`, `policy_status_question`, `assistance_question`, `process_status_question`, `dispatch_status_question`, `clarification_question`, `off_topic_but_answerable`, `customer_frustration` (inclui pedido de humano), `new_issue_or_intent_shift`, `slot_answer`, `unknown`. **Conservador:** só vira Q&A com sinal forte; respostas de slot ("é na cozinha", "sim, é o mesmo endereço da apólice", CPF) permanecem `slot_answer` → fluxo intacto (goldens preservados).

## 5. Contexto sanitizado (`buildPolicyQAContext`)
Inclui intent/corredor, insurer/product, policy_status, active_now, valid_to, coverage_confirmed, coverage_summary, confidence, human_required, cancelled, coverage_readiness_state, dispatch_state, assistance_signals, gaps, pending_question, has_policy, e listas `allowed`/`forbidden`. **Nunca** CPF/telefone/nome/endereço completo/token/payload (testado).

## 6. Exemplos de resposta (determinístico)
- **"cobre eletricista?" (cobertura não confirmada):** *"Localizei uma apólice Allianz Residencial vigente na InfoCap, mas o documento não trouxe os itens de cobertura detalhados para eu afirmar isso automaticamente. Para não te passar informação errada, vou deixar essa cobertura validada pela equipe antes de qualquer acionamento. Para eu continuar: [pergunta do slot]."*
- **"minha apólice está ativa?":** *"Sim, localizei uma apólice Allianz Residencial vigente na InfoCap, com validade até 31/10/2026."*
- **"por que precisa de humano?":** explicação (localizada ≠ confirmada).
- **"qual a previsão?":** *"Ainda não tenho protocolo nem prestador confirmado…"*
- **"quero falar com humano":** encaminha + marca handoff.

## 7. Integração no runtime/reply (e WhatsApp)
A interceptação roda **após resolver o slot alvo e antes de extrair o slot**: se a mensagem é pergunta livre answerable (ou pedido de humano), responde via Q&A + **retoma o slot** ("Para eu continuar: …") e **não consome o slot** (sem mudar estado). Como o **bridge WhatsApp chama o reply in-process** (42W1.1), o Q&A vale **igual no WhatsApp simulate-inbound** — sem repetir CPF/apólice, outbound dry-run preservado.

## 8. RAG/Knowledge
Hoje o Q&A **não** usa RAG para decidir cobertura (proibido). O contexto traz `allowed`/`forbidden` e o conhecimento operacional vem do Evidence Pack. A interface está **future-ready**: quando houver um serviço de knowledge seguro, anexa-se um `knowledge_context` sanitizado **apenas para explicar conceitos gerais**, nunca sobrepondo o evidence_pack — isso fica para o **42R0**.

## 9. Handoff/frustração
- Pedido explícito de humano (`falar com humano`, `atendente`) → resposta empática + **handoff** (`status='handoff'`, `handoff_required`, `handoff_reason='customer_requested_human'`); inbound seguinte é bloqueado pelo bridge.
- Frustração sem pedido de humano → **não** intercepta no Q&A; segue na recuperação conversacional existente (preserva o golden de frustração).

## 10. Flags/envs
- `ATTENDANCE_LLM_FALLBACK_ENABLED` (default off) — liga o rephrase por LLM nas categorias de baixo risco. Off → 100% determinístico (seguro).
- Reusa `ATTENDANCE_AGENT_REPLY_URL`/`NEXT_PUBLIC_BACKEND_URL` do fallback existente.

## 11. Testes que rodei (offline)
- `node scripts/policy-qa.test.mjs` → **37/37**: classificação (coverage/status/dispatch/process/why/assistance/human/slot_answer); coverage não confirmada **não afirma**; confirmada usa evidência; status vigente/cancelada/sem-apólice; previsão sem protocolo; frustração→handoff; contexto **sem PII**.
- Regressão: intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **257/257**.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde. Goldens 42B7.2 preservados (Q&A só dispara em perguntas claras; slot answers/CPF inalterados).

## 12. Reteste manual (console, logado) — pergunta livre no meio do fluxo
```js
// Após ter um caso em coleta (dashboard ou WhatsApp), mande uma pergunta:
const id = '<caseId>';
const r = await (await fetch(`/api/attendance/cases/${id}/runtime/reply`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ message:'mas cobre eletricista mesmo?', source:'dashboard' })})).json();
console.log(r.intake.kind, r.next_step.question); // policy_qa + resposta com limite + retomada do slot
// WhatsApp:
const w = await (await fetch('/api/attendance/whatsapp/simulate-inbound',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from_phone:'5544990001122',text:'minha apólice está ativa?'})})).json();
console.log(w.auto_reply);
```
**Esperado:** `intake.kind='policy_qa'`; resposta humana que **diferencia localizada de confirmada**; termina retomando o slot; nunca afirma cobertura sem evidência; nunca promete prazo; sem PII; `outbound.dry_run=true`.

## 13. Critério de pronto
| Critério | Status |
|---|---|
| segurado faz perguntas livres | ✅ |
| agente responde com inteligência + limites | ✅ |
| não inventa cobertura | ✅ (coverage sempre determinístico) |
| agente retoma o fluxo | ✅ ("Para eu continuar: …") |
| dashboard + WhatsApp simulado | ✅ (reply in-process) |
| LLM fallback/determinístico seguro | ✅ (gated; coverage/dispatch nunca via LLM) |
| goldens continuam verdes | ✅ (Q&A conservador) |
| sem PII/side effects | ✅ |

## 14. Gaps / próximos
- **42R0 — Knowledge/RAG seguro para Q&A:** anexar conhecimento de produto/assistência (explicar conceitos), sem decidir cobertura.
- **42M0 — Media:** "posso mandar foto?" hoje é respondido genericamente; pipeline de mídia completo depois.
- **42W2 — Webhook real Z-API:** pausado (pagamento). O Q&A já vale no WhatsApp simulado.
- LLM rephrase só para categorias de baixo risco; expandir com avaliação/evals (42Q1) se desejado.

## 15. Checks
| Check | Resultado |
|---|---|
| `node scripts/policy-qa.test.mjs` | ✅ 37/37 |
| intent/selection/whatsapp-inbound/dispatch/coverage/evidence | ✅ 39/32/44/35/33/37 |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · runtime/agent paralelo · RAG decide cobertura · envio externo · inventar cobertura · PII · quebra goldens/dashboard | ✅ nenhum |
