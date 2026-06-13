# 42B5A — Attendance Case Runtime API Foundation Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema/migration, sem backend Python, sem LangGraph/RAG/prompts/agentes/WhatsApp) · sem deploy automático.
> **Data:** 2026-06-12 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `app/api/attendance/cases/route.ts` (**novo**) — `GET` (listar) + `POST` (criar caso).
- `app/api/attendance/cases/[caseId]/route.ts` (**novo**) — `GET` (detalhe) + `PATCH` (atualização mínima).
- `lib/attendance/case-number.ts` (**novo**) — helper `generateCaseNumber()` (`ATD-YYYYMMDD-HHMMSS-XXXX`).
- `docs/canon/design/2026-06-claude-design/42B5A-attendance-case-runtime-api-report.md` (este).

## 2. Endpoints criados
| Método | Rota | Função |
|---|---|---|
| GET | `/api/attendance/cases` | Lista casos da corretora (status?, limit?, q?), ordenados por `updated_at desc`. |
| POST | `/api/attendance/cases` | Cria caso manual/dry-run: conversation (opcional) + `attendance_cases` + `corridor_run` inicial. |
| GET | `/api/attendance/cases/[caseId]` | Detalha caso: case + conversation + messages + corridor_run + corridor_template + dispatch_packets. |
| PATCH | `/api/attendance/cases/[caseId]` | Atualiza mínimo: status/priority/summary/next_step/handoff_required/handoff_reason. |

## 3. Fluxo implementado (POST)
1. Deriva `company_id` do usuário logado (`users_v2`) — **nunca** do body.
2. Resolve o **Attendance Agent** da empresa (`agent_role='attendance'`, `is_active`, preferindo slug `attendance-sandbox`). Se não existir → `assigned_agent_id = null` (não bloqueia).
3. Resolve o **template global** `corridor_templates` (`corridor_key='allianz_residential_assistance'`, `subcorridor_key=selected||'electrician'`, `is_active`, `company_id IS NULL`). 404 se não encontrado.
4. Cria **conversation** (se `create_conversation !== false`) no padrão de `/api/conversations` (+ `channel='dashboard'`, `session_id=crypto.randomUUID()`).
5. Cria **attendance_cases** com os defaults do MVP (status `collecting_slots`, insurer `allianz`, line `residential`, macro `residential_assistance`, corridor `allianz_residential_assistance`, subcorridor escolhido, `policy_source='unknown'`, `verification_status='unverified'`, `risk_level='low'`, `handoff_required=false`, summary/next_step) + `case_number` único.
6. Cria **corridor_run** (`phase='collect_slots'`, `status='active'`) com `slots.filled` (problem_description/contact_name/contact_phone quando enviados) e `slots.missing` derivado de `template.required_slots`; `diagnostics` marca `external_action_allowed=false`, `hitl_required=true`, `mvp_mode='dry_run_hitl'`.
7. Retorna `{ case, corridor_run, corridor_template, conversation_id }`.

## 4. Tabelas usadas (somente leitura/escrita de linhas; sem DDL)
`users_v2` (read), `agents` (read), `corridor_templates` (read), `conversations` (insert), `attendance_cases` (insert/list/get/update), `corridor_runs` (insert/get), `messages` (read), `dispatch_packets` (read). **Nenhuma** alteração de schema/migração.

## 5. Decisões de segurança
- **Multi-tenant rígido:** `company_id` sempre derivado de `users_v2` pela sessão; todos os GET/PATCH filtram por `company_id` (isolamento por corretora).
- **Service role** só no servidor (route handler), nunca exposto ao client.
- **Logs seguros:** apenas ids/status/contagens; **nunca** prompt/config/token/segredo/PII.
- **`q` sanitizado** (remove `,()%*`) para não quebrar a sintaxe do PostgREST `.or()`.
- **Sem ação externa:** não envia WhatsApp, não aciona seguradora, não toca InfoCap/portal. `external_action_allowed=false`.
- **`messages.role` inalterado** (mapeamento segurado→user, agente→assistant permanece para batches futuros).

## 6. O que NÃO foi implementado (fora de escopo)
Runtime LangGraph / Attendance agent invocando o corredor; geração de dispatch_packet + HITL; UI de Fila/Casos/Conversas; envio WhatsApp/portal/InfoCap; alterações no Core. (Ficam para 42B5/42B4/42B6.)

## 7. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| banco/SQL/schema/migration | ✅ nenhum |
| backend Python | ✅ nenhum |
| RAG/prompts/agentes/LangGraph/WhatsApp | ✅ nenhum |
| segredo/PII em log/diff | ✅ nenhum |

## 8. Deploy recomendado
- **Web apenas** (Next route handlers). Sem backend Python, sem SQL/migration, sem reupload.

## 9. Testes manuais (após deploy Web)
1. **POST** `/api/attendance/cases` `{ "customer_name":"Cliente Teste","customer_phone":"5547999999999","problem_description":"Estou sem luz só na cozinha","channel":"dashboard","priority":"normal","selected_subcorridor_key":"electrician","create_conversation":true }` → cria case + conversation + corridor_run; `selected_subcorridor_key='electrician'`; `verification_status='unverified'`; sem ação externa.
2. **GET** `/api/attendance/cases` → o caso aparece na lista.
3. **GET** `/api/attendance/cases/{caseId}` → retorna case + corridor_run + corridor_template (Allianz Eletricista) + messages (vazio/inicial) + dispatch_packets (vazio).
4. **Chat Core** (`/dashboard/chat`): CORE-001 (assistente interno), CORE-007 (Resumo + Follow-up), CORE-006 (NEVOA-791) — inalterado.

## 10. Próximos passos
1. **42B5** — runtime assistido do corredor (Attendance agent + LangGraph + Context Package; ler `corridor_run.slots`, perguntar 1 dado por vez; HITL via `approval_requests`).
2. **42B4** — UI Fila/Casos/Conversas consumindo esta API.
3. **42B6** — dispatch_packet + WhatsApp dry-run/HITL.
4. Rodar **CORE-REGRESSION-001** após o deploy.
