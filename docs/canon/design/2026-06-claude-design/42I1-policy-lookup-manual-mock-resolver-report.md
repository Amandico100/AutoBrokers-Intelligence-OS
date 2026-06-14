# 42I1 — Policy Lookup Manual/Mock Resolver Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/UI/WhatsApp/Vault real/InfoCap real/credenciais) · sem deploy automático.
> **Data:** 2026-06-14 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `lib/attendance/policy-lookup.ts` (**novo**) — helpers puros do contrato (`buildPolicyLookupResult`, `buildMockPolicyLookupResult`, `validatePolicyLookupInput`, `applyPolicyLookupResultToCasePayload`, `maskPolicyNumber`, `maskName`, `sanitizePolicySnapshot`, `safePolicyLookupSummary`, fixtures).
- `app/api/attendance/cases/[caseId]/runtime/policy-lookup/route.ts` (**novo**) — endpoint `POST`.
- `docs/canon/design/2026-06-claude-design/42I1-policy-lookup-manual-mock-resolver-report.md` (este).

Nenhum runtime existente foi alterado. UI/dashboard intactos.

## 2. Endpoint criado
`POST /api/attendance/cases/[caseId]/runtime/policy-lookup`
- Auth padrão (Iron Session + `users_v2.company_id` via service role). `company_id` **sempre** da sessão.
- Body **mock:** `{ "source":"mock", "mode":"mock", "fixture":"allianz_residential_electrician_covered" }`.
- Body **manual:** `{ "source":"manual", "mode":"manual", "policy_number", "insurer_key", "product", "line_kind", "policy_status", "coverage_summary", "limitations":[], "confidence", "human_required" }`.
- `force=true` permite resolver mesmo fora de `policy_lookup_required`.

## 3. Contrato implementado (`policy_lookup_result`)
Segue 42I0P: `status` (policy_selected | policy_evidence_ready | policy_multiple_matches | policy_not_found | policy_lookup_pending | policy_lookup_blocked) · `source` (manual|mock|infocap|connector|upload|human|unknown) · `source_ref` · `queried_document_type` · `matches[]` (mascarados) · `selected` · `coverage_evidence` (SPEC-005 §12.4) · `verification_status` · `next_macro_state` · `blockers[]` · `requires_human` · `notes`.

**Fixture obrigatória:** `allianz_residential_electrician_covered` → Allianz / residencial / produto Residencial / eletricista / apólice `active` / `coverage_evidence.confidence='medium'` / `verification_status='verified_by_human'` / `limitations` deixa claro que é mock (não consulta real).

**Modo manual:** com `coverage_summary` → `policy_evidence_ready` + `verified_by_human`; sem `coverage_summary` → `policy_lookup_pending` (`blocker=no_coverage_summary`, `requires_human=true`) — não destrava sem evidência.

## 4. Como mapeia no schema atual (sem tabela nova)
`applyPolicyLookupResultToCasePayload` grava nos campos existentes de `attendance_cases`:
| Campo | Valor |
|---|---|
| `policy_source` | `'manual'` (manual) / `'snapshot'` (mock) — ver nota abaixo |
| `policy_number` | número (mock `MOCK-ALLIANZ-RES-0001` / manual informado) |
| `policy_snapshot` | snapshot mínimo sanitizado (insurer/produto/ramo/status/`masked_policy_number`/source/note) |
| `coverage_evidence` | objeto de evidência (SPEC-005 §12.4) |
| `verification_status` | `verified_by_human` (evidência pronta) / `pending_human` (sem cobertura) |
| `next_step` | "Apólice/evidência registrada. Próximo passo: retomar o corredor de atendimento." |
| `metadata.attendance_macro_state` | `policy_evidence_ready` |
| `metadata.policy_lookup` | resumo seguro (status/source/verification/selected mascarado/matches_count) |

`corridor_runs`: `last_agent_action='policy_lookup:mock_verified'` (ou `:manual_verified`), `diagnostics.runtime.{macro_state=policy_evidence_ready, coverage_evidence_ready=true, external_action_allowed=false, policy_lookup=resumo}`.

> **Nota importante (schema CHECK):** `attendance_cases.policy_source` só aceita `manual|upload|snapshot|infocap|connector|human|unknown` (migração 20260612). **`mock` NÃO existe** no CHECK. Para **não** alterar schema, o modo mock persiste `policy_source='snapshot'` (snapshot canned), enquanto a origem real `'mock'` fica visível em `coverage_evidence.source`, `metadata.policy_lookup.source` e no `policy_lookup_result.source` retornado. O modo manual persiste `policy_source='manual'`. Se o Founder quiser um literal `policy_source='mock'`, isso exige um batch de migração para estender o CHECK.

## 5. O que ficou de fora (proposital)
- **Não** retoma o corredor nem gera próxima pergunta de slot → fica para **42B5H**.
- **Não** chama InfoCap real, **não** cria connector real, **não** acessa Vault real, **não** usa credenciais.
- **Não** cria tabela `policy_lookups`, SQL, migration, UI, dispatch, approval, WhatsApp.
- **Não** deixa a LLM afirmar cobertura — a cobertura vem só de `coverage_evidence`.

## 6. Segurança
- `company_id` sempre da sessão; nunca do body.
- Body rejeita campos sensíveis (`token`/`password`/`api_key`/`secret`/`credential`) → 400.
- `insured_document_ref` (CPF/CNPJ) **removido** da resposta (`safeCase`) e **nunca logado**; logs só `case`, `source`, `status`, `verification`, `macro`.
- `policy_number` e nome aparecem **mascarados** em `matches`/`snapshot` (`maskPolicyNumber`, `maskName`); `policy_snapshot` é mínimo e sanitizado.
- Sem `NEXT_PUBLIC` sensível; sem segredo/token na resposta.

## 7. Estados de erro
400 (body inválido/campo sensível) · 404 (caso inexistente/outra company) · 409 (`handoff`/`closed`/`cancelled`; ou não está em `policy_lookup_required`/`policy_check` sem `force`) · 422 (fixture desconhecida, lista `available`) · 500 (inesperado).

## 8. Alterou SQL/schema/backend Python/RAG/prompts/UI/WhatsApp?
**Não — nenhum.** Apenas 2 arquivos TS/Next novos + relatório. Reusa exclusivamente campos jsonb/colunas já existentes.

## 9. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema · backend Python · RAG · prompts/agentes · UI · WhatsApp · Vault/InfoCap real · credenciais | ✅ nenhum |
| dispatch · approval · Core · Auxiliares | ✅ intactos |
| CPF/secret/PII no diff/logs/resposta | ✅ nenhum (mascarado/omitido) |

## 10. Testes manuais (após deploy Web)
1. Criar caso → `reply 'Estou sem luz só na cozinha'` → `reply 'Não, sem cheiro de queimado nem faísca.'` → sistema pede CPF → enviar CPF → caso fica `policy_lookup_required`/`policy_check`.
2. Resolver mock:
```js
const caseId = 'ID_DO_CASO';
const res = await fetch(`/api/attendance/cases/${caseId}/runtime/policy-lookup`, {
  method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ source:'mock', mode:'mock', fixture:'allianz_residential_electrician_covered' })
});
console.log(res.status, await res.json());
```
**Esperado:** `200`; `verification_status` deixa de ser `unverified` (→ `verified_by_human`); `coverage_evidence` preenchido; `metadata.attendance_macro_state='policy_evidence_ready'`; `corridor_runs.last_agent_action='policy_lookup:mock_verified'`; `policy_source='snapshot'` (mock — ver §4) com `coverage_evidence.source='mock'`; `external_action.sent=false`; nenhum WhatsApp.
3. Manual: enviar `{source:'manual',mode:'manual',policy_number:'...',coverage_summary:'...'}` → `policy_evidence_ready`, `policy_source='manual'`.
4. Erros: fixture errada → 422; caso fora do gate → 409; body com `api_key` → 400.
5. Core/Auxiliares/RAG (NEVOA-791) intactos.

## 11. Próximo batch recomendado
**42B5H — Resume Corridor After Policy Lookup:** quando `coverage_evidence_ready=true` / `macro_state=policy_evidence_ready`, voltar `status` para `collecting_slots`, limpar o `policy_lookup:pending` e retomar os slots do corredor (`affected_area`, `electrical_issue_type`, …) via `computeRuntimeStep` + `macroGateOverride` (que agora retorna `null` porque o gate de apólice está resolvido). Depois: 42I2 (InfoCap read-only via Vault), 42I3 (normalizer), 42B5J (simulator), 42B7 (goldens), 42B6 (dispatch).
