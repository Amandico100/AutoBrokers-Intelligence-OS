# 43P0 — Portal Browser Relay Audit, Architecture & Foundation Plan Report

> **Status:** concluído (fundação/READ-mostly) · testes offline **56 verdes** (portal contracts) + regressão da stack de ação verde (provider 63 / alignment 32 / registry 61 / outbox 42 / execution 31 / engine 42) · `typecheck` EXIT=0 · build verde · **NENHUM browser/login/credencial/portal real** · contratos puros `dry_run`/`real_action_allowed=false`.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. O que este batch é (e o que não é)
É a **fundação canônica** da frente de portais: auditoria + SPEC + **contratos TS puros** + testes. **Não** executa browser, **não** faz login, **não** toca portal/credencial/sessão real. Tudo nasce travado: `dry_run=true`, `real_action_allowed=false`, CAPTCHA/2FA = HITL (nunca bypass), zero segredo/cookie/storageState/OTP nesta camada.

## 1. O que o Agent OS antigo já tinha de útil
O diretório legado (`AUTOBROKERS_AGENT_OS/...`) **não está sincronizado no workspace** (confirmado por `ls`). Uso-o conceitualmente, via SPEC-011 (que o consolidou) e os relatórios. O que aproveitamos da teoria antiga: **Portal Registry, Portal Map, Portal Skill, CredentialRef, SessionRef, Browser Relay, Action Safety, HITL, Trace/Replay/Eval e Promotion Gate** — além da postura "plano arquitetural, não runtime; portal real bloqueado; sem bypass de CAPTCHA/2FA". É uma boa **arquitetura conceitual**.

## 2. O que NÃO deve ser reutilizado
- Qualquer **runtime paralelo** de agentes/browser do Agent OS antigo (Smith é o runtime).
- Scripts Playwright "por seguradora" soltos.
- Qualquer ideia de **burlar** CAPTCHA/2FA ou guardar segredo fora do Vault.
- Acoplar portal a um corredor específico (portal é infraestrutura global).

## 3. Como isso se encaixa no Smith
Reaproveita as camadas já entregues: **Action Engine** (42X0) gera o objetivo → **Portal Action Candidate** (novo) → **Portal Registry + Portal Map + Portal Skill** → **CredentialRef + SessionRef + Permission Gate + HITL** → **Browser Relay** → provider de browser → **Trace + Replay + Eval + Promotion Gate**. Reusa o modelo de gates do 42X2 (Outbox/permissão) e o padrão de adapters do 42X3/42X4. **Sem motor paralelo, sem schema novo** (contratos puros; persistência futura via `tenant_connections`/metadata, como nas fases X).

## 4. Stack recomendada e por quê
- **Browserbase + Playwright + Stagehand (principal).** Browserbase = cloud browsers estáveis/observáveis para agentes. Playwright = execução determinística + `storageState` (base do SessionRef). Stagehand = `act/extract/observe/agent` — híbrido: determinístico quando o caminho é conhecido, inteligente (LLM) quando a tela muda.
- **Skyvern (lab/fallback pesado):** visão + LLM + Playwright para fluxos difíceis/desconhecidos; homologação, não dependência primária do MVP.
- **Apify/Crawlee (scraping/rotinas auxiliares):** consultas/coleta sem login pesado; **nunca** ação crítica com 2FA/CAPTCHA.
- **Local Playwright:** só dev/sandbox.
Fontes oficiais consultadas: Browserbase (docs.browserbase.com), Stagehand (docs.stagehand.dev — primitivas `act/extract/observe/agent`, híbrido AI+código determinístico), Playwright (playwright.dev/docs/auth — `storageState` reutilizável mas **sensível, não versionar**), Skyvern (github.com/Skyvern-AI/skyvern — LLM+visão+Playwright, anti-bot/proxy/CAPTCHA na cloud).

## 5. Login persistente
Playwright recomenda salvar/reutilizar `storageState` para não logar toda vez — **mas o arquivo contém cookies/headers sensíveis e não deve ir ao repositório**. Isso valida exatamente o **SessionRef**: o conteúdo (`storageState`) fica criptografado no Vault; o sistema guarda só uma **`storage_ref` opaca**, faz health-check por metadados (status + expiração) e **nunca** expõe cookies ao agente/LLM.

## 6. CredentialRef
Referência opaca ao segredo no Vault (`vault_ref`); **nunca** carrega usuário/senha/token. `buildCredentialRef` **lança** se o input contiver campo proibido (defesa em profundidade); `sanitizeCredentialRef` mascara o `vault_ref` e remove qualquer campo sensível antes de responder.

## 7. SessionRef
Referência opaca ao `storageState` criptografado (`storage_ref`); status (`healthy|expired|challenge_required|revoked|unknown`), provider e expiração. `buildSessionRef` **lança** se receber cookie/storageState cru; `evaluateSessionHealth` decide usabilidade **só por metadados** (sem acessar a sessão real); expirada/challenge → `requires_human`.

## 8. CAPTCHA / 2FA
**Nunca bypass.** `classifyChallenge` rotula (`captcha|otp|mfa_app|certificate|token|account_locked`) e **sempre** retorna `requires_human:true, bypass_allowed:false`, com hint **mascarado** (OTP/números omitidos). Fluxo: detectar → pausar → abrir HITL → corretor resolve uma vez → salvar nova SessionRef. OTP nunca vai para o LLM.

## 9. Como o agente é inteligente sem ser perigoso
5 camadas (SPEC-011 §6): (1) **Portal Skill** determinística; (2) **Stagehand observe/act/extract** para UI drift; (3) **Reasoner/Planner** decide o próximo passo pelo estado, não por prompt solto; (4) **HITL** para risco/challenge/ambiguidade; (5) **Trace/Replay/Eval**. O LLM pode interpretar página, sugerir ação, extrair dado e recuperar de drift; **não** pode inserir credencial, resolver 2FA, confirmar cobertura, submeter ação real ou baixar/enviar documento sem permissão.

## 10. Como Portal Map e Portal Skill são aprendidos/promovidos
Portal Map é **versionado** (páginas/journeys/challenges/drift_signals); mudança pequena de UI → Stagehand recupera; mudança grande → `drift_signal` (evento, não erro silencioso). Portal Skill tem `promotion_status` (`draft→sandbox→validated→approved_future`) e só passa de fase com trace/replay/eval. O **Promotion Gate** (`evaluatePortalPromotionGate`) exige 12 condições simultâneas (flag, portal aprovado, skill aprovada, credential, session saudável, dry-run, trace, replay, eval, approval, kill switch) — e ainda assim `real_action_allowed` é **literal false** no 43P0.

## 11. Quantos batches
4 blocos grandes + 2 reais (SPEC-011 §7): **43P0** (este: fundação) → **43P1** (Portal Registry + CredentialRef + SessionRef + Admin UI, browser mock) → **43P2** (Browser Relay Sandbox Harness: browserbase/local_playwright/skyvern_lab, trace/replay, health mock) → **43P3** (primeira Portal Skill dry-run + Portal Map v1) → depois **43P4** (login setup real + SessionRef real) → **43P5** (primeira ação real com HITL). Recomendação: **abrir novo chat** após o 43P0 para conduzir 43P1+ com a SPEC-011 + este relatório como base, evitando contexto pesado.

## 12. Primeiro portal/corredor para dry-run
**Allianz Residencial / assistência eletricista** (corredor MVP já modelado em todas as fases X) — ou, se o portal Allianz exigir certificado/MFA pesado logo no login, escolher no 43P3 o **portal de menor atrito de login** entre os mapeados, fazendo o dry-run primeiro nele e mantendo Allianz como segundo. A decisão final de "qual portal primeiro" depende do `PESQUISA DOS PORTAIS` (intake) a ser auditado no 43P1.

## 13. Riscos que impedem produção (decisões pendentes do Founder)
1. **Custo/estabilidade Browserbase vs Skyvern** em escala (sessões concorrentes, proxies).
2. **Política de retenção do SessionRef** (quanto tempo manter a sessão criptografada; rotação).
3. **Autorização do titular** antes de agir em portal em nome do segurado (LGPD/consentimento).
4. **Termos de uso dos portais** (automação permitida? risco de bloqueio de conta).
5. **2FA recorrente**: portais que forçam OTP a cada login inviabilizam reuso — exigem HITL frequente (definir tolerância operacional).
6. **Certificado digital** (e-CNPJ/e-CPF) em alguns portais → fluxo de credencial especial.

## 14. Arquivos criados/alterados
- `lib/attendance/portal-browser-registry.ts` (**novo**) — `PortalDefinition`/`PortalMap`/`PortalSkill`/`PortalActionCandidate` + `validate*`/`sanitizePortalDefinition`/`buildPortalActionCandidate`/`findForbiddenKeys`.
- `lib/attendance/portal-session-contracts.ts` (**novo**) — `CredentialRef`/`SessionRef` + `build*` (lançam em segredo cru) / `sanitize*` / `evaluateSessionHealth` / `findSessionForbiddenKeys`.
- `lib/attendance/browser-relay-contracts.ts` (**novo**) — `BrowserRelaySession`/`BrowserRelayEvent`/`PortalChallenge`/`PortalTraceSummary` + `createBrowserRelaySession`/`applyRelayEvent`/`classifyChallenge`/`buildTraceSummary`/`evaluatePortalPromotionGate`.
- `docs/canon/SPEC-011-...md` (**atualizado**) — seção "Status de implementação (43P0)".
- `scripts/attendance-portal-browser-contracts.test.mjs` (**novo**, 56 testes) + `package.json` (`test:portal-browser-contracts`).
- `docs/canon/design/2026-06-claude-design/43P0-...md` (este).

## 15. Testes que rodei (offline)
- `node scripts/attendance-portal-browser-contracts.test.mjs` → **56/56**: validação de PortalDefinition/Map/Skill (https obrigatório, HITL obrigatório em challenge); PortalActionCandidate (`dry_run`/`real_send_allowed:false`/`approval_required`/missing inputs); CredentialRef/SessionRef (lançam em segredo cru, sanitizam, mascaram refs); session health (expirada/challenge → humano); challenge policy (captcha/otp/mfa/certificate/locked → HITL, sem bypass, OTP mascarado); relay session (real_future→sandbox, terminal guard, cancel, trace sem PII); promotion gate (sempre `real_action_allowed:false`); detecção de campos proibidos.
- Regressão da stack de ação: provider **63**, alignment **32**, registry **61**, outbox **42**, execution **31**, engine **42** — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde.

## 16. Critério de pronto
| Critério | Status |
|---|---|
| SPEC canônica auditada no repo | ✅ (SPEC-011 + status 43P0) |
| contratos puros sem execução real | ✅ (3 módulos) |
| CredentialRef/SessionRef sanitizam, sem segredo | ✅ |
| CAPTCHA/2FA = HITL, nunca bypass | ✅ |
| PortalActionCandidate/RelaySession nunca real | ✅ (`dry_run`/`real_action_allowed=false`/`external_action_sent=false`) |
| sequência 43P1/P2/P3 definida | ✅ |
| testes verdes + tsc + build | ✅ 56/56, EXIT=0, verde |
| sem quebrar Action Engine/Outbox/Provider | ✅ (regressão verde) |

## 17. Próximos passos
- **43P1** — Portal Registry + CredentialRef + SessionRef + Admin UI (browser mock; sem real). Auditar `PESQUISA DOS PORTAIS` (intake) para escolher o primeiro portal.
- **43P2** — Browser Relay Sandbox Harness (browserbase/local_playwright/skyvern_lab) com trace/replay/health mock.
- **43P3** — primeira Portal Skill dry-run + Portal Map v1.
- Recomendado: novo chat a partir daqui, com SPEC-011 + este relatório como base.
