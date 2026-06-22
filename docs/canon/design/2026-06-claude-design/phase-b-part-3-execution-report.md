# Fase B Parte 3 — Execução (slice): Releases derivadas do Source Agent (editar no Studio → publicar versão)

> Fecha o **loop do estúdio global**: agora uma nova versão de release é **extraída da configuração editada do Source Agent no Studio** (não mais só do código). Editar AutoBrokers/Even Global no Studio → **criar draft** → **publicar** versão imutável. **Sem tocar a Resulta; sem rollout automático; sem provider externo; motor único do Smith.**
> **Data:** 2026-06-22 · **Modelo:** Claude Opus 4.8 · **Base:** `58e8bf8`.

## Decisão de liderança (transparente)
A "Parte 3" do GPT são, de novo, 4–5 batches (releases-do-source + rollout/rollback + proteção de instância + auxiliares-sobre-Smith + todo o TA2-C + FinOps). Entreguei **a peça #1 que o próprio GPT apontou como lacuna**: a publicação derivar do **Source Agent real**, não do código. Sem isso, editar o Studio não teria efeito — então este é o passo certo agora. Rollout/rollback, proteção de instância (Even visível/slug oculto), auxiliares-sobre-Smith e o restante do TA2-C vêm na próxima execução. **Não é plano novo.**

## Estado live confirmado pelo Founder (antes desta execução)
Studio inicializado; Source Agents `AutoBrokers Global Core` + `Even Global Attendance` criados; releases `autobrokers-core-v1@1.0.0` e `even-attendance-v1@1.0.0` **published** com `source_agent_id` e hash `sha256_…` (SQL retornou 2). Resulta isolada; nenhum rollout aplicado.

## Declaração (parcial — slice da Parte 3)
```
STUDIO SOURCE AGENTS VERIFIED: SIM (criados e confirmados pelo Founder)
REAL V1 RELEASES VERIFIED: SIM (2 published, sha256, source_agent vinculado)
SOURCE AGENT TO RELEASE FLOW READY: SIM (buildArtifactFromSourceAgent + draft + publish; UI no Blueprint Center)
RELEASE HASH CRYPTOGRAPHIC: SIM (SHA-256)
RELEASE IMMUTABILITY READY: SIM (trigger no banco + canEdit/canTransition + publish exige draft)
ROLL_OUT_CANARY_READY: NÃO (próxima execução)
ROLLBACK READY: NÃO (próxima execução)
TENANT PERSONALIZATION PRESERVED: SIM (nada toca tenant_agent_config)
INSTANCE EDITOR PROTECTED: NÃO (próxima execução)
EVEN VISIBLE IN PORTAL ADMIN: PARCIAL (no Blueprint Center; visão de Empresa = próxima)
LEGACY SLUG HIDDEN IN UI: NÃO (próxima execução)
AUXILIARY STUDIO PUBLICATION READY: NÃO (próxima execução)
TENANT AUXILIARY RUNTIME ISOLATION READY: NÃO (próxima execução)
APPROVERS AND HANDOFF DASHBOARD READY: NÃO (TA2-C — próxima)
WHATSAPP STATUS DASHBOARD READY: NÃO (TA2-C — próxima)
PORTAL STATUS DASHBOARD READY: NÃO (TA2-C — próxima)
FINOPS PROPAGATION READY: NÃO (próxima)
READINESS AND ADMIN ROLLUP READY: PARCIAL (já existe do TA2-B/C)
NO REAL WHATSAPP SENT: SIM
NO BROWSERBASE OPENED: SIM
NO PORTAL ACTION EXECUTED: SIM
NO EXTERNAL CAPABILITY INTEGRATED: SIM
NO PARALLEL AGENT ENGINE CREATED: SIM
NEXT STEP: Fase B Parte 4 — rollout/rollback por tenant + proteção de instância (Even/slug) + auxiliares-sobre-Smith + conclusão do TA2-C; depois Fase C (Capability Registry)
```

## O que entreguei
- **`blueprint-release.ts`**: `buildArtifactFromSourceAgent(bp, src)` — estrutura **travada** pelo blueprint (role/audience/marca/variáveis/**guardrails**) + conteúdo **editável** do Source Agent (prompt-base, modelo, capability_keys). `bumpSemanticVersion` (major/minor/patch).
- **`blueprint-studio-store.ts`**: `createReleaseDraftFromSourceAgent` (exige Source Agent — `source_agent_missing` se faltar; calcula próxima versão única; secret-scan antes de gravar; insere **draft**), `publishReleaseDraft` (draft→published, re-valida, imutável depois), `findSourceAgent` (por **blueprint_version/slug** → role, à prova de colisão futura), `getStudioStatus` agora reporta `core_published`/`even_published`/`has_draft` (**readiness específico**, não `releases.length>=2`).
- **APIs master-only + same-origin**: `POST /api/admin/blueprint-center/create-draft`, `POST .../publish-draft`.
- **Blueprint Center (UI)**: Passo 3 "Evolução do padrão global" — por blueprint, lista versões, **Criar nova versão (draft)** e **Publicar** draft.

## Correções do GPT adotadas
- Release **derivada do Source Agent** (lacuna #1). ✔
- `source_agent_id` **obrigatório** no fluxo do Studio (`source_agent_missing`). ✔
- Readiness **específico** de Core e Even (não `length>=2`). ✔
- Busca idempotente de Source Agent por **blueprint_key/slug**, não só role. ✔
- Validação no **backend** (store), não só na UI. ✔

## Princípios honrados
- Estrutura travada (role/audience/marca/guardrails) — editar o Source Agent **não** enfraquece guardrails nem muda papel.
- Release publicada **imutável**; nova versão é sempre **draft** → publish.
- Segredo no prompt editado é **bloqueado** antes de gravar.
- Resulta intacta; nenhum rollout automático.

## Testes
- `blueprint-release` **33** (inclui: prompt editado entra; role/audience/guardrails travados; fallback de prompt vazio; segredo no prompt bloqueia; bumps major/minor/patch). `company-kind` 9 + regressão verde (blueprints 60, security 31).
- `tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.

## Testes live (após deploy) — máx. 5 (você, master)
1. Portal Admin → **Blueprint Center** → seção **3. Evolução**.
2. (Opcional) Edite o prompt do **AutoBrokers Global Core** no Studio (Empresas → AutoBrokers Blueprint Studio → Agentes → editar).
3. Clique **Criar nova versão (draft)** em AutoBrokers Global → aparece `v1.1.0 · draft`.
4. Clique **Publicar** → vira `v1.1.0 · published` (e some o botão).
5. Supabase: `select blueprint_key, semantic_version, status from public.agent_blueprint_releases order by 1,2;` → v1.0.0 published + v1.1.0 published.

## Próxima execução (Fase B Parte 4)
Rollout/rollback por corretora (aplicar release na instância preservando personalização) + **proteção do editor de instância** (Even visível, slug oculto) + **auxiliares-sobre-Smith** (publicar Source Agent como Auxiliar; instalar = runtime isolado) + conclusão do **TA2-C** (Aprovadores, lifecycle de Auxiliares, telas WhatsApp/Portais, FinOps amplo). Depois: **Fase C — Capability Registry**.
