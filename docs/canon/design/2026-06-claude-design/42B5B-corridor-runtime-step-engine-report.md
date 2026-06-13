# 42B5B — Corridor Runtime Step Engine Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/envio externo/approval/dispatch/InfoCap/portal) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Auditoria realizada antes de editar
Foram lidos antes de qualquer alteração:
- `docs/canon/SPEC-005-atendimento-runtime-architecture.md` (runtime = estado + workflow estruturado dentro do Smith; corredor estruturado, não RAG; HITL para ação externa; nunca cobertura sem fonte; uma pergunta por vez; provider de WhatsApp é detalhe de canal).
- `docs/canon/SPEC-006-...` e `SPEC-004-...` (família Allianz Residencial / Eletricista; Context Package attendance-v1).
- `docs/canon/design/2026-06-claude-design/42H5-handoff-dossier-ui-report.md`.
- `docs/canon/qa/CORE-REGRESSION-001-autobrokers-core-mvp.md`.
- Código: `app/api/attendance/cases/route.ts`, `.../[caseId]/route.ts`, `.../handoff-dossier/route.ts`, `CaseDetailClient.tsx`, `HandoffDossierPanel.tsx`, migrations `20260612`/`20260613` e `schema_completo.sql` (tabela `messages`).

**Achados que guiaram a implementação:**
- `attendance_cases.status` aceita `policy_check` (CHECK), então a conclusão de coleta usa `policy_check`.
- `corridor_runs.slots` é `{ filled:{...}, missing:[...], conflicts:[...] }` (confirmado no POST de criação de caso).
- `messages` (Smith): colunas `conversation_id, role (CHECK user|assistant), content, type (CHECK text|voice)`, **sem** `metadata`/`company_id` → inserimos só `conversation_id, role='assistant', content, type='text'`.
- Todo caso criado em 42B5A já nasce com um `corridor_run` ativo (`phase='collect_slots'`).

**Princípios respeitados (documentados):** pergunta mínima; baixa fricção; não repetição; uma pergunta boa por vez; sem confirmação de cobertura sem fonte; sem acionamento externo; sem WhatsApp real.

## 1. Arquivos criados
- `lib/attendance/corridor-runtime.ts` (**novo**) — motor determinístico puro (sem I/O): `ELECTRICIAN_SLOT_PRIORITY`, `RUNTIME_ENGINE`, `isSlotFilled`, `selectNextSlot`, `questionForSlot`, `detectHighRisk`, `computeRuntimeStep`.
- `app/api/attendance/cases/[caseId]/runtime/step/route.ts` (**novo**) — endpoint `POST` que lê estado, chama o motor, grava mensagem/diagnostics/next_step.
- `docs/canon/design/2026-06-claude-design/42B5B-corridor-runtime-step-engine-report.md` (este).

**UI não foi alterada** (preferência do batch: API/helper apenas).

## 2. Endpoint criado
`POST /api/attendance/cases/[caseId]/runtime/step`
- Auth padrão 42B5A (Iron Session + `users_v2.company_id` via service role server-side). `company_id` **sempre** derivado da sessão — nunca do body.
- Body opcional: `{ "source": "dashboard", "force": false }`.
- Isolamento por `company_id` em todas as queries.

## 3. Como escolhe o próximo slot
Prioridade segura (Allianz Eletricista MVP), risco físico antes de dados administrativos:
1. `risk_indicators` 2. `affected_area` 3. `electrical_issue_type` 4. `property_address_confirmed` 5. `policy_evidence_status`.

`selectNextSlot` percorre a prioridade e retorna o **primeiro não preenchido**. `isSlotFilled` trata `false`/`0` como preenchido, e string vazia/objeto vazio como **não** preenchido (ex.: `risk_indicators: {}` ainda conta como faltante).

## 4. Como reduz atrito e evita repetição
- **Uma pergunta por vez:** o motor gera no máximo **uma** pergunta por passo.
- **Não pede o que já existe:** slots já preenchidos (ex.: `problem_description`, `contact_name`, `contact_phone` vindos da criação) são pulados.
- **Não repete:** só insere a mensagem se `force=true` **ou** se a última mensagem `assistant` da conversa for diferente da pergunta atual (dedupe por conteúdo). A pergunta continua retornada no JSON mesmo quando não reinserida.
- **Humanização:** perguntas curtas, empáticas, sem termos internos (`slot`, `corridor_run`, `dispatch`). A abertura de `risk_indicators` é levemente contextualizada se `problem_description` menciona termos elétricos.

## 5. Como atualiza next_step / status / diagnostics
- **`attendance_cases.next_step`** = a pergunta gerada (ou a mensagem de conclusão segura).
- **`attendance_cases.status`**: `new`/`triage` → `collecting_slots`; ao concluir todos os slots e estando em fase de coleta → `policy_check`. **Nunca** reabre `closed`, **nunca** remove `handoff`, **nunca** mexe em `cancelled` (esses retornam **409 `case_not_runtime_editable`**).
- **`corridor_runs.diagnostics`** (merge, preservando o anterior):
  ```
  mvp_mode, hitl_required:true, external_action_allowed:false,
  runtime: { last_step_at, selected_slot, question_generated,
             external_action_allowed:false, channel, engine:'corridor_runtime_step_v1', safety_notes:[...] }
  ```
- **`corridor_runs.phase`**: avança fases de intake → `collect_slots` ao perguntar; → `readiness_check` ao concluir. `next_step` e `last_agent_action` (`ask:<slot>` ou `slots_complete`) também atualizados.
- **Sem run?** O endpoint não falha: ainda calcula a pergunta, grava a mensagem e atualiza o caso; apenas não persiste diagnostics (não cria run — fora do escopo deste batch).

## 6. Como grava a mensagem
Se `conversation_id` existir e houver pergunta (e não for repetição), insere em `messages`: `conversation_id`, `role='assistant'`, `content=pergunta`, `type='text'`. Sem `metadata` (coluna inexistente). Sem `conversation_id` → não falha, retorna a pergunta e registra em diagnostics/next_step.

## 7. Tratamento de risco
`detectHighRisk(risk_indicators)` sinaliza risco elétrico alto (faísca/fumaça/cheiro de queimado/choque, flags booleanas ou `risk_level high/critical`) e adiciona em `diagnostics.runtime.safety_notes` que o caso exige atenção/handoff humano. **Não** implementa handoff automático neste batch (apenas prepara a estrutura).

## 8. O que NÃO faz
- Não envia WhatsApp / nenhuma mensagem externa.
- Não cria `dispatch_packet` nem `approval_request`.
- Não aciona seguradora, portal, browser automation nem InfoCap.
- Não confirma cobertura (`external_action_allowed=false` sempre).
- Não altera banco/schema/migration, backend Python, RAG, prompts, agentes, WhatsApp.
- Não chama Supabase no client; não cria UI; não instala pacote.

## 9. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / RAG / prompts / agentes | ✅ nenhum |
| WhatsApp/envio externo/approval/dispatch/InfoCap/portal | ✅ nenhum |
| Supabase no client / UI nova / pacote novo | ✅ nenhum |
| token/secret/PII no diff | ✅ nenhum |

## 10. Deploy recomendado
- **Web apenas** (Next route handler + helper). Sem backend Python, sem SQL/migration.

## 11. Testes manuais (após deploy Web)
```js
const caseId = 'ID_DE_UM_CASO_COLLECTING_SLOTS';
const res = await fetch(`/api/attendance/cases/${caseId}/runtime/step`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ source: 'dashboard' }),
});
const data = await res.json();
console.log(res.status, data);
```
**Esperado:** `200`; `step.selected_slot` = primeiro slot faltante prioritário (caso novo → `risk_indicators`); `step.question` humanizada; `external_action_allowed=false`; `attendance_cases.next_step` atualizado; `corridor_runs.diagnostics.runtime` preenchido; se `conversation_id` existir, `message_id` preenchido (mensagem `assistant` criada). Repetir sem `force` → não duplica a mesma pergunta. Quando todos os slots prioritários estiverem preenchidos → `step.status='no_missing_slots'`, `question=null`, `next_step` de conclusão e (se em coleta) `status='policy_check'`. Caso `closed/handoff/cancelled` → **409** `case_not_runtime_editable`. Abrir o detalhe do caso: a conversa deve listar a pergunta (o GET detail já retorna `messages`). **Chat Core inalterado** (CORE-001/006/007).

## 12. Próximos passos
1. **42B6** — Dispatch Packet + WhatsApp dry-run/HITL (usa o destino primário/fallback de 42H1–H3; cria `dispatch_packet` + `approval_request`, sem envio real).
2. **42B7** — Golden tests do corredor.
3. Integração futura: expor `computeRuntimeStep` como ferramenta chamável pelo Attendance Agent/Smith.
