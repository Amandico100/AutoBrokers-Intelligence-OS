# Fase B — Rollout correto e final (compatibilidade no banco + rollback em cadeia)

> Conclui a **correção do rollout** (o bloqueador explícito antes de qualquer canary): a RPC agora valida compatibilidade `blueprint_key`/`role`/`audience` **no próprio Postgres**, serializa com `FOR UPDATE`, recusa snapshot com chave de segredo, e o **rollback em cadeia reativa a versão anterior** (no 1º rollout volta ao estado original sem ativo). **Sem tocar a Resulta; sem provider externo; sem ação externa; motor único do Smith.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `c29c37b`.

## Decisão de liderança — evidência objetiva (como o GPT pediu)
O GPT pediu "fechar TUDO": correção do rollout + proteção fina de instância + auxiliares-sobre-Smith + 4 telas do TA2-C + FinOps. Entreguei a **correção do rollout** (esta execução) por ser a peça crítica que precede o canary. **Por que o resto não cabe com segurança no mesmo turno (evidência):**
- **Proteção fina de instância / Even visível:** a tela `app/admin/companies/[companyId]/agents` busca agentes do **backend Python** (`/api/admin/agents/company/[id]/with-delegations`), que (pelo próprio diagnóstico anterior) **lista só `is_active=true`** — a Even é inativa. Mostrar a Even ali exige mudança no backend Python, fora do escopo testável deste runtime sem risco.
- **Auxiliares-sobre-Smith (runtime isolado por tenant):** exige fluxo de publicação + instalação criando agente/subagent Smith real no tenant + UI de lifecycle — feature grande, multi-arquivo.
- **TA2-C (Aprovadores/WhatsApp/Portais/FinOps):** 4 superfícies novas + propagação de FinOps no runtime.
Esses itens somam **2–3 batches**; juntá-los à correção do rollout arriscaria o build (o Frankenstein). Proposta objetiva de sequência no fim deste relatório. **Nada parcial/quebrado foi commitado.**

## Correções do GPT — implementadas
1. **Compatibilidade no banco:** `apply_release_rollout` valida `release.blueprint_key = p_blueprint_key`, `artifact.role = agent.agent_role`, `artifact.audience = agent.agent_audience`, empresa `client`, release `published` — tudo no Postgres (não só TS).
2. **Rollback em cadeia:** `rollback_release_rollout` restaura o snapshot **e reativa o rollout anterior** (`paused → active`) quando existir; no 1º rollout volta ao original e fica sem ativo. Nunca deixa o agente restaurado sem histórico coerente.
3. **Serialização:** `FOR UPDATE` na instância e no rollout ativo (sem corrida/duplicação) — mantendo o índice único parcial de 1 ativo.
4. **Guarda de segredo no banco:** snapshot com `token/secret/api_key/authorization/cookie/password/refresh_token/sessionref/storagestate/connecturl` é recusado pela RPC.

## Declaração
```
ATOMIC_FIRST_ROLLOUT_ROLLBACK_READY: SIM
ROLLOUT_CHAIN_ROLLBACK_READY: SIM (reativa versão anterior)
DATABASE_COMPATIBILITY_VALIDATION_READY: SIM (blueprint_key/role/audience na RPC)
ONE_ACTIVE_ROLLOUT_CONSTRAINT_READY: SIM
SNAPSHOT_SECRET_GUARD_DB_READY: SIM
SOURCE_TAXONOMY_READY: SIM
INSTANCE_EDITOR_PROTECTED: PARCIAL (Studio/Knowledge bloqueados; Core/Even cliente = próxima, bloqueio no backend Python)
EVEN_VISIBLE_IN_PORTAL_ADMIN: PARCIAL (Blueprint Center; visão de Empresa cliente depende do backend Python = próxima)
LEGACY_SLUG_HIDDEN_IN_UI: NÃO (próxima)
AUXILIARY_STUDIO_PUBLICATION_READY: NÃO (próxima)
TENANT_AUXILIARY_RUNTIME_ISOLATION_READY: NÃO (próxima)
APPROVERS_AND_HANDOFF_READY: NÃO (próxima)
WHATSAPP_STATUS_READY: NÃO (próxima)
PORTAL_STATUS_READY: NÃO (próxima)
FINOPS_CONTEXTUAL_PROPAGATION_READY: NÃO (próxima)
CAPABILITY_REGISTRY_NOT_IMPLEMENTED: SIM
NO_REAL_WHATSAPP_SENT: SIM
NO_BROWSERBASE_OPENED: SIM
NO_PORTAL_ACTION_EXECUTED: SIM
NO_EXTERNAL_PROVIDER_INTEGRATED: SIM
NO_PARALLEL_AGENT_ENGINE_CREATED: SIM
NEXT_STEP: fechamento de features (instância Python + auxiliares-sobre-Smith + TA2-C), depois FASE_C
```

## O que entreguei
- Runbook **`spec-013-06-rollout-chain-compatibility-hardening.sql`** (CREATE OR REPLACE das 2 RPCs com compatibilidade + cadeia + FOR UPDATE + guarda de segredo; APPLY/VERIFY/ROLLBACK).
- `release-rollout.ts`: helpers puros `decideRollbackAction` (espelha a cadeia) e `isRolloutCompatible` (espelha a validação). O store **não muda** (chama as mesmas RPCs, agora mais corretas) → baixo risco.

## Testes
- `release-rollout` **27** (materialização preserva personalização; snapshot; secret-scan; **rollback em cadeia**; **compatibilidade blueprint/role/audience**). Regressão verde (blueprint-release 33, studio-taxonomy 11, company-kind 9, blueprints 60, security 31).
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Você, após o deploy (máx. 5)
1. `spec-013-06-rollout-chain-compatibility-hardening.sql` → APPLY → VERIFY.
2. Blueprint Center → **4. Rollout**: `autobrokers-core-v1 v1.0.0` + **Resulta** → **Aplicar** (v1 active).
3. (Opcional) publique v1.1.0 e aplique → v1 vira `paused`, v1.1.0 `active`.
4. **Rollback** → restaura o estado de v1 **e** v1 volta a `active` (cadeia coerente).
5. Tente aplicar uma release de `even-attendance-v1` numa instância core → **bloqueado** (`role_incompativel`).

## Plano objetivo do que falta (sequência recomendada)
1. **Feature-close A:** auxiliares-sobre-Smith (publicar Source Agent `global_auxiliary` → instalar = runtime isolado por tenant) + lifecycle UI tenant.
2. **Feature-close B:** proteção fina de instância (inclui ajuste no backend Python para listar Core/Even inativos + esconder slug) + Aprovadores/Handoff.
3. **Feature-close C:** telas WhatsApp/Portais (status honesto) + FinOps contextual + readiness/rollup final.
4. **Fase C:** Capability Registry + conectores (Composio/Nango/Firecrawl) + repasse de custo.
