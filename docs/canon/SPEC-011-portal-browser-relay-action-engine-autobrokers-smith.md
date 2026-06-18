# SPEC-011 — Portal Browser Relay, SessionRef, Portal Maps & Action Execution for AutoBrokers/Smith

> Status: proposta canônica para próximo chat/batch de auditoria e fundação.  
> Objetivo: criar a arquitetura global de portais para seguradoras, prestadores, reguladoras e rotinas auxiliares usando a estrutura do Smith, sem motor paralelo e sem acesso real prematuro.  
> Escopo recomendado do próximo batch: **43P0 — Portal Browser Relay Audit, Architecture & Foundation Plan**.

---

## 1. Decisão executiva

A automação de portais não deve ser tratada como “um script Playwright para Allianz”. Ela deve ser uma infraestrutura global do AutoBrokers/Smith, reutilizável por todos os corredores, auxiliares, seguradoras, prestadores e rotinas futuras.

A arquitetura correta é:

```txt
Action Engine / Corridor Runtime
  ↓
Portal Action Candidate
  ↓
Portal Registry + Portal Map + Portal Skill
  ↓
CredentialRef + SessionRef + Permission Gate + HITL
  ↓
Browser Relay
  ↓
Provider de browser: Browserbase/Playwright/Stagehand/Skyvern/Local
  ↓
Trace + Replay + Evals + Promotion Gate
```

No MVP, nada deve tentar “burlar” CAPTCHA/2FA. O correto é detectar challenge, pausar, pedir HITL, capturar SessionRef aprovada e reutilizar sessão enquanto estiver válida.

---

## 2. Princípios obrigatórios

1. **Smith é o runtime.** Não criar motor paralelo de agentes/browser.
2. **Portal não é corredor.** Corredor define objetivo; Portal Map define superfície; Browser Relay executa.
3. **CredentialRef nunca expõe senha.** Senha/token/cookie/storageState ficam no Vault/secret store.
4. **SessionRef reduz atrito.** O corretor pode fazer primeiro login interativo; a sessão persistida é reutilizada com expiração/health-check.
5. **CAPTCHA/2FA não é bypass.** É challenge. Deve abrir HITL e registrar auditoria.
6. **Playwright determinístico primeiro.** Stagehand/LLM só entra como fallback controlado ou exploração/homologação.
7. **Skyvern é laboratório/fallback pesado**, não dependência principal do MVP.
8. **Browserbase é infraestrutura cloud browser recomendada** para sessões estáveis, observabilidade e execução remota.
9. **Trace/Replay/Eval antes de real.** Toda ação deve ser reprodutível, auditável e promovível.
10. **Sem ação real antes de gates.** Todo clique/submissão/download/upload real exige permission, HITL, dry-run anterior, trace, allowlist e kill switch.

---

## 3. Modelo conceitual

### 3.1 Portal Registry

Cadastro global/sandbox de portais:

```ts
type PortalDefinition = {
  portal_id: string;
  label: string;
  owner_kind: 'insurer' | 'provider' | 'regulator' | 'broker_tool' | 'other';
  insurer_key?: string;
  provider_key?: string;
  base_url: string;
  login_url?: string;
  supported_channels: ('browser' | 'api' | 'email' | 'phone')[];
  auth_methods: ('password' | 'mfa' | 'captcha' | 'sso' | 'certificate')[];
  risk_level: 'low' | 'medium' | 'high';
  status: 'draft' | 'mapped' | 'sandbox_ready' | 'homologating' | 'approved_future' | 'blocked';
  notes?: string;
};
```

### 3.2 Portal Map

Mapa versionado da superfície de um portal. Não contém segredo nem sessão.

```ts
type PortalMap = {
  portal_id: string;
  version: string;
  journeys: PortalJourney[];
  known_pages: PortalPage[];
  challenges: PortalChallengeRule[];
  drift_signals: string[];
  evidence_outputs: string[];
};
```

### 3.3 Portal Skill

Skill versionada para uma tarefa específica:

```ts
type PortalSkill = {
  skill_id: string;
  portal_id: string;
  objective: string;
  corridor_key?: string;
  subcorridor_key?: string;
  action_kind: 'open_assistance' | 'open_claim' | 'check_payment' | 'download_policy' | 'consult_status' | 'upload_document' | 'other';
  required_inputs: string[];
  output_schema: Record<string, unknown>;
  allowed_actions: string[];
  forbidden_actions: string[];
  promotion_status: 'draft' | 'sandbox' | 'validated' | 'approved_future';
};
```

### 3.4 CredentialRef

Referência ao segredo; nunca carrega segredo em prompt/contexto.

```ts
type CredentialRef = {
  credential_ref_id: string;
  company_id: string;
  portal_id: string;
  account_label: string;
  vault_ref: string;
  status: 'missing' | 'configured' | 'needs_rotation' | 'revoked';
  last_verified_at?: string;
};
```

### 3.5 SessionRef

Referência à sessão persistida; nunca expõe cookies/storageState ao agente.

```ts
type SessionRef = {
  session_ref_id: string;
  company_id: string;
  portal_id: string;
  credential_ref_id?: string;
  storage_ref: string;
  browser_provider: 'browserbase' | 'local_playwright' | 'skyvern' | 'other';
  status: 'healthy' | 'expired' | 'challenge_required' | 'revoked' | 'unknown';
  expires_at?: string;
  last_health_check_at?: string;
};
```

### 3.6 Portal Action Candidate

Candidato de ação gerado pelo Action Engine. Ainda não é execução.

```ts
type PortalActionCandidate = {
  case_id?: string;
  action_goal: string;
  portal_id: string;
  portal_skill_id?: string;
  required_inputs: string[];
  available_inputs: Record<string, unknown>;
  missing_inputs: string[];
  credential_ref_required: boolean;
  session_ref_required: boolean;
  approval_required: boolean;
  dry_run: true;
  real_send_allowed: false;
};
```

### 3.7 Browser Relay Session

Sessão operacional, controlada e auditável.

```ts
type BrowserRelaySession = {
  relay_session_id: string;
  mode: 'recon' | 'sandbox' | 'dry_run' | 'real_future';
  portal_id: string;
  portal_skill_id?: string;
  action_candidate_id?: string;
  browser_provider: 'browserbase' | 'local_playwright' | 'skyvern';
  status: 'created' | 'waiting_session' | 'running' | 'challenge_required' | 'waiting_human' | 'completed_dry_run' | 'failed' | 'cancelled';
  events: BrowserRelayEvent[];
  trace_ref?: string;
  replay_ref?: string;
  outputs?: Record<string, unknown>;
  external_action_sent: false;
};
```

---

## 4. Ferramentas recomendadas

### 4.1 Base principal para MVP

```txt
Browserbase + Playwright + Stagehand
```

Uso:
- Browserbase para browser cloud, sessão, infraestrutura e observabilidade.
- Playwright para fluxos determinísticos e storageState.
- Stagehand para act/extract/observe, self-healing, cache e fallback agentic controlado.

### 4.2 Fallback/lab para fluxos difíceis

```txt
Skyvern
```

Uso:
- exploração visual de portais desconhecidos;
- workflows longos ou pouco mapeados;
- laboratório de homologação;
- comparar contra Playwright/Stagehand;
- não usar como primeira dependência de produção até custo/estabilidade serem comprovados.

### 4.3 Scraping/rotinas auxiliares

```txt
Apify/Crawlee
```

Uso:
- scraping/consulta periódica quando login não é pesado;
- download de páginas/arquivos;
- auxiliares de cobrança/status;
- não usar como executor principal de portais sensíveis com 2FA/CAPTCHA.

---

## 5. Como lidar com login, CAPTCHA e 2FA

### 5.1 Primeiro acesso

O fluxo ideal:

1. Admin/corretor cadastra portal.
2. Admin informa CredentialRef ou abre login assistido.
3. Browser Relay abre browser isolado em modo `login_setup`.
4. Corretor faz login e completa 2FA/CAPTCHA manualmente.
5. Sistema salva SessionRef criptografada.
6. Sistema faz health check sem expor cookies.
7. SessionRef passa a ser usada por agentes.

### 5.2 Reuso de sessão

O agente não deve fazer login completo toda vez. Deve:
- carregar SessionRef;
- testar health check;
- se válida, executar task;
- se expirada/challenge, pausar e pedir HITL.

### 5.3 CAPTCHA/2FA

Não tentar burlar. Regras:
- detectar challenge;
- classificar: captcha, OTP, MFA app, certificado, token, bloqueio;
- pausar browser;
- pedir humano;
- salvar nova SessionRef depois da resolução;
- nunca mandar OTP para LLM.

---

## 6. Inteligência dentro do portal

O agente precisa ser inteligente, mas não solto.

Camadas:

1. **Portal Skill determinística:** passos conhecidos.
2. **Stagehand observe/act/extract:** adaptação controlada quando seletor muda.
3. **Reasoner/Planner:** decide próximo passo com base em estado, não em prompt solto.
4. **HITL:** quando há risco, challenge ou ambiguidade.
5. **Trace Replay Evals:** grava e valida tudo para melhorar skill.

Regra:
- LLM pode interpretar página, sugerir ação, extrair dados e recuperar de UI drift.
- LLM não pode inserir credencial, resolver 2FA, confirmar cobertura, submeter ação real ou baixar/enviar documentos sem permissão.

---

## 7. Fases recomendadas

### 43P0 — Audit & Architecture Foundation

Entregas:
- auditoria do Smith atual;
- auditoria do Agent OS antigo;
- auditoria dos documentos de portal;
- inventário das ferramentas;
- SPEC canônica de Portal Browser Relay no repo;
- contratos TS puros sem execução real;
- relatório de decisão.

### 43P1 — Portal Registry, CredentialRef, SessionRef & Admin UI

Entregas:
- Portal Registry admin;
- CredentialRef/SessionRef contracts;
- UI para cadastro de portal e conta;
- login setup placeholder;
- nenhum browser real ainda ou apenas mock.

### 43P2 — Browser Relay Sandbox Harness

Entregas:
- provider adapters: browserbase, local_playwright, skyvern_lab;
- relay session sandbox;
- trace/replay contrato;
- health check mock/controlled;
- screenshots sanitizados;
- nenhuma ação real.

### 43P3 — First Portal Skill Dry-run

Entregas:
- primeira skill: Allianz Residencial / assistência eletricista ou portal mais acessível;
- Portal Map v1;
- execução dry-run com Browserbase/Playwright/Stagehand;
- nenhum submit real;
- trace/replay/evals.

### 43P4 — Controlled Real Portal Action

Entregas futuras:
- login setup real;
- SessionRef real;
- submit real único com aprovação humana;
- kill switch;
- rollback;
- observabilidade.

---

## 8. Prompt recomendado para Claude — 43P0

```txt
BATCH 43P0 — Portal Browser Relay Audit, Architecture & Foundation Plan

Objetivo:
Auditar o que já existe no Smith e no Agent OS antigo sobre portais, browser automation, CredentialRef, SessionRef, Portal Map, Browser Relay, Stagehand/Playwright, Browserbase, Skyvern, Action Safety e HITL. Criar uma SPEC canônica e contratos puros para a futura infraestrutura global de portais, sem executar browser real.

Contexto:
O AutoBrokers já tem Action Engine, Outbox, Provider Registry, Q&A, mídia, InfoCap e dispatch. Z-API real está pausada. Agora vamos estruturar a camada de portais para seguradoras/prestadores/reguladoras/rotinas auxiliares, usando Smith e sem motor paralelo.

Auditar no repo atual:
- docs/canon/SPEC-005
- docs/canon/SPEC-007
- docs/canon/SPEC-008
- docs/canon/SPEC-010
- todos os relatórios 42X0 a 42X4
- lib/attendance/action-engine.ts
- provider registry/outbox/execution
- backend services de browser se existirem
- Vault/tenant_connections/connector_templates

Auditar no Agent OS antigo se disponível:
- AUTOBROKERS_AGENT_OS/17_INTELIGENCIA_OPERACIONAL/PORTAL_BROWSER_ROUTINES_MASTER_PLAN.md
- 03_EXECUTION_PLANE/PORTAL_ACTIONS.md
- 03_EXECUTION_PLANE/BROWSER_RELAY_POLICY.md
- 03_EXECUTION_PLANE/PORTAL_MAP_CONTRACT.md
- 09_CONTRATOS/VAULT_CREDENTIAL_REF_POLICY.md
- docs de Stagehand/Playwright/Portal Skills
- AUTOBROKERS_RESULTA_INTAKE/PESQUISA DOS PORTAIS
- conversas com seguradoras/prestadores/reguladoras apenas como referência de domínio

Pesquisar docs oficiais atuais:
- Browserbase docs
- Stagehand docs
- Playwright auth/storageState/trace
- Skyvern docs/GitHub
- Apify/Crawlee docs
- qualquer SDK oficial relevante

Entregar:
1. SPEC canônica docs/canon/SPEC-011-portal-browser-relay-action-engine-autobrokers-smith.md
2. Relatório docs/canon/design/2026-06-claude-design/43P0-portal-browser-relay-audit-foundation-report.md
3. Helpers puros se seguro:
   - lib/attendance/portal-browser-registry.ts
   - lib/attendance/portal-session-contracts.ts
   - lib/attendance/browser-relay-contracts.ts
4. Sem browser real, sem login real, sem senha, sem sessão real, sem Playwright real, sem Browserbase real.

Decisão arquitetural obrigatória:
- Smith é runtime.
- Browser Relay não é Action Engine paralelo.
- CredentialRef/SessionRef nunca expõem segredo.
- CAPTCHA/2FA = HITL challenge, não bypass.
- Playwright deterministic first; Stagehand fallback; Skyvern lab/fallback pesado; Browserbase cloud infra.
- Toda ação real futura exige approval, permission, trace, eval, kill switch.

Testes:
- contratos puros;
- Portal Definition valida;
- Portal Map valida;
- CredentialRef/SessionRef sanitizados;
- Portal Action Candidate não executa;
- challenge policy bloqueia CAPTCHA/2FA;
- sem PII/secrets;
- regressões existentes verdes.

Critério de pronto:
43P0 está pronto quando temos mapa completo para executar 43P1/P2/P3 com previsibilidade, sem improvisar browser automation.
```
```

---

## 8.1 Status de implementação — 43P0 (fundação)

> Executado em 2026-06-17 (Claude Opus 4.8). Contratos **puros**, sem browser/login/portal real.

Contratos TS criados (todos `dry_run`/`real_action_allowed=false`, sem segredo/PII):
- `lib/attendance/portal-browser-registry.ts` — `PortalDefinition`, `PortalPage`, `PortalJourney`, `PortalChallengeRule`, `PortalMap`, `PortalSkill`, `PortalActionCandidate` + `validatePortalDefinition`/`validatePortalMap`/`validatePortalSkill`, `sanitizePortalDefinition`, `buildPortalActionCandidate`, `findForbiddenKeys`.
- `lib/attendance/portal-session-contracts.ts` — `CredentialRef`, `SessionRef` + `buildCredentialRef`/`buildSessionRef` (lançam se receberem segredo cru), `sanitizeCredentialRef`/`sanitizeSessionRef` (mascaram refs), `evaluateSessionHealth` (só metadados), `findSessionForbiddenKeys`.
- `lib/attendance/browser-relay-contracts.ts` — `BrowserRelaySession`, `BrowserRelayEvent`, `PortalChallenge`, `PortalTraceSummary` + `createBrowserRelaySession` (rebaixa `real_future`→`sandbox`), `applyRelayEvent` (guard de estado terminal, mascarado), `classifyChallenge` (CAPTCHA/2FA → HITL, nunca bypass), `buildTraceSummary`, `evaluatePortalPromotionGate` (12 gates; `real_action_allowed` literal `false`).

Testes: `scripts/attendance-portal-browser-contracts.test.mjs` (56/56). `tsc` EXIT=0, build verde, regressão da stack de ação verde.

Garantias travadas no 43P0:
- `dry_run=true`, `real_send_allowed=false`, `external_action_sent=false`, `real_action_allowed=false` (tipos literais).
- CredentialRef/SessionRef nunca carregam senha/token/cookie/storageState/OTP; sanitização mascara `vault_ref`/`storage_ref`.
- CAPTCHA/OTP/MFA/certificado/conta bloqueada → `requires_human:true, bypass_allowed:false`; OTP mascarado.
- Promotion Gate sempre bloqueia ação real (faltam credencial real, sessão saudável, flag `PORTAL_REAL_ACTION_ENABLED`, approval, kill switch, eval).

Relatório completo: `docs/canon/design/2026-06-claude-design/43P0-portal-browser-relay-audit-foundation-report.md`.

---

## 9. Critérios de sucesso de longo prazo

A estrutura será considerada forte quando:

1. Corretor faz login uma vez.
2. SessionRef fica saudável por dias/semanas quando o portal permitir.
3. Se expirar, o sistema pede HITL só quando necessário.
4. Portal Skill roda em dry-run e real com trace.
5. Mudança pequena de UI não quebra tudo.
6. Mudança grande gera drift event, não erro silencioso.
7. O agente sabe pedir dado faltante.
8. O agente nunca inventa informação.
9. Ação real sempre tem auditoria e rollback.
10. Novo portal usa mesma infraestrutura, não mini-projeto paralelo.
