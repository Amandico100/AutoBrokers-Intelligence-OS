# 42B5D — Runtime Config Resolver & Slot Catalog Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/UI/Core) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main
> **Natureza:** refatoração estrutural — **sem mudança funcional perceptível**.

## 0. Auditoria realizada antes de editar
Lidos: `SPEC-005`, `SPEC-006`, `42B5B-...report.md`, `42B5C-...report.md`; código `corridor-runtime.ts`, `runtime/step/route.ts`, `runtime/reply/route.ts`, migration `20260612` (vocabulário de `attendance_cases.status`, `corridor_runs`, `corridor_templates.required_slots/metadata`).

**Princípios preservados:** uma pergunta por vez; não repetir pergunta (dedupe); não perguntar dado já preenchido; **risco antes de dados administrativos**; não confirmar cobertura; não acionar externamente. `external_action_allowed=false` sempre.

## 1. Arquivos criados/alterados
- `lib/attendance/runtime-slot-catalog.ts` (**novo**) — catálogo declarativo por slot (label, priority_default, question, clarification, extractor, safety) + `detectHighRisk`, `genericExtractor`, `ELECTRICIAN_SLOT_PRIORITY` (derivada do catálogo).
- `lib/attendance/runtime-config-resolver.ts` (**novo**) — `resolveRuntimeConfig(...)` → `{ engine, corridor_key, subcorridor_key, slot_priority, slot_catalog, slot_priority_source }`.
- `lib/attendance/corridor-runtime.ts` (**refatorado**) — agora cuida só do **fluxo genérico** (seleção, status, fases, diagnostics) e **delega** pergunta/clarificação/extração ao catálogo. `computeRuntimeStep` aceita `slotPriority?` (default = MVP Eletricista). **Todas as exports públicas preservadas** (`computeRuntimeStep`, `selectNextSlot`, `extractSlotValue`, `clarificationForSlot`, `questionForSlot`, `isSlotFilled`, `detectHighRisk`, `RUNTIME_ENGINE`, `ELECTRICIAN_SLOT_PRIORITY`, tipos `SlotExtraction`/`SlotConfidence`).
- `app/api/attendance/cases/[caseId]/runtime/step/route.ts` (**alterado**) — busca `corridor_template` (best-effort) e usa `resolveRuntimeConfig` → passa `slot_priority` ao motor; registra `slot_priority_source` em diagnostics.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — idem; `resolveTargetSlot` e `computeRuntimeStep` usam `slot_priority` resolvida.
- `docs/canon/design/2026-06-claude-design/42B5D-runtime-config-resolver-slot-catalog-report.md` (este).

**UI não foi alterada. Core chat não foi tocado.**

## 2. Como separou runtime genérico, slot catalog e config resolver
- **Slot Catalog** (`runtime-slot-catalog.ts`): tudo que é *específico de um slot* — a pergunta, a clarificação, o extrator e a flag de segurança — fica em um registro declarativo `SLOT_CATALOG[key]`. Novos slots = novas entradas, sem `if/else` no motor.
- **Runtime genérico** (`corridor-runtime.ts`): seleção do próximo slot, transições de status/fase, montagem de `RuntimeStepResult`, notas de segurança. Não conhece os detalhes de cada slot — apenas consulta o catálogo via `getSlotDefinition`.
- **Config Resolver** (`runtime-config-resolver.ts`): decide *qual ordem de slots* e *qual catálogo* usar para um caso, a partir de `corridor_template`/`corridor_run`/`caseRow`, com fallback seguro. É o ponto único onde a configuração por corredor entra.

## 3. Como evita retrabalho para dezenas de corredores
- Adicionar um subcorredor/slot novo é **declarativo**: criar a entrada no `SLOT_CATALOG` e (se preciso) declarar a ordem em `corridor_templates.metadata.runtime_slot_priority`. O motor e as rotas **não mudam**.
- As rotas já chamam `resolveRuntimeConfig`, então quando um template trouxer prioridade própria, o runtime passa a respeitá-la **sem alteração de código**.
- O catálogo é keyed por slot e reutilizável entre corredores (ex.: `policy_evidence_status` serve a qualquer seguradora).

## 4. Fallback atual para Allianz/Eletricista (e por que a ordem do template não é usada crua)
`resolveSlotPriority` resolve `slot_priority` por:
1. `template.metadata.runtime_slot_priority` (explícito);
2. `template.config.slot_priority` / `template.metadata.config.slot_priority` (explícito);
3. **fallback `ELECTRICIAN_SLOT_PRIORITY`** (comportamento atual).

**Decisão de design:** a ordem bruta de `required_slots` do template **não** é usada como prioridade de runtime, porque ela está ordenada para o *contrato de dispatch* (`problem_description`, `electrical_issue_type`, contato…) e **não** para a conversa segura (risco antes de dados administrativos). Usá-la cruamente mudaria o comportamento (perguntaria `electrical_issue_type` antes de `risk_indicators`/`affected_area`) e quebraria os testes do 42B5B/42B5C. Por isso só uma prioridade de runtime **declarada explicitamente** sobrescreve o fallback. Em todos os casos aplicamos sanitização (só slots do catálogo, dedupe) + **hoist de segurança** (slots `safety.raisesRisk` vão para o início). O template seed do Eletricista **não** declara `runtime_slot_priority` → usa o fallback → comportamento idêntico.

## 5. Impacto no comportamento
- **Nenhum impacto funcional.** `ELECTRICIAN_SLOT_PRIORITY` continua `['risk_indicators','affected_area','electrical_issue_type','property_address_confirmed','policy_evidence_status']`. Perguntas, clarificações e extratores foram movidos **verbatim**.
- Único acréscimo: `diagnostics.runtime.slot_priority_source` (auditoria) — campo informativo, não altera fluxo.

## 6. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · UI · backend Python · RAG · prompts/agentes · WhatsApp | ✅ nenhum |
| dispatch · approval · InfoCap/portal · envio externo | ✅ nenhum |
| Core chat / prompt do Core | ✅ inalterado |
| token/secret/PII no diff | ✅ nenhum |

## 7. Deploy recomendado
- **Web apenas** (route handlers + helpers). Sem backend Python, sem SQL/migration.

## 8. Testes manuais (após deploy Web) — reexecutar 42B5B/42B5C
1. `POST runtime/step` em caso novo → `selected_slot=risk_indicators`, pergunta gerada, `message_id` preenchido.
2. Repetir `step` sem `force` → **não** duplica a pergunta.
3. `POST runtime/reply` com "Não, sem cheiro de queimado nem faísca." → `target_slot=risk_indicators`, `filled=true`, `risk_level low`, próximo `selected_slot=affected_area`, próxima pergunta gravada.
4. `POST runtime/reply` com "Tem cheiro de queimado e saiu uma faísca." (caso novo) → `risk_level/priority=high` no caso, safety_note, sem acionamento.
5. **Core chat intacto:** Core interno, Auxiliares, NEVOA-791 (CORE-REGRESSION-001).
6. (Opcional) Conferir `diagnostics.runtime.slot_priority_source='fallback_electrician'`.

## 9. Próximos passos
- **42B5E** — first response/saudação inicial e/ou condições de handoff automático (risco alto / rede externa).
- **42B6** — Dispatch Packet + WhatsApp dry-run/HITL.
- Novos subcorredores (Encanador/Chaveiro/etc.): adicionar slots no catálogo + `runtime_slot_priority` no template, sem mexer no motor.
