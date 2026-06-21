# 43P-FINAL-2A.1 — Patch: Canary Readiness Account-Aware (botão "Iniciar canary")

> Patch pequeno e obrigatório: o botão "Iniciar canary" ficava travado mesmo com approval válida. Sem nova arquitetura/agente/Skill/migration; gates fechados; nada real aberto.
> **Data:** 2026-06-20 · **Modelo:** Claude Opus 4.8 · base: `a6e57e6`

## Causa raiz
O card "Browserbase readiness" era carregado uma vez (no mount) pela rota `login-setup/browserbase/readiness`, que passava `approval_exists: false` fixo. Resultado: a readiness GLOBAL sempre exibia `no_human_approval` e `can_open_real_browser=false`. O botão "Iniciar canary" dependia desse readiness global → ficava desabilitado **mesmo com a approval da Portal Account criada e válida**. A readiness não era específica da conta selecionada.

## Correção (sem duplicar regra)
1. **Nova rota** `GET /api/admin/portal-browser/real-execution/readiness?portal_account_id=...` — reaproveita a MESMA lógica canônica (`guardCanary` → `evaluateBrowserbaseReadiness` + `evaluateTenantCanaryAuthorization`). Retorna só booleanos seguros: `env_ok, kill_switch_off, flags_ok, browserbase_ready, approval_valid, start_allowed, blockers`. **Nunca** retorna API key/projectId/connectUrl/signingKey/cookies/storageState/token.
2. **Helper puro** `deriveCanaryReadinessFlags(blockers)` (em `portal-tenant-canary-authorization.ts`) — deriva os flags granulares dos blockers; usado pela rota (DRY) e coberto por teste.
3. **Readiness global** (`login-setup/browserbase/readiness`) agora passa `approval_exists: true` → o card global reflete só **infraestrutura** (env+flags+kill switch), sem o falso `no_human_approval`. Card relabelado: "readiness global de infraestrutura".
4. **UI Portal Lab:** readiness por-conta é carregada ao selecionar a Portal Account e recarregada após **Aprovar / Revogar / Atualizar status**. O botão "Iniciar canary" agora depende de `start_allowed` (backend). Checklist usa `approval_valid` / `flags_ok && kill_switch_off` / `env_ok` reais. Linha "Canary pronto para iniciar: SIM/NÃO + bloqueios". Removido o botão-fachada "Iniciar canary real" do card global.

## Segurança
- `start_allowed=true` só quando o backend autoriza (env + flags + kill switch off + approval válida da conta + tenant correto). Kill switch sempre vence; ação de negócio segue `allowed=false`.
- Readiness não expõe segredo; sem migration; sem abrir Browserbase; sem tocar Z-API/flags.

## Testes
- `attendance-portal-tenant-canary-authorization` **25** (incluindo: flags off → start_allowed false; flags on sem approval → false; tudo ok → true; expirada/revogada → approval_valid false; granular flags). Regressão (adapter 25, controller 27, reuse 13, security 31) verde. `tsc` EXIT=0, build verde.

## 3 passos do Founder para o canary (após deploy)
1. No Portal Lab (master): selecionar **Resulta Seguros** → no Catálogo, "Conectar à corretora" no **AllianzNet Corretor** (se ainda não houver conta).
2. No painel "Canary real de login": selecionar a conta → **Aprovar canary** (a linha "Canary pronto para iniciar" deve virar **SIM** quando envs+flags+kill switch+approval estiverem ok).
3. **Iniciar canary** → **Abrir Browserbase Console** → login humano → **Verificar** → **Capturar** → **Rodar session_login_verify** → desligar flags.

## Nota estratégica (decisão do Founder)
O Founder quer que a conexão de portais/canary seja feita **no dashboard da própria corretora** (Resulta), não no Portal Admin — com tudo global (chat AutoBrokers, agente de atendimento, corredores, portais com links já cadastrados, auxiliares globais) disponível em cada dashboard para personalizar. Isso é o **Tenant Activation Center** (contrato já commitado em `tenant-activation-center-v1-contract.md`). É um build estrutural maior (UI tenant-facing) e deve ser um batch dedicado — **não** cabe neste patch. O Portal Lab continua como área interna (master) de homologação.
