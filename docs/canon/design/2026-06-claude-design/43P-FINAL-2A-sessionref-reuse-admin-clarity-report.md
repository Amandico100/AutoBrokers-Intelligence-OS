# 43P-FINAL-2A — SessionRef Reuse Acceptance Fix + Portal Admin Clarity + Tenant Activation Contract

> Correção final de aceitação do Portal MVP: SessionRef vinculada à Portal Account, Vault **read** server-side e **reuso** real (independente do canary). + clareza de UX (Portal Lab) + contrato do Tenant Activation Center. **Nada real aberto/ligado; gates fechados; sem segredos.**
> **Data:** 2026-06-20 · **Modelo:** Claude Opus 4.8 · **Branch:** main · base: `9332c1c`

## Declaração
```
PORTAL ACCESS INFRASTRUCTURE FINALIZADA: SIM
SESSIONREF VINCULADA À PORTAL ACCOUNT: SIM
VAULT WRITE: SIM
VAULT READ SERVER-SIDE: SIM (RPC; requer migration atualizada aplicada — runbook)
SESSION RESTORE APÓS CANARY ENCERRADO: SIM (código pronto)
READ-ONLY SKILL COM SESSIONREF REUTILIZADA: SIM
CÓDIGO DE REUSO PRONTO PARA CANARY: SIM
REUSO VALIDADO EM BROWSERBASE REAL: PENDENTE DE CANARY CONTROLADO
CROSS-TENANT BLOCKED: SIM (app + guarda no RPC do Vault)
PORTAL LAB MASTER-ONLY: SIM (sidebar master + redirect de company_admin + banner)
PORTAL ACCOUNT VIA CATÁLOGO GLOBAL: SIM ("Conectar à corretora" — sem campos técnicos)
TENANT ACTIVATION CENTER CONTRACT COMMITADO: SIM
AÇÃO DE NEGÓCIO REAL: CONTINUA BLOQUEADA (evaluatePortalRealActionGate allowed=false)
NÃO HÁ NOVO BATCH DE INFRAESTRUTURA PORTAL APÓS ESTE: SIM
PRÓXIMO PASSO OPERACIONAL: Browserbase Free + migration Vault atualizada + canary Resulta
```

## Ajustes de UX/clareza desta finalização
- **Portal Lab no sidebar (master only):** entrada `Portal Lab` adicionada ao `masterMenuItems` em `app/admin/layout.tsx`; `/admin/portal-browser` incluído em `masterOnlyRoutes` (company_admin é redirecionado). Banner explicativo no topo.
- **Conexão de portal por catálogo:** na tabela do Catálogo Global, botão **"Conectar à corretora"** cria a Portal Account a partir do portal do catálogo (label sugerida `Corretora — Portal`), **sem** preencher owner_key/URL/journey. O formulário técnico manual continua disponível abaixo, agora sob o separador "Avançado / Engenharia".
- **Fixtures identificadas:** tag `fixture` no catálogo e `· teste/fixture` no seletor de corretora (heurística sandbox/mock/fixture/canonical/test/demo) — evita confundir Rafael/teste com Resulta. Nenhum dado é apagado.
- **Separação operação × engenharia:** separador "Avançado / Engenharia — uso interno" antes de Relay Sandbox / Portal Skills / Skill Factory (DS-001 §6.5).
- **Design:** segui o DS-001 (visual calmo, hierarquia clara, linguagem não técnica para o que a corretora toca). **Recomendação (a combinar):** uma reorganização mais profunda do Portal Lab em abas (Visão geral / Contas & Sessões / Canary / Avançado), mobile-first, merece um passo de design dedicado — não fiz agora para não arriscar a UI funcional do canary/reuso; aviso por ser mudança estrutural.

## Análise: o GPT estava certo
As 4 lacunas de aceitação eram reais (verifiquei no código):
1. Vault adapter só tinha `available()`+`write()` — **faltava `read()`**. ✓
2. Capture gravava `storage_ref` no canary mas **não vinculava SessionRef à Portal Account**. ✓
3. `run-read-only-skill` usava a observação do canary, **não** uma SessionRef reaberta. ✓
4. Sem ciclo de reuso após o canary fechar. ✓
Também confirmei: `evaluatePortalRealActionGate()` é hard-locked `allowed:false` (ação de negócio bloqueada independ. de flags) — exatamente como o GPT disse. **Recomendação dele de não aplicar a migration antiga antes do read estava correta** — agora a migration tem write **e** read; aplica-se uma vez só.

## Parte A — reuso (implementado)
- **`portal-session-vault.ts`**: interface ganhou `read()`; `failClosedVaultAdapter.read` → `vault_unavailable`; `readSessionRefViaVault()` (fail-closed; payload só em memória).
- **`portal-supabase-vault.ts`**: `read()` via RPC `portal_vault_read_session` (parse em memória; nunca loga).
- **`portal-admin-sanitizers.ts`**: `SessionRefRecord` ganhou `storage_ref` (uuid **completo**, server-side, para reuso) + `last_verified_at`; status `reauth_required`. **Sanitizers só expõem `storage_ref_masked`** (o uuid completo nunca vai ao frontend) + `reusable`/`last_verified_at`.
- **Capture route**: ao capturar, **vincula** `session_ref` à Portal Account (`buildSessionRefRecord` + `savePortalAccount`) — não depende mais só do objeto canary.
- **`portal-cdp-transport.ts`**: `restoreStorageStateViaCdp(connectUrl, storageState)` → `newContext({storageState})` → observa (read-only). NOTA: o caminho produção-grade do Browserbase é "Contexts"; documentado para validar no 1º canary.
- **`portal-session-reuse.ts`** (novo, self-contained, DI): `reuseSessionRefForReadOnly` orquestra Vault read → restore → skill, **falha fechado** (revoked/expired/reauth/sem authz/sem vault), e **bloqueia qualquer segredo no resultado** (`findReuseSecrets`).
- **Rotas novas (gated)**: `real-execution/reuse-skill` (abre NOVA sessão, restaura, roda skill; storageState/connectUrl só em memória) e `real-execution/session-ref` (verify/revoke/mark_expired/request_relogin por metadados).
- **Dashboard**: painel "Sessões e Saúde" por conta — status, reutilizável, última verificação, expiração + botões **Verificar SessionRef / Reutilizar p/ login_verify / Solicitar re-login / Revogar** (handlers reais).

## Parte B — clareza do Portal Admin
- Banner "Portal Lab — área interna de homologação técnica" no topo (corretoras não usam Relay Sandbox/Skill Factory).
- Painel de Sessões/Saúde separa a operação de SessionRef das telas técnicas.
- **Follow-up cosmético (não bloqueia):** entrada no sidebar master-only e recolher Relay Sandbox/Skill Factory em `<details>` — evitei mexer no layout compartilhado para não arriscar a build; documentado.

## Parte C — contrato
`docs/canon/design/2026-06-claude-design/tenant-activation-center-v1-contract.md` — define a futura experiência da corretora (o que vê / não vê), quem cria o quê, e os princípios de dados (SessionRef por corretora, sem duplicação, banco canônico).

## Segurança (garantida + testada)
- storageState/cookies/connectUrl/signingKey/token **nunca** em resposta/log/trace/tabela comum/`tenant_connections`/frontend.
- O uuid `storage_ref` completo fica só em `connection_config` (server-side) e no Vault; o frontend só recebe `storage_ref_masked`.
- Vault read **fail-closed** sem migration; **guarda cross-tenant no RPC** (o name do secret precisa pertencer à company+account).
- Reuso falha fechado: não autorizado / revogada / expirada / reauth_required / sem vault / challenge.
- Cross-tenant: SessionRef da Resulta não serve para outra corretora (app valida conta no tenant + RPC valida name).
- `real_action_allowed=false` em tudo; ação de negócio segue hard-locked.

## Testes (offline) — verdes
- Novos/atualizados: **portal-session-reuse 13**, **portal-session-vault 12** (+read), browserbase-session-server 12, read-only-skill 15, real-execution-controller 27, tenant-canary-authorization 14, company-scope 19, browserbase-adapter 25, login-setup 33.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Migration (passo manual único, atualizado)
Aplicar `43P-FINAL-2-supabase-vault-portal-session.sql` (agora com `portal_vault_probe` + `portal_vault_store_session` + **`portal_vault_read_session`**; SECURITY DEFINER; `search_path=''`; só `service_role`; guarda cross-tenant; APPLY/VERIFY/ROLLBACK). Sem ela, write/read falham fechados.

## 3 testes live para o Founder
1. `/admin/portal-browser` → selecionar corretora → recarregar → continua selecionada + Contas sem 403 + aparecem os painéis "Sessões e Saúde" e "Canary".
2. Snippet único:
```js
(async () => {
  const c = await (await fetch('/api/admin/portal-browser/companies')).json();
  const a = await fetch('/api/admin/portal-browser/accounts');
  const s = await (await fetch('/api/admin/portal-browser/real-execution/status')).json();
  console.log({ selected: c.current_company_id, accounts_http: a.status, real_action_allowed: s.real_action_allowed });
})(); // esperado: selected=UUID, accounts_http=200, real_action_allowed=false
```
3. Visual: painel "Sessões e Saúde" mostra status/reutilizável e botões; "Reutilizar" fica habilitado só quando a SessionRef é `healthy` e reutilizável.

## O que o Founder deve fazer depois (operação)
1. Criar a company real **RESULTA SEGUROS** no painel (não usar AutoBrokers Global Knowledge/RAFAEL como produção da corretora piloto).
2. Conta Browserbase Free → `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID` no EasyPanel.
3. Aplicar a migration do Vault (write+read).
4. Criar Portal Account AllianzNet da Resulta.
5. Janela de canary (ligar as 5 flags) → Aprovar → Iniciar → Console → login humano → Verificar → Capturar (vincula SessionRef à conta) → `session_login_verify` → testar **Reutilizar p/ login_verify** (prova reuso após o canary fechar) → desligar flags.

## O que NÃO fazer ainda
- Não habilitar ação de negócio real (consulta de apólice/boleto, abrir assistência/sinistro) — são **Skills de negócio**, cada uma criada/validada via Claude Code com gate próprio (próxima fase).
- Não conectar credenciais reais antes da migration + Browserbase + consentimento.

## Próximo trabalho técnico (Portal sai do roadmap principal)
`42X5B` (Z-API real gated) → `42X5C` (canary WhatsApp) → **Allianz Residencial Eletricista Capability Pack** (Skills de negócio + corredor ponta a ponta). Sem novo batch de infraestrutura Portal.
