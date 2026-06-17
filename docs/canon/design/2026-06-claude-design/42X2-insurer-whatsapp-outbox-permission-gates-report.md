# 42X2 — Insurer WhatsApp Outbox, Permission Gates & Real Adapter Skeleton Report

> **Status:** concluído · testes offline **466 verdes** (42 outbox + 31 action-execution + 42 action-engine + 351 anteriores) · `typecheck` EXIT=0 · build verde · **sem schema** (usa `metadata`) · **NENHUM envio real** (`send_allowed=false` e `sent=false` sempre · `canSendReal=false` em todos os adapters) · **respeita HITL** · **sem PII**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que muda do 42X1 para o 42X2
O 42X1 entregou a **execução sandbox** (estado, eventos, recuperação). O 42X2 constrói a **ponte segura entre sandbox e futura execução real**: uma **outbox** de mensagens externas, **gates de permissão** explícitos, **approval request** (HITL), **trilha de auditoria**, um **adapter skeleton** de WhatsApp da seguradora e **kill switch / flags / rate-limit**. Nada disso envia: `send_allowed` é sempre `false` porque os adapters têm `canSendReal=false` e as flags vêm desligadas por padrão.

## 2. Por que ainda NÃO envia real
Ligar envio real sem essa camada seria perigoso. O 42X2 modela **todos os gates** que precisam passar simultaneamente, mas trava o resultado em `send_allowed=false` por dois motivos redundantes: (a) nenhum adapter tem `canSendReal=true`; (b) `EXTERNAL_ACTION_REAL_ENABLED`/`INSURER_WHATSAPP_REAL_SEND_ENABLED` default `false` e `EXTERNAL_ACTION_KILL_SWITCH` default ativo. O tipo TypeScript de `evaluateExternalSendPermission` retorna `send_allowed: false` (literal), então mesmo que um dia todos os gates passem, este batch não pode liberar envio.

## 3. Arquivos criados/alterados
- `lib/attendance/action-engine.ts` (**alterado**, puro) — `ExternalActionOutboxEntry` + `buildOutboxEntry`/`approveOutboxEntry`/`cancelOutboxEntry`; `evaluateExternalSendPermission` (14 gates); `getInsurerWhatsAppRealAdapterSkeleton` (canSendReal=false, `send()`→`blocked_real_send_disabled`); `buildAuditEvent`/`safeOutboxSummary`; mascaramento de destino/mensagem.
- `app/api/attendance/cases/[caseId]/runtime/action-outbox/prepare/route.ts` (**novo**) — cria entrada draft/awaiting_approval, avalia gates, registra auditoria.
- `app/api/attendance/cases/[caseId]/runtime/action-outbox/approve/route.ts` (**novo**) — `approved_not_sent` (não envia).
- `app/api/attendance/cases/[caseId]/runtime/action-outbox/cancel/route.ts` (**novo**).
- `app/api/attendance/cases/[caseId]/runtime/action-outbox/route.ts` (**novo**, GET) — retorna outbox + auditoria.
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**alterado**) — sub-painel "Outbox & permissão (envio real bloqueado)": preparar/aprovar, status, blockers, gates pendentes, auditoria.
- `scripts/attendance-action-outbox.test.mjs` (**novo**, 42 testes) + `package.json` (`test:action-outbox`).
- `docs/canon/design/2026-06-claude-design/42X2-...md` (este).

## 4. ExternalActionOutbox
Contrato (persistido em `dispatch_packets.metadata.external_action_outbox[]`; resumo em `attendance_cases.metadata.external_action_outbox_summary`):
`outbox_id, case_id, dispatch_packet_id, execution_id, channel, provider, destination_ref_masked, message_text (mascarado), payload_sanitized, status (draft|awaiting_approval|approved_not_sent|blocked|cancelled|sent_future), approval_required, approved_by, approved_at, send_allowed:false, sent:false, blockers[], created_at, updated_at`.
`buildOutboxEntry` exige plano `ready_for_human_approval` (senão `blocked`) e sempre adiciona o blocker `real_send_disabled_42x2`.

## 5. Quais gates impedem o envio
`evaluateExternalSendPermission` checa 14 gates: `real_flag_enabled`, `insurer_whatsapp_real_send_enabled`, `kill_switch_off`, `adapter_can_send_real`, `tenant_connection_active`, `credential_present`, `action_plan_ready`, `execution_ready`, `coverage_human_approved`, `dispatch_ready`, `approval_exists`, `rate_limit_ok`, `channel_homologated`, `no_pii_violation`. No 42X2, no mínimo `adapter_can_send_real`, `real_flag_enabled` e `channel_homologated` falham — e `send_allowed` é forçado a `false` independentemente. Testado: flag off, kill switch, sem tenant_connection, sem credential, sem aprovação, rate-limit estourado, canal não homologado e violação de PII, cada um, bloqueiam.

## 6. Como será ativado no futuro (42X3+)
Para um canal enviar de verdade, **todos** estes precisarão existir simultaneamente: `EXTERNAL_ACTION_REAL_ENABLED=true` + `INSURER_WHATSAPP_REAL_SEND_ENABLED=true` + kill switch desligado + adapter homologado com `canSendReal=true` + `tenant_connection` `connected` com `encrypted_secret_ref` (segredo no Vault, nunca no repo) + `action_plan`/`execution`/`coverage`/`dispatch` nos estados certos + `approval_requests.status='approved'` + rate-limit ok + canal homologado + sem PII. O 42X3 troca o skeleton por um adapter homologado; o 42X4 faz o primeiro envio real controlado.

## 7. Como usar tenant_connection/Vault
A rota `prepare` consulta `tenant_connections` (status `connected`, `encrypted_secret_ref`) de forma **defensiva** (try/catch — a tabela pode não ter linhas ainda) e alimenta os gates `tenant_connection_active`/`credential_present`. O segredo **nunca** é lido nem exposto: usamos apenas a presença da referência. Modela-se o uso futuro de `permission_grants` (ações permitidas) e `approval_requests` (HITL), hoje representados por `approval_required`/`approved_by`/`approval_exists`.

## 8. Como funciona a aprovação
`prepare` cria `awaiting_approval` (ou `blocked`). `approve` chama `approveOutboxEntry` → `approved_not_sent`, gravando `approved_by`/`approved_at`, mas mantendo `send_allowed=false` e `sent=false` — **aprovação ≠ envio**. Aprovar um item `blocked` por gate de segurança não o libera. `cancel` → `cancelled`.

## 9. Audit trail (sem PII)
Eventos sanitizados em `dispatch_packets.metadata.external_action_audit_events[]`: `outbox_prepared`, `approval_requested`, `permission_evaluated`, `adapter_not_real_enabled`, `approved_not_sent`, `send_blocked_by_gate`, `cancelled`. `buildAuditEvent` mascara dígitos longos (CPF/telefone) nas notas. Testado: CPF injetado numa nota não aparece no JSON.

## 10. Adapter skeleton
`getInsurerWhatsAppRealAdapterSkeleton`: `canSendReal=false`; valida destino (8–15 dígitos) e provider (`zapi`/`meta_cloud`/`evolution`); `buildPayload` mascara destino/corpo; `send()` valida pré-condições só para diagnóstico e **sempre** retorna `blocked_real_send_disabled` (ou `no_tenant_connection`/`invalid_*`), **nunca** chamando Z-API/Meta. Nenhum caminho de código chama provider real.

## 11. Kill switch / flags / rate-limit
- `EXTERNAL_ACTION_REAL_ENABLED` (default `false`) · `INSURER_WHATSAPP_REAL_SEND_ENABLED` (default `false`) · `EXTERNAL_ACTION_KILL_SWITCH` (default **ativo** — só `=false` desativa) · `EXTERNAL_ACTION_RATE_LIMIT_PER_HOUR` (default `20`, conta entradas da última hora). Consumidas nas rotas Next via `process.env`; defaults **impedem** envio.

## 12. UI
Sub-painel "Outbox & permissão (envio real bloqueado)" dentro do painel de acionamento: botões "Preparar outbox" / "Aprovar (dry-run)", status, canal/provider/destino mascarado, lista de blockers e gates pendentes, e timeline de auditoria. Deixa explícito "envio real: bloqueado".

## 13. Testes que rodei (offline)
- `node scripts/attendance-action-outbox.test.mjs` → **42/42**: build (blocked/awaiting_approval); approve (approved_not_sent, item blocked não libera); cancel; 11 cenários de gate (todos `send_allowed=false`); adapter skeleton (canSendReal false, validações, `send`→blocked, destino mascarado); auditoria mascara CPF; outbox/summary sem PII/destino cru.
- Regressão: action-execution **31**, action-engine **42**, document **15**, vision/doc **21**, media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **424**. **Total 466/466.**
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde (4 rotas `action-outbox` compiladas).

## 14. Reteste (console, logado)
```js
const id = '<caseId com action-plan ready_for_human_approval>';
const prep = await (await fetch(`/api/attendance/cases/${id}/runtime/action-outbox/prepare`, { method:'POST' })).json();
console.log(prep.outbox_entry.status, prep.permission.send_allowed, prep.permission.blockers); // awaiting_approval, false, [...]
const appr = await (await fetch(`/api/attendance/cases/${id}/runtime/action-outbox/approve`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ outbox_id: prep.outbox_entry.outbox_id })})).json();
console.log(appr.outbox_entry.status, appr.external_action); // approved_not_sent, sent:false
const get = await (await fetch(`/api/attendance/cases/${id}/runtime/action-outbox`)).json();
console.log(get.outbox.length, get.audit_events.map(e=>e.type)); // outbox + auditoria
```
**Esperado:** outbox `awaiting_approval` com `send_allowed=false` e blockers; approve → `approved_not_sent` ainda `sent:false`; auditoria persistida; **nada enviado**.

## 15. Critério de pronto
| Critério | Status |
|---|---|
| outbox existe | ✅ |
| approval existe | ✅ |
| permission gates existem | ✅ (14 gates) |
| adapter skeleton existe | ✅ (`canSendReal=false`) |
| envio real bloqueado por padrão | ✅ (`send_allowed=false` sempre) |
| audit existe | ✅ |
| sem PII | ✅ (destino/CPF mascarados) |
| testes verdes | ✅ 466/466 |

## 16. Próximos passos (42X3)
- **42X3 — Insurer WhatsApp Real Adapter (controlado)**: substituir o skeleton por adapter homologado `canSendReal=true`, atrás de `tenant_connection` real + `permission_grants` + `approval_requests` + flags + rate-limit + kill switch + auditoria no `vault_audit_log`.
- **42X4 — Primeiro envio real homologado**: envio único, com aprovação humana explícita por mensagem e observabilidade total.
- Portal/0800/e-mail/API: cada canal com seu adapter e homologação.
