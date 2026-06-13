# 42B5C — Customer Reply Slot Intake Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/envio externo/approval/dispatch/InfoCap/portal) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Auditoria realizada antes de editar
Lidos antes de qualquer alteração: `SPEC-005`, `SPEC-006`, `SPEC-004`, `42B5B-...report.md`; código `lib/attendance/corridor-runtime.ts`, `runtime/step/route.ts`, `[caseId]/route.ts`, `handoff-dossier/route.ts`, `lib/attendance/handoff-dossier.ts`, migration `20260612`.

**Princípios respeitados:** baixa fricção; pergunta mínima; não repetição (dedupe da pergunta do agente); uma resposta por vez; não confirmação de cobertura; não acionamento externo; sem WhatsApp real. `external_action_allowed=false` sempre.

## 1. Arquivos criados/alterados
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**novo**) — endpoint `POST`.
- `lib/attendance/corridor-runtime.ts` (**alterado**) — adicionados extratores seguros de slot: `extractSlotValue`, `clarificationForSlot`, tipos `SlotExtraction`/`SlotConfidence` (o motor `computeRuntimeStep`/`selectNextSlot` do 42B5B foi reutilizado, não reescrito).
- `docs/canon/design/2026-06-claude-design/42B5C-customer-reply-slot-intake-report.md` (este).

**UI não foi alterada.**

## 2. Endpoint criado
`POST /api/attendance/cases/[caseId]/runtime/reply`
- Auth padrão (Iron Session + `users_v2.company_id` via service role). `company_id` **sempre** da sessão.
- Body: `{ "message": "...", "source": "dashboard", "force": false }`. `message` obrigatório, `≤ 2000` chars (valida 400 se vazio/longo).
- Guarda: caso em `closed`/`cancelled`/`handoff` → **409 `case_not_runtime_editable`** (não reabre).

## 3. Como identifica o slot alvo
Ordem de prioridade (`resolveTargetSlot`):
1. `corridor_runs.diagnostics.runtime.selected_slot`;
2. `corridor_runs.last_agent_action` no formato `ask:<slot>`;
3. `selectNextSlot(filled)` (próximo faltante prioritário);
4. nenhum → `intake.status='no_slot_pending'` (computa estado e retorna sem falhar).

## 4. Como extrai valores por slot (heurística leve, segura, sem inventar)
- **risk_indicators** → `{ raw, has_immediate_risk, risk_level, signals[] }`. Detecta `fumaça/faísca/cheiro de queimado/choque/fogo/incêndio/derretendo/curto`. Com **negação** ("não", "sem", "nenhum", "tudo normal") → `low` mesmo citando os termos (ex.: "Não, sem cheiro de queimado nem faísca." → low). Sem negação e com sinal → `high`.
- **affected_area** → string limpa (truncada). Vazio/curto → ambíguo.
- **electrical_issue_type** → `{ raw, normalized }` com `breaker_tripping | no_power | outlet_issue | shower_issue | wiring_issue | other`.
- **property_address_confirmed** → `{ raw, confirmed: true|false }`. `true` (sim/confere/é esse); `false` (não/mudou/outro endereço) + conflict `address_not_confirmed`; "não sei/preciso verificar" → ambíguo.
- **policy_evidence_status** → `{ raw, status: provided|not_available|pending }`. **Não valida apólice, não consulta InfoCap.**
- Slot genérico → texto limpo, confiança baixa.

## 5. Risco alto
Se `risk_indicators` vier `high`: `attendance_cases.risk_level='high'` + `priority='high'` + `safety_note` "Risco elétrico alto detectado; orientar segurança e considerar handoff humano." **Sem handoff automático** (fica para 42B5E) e **sem acionamento externo**.

## 6. Como atualiza os slots
Lê `corridor_runs.slots = {filled, missing, conflicts}` e atualiza preservando o resto:
- sucesso → `filled[targetSlot]=valor`, remove de `missing`, remove conflicts antigos do slot (resolvido), adiciona conflict informativo se `address_not_confirmed`;
- ambíguo/vazio → **não** preenche, mantém em `missing`, adiciona conflict `{slot, reason:'ambiguous_reply', raw≤200}` e gera **clarificação curta** (re-pergunta o mesmo slot, `status='needs_clarification'`).

## 7. Como gera a próxima pergunta
Após preencher, chama `computeRuntimeStep` (mesmo helper do 42B5B) com os slots atualizados:
- próximo slot → gera próxima pergunta, grava `messages.role='assistant'` (com dedupe), atualiza `case.next_step` e `run.phase`/`next_step`/`last_agent_action='ask:<slot>'`;
- sem faltantes → `next_step` de conclusão, `status='policy_check'` (se em coleta), `last_agent_action='slots_complete'` — **não cria dispatch**.

## 8. Como evita atrito / repetição
- Uma resposta por vez; uma pergunta por vez.
- Pergunta do agente só é (re)gravada se `force=true` ou se diferir da última `assistant` (dedupe por conteúdo).
- Slots já preenchidos não são repetidos.

## 9. Mensagens (`messages`)
Com `conversation_id`: insere **user** (`role='user'`, `type='text'`) e, se houver, **assistant** com a próxima pergunta. Sem `metadata` (coluna inexistente). Sem `conversation_id` → não falha (retorna estado, `message_id=null`).

## 10. O que NÃO faz
Sem WhatsApp/envio externo; sem `dispatch_packet`; sem `approval_request`; sem InfoCap/portal/browser; sem confirmação de cobertura; sem alteração de banco/schema/migration, backend Python, RAG, prompts, agentes, UI; sem Supabase no client; sem pacote novo.

## 11. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · UI · backend Python · RAG · prompts · agentes | ✅ nenhum |
| WhatsApp/envio externo · approval · dispatch · InfoCap/portal | ✅ nenhum |
| token/secret/PII no diff | ✅ nenhum |

## 12. Deploy recomendado
- **Web apenas** (Next route handler + helper). Sem backend Python, sem SQL/migration.

## 13. Testes manuais (após deploy Web)
```js
const caseId = 'ID_DO_CASO';
// 1) gerar pergunta inicial
await fetch(`/api/attendance/cases/${caseId}/runtime/step`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ source:'dashboard' }) });
// 2) responder risco (baixo)
let r = await fetch(`/api/attendance/cases/${caseId}/runtime/reply`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ source:'dashboard', message:'Não, sem cheiro de queimado nem faísca.' }) });
console.log(r.status, await r.json());
```
**Esperado (2):** `target_slot=risk_indicators`, `filled=true`, `risk_level low`, próximo `selected_slot=affected_area`, próxima pergunta gravada. **GET detail:** `slots.filled.risk_indicators` presente, `missing` sem `risk_indicators`, `messages` com user+assistant, `next_step` = pergunta de affected_area.

**Alto risco (outro caso):** message "Tem cheiro de queimado e saiu uma faísca." → `extracted_value.risk_level='high'`, `case.risk_level='high'`, `case.priority='high'`, `safety_note` registrada, **sem acionamento externo**. **Chat Core inalterado** (CORE-001/006/007).

## 14. Próximos passos
- **42B5D/E** — clarificação avançada e condições de handoff automático (risco alto / rede externa / fora do corredor).
- **42B6** — Dispatch Packet + WhatsApp dry-run/HITL.
- Futuro: expor `extractSlotValue`/`computeRuntimeStep` como ferramentas do Attendance Agent/Smith.
