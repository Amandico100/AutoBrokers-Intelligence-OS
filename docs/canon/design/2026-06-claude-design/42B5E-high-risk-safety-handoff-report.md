# 42B5E — High Risk Safety & Handoff Decision Layer Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/UI/WhatsApp/dispatch/approval/Vault/Auxiliares/Core) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Auditoria realizada antes de editar
Inspecionados os valores/status já usados: `attendance_cases.status` aceita `handoff` (CHECK), `corridor_runs.phase` aceita `handoff`, e as rotas de runtime já tratam `handoff` como status **não editável** (409). Por isso reusamos `status='handoff'` — sem inventar status novo, sem mexer em schema/CHECK.

## 1. Arquivos criados/alterados
- `lib/attendance/runtime-safety-policy.ts` (**novo**) — política pura `evaluateRuntimeSafetyDecision(input)`.
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — branch de segurança antes da coleta normal.
- `app/api/attendance/cases/[caseId]/runtime/step/route.ts` (**alterado**) — branch de segurança quando o caso já tem risco alto.
- `docs/canon/design/2026-06-claude-design/42B5E-high-risk-safety-handoff-report.md` (este).

`corridor-runtime.ts` e `runtime-slot-catalog.ts` **não** precisaram mudar (a detecção `detectHighRisk` já existia no catálogo e foi reutilizada).

## 2. Como a política de segurança foi implementada
`evaluateRuntimeSafetyDecision({ caseRow, targetSlot, extraction, filledSlots })` é **pura e testável** (sem I/O). Dispara quando:
- a extração do slot `risk_indicators` retornou `riskHigh === true` (resposta atual), **ou**
- os slots já preenchidos contêm `risk_indicators` com indício de risco alto (`detectHighRisk`).

Quando dispara, retorna a decisão:
```
{ triggered:true, reason:'high_risk_electrical', risk_level:'high', priority:'high',
  handoff_required:true, handoff_reason:'high_risk_electrical', stop_normal_collection:true,
  assistant_message:'Entendi. Como você mencionou cheiro de queimado/faísca, por segurança não toque em tomadas, fios ou quadro. Afaste as pessoas do local e, se for seguro fazer isso, desligue o disjuntor geral. Vou tratar como prioridade e encaminhar com as informações necessárias.',
  next_step:'Risco elétrico alto detectado. Preparar dossiê e transferir para suporte humano configurado.',
  last_agent_action:'safety_handoff:risk_indicators', safety_note:'...' }
```
A mensagem é curta, calma, humana, sem termos internos, sem prometer cobertura/acionamento.

## 3. O que acontece com high risk (`/runtime/reply`)
1. grava `user`; 2. preenche `risk_indicators` e remove de `missing`; 3-7. marca `priority='high'`, `risk_level='high'`, `handoff_required=true`, `handoff_reason='high_risk_electrical'`, `status='handoff'`; 8. **não** computa/pergunta o próximo slot normal; 9. grava **uma** mensagem `assistant` de segurança (com dedupe); 10-12. `attendance_cases.next_step` e `corridor_runs.next_step` viram o passo de handoff, `corridor_runs.last_agent_action='safety_handoff:risk_indicators'`, `phase='handoff'`; 13. `diagnostics.runtime` recebe `safety_decision.triggered=true`, `reason='high_risk_electrical'`, `selected_slot=null`, `external_action_allowed=false`, `slot_priority_source` preservado, `safety_notes` acrescidas.

`/runtime/step` aplica a **mesma** política se o caso já tiver risco alto e ainda não estiver bloqueado: responde com a orientação de segurança (não pergunta `affected_area`), marca handoff e retorna `step.status='safety_handoff'`.

## 4. Low risk permanece inalterado
`evaluateRuntimeSafetyDecision` retorna `{triggered:false}` quando não há risco alto → o fluxo segue exatamente como no 42B5D: step pergunta risco → reply "Não, sem cheiro…" preenche low risk → próxima pergunta `affected_area` → reply de área → `electrical_issue_type`; `priority` normal, `risk_level` low. Nenhuma mudança de comportamento.

## 5. Qual status foi usado e por quê
**`status='handoff'`** — já existe no CHECK de `attendance_cases`, já é reconhecido pela UI/API e as rotas de runtime já o tratam como **não editável** (retornam 409). Isso garante, sem schema novo, que após risco alto o runtime **não continua** a coleta. `corridor_runs.phase` também vai para `handoff` (valor já válido).

## 6. Side effects que NÃO acontecem
Sem WhatsApp/envio externo; **não** cria `dispatch_packet`; **não** cria `approval_request`; **não** consulta InfoCap/portal; **não** confirma cobertura; **não** gera/“envia” dossiê automaticamente (nem chama o endpoint de handoff-dossier); sem alteração de SQL/schema/migration, backend Python, RAG, prompts/agentes, UI, Vault, Auxiliares, Core. `external_action_allowed=false` sempre.

## 7. Idempotência
A mensagem de segurança só é inserida se `force=true` ou se a última `assistant` for diferente dela. Como o caso passa a `handoff`, chamadas seguintes de `/runtime/step` ou `/runtime/reply` retornam **409** (`case_not_runtime_editable`).

## 8. Logs seguros
Sem telefone, sem mensagem do cliente, sem slots completos, sem `destination_ref`/PII. Apenas `case`, `safety_handoff/reason`, `message_id` (step) e `target_slot/next_slot/ids` (reply).

## 9. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · backend Python · RAG · prompts/agentes · UI · WhatsApp | ✅ nenhum |
| dispatch · approval · Vault · InfoCap/portal · dossiê automático | ✅ nenhum |
| Core chat / Auxiliares | ✅ inalterado |
| token/secret/PII no diff | ✅ nenhum |

## 10. Testes manuais (após deploy Web)
**Test A — low risk intacto:** criar caso → `step` → `reply` "Não, sem cheiro de queimado nem faísca." → `reply` "É só na cozinha." → esperado: `risk_level low`, `priority normal`, próximo slot `electrical_issue_type`, **não** handoff.

**Test B — high risk para o fluxo:** criar caso → `step` → `reply` "Tem cheiro de queimado e saiu uma faísca." → esperado: 200, `case.priority=high`, `case.risk_level=high`, `case.handoff_required=true`, `case.handoff_reason=high_risk_electrical`, `case.status=handoff`, `next_step` = preparar dossiê/handoff, assistant = orientação de segurança, **não** pergunta `affected_area`, `corridor_run.last_agent_action=safety_handoff:risk_indicators`, `diagnostics.runtime.safety_decision.triggered=true`, `external_action_allowed=false`.

**Test C — step após handoff:** `step` no caso de alto risco → **409** (`case_not_runtime_editable`), não cria pergunta, não reabre.

**Test D — Core regression:** Core interno + Auxiliares (Resumo de Atendimentos + Follow-up WhatsApp) + RAG NEVOA-791 intactos.

## 11. Deploy recomendado
- **Web apenas** (route handlers + helper puro). Sem backend Python, sem SQL/migration.

## 12. Próximos passos
- **42B6** — Dispatch Packet + WhatsApp dry-run/HITL (e, no handoff de risco alto, geração do dossiê + transferência ao destino humano configurado em 42H1–H5).
- Eventual `42B5F` — first response/saudação inicial; refinamento de condições de handoff (rede externa/concessionária, eletrodoméstico fora do corredor).
