# 43P-FINAL-2 — PORTAL MVP GO-LIVE (último batch de Portal Browser)

> Wiring real de ponta a ponta: dashboard operacional, Browserbase server-side, CDP real (Playwright), Vault real (Supabase Vault), captura/verify/skill read-only — **tudo gated, nada real aberto neste batch**.
> **Data:** 2026-06-20 · **Modelo:** Claude Opus 4.8 · **Branch:** main · base: `7940a10`

## Declaração de prontidão
```
PORTAL MVP — CÓDIGO PRONTO: SIM
PORTAL MVP — DASHBOARD PRONTO: SIM (botões funcionais: aprovar, iniciar, console, verificar, capturar, skill, abortar, revogar, atualizar)
PORTAL MVP — VAULT PRONTO: SIM (Supabase Vault via RPC; requer 1 migration aplicada — runbook abaixo; sem ela falha fechado)
PORTAL MVP — CDP PRONTO: SIM (playwright-core instalado; connectOverCDP via connectUrl obtido server-side por session_id)
PORTAL MVP — CANARY PRONTO APÓS CONFIG: SIM
PORTAL MVP — PRIMEIRA LEITURA REAL PRONTA APÓS CONFIG: SIM (após envs + flags + migration Vault + login humano)
```
**O único passo restante é operação do Founder** (conta Browserbase Free, 2 envs no EasyPanel, aplicar a migration do Vault, escolher tenant piloto, login humano). **Não há Batch 3 de Portal.**

## Análise da auditoria do GPT (concordo)
As 4 lacunas apontadas eram reais e foram fechadas:
1. **Botões sem `onClick`** → agora todos os botões do canary chamam rotas reais, com loading, erro sanitizado e estado pela state machine.
2. **`connectUrl` descartado sem ponte CDP** → implementado o padrão correto: persistir só `session_id`; ao verificar/capturar, o backend faz `GET /v1/sessions/{id}` server-side, obtém o `connectUrl` **em memória** (`withBrowserbaseConnectUrl`), conecta CDP e descarta. `connectUrl` nunca é retornado/persistido/logado. (Confirmado nas docs: Get a Session devolve o `connectUrl`.)
3. **Sem rota de captura/verify/skill** → criadas `capture`, `verify`, `run-read-only-skill`.
4. **Vault só fail-closed** → criado `createSupabaseVaultAdapter` (RPC do Supabase Vault); sem a migration aplicada, falha fechado (não há falso sucesso).

## Arquivos novos/alterados
| Arquivo | Função |
|---|---|
| `lib/attendance/browserbase-session-server.ts` (novo) | create/get/close server-side + `withBrowserbaseConnectUrl` (connectUrl só em memória) + `findServerSecrets`. |
| `lib/attendance/portal-cdp-transport.ts` (atualizado) | `observeViaCdp` (read-only) + `captureStorageStateViaCdp` (storageState só em memória); playwright-core lazy/externo. |
| `lib/attendance/portal-supabase-vault.ts` (novo) | `createSupabaseVaultAdapter` via RPC `portal_vault_store_session`/`portal_vault_probe`; fail-closed sem migration. |
| `lib/attendance/portal-canary-guard.ts` (novo) | guard compartilhado: conta + flags + readiness + autorização tenant/approval + host allowlist. |
| `lib/attendance/portal-real-execution-controller.ts` (atualizado) | `recordCanaryCapture` (ref opaca), `setCanaryObservation`, campo `observation` sanitizado. |
| `app/api/admin/portal-browser/real-execution/capture|verify|run-read-only-skill/route.ts` (novos) | fluxo real gated. |
| `app/admin/portal-browser/page.tsx` (atualizado) | painel de canary **operacional** (todos os botões com handler). |
| `next.config.js` | `serverExternalPackages: ['playwright-core']`. |
| `package.json` | `playwright-core` + scripts de teste. |
| `docs/.../43P-FINAL-2-supabase-vault-portal-session.sql` | migration Vault (apply/verify/rollback). |

## Fluxo de ponta a ponta (gated)
`select-company` → criar Portal Account → **aprovar canary** (`approve`, expira ≤1h) → **iniciar** (`start`: cria sessão Browserbase server-side; sem env/flags falha fechado sem rede) → **Abrir Browserbase Console** (operador) → humano loga + resolve CAPTCHA/2FA → **verificar** (`verify`: CDP observe read-only + valida metadados) → **capturar** (`capture`: CDP `storageState` em memória → Vault → `storage_ref` opaca) → **rodar** `session_login_verify` (`run-read-only-skill`) → **abortar/encerrar** (`abort`). Kill switch encerra tudo.

## Segurança (garantida + testada)
- `connectUrl/signingKey/debuggerUrl/wsUrl/cookies/storageState/token` **nunca** em resposta/frontend/Supabase comum/`tenant_connections`/logs/trace (scanners `findServerSecrets`/`findCanarySecrets`/`findSkillOutputSecrets` + sanitização em todas as rotas).
- storageState fica **só no closure** do request; gravado direto no Vault; só `storage_ref` (uuid opaco) é persistido.
- Vault **fail-closed**: sem RPC/migration → `vault_unavailable`; **nunca** fallback para JSONB/tabela comum.
- CDP: sem `connectUrl` bloqueia; challenge bloqueia captura; host fora da allowlist bloqueia skill; read-only (sem ação de negócio).
- Autorização por tenant + approval que expira; kill switch sempre vence; cross-tenant negado; `real_action_allowed=false` em tudo.

## playwright-core (decisão)
Instalado como dependência (`^1.61.0`) — **não baixa Chromium** (é só o cliente CDP). Marcado em `serverExternalPackages` (não bundled) + import lazy com `webpackIgnore` (dupla proteção). Build e tsc verdes com ele instalado. Em runtime, conecta a Browserbase via `connectOverCDP`; se indisponível, falha fechado.

## Migration do Vault (passo manual único)
Aplicar `docs/canon/design/2026-06-claude-design/43P-FINAL-2-supabase-vault-portal-session.sql` no SQL editor do Supabase (cria `portal_vault_probe` + `portal_vault_store_session`, SECURITY DEFINER, `search_path=''`, execução só por `service_role`). Inclui VERIFY e ROLLBACK. Sem isso, a captura falha fechada (sem falso sucesso).

## Runbook do canary (produção restrita)
Estado seguro padrão: `GLOBAL_KILL_SWITCH=true` e todas as flags de portal `false`.
1. Criar conta Browserbase Free → `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID` no EasyPanel.
2. Aplicar a migration do Vault.
3. Escolher tenant piloto (RAFAEL SEGUROS ou AutoBrokers Global Knowledge — ou criar a corretora real pelo painel) + criar Portal Account AllianzNet.
4. Janela deliberada de canary: `GLOBAL_KILL_SWITCH=false` + `PORTAL_REAL_ACTION_ENABLED` + `PORTAL_LOGIN_REAL_ENABLED` + `PORTAL_SESSION_CAPTURE_ENABLED` + `BROWSERBASE_REAL_BROWSER_ENABLED`.
5. No `/admin/portal-browser`: Aprovar canary → Iniciar → Abrir Browserbase Console → humano loga → Verificar → Capturar → Rodar `session_login_verify` (esperado `authenticated:true`, `session_state:healthy`).
6. Encerrar: desligar todas as flags + `GLOBAL_KILL_SWITCH=true`; revisar logs sanitizados.
**Abortar se:** qualquer leak, challenge não resolvido, custo/timeout anômalo, comportamento inesperado → botão "Abortar canary".

## Envs necessárias (sem valores)
`BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID` (EasyPanel, server-side). Flags listadas acima.

## Testes (offline) — todos verdes
- Novos/atualizados: browserbase-session-server **12**, real-execution-controller **27** (inclui recordCapture/observation), tenant-canary-authorization 14, session-vault 9, read-only-skill 15.
- Regressão: company-scope 19, browserbase-adapter 25, login-setup 33, relay 47, skill-factory 46, security 31.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde (com playwright-core) · `git diff --check` limpo.

## 3 testes live para o Founder
**Teste 1 (UI, sem console):** `/admin/portal-browser` → selecionar corretora → recarregar → corretora continua selecionada → seção "Contas" não dá 403.
**Teste 2 (readiness, um snippet):**
```js
(async () => {
  const c = await (await fetch('/api/admin/portal-browser/companies')).json();
  const a = await fetch('/api/admin/portal-browser/accounts');
  const s = await (await fetch('/api/admin/portal-browser/real-execution/status')).json();
  console.log({ selected: c.current_company_id, accounts_http: a.status, canaries:(s.canaries||[]).length, real_action_allowed: s.real_action_allowed });
})(); // esperado: selected=UUID, accounts_http=200, real_action_allowed=false
```
**Teste 3 (go/no-go visual):** após Browserbase Free/envs + migration, o painel "Canary real de login" mostra o checklist e os botões habilitam conforme o estado.

## Riscos restantes
- **Migration Vault** precisa ser aplicada (1 passo manual; sem ela captura falha fechada).
- **Seletores específicos do portal** (auth marker/challenge): hoje genéricos; o portal map fornece os específicos do AllianzNet — refinar no primeiro canary (não bloqueia o MVP de login-verify).
- **Get Session connectUrl**: o adapter extrai `connectUrl` da resposta; se a conta Browserbase exigir um endpoint/campo diferente, ajuste pontual no `browserbase-session-server` durante o canary (defensivo: sem connectUrl → falha fechada).

## Expansão futura (NÃO bloqueia Portal MVP)
Ações de negócio reais (consultar apólice/CPF, abrir sinistro/assistência, cotação), novos portais/skills/seguradoras, reuso de SessionRef para automação — tudo entra **depois**, com gates próprios. Portal MVP = conectar + login humano + SessionRef segura + leitura read-only verificada.

## Próxima prioridade (Portal sai do roadmap principal)
`42X5B` + `42X5C` (WhatsApp/Z-API) → **Piloto Allianz Residencial** → Auxiliares → Core/Jarvys → RAG/Knowledge OS.
