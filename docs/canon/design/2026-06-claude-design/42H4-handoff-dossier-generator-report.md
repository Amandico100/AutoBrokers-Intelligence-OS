# 42H4 — Handoff Dossier Generator Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/UI) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados
- `app/api/attendance/cases/[caseId]/handoff-dossier/route.ts` (**novo**) — `GET` que gera o dossiê.
- `lib/attendance/handoff-dossier.ts` (**novo**) — `maskPhone`, `normalizeSlots`, `buildHandoffDossier`, `formatHandoffMarkdown`.
- `docs/canon/design/2026-06-claude-design/42H4-handoff-dossier-generator-report.md` (este).

## 2. Endpoint criado
`GET /api/attendance/cases/[caseId]/handoff-dossier` — autenticação no padrão da 42B5A (Iron Session + `users_v2.company_id` + service role server-side). Caso buscado por **id + company_id**; 404 se não existir.

## 3. Dados usados no dossiê
- **attendance_cases** (campos seguros): número, status, prioridade, risco, intenção, seguradora, ramo, macro, corredor/subcorredor, policy_source/number, verification_status, **coverage_evidence (só status registered/not_verified)**, handoff_required/reason, summary, next_step, customer_name/phone.
- **conversation/messages**: contagem + última mensagem `role='user'` (trecho ≤200 chars). Não inclui histórico inteiro.
- **último corridor_run** (fase/status/slots/diagnostics/next_step) + **corridor_template** (display_name/keys/readiness).
- **dispatch_packets**: contagem + statuses (sem criar nenhum).
- **human_support_destinations** ativos: **primary** primeiro + **fallbacks** por `priority_order` (colunas seguras; **sem destination_ref cru**; usa `display_ref`).
- Saída: JSON estruturado (`dossier`) + **`dossier.markdown`** copiável.

## 4. Estratégia de PII
- Inclui `customer_phone` **apenas se já existir** em `attendance_cases.customer_phone` (o humano precisa continuar o atendimento). Helper `maskPhone` disponível para usos que exijam máscara.
- **Nunca** inclui: CPF/`insured_document_ref`, `policy_snapshot` cru, token/secret, `destination_ref` cru, prompt/config/agent internals.
- **Logs seguros:** `case`, `company`, `hasDestination`, `message_count` — **nunca** telefone/destination_ref/markdown/slots completos.

## 5. Estratégia de destino humano
- Seleciona destinos **ativos** da corretora (query `is_active=true`, ordem `is_primary desc`, `priority_order asc`): **primary** = primeiro com `is_primary`; **fallbacks** = demais ativos.
- Objeto slim por destino: `id, name, destination_type, channel_provider, display_ref, is_primary, fallback_enabled, silence_minutes` — **nunca** `destination_ref` cru.
- Sem destino ativo → `support_destination.configured=false` e o markdown diz **"Destino humano ainda não configurado."**

## 6. Confirmações de comportamento
- **NÃO envia WhatsApp / mensagem** — `external_action.sent=false`, nota "Nenhuma mensagem foi enviada neste endpoint."
- **NÃO cria** `approval_request` nem `dispatch_packet` (apenas **lê** dispatch para contagem).
- **NÃO altera** banco/schema/Supabase/backend Python/RAG/prompts/agentes/UI/WhatsApp.

## 7. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| UI / backend Python / Supabase no client | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo/approval/dispatch criado | ✅ nenhum |
| token/secret/`destination_ref` cru no diff | ✅ nenhum |

## 8. Deploy recomendado
- **Web apenas** (Next route handler). Sem backend Python, sem SQL/migration.

## 9. Testes manuais (após deploy Web)
```js
const caseId = 'ID_DE_UM_CASO';
const res = await fetch(`/api/attendance/cases/${caseId}/handoff-dossier`);
const data = await res.json();
console.log(res.status, data);
console.log(data.dossier.markdown);
```
Esperado: status **200**; `dossier.case_number` preenchido; `dossier.slots.filled`/`missing`; `support_destination.configured=true` se houver destino ativo; `primary.display_ref` **mascarado**; **`destination_ref` cru NÃO aparece**; `external_action.sent=false`; `markdown` gerado. Caso sem destino ativo → `configured=false` e markdown "Destino humano ainda não configurado.". Chat Core inalterado (CORE-001/006/007).

## 10. Próximos passos
1. **42H5** — botão **copiar dossiê / dry-run handoff** no detalhe do caso (`CaseDetailClient`), consumindo este endpoint; o dry-run criará `approval_request` (HITL), **sem envio real**.
2. Depois: **42B5B** (Corridor Runtime Step Engine), **42B6** (Dispatch + WhatsApp dry-run/HITL).
