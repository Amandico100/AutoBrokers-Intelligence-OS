# Fase B Parte 2 — Execução (marco): Blueprint Center + Source Agents + Releases reais (SHA-256)

> Marco real e visível da Fase B. Entrega o **Blueprint Center** (master) onde o Founder **inicializa o Studio** (cria os Source Agents AutoBrokers/Even no motor real do Smith) e **publica as releases globais reais v1.0.0** (artefato sanitizado + **SHA-256** + secret-scan + imutáveis). Ações **master-only, disparadas manualmente** (sem escrita automática). **Não toca a Resulta; sem provider externo; sem ação externa; motor único do Smith.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `7b98892`.

## Decisão de liderança (transparente)
A "Parte 2" do GPT são, de fato, **4–5 batches** (Studio init + releases + rollout + Blueprint Center + proteção de instância + auxiliares-sobre-Smith + todo o TA2-C pendente + FinOps). Fazer tudo num turno **criaria o Frankenstein** que estamos evitando. Entreguei o **marco que torna o global REAL e visível** — Studio com Source Agents + releases persistidas — que é a base de tudo que vem depois. O restante (rollout, proteção de instância, auxiliares, TA2-C) vem na próxima execução segura. **Não é plano novo; é a Fase B em execuções seguras.**

### Correções do GPT que adotei
- **SHA-256** no hash da release (era djb2) — `hashArtifact` agora usa `node:crypto`. ✔
- `policyname` (não `polname`) no VERIFY — usarei nos próximos runbooks. ✔
- **Disparo manual** das ações (Studio init / publish), sem escrita no load da página — implementado. ✔

## Declaração
```
STUDIO INITIALIZED: PRONTO P/ DISPARO (ação master "Inicializar" no Blueprint Center; idempotente)
STUDIO SOURCE AGENTS READY: PRONTO P/ DISPARO (cria AutoBrokers Core + Even no Studio via motor Smith)
REAL V1 RELEASES PERSISTED: PRONTO P/ DISPARO (ação master "Publicar releases"; grava em agent_blueprint_releases)
RELEASE HASH CRYPTOGRAPHIC: SIM (SHA-256)
RELEASE IMMUTABILITY READY: SIM (trigger SQL já aplicado pelo Founder + canEdit/canTransition puros)
RELEASE SECRET SCAN READY: SIM (assertReleasePublishable antes de persistir)
ROLLOUT CANARY READY: NÃO (próxima execução)
ROLLBACK READY: NÃO (próxima execução)
TENANT PERSONALIZATION PRESERVED: SIM (nada toca tenant_agent_config; Studio é isolado)
INSTANCE EDITOR PROTECTED: NÃO (próxima execução — UI)
EVEN VISIBLE IN PORTAL ADMIN: PARCIAL (visível no Blueprint Center; correção na visão de Empresa = próxima)
LEGACY SLUG HIDDEN IN UI: NÃO (próxima execução)
AUXILIARY STUDIO PUBLICATION READY: NÃO (próxima execução)
TENANT AUXILIARY RUNTIME ISOLATION READY: NÃO (próxima execução)
APPROVERS AND HANDOFF DASHBOARD READY: NÃO (TA2-C pendente — próxima execução)
WHATSAPP STATUS DASHBOARD READY: NÃO (TA2-C pendente)
PORTAL STATUS DASHBOARD READY: NÃO (TA2-C pendente)
FINOPS PROPAGATION READY: NÃO (próxima execução)
READINESS AND ADMIN ROLLUP READY: PARCIAL (já existe do TA2-B/C)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO EXTERNAL CAPABILITY INTEGRATED: SIM
NO PARALLEL AGENT ENGINE CREATED: SIM
NEXT STEP: Fase B Parte 3 — rollout/rollback, proteção de instância (Even visível + slug oculto), auxiliares-sobre-Smith e conclusão do TA2-C; depois Fase C (Capability Registry)
```

## O que entreguei
- **`lib/admin/blueprint-studio-store.ts`**: `getStudioCompanyId` (por `company_kind`), `initializeStudio` (idempotente: cria Source Agents Core+Even **na empresa Studio**, motor Smith real), `publishSeedReleases` (idempotente: artefato sanitizado → secret-scan → **SHA-256** → grava em `agent_blueprint_releases`, sem duplicar chave/versão, `source_company_id`/`source_agent_id` preenchidos), `getStudioStatus` (read sanitizado).
- **APIs master-only + same-origin:** `GET /api/admin/blueprint-center`, `POST .../initialize`, `POST .../publish-seed`.
- **Tela `app/admin/blueprint-center/page.tsx`** (DS-001): Passo 1 "Inicializar Studio" + Passo 2 "Publicar releases v1.0.0", com status (Source Agents criados? releases publicadas? hash) — **disparo manual**.
- **`blueprint-release.ts`**: hash agora **SHA-256**.

## Princípios honrados
- **Motor único do Smith** — Source Agents são agentes Smith reais dentro do Studio; nada paralelo.
- **Fonte única:** código = seed/validador; release publicada (persistida) = fonte global.
- **Segredo nunca na release** (scan antes de persistir + trigger + RLS já no banco).
- **Personalização local intacta**; Studio isolado de cliente; `provisionTenant` já pula plataforma.
- **Sem escrita automática:** o master dispara as ações.

## Testes
- `blueprint-release` **23** (inclui SHA-256 64-hex), `company-kind` **9** + regressão verde (blueprints 60, security 31, finops 7).
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.
- (As funções de I/O do Studio são exercidas pelos testes live abaixo — a lógica pura por trás já é coberta por blueprint-release.)

## Testes live (após deploy) — máx. 5 (você, master)
1. Portal Admin → **Blueprint Center**: ver Studio presente, Source Agents "pendentes".
2. Clicar **Inicializar Studio** → AutoBrokers Core + Even aparecem como "criados".
3. Clicar **Publicar releases v1.0.0** → as 2 releases aparecem `published` com hash `sha256_…`.
4. Clicar **Publicar** de novo → idempotente (mostra "exists", não duplica).
5. No Supabase: `select blueprint_key, semantic_version, status from public.agent_blueprint_releases;` → 2 linhas published.

## Próxima execução (Fase B Parte 3)
Rollout/rollback por corretora (com release aplicada por instância, preservando personalização) + **proteção do editor de instância** (mostrar Even na visão de Empresa, esconder slug legado) + **auxiliares-sobre-Smith** (publicar Source Agent como Auxiliar; instalar = runtime isolado por tenant) + conclusão do **TA2-C** (Aprovadores, lifecycle de Auxiliares, telas WhatsApp/Portais, FinOps amplo). Depois: **Fase C — Capability Registry**. Em paralelo: **42X5C** quando a Z-API for paga.
