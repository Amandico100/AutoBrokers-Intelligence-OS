# 42B5H — Resume Corridor After Policy Lookup Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/UI/WhatsApp/InfoCap real/credenciais) · sem deploy automático.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Auditoria
Lidos/confirmados: `SPEC-005` (§7 fluxo, §12 policy evidence), `SPEC-006`, `SPEC-004`, `ADR-003`, `ADR-002`, `42I0P`, `42I1`, e os relatórios 42B5B–G; código `corridor-runtime.ts`, `runtime-config-resolver.ts`, `runtime-slot-catalog.ts`, `attendance-macro-state.ts`, `runtime-identity-policy.ts`, `runtime-safety-policy.ts`, `runtime-intake-policy.ts`, `policy-lookup.ts`, rotas `runtime/{step,reply,policy-lookup}`. **Legado Agent OS não está sincronizado no workspace local** — seguido pelos docs canônicos, que já consolidam as decisões (ADR-003 §13 apólice/elegibilidade; SPEC-005 §7/§12).

## 1. Arquivos alterados/criados
- `lib/attendance/attendance-macro-state.ts` (**alterado**) — `isPolicyEvidenceReady(caseRow)` + `RESUME_AFTER_POLICY_PREFIX`.
- `app/api/attendance/cases/[caseId]/runtime/step/route.ts` (**alterado**) — branch de **retomada** após a evidência de apólice, antes do macro gate.
- `docs/canon/design/2026-06-claude-design/42B5H-resume-corridor-after-policy-lookup-report.md` (este).

Nenhuma alteração em `reply`/`policy-lookup`. UI/dashboard intactos.

## 2. Não alterou SQL/schema/backend Python/RAG/prompts/UI/WhatsApp
Confirmado — apenas 2 arquivos TS/Next + relatório, reusando colunas/jsonb existentes.

## 3. Comportamento implementado
Em `POST /api/attendance/cases/[caseId]/runtime/step`, quando `isPolicyEvidenceReady(caseRow)` (macro `policy_evidence_ready` + `coverage_evidence` preenchido + `verification_status` confiável: `verified_by_human`/`verified_by_connector`/`verified_by_document`):
1. resolve o gate de apólice (não pede CPF de novo);
2. `attendance_cases.status = collecting_slots`;
3. **preserva** `verification_status`, `policy_source`, `policy_number`, `policy_snapshot`, `coverage_evidence`;
4. `metadata.attendance_macro_state = corridor_collecting_slots` (merge — preserva `identity`/`policy_lookup`);
5. `corridor_runs.phase = collect_slots`;
6. `corridor_runs.last_agent_action = ask:<next_slot>` (ou `resume_after_policy_lookup` se não houver slot);
7. usa `computeRuntimeStep` com o **runtime config resolver + slot catalog** atuais para escolher o próximo slot faltante (`affected_area` → `electrical_issue_type` → …);
8. cria **uma** mensagem assistant curta humanizada com retomada + pergunta:
   *"Apólice localizada e evidência registrada. Agora vou seguir com os dados do atendimento. \<pergunta do próximo slot\>"* (com dedupe);
9. `diagnostics.runtime`: `macro_state=corridor_collecting_slots`, `resumed_after_policy_lookup=true`, `coverage_evidence_ready=true`, `external_action_allowed=false`, `selected_slot`, `slot_priority_source`.

## 4. Como retoma (arquitetura)
Runtime determinístico apenas resolve o gate e escolhe o próximo passo do **workflow estruturado** — não cria motor paralelo, não move lógica para RAG, não vira prompt solto, não cria agente. É a mesma camada que o Attendance Agent/Smith chamará como tool. A cobertura **não** é reafirmada pela LLM — só o que já está em `coverage_evidence`.

## 5. Estados que BLOQUEIAM a retomada
- `status` em `handoff`/`closed`/`cancelled` → **409** (guard existente).
- Sem `coverage_evidence` → `isPolicyEvidenceReady=false` → cai no macro gate (pede policy lookup), **não** retoma.
- `verification_status=unverified` (ou não confiável) → não retoma.
- policy lookup pendente/blocked → macro não é `policy_evidence_ready` → não retoma.
- Risco alto → safety/handoff tem precedência (avaliado antes da retomada).

## 6. Genérico para outros corredores
Sim. A retomada não tem nada específico de Eletricista: usa `isPolicyEvidenceReady` (campos genéricos do caso) + `resolveRuntimeConfig`/`computeRuntimeStep`/slot catalog. Qualquer corredor com evidência pronta + slots faltantes + config resolvida retoma igual. Eletricista é só o primeiro caso de teste.

## 7. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · backend Python · RAG · prompts/agentes · UI · WhatsApp · InfoCap real · credenciais | ✅ nenhum |
| dispatch · approval · Core · Auxiliares | ✅ intactos |
| CPF/PII em logs | ✅ nenhum (log só case/slot/message_id) |

## 8. Testes manuais (após deploy Web)
**A — fluxo completo até retomada:** criar caso → `reply 'Estou sem luz só na cozinha'` → `reply 'Não, sem cheiro de queimado nem faísca.'` → `reply '123.456.789-09'` → `policy-lookup {source:'mock',mode:'mock',fixture:'allianz_residential_electrician_covered'}` → **`step`** →
esperado: `status=collecting_slots`; `metadata.attendance_macro_state=corridor_collecting_slots`; `verification_status=verified_by_human` preservado; `coverage_evidence` preservado; `selected_slot=affected_area`; mensagem de retomada criada; **não** pediu CPF; **sem** WhatsApp/dispatch; `diagnostics.runtime.resumed_after_policy_lookup=true`.

**B — não retomar sem evidência:** caso `policy_check` sem `coverage_evidence` → `step` não avança ao corredor (cai no macro gate de apólice).

**C — não retomar handoff:** `status=handoff` → `step` retorna **409**.

**D — Core intacto:** Core interno; Auxiliares (Resumo + Follow-up); RAG NEVOA-791.

## 9. Próximo batch recomendado
**42I2 — InfoCap Connector Read-only (via Vault)** para substituir o mock por consulta real read-only (mantendo o mesmo `policy_lookup_result`/`coverage_evidence` e a mesma retomada). Em paralelo: **42B5J** (Dashboard Conversation Simulator) para testar o E2E na UI e **42B7** (golden tests). Depois: 42I3 (normalizer), 42B6 (dispatch dry-run/HITL).
