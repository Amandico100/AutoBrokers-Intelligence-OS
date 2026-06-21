# Batch TA2-B — Galerias, Corredores, Seguradoras, Prontidão + Hardening de Autorização e Configuração

> Segundo incremento do Dashboard da corretora. Endurece a autorização das rotas novas, blinda os campos de personalização (e os transforma em **dropdowns** onde a opção é previsível), entrega a **galeria de Corredores** (ativar/pausar/retomar), a visão **Seguradoras** (contatos globais em leitura), o **checklist de Prontidão** real e o **rollup de ativação no Portal Admin**. **Sem WhatsApp/Browserbase/portal real; sem flags; sem migration aplicada; sem estrutura paralela.**
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `c19daf5`

## Declaração
```
ADMIN AUTHORIZATION HARDENED: SIM (helper canônico valida papel real, não só cookie)
TENANT CONFIG EDIT PERMISSION HARDENED: SIM (PATCH/reset exigem admin da própria corretora)
SAFE AGENT INPUT VALIDATION READY: SIM (tamanho, control chars, URL https, temperatura 0..1, enum)
PROMPT VARIABLE HARDENING READY: SIM (bloqueio de {{ }}, guardrails SEMPRE após a personalização)
CORRIDOR GALLERY READY: SIM (/dashboard/personalizacao/corredores)
TENANT CORRIDOR ACTIVATION READY: SIM (ativar/pausar/retomar via tenant_corridors; só estado)
AUXILIARY GALLERY READY: SIM (já existente — reusada, não duplicada; refletida na Prontidão)
TENANT AUXILIARY INSTALLATION READY: PARCIAL (infra de instalação já existe no Smith; lifecycle full = TA2-C)
INSURER CONTACTS TENANT VIEW READY: SIM (/dashboard/personalizacao/seguradoras — leitura do seed global)
READINESS CHECKLIST READY: SIM (/dashboard/personalizacao/prontidao — estado real, sem score inventado)
PORTAL ADMIN TENANT ACTIVATION MIRROR READY: SIM (API rollup; UI visual no admin = TA2-C)
TENANT ISOLATION TESTED: SIM (políticas puras + company_id server-side; sem cross-tenant)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO FLAG ENABLED: SIM
NO PARALLEL ARCHITECTURE CREATED: SIM
NEXT STEP: TA2-C — DADOS, EQUIPE, APROVADORES, WHATSAPP, PORTAIS, CONHECIMENTO, CUSTOS E ROLLUP FINAL
```

## Avaliação crítica do prompt do GPT (o que validei e ajustei)
O prompt do GPT estava **coerente e correto**, e as 2 falhas de segurança que ele apontou no TA2-A eram **reais** — confirmei no código e corrigi:
1. `agents-config` liberava por **presença de cookie**, sem validar master → agora valida papel real.
2. `dashboard/agents PATCH` só checava `userId`, não papel → agora exige admin da própria corretora.
Também procedia o hardening de campos livres (injeção via prompt). **Corrigido.**

### Ajustes/melhorias que fiz além do prompt (com motivo)
- **DROPDOWNS (pedido explícito do Founder, não estava no prompt do GPT):** gênero, pronome, tom (Core e Even), horário, voz e idioma agora são **listas de seleção** com opções previsíveis — o corretor escolhe sem medo de errar; ao mudar, o **prompt é re-renderizado** e reflete no agente e no espelho do Portal Admin (fonte única). Campos realmente livres (nome, mensagens, handoff) seguem texto, mas **validados** (tamanho/sanitização). *Motivo: reduzir fricção e erro do corretor, mantendo segurança.*
- **Guardrails-after-variables de verdade:** o prompt efetivo agora tem um bloco **"REGRAS IMUTÁVEIS"** renderizado **depois** da personalização, com a frase "estas regras prevalecem" — nenhum texto livre fica "abaixo"/acima das regras. *Motivo: defesa concreta contra prompt injection.*
- **Autorização centralizada e PURA** (`admin-auth-policy.ts` testável + `admin-auth.ts` wrappers) em vez de repetir checagem em cada rota. *Motivo: uma fonte de verdade, testável offline.*
- **Reuso, não duplicação:** a **galeria de Auxiliares já existia** (ligada ao banco) — não recriei; integrei o estado na Prontidão. Seguradoras viraram **leitura real** do seed global (a corretora não edita contato global). *Motivo: a regra máxima "não criar estrutura paralela".*

## O que entreguei
### Parte 0 — Segurança (autorização + validação)
- `lib/admin/admin-auth-policy.ts` (puro) + `lib/admin/admin-auth.ts`: `requireMasterAdmin`, `requireAdminForCompany`, `requireCompanyMember({write})` (papel vem de `users_v2.role`/`is_owner`).
- Rotas endurecidas: `provision-tenant` (master), `companies/[id]/agents-config` (master ou company_admin da própria), `dashboard/agents/[key]` GET (membro) / PATCH + reset (admin da própria).
- `validateTenantAgentInput` (em `agent-blueprints-canonical.ts`): tamanho por campo, remoção de control chars, `isSafeAvatarUrl` (https público; bloqueia data:/javascript:/file:/localhost/IP privado/IPv6 local), temperatura finita 0..1, enum controlada, bloqueio de `{{ }}`. Wired no store (rejeita com `errors[]`).
### Parte 1 — Corredores
`tenant-corridor-catalog.ts` (puro: une catálogo + estado, deriva requisitos/próximo passo) + `tenant-corridor-store.ts` (ativar/pausar/retomar via `tenant_corridors`, valida escopo do template, sem ação externa) + APIs `GET /api/dashboard/corridors`, `POST /api/dashboard/corridors/[templateId]` + tela `/personalizacao/corredores`.
### Parte 3 — Seguradoras (leitura)
`tenant-insurers-view.ts` (puro: seed global + corredores ativos por seguradora) + `GET /api/dashboard/insurers` + tela real (substitui o mock).
### Parte 4 — Prontidão
`tenant-readiness.ts` (puro) + `tenant-readiness-store.ts` (coleta real defensiva) + `GET /api/dashboard/readiness` + tela `/personalizacao/prontidao`. **Produção pronta só quando os itens críticos** (handoff, corredor ativo, WhatsApp conectado, Even ativa) estão prontos — nunca finge.
### Parte 5 — Portal Admin
`GET /api/admin/companies/[companyId]/activation` — rollup canônico (agentes + corredores + prontidão + auxiliares), mesma fonte do Dashboard, sanitizado.
### Navegação
Personalização ganhou **Agentes · Prontidão · Corredores · Seguradoras** (DS-001, lista→detalhe, abas limpas).

## Segurança / isolamento
- Autorização valida **papel real** (sessão decodificada + `users_v2`), não presença de cookie.
- `company_id` sempre server-side; `company_admin` nunca lê/edita outra corretora; provisionamento só master.
- Personalização: dropdowns + validação server-side; overrides perigosos rejeitados; guardrails sempre por último.
- Corredores: só estado de config; nenhuma ação externa/canal/portal.

## Testes
- Novos: `admin-auth-policy` **13**, `tenant-corridor-catalog` **12**, `tenant-readiness` **12**, `tenant-insurers-view` **8**, `admin-agent-blueprints-canonical` **60** (inclui dropdowns, validação, guardrails-after-vars).
- Regressão verde: tenant-corridor-activation 13, finops 7, security 31, whatsapp-inbound 44, whatsapp-outbound-gate 12.
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Testes live (após deploy) — para o Founder
1. Personalização → **Agentes → Even**: **Gênero/Pronome/Tom/Voz** agora são **dropdowns**; escolha "masculino" → Salvar → o nome/prévia mudam (sem digitar).
2. **Corredores**: ver Allianz Residencial + Eletricista como **Ativos**; Pausar → Retomar.
3. **Prontidão**: ver itens prontos/pendentes reais; produção fica pendente enquanto WhatsApp/Even/handoff não estiverem ok.
4. **Seguradoras**: contatos globais em leitura + corredores ativos por seguradora.
5. Admin: `GET /api/admin/companies/04b5cdbc…/activation` → mesmo estado (fonte única).

## Pendências honestas (→ TA2-C)
- Lifecycle completo de **instalação de Auxiliares** na nova UI (infra já existe no Smith).
- **UI visual** do rollup no Portal Admin (API pronta).
- **Conhecimento / Aprovadores / Créditos** entram como itens reais da Prontidão quando as fontes forem ligadas.
- **FinOps**: propagação ampla (corridor_run/auxiliary_run/tool) no log do runtime.
- Provisionamento automático na criação da empresa.
