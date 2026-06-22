# Fase B (SPEC-013) — Execução Parte 1: Espinha dorsal (Studio + Releases imutáveis + Guardas)

> Primeira execução **segura** da Fase B. Entrega a fundação que torna a arquitetura global concreta e **impede o Frankenstein**: classificação de empresa (Studio isolado), **releases globais imutáveis com varredura de segredos**, seed dos blueprints de código → release v1, e os guardas que mantêm o Studio fora dos fluxos de cliente. **Tudo puro/testável, sem tocar a Resulta, sem aplicar migration, sem ação externa.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `9a115c2` (SPEC-013).

## Decisão de liderança (transparente)
A "Fase B" do GPT é, na prática, **3–4 batches** (classificação + releases + rollout + Blueprint Center UI + editor de instância + auxiliares + telas pendentes do TA2-C). Fazer tudo num turno **criaria o Frankenstein que estamos evitando** (UI meia-feita, build frágil). Entreguei nesta execução a **espinha dorsal pura, testável e sem risco** — o antídoto real (fonte única + releases imutáveis + secret scan + Studio isolado). As partes de UI vêm na 2ª execução, em cima desta base verificada. **Não é plano novo: é a Fase B em execuções seguras.**

### Concordo com o GPT (e ajustei minha SPEC)
- **Studio dedicado** (`AutoBrokers Blueprint Studio`), **sem** reusar a `AutoBrokers Global Knowledge` — separa conhecimento/RAG de autoria de agentes. Aceito; melhora a SPEC-013 (que sugeria reaproveitar).
- 11.A (política de evolução) e 11.C (modelar o registry completo, sem ligar provider) — aprovados e refletidos.

## Declaração
```
BLUEPRINT STUDIO PLATFORM COMPANY READY: PARCIAL (runbook entregue; aplica no deploy)
GLOBAL KNOWLEDGE KEPT SEPARATE: SIM (classificada platform_knowledge; Studio é empresa separada)
STUDIO EXCLUDED FROM CLIENT FLOWS: SIM (guardas por company_kind: provisionamento pula plataforma; helpers de listagem/dashboard)
AUTOBROKERS GLOBAL SOURCE AGENT READY: PARCIAL (release v1 seed pronto; Source Agent no Studio = próxima execução UI)
EVEN GLOBAL SOURCE AGENT READY: PARCIAL (idem)
INITIAL RELEASES SEEDED: SIM (seedReleasesFromCanonical → core+even v1.0.0, com hash, sem segredo)
RELEASE IMMUTABILITY READY: SIM (canEditRelease/canTransitionRelease + trigger SQL de imutabilidade)
RELEASE SECRET SCAN READY: SIM (scanForSecrets + assertReleasePublishable bloqueia segredo/tool livre)
ROLLOUT CANARY READY: NÃO (próxima execução — UI/estado de rollout)
ROLLBACK READY: PARCIAL (transições de status puras prontas; orquestração = próxima)
TENANT PERSONALIZATION PRESERVED: SIM (nada toca tenant_agent_config; releases são camada global)
INSTANCE EDITOR PROTECTED: NÃO (próxima execução — UI Portal Admin)
EVEN VISIBLE IN PORTAL ADMIN: NÃO (próxima execução — UI)
LEGACY SLUG HIDDEN IN UI: NÃO (próxima execução — UI)
AUXILIARY STUDIO PUBLICATION READY: NÃO (próxima execução)
TENANT AUXILIARY RUNTIME ISOLATION READY: NÃO (próxima execução)
APPROVERS AND HANDOFF DASHBOARD READY: NÃO (TA2-C pendente — próxima execução)
WHATSAPP STATUS DASHBOARD READY: NÃO (TA2-C pendente)
PORTAL STATUS DASHBOARD READY: NÃO (TA2-C pendente)
FINOPS PROPAGATION READY: NÃO (próxima execução)
READINESS AND ADMIN ROLLUP READY: PARCIAL (já existe do TA2-B/C; integração nova = próxima)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO EXTERNAL CAPABILITY INTEGRATED: SIM
NO PARALLEL AGENT ENGINE CREATED: SIM
NEXT STEP: Fase B Parte 2 — Blueprint Center (UI), separar Instance×Blueprint editor, mostrar Even, esconder slug, publicar Agent como Auxiliar, concluir TA2-C; depois Fase C (Capability Registry)
```

## O que entreguei (verificado)
### Classificação de empresa (Studio isolado)
`lib/admin/company-kind.ts` (puro): `company_kind` = `client | platform_knowledge | platform_blueprint_studio` + decisões de fluxo (`visibleInClientListing`, `canUseTenantDashboard`, `shouldAutoProvisionOnCreate`, `allowsClientOperations`, `requiresMasterOnly`). `lib/admin/company-kind-store.ts` (defensivo: pré-migration retorna `client` → comportamento idêntico ao de hoje). **Guarda real:** `provisionTenant` agora **pula empresas-plataforma** (Studio não recebe provisionamento comercial).
### Releases globais imutáveis + secret scan
`lib/admin/blueprint-release.ts` (puro): `buildArtifactFromCanonical` (artefato sanitizado), `scanForSecrets` (token/sk-/Bearer/JWT/AWS/Slack/URL-com-segredo + nomes de campo proibidos), `assertReleasePublishable` (bloqueia segredo, tool/MCP livre, capability_keys inválidas), `hashArtifact` (determinístico), `canEditRelease`/`canTransitionRelease` (só draft edita; published→retired), `seedReleasesFromCanonical` (core+even → v1.0.0 publicado, sem segredo).
### Runbooks (entregues, NÃO aplicados)
`spec-013-01-company-kind.sql` (coluna + constraint + índice + classifica Global Knowledge + cria Studio; APPLY/VERIFY/ROLLBACK escopado). `spec-013-02-agent-blueprint-releases.sql` (tabela + unique + índices + **trigger de imutabilidade** + RLS + revoke anon/authenticated + policy service_role; APPLY/VERIFY/ROLLBACK).

## Princípios honrados
- **Motor único do Smith** — nada de engine paralela. Releases e classificação só governam fluxos.
- **Fonte única:** o código vira **seed/validador**; a release publicada é a fonte global. Sem duas fontes editáveis concorrentes.
- **Segredo nunca na release** (scan + trigger + RLS).
- **Personalização local intacta:** nada toca `tenant_agent_config`.
- **DI para testabilidade** (sem import quebrado no loader .mjs).

## Testes
- Novos: `company-kind` **9**, `blueprint-release` **22** (artefato, secret scan, publicabilidade, hash, imutabilidade, seed v1).
- Regressão verde: blueprints 60, finops 7, security 31, company-profile 19 (+ demais do TA2-B/C inalterados).
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Você (após o deploy) — ordem dos runbooks
1. `spec-013-01-company-kind.sql` → APPLY → VERIFY (confere Studio + Global Knowledge classificados).
2. `spec-013-02-agent-blueprint-releases.sql` → APPLY → VERIFY (tabela + trigger de imutabilidade).
Antes de aplicar, o sistema roda **idêntico ao de hoje** (guardas defensivos retornam `client`).

## Próxima execução (Fase B Parte 2)
Blueprint Center no Portal Admin (editor Smith real para os Source Agents do Studio) + separar Instance Editor de Blueprint Editor + **mostrar a Even** + **esconder o slug legado** + publicar Agent como Auxiliar Global + concluir o TA2-C pendente (Aprovadores, lifecycle de Auxiliares, telas WhatsApp/Portais, FinOps amplo). Depois: **Fase C — Capability Registry** (connect-once-reuse). Em paralelo: **42X5C** quando a Z-API for paga.
