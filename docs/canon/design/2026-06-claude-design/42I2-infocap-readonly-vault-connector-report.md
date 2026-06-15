# 42I2 — InfoCap Connector Read-only via Vault Report

> **Status:** concluído · typecheck verde · build verde · `node --check` verde · `git diff --check` limpo · **só TS/Next no Web/runtime** (sem SQL/schema/migrations, sem backend Python, sem RAG/prompts/WhatsApp/dispatch/approval, sem credenciais commitadas) · sem deploy automático.
> **Data:** 2026-06-15 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `lib/attendance/connectors/infocap-policy-lookup.ts` (**novo**) — adapter read-only + resolução via Vault `tenant_connections`.
- `app/api/attendance/cases/[caseId]/runtime/policy-lookup/route.ts` (**alterado**) — aceita `source:'infocap'`/`mode:'connector'`; refatora a persistência em `persistPolicyLookupResult` (reusado por mock/manual/connector).
- `scripts/attendance-golden-tests.mjs` (**alterado**) — cenário 8: InfoCap sem conexão não confirma cobertura.
- `docs/canon/design/2026-06-claude-design/42I2-infocap-readonly-vault-connector-report.md` (este).

## 2. Encontrou Vault/tenant_connections? **Sim**
Tabelas do Vault (39A1) existem e são usadas pelo Web (`app/api/vault/connections`): `connector_templates` (seed global **`infocap`**), `tenant_connections` (`company_id`, `connector_template_id`, `status`, `connection_config jsonb`, `encrypted_secret_ref` = **referência**, nunca o segredo). O adapter resolve a conexão da corretora por `connector_templates.slug='infocap'` + `tenant_connections(company_id, status='connected')` usando o admin client (server-side). **Não criei tabela nem migration.**

## 3. Encontrou configuração real do InfoCap no repo? **Não**
Não há, no repositório/envs, especificação verificada de endpoint/payload/response da API InfoCap (só uma coleção Postman externa). Conforme o requisito #3, **não inventei URL/payload/autenticação**.

## 4. Implementou chamada real ou só o contrato/adapter? **Adapter/contrato (fundação)**
O adapter é a **fundação read-only**:
- **Sem conexão ativa** → `blocked_not_configured`.
- **Conexão sem credenciais** (`encrypted_secret_ref` ausente) → `blocked_missing_credentials`.
- **Conexão + credenciais presentes** → `unsupported` (a chamada HTTP real read-only será implementada no próximo batch a partir da doc oficial).
- Erro ao resolver → `provider_error`.
Em **nenhum** caso fabrica evidência de cobertura nem confirma cobertura.

## 5. Sobre as credenciais piloto (decisão)
O Founder forneceu base_url (`https://api.corpnuvem.com`), login/senha das corretoras piloto (Resulta, AutoFleet) e um link Postman. **Decisão: NÃO usar/commitar essas credenciais neste batch.** Elas são **por corretora** (secrets de tenant) e devem ser inseridas em **Vault/`tenant_connections`** (referência em `encrypted_secret_ref`), não em código/env/RAG/log/diagnostics. A estrutura do conector é **global** (cada corretora pluga seu acesso). `base_url` pode virar default global (não-secreto) em `connection_config.base_url`/env `INFOCAP_BASE_URL` no batch da chamada real. **Nenhum segredo entrou no repositório.**

## 6. Contrato do adapter
`InfocapPolicyLookupResult { ok, status, source:'infocap', source_ref?, matches?, selected?, coverage_evidence?, verification_status?, blockers?, requires_human?, notes? }` com `status ∈ { found | not_found | multiple_matches | blocked_missing_credentials | blocked_not_configured | provider_error | unsupported }`. Quando (futuramente) `found` com `coverage_evidence`, a rota mapeia para `PolicyLookupResult { source:'connector', verification_status:'verified_by_connector' }` e persiste via `persistPolicyLookupResult` → `policy_source='connector'` (valor aceito pelo CHECK), `policy_snapshot` sanitizado, `coverage_evidence`, `macro_state=policy_evidence_ready`.

## 7. Como preservou mock/manual
`source:'mock'` e `source:'manual'` continuam **idênticos** (mesma validação e persistência). A detecção de `infocap`/`connector` ocorre antes do `validatePolicyLookupInput` (que é específico de mock/manual) e desvia para o adapter. A persistência foi extraída para `persistPolicyLookupResult` e é compartilhada — sem mudança de comportamento para mock/manual.

## 8. Sanitização e logs
- Adapter **nunca** retorna CPF/token/credencial/payload bruto/`policy_snapshot` cru — só campos resumidos/mascarados e flags (`status`, `blockers`, `notes`).
- A resolução de conexão lê apenas `status`/`connection_config`/existência de `encrypted_secret_ref` (booleano `hasSecretRef`), **nunca o valor do segredo**.
- Logs: `company_id`, `case_id`, `provider=infocap`, `status` — sem documento/segredo.
- Resposta da rota passa por `safeCase` (sem `insured_document_ref`).

## 9. Como testar
- **mock (inalterado):** `POST .../runtime/policy-lookup { source:'mock', mode:'mock', fixture:'allianz_residential_electrician_covered' }` → `verified_by_human`, `policy_evidence_ready`.
- **infocap sem conexão:** `POST .../runtime/policy-lookup { source:'infocap', mode:'connector' }` → `ok:false`, `policy_lookup_result.status='blocked_not_configured'`, **não** muda `verification_status`, atendimento segue aguardando validação. Não quebra.
- Golden cenário 8 cobre isso (skip sem `SESSION_COOKIE`).

## 10. O que falta para produção (próximo batch)
1. **Doc oficial InfoCap** (do Postman): endpoint de login (login/senha → token), endpoint de busca de segurado/apólice, parâmetros (CPF/CNPJ/telefone/número), e **response sample** para normalizar `matches`/`coverage_evidence`.
2. **Inserir credenciais piloto no Vault** (`tenant_connections` de Resulta/AutoFleet) — passo do Architect/Founder, fora do código.
3. Implementar a chamada HTTP read-only no adapter (auth → search → normalizar → `found`/`not_found`/`multiple_matches`), com timeout e tratamento de erro (já há os estados).
4. (Opcional) `INFOCAP_BASE_URL` como default global não-secreto.

## 11. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `node --check scripts/attendance-golden-tests.mjs` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/schema/migrations · backend Python · RAG/prompts · WhatsApp/dispatch/approval | ✅ nenhum |
| credenciais em código/log/diagnostics | ✅ nenhuma |

## 12. Houve SQL/schema? Chamada real ou bloqueio?
- **SQL/schema:** **não** (reusa Vault 39A1 + campos de `attendance_cases`).
- **Chamada real:** **não** — adapter retorna `blocked_not_configured`/`blocked_missing_credentials`/`unsupported`; a chamada real fica para o próximo batch com a doc oficial e credenciais no Vault.

## 13. Próximo recomendado
**42I2.1 — InfoCap Read-only Real Call** (implementar a chamada HTTP no adapter a partir da doc Postman, com credenciais no Vault/tenant_connections; manter mock/manual e os estados de erro). Em paralelo: **42B6 — Dispatch Packet dry-run/HITL**.
