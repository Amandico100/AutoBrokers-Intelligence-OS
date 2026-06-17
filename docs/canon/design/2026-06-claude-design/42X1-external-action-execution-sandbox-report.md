# 42X1 — External Action Execution State Machine, Insurer Channel Sandbox & Intelligent Recovery Report

> **Status:** concluído · testes offline **424 verdes** (31 action-execution + 42 action-engine + 351 anteriores) · `typecheck` EXIT=0 · build verde · **sem schema** (usa `metadata`) · **channel-agnostic/global** · **NENHUM envio externo** (`canSendReal=false` em todos os adapters · `external_action_sent=false` sempre) · **não confirma cobertura** · **respeita HITL** · **sem PII**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que muda do 42X0 para o 42X1
O 42X0 produzia um **plano** dry-run (`ExternalActionPlan`): canal recomendado, draft mascarado e interpretação de uma resposta isolada. O 42X1 transforma esse plano em uma **sessão de execução com estado** (`ExternalActionExecutionSession`): uma máquina de estados que percorre o ciclo "preparar → enviar (simulado) → receber resposta (simulada) → decidir próximo passo" e **recupera** de imprevistos. Continua tudo **sandbox**: nenhum adapter envia de verdade.

## 2. Arquivos criados/alterados
- `lib/attendance/action-engine.ts` (**alterado**, puro, self-contained) — adicionados `ExecutionStatus`/`ExecutionMode`/`ExecutionEvent`/`ExternalActionExecutionSession`, `ChannelAdapter` + `getChannelAdapter` (todos `canSendReal:false`), `startExecutionSession`, `recoverExternalExecutionStep`, `applyExecutionEvent`, `safeExecutionSessionSummary`. (Também o ajuste cosmético de normalização de área no `buildInsurerMessageDraft`.)
- `app/api/attendance/cases/[caseId]/runtime/action-execution/start/route.ts` (**novo**) — POST: lê `metadata.external_action_plan`, `startExecutionSession`, persiste, `external_action.sent=false`.
- `app/api/attendance/cases/[caseId]/runtime/action-execution/event/route.ts` (**novo**) — POST: aplica evento (`simulated_insurer_reply`/`insured_answer`/`human_note`/`simulated_send_ack`) à sessão.
- `app/api/attendance/cases/[caseId]/runtime/action-execution/route.ts` (**novo**) — GET: retorna a sessão persistida.
- `app/api/attendance/cases/[caseId]/runtime/action-execution/cancel/route.ts` (**novo**) — POST: cancela a sessão.
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**alterado**) — sub-painel "Execução (sandbox)" dentro do painel de acionamento externo: estado/canal/mensagem preparada/update ao cliente, simulador de resposta e timeline.
- `scripts/attendance-action-execution.test.mjs` (**novo**) + `package.json` (`test:action-execution`).
- `docs/canon/design/2026-06-claude-design/42X1-...md` (este).

## 3. A máquina de estados (`ExecutionStatus`)
`startExecutionSession` exige `plan.status === 'ready_for_human_approval'` (senão `{ error }`, sem criar sessão) e nasce em **`waiting_insurer`** com um evento `simulated_send` (preparado, **não enviado**). A partir daí, cada resposta simulada da seguradora é classificada (reusa `interpretInsurerReply`) e `recoverExternalExecutionStep` mapeia para o próximo estado:
- **`completed_sandbox`** — aceito/protocolo (no sandbox; nada real foi aberto).
- **`waiting_insured`** — falta dado não-sensível (endereço/telefone) ou documento → pergunta ao segurado.
- **`waiting_human`** — dado sensível (CPF), pergunta de cobertura, redirecionamento a portal, indisponibilidade, ambiguidade, ou apólice pedida **sem** tê-la (`hasPolicyNumber:false`).
- **`waiting_insurer`** — apólice pedida e **disponível** → segue o fluxo.
- **`cancelled`** — cancelamento manual; estado terminal.
Estados terminais (`completed_sandbox`/`cancelled`) ignoram eventos posteriores (registram `event_ignored_terminal`).

## 4. Adapters de canal — nenhum envia
`getChannelAdapter(channel)` devolve um `ChannelAdapter` com `canSendReal:false` para **todos** os canais. `insurer_whatsapp` e `human_broker_manual` operam em `mode:'sandbox'` (têm fluxo simulado); `insurer_portal`/`insurer_phone_0800`/`insurer_email`/`insurer_api` ficam em `mode:'real_future'` (estrutura reservada, sem implementação de envio). Não há nenhum caminho de código que chame Z-API/Browserbase/Skyvern/Airtop/0800/SMTP/HTTP de seguradora.

## 5. Recuperação inteligente
`recoverExternalExecutionStep(classification, { hasPolicyNumber })` é o cérebro determinístico da recuperação: traduz a classificação da resposta em `next_status` + `suggested_channel` + `customer_update` humano. Casos tratados: aceito, falta de dado (sensível→humano, não-sensível→segurado), pedido de documento, redirecionamento de canal (→ `insurer_portal` + humano), indisponibilidade (→ `human_broker_manual`), pergunta de cobertura (→ humano, **nunca** confirma) e ambiguidade (→ humano). O LLM **não** participa da decisão de side effect nem confirma cobertura; se um dia entrar, será só para reescrever texto, com fallback determinístico.

## 6. Eventos (`applyExecutionEvent`)
Eventos aceitos: `simulated_insurer_reply` (classifica + transita), `insured_answer` (segurado respondeu → volta a `waiting_insurer`), `human_note` (anotação do corretor), `simulated_send_ack` (confirma o "envio" simulado), `cancel` (→ `cancelled`). Cada evento é mascarado por `maskExec` antes de virar excerpt no histórico (CPF/telefone/tokens nunca persistem crus). A sessão guarda `events[]` (timeline) e `external_action_sent` permanece `false`.

## 7. Persistência (sem schema novo)
- `dispatch_packets.metadata.external_action_execution` — a sessão completa.
- `dispatch_packets.metadata.execution_events` — últimos ~30 eventos sanitizados (timeline).
- `attendance_cases.metadata.external_action_execution_summary` — `safeExecutionSessionSummary` (estado/canal/`external_action_sent:false`, sem PII).
O packet é localizado por `idempotency_key = dispatch_dry_run:${caseId}` (mesmo do 42X0/42B6). Nada de tokens/destinos crus.

## 8. UI — timeline e estado
Dentro do painel "Plano de acionamento externo (dry-run)", o sub-painel **"Execução (sandbox)"** mostra: status atual, canal, mensagem preparada, `customer_update` sugerido, um textarea para simular a resposta da seguradora ("Enviar à execução") e a timeline dos últimos 8 eventos. Botões disparam `start`/`event`/`cancel`. Deixa explícito que **nada externo é enviado**.

## 9. Por que ainda não é real
Execução real de qualquer canal exigirá, por canal: **adapter** com `canSendReal:true` homologado + `tenant_connection` da seguradora (segredo no Vault, nunca no repo) + `permission_grant` + **approval humano** + flag `EXTERNAL_ACTION_REAL_ENABLED` + auditoria (`vault_audit_log`) + rate-limit + kill switch. Nenhuma dessas peças é ativada aqui; o 42X1 só prova a **mecânica de estado** offline.

## 10. Segurança/PII
`maskExec` mascara CPF/telefone/tokens em todo excerpt; `safeExecutionSessionSummary` é sanitizado. Testado: CPF injetado numa resposta simulada **não** aparece em `JSON.stringify(session)` nem no summary; `external_action_sent=false` em sessão e summary.

## 11. Testes que rodei (offline)
- `node scripts/attendance-action-execution.test.mjs` → **31/31**: adapters (`canSendReal=false`, whatsapp→sandbox, portal→real_future); start (plano não-pronto → erro; pronto → `waiting_insurer`, `external_action_sent=false`, evento `simulated_send`); estados (aceito→completed, CPF→waiting_human+review, apólice disponível→waiting_insurer, endereço→waiting_insured, portal→waiting_human, documento→waiting_insured, cobertura→waiting_human, indisponível→waiting_human, ambíguo→waiting_human); cancel/insured/terminal (evento após terminal ignorado); sem PII (CPF mascarado, summary sent=false); recovery direto (apólice sem ter→waiting_human).
- Regressão: action-engine **42**, document **15**, vision/doc **21**, media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **393/393**. **Total 424/424.**
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 12. Reteste (console, logado)
```js
const id = '<caseId com action-plan ready_for_human_approval>';
const s = await (await fetch(`/api/attendance/cases/${id}/runtime/action-execution/start`, { method:'POST' })).json();
console.log(s.execution.status, s.external_action); // waiting_insurer, sent:false
const r = await (await fetch(`/api/attendance/cases/${id}/runtime/action-execution/event`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ event_type:'simulated_insurer_reply', text:'Qual o número da apólice?' })})).json();
console.log(r.execution.status, r.customer_update); // próximo estado + update humano
const g = await (await fetch(`/api/attendance/cases/${id}/runtime/action-execution`)).json();
console.log(g.execution.events.length); // timeline persistida
```
**Esperado:** sessão nasce `waiting_insurer` com `sent:false`; resposta simulada transita o estado e gera update humano; timeline persistida; **nada enviado**.

## 13. Critério de pronto
| Critério | Status |
|---|---|
| Action Plan vira Execution Session | ✅ |
| sandbox "executa" a primeira mensagem (simulada) | ✅ |
| resposta simulada vira próximo estado | ✅ |
| recuperação inteligente funciona | ✅ |
| UI mostra timeline/estado | ✅ |
| nada externo é enviado | ✅ (`canSendReal=false` · `sent=false`) |
| PII protegida | ✅ |
| estrutura serve a todos corredores/canais | ✅ |
| goldens verdes | ✅ 424/424 |

## 14. Próximos (42X2+)
- **42X2 — Execução real do WhatsApp da seguradora**: adapter `canSendReal:true` + `tenant_connection` + permissão + HITL + flag `EXTERNAL_ACTION_REAL_ENABLED` + auditoria + rate-limit + kill switch; envio só após approval humano.
- **Portal/0800/e-mail/API**: cada adapter homologado individualmente.
- **LLM no recovery**: reescrita de mensagem/recuperação (gated), sem decidir side effect/cobertura.
- **42P0** — orquestração de aprovação/permissão (Vault `permission_grants`/`approval_requests`).

## 15. Checks
| Check | Resultado |
|---|---|
| `node scripts/attendance-action-execution.test.mjs` | ✅ 31/31 |
| `node scripts/attendance-action-engine.test.mjs` | ✅ 42/42 |
| document/vision/media/knowledge/policy-qa/intent/selection/whatsapp/dispatch/coverage/evidence | ✅ 15/21/36/22/37/39/32/44/35/33/37 |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · runtime paralelo · envio externo · confirma cobertura · ignora HITL · PII · quebra goldens | ✅ nenhum |
