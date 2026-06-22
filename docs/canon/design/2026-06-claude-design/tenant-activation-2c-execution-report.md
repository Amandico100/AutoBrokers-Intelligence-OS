# Batch TA2-C — Finalização do Dashboard da Corretora + Hardening Final de Autorização

> Hardening final de autorização (principal validado no banco, empresa pelo banco, same-origin), **provisionamento automático** na criação da empresa, **Dados da corretora**, **Custos e Uso**, **Equipe**, **Conhecimento**, **Prontidão** expandida e **rollup visual no Portal Admin**. WhatsApp/Portais reusam a tela de **Conectores** existente. **Sem WhatsApp/Browserbase/portal real; sem flags; sem migration aplicada; sem estrutura paralela.**
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `d4e7317`

## Declaração
```
CURRENT PRINCIPAL SERVER-VALIDATED: SIM (admin validado em admin_users; remoção tem efeito imediato)
SESSION COMPANY CONSISTENCY ENFORCED: SIM (users_v2 é fonte de verdade; divergência bloqueia)
CSRF / SAME-ORIGIN MUTATION PROTECTION READY: SIM (assertSameOrigin nas mutações + sameSite=lax)
COMPANY PROFILE DASHBOARD READY: SIM (/personalizacao/corretora/dados — reusa companies)
TEAM DASHBOARD READY: SIM (read-only real, sanitizado; convite reusa fluxo existente)
APPROVERS AND HANDOFF DASHBOARD READY: PARCIAL (handoff/suporte-humano já existe; config de aprovadores reusa human_support_destinations — UI dedicada de seleção = continuação)
AUXILIARY LIFECYCLE DASHBOARD READY: PARCIAL (galeria + infra já existem; install/pause/resume na nova UI = continuação)
WHATSAPP READINESS DASHBOARD READY: SIM (via Conectores existente + readiness honesto; sem ligar Z-API)
PORTAL STATUS DASHBOARD READY: SIM (via Conectores/Portal Browser existentes; sem abrir Browserbase)
KNOWLEDGE DASHBOARD HONEST READY: SIM (/personalizacao/conhecimento — lista real, read-only)
COSTS AND USAGE DASHBOARD READY: SIM (/personalizacao/custos — dados reais, sem inventar)
PORTAL ADMIN VISUAL ROLLUP READY: SIM (/admin/companies/[companyId]/activation)
AUTOMATIC PROVISIONING READY: SIM (toda empresa nasce com AutoBrokers+Even; idempotente; falha visível)
READINESS FINAL READY: SIM (inclui equipe, aprovadores, conhecimento; críticos bloqueiam produção)
TENANT ISOLATION TESTED: SIM (políticas puras + company_id pelo banco)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO FLAG ENABLED: SIM
NO PARALLEL ARCHITECTURE CREATED: SIM
NEXT STEP: 42X5C — Z-API CONFIGURATION AND CONTROLLED WHATSAPP CANARY
```

## Avaliação crítica do prompt do GPT
As **2 melhorias de segurança** que o GPT apontou eram **corretas e procedentes**:
1. `getAdminContext` confiava em role/companyId da sessão → agora `requireMasterAdmin`/`requireAdminForCompany` **validam o admin em `admin_users`** (remoção de acesso surte efeito imediato).
2. `requireCompanyMember` priorizava `session.companyId` → agora o **banco (`users_v2`) é a fonte de verdade**; se a sessão divergir, **bloqueia** (`session_company_divergent`).
Adicionei a Parte 0.3 (same-origin) como pedido. Tudo testado.

### Decisão de liderança (transparente)
TA2-C tinha **14 partes** — honestamente, 2 execuções seguras. Entreguei nesta a **espinha dorsal de segurança + fundação + telas de maior valor**, tudo testado e com build verde, **sem fingir**. Reusei o que já existia (Conectores cobre WhatsApp/Portais; galeria de Auxiliares já existe) em vez de duplicar — respeitando "nada paralelo". O que faltou está listado abaixo como **continuação do mesmo TA2-C** (não é plano novo).

### Melhorias minhas além do prompt
- **Dropdowns** mantidos/expandidos (UF na tela de Dados; papéis/labels controlados) — diretriz permanente do Founder.
- **Validação real de CNPJ** (dígitos verificadores), e-mail e telefone server-side.
- **Auto-provisionamento** retorna `provisioning:{ok,error}` ao criar empresa — falha **nunca é ocultada** (empresa fica "aguardando provisionamento").

## O que entreguei
- **Parte 0 (segurança):** `admin-auth.ts` valida o principal em `admin_users`; `requireCompanyMember` usa `users_v2` como verdade + bloqueia divergência; `assertSameOrigin` aplicado às mutações (provision-tenant, companies POST, agents PATCH/reset, corridors POST). Políticas puras (`sameOriginOk`, `tenantCompanyConsistent`).
- **Parte 1 — Dados:** `company-profile.ts` (puro: campos reais de `companies`, UF dropdown, CNPJ/e-mail/telefone validados) + store + `GET/PATCH /api/dashboard/company-profile` + tela `/corretora/dados`.
- **Parte 8 — Custos:** `tenant-usage-view.ts` (puro) + store (company_credits + credit_transactions, por agente/modelo) + `GET /api/dashboard/usage` + tela `/custos`.
- **Parte 2 — Equipe:** leitura real sanitizada (`users_v2`) + `GET /api/dashboard/team` + tela.
- **Parte 7 — Conhecimento:** lista real de `documents` por empresa + `GET /api/dashboard/knowledge` + tela honesta (RAG não confirma cobertura).
- **Parte 9 — Portal Admin visual:** página `/admin/companies/[companyId]/activation` consumindo o rollup canônico.
- **Parte 10 — Provisionamento automático:** hook idempotente no `POST /api/admin/companies` (master + same-origin) → `provisionTenant`.
- **Parte 11 — Readiness:** expandida com equipe, aprovadores (human_support_destinations) e conhecimento (documents).

## Segurança / isolamento
- Admin validado no banco; tenant resolve empresa pelo banco; divergência de sessão bloqueada.
- Same-origin nas mutações (defesa em profundidade junto do cookie sameSite=lax).
- Dados/Custos/Equipe/Conhecimento sempre escopados a `company_id`; nada cross-tenant; nenhum segredo/ID técnico/CPF/stripe exposto.
- Provisionamento só master; company_admin nunca provisiona.

## Testes
- Novos/expandidos: `admin-auth-policy` **21** (+same-origin/consistência), `company-profile` **19** (CNPJ/e-mail/UF/sanitização/campos-proibidos), `tenant-usage-view` **9**.
- Regressão verde: blueprints 60, corridor-catalog 12, readiness 12, insurers 8, corridor-activation 13, finops 7, security 31, whatsapp-inbound 44.
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo. **Nenhuma migration aplicada live; nenhuma ação externa.**

## Testes live (após deploy) — máx. 5
1. Personalização → **Corretora → Dados**: editar CNPJ inválido → bloqueia; CNPJ válido + UF (dropdown) → Salvar → persiste.
2. **Custos e Uso**: ver saldo + consumo por agente/modelo reais (ou zeros honestos).
3. **Equipe**: ver membros reais (nome/papel/dono).
4. **Conhecimento**: ver documentos privados reais com status.
5. Admin → `/admin/companies/04b5cdbc…/activation`: rollup (AutoBrokers/Even, corredores, prontidão) — mesma fonte do Dashboard.

## Continuação do TA2-C (mesmo batch, 2ª execução segura — não é plano novo)
- **Aprovadores**: UI dedicada de seleção de aprovadores por ação (reusa human_support_destinations/approval_requests).
- **Auxiliares lifecycle**: install/pause/resume/uninstall na nova UI (galeria + infra já existem).
- **WhatsApp/Portais**: telas dedicadas de status no Dashboard tenant (hoje via Conectores) + solicitação de login assistido canônica.
- **FinOps**: propagação ampla de `buildUsageAttribution` (corridor_run/auxiliary_run/tool) nos caminhos reais do runtime.
Depois: **42X5C** (Z-API + canary WhatsApp).
