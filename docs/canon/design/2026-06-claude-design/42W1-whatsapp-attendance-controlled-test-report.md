# 42W1 — WhatsApp Attendance Controlled Test, Conversational Policy Selection & Auto Dispatch Draft Report

> **Status:** concluído · testes offline **172 verdes** (23 policy-selection + 44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `py_compile` OK · `typecheck` EXIT=0 · build verde · `git diff --check` limpo · **sem schema novo** · **sem runtime paralelo** (orquestra os endpoints existentes) · **sem envio externo real** (dry-run + flag explícita default OFF).
> **Data:** 2026-06-16 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos auditados
SPEC-007/008, relatórios 42W0/42B6/42I3B, `backend/app/api/webhook.py`, `message_buffer_service`, `buffer_processor`, `whatsapp/*`, `integration_service`, `core/config`, e no Next: `whatsapp/inbound`, `runtime/{reply,step,policy-lookup,policy-select,dispatch-dry-run}`, `lib/attendance/{whatsapp-inbound,whatsapp-case-routing,corridor-runtime,runtime-message-router,policy-evidence-pack,dispatch-readiness}`.

## 2. Arquivos alterados/criados
- `lib/attendance/whatsapp-policy-selection.ts` (**novo**, puro) — `resolvePolicySelectionFromCustomerReply`, `buildPolicyOptionsMessage`, `buildPolicySelectedMessage`.
- `lib/attendance/whatsapp-orchestration.ts` (**novo**) — `callRuntimeInternal`, `maybePrepareDispatchDraft` (hook idempotente).
- `lib/attendance/runtime-internal-auth.ts` (**novo**) — `resolveInternalCompanyId` (auth interna compartilhada).
- `app/api/attendance/whatsapp/inbound/route.ts` (**alterado**) — seleção conversacional + **avanço autônomo** (auto policy-lookup → multiple/found → step) + auto dispatch draft + flag de envio real.
- `app/api/attendance/whatsapp/preflight/route.ts` (**novo**) — preflight sanitizado.
- `app/api/attendance/whatsapp/simulate-inbound/route.ts` (**novo**) — simulador (reusa o bridge).
- `app/api/attendance/cases/[caseId]/runtime/{reply,step,policy-lookup,policy-select,dispatch-dry-run}/route.ts` (**alterado**) — branch de **auth interna aditivo** (sessão do dashboard inalterada).
- `scripts/whatsapp-policy-selection.test.mjs` (**novo**) + `package.json` (**alterado**).
- `docs/canon/design/2026-06-claude-design/42W1-...md` (este).

## 3. Envs necessárias
**Next (app):** `BACKEND_INTERNAL_API_KEY` (igual ao backend); `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED=false` (default; envio real só quando `true`); `ATTENDANCE_WHATSAPP_DRY_RUN` (default dry-run).
**Backend:** `ATTENDANCE_WHATSAPP_ENABLED=true` (liga o desvio para o Attendance Runtime), `ATTENDANCE_BRIDGE_URL=<app>/api/attendance/whatsapp/inbound`, `BACKEND_INTERNAL_API_KEY`, `WHATSAPP_WEBHOOK_AUTH_MODE=shared_secret` + `WHATSAPP_WEBHOOK_SECRET` (produção), Redis para buffer/dedupe.

## 4. Preflight — como rodar
`GET /api/attendance/whatsapp/preflight` (logado). Retorna `{ ok, readiness: ready|warning|blocked, checks[], blockers[], warnings[], next_required_env[] }` — verifica chave interna, envio real OFF, integração WhatsApp ativa, agente attendance, conexão InfoCap; envs do backend são sinalizadas para checagem no backend. **Sem segredo/telefone.**

## 5. Simulate-inbound — como rodar
`POST /api/attendance/whatsapp/simulate-inbound` (logado) — testa o fluxo completo **sem Z-API real**. Cria/reusa uma conversa de teste estável por (company, phone) e **delega ao mesmo bridge** (não duplica). Body: `{ from_phone, text, from_name?, agent_id?, message_id? }`. Retorna `{ action, case_id, conversation_id, auto_reply, outbound:{dry_run}, diagnostics }`.

## 6. Seleção conversacional de apólice (lacuna do WhatsApp resolvida)
`resolvePolicySelectionFromCustomerReply(message, matches)` — determinístico, sem LLM. Entende: ordinal/número ("a primeira", "2", "opção 3"), `policy_ref` explícito ("97652"), final mascarado ("final 99", "termina em 53"), data/ano ("vence em 31/10/2026", "a de 2026"), seguradora/produto, e afirmativo quando há só uma opção. **Só aceita `policy_ref` presente nos matches**; ambíguo → não seleciona e pede lista curta mascarada (`buildPolicyOptionsMessage`). Resolveu → chama `policy-select` interno → resposta humana (`buildPolicySelectedMessage`: "Perfeito, selecionei a apólice com final ****99. Ela está vigente…").

## 7. Avanço autônomo no bridge (sem cliques)
O bridge orquestra os **endpoints existentes** (não recria runtime):
1. **multiple_matches pendente** + resposta do cliente → resolve seleção → `policy-select` → dispatch draft.
2. Senão → `runtime/reply` (intake/identidade/slots, mesmo cérebro do dashboard).
3. Se `macro=policy_lookup_required` (após CPF) → **auto `policy-lookup` InfoCap**: `multiple_matches`→ pergunta qual apólice; `found`→ `step` (mensagem inteligente); outros→ next_step humanizado.
4. `maybePrepareDispatchDraft` (idempotente) quando a apólice está verificada.

## 8. Auto dispatch draft
`maybePrepareDispatchDraft(caseId)` só dispara com `verification_status` verificada; chama `dispatch-dry-run` interno (idempotente). `hitl_required` → *"Já organizei o pacote… nossa equipe precisa validar a cobertura…"*; `ready_for_human_approval` → *"…pronto para aprovação de envio…"*; `incomplete` → não anuncia (segue coletando). **Nunca envia externo.**

## 9. Segurança do outbound
Envio real exige **3 condições**: `environment='production'` + `external_send_authorized=true` + **flag `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED=true`** (default false). Sem todas → dry-run (`outbound.sent=false`, salva no histórico, loga `outbound_dry_run`). O backend só envia quando o bridge devolve `external_send_allowed=true && dry_run=false`. Dispatch externo (42B6) segue `external_action_sent=false`.

## 10. Handoff / Mídia
- **Handoff**: case em `handoff` → bridge registra inbound e **não responde** (`handoff_blocked_auto_reply`); webhook já respeita `HUMAN_REQUESTED`.
- **Mídia**: áudio/imagem/documento/localização sem texto → **ack humano seguro** + registro do tipo; não vaza URL; não manda mídia bruta a LLM; **TODO 42M0**.

## 11. Observabilidade (sanitizada)
`diagnostics.events[]`: `inbound_received`, `case_routing:<action>`, `case_created`, `runtime_reply_called`, `policy_lookup_auto`, `policy_lookup_multiple_matches`/`_found`, `policy_selection_resolved`/`_ambiguous`/`_failed`, `dispatch_draft_auto_prepared`, `outbound_dry_run`/`outbound_sent`, `handoff_blocked_auto_reply`, `media_ack`. Sem telefone cru/CPF/token/payload.

## 12. Conversa controlada E2E (simulada) — como rodar
```js
// logado no dashboard (cookie de sessão). Mesmo from_phone mantém a conversa.
async function sim(text){const r=await fetch('/api/attendance/whatsapp/simulate-inbound',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from_phone:'5544998887766',from_name:'Cliente Teste',text})});return r.json();}
await sim('Oi');
await sim('estou sem luz');
await sim('só na cozinha');
await sim('não tem cheiro de queimado nem faísca');
const cpf = await sim('04760897941');           // → auto InfoCap → multiple_matches → lista de apólices
console.log('apólices:', cpf.auto_reply);
const pick = await sim('a primeira');             // → policy-select 97652 → evidência + dispatch draft
console.log('selecionado:', pick.auto_reply, pick.dispatch_packet_state);
await sim('é na cozinha');
await sim('fico totalmente sem energia na cozinha');
const end = await sim('sim, é o mesmo endereço da apólice'); // → dispatch dry-run preparado
console.log('fim:', end.auto_reply, end.dispatch_packet_state, end.outbound);
```
**Esperado:** case `channel='whatsapp'` criado; conversation vinculada; `multiple_matches`; seleção por texto executa `policy-select`; `coverage_readiness=human_validation_required`; `dispatch_packet_state=hitl_required`; `outbound.dry_run=true`; **nenhuma ação externa**.

## 13. Modo real controlado (webhook Z-API) — como testar (sem habilitar envio real)
1. Backend: `ATTENDANCE_WHATSAPP_ENABLED=true`, `ATTENDANCE_BRIDGE_URL`, `BACKEND_INTERNAL_API_KEY`, `WHATSAPP_WEBHOOK_AUTH_MODE=shared_secret`, `WHATSAPP_WEBHOOK_SECRET`, `DRY_RUN=true` (ou integração sandbox).
2. Integração WhatsApp **ativa** vinculada ao **agente attendance** (provider z-api, `connectedPhone`).
3. App: `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED=false` (mantém dry-run).
4. Enviar mensagens reais ao número conectado → buffer consolida → bridge → runtime → **resposta dry-run** (não sai no WhatsApp).
5. Ver o case em **Atendimentos → Casos** no dashboard (channel=whatsapp), com a conversa espelhada. **Outbound real NÃO é habilitado neste batch.**

## 14. Testes que rodei (eu mesmo)
- `node scripts/whatsapp-policy-selection.test.mjs` → **23/23** (ordinal/número/ref/final/data/afirmativo/ambíguo; só aceita ref dos matches; mensagens sem número cru).
- Regressão: whatsapp-inbound **44/44**, dispatch **35/35**, coverage **33/33**, evidence **37/37**.
- `python -m py_compile` (webhook+config) OK · `npx tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo. Dashboard/simulador e Core **não alterados** (auth interna é aditiva; fluxo de sessão idêntico).

## 15. Riscos remanescentes
- Assinatura real Z-API (hoje `shared_secret`; `provider_signature` pronto, inerte).
- Plaintext legado residual de token/client_token (recadastrar pela camada cifrada).
- Outbound real homologado (gate de 3 condições pronto; ativar só com observabilidade + rate-limit em 42W2).
- Mídia completa (transcrição/visão) → 42M0.
- Bridge usa a `BACKEND_INTERNAL_API_KEY` compartilhada — avaliar chave dedicada + assinatura.
- E2E real com CPF depende de InfoCap connection + integração ativas no ambiente (o simulador cobre o fluxo conversacional sem Z-API).

## 16. Critério de pronto
| Critério | Status |
|---|---|
| preflight existe | ✅ |
| simulate-inbound existe | ✅ (reusa bridge) |
| inbound controlado cria/roteia case | ✅ |
| múltiplas mensagens não quebram | ✅ (buffer reusado) |
| seleção conversacional funciona | ✅ (23/23) |
| policy-select chamado por texto | ✅ |
| dispatch-dry-run auto-preparado | ✅ (idempotente) |
| outbound permanece dry-run | ✅ (flag default OFF) |
| handoff bloqueia auto-resposta | ✅ |
| mídia simples não quebra | ✅ |
| dashboard mostra estado | ✅ (case channel=whatsapp + painéis 42B6/42I3B) |
| testes verdes | ✅ 172/172 |

## 17. Decisão: seguir para 42W2 ou corrigir pendências?
**Pode seguir para 42W2 — WhatsApp Controlled Real Webhook Conversation**, com guarda: o 42W2 deve rodar a conversa real **em dry-run** (sem habilitar `WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED`), validar buffer/dedupe/seleção/dispatch com mensagens reais, e só então planejar o **envio real homologado** (com assinatura de webhook real, observabilidade e rate-limit). A lacuna conversacional (seleção de apólice por texto) e o avanço autônomo estão fechados; nada bloqueia o teste real em dry-run. Mídia completa fica para **42M0**.

## 18. Checks
| Check | Resultado |
|---|---|
| `node scripts/whatsapp-policy-selection.test.mjs` | ✅ 23/23 |
| whatsapp-inbound / dispatch / coverage / evidence (regressão) | ✅ 44/35/33/37 |
| `python -m py_compile` | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| runtime paralelo · provider recriado · n8n · Evolution principal · envio externo · seguradora/prestador · schema · PII/token exposto · quebra dashboard/Core | ✅ nenhum |
