# Fase B Parte 4 (slice) — Rollout/Rollback Studio→corretora + tela do Studio corrigida

> Fecha o **loop de distribuição** da Fase B: a release publicada no Studio agora pode ser **aplicada a uma corretora (canário) preservando a personalização local**, com **rollback**. Também corrige a tela "Nenhum agente criado" do Studio (era a tela genérica filtrando `is_active=true`). **Sem tocar a Resulta automaticamente; sem provider externo; sem ação externa; motor único do Smith.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `7fba8b0`.

## Decisão de liderança (transparente)
O GPT pediu "terminar a Fase B num batch", mas a Parte 4 são ~9 frentes (Studio UI + taxonomia + rollout + proteção de instância + auxiliares-sobre-Smith + TA2-C inteiro + FinOps). Entregar tudo num turno com qualidade e **build verde** não é realista — e um build quebrado **é** o Frankenstein que evitamos. Entreguei **o keystone arquitetural restante — rollout/rollback** (Studio→instância preservando personalização) **+ o conserto da tela vazia do Studio** (sua dor no print). Auxiliares-sobre-Smith, proteção completa do editor de instância e o restante do TA2-C ficam para a execução de fechamento. **Não é plano novo.**

### Análise do GPT que adotei
- **3 grupos de conectores** (capacidade de plataforma / conta própria da corretora / conector empresarial) — correto; entra na **Fase C**.
- **Composio para o grupo 2 / Nango como comparação / Firecrawl como capacidade de plataforma direta** — concordo: **decisão e piloto na Fase C**, sem integrar provider agora.
- **Tela do Studio**: a causa é a rota genérica que só lista `is_active=true`; **não** resolver ativando os Source Agents. Corrigi pela UX (abaixo).

## Declaração (slice da Parte 4)
```
STUDIO SOURCE AGENTS VISIBLE AND MANAGED: PARCIAL (Blueprint Center já gerencia; tela de Empresa→Studio agora redireciona p/ lá em vez de "criar agente")
SOURCE AGENT TAXONOMY READY: PARCIAL (Core/Even/auxiliary/subagent conceituados; campo dedicado studio_source_kind = próxima)
SOURCE AGENT TO RELEASE FLOW READY: SIM (P3)
ROLLOUT CANARY READY: SIM (applyRollout manual por corretora; Blueprint Center "4. Rollout")
ROLLBACK READY: SIM (rollbackRollout para release anterior, preservando personalização)
TENANT PERSONALIZATION PRESERVED: SIM (testado: nome/var local + context_package preservados; prompt vem da release)
INSTANCE EDITOR PROTECTED: PARCIAL (Studio/Knowledge bloqueados na tela de agentes; proteção fina de Core/Even cliente = próxima)
EVEN VISIBLE IN PORTAL ADMIN: PARCIAL (Blueprint Center; visão de Empresa cliente = próxima)
LEGACY SLUG HIDDEN IN UI: NÃO (próxima)
AUXILIARY STUDIO PUBLICATION READY: NÃO (próxima)
TENANT AUXILIARY RUNTIME ISOLATION READY: NÃO (próxima)
APPROVERS AND HANDOFF DASHBOARD READY: NÃO (TA2-C — próxima)
WHATSAPP STATUS DASHBOARD READY: NÃO (TA2-C — próxima)
PORTAL STATUS DASHBOARD READY: NÃO (TA2-C — próxima)
FINOPS PROPAGATION READY: NÃO (próxima)
READINESS AND ADMIN ROLLUP READY: PARCIAL (TA2-B/C)
CAPABILITY REGISTRY NOT IMPLEMENTED: SIM
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO EXTERNAL PROVIDER INTEGRATED: SIM
NO PARALLEL AGENT ENGINE CREATED: SIM
NEXT STEP: Fase B fechamento — taxonomia source/instância, proteção fina de instância (Even/slug), auxiliares-sobre-Smith e TA2-C; depois Fase C (Capability Registry + conectores: Composio/Nango/Firecrawl)
```

## O que entreguei
### Rollout / Rollback (keystone)
- `lib/admin/release-rollout.ts` (puro): `artifactToBlueprint` (artefato→blueprint p/ reusar materialização), `extractSavedTenantInput` (lê a personalização local salva), `canRolloutTransition` + `ROLLOUT_STATES`.
- `lib/admin/release-rollout-store.ts`: `applyRollout` (só corretora **cliente**; release **published**; materializa via `computeAgentConfigUpdate` **preservando `tenant_agent_config`**; grava `blueprint_version` + registro de rollout; pausa o anterior), `rollbackRollout` (reaplica a release anterior), `listRollouts`.
- Runbook `spec-013-03-agent-release-rollouts.sql` (tabela + RLS + revoke + índices; APPLY/VERIFY/ROLLBACK).
- APIs master-only + same-origin: `POST rollout`, `POST rollback`, `GET rollouts`.
- Blueprint Center: seção **"4. Rollout por corretora (manual)"** — escolher release publicada + corretora (canário) → Aplicar; lista de rollouts + **Rollback**.
### Tela do Studio corrigida
- `GET /api/admin/companies/[companyId]/kind` + guarda na página de agentes: empresa **plataforma** (Studio/Knowledge) agora mostra um card explicativo + **"Abrir Blueprint Center"** em vez de "Nenhum agente criado / Criar Primeiro Agente". Source Agents continuam **inativos** (autoria), como deve ser.

## Princípios honrados
- Rollout **manual** e **por corretora**; **nunca** automático no deploy; **nunca** cruza tenant (só cliente; Studio/Knowledge excluídos).
- **Personalização local preservada** (testado): nome/voz/var locais + `context_package` intactos; o que muda é a camada global (prompt da release) + guardrails sempre presentes.
- Release publicada **imutável**; rollback reaplica a anterior.
- Tudo master-only, same-origin, sanitizado.

## Testes
- `release-rollout` **15** (materialização preserva Joana + context_package; usa template da release; guardrails presentes; transições). + `blueprint-release` 33, `company-kind` 9, blueprints 60, security 31 — verdes.
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Você, após o deploy — máx. 5 testes (master)
1. Aplique o runbook `spec-013-03-agent-release-rollouts.sql` (APPLY → VERIFY).
2. Portal Admin → **Empresas → AutoBrokers Blueprint Studio → Agentes**: agora mostra o card da plataforma + **Abrir Blueprint Center** (não mais "criar agente").
3. **Blueprint Center → 4. Rollout**: escolha `autobrokers-core-v1 v1.0.0` + **Resulta** → **Aplicar à corretora**.
4. Veja o rollout `active`; clique **Rollback** → volta ao estado anterior.
5. Confirme que a personalização da Resulta (se houver) seguiu intacta no Dashboard.

## Próxima execução (fechamento da Fase B)
Taxonomia `studio_source_kind`/`tenant_instance_kind` + **proteção fina do editor de instância** (Even visível e slug oculto na visão de Empresa cliente) + **auxiliares-sobre-Smith** (publicar Source Agent como Auxiliar; instalar = runtime isolado) + conclusão do **TA2-C** (Aprovadores, lifecycle de Auxiliares, telas WhatsApp/Portais, FinOps amplo). Depois: **Fase C — Capability Registry + conectores** (Composio/Nango/Firecrawl, com repasse de custo no FinOps).
