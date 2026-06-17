# 42X0 — Global External Action Engine Dry-run, Channel Playbooks & Intelligent Execution Planner Report

> **Status:** concluído · testes offline **393 verdes** (42 action-engine + 351 anteriores) · `typecheck` EXIT=0 · build verde · **sem schema** (usa `metadata`) · **channel-agnostic/global** · **NENHUM envio externo** (`external_action_sent=false` sempre) · **não confirma cobertura** · **sem PII**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquitetura do Action Engine
Camada **global e channel-agnostic** que **não** é um runtime conversacional novo: lê `attendance_case` + `corridor_run` + `dispatch_packet` + os gates (`coverage_readiness`/`dispatch_readiness`) — que continuam a **autoridade** — e produz um `ExternalActionPlan` em **dry-run**. Avalia canais, escolhe o recomendado, lista dados faltantes, gera draft (mascarado) e interpreta respostas **simuladas** da seguradora. Todo side effect real exigirá adapter + permissão + HITL + flag (42X1+); aqui **nada é enviado**.

## 2. Arquivos criados/alterados
- `lib/attendance/action-engine.ts` (**novo**, puro, self-contained) — playbooks (Allianz eletricista + fallback genérico), `getPlaybook`/`buildInsurerMessageDraft`, `evaluateChannelCandidates`, `buildExternalActionPlan`, `interpretInsurerReply`, `safeActionPlanSummary`.
- `app/api/attendance/cases/[caseId]/runtime/action-plan/route.ts` (**novo**) — POST gera/atualiza, GET retorna (sessão OU chave interna).
- `app/api/attendance/cases/[caseId]/runtime/action-simulate/route.ts` (**novo**) — interpreta resposta simulada; registra evento sanitizado.
- `app/api/attendance/cases/[caseId]/runtime/action-approve-dry-run/route.ts` (**novo**) — aprova p/ futura execução (não envia).
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**alterado**) — painel "Plano de acionamento externo (dry-run)" + simulador de resposta.
- `scripts/attendance-action-engine.test.mjs` (**novo**) + `package.json` (`test:action-engine`).
- `docs/canon/design/2026-06-claude-design/42X0-...md` (este).

## 3. Como é global
- **Playbooks** com `scope: global|insurer|corridor|tenant`; `getPlaybook` escolhe o mais específico (corredor > seguradora > genérico). MVP: `allianz_residential_electrician_whatsapp_v1`; qualquer outro corredor/seguradora cai no `generic_manual_v1` (fallback humano). Adicionar corredor/seguradora = novo playbook, **sem** mexer no engine.
- **Canais** conceituais: `insurer_whatsapp`, `insurer_portal`, `insurer_phone_0800`, `insurer_email`, `insurer_api`, `human_broker_manual`. `evaluateChannelCandidates` ranqueia por prioridade e marca `current_mode` (dry_run/not_configured/future) e `available_now=false` (nada enviável no 42X0).

## 4. Escolha de canal (registry)
A rota consulta `human_support_destinations` (fallback humano disponível) e marca canais de seguradora como `not_configured`/`future` (modelo de conexão de seguradora ainda não existe). O engine seleciona o canal de maior prioridade em `dry_run`; senão, `human_broker_manual`. Estrutura pronta para, no futuro, ler `tenant_connections`/`connector_templates` por seguradora.

## 5. dispatch_packet → ExternalActionPlan (gates)
`buildExternalActionPlan` deriva o `status`:
- `blocked` (risco alto / cobertura bloqueada / conflito) → `human_review_required`, sem draft.
- `incomplete` (faltam slots) → `missing_data`, sem draft.
- `hitl_required` (cobertura não validada) → `human_review_required`, sem draft.
- `ready_for_human_approval` (+ cobertura `human_approved`) → `allowed_to_prepare=true`, **gera draft mascarado**.
`external_action_sent=false` e `dry_run=true` em todos os casos.

## 6. Planner inteligente (sem side effects)
`interpretInsurerReply` (determinístico; LLM opcional no futuro) classifica a resposta simulada: `accepted`, `asks_for_missing_data`, `coverage_question`, `requests_document`, `redirects_channel`, `unavailable`, `human_required`, `unknown` → `next_step` (`ask_insured`/`ask_human`/`update_action_plan`/`retry_message`/`wait`/`manual_handoff`) + `customer_message` humano. **Dado sensível** (CPF) → `ask_human` (nunca pede CPF cru ao cliente). **Cobertura** → `human_required` (nunca confirma). Ambíguo/vazio → `human_required`.

## 7. Imprevistos / recuperação
Seguradora pede apólice/CPF/endereço/telefone → vira `missing_data_request` (sensível → humano; não-sensível → segurado). Redireciona ao portal → `update_action_plan` (canal portal). "Não fazemos assistência" → `manual_handoff`. Pede documento → pede ao segurado. Tudo registrado em `dispatch_packets.metadata.action_simulation_events[]` (sanitizado/truncado).

## 8. Bloqueio de envio real
`external_action.sent=false` em todas as rotas/respostas; `available_now=false` em canais de seguradora; playbooks listam `forbidden_actions` ("enviar sem adapter+permissão+HITL"). `action-approve-dry-run` só marca `approved_for_dry_run` (sem enviar) e exige `status=ready_for_human_approval`.

## 9. Persistência (sem schema novo)
`attendance_cases.metadata.external_action_plan` (+ `action_readiness` summary), `dispatch_packets.metadata.external_action_plan` (espelho) e `dispatch_packets.metadata.action_simulation_events[]`. Sem tokens/destinos crus; drafts mascarados; resposta da seguradora truncada/mascarada.

## 10. Segurança/PII
Draft nunca contém CPF/telefone/endereço completos (só seguradora + nº **mascarado** + área/problema). Summary/diagnostics sanitizados. Testado: sem CPF/telefone no plano/draft/summary; `external_action_sent=false`.

## 11. Testes que rodei (offline)
- `node scripts/attendance-action-engine.test.mjs` → **42/42**: canais; planos (incomplete/blocked/hitl/ready); draft Allianz mascarado (sem CPF/telefone/endereço); fallback genérico; interpretação (accepted/missing/portal/unavailable/document/coverage/ambíguo); CPF→ask_human; summary sem PII; `sent=false`.
- Regressão: document **15**, vision/doc **21**, media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **393/393**.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde. Goldens/Q&A/dispatch preservados.

## 12. Reteste (console, logado)
```js
const id = '<caseId com dispatch dry-run já preparado>';
const plan = await (await fetch(`/api/attendance/cases/${id}/runtime/action-plan`, { method:'POST' })).json();
console.log(plan.action_plan.status, plan.action_plan.selected_channel, plan.external_action); // dry-run, sent:false
console.log(plan.action_plan.message_drafts?.[0]?.text); // draft mascarado quando ready_for_human_approval
const sim = await (await fetch(`/api/attendance/cases/${id}/runtime/action-simulate`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ simulated_insurer_reply:'Qual o número da apólice?' })})).json();
console.log(sim.interpretation); // asks_for_missing_data → próximo passo
```
**Esperado:** plano dry-run conforme o gate; draft só quando pronto; resposta da seguradora classificada com próximo passo; **nada enviado**.

## 13. Critério de pronto
| Critério | Status |
|---|---|
| Action Plan dry-run gerado | ✅ |
| canais candidatos avaliados | ✅ |
| playbook Allianz Eletricista existe | ✅ |
| draft para seguradora gerado (mascarado) | ✅ |
| resposta simulada interpretada | ✅ |
| faltas/imprevistos → próximo passo | ✅ |
| nada externo enviado | ✅ (`sent=false` sempre) |
| PII protegida | ✅ |
| goldens verdes | ✅ 393/393 |

## 14. Próximos (42X1+)
- **42X1 — Action Engine real (WhatsApp da seguradora)**: adapter + `tenant_connection` da seguradora + permissão + HITL + flag `EXTERNAL_ACTION_REAL_ENABLED`; envio só após aprovação humana.
- **Portal (Browserbase/Skyvern), 0800 (voz), e-mail/API**: adapters específicos, cada um homologado.
- **LLM no planner**: reescrita de mensagem/interpretação de resposta (gated), sem decidir side effects/cobertura.
- **42W2** — webhook real Z-API (pausado) · **42R1** — KB real (Qdrant).

## 15. Checks
| Check | Resultado |
|---|---|
| `node scripts/attendance-action-engine.test.mjs` | ✅ 42/42 |
| document/vision/media/knowledge/policy-qa/intent/selection/whatsapp/dispatch/coverage/evidence | ✅ 15/21/36/22/37/39/32/44/35/33/37 |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · runtime paralelo · envio externo · confirma cobertura · ignora HITL · PII · quebra goldens | ✅ nenhum |
