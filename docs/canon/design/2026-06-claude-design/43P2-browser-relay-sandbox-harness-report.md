# 43P2 — Browser Relay Sandbox Harness, Trace/Replay & Provider Mock Adapters Report

> **Status:** concluído · testes offline **47 verdes** (browser-relay-sandbox) + regressão portal/ação verde · `typecheck` EXIT=0 · build verde · **sem schema novo** · **NENHUM browser/URL/credencial real** · `canOpenRealBrowser/canAccessRealUrl/canUseRealCredential=false` · `real_action_allowed=false`.
> **Data:** 2026-06-18 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Teste live 43P1.2
Passou: catálogo global 189/18, Allianz 16 com `official_sources`+`confidence`, resolve Porto→`global`/`create_portal_account`, Allianz→`tenant_draft`/`ready_for_dry_run`, sandbox_ready 111, tudo `connector_template=portal_browser`/`real_action_allowed=false`.

## 1. O que foi criado
A camada de **execução sandbox de portal**, sem abrir browser:
- **Adapters mock** (`browser-relay-adapters.ts`): `browserbase`, `local_playwright`, `stagehand`, `skyvern_lab`, `mock` — todos `mode:'mock'`, `canOpenRealBrowser/canAccessRealUrl/canUseRealCredential=false`, com `createSession/observe/act/extract/close` retornando eventos **mock** (zero rede).
- **Runtime sandbox** (`browser-relay-runtime.ts`): `startBrowserRelaySandbox`, `applyBrowserRelaySandboxStep`, `buildRelayTrace`, `buildRelayReplay`, `sanitizeRelayRuntimeOutput`, `findRelaySecrets`. Estados: `draft→ready→running_sandbox→observing/acting/extracting→challenge_required/waiting_human→completed_sandbox/failed_sandbox/cancelled`.
- **6 rotas** `relay/{start,step,[relayId],[relayId]/cancel,[relayId]/trace,[relayId]/replay}`.
- **UI** "Relay Sandbox (mock)" na página Conectores → Portais.

## 2. Arquitetura — injeção de dependência (sem motor paralelo)
O runtime **não importa** os adapters em runtime: recebe o `BrowserRelayProviderAdapter` por **parâmetro** (DI). Isso mantém cada módulo self-contained (exigência do loader Node `.ts`/`.mjs`) e deixa explícito que Browserbase/Playwright/Stagehand/Skyvern são **adapters conectáveis**, não o cérebro. A rota resolve o adapter (`getBrowserRelayAdapter(provider)`) e o injeta. Reusa o resolve canônico (43P1.1/43P1.2) e o Global Catalog (43P1.2).

## 3. Quais adapters existem / como entram
| provider | mode | papel |
|---|---|---|
| `browserbase` | mock | cloud browser recomendado (sandbox/real futuro) |
| `local_playwright` | mock | dev/sandbox; storageState/trace via SessionRef opaco no futuro |
| `stagehand` | mock | camada agentic `observe/act/extract` sobre Playwright/Browserbase |
| `skyvern_lab` | mock | laboratório/fallback para fluxos difíceis |
| `mock` | mock | simulação neutra |
No 43P2 todos são **mock**; o `real_future` virá nos 43P4/43P5 atrás de SEC-001 + flags + Vault + HITL.

## 4. Por que nada acessa portal real
Os 3 flags `can*` são `false` (tipo literal) em todos os adapters; `mockSend`-style: cada método retorna `{ mock:true, real_action_allowed:false }` sem rede; o runtime nunca recebe URL real para abrir; `external_action_sent=false`/`real_action_allowed=false` em toda sessão/resposta; bodies com segredo cru → **400**.

## 5. Como trace/replay funcionam
`buildRelayTrace` → `{ relay_id, portal_id, journey, provider, steps[], observed/actions/extracted counts, challenges[], outcome, has_pii:false, real_action_allowed:false }`. `buildRelayReplay` → timeline numerada dos eventos (lógica), `has_pii:false`. Ambos passam por mascaramento (dígitos longos/OTP omitidos). `sanitizeRelayRuntimeOutput` remove recursivamente qualquer chave de segredo antes de responder no GET.

## 6. Como o challenge handling funciona
`applyBrowserRelaySandboxStep(..., {type:'challenge'})` classifica o sinal (`captcha/otp/mfa_app/certificate/account_locked/session_expired/unknown`) e sempre marca `requires_human:true, bypass_allowed:false`, status `challenge_required`, `next_step=human_challenge_required`. OTP/números são mascarados no hint e nos eventos. Sessão `expired`/`challenge_required` no start já nasce em `challenge_required`. **Nunca bypass.**

## 7. Como o SessionRef é usado (só metadata)
O start recebe apenas `session_status` e `session_ref_masked` (vindos da conta tenant) — **nunca** o `storageState`/cookies. O adapter `createSession` recebe só a ref mascarada. Nenhum conteúdo de sessão real é lido/aberto.

## 8. Integração com Global Catalog
`relay/start` resolve via `resolvePortalCanonical(getGlobalPortalCatalogSeed(), tenantDefs, accounts, ctx)`: sem portal → `failed_sandbox`; portal mas sem conta → `draft`/`create_portal_account` (a menos que `allow_demo_without_account=true`, default false); conta `expired`/`challenge` → `challenge_required`; conta saudável → `running_sandbox`.

## 9. Arquivos criados/alterados
- `lib/attendance/browser-relay-adapters.ts` (**novo**) · `lib/attendance/browser-relay-runtime.ts` (**novo**).
- `lib/attendance/portal-admin-context.ts` — `getRelaySession`/`saveRelaySession` (em `connection_config.relay_sessions[]`, últimas 25).
- Rotas (**novas**): `relay/start`, `relay/step`, `relay/[relayId]`, `relay/[relayId]/cancel`, `relay/[relayId]/trace`, `relay/[relayId]/replay`.
- `app/admin/portal-browser/page.tsx` — painel "Relay Sandbox (mock)".
- `scripts/attendance-browser-relay-sandbox.test.mjs` (**novo**, 47) + `package.json`.
- `docs/canon/design/2026-06-claude-design/43P2-...md` (este).

## 10. Testes que rodei (offline)
- `node scripts/attendance-browser-relay-sandbox.test.mjs` → **47/47**: adapters (5, can*=false); start gating (sem portal/sem conta/demo/expired/healthy); observe/act/extract mock + terminal guard; challenge captcha/otp (HITL, OTP mascarado); cancel; trace/replay sem PII; sanitização/`findRelaySecrets`; skyvern_lab mock sem API.
- Regressão: intake-importer **45**, canonical-store **20**, admin-registry **34**, contracts **56**, provider **63**, outbox **42**, execution **31** — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 11. Reteste (console admin, logado)
```js
const s = await (await fetch('/api/admin/portal-browser/relay/start', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ owner_key:'porto', journey:'login', provider:'browserbase' })})).json();
console.log(s.relay.status, s.relay.next_step, s.adapter.canOpenRealBrowser); // sem conta → draft/create_portal_account, false
// com a conta Allianz de teste (tenant_draft saudável):
const a = await (await fetch('/api/admin/portal-browser/relay/start', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ owner_key:'allianz', journey:'login', provider:'browserbase' })})).json();
const id = a.relay.relay_id;
await fetch('/api/admin/portal-browser/relay/step', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ relay_id:id, type:'observe' })});
const ch = await (await fetch('/api/admin/portal-browser/relay/step', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ relay_id:id, type:'challenge', challenge_signal:'codigo 123456' })})).json();
console.log(ch.relay.status, JSON.stringify(ch.relay).includes('123456')); // challenge_required, false (mascarado)
const t = await (await fetch(`/api/admin/portal-browser/relay/${id}/trace`, { method:'POST' })).json();
console.log(t.trace.has_pii, t.trace.real_action_allowed); // false, false
```
**Esperado:** relay sandbox conduz observe/act/extract mock; challenge vira HITL com OTP mascarado; trace sem PII; nenhum browser real; `real_action_allowed=false`.

## 12. Critério de pronto
| Critério | Status |
|---|---|
| Browser Relay Sandbox existe | ✅ |
| adapters mock existem | ✅ (5, can*=false) |
| start/step/trace/replay funcionam | ✅ (6 rotas) |
| challenge vira HITL | ✅ (sem bypass, OTP mascarado) |
| trace/replay sanitizados | ✅ (has_pii:false) |
| UI/API mínima | ✅ |
| nenhum browser real | ✅ |
| testes verdes | ✅ 47 + regressão |

## 13. Como escolher o primeiro portal para o 43P3 + recomendações 100/100
- **Primeiro alvo de dry-run (43P3):** um portal `sandbox_ready`, `audience=corretor`, `auth_type=login_password` **sem MFA/captcha** (`challenge_profile.requires_hitl=false`), jornada `login`/`policy_query`/`billing_query`/`status`, `confidence=confirmed`. Pelo catálogo, `allianz__allianznet_corretor_portal_do_corretor` é um bom candidato (corretor, login, password, sem HITL). Evitar superfícies `segurado`/`desenvolvedor` e as com MFA (ex.: tela de código de ativação).
- **SEC-001 antes do 43P4** (qualquer acesso real): RLS em `tenant_connections`, auditoria de segredos, logs sem PII, kill switches por portal/provider, e um gate global `PORTAL_REAL_ACTION_ENABLED` (default false) cruzado com `evaluatePortalPromotionGate` (43P0).
- **Filtro de elegibilidade no `relay/start`** (próximo refinamento): recusar provider `real_future`/canais não homologados explicitamente (hoje já é mock, mas vale um gate nomeado para o 43P4).
- **Curadoria dos 78 `needs_review`** (batch "Portal Catalog Review Queue") para promover a `sandbox_ready` por revisão humana — aumenta o pool elegível ao dry-run.

## 14. Próximos passos
- **43P3 — First Portal Skill dry-run + Portal Map v1**: escolher o portal acima, montar Portal Map v1 (páginas/journeys/challenges) e uma Portal Skill determinística que roda observe→act→extract em dry-run com trace/replay/evals, sobre o Relay Sandbox.
- **SEC-001** antes de 43P4/43P5.
