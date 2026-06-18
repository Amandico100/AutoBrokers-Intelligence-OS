# 43P3 — First Portal Skill Dry-run, Portal Map v1 & Skill Eval Harness Report

> **Status:** concluído · testes offline **39 verdes** (portal-skill-dryrun) + regressão portal/ação verde · `typecheck` EXIT=0 · build verde · **sem schema novo** · **NENHUM portal/URL/browser/credencial real** · `real_action_allowed=false`; skill no máximo `sandbox_validated`.
> **Data:** 2026-06-18 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Teste live 43P2 + ajuste de qualidade
O teste live passou em tudo. Encontrei **1 imprecisão** (não-bug de segurança): o challenge "Digite o **código** 123456" classificou como `unknown` em vez de `otp` por causa do acento ("código" ≠ "codigo"). O OTP **foi mascarado** (segurança intacta), mas corrigi a classificação tornando os classificadores (`classifyRelayChallenge` no runtime e `classifyChallenge` nos contracts) **insensíveis a acento** (NFD + strip diacríticos). Também incluí o **gate de elegibilidade nomeado** `evaluateRelayEligibility` no `relay/start` (recusa modo real, downgrade para sandbox), como combinado.

## 1. Qual portal foi escolhido e por quê
**`allianz__allianznet_corretor_portal_do_corretor`** — `sandbox_ready`, `audience=corretor`, `auth_methods=[password]`, `challenge_profile.requires_hitl=false`, `confidence=confirmed`. É o de **menor atrito** (login simples, sem MFA/captcha explícito), ideal para validar a estrutura de Portal Map/Skill sem acionar portal real nem exigir HITL.

## 2. Como o Portal Map v1 foi definido
`lib/attendance/portal-maps.ts` → `allianznet_corretor_login_map_v1` (status `draft`): páginas `landing_or_login`, `login_form` (com `field_label_candidates` usuário/cpf/susep/codigo + botões), `post_login_home_mock`, `session_expired_mock`, `challenge_detected_mock`; jornada `login`; `challenge_signals` (captcha/otp/2fa/certificado/sessão expirada/...); `outputs` (`login_form_detected`/`auth_required`/`post_login_home_detected`/`session_expired_detected`/`challenge_required`); `drift_signals`. **Sem segredo, sem acesso real.**

## 3. Como a Portal Skill v1 funciona
`lib/attendance/portal-skills.ts` → `allianznet_corretor_login_check_v1` (`skill_key=login_check`, journey `login`, `promotion_status=draft`): objetivo = validar em dry-run que a jornada de login é mapeável **sem login real**. `required_inputs`, `allowed_actions` (observe/detect/extract/challenge mock + trace), `forbidden_actions` (inserir credencial real, submeter login, bypass CAPTCHA/2FA, acessar URL real, download/upload, guardar storageState/cookie, expor credencial), `steps` (7), `expected_outputs`, `guardrails`.

## 4. Como o Skill Runner usa o Browser Relay
`lib/attendance/portal-skill-runner.ts` — **injeção de dependência** (recebe `adapter` + `startBrowserRelaySandbox` + `applyBrowserRelaySandboxStep`), mantendo-se self-contained. `runPortalSkillDryRun`: aplica gates (map/account/credential/session) e, se ok, abre relay sandbox e roda `observe → extract → (challenge? | complete)`. Estados: `planned/running_sandbox/waiting_human/sandbox_passed/sandbox_failed/cancelled`. `applyPortalSkillStep` bloqueia ações proibidas (registra `forbidden_action_blocked`, não executa).

## 5. Quais outputs são extraídos
Dry-run feliz: `login_form_detected`, `auth_required` (observe) → `post_login_home_detected` (complete mock). Caminho de challenge: `challenge_required` + `waiting_human`. Tudo mock — nenhum dado real de portal.

## 6. Como eval/promotion funciona
`evaluatePortalSkillRun`/`buildPortalSkillEval` → `{ passed, score, required_outputs_found, forbidden_actions_detected, challenge_detected, trace_available, replay_available, safe_to_promote_to_sandbox_validated, real_action_allowed:false }`. Promoção só quando: dry-run `passed` + todos `expected_outputs` presentes + sem forbidden + trace+replay + sem challenge não resolvido + sem PII. **Mesmo assim, o máximo é `sandbox_validated` — nunca `approved_future`** neste estágio.

## 7. Por que ainda não acessa URL real
Adapters `can*=false`; runner usa só o relay sandbox (mock); nenhuma URL é aberta; `forbidden_actions` proíbem login/submit/bypass/URL real; bodies com segredo cru → **400**; trace/replay sanitizados (OTP/dígitos mascarados, `has_pii:false`); `real_action_allowed=false` em tudo.

## 8. Arquivos criados/alterados
- `lib/attendance/portal-maps.ts` (**novo**) · `lib/attendance/portal-skills.ts` (**novo**) · `lib/attendance/portal-skill-runner.ts` (**novo**).
- `lib/attendance/browser-relay-runtime.ts` + `browser-relay-contracts.ts` — classificador de challenge insensível a acento.
- `lib/attendance/browser-relay-adapters.ts` — `evaluateRelayEligibility` (gate nomeado).
- `app/api/admin/portal-browser/relay/start/route.ts` — usa o gate.
- `lib/attendance/portal-admin-context.ts` — `getSkillRun`/`saveSkillRun`.
- Rotas (**novas**): `skills`, `skills/dry-run`, `skills/runs/[runId]`, `skills/runs/[runId]/trace`, `skills/runs/[runId]/replay`.
- `app/admin/portal-browser/page.tsx` — seção "Portal Skills (dry-run)".
- `scripts/attendance-portal-skill-dryrun.test.mjs` (**novo**, 39) + `package.json`.
- `docs/canon/design/2026-06-claude-design/43P3-...md` (este).

## 9. Testes que rodei (offline)
- `node scripts/attendance-portal-skill-dryrun.test.mjs` → **39/39**: map/skill v1 válidos; gates (no_map/create_portal_account/credential_required/expired→waiting_human); dry-run `sandbox_passed` com 3 outputs; eval passed/score 1/safe_to_promote; challenge → waiting_human + não promove + OTP mascarado; forbidden bloqueado; trace/replay sem PII; providers stagehand/skyvern_lab mock; `real_action_allowed=false`.
- Regressão: browser-relay **47**, intake **45**, canonical **20**, admin **34**, contracts **56**, provider **63**, outbox **42**, execution **31** — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 10. Reteste (console admin, logado)
```js
// requer a conta tenant saudável do portal allianz__allianznet_corretor_portal_do_corretor (criada no teste 43P2)
const dr = await (await fetch('/api/admin/portal-browser/skills/dry-run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ portal_id:'allianz__allianznet_corretor_portal_do_corretor', skill_key:'login_check', provider:'browserbase' })})).json();
console.log(dr.run.status, dr.run.outputs, dr.eval.passed, dr.eval.safe_to_promote_to_sandbox_validated, dr.real_action_allowed);
const ch = await (await fetch('/api/admin/portal-browser/skills/dry-run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ portal_id:'allianz__allianznet_corretor_portal_do_corretor', skill_key:'login_check', provider:'browserbase', inject_challenge:'codigo 123456' })})).json();
console.log(ch.run.status, JSON.stringify(ch.run).includes('123456')); // waiting_human, false
```
**Esperado:** dry-run `sandbox_passed` com outputs e `eval.passed=true`; com `inject_challenge` → `waiting_human` e OTP mascarado; `real_action_allowed=false`.

## 11. Critério de pronto
| Critério | Status |
|---|---|
| Portal Map v1 existe | ✅ |
| Portal Skill v1 existe | ✅ |
| dry-run da skill funciona | ✅ |
| trace/replay/eval existem | ✅ |
| skill no máximo `sandbox_validated` | ✅ (nunca approved_future) |
| nenhum portal real | ✅ |
| testes verdes | ✅ 39 + regressão |

## 12. Próximos passos + recomendações 100/100
- **SEC-001 — hardening ANTES de qualquer real (bloqueante para 43P4):** RLS em `tenant_connections`; auditoria de segredos (garantir que vault_ref/storage_ref nunca expõem valor); logs sem PII; kill switches por portal/provider; flag global `PORTAL_REAL_ACTION_ENABLED=false` cruzada com `evaluatePortalPromotionGate` (43P0); rate-limit por conta/portal.
- **43P4 — Login setup real controlado** (só após SEC-001): captura de SessionRef real via login assistido pelo corretor (HITL), com `canOpenRealBrowser` ainda gated por flag + approval; nada automático.
- **43P5 — primeira ação real com HITL**: uma jornada de leitura (ex.: consulta de status/apólice) antes de qualquer escrita; aprovação humana por execução; trace/replay/eval + rollback.
- **Catalog Review Queue** (paralelo): promover os 78 `needs_review` a `sandbox_ready` por revisão humana, ampliando o pool de skills dry-run.
- **Mais skills dry-run**: `policy_query`/`billing_query`/`status_query` reaproveitando o mesmo runner/eval — a estrutura já é genérica.
