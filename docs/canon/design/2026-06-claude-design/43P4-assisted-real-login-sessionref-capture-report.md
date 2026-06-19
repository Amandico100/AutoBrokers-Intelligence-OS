# 43P4 — Assisted Real Login Setup & Secure SessionRef Capture Report

> **Status:** concluído (estrutura controlada/gated) · testes offline **33 verdes** (portal-login-setup) + regressão security/portal/ação verde · `typecheck` EXIT=0 · build verde · **sem schema novo** · **NENHUM browser/login/portal real aberto** · `real_browser_opened=false`, `business_action_allowed=false`, `real_action_allowed=false`.
> **Data:** 2026-06-19 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Análise dos seus testes/SQL anteriores (tudo certo)
- **Código SEC-001/SEC-001A:** o teste do console confirmou — `evaluate`/`relay/start` voltaram a **200** (bug 403 resolvido), gates todos `false`, kill switch `true`. ✅
- **SQL:** você só viu `rls_enabled=true, policy_count=2` porque o diagnostics tinha **8 queries** e o Supabase mostra só a **última** (`tenant_connections` → 2 policies, correto). A migration rodou ("Success. No rows returned" = DDL/DO ok). **Corrigi o diagnostics** para retornar **uma única tabela** (UNION ALL) — agora um Run mostra memória, buckets, SECURITY DEFINER, PK, etc. de uma vez. **Importante:** RLS-on-sem-policy = **deny-all = seguro** (não é vazamento); o risco seria policy permissiva, que não existe.

## 1. O que o 43P4 entregou (estrutura, sem cruzar para o real)
A estrutura de **login assistido por humano** com **captura segura de SessionRef**, toda **gated**. Como nenhum adapter de browser real está homologado (todos `canOpenRealBrowser=false`) e as flags estão off, **nada abre de verdade** — exatamente o padrão sandbox-first dos batches anteriores. Quando as flags + approval + adapter real existirem (43P5/homologação), a mesma máquina de estados conduz o login real.

## 2. Decisão de segurança importante
O 43P4 **não** faz login automático nem abre browser real. A abertura é **simulada (sandbox)**: `applyLoginSetupStep('open_browser')` registra `browser_opened_sandbox` e segue para `waiting_human_login`, sem rede. O login real só ocorrerá com: `GLOBAL_KILL_SWITCH=false` + `PORTAL_REAL_ACTION_ENABLED` + `PORTAL_LOGIN_REAL_ENABLED` + `PORTAL_SESSION_CAPTURE_ENABLED` + **approval humano** + **adapter de browser real homologado** (inexistente neste batch). `business_action_allowed` é **sempre false** — login setup ≠ ação de negócio.

## 3. Máquina de estados
`draft → awaiting_approval → ready_to_open_browser → browser_opened → waiting_human_login → (challenge_required) → session_captured → session_verified` (+ `failed`/`cancelled`). Gate (`evaluateLoginSetupGate`) falha fechado: flags off / kill switch on / sem conta / sem credencial / portal não saudável / sem approval → bloqueia. Sem approval → `awaiting_approval`; `approveLoginSetup` → `ready_to_open_browser`.

## 4. Captura segura de SessionRef
`captureSessionRef` aceita **somente uma `storage_ref` opaca** (referência ao storageState criptografado no Vault) e **lança** se receber `cookie`/`storage_state`/`headers`/`token`/`otp`/etc. Retorna `storage_ref_masked` (`abc…456`), provider, status, expiração. `verifyCapturedSession` decide usabilidade **só por metadados**. A SessionRef capturada é anexada (mascarada) à conta de portal para continuidade — **nunca** cookies/storageState crus no frontend/JSON.

## 5. CAPTCHA / 2FA / OTP
`applyLoginSetupStep('challenge')` classifica (captcha/otp/mfa_app/certificate/account_locked), sempre `requires_human:true, bypass_allowed:false`, status `challenge_required`, `next_step=human_challenge_required`. OTP/números **mascarados** (acento-insensível, ex.: "código 123456"). **Nunca** salva OTP; **nunca** bypass.

## 6. Arquivos criados/alterados
- `lib/attendance/portal-session-capture.ts` (**novo**, puro) · `lib/attendance/portal-login-setup.ts` (**novo**, puro).
- `lib/attendance/portal-admin-context.ts` — `getLoginSetup`/`saveLoginSetup`.
- Rotas (**novas**): `login-setup/{start,challenge,complete}`, `login-setup/[setupId]` (GET), `login-setup/[setupId]/cancel`.
- `app/admin/portal-browser/page.tsx` — botão "Iniciar login assistido" + painel de status (gated).
- `docs/canon/design/2026-06-claude-design/SEC-001-supabase-security-diagnostics.sql` — **consolidado em resultado único**.
- `scripts/attendance-portal-login-setup.test.mjs` (**novo**, 33) + `package.json`.
- `docs/canon/design/2026-06-claude-design/43P4-...md` (este).

## 7. Segurança / gates
- Toda rota POST rejeita body com segredo cru → **400** (`findRequestSecrets`/`findCaptureSecrets`).
- `complete` exige `storage_ref` opaco; cookie/storageState cru → 400; nunca retorna segredo.
- `production_gate` (SEC-001) anexado no `start` (sempre `allowed=false` hoje).
- `real_browser_opened=false`, `business_action_allowed=false`, `real_action_allowed=false` em todas as respostas.
- `getPortalAdminContext` robusto (SEC-001A) → rotas POST não dão mais 403 indevido.

## 8. Testes que rodei (offline)
- `node scripts/attendance-portal-login-setup.test.mjs` → **33/33**: gates (flags/kill/approval/credential/conta); start states; approve; challenge (OTP mascarado, HITL, no bypass); captura (rejeita cookie/storageState, mascara ref, verify); complete (open sandbox → human_login → capture → verify = session_verified, sem segredo, terminal guard); cancel.
- Regressão: security **31**, skill-factory **46**, skill-dryrun **39**, relay **47**, outbox **42**, execution **31** — verdes.
- `npx tsc --noEmit` EXIT=0 (corrigi `let session: any`) · `npm run build` verde.

## 9. Reteste (console admin, logado) — fluxo gated
```js
// Sem flags reais, o start fica em draft (enable_flags) ou awaiting_approval; nada abre.
const s = await (await fetch('/api/admin/portal-browser/login-setup/start', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ portal_id:'allianz__allianznet_corretor_portal_do_corretor', portal_account_id:'<conta saudável>', approval_exists:false })})).json();
console.log(s.login_setup.status, s.login_setup.next_step, s.production_gate.allowed); // draft/awaiting_approval, false
// Segredo cru → 400:
const bad = await fetch('/api/admin/portal-browser/login-setup/complete', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ setup_id:s.login_setup.setup_id, storageState:{cookies:[]} })});
console.log('segredo cru:', bad.status); // 400
```
**Esperado:** status gated (sem abrir nada); `production_gate.allowed=false`; segredo cru → 400; `real_browser_opened` nunca true.

## 10. Critério de pronto
| Critério | Status |
|---|---|
| login setup gated (flags+approval+kill switch) | ✅ |
| sem login automático / sem browser real | ✅ |
| SessionRef opaca, sem cookie/storageState cru | ✅ |
| CAPTCHA/2FA → human, sem bypass | ✅ |
| nenhuma ação de negócio | ✅ |
| segredo cru → 400 | ✅ |
| 5 rotas + UI | ✅ |
| testes verdes + tsc + build | ✅ |
| diagnostics SQL consolidado | ✅ |

## 11. Próximos passos
- **Aplicar/verificar o SQL no Supabase** com o diagnostics consolidado (um Run) → confirmar policies de memória / PK / buckets / SECURITY DEFINER; tratar follow-ups manuais.
- **43P4-real / homologação de adapter de browser real (Browserbase):** credenciais no Vault, `tenant_connection`, e ligar o `canOpenRealBrowser` real atrás de flags + approval + kill switch. Só então um login real assistido de verdade.
- **43P5 — primeira ação real de leitura com HITL** (consulta status/apólice), depois E2E piloto.
- Antes de qualquer real: confirmar o teste live (start gated 200, segredo→400) e o verify do banco.
