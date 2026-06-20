# 43P-FINAL-1 — Production-Ready Portal Execution Layer, Secure Session Lifecycle & Read-Only Skill

> **Portal Browser — Batch 1 de 2 (final).** Camada técnica completa para o canary real. **Nada real foi aberto/ligado.** Gates fechados, `can_open_real_browser=false`, sem segredos.
> **Data:** 2026-06-19 · **Modelo:** Claude Opus 4.8 · **Branch:** main · base: `3c2fa29`

## APTO PARA BATCH 2: SIM
Falta apenas operação/config (não código estrutural): configurar Browserbase Free + envs no EasyPanel, `npm install playwright-core`, escolher o tenant piloto, criar a portal account, aprovar o canary, abrir live view, humano logar, capturar SessionRef, verificar e rodar a leitura read-only.

## 0. Correção do atrito do teste (selected_company: null)
O teste do GPT mostrou `companies_found: Array(2)` (✅ a coluna `company_name` já corrigida funcionou) mas `selected_company: null` e accounts **403** — porque **nenhuma corretora estava selecionada** (o `document.cookie` client-side não persistiu/ não foi escolhido). **Corrigido**: a seleção agora é **server-side** via `POST /api/admin/portal-browser/select-company` (cookie **HttpOnly** `aj_company`, validado: só master, company precisa existir). A UI usa essa rota. Assim o escopo persiste de forma robusta e o accounts passa a **200**.

## 1. Referências oficiais Browserbase (consultadas)
- `docs.browserbase.com/reference/api/create-a-session` — `POST /v1/sessions`, `X-BB-API-Key`, `{projectId}` → `id/connectUrl/signingKey/status/region/expiresAt`.
- `connectUrl` = WebSocket CDP para Playwright `chromium.connectOverCDP(connectUrl)` — **é segredo** (fica server-side).
- Live view/inspector: o caminho seguro é o operador autorizado acompanhar pelo **console oficial Browserbase**; o AutoBrokers **não** recebe `connectUrl`/`liveUrl`. (Decisão de segurança documentada na Parte B3.)
- Encerramento: `POST /v1/sessions/{id}` `{status:'REQUEST_RELEASE'}`.

## 2. O que foi implementado (estrutural, gated, testado)
### Módulos puros (self-contained, testáveis offline)
| Módulo | Função |
|---|---|
| `lib/attendance/portal-tenant-canary-authorization.ts` | `evaluateTenantCanaryAuthorization` — autoriza canary por **company+portal_account+portal+journey+approval(expira)**; kill switch SEMPRE vence; flag global = freio; isolamento cross-tenant. |
| `lib/attendance/portal-session-vault.ts` | `PortalSessionVaultAdapter` + `persistSessionRefViaVault` (FALHA FECHADA `vault_unavailable`; nunca grava cookie em storage comum) + `findVaultRefSecrets`. |
| `lib/attendance/portal-read-only-skill.ts` | `session_login_verify` (read-only): `runSessionLoginVerify`, allowlist de host, `forbidden_actions`, `toSafePageLabel` (descarta PII/dígitos longos), `findSkillOutputSecrets`. |
| `lib/attendance/portal-real-execution-controller.ts` | Máquina de estados do canary (draft→…→session_verified/failed/aborted/expired/closed), DI de transports (browser/vault/skill), `sanitizeCanary`, `findCanarySecrets`. |

### Camada server-side (não testada por .mjs; usa os módulos acima)
| Arquivo | Função |
|---|---|
| `lib/attendance/portal-cdp-transport.ts` | `verifyViaCdp` — Playwright `connectOverCDP` **lazy/opcional** (fail-closed `playwright_not_available` até o Batch 2 instalar `playwright-core`); só OBSERVA (host/título/marcador/challenge); `connectUrl` nunca sai. |
| `app/api/admin/portal-browser/select-company` | Seleção de tenant (cookie HttpOnly; só master). |
| `app/api/admin/portal-browser/real-execution/approve` | Cria/revoga **approval** de canary (tenant-scoped, expira ≤1h). |
| `app/api/admin/portal-browser/real-execution/start` | Inicia canary **gated** (authorization + readiness + controller). Sem env/flags → falha fechado **sem rede**. |
| `app/api/admin/portal-browser/real-execution/status` | Lista canaries/approvals sanitizados. |
| `app/api/admin/portal-browser/real-execution/abort` | Aborta/encerra (fecha sessão best-effort). |
| `lib/attendance/portal-admin-context.ts` | Persistência `canary_approvals[]`/`canaries[]` em `connection_config` (sem schema novo). |
| `app/admin/portal-browser/page.tsx` | Seletor server-side + **checklist go/no-go** do canary + avisos de segurança. |

## 3. Ciclo de vida do canary (estados)
`draft → awaiting_approval → ready_for_canary → browser_opened → waiting_human_login → challenge_required ↔ waiting_human_login → session_capture_pending → session_captured → session_verified → (closed)` · saídas: `failed | aborted | expired`. Transições inválidas são bloqueadas (`invalid_transition`).

## 4. Segurança (garantida + testada)
- `openCanaryBrowser` **não chama rede** se `readiness.can_open_real_browser=false` (provado por spy).
- Vault ausente → captura **falha fechada** (`vault_unavailable`); cookies/storageState reais nunca entram na session nem no banco comum.
- `connectUrl/signingKey/cookies/storageState/token/authorization` nunca entram na `CanarySession` nem nas respostas (`findCanarySecrets`/sanitização nas rotas).
- CAPTCHA/2FA = `challenge_required` (humano resolve; OTP nunca persistido).
- Skill read-only: sem SessionRef/authorization/healthy → bloqueia; host fora da allowlist bloqueia; output sem PII/DOM/segredo.
- Autorização por tenant: approval expira, é por company+account; kill switch vence; cross-tenant negado.
- Isolamento multi-tenant: master seleciona; tenant travado na própria company.

## 5. Decisão sobre Playwright (Founder: não quebrar produção)
Para **não arriscar o build/deploy** atual, **não** adicionei `playwright-core` ao `package.json` neste batch. O `portal-cdp-transport.ts` faz `import('playwright-core')` **lazy/opcional** e **falha fechado** se ausente. **Batch 2** roda `npm install playwright-core` (não baixa browsers — é só o cliente CDP). Impacto: ativa o `connectOverCDP` real; nenhum efeito no bundle do app (server-only + `import()` dinâmico).

## 6. Migrations
**Nenhuma migration aplicada.** Tudo reusa `tenant_connections.connection_config` (arrays `canary_approvals[]`/`canaries[]`) e `companies/users_v2/sessão`. Não há passo manual de SQL para o Batch 2.

## 7. Tenant pilot identity (decisão do Founder p/ Batch 2)
No banco há **RAFAEL SEGUROS** e **AutoBrokers Global Knowledge** (não "Resulta"/"Autofleet"). **Não** criei/alterei company (sem hardcode). Antes do Batch 2 o Founder precisa:
1. Escolher **qual company existente** será o tenant piloto (ou criar Resulta/Autofleet pelo fluxo admin `/api/admin/companies`).
2. Criar a **portal account** AllianzNet **dessa company** (Portal Account e SessionRef são sempre de UMA company; nunca global entre corretoras).
3. Definir o usuário/credencial real (consentido) que fará o login humano.

## 8. Testes
- Novos: `portal-tenant-canary-authorization` **14**, `portal-session-vault` **9**, `portal-read-only-skill` **15**, `portal-real-execution-controller` **21** = **59**.
- Regressão: company-scope 19, browserbase-adapter 25, login-setup 33, relay 47, skill-factory 46, security 31, action-outbox 42.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## 9. Roteiro de teste live (simples) para o Founder
No `/admin/portal-browser` (logado como master), Ctrl+F5, escolha a corretora no seletor. Depois, **um** teste no Console:
```js
(async () => {
  const c = await (await fetch('/api/admin/portal-browser/companies')).json();
  const a = await fetch('/api/admin/portal-browser/accounts');
  const s = await (await fetch('/api/admin/portal-browser/real-execution/status')).json();
  console.log({ selected: c.current_company_id, accounts_http: a.status, canaries: (s.canaries||[]).length, real_action_allowed: s.real_action_allowed });
})();
```
**Esperado:** `selected` com UUID, `accounts_http: 200`, `real_action_allowed: false`. **Não pode** vir `403 No company associated` (depois de selecionar a corretora).

## 10. Implementado vs mock vs bloqueado
- **Implementado/real:** seleção de tenant server-side; authorization por tenant/approval; controller; vault adapter (fail-closed); skill read-only; rotas approve/start/status/abort; checklist UI; persistência.
- **Mock/teste:** transports (browser/vault/skill) injetados nos testes; nenhum acesso real.
- **Bloqueado por env/Browserbase:** abertura real do browser, CDP real (precisa `playwright-core` + envs), live view, captura real de SessionRef — tudo Batch 2.

## 11. Riscos restantes
- **Live view:** decidido usar o **console oficial Browserbase** pelo operador (não expor `connectUrl`). Avaliar no Batch 2 se há inspector efêmero oficial seguro.
- **Vault real:** a captura exige um `PortalSessionVaultAdapter` real (cifrado). Sem ele, falha fechada — Batch 2 conecta o Vault real (39A1) ou implementa o adapter.
- **playwright-core:** dependência a instalar no Batch 2 (não baixa browsers; baixo risco).

## 12. Critérios exatos para o Batch 2
1. Conta Browserbase Free + `BROWSERBASE_API_KEY`/`BROWSERBASE_PROJECT_ID` no EasyPanel.
2. `npm install playwright-core`.
3. Tenant piloto escolhido + portal account AllianzNet criada nesse tenant.
4. Ligar deliberadamente: `GLOBAL_KILL_SWITCH=false` + `PORTAL_REAL_ACTION_ENABLED` + `PORTAL_LOGIN_REAL_ENABLED` + `PORTAL_SESSION_CAPTURE_ENABLED` + `BROWSERBASE_REAL_BROWSER_ENABLED`.
5. Aprovar canary (approve route) + adapter expor `connectUrl` **server-side** para o CDP transport.
6. Vault real conectado.
7. Abrir → humano loga → resolver challenge → capturar → verificar → `session_login_verify` → desligar flags → registrar evidência → **Portal MVP fechado**.
