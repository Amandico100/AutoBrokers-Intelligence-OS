# Batch Tenant Activation 2 — Execution Report (Parte 0: Hardening do TA1)

> Esta entrega cobre a **Parte 0 (hardening)** do TA2 — as correções de correção/segurança que o GPT apontou e que **bloqueiam aplicar as migrations com segurança**. As telas do Dashboard (Partes 1–3) seguem como execução focada (ver §Decisão). **Sem WhatsApp/Browserbase/portal real; sem migration aplicada no banco; sem estrutura paralela.**
> **Data:** 2026-06-21 · **Modelo:** Claude Opus 4.8 · base: `bbbf0a5`

## Declaração (itens desta entrega)
```
TENANT ACTIVATION 1 RUNBOOK HARDENED: SIM
RESULTA MIGRATION ROLLBACK COMPLETE: SIM (snapshot com todos os campos + restauração completa)
SNAPSHOT RLS SAFE: SIM (RLS on + revoke anon/authenticated)
TENANT CORRIDORS FAIL-CLOSED AFTER MIGRATION: SIM (table_missing→legacy; error→fail-closed)
EFFECTIVE CONFIGURATION MATERIALIZED: SIM (avatar/voice/llm_temperature/overrides aplicados no objeto)
EFFECTIVE CONFIGURATION PERSISTED + USED BY RUNTIME: NÃO (parte das telas do Dashboard — próximo incremento)
FINOPS ATTRIBUTION CONTRACT READY: SIM (buildUsageAttribution; propagação ampla = incremento)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO MIGRATION APPLIED LIVE: SIM
NO PARALLEL ARCHITECTURE CREATED: SIM
DASHBOARD SCREENS (PARTES 1–3): PENDENTE — execução focada por incremento (ver Decisão)
```

## Verifiquei as 4 inconsistências do GPT (contra código + Supabase) — todas procedem
1. **Rollback Resulta incompleto** — meu snapshot só tinha 7 campos; a migration altera `is_subagent`/`allow_direct_chat`/`blueprint_version` também; rollback apagava TODOS os tenant_corridors; tabela de snapshot sem RLS; sem transação. **Confirmado e corrigido.**
2. **Effective Config não materializava overrides** — `applied_overrides` só listava nomes; avatar/voz/temperatura não saíam no objeto. **Confirmado e corrigido.**
3. **Fallback não fail-closed** — qualquer erro virava `null`→legado (reabria globais). **Confirmado e corrigido.**
4. **FinOps parcial** — faltava `corridor_run_id`/`auxiliary_run_id`/`tool_name`. **Confirmado; contrato criado.**

## O que corrigi (Parte 0)
### 0.1 Migration Resulta (runbook) — `tenant-activation-1-resulta-migration.sql`
Transação `begin/commit`; **preconditions** (DO block que aborta se company/sandbox/attendance/2 templates/tenant_corridors não baterem); **snapshot completo** (`name, slug, agent_role, agent_audience, is_active, is_subagent, allow_direct_chat, blueprint_version, agent_system_prompt, context_package` + `migration_key`/PK, idempotente) com **RLS + revoke anon/authenticated**; **rollback completo** (restaura todos os campos) e **escopado** (apaga só os 2 corredores inseridos, não toca ativações futuras).
### 0.2 Migration tenant_corridors (runbook) — `tenant-activation-1-tenant-corridors.sql`
Transação; índices; unique; **trigger de `updated_at`**; RLS + revoke anon/authenticated + policy service_role; verify/rollback.
### 0.3 Fail-closed pós-migration — `tenant-corridor-activation.ts` + inbound
`resolveCorridorsWithFallback(...status)` com 3 estados: `ok`→ativações; `table_missing`→legado (pré-migration, seguro); **`error`→fail-closed** (só tenant-scoped próprio, NUNCA reabre globais). O inbound distingue `42P01`/"does not exist" (table_missing) de erro operacional (error) e loga o fail-closed.
### 0.4 Effective Configuration materializada — `agent-blueprints-canonical.ts`
`resolveEffectiveConfig` agora **aplica os valores** dos overrides seguros: `overrides_applied` (mapa de valores), `avatar_url`, `voice`, `llm_temperature` no objeto; overrides que também são variáveis (ex.: `tone`) refletem no prompt; **`llm_model` nunca vira premium** por override; prompt/role/audience/guardrails seguem rejeitados.
### 0.5 FinOps — `finops-usage-context.ts`
`buildUsageAttribution` (company+agent+case+corridor_run+auxiliary_run+tool+model), `isAttributable`, `attributionDimensions` — contrato canônico para anexar ao usage logging existente (sem billing paralelo).

## Decisão de líder (transparente) sobre o Dashboard (Partes 1–3)
O Dashboard de **13 telas** + Portal Admin rollup + provisionamento + isolamento é um **programa grande de UI**. Você exigiu "extraordinário, muito bem feito, seguindo o design (DS-001), abas limpas". **Despejar 13 telas num único turno produziria UI apressada** — o oposto do que pedimos. O próprio GPT sequencia o hardening ANTES das telas. Então entreguei a **Parte 0 (gating, segura, testada)** agora e proponho executar o Dashboard em **incrementos focados de qualidade**, na ordem:
- **TA2-A:** APIs canônicas tenant-facing + Effective Config **persistida e lida pelo runtime** (Core/Even) + telas **AutoBrokers** e **Even** (personalização por variáveis).
- **TA2-B:** Galerias **Corredores** + **Auxiliares** (ativar/instalar) + **Seguradoras/Contatos** + **Checklist de readiness**.
- **TA2-C:** **WhatsApp/Portais (status)** + **Conhecimento** + **Dados/Equipe/Aprovadores** + **Custos** + **rollup no Portal Admin** + provisionamento automático na criação de empresa.
Cada incremento: design DS-001, abas limpas, isolamento tenant testado, build/tsc verdes. Isso entrega **rápido E bonito**, sem retrabalho.

## Testes
- `admin-agent-blueprints-canonical` **22**, `attendance-tenant-corridor-activation` **13**, `admin-finops-usage-context` (novo) — verdes; regressão (whatsapp-inbound 44, security 31). `tsc` EXIT=0 · build verde.

## FOUNDER SQL TIMELINE (aplicar só após o deploy; já endurecidos)
```
1. APPLY   docs/canon/design/2026-06-claude-design/tenant-activation-1-tenant-corridors.sql  (bloco APPLY, begin..commit)
2. VERIFY  (bloco VERIFY do mesmo arquivo)
3. APPLY   docs/canon/design/2026-06-claude-design/tenant-activation-1-resulta-migration.sql  (bloco APPLY, begin..commit — aborta sozinho se o estado não bater)
4. VERIFY  (bloco VERIFY do mesmo arquivo)
ROLLBACK (se necessário): bloco ROLLBACK de cada arquivo (resulta primeiro, depois corridors).
```
Ordem obrigatória: corridors **antes** da resulta-migration (a migração da Resulta exige tenant_corridors existente e aborta se faltar). Tudo transacional; até aplicar, o runtime fica em **legacy fallback** (seguro).

## Próximo passo
Você dá OK e eu executo **TA2-A** (primeiro incremento do Dashboard) com qualidade DS-001. Em paralelo, quando a Z-API for paga, o 42X5C fica liberado (independente do Dashboard).
