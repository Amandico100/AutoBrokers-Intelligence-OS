# Batch Tenant Activation 1 — Execution Report

> Núcleo canônico conforme SPEC-012. **Sem WhatsApp real, sem Browserbase, sem ação de portal, sem migration aplicada no banco live, sem estrutura paralela.** Migrations entregues como runbook (Founder aplica).
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `6a535f9`

## Declaração
```
CORE BLUEPRINT ROLE-AWARE READY: SIM
ATTENDANCE BLUEPRINT ROLE-AWARE READY: SIM
EFFECTIVE CONFIGURATION READY: SIM
PROVISIONTENANT IDEMPOTENT READY: SIM
SANDBOX BOOTSTRAP NON-DESTRUCTIVE: SIM (skip se Core canônico existe)
RESULTA MIGRATION FILE READY: SIM
RESULTA MIGRATION APPLIED: NÃO — AGUARDA FOUNDER
TENANT_CORRIDORS MIGRATION FILE READY: SIM
TENANT_CORRIDORS APPLIED: NÃO — AGUARDA FOUNDER
GLOBAL CORRIDOR REQUIRES TENANT ACTIVATION: SIM (defensivo: fallback legado até a migration)
RESULTA ALLIANZ RESIDENTIAL + ELETRICISTA READY FOR DRY-RUN: SIM (após aplicar migrations + provisionar)
DISPATCH TARGET GLOBAL WIRED: SIM (dry-run; suggested_dispatch_target no packet)
FINOPS ATTRIBUTION READY: PARCIAL (company_id+agent_id já via credit_transactions; propagação corridor_run_id/auxiliary_run_id = enhancement)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO PARALLEL ARCHITECTURE CREATED: SIM
NEXT STEP: FOUNDER APPLIES MIGRATIONS → DEPLOY → ACCEPTANCE TESTS → 42X5C OU BATCH 2
```

## O que foi implementado (código)
1. **Blueprints role-aware** `lib/admin/agent-blueprints-canonical.ts` (puro): `autobrokers-core-v1` (core/broker_internal, marca "AutoBrokers" travada, apresentação "AutoBrokers da {{company_name}}", ativo) + `even-attendance-v1` (attendance/insured_external, "Even" feminino, **inativo**), com variáveis seguras, guardrails imutáveis e whitelist de overrides.
2. **Effective Configuration** `resolveEffectiveConfig`: compõe blueprint + guardrails + variáveis + overrides seguros; **rejeita** overrides fora da whitelist (ex.: `agent_system_prompt`, `role`, `llm_model` premium); `company_name` imposto pelo sistema (não editável). Renderização de variáveis `{{...}}`.
3. **provisionTenant** `lib/admin/provision-tenant.ts` + rota `POST /api/admin/provision-tenant`: idempotente, garante 1 Core (ativo) + 1 Even (inativa) por empresa; **não** instala corredores/auxiliares; não sobrescreve agente existente do mesmo role. Reusa a tabela `agents`.
4. **Bootstrap não-destrutivo** `app/api/admin/sandbox/bootstrap-tenant`: se já existe Core canônico (`agent_role='core'`), **não sobrescreve** — retorna o Core e aponta para `provision-tenant`. Impede a regressão Core→Sandbox.
5. **Ativação por tenant (runtime)** `lib/attendance/tenant-corridor-activation.ts` (puro) + alteração **defensiva** em `loadAvailableCorridors` (inbound): corredor global só opera se houver `tenant_corridors` ativo; **se a tabela não existir ainda, fallback legado** (não quebra). Tenant-scoped continua isolado.
6. **Dispatch usando contatos globais** (dry-run): `dispatch-dry-run` anexa `suggested_dispatch_target` via `resolveInsurerDispatchTarget` (residencial/eletricista → WhatsApp da assistência, fallback 24h). Não envia.

## Migrations (runbook — NÃO aplicadas)
- `docs/canon/design/2026-06-claude-design/tenant-activation-1-tenant-corridors.sql` — tabela `tenant_corridors` (+ índices, RLS service_role, unique company+template) · APPLY/VERIFY/ROLLBACK.
- `docs/canon/design/2026-06-claude-design/tenant-activation-1-resulta-migration.sql` — Resulta: Sandbox→**AutoBrokers Core** (mesmo `agent_id`, snapshot p/ rollback), attendance→**Even** (inativa), e **ativa** Allianz Residencial + Eletricista em `tenant_corridors` · APPLY/VERIFY/ROLLBACK.

> **Ordem de aplicação:** 1º `tenant-corridors.sql`, 2º `resulta-migration.sql`. Sem isso, o runtime fica em fallback legado (comportamento atual) — seguro.

## Segurança
- Nada real enviado/aberto; gates `false`; Even nasce inativa; nenhuma flag ligada.
- Overrides perigosos rejeitados (whitelist); marca AutoBrokers travada; `company_name` imposto.
- Mudança de runtime é **defensiva** (fallback) → não quebra antes da migration.
- Migrations não aplicadas automaticamente; snapshot/rollback fornecidos.

## Testes
- Novos: `admin-agent-blueprints-canonical` **19**, `attendance-tenant-corridor-activation` **10**.
- Regressão: insurer-contacts 22, whatsapp-inbound 44, action-outbox 42, security 31, company-scope 19.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Migrations que o Founder deve aplicar (passo único)
1. SQL editor do Supabase → rodar `tenant-activation-1-tenant-corridors.sql` (APPLY) → VERIFY.
2. Rodar `tenant-activation-1-resulta-migration.sql` (APPLY) → VERIFY (Resulta com AutoBrokers Core + Even; corredores ativos).
3. Deploy do código (já no main).
4. (Empresas novas) chamar `POST /api/admin/provision-tenant {companyId}` para nascerem com Core+Even.

## 5 testes live para o Founder (após deploy + migrations)
1. **Provisionar empresa nova:** `POST /api/admin/provision-tenant {companyId}` → retorna Core criado + Even criada (inativa). Repetir → `exists` (idempotente).
2. **Resulta no Portal Admin:** Empresas → Resulta → Agentes → ver **AutoBrokers** (Core, ativo) + **Even** (inativo); o "AutoBrokers Sandbox" sumiu (virou Core, mesmo id).
3. **Ativação por tenant:** `GET` corredores de uma empresa SEM ativação não operam; Resulta opera Allianz Residencial/Eletricista (dry-run via simulate-inbound).
4. **Dispatch global:** rodar `dispatch-dry-run` num caso Allianz → `dispatch_packet.suggested_dispatch_target` traz o WhatsApp de assistência correto; nada enviado.
5. **Bootstrap não-destrutivo:** chamar bootstrap-tenant na Resulta → resposta `core_exists_skip_sandbox` (não recria Sandbox).

## Itens restantes (honestos)
- **FinOps:** `company_id`+`agent_id` já são atribuídos no custo (`credit_transactions.agent_id`). A propagação de `corridor_run_id`/`auxiliary_run_id` no log de uso é um enhancement (não bloqueia atribuição por empresa/agente). [próximo, pequeno]
- **provisionTenant via blueprint vs migration:** a migration da Resulta inlina os prompts (Sandbox→Core) para preservar o `agent_id`; empresas novas usam `provisionTenant` (blueprints). Ambos consistentes.

## Próximo passo
Founder aplica as 2 migrations + deploy + testes de aceite. Depois: **42X5C** (canary WhatsApp, se Z-API paga) **ou** **Batch Tenant Activation 2** (Dashboard da corretora). Recomendo Batch 1 → 42X5C → Batch 2.
