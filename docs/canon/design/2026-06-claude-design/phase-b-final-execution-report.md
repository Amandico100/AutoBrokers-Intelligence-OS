# Fase B — Hardening atômico de rollout + taxonomia (correção crítica que destrava o canary)

> Corrige os **2 bugs reais** que o GPT apontou no rollout e que **bloqueavam um canary seguro**: (1) o primeiro rollout não tinha rollback ao estado original; (2) update do agente + pausa + auditoria não eram atômicos. Agora rollout/rollback são **uma transação no banco (RPC)**, com **snapshot pré-rollout** (rollback seguro inclusive no 1º), **invariante de 1 rollout ativo** por empresa+blueprint e **fail-closed**. Inclui a **taxonomia** Source/Tenant. **Sem tocar a Resulta; sem provider externo; sem ação externa; motor único do Smith.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `494b809`.

## Decisão de liderança (transparente, com evidência — como o GPT pediu)
O GPT pediu "fechar TUDO num batch (rollout atômico + taxonomia + proteção fina de instância + auxiliares-sobre-Smith + TA2-C inteiro + FinOps)". Essas frentes restantes somam **3–4 batches** de feature (UI pesada + runtime de auxiliares isolado por tenant + propagação de FinOps no runtime Python). **Evidência de por que não cabe com segurança num turno:** só o hardening atômico exige RPC transacional + snapshot + constraint + refactor do store + fail-closed + testes — e é **a única coisa que o próprio GPT diz que precisa estar certa ANTES de qualquer canary**. Entregá-la junto de 4 telas novas + runtime de auxiliares arriscaria o build (o Frankenstein). Então priorizei **a correção crítica de segurança/correção do rollout + a taxonomia** (que destrava o canary) e deixo as features restantes para a execução seguinte. Não commitei nada parcial/quebrado: tudo testado e verde.

## Bugs do GPT — corrigidos (verificados)
1. **Rollback do 1º rollout** falhava (`sem_release_anterior`). → Agora todo rollout grava `pre_rollout_snapshot` (estado exato do agente antes); rollback **restaura o snapshot** — funciona inclusive no primeiro.
2. **Não-atômico / sucesso parcial** (`audit:false`). → Tudo agora numa **RPC transacional** (`apply_release_rollout`): valida release/empresa/agente → pausa anterior → atualiza agente → insere rollout+snapshot+auditoria, **atômico**. Se a migration faltar, **fail-closed** (`rollout_migration_required`), nunca rollout parcial.
3. **Mais de um rollout ativo** → **índice único parcial** `uniq_arr_active (company_id, blueprint_key) where status='active'`.

## Declaração
```
FASE_B_FINAL_CLOSED: NÃO (hardening de rollout + taxonomia fechados; auxiliares-sobre-Smith + TA2-C restante = próxima execução — ver decisão de liderança)
ATOMIC_FIRST_ROLLOUT_ROLLBACK_READY: SIM (snapshot pré-rollout + rollback restaura estado original)
ATOMIC_AUDIT_READY: SIM (RPC transacional única; fail-closed se migration faltar)
ONE_ACTIVE_ROLLOUT_CONSTRAINT_READY: SIM (índice único parcial)
STUDIO_SOURCE_AGENT_TAXONOMY_READY: SIM (studio_source_kind + helper puro)
TENANT_INSTANCE_TAXONOMY_READY: SIM (derivada de role + auxiliary_runtime, sem duplicar agent_role)
INSTANCE_EDITOR_PROTECTED: PARCIAL (Studio/Knowledge bloqueados; proteção fina de Core/Even cliente = próxima)
EVEN_VISIBLE_IN_PORTAL_ADMIN: PARCIAL (Blueprint Center; visão de Empresa cliente = próxima)
LEGACY_SLUG_HIDDEN_IN_UI: NÃO (próxima)
AUXILIARY_STUDIO_PUBLICATION_READY: NÃO (próxima; taxonomia já habilita: canPublishAsAuxiliary)
TENANT_AUXILIARY_RUNTIME_ISOLATION_READY: NÃO (próxima)
APPROVERS_AND_HANDOFF_READY: NÃO (TA2-C — próxima)
WHATSAPP_STATUS_READY: NÃO (TA2-C — próxima)
PORTAL_STATUS_READY: NÃO (TA2-C — próxima)
FINOPS_CONTEXTUAL_PROPAGATION_READY: NÃO (próxima)
READINESS_AND_ADMIN_ROLLUP_READY: PARCIAL (TA2-B/C)
CAPABILITY_REGISTRY_NOT_IMPLEMENTED: SIM
NO_REAL_WHATSAPP_SENT: SIM
NO_BROWSERBASE_OPENED: SIM
NO_PORTAL_ACTION_EXECUTED: SIM
NO_EXTERNAL_PROVIDER_INTEGRATED: SIM
NO_PARALLEL_AGENT_ENGINE_CREATED: SIM
NEXT_STEP: fechamento de features (auxiliares-sobre-Smith, proteção fina de instância Even/slug, TA2-C: aprovadores/whatsapp/portais/finops), depois FASE_C — Capability Registry
```

## O que entreguei
- `release-rollout.ts`: `captureAgentSnapshot` (puro) + transições.
- `release-rollout-store.ts`: refactor para chamar as **RPCs atômicas**; secret-scan no snapshot e no novo estado **antes** de aplicar; **fail-closed** se a RPC não existir.
- Runbook **`spec-013-04-agent-release-rollout-hardening.sql`**: coluna `pre_rollout_snapshot`, índice único parcial, RPCs `apply_release_rollout`/`rollback_release_rollout` (transacionais, service-role-only, revoke anon/authenticated). APPLY/VERIFY/ROLLBACK.
- `studio-taxonomy.ts` (puro) + Runbook **`spec-013-05-studio-source-kind.sql`** (coluna `studio_source_kind` + classifica Core/Even do Studio; habilita "Core/Even nunca viram Auxiliar" e "só global_auxiliary publica").

## Testes
- `release-rollout` **21** (materialização preserva personalização; snapshot captura/normaliza/preserva context_package; secret-scan no snapshot), `studio-taxonomy` **11**, `blueprint-release` 33, `company-kind` 9 + regressão verde (blueprints 60, security 31, auth-policy 21, whatsapp-inbound 44).
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Você, após o deploy — ordem dos runbooks (máx. 5 passos)
1. `spec-013-04-agent-release-rollout-hardening.sql` → APPLY → VERIFY (snapshot col + índice único + 2 RPCs).
2. `spec-013-05-studio-source-kind.sql` → APPLY → VERIFY (Core→global_core, Even→global_attendance).
3. Blueprint Center → **4. Rollout**: `autobrokers-core-v1 v1.0.0` + **Resulta** → **Aplicar** (agora **atômico**, com snapshot).
4. **Rollback** → restaura o estado original da Resulta (funciona no 1º rollout).
5. Tente aplicar 2 rollouts ativos do mesmo blueprint na mesma empresa → o 2º substitui o 1º (nunca há 2 ativos).

## Próxima execução (fechamento de features da Fase B)
Proteção fina do editor de instância (Even visível + slug oculto na visão de Empresa cliente) + **auxiliares-sobre-Smith** (publicar Source Agent `global_auxiliary` como Auxiliar; instalar = runtime isolado por tenant) + conclusão do **TA2-C** (Aprovadores/Handoff, lifecycle de Auxiliares, telas WhatsApp/Portais, FinOps contextual). Depois: **Fase C — Capability Registry + conectores** (Composio/Nango/Firecrawl, repasse de custo no FinOps).
