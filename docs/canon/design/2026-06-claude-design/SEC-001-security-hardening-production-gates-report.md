# SEC-001 — Security Hardening & Production Gates Report

> **Status:** concluído · testes offline **31 verdes** (security-production-gates) + regressão portal/ação verde · `typecheck` EXIT=0 · build verde · **NENHUM side effect real ativado** · gates **falham fechado** (env ausente ⇒ bloqueado) · `real_action_allowed=false`, `send_allowed=false`, `canSendReal=false` mantidos.
> **Data:** 2026-06-19 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Sobre o teste 404 do 43P3.1
As rotas `skill-factory/*` deram **404 em produção** porque o deploy ainda não havia reconstruído com o commit `34e8150` quando o teste rodou — **não é bug**: o build local compilou as três rotas e o tsc passou. Basta reexecutar o teste após o deploy. Este build do SEC-001 recompila tudo e confirma as rotas.

## 1. O que foi hardenizado
Criada a camada de **gates de produção que falham fechado** + **redação de PII/segredos**, integrada (de forma aditiva) aos pontos que cruzariam a fronteira sandbox→real, sem ativar nada. Nenhuma flag real foi ligada; nenhum portal/WhatsApp/Browserbase/credencial real foi tocado.

## 2. Quais gates existem
`lib/security/production-gates.ts` (puro): `getProductionFlags`, `evaluateGlobalKillSwitch`, `evaluatePortalRealActionGate`, `evaluateExternalActionRealSendGate`, `evaluateRagKnowledgePublishGate`, `evaluateMemoryAccessGate`, `explainGateBlockers`, `assertNoRawSecrets`, `assertNoPIIInLogPayload`, `sanitizeAuditPayload`. Todos retornam `allowed=false`/`real_action_allowed=false` neste estágio — **mesmo com todas as flags ligadas** (provado em teste: portal/external gate continuam `allowed=false`).

## 3. Quais flags default false (falha fechado)
`GLOBAL_KILL_SWITCH` (default **ativo**; só `=false` desliga), `PORTAL_REAL_ACTION_ENABLED`, `PORTAL_LOGIN_REAL_ENABLED`, `PORTAL_SESSION_CAPTURE_ENABLED`, `EXTERNAL_ACTION_REAL_ENABLED`, `INSURER_WHATSAPP_REAL_SEND_ENABLED`, `RAG_PUBLISH_TO_ATTENDANCE_ENABLED`, `MEMORY_LONG_TERM_ENABLED`, `WEB_SEARCH_CORE_ENABLED`, `MEDIA_PUBLIC_URLS_ENABLED` — todas `=== 'true'` para ligar (ausente ⇒ bloqueado). `WEB_SEARCH_ATTENDANCE_ENABLED` é **travado em false no código** (ignora env) no MVP.

## 4. Integrações (aditivas, sem mudar bloqueio existente)
- `relay/start` → `production_gate = evaluatePortalRealActionGate(...)` no response.
- `action-outbox/approve` → `production_gate = evaluateExternalActionRealSendGate(...)` no response.
- Nova rota admin `GET /api/admin/security/production-gates` (health-check: flags booleanas, kill switch, gates, sem segredos).
- Os bloqueios reais já existentes (42X/43P: `send_allowed=false`, `canSendReal=false`, `real_action_allowed=false`) permanecem — os gates são uma **segunda barreira**.

## 5. Riscos do RAG0.1 — corrigidos vs. follow-up
**Corrigidos por app-level gate (código, já ativo):**
- Acesso indevido a memória/conhecimento por Attendance → `evaluateMemoryAccessGate` (Attendance só `insured_external` + próprio caso; cross-tenant/company bloqueados) e `evaluateRagKnowledgePublishGate` (broker_internal/confidential/restricted **proibidos** no Attendance; raw_intake → quarantine; sem audience/sensitivity → bloqueado).
- PII/segredo em logs/traces → `redactPII`/`redactDeep`/`sanitizeAuditPayload` (CPF/CNPJ/telefone/email/OTP/token/cookie/storageState/apikey/vault_ref/storage_ref/destination_ref/base64).

**Follow-up via SQL (guardado, revisar antes de aplicar):**
- `SEC-001-supabase-security-diagnostics.sql` (READ-ONLY): inspeciona policies de `memory_settings`/`user_memories`/`session_summaries`, policy anon de `messages`, buckets públicos, funções `SECURITY DEFINER`, PK de `memory_processing_locks`, RLS de `tenant_connections`, governança de `documents`.
- `SEC-001-security-hardening-migration.sql` (IDEMPOTENTE/GUARDADA): PK em `memory_processing_locks`, índices de memória, e RLS + policy de isolamento por `company_id` nas 3 tabelas de memória **só se a coluna existir** (service role ignora RLS → backend não quebra).

**Follow-up MANUAL (alto risco — NÃO automatizado):** policy anon de `messages` (realtime), buckets `avatars`/`chat-media`/`voice-messages` (avaliar privado + signed URLs com `MEDIA_PUBLIC_URLS_ENABLED`), `search_path` das funções `SECURITY DEFINER`. Documentado no rodapé da migration + aqui.

## 6. Impacto em 43P4
**Desbloqueia o caminho com segurança.** O 43P4 (login setup real) só poderá agir quando `evaluatePortalRealActionGate` retornar `allowed=true`, o que exige: kill switch off + `PORTAL_REAL_ACTION_ENABLED` + `PORTAL_LOGIN_REAL_ENABLED` + `PORTAL_SESSION_CAPTURE_ENABLED` + portal aprovado + dry-run/trace/replay + aprovação humana. Hoje, todos bloqueiam.

## 7. Impacto em RAG1A/RAG1B
`evaluateRagKnowledgePublishGate` + `evaluateMemoryAccessGate` já definem as regras que o RAG1A (security/memory hardening) e RAG1B (governança de `documents`: audience/sensitivity/status/provenance) vão consumir. A migration de memória + diagnostics adiantam o RAG1A no nível de banco.

## 8. Por que nada real foi liberado
Gates `allowed=false` por construção (literal `real_action_allowed:false`); flags default false; kill switch ativo; integrações são apenas snapshots no response; SQL não-destrutivo e guardado; nenhuma chamada a Z-API/Browserbase/portal/credencial real.

## 9. Arquivos criados/alterados
- `lib/security/production-gates.ts` (**novo**) · `lib/security/pii-redaction.ts` (**novo**).
- `app/api/admin/security/production-gates/route.ts` (**novo**).
- `app/api/admin/portal-browser/relay/start/route.ts` + `app/api/attendance/cases/[caseId]/runtime/action-outbox/approve/route.ts` — snapshot de gate (aditivo).
- `docs/canon/design/2026-06-claude-design/SEC-001-supabase-security-diagnostics.sql` (**novo**, read-only).
- `docs/canon/design/2026-06-claude-design/SEC-001-security-hardening-migration.sql` (**novo**, idempotente/guardada).
- `scripts/security-production-gates.test.mjs` (**novo**, 31) + `package.json`.
- `docs/canon/design/2026-06-claude-design/SEC-001-...report.md` (este).

## 10. Testes que rodei (offline)
- `node scripts/security-production-gates.test.mjs` → **31/31**: flags default safe (env vazio bloqueia; web_search_attendance sempre false); kill switch; portal/external (mesmo com tudo ligado → `allowed=false`); RAG (broker_internal bloqueado, insured_external ainda off, raw_intake quarantine, missing audience/sensitivity); memory (attendance só insured_external, cross-tenant/company bloqueados, core com flag); segredos (`assertNoRawSecrets`), PII (`assertNoPIIInLogPayload`/`redactPII`/`sanitizeAuditPayload` mascaram CPF/OTP/email/num e removem cookie/vault_ref).
- Regressão: skill-factory **46**, skill-dryrun **39**, relay **47**, provider **63**, outbox **42**, execution **31** — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 11. Reteste (console admin, logado)
```js
const g = await (await fetch('/api/admin/security/production-gates')).json();
console.log(g.global_kill_switch, g.portal_real_action_allowed, g.external_action_real_send_allowed, g.rag_attendance_publish_allowed);
console.log(g.flags); // só booleans, sem segredos
console.log(g.gates.portal_real_action.blockers);
```
**Esperado:** `global_kill_switch=true`, todos os `*_allowed=false`, `flags` só booleanas, blockers listados.

## 12. Checklist para aplicar no Supabase
1. Rodar `SEC-001-supabase-security-diagnostics.sql` no SQL editor → revisar resultado (policies, buckets, funções, PK).
2. Em **staging**, aplicar `SEC-001-security-hardening-migration.sql` (idempotente) → conferir `notice`s (PK/índices/RLS criados só onde aplicável).
3. Validar que o app (service role) segue funcionando (RLS não afeta service role).
4. Planejar follow-ups manuais (messages/buckets/funções) com testes de realtime/mídia antes.

## 13. Critério de pronto
| Critério | Status |
|---|---|
| production gates existem | ✅ |
| flags ausentes bloqueiam | ✅ (falha fechado) |
| portal/action/RAG/memory real bloqueados | ✅ |
| PII/log sanitizer existe | ✅ |
| SQL diagnostics existe | ✅ |
| migration idempotente existe (+ pendências justificadas) | ✅ |
| rota admin security existe | ✅ |
| testes verdes | ✅ 31 + regressão |
| nenhum side effect real ativado | ✅ |

## 14. Próximos passos
- **Aplicar diagnostics + migration no Supabase** (staging → prod) e endereçar os follow-ups manuais.
- **43P4 — Login setup real controlado** (atrás dos gates: ligar `PORTAL_REAL_ACTION_ENABLED`+`PORTAL_LOGIN_REAL_ENABLED`+`PORTAL_SESSION_CAPTURE_ENABLED` + approval, com kill switch como freio).
- **43P5 — primeira ação real de leitura com HITL** + rollback.
- **RAG1A/RAG1B** consumindo os gates de RAG/memória.
- **E2E final piloto** após 43P5.
