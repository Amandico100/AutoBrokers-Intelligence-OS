# 43P1 — Portal Registry, CredentialRef, SessionRef & Admin UI Foundation Report

> **Status:** concluído · testes offline **34 verdes** (portal-admin-registry) + regressão verde (portal-contracts 56 / provider 63 / alignment 32 / outbox 42 / execution 31) · `typecheck` EXIT=0 · build verde · **sem schema novo** (usa `tenant_connections.connection_config`) · **NENHUM browser/login/portal real** · `real_action_allowed=false` em toda resposta · refs opacas, segredo cru rejeitado (400).
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que foi criado
A camada administrativa/operacional do Portal Browser, ainda 100% mock/dry-run:
- **Portal Registry** — cadastro de `PortalDefinitionRecord` (label, owner, base_url, jornadas, auth_methods, `challenge_profile`, `browser_strategy`, status).
- **Portal Accounts** — `PortalAccountRecord` por corretora (tenant-private), com `credential_ref`/`session_ref` opcionais e `status` derivado.
- **CredentialRef/SessionRef** — `CredentialRefRecord`/`SessionRefRecord` como **referências opacas** (`vault_ref_masked`/`storage_ref_masked`); nunca senha/token/cookie/storageState.
- **Health-check mock** — reavalia a sessão só por metadados (status + expiração).
- **Resolve** — `resolvePortalForJourney` por `portal_id` ou `owner_key`+`journey`, pronto para o Action Engine (43P2/43P3).
- **Admin UI** `/admin/portal-browser` + 8 rotas admin.
- **Intake audit** `scanPortalIntakeSources` (resultado: `intake_sources_not_available` — ver §7).

## 2. Arquivos criados/alterados
- `lib/attendance/portal-admin-sanitizers.ts` (**novo**, puro) — records + `validatePortalDefinitionInput`, `buildPortalDefinitionRecord`, `buildPortalAccountRecord`, `buildChallengeProfile`, `buildCredentialRefRecord`/`buildSessionRefRecord` (lançam em segredo cru), `deriveAccountStatus`, `mockHealthCheck`, `sanitizePortalAccountRecord`, `resolvePortalForJourney`, `scanPortalIntakeSources`, `findRequestSecrets`.
- `lib/attendance/portal-admin-context.ts` (**novo**) — `getPortalAdminContext` (auth admin/user) + store em `tenant_connections.connection_config` (`portal_definitions[]`/`portal_accounts[]`), defensivo (`vault_not_available`).
- Rotas (**novas**): `app/api/admin/portal-browser/portals/{route,[portalId]}`, `.../accounts/{route,[portalAccountId]}`, `.../accounts/[portalAccountId]/{credential-ref,session-ref,health-check}`, `.../resolve`.
- `app/admin/portal-browser/page.tsx` (**nova** UI).
- `scripts/attendance-portal-admin-registry.test.mjs` (**novo**, 34) + `package.json` (`test:portal-admin-registry`).
- `docs/canon/design/2026-06-claude-design/43P1-...md` (este).

## 3. Onde persiste
`tenant_connections.connection_config` de um connection determinístico por company (`autobrokers_portal_browser`): `portal_definitions[]` (registry) e `portal_accounts[]` (contas + refs). **Sem schema novo.** Find-or-create reusa o `connector_template` `whatsapp_zapi` para satisfazer a FK; se o Vault não estiver migrado, as rotas degradam com `vault_not_available` (sem crash). **Decisão MVP:** o registry de portais é conceitualmente **global**, mas no 43P1 ficou **tenant-scoped** para evitar mutar a tabela global `connector_templates`; **TODO** documentado para promover a global quando houver um store global seguro.

## 4. Como o admin usa
Tela `/admin/portal-browser`: cria portal (label/owner/base_url https/jornadas/auth_methods), lista portais, cria conta de portal por corretora, e por conta dispara **+ CredentialRef (mock)**, **+ SessionRef (mock)** e **Health check (mock)**. Banner fixo: "Nenhum portal real é acessado nesta fase". APIs exigem sessão admin/usuário com company e sanitizam toda resposta.

## 5. Como CredentialRef funciona
`buildCredentialRefRecord({ vault_ref })` cria a ref a partir de uma **referência opaca ao Vault**; **lança** se o body contiver `password/token/secret/...`. A resposta só expõe `vault_ref_masked` (`abc…456`) + status. A rota `credential-ref` rejeita segredo cru com **400** antes de tocar o store.

## 6. Como SessionRef funciona
`buildSessionRefRecord({ storage_ref, provider, status, expires_at })` referencia o `storageState` criptografado (no Vault), **nunca** cookies/headers; **lança** se receber `cookie`/`storage_state`/`storagestate`. Resposta expõe só `storage_ref_masked`, provider, status, expiração. Isso segue a orientação oficial do Playwright (o `storageState` é sensível e não deve sair do cofre/repo).

## 7. Resultado da auditoria do intake
**`intake_sources_not_available`.** Os diretórios `AUTOBROKERS_RESULTA_INTAKE/`, `AUTOBROKERS_AGENT_OS/` e `AUTOFLEET/` **não estão no workspace** (confirmado por `ls`). Não inventei portais. `scanPortalIntakeSources([])` retorna `available:false`. **Checklist para o Founder sincronizar depois** (necessário para semear portais reais com confiança):
- `AUTOBROKERS_RESULTA_INTAKE/PESQUISA DOS PORTAIS`
- `AUTOBROKERS_RESULTA_INTAKE/conversa com allianz residencial`
- `AUTOBROKERS_RESULTA_INTAKE/conversas com reguladoras`
- `AUTOBROKERS_RESULTA_INTAKE/conversas seguradoras - assistência outros ramos`
- `AUTOFLEET/conversas com seguradoras - auto`
- `AUTOBROKERS_AGENT_OS/17_INTELIGENCIA_OPERACIONAL/PORTAL_BROWSER_ROUTINES_MASTER_PLAN.md` e os demais de `03_EXECUTION_PLANE/06_SKILLS/09_CONTRATOS`.
Quando sincronizados, `scanPortalIntakeSources` extrai só metadados seguros (nome, URL pública, jornadas, sinais de challenge), sem PII/credencial.

## 8. Seeds
Como o intake não está disponível, **não criei seed em produção** (evita inventar dados de portal). O exemplo `demo_insurer_portal` existe apenas conceitualmente nos testes. O admin pode criar manualmente o portal `allianz` (owner_key `allianz`, jornada `residential_assistance`, status `draft`) — o resolve já o reconhece.

## 9. Portais candidatos
Nenhum candidato automático (intake ausente). **Recomendado para o 43P3** (dry-run): **Allianz Residencial / assistência eletricista** (corredor MVP), criando a `PortalDefinition` no admin e validando o resolve antes do Browser Relay. Decisão final depende do `PESQUISA DOS PORTAIS`.

## 10. Por que ainda não acessa portal real
Nenhuma rota abre browser; nenhuma credencial/sessão real é usada; `mockHealthCheck` só lê metadados; `real_action_allowed=false` em toda resposta; segredo cru → 400. O acesso real só virá no 43P4/43P5 atrás de login setup real + SessionRef real + HITL + kill switch (gates já modelados no 43P0 `evaluatePortalPromotionGate`).

## 11. Integração futura com o Action Engine
`resolvePortalForJourney(definitions, accounts, ctx)` devolve `{ portal_available, portal_id, portal_account_status, credential_status, session_status, challenge_required, next_step, real_action_allowed:false }` — pronto para o 43P2/43P3 ligarem o Portal Action Candidate (43P0) ao Browser Relay sandbox, sem mudar o engine.

## 12. Testes que rodei (offline)
- `node scripts/attendance-portal-admin-registry.test.mjs` → **34/34**: validação de portal (https/HITL/segredo); challenge_profile; account + status derivado; refs opacas (mascaram, **lançam** em password/cookie/storageState); health-check mock (credential_pending/session_pending/healthy/expired/challenge); resolve (ready/sem conta/sem portal); sanitização sem PII; intake audit vazio não quebra.
- Regressão: portal-contracts **56**, provider **63**, alignment **32**, outbox **42**, execution **31** — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 13. Reteste (console admin, logado)
```js
const P = await (await fetch('/api/admin/portal-browser/portals', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ label:'Allianz Portal', owner_key:'allianz', base_url:'https://portal.allianz.com.br', supported_journeys:['residential_assistance'], auth_methods:['password','mfa','captcha'] })})).json();
const A = await (await fetch('/api/admin/portal-browser/accounts', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ portal_id:P.portal.portal_id, label:'Conta Resulta' })})).json();
await fetch(`/api/admin/portal-browser/accounts/${A.account.portal_account_id}/credential-ref`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ vault_ref:'vault://mock-1' })});
await fetch(`/api/admin/portal-browser/accounts/${A.account.portal_account_id}/session-ref`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ storage_ref:'store://mock-1', provider:'browserbase', status:'healthy', expires_at:new Date(Date.now()+6048e5).toISOString() })});
const H = await (await fetch(`/api/admin/portal-browser/accounts/${A.account.portal_account_id}/health-check`, { method:'POST' })).json();
const R = await (await fetch('/api/admin/portal-browser/resolve?owner_key=allianz&journey=residential_assistance')).json();
console.log(H.health.status, R.resolution.next_step, R.resolution.real_action_allowed);
// tentar segredo cru → deve dar 400:
const bad = await fetch(`/api/admin/portal-browser/accounts/${A.account.portal_account_id}/credential-ref`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ password:'123' })});
console.log('segredo cru status:', bad.status); // 400
```
**Esperado:** health `healthy`; resolve `ready_for_dry_run_43p3` com `real_action_allowed:false`; segredo cru → **400**; nenhuma ref crua nas respostas.

## 14. Critério de pronto
| Critério | Status |
|---|---|
| admin cadastra portal | ✅ |
| admin cadastra conta de portal | ✅ |
| CredentialRef/SessionRef como refs opacas | ✅ |
| health-check mock funciona | ✅ |
| segredo cru rejeitado | ✅ (400 + builders lançam) |
| portal resolve funciona | ✅ |
| UI mínima existe | ✅ `/admin/portal-browser` |
| nenhum browser real | ✅ |
| testes verdes | ✅ 34/34 + regressão |

## 15. Próximos passos
- **43P2 — Browser Relay Sandbox Harness**: adapters `browserbase`/`local_playwright`/`skyvern_lab` (mock), relay session sandbox, trace/replay, health-check controlado — **sem ação real** (reusa `browser-relay-contracts.ts` do 43P0).
- **43P3 — First Portal Skill dry-run**: Portal Map v1 + primeira skill (Allianz residencial) em dry-run, com trace/replay/evals.
- **Founder**: sincronizar as fontes de intake (§7) para semear portais reais com confiança.
