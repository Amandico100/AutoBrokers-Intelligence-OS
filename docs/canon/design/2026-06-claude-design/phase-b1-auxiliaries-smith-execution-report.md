# Fase B1 — Auxiliares Globais sobre o runtime Smith (reuso do motor + gaps fechados)

> **Auditoria primeiro (regra "sem estrutura paralela"):** o motor de Auxiliares já existe e é canônico (SPEC-002) — `from-agent` publica um agente como template com `runtime.kind='smith_agent_blueprint'` + blueprint sanitizado; o `install` **já cria um Agent Smith ISOLADO na corretora**. Em vez de recriar, **fechei os gaps reais do SPEC-013** reusando esse motor. **Sem provider externo; sem ação externa; sem migration (reusa jsonb); motor único do Smith.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `8cc9875`.

## Decisão de liderança (bloco maior, como você pediu — e sem Frankenstein)
Você pediu **blocos maiores, menos idas e voltas**. Entreguei o **B1 inteiro num turno**, mas **reusando** o que já existe (não recriei o motor de auxiliares — isso evita o Frankenstein). Os gaps reais vs SPEC-013 eram 3, e foram fechados:

1. **Guard de publicação:** Auxiliar **global** só nasce de um **Source Agent do Studio `global_auxiliary`**. Core/Even e agentes de cliente **nunca** viram Auxiliar global (validado no `from-agent`).
2. **Autoria no Studio:** criar **Source Auxiliar** no Blueprint Center (motor Smith, inativo) + **publicar como Auxiliar Global** (1 clique, reusa `from-agent`).
3. **Lifecycle por corretora:** galeria tenant com **instalar / pausar / retomar / desinstalar** + status honesto; instalar cria **runtime Smith isolado** (reusa o `install` canônico) ou fica **"aguardando configuração"** (honesto) se o backend não estiver disponível.

## Declaração
```
SOURCE_AUXILIARY_CREATION_READY: SIM (Blueprint Center → 5. Auxiliares → Criar Source Auxiliar)
SOURCE_SUBAGENT_CREATION_READY: PARCIAL (taxonomia source_subagent pronta; UI dedicada = futuro)
AUXILIARY_RELEASE_READY: REUSO (publicação via from-agent grava blueprint sanitizado em default_config.runtime; release imutável formal = evolução)
AUXILIARY_SECRET_SCAN_READY: SIM (sanitizeBlueprint profundo + FORBIDDEN_SECRET_KEYS já no motor)
CORE_AND_EVEN_NON_PUBLISHABLE_AS_AUXILIARY: SIM (guard publishBlockReason; testado)
AUXILIARY_TEMPLATE_LINKED_TO_RELEASE: SIM (default_config.runtime.agent_blueprint + source{company,agent,origin})
TENANT_AUXILIARY_RUNTIME_ISOLATION_READY: SIM (install cria Agent Smith próprio do tenant; nunca compartilha Source)
TENANT_AUXILIARY_LIFECYCLE_READY: SIM (install/pause/resume/uninstall + status honesto)
AUXILIARY_READINESS_READY: PARCIAL (status por install; integração na Prontidão = próxima)
AUXILIARY_FINOPS_CONTEXT_READY: PARCIAL (contrato buildUsageAttribution pronto; propagação no run = próxima)
SPECIFIC_EXECUTOR_BACKWARD_COMPATIBLE: SIM (resumo-atendimentos/follow-up-whatsapp intactos)
NO_EXTERNAL_PROVIDER_INTEGRATED: SIM
NO_REAL_WHATSAPP_SENT: SIM
NO_BROWSERBASE_OPENED: SIM
NO_PORTAL_ACTION_EXECUTED: SIM
NO_PARALLEL_AGENT_ENGINE_CREATED: SIM (reusou o motor existente)
NEXT_STEP: FASE_B2 — INSTANCE_PROTECTION_EVEN_APPROVERS_HANDOFF
```

## O que entreguei
- `lib/admin/auxiliary-publish.ts` (puro): `canPublishAgentAsGlobalAuxiliary`/`publishBlockReason` (guard) + lifecycle `nextTenantAuxStatus`/`tenantAuxStatusLabel`.
- `from-agent` route: **guard** — publicar como global exige Studio `global_auxiliary` (bloqueia Core/Even/cliente) + grava `source{company,agent,origin:blueprint_studio}`.
- `blueprint-studio-store.ts`: `createSourceAuxiliary` (Source Agent `global_auxiliary` no Studio) + `listStudioAuxiliarySources`.
- APIs: `GET/POST /api/admin/blueprint-center/source-auxiliary` (master) + `GET /api/dashboard/auxiliaries` + `POST /api/dashboard/auxiliaries/[templateId]` (install/pause/resume/uninstall, tenant admin).
- `tenant-auxiliary-store.ts`: galeria + install (reusa `createAgentViaBackend` → runtime isolado; defensivo → `awaiting_runtime`) + pause/resume/uninstall.
- UI: Blueprint Center **"5. Auxiliares Globais"** (criar + publicar) e Dashboard **Meus Auxiliares** (galeria acionável com lifecycle + status honesto).

## Princípios honrados
- **Reuso, não paralelo:** mesmo motor (`auxiliary_templates`/`tenant_auxiliaries`/`smith_agent_blueprint`/`createAgentViaBackend`/`sanitizeBlueprint`). **Sem migration** (runtime vive no jsonb).
- **Isolamento:** instalar cria agente próprio do tenant; Source do Studio nunca é compartilhado.
- **Sem ação externa:** instalar não conecta provedor, não envia WhatsApp, não abre portal; status honesto.
- Guards master/same-origin nas mutações.

## Testes
- `auxiliary-publish` **19** (guard Core/Even/subagent/cliente + lifecycle) + regressão verde (blueprint-release 33, release-rollout 27, studio-taxonomy 11, company-kind 9, security 31).
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo. **Nenhuma migration** nova.

## Você, após o deploy — máx. 5 testes (master + corretora)
1. Blueprint Center → **5. Auxiliares Globais** → criar Source Auxiliar (ex.: nome "Pesquisa de Empresas", slug "pesquisa-empresas").
2. Clicar **Publicar como Auxiliar Global** → aparece na Galeria.
3. (Tente publicar via API a partir do Core → deve ser **bloqueado**.)
4. Dashboard da Resulta → **Auxiliares → Meus Auxiliares**: o novo Auxiliar aparece → **Instalar** → status "Pronto" ou "Aguardando configuração".
5. **Pausar / Retomar / Desinstalar** → status muda corretamente; o motor é isolado da Resulta.

## Próxima execução (Fase B2)
Proteção fina do editor de instância (Even visível + slug oculto na visão de Empresa cliente — exige ajuste no backend Python que hoje lista só `is_active=true`) + **Aprovadores/Handoff**. Depois B3 (WhatsApp/Portais status + FinOps contextual + readiness/rollup). Depois **Fase C — Capability Registry + conectores** (Composio/Nango/Firecrawl).
