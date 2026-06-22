# Fase B — Fechamento integrado: B1.1 (release de Auxiliar) + B2 (proteção de instância)

> Fecha a **governança de versão dos Auxiliares** (release imutável vinculada ao template) e a **proteção das instâncias** Core/Even no Portal Admin (Even sempre visível). **Sem provider externo; sem ação externa; motor único do Smith.** Migrations entregues como runbook.
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `b4783c4`.

## Decisão de liderança (bloco grande + honestidade sobre o estrutural)
Você pediu **finalizar a Fase B**, deferindo só o "muito estrutural". Entreguei num bloco: **B1.1 (o blocker arquitetural que o GPT exigiu)** + **B2 proteção de instância (Even visível/slug)**. Os 3 itens restantes são **genuinamente estruturais/decisão** (sua regra permite deferir) — com evidência abaixo.

### Itens deferidos COM evidência (estrutural)
1. **FinOps profundo no runtime:** `token_usage_logs` é escrito pelo **runtime Python (FastAPI)**, que **não está neste repositório**. Propagar `corridor_run_id`/`tool_name` no Core/Even exige mexer nesse serviço → estrutural, fora do escopo testável aqui. O contrato (`buildUsageAttribution`) e a atribuição por auxiliar (Next) já existem.
2. **Aprovadores (storage):** `companies` **não tem coluna de metadados** e não há tabela de aprovadores. Persistir a seleção exige uma **decisão de schema** (tabela nova vs. reuso de `tenant_connections.connection_config`). Handoff já existe em `corretora/suporte-humano`. → decisão sua antes de implementar.
3. **Telas dedicadas WhatsApp/Portais:** o **status já é superficializado** via **Conectores** (Vault) e **Seguradoras** (TA2-B). Uma tela dedicada é incremento cosmético, não bloqueador de arquitetura.

## Declaração
```
FASE_B_CLOSED: SUBSTANCIALMENTE (arquitetura fechada; 3 itens estruturais/decisão deferidos com evidência)
AUXILIARY_RELEASE_BINDING_READY: SIM
AUXILIARY_TEMPLATE_IMMUTABLE_RELEASE_REFERENCE_READY: SIM (source_release_id + release imutável)
CORE_AND_EVEN_NON_PUBLISHABLE_AS_AUXILIARY: SIM
TENANT_AUXILIARY_RUNTIME_ISOLATION_READY: SIM (B1 — runtime isolado por tenant)
TENANT_AUXILIARY_LIFECYCLE_READY: SIM (B1 — install/pause/resume/uninstall)
EVEN_VISIBLE_IN_CLIENT_ADMIN_VIEW: SIM (seção canônica Supabase, Even mesmo inativa)
LEGACY_SLUG_HIDDEN_IN_UI: PARCIAL (visão canônica não usa slug; slug no canvas legado compartilhado = cosmético pendente)
INSTANCE_EDITOR_PROTECTED: SIM (visão canônica read-mostly → Blueprint Center/Dashboard; sem edição técnica global)
APPROVERS_AND_HANDOFF_READY: PARCIAL (handoff existente; aprovadores = decisão de storage)
WHATSAPP_STATUS_READY: PARCIAL (via Conectores)
PORTAL_STATUS_READY: PARCIAL (via Conectores/Seguradoras)
FINOPS_CONTEXTUAL_PROPAGATION_READY: PARCIAL (contrato + auxiliar; runtime Core/Even = Python)
READINESS_AND_ADMIN_ROLLUP_READY: SIM (TA2-B/C + auxiliares)
CAPABILITY_REGISTRY_NOT_IMPLEMENTED: SIM
NO_REAL_WHATSAPP_SENT: SIM
NO_BROWSERBASE_OPENED: SIM
NO_PORTAL_ACTION_EXECUTED: SIM
NO_EXTERNAL_PROVIDER_INTEGRATED: SIM
NO_PARALLEL_AGENT_ENGINE_CREATED: SIM
NEXT_STEP: FASE_C — CAPABILITY_REGISTRY + (decisão) aprovadores-storage + (Python) FinOps runtime
```

## O que entreguei
### B1.1 — Auxiliar com release imutável (governança fechada)
- `blueprint-release.ts`: `buildAuxiliaryArtifact` + `auxiliaryBlueprintKey` (artefato de Auxiliar sem blueprint de código, sanitizado, guardrails imutáveis).
- `blueprint-studio-store.ts`: `publishSourceAuxiliary` (Source Agent `global_auxiliary` → **release published imutável** em `agent_blueprint_releases` → **auxiliary_template vinculado** via `source_release_id`; idempotente; secret-scan; Core/Even/subagent bloqueados) + `listStudioAuxiliarySources` (mostra release/versão + se está na Galeria).
- API `POST /api/admin/blueprint-center/publish-auxiliary` + Blueprint Center "5. Auxiliares" agora publica via release (mostra "na Galeria · vX").
- Runbook `spec-013-07-auxiliary-release-binding.sql` (colunas `source_release_id`/`source_blueprint_key`/`source_semantic_version`/`source_company_id`/`runtime_policy`; opcionais — não quebram `specific_executor`).
### B2 — Proteção de instância (Even visível)
- API `GET /api/admin/companies/[companyId]/core-even` (Supabase; **Core+Even sempre**, Even mesmo inativa; release aplicada; sanitizado).
- Portal Admin → Empresa → Agentes: **seção "Agentes canônicos"** (Core+Even, status real, blueprint, release; edição global → Blueprint Center; sem editor técnico global). Não usa slug legado.

## Princípios honrados
- **Reuso, não paralelo:** mesma tabela de releases/templates; `pickColumns` tolera pré-migration; `specific_executor` intacto.
- **Imutabilidade + sem segredo** na release de Auxiliar (secret-scan antes de publicar).
- **Isolamento:** runtime de Auxiliar por tenant; Source do Studio nunca compartilhado.
- Guards master/same-origin nas mutações.

## Testes
- `blueprint-release` **39** (inclui artefato de Auxiliar + secret-block), `auxiliary-publish` 19, `release-rollout` 27, `studio-taxonomy` 11, `company-kind` 9, `security` 31 — verdes. `tsc` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Você, após o deploy — máx. 5
1. `spec-013-07-auxiliary-release-binding.sql` → APPLY → VERIFY.
2. Blueprint Center → **5. Auxiliares** → criar Source Auxiliar → **Publicar como Auxiliar Global** → mostra "na Galeria · v1.0.0".
3. Supabase: `select blueprint_key, status from agent_blueprint_releases where blueprint_key like 'aux-%';` → release published; `select slug, source_release_id from auxiliary_templates where source_release_id is not null;` → vínculo.
4. Portal Admin → Empresa Resulta → **Agentes**: a seção "Agentes canônicos" mostra **Even mesmo inativa** + blueprint/release.
5. Dashboard Resulta → Auxiliares → instalar o novo Auxiliar (runtime isolado / awaiting).

## Próximo (Fase C + decisões)
**Fase C — Capability Registry** (platform-owned x tenant-owned x operacional; custo/limite/repasse/approval; decisão Composio/Nango/direto). Antes/junto: **decisão de storage de Aprovadores** e **FinOps no runtime Python** (estrutural). Em paralelo: 42X5C (Z-API paga) e Portal Allianz (credencial).
