# 42I3A — InfoCap Policy Selection, Detail Loading & Evidence Pack Report

> **Status:** concluído · `py_compile` verde · `typecheck` verde · `node --check` verde · **testes unitários 37/37 verdes** · build verde · `git diff --check` limpo · **backend Python + adapter/route/normalizer TS + UI + testes + docs** (sem SQL/migration, sem confirmar cobertura sem itens/coberturas, sem RAG/LLM decidindo cobertura, sem WhatsApp/dispatch, sem acionar seguradora/prestador, sem PII/segredo exposto/logado) · sem deploy automático.
> **Data:** 2026-06-16 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. O que foi resolvido
A camada MVP de apólice InfoCap agora fecha o ciclo **cliente → apólices → seleção → detalhe → evidência estruturada → retomada do atendimento**, sem motor paralelo e sem inventar cobertura. Eu mesmo testei o que é testável localmente (normalizadores puros com fixtures sanitizadas, typecheck, py_compile, build). O teste com **CPF real** continua dependendo de backend deployado + Vault da corretora (não há credencial global), mas a lógica de interpretação foi validada com fixtures que reproduzem o shape real (ALLI/RESI, `Recebido e não entregue ao cliente`, vigências, cancelado).

## 2. Arquivos alterados/criados
- `backend/app/api/infocap_connector.py` (**alterado**) — `active_now`/`expired` (parser de data flexível), ordenação de apólices, flags de cliente em todos os desfechos, **novo endpoint `POST /attendance/connectors/infocap/policy-detail`** + builder `_build_evidence_pack` + sinais de assistência.
- `lib/attendance/connectors/infocap-policy-lookup.ts` (**alterado**) — match enriquecido (`active_now`/`expired`/`valid_from`/`valid_to`/`coverages_count`/`cancelled`), tipos `InfocapEvidencePack`/`InfocapPolicyDetailResult`, **nova função `loadInfocapPolicyDetail`**, forward de `prefer_insurer`/`prefer_product`.
- `lib/attendance/policy-evidence-pack.ts` (**novo**) — normalizadores PUROS: `buildPolicyEvidencePackFromDocument`, `normalizeEvidencePack`, `evidencePackToCoverageEvidence`, `coverageSummaryFromPack`, `buildPolicyInterpretationContext`, `safeEvidencePackSummary`.
- `app/api/attendance/cases/[caseId]/runtime/policy-select/route.ts` (**novo**) — seleção segura de apólice.
- `app/api/attendance/cases/[caseId]/runtime/policy-lookup/route.ts` (**alterado**) — persiste `matches` mascarados + `client_ref_available` no `metadata.policy_lookup`.
- `app/dashboard/atendimentos/casos/[caseId]/AttendanceConversationSimulator.tsx` (**alterado**) — botão "Consultar InfoCap (real)" + painel de seleção de apólice + ação de selecionar.
- `scripts/infocap-evidence-pack.test.mjs` (**novo**) + `scripts/fixtures/infocap-policy.fixtures.mjs` (**novo**) — testes offline + fixtures sanitizadas.
- `package.json` (**alterado**) — script `test:infocap-evidence`.
- `docs/canon/design/2026-06-claude-design/42I3A-...md` (este).

## 3. Partes do ResultVision usadas (referência, não cópia)
Mantida a cadeia já confirmada em 42I2.1D: `/login` → `/cliente_cpf` → `/cliente_ligacoes?codigo` → fallback `/documentos?codfil&texto` → **`/documento?codfil&nosnum`** (detalhe). O 42I3A apenas isola o último passo (`/documento`) em um endpoint dedicado `policy-detail` e adiciona a normalização de evidência. Status de apólice (`cancelado` truthy; `sit_acompanhamento_txt`) segue `resolveInfocapPolicyStatus`. Nenhuma arquitetura/motor antigo foi copiado.

## 4. Correção de flags e estados (req.1)
- `infocap_client_found = true` e `client_ref_available` agora vêm em **todos** os desfechos com `client_ref` (`client_found`, `multiple_matches`, `found`) via `client_flags` reutilizado.
- `multiple_matches` **não** cria `coverage_evidence`; `verification_status` permanece `unverified` até a seleção.
- `coverage_evidence: {}` evitado: as rotas gravam `null` (nunca `{}`); o detalhe do caso já trata `Object.keys(coverage_evidence).length > 0`, então `{}` legado nunca é exibido como evidência.

## 5. Múltiplas apólices melhoradas (req.2)
`multiple_matches` retorna até **5** apólices mascaradas com: `policy_ref`, `masked_policy_number`, `insurer_key`, `product`, `policy_status`, `valid_from`, `valid_to`, `active_now` (true/false/null=unknown), `expired`, `coverages_count`, `cancelled`. **Ordenação** (`_policy_sort_key`, `reverse=True`): vigentes/ativas → não canceladas → fim de vigência mais futuro → preferência seguradora/produto (`prefer_insurer`/`prefer_product`). **Não auto-seleciona** quando há mais de uma apólice ativa.

## 6. Endpoint de seleção (req.3) — `POST /api/attendance/cases/[caseId]/runtime/policy-select`
Body `{ source:'infocap', policy_ref:'97652' }`. Fluxo: autentica sessão → carrega caso (isolado por `company_id`) → **valida** que `policy_ref` está nos `matches` anteriores (`metadata.policy_lookup.matches`) **ou recarrega** pelo conector → `loadInfocapPolicyDetail` (codfil de `client_ref`) → normaliza pack → persiste `policy_snapshot` sanitizado + `coverage_evidence` estruturado, seta `verification_status='verified_by_connector'`, `policy_source='connector'`, `metadata.attendance_macro_state='policy_evidence_ready'`, `next_step` de continuação. `policy_ref` inválido → `409 policy_ref_not_in_matches`. Nunca expõe payload bruto/CPF/segredo.

## 7. Backend policy-detail (req.4)
`POST /attendance/connectors/infocap/policy-detail` (input interno `company_id`, `tenant_connection_id`, `codfil`, `policy_ref`): valida conexão+template InfoCap → decifra credencial (Fernet) → `/login` → `GET /documento?codfil&nosnum=policy_ref` → `_extract_documents` → `_build_evidence_pack`. Retorna `policy` (sanitizada) + `policy_evidence_pack` + `verified_at`. Erros mapeados: `auth_error`/`not_found`/`provider_error`/`blocked_*`. Log: `company`, `connection`, `endpoint`, `status`, `selected_policy_ref`, `duration_ms` (sem PII/segredo).

## 8. Policy Evidence Pack (req.5)
Objeto estruturado e sanitizado: `policy_found`/`policy_selected`, `policy_ref`, `masked_policy_number`, `insurer_detected`, `product_detected`, `line_kind_detected`, `policy_status`, `active_now`, `expired`, `valid_from/to`, `holder_name_masked`, `risk_address_summary_masked`, `object_summary`, `coverage_sections[]` (label+amount), `coverages_count`, `cancelled`, `assistance_signals {residential, electrician, emergency_assistance}` (true/false/null), `confidence`, `human_required`, `limitations[]`. **Regras de confiança:** cancelada/não-vigente → `low`; sinais positivos + coberturas → `high`; coberturas sem sinais → `medium`; **sem itens/coberturas → `low` e cobertura específica NÃO confirmada** (registra limitação). A lógica TS (`buildPolicyEvidencePackFromDocument`) espelha o backend e é coberta por testes.

## 9. Inteligência do agente sem motor paralelo (req.6)
`buildPolicyInterpretationContext` monta um `policy_interpretation_context` seguro (persistido em `metadata.policy_interpretation_context`): resumo da apólice, `coverage_confirmed` (true só com coberturas + não cancelada + vigente), `evidence_found`, `gaps[]`, `insured_question` e `rules[]` ("diferencie apólice localizada de cobertura confirmada", "não invente", "se ambíguo, peça validação humana"). É **helper puro/future-ready**: não cria motor LLM novo. Conectá-lo à resposta do Smith fica para um próximo batch (42I3B) — registrado abaixo.

## 10. Runtime após seleção (req.7)
Após `policy-select` com sucesso: `macro_state='policy_evidence_ready'`, `coverage_evidence_ready=true` no run, `last_agent_action='policy_select:connector_verified'`, e `next_step` = *"Apólice selecionada e registrada. Próximo passo: confirmar endereço do atendimento e dados mínimos para acionamento."* Como o gate de identidade/apólice já está satisfeito (`verified_by_connector`), `evaluateAttendanceMacroState` libera o corredor — **não pede CPF/apólice de novo**.

## 11. UI/Simulador (req.8)
No simulador: botão **"Consultar InfoCap (real)"** (lookup) e, quando há `metadata.policy_lookup.matches` e o caso ainda não está `policy_evidence_ready`, um **painel de seleção** lista as apólices mascaradas (seguradora/produto/nº/status/vigência/cancelada/coberturas) com botão **Selecionar** → chama `policy-select` → recarrega o caso. MVP funcional, sem design final.

## 12. Testes que rodei (req.9, 11) — **eu mesmo executei**
- `node scripts/infocap-evidence-pack.test.mjs` → **37/37 verdes**. Cobre: detalhe sem cobertura (existência≠cobertura), detalhe com sinais residencial/elétrico vigente (high + coverage_confirmed), cancelada (low + human_required), vencida (expired), `normalizeEvidencePack` + sanitização (sem nome/numero crus), ordenação das 3 apólices.
- `python -m py_compile backend/app/api/infocap_connector.py` → OK.
- `npx tsc --noEmit` → **TSC_EXIT=0**.
- `node --check` nos scripts/fixtures → OK.
- `npm run build` → verde (registro de `/api/attendance/cases/[caseId]/runtime/policy-select`). **mock/manual preservados** (cenário golden inalterado).

## 13. Testes reais documentados (req.10) — console logado, backend deployado + conexão ready
```js
const caseId = '<id>';
// A) lookup com CPF real → multiple_matches (ou found/client_found)
const A = await (await fetch(`/api/attendance/cases/${caseId}/runtime/policy-lookup`, {
  method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ source:'infocap', mode:'connector' })
})).json();
console.log(A.policy_lookup_result.status, A.policy_lookup_result.matches?.map(m => m.policy_ref)); // sem CPF

// B) selecionar uma apólice → policy_evidence_ready
const ref = A.policy_lookup_result.matches[0].policy_ref;
const B = await (await fetch(`/api/attendance/cases/${caseId}/runtime/policy-select`, {
  method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ source:'infocap', policy_ref: ref })
})).json();
console.log(B.policy_select_result.status, B.policy_select_result.confidence, B.policy_select_result.coverage_confirmed);

// C) step após seleção → não pede CPF de novo e continua coleta
const C = await (await fetch(`/api/attendance/cases/${caseId}/runtime/step`, {
  method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ source:'dashboard' })
})).json();
console.log(C.case.status, C.step?.selected_slot, C.case.next_step);
```
**Esperado:** A=`multiple_matches` com refs; B=`policy_evidence_ready`, `confidence` high/medium, `coverage_confirmed` conforme coberturas; C=`collecting_slots`, próximo slot operacional, sem voltar a pedir CPF.

## 14. Segurança / logs (req.12)
Logs apenas: `company_id`, `connection_id`, `endpoint`, `status`, `result_count`, `selected_policy_ref`, `duration_ms`. Sem CPF/nome/email/telefone/token/senha/ciphertext/payload bruto. Tudo mascarado (nº só 2 últimos dígitos; nome em iniciais). Testes asseguram que nome/numero crus não vazam no JSON. Segredo nunca trafega pelo Web (backend decifra). Cobertura **nunca** afirmada sem itens/coberturas no documento.

## 15. Próximo: 42B6 Dispatch ou 42I3B?
**Recomendo 42I3B antes do 42B6**, pequeno e focado: conectar o `policy_interpretation_context` ao Attendance Agent do Smith (resposta humana que diferencia apólice localizada de cobertura confirmada) — hoje o contexto está pronto e persistido, mas a geração da resposta interpretativa ainda não está ligada ao runtime de reply. Com isso feito, seguimos para **42B6 — Dispatch Packet dry-run/HITL** com a evidência de cobertura já confiável. (O teste real com CPF da corretora pode rodar em paralelo, pois a infra de lookup/seleção/detalhe já está completa.)

## 16. Checks
| Check | Resultado |
|---|---|
| `node scripts/infocap-evidence-pack.test.mjs` | ✅ 37/37 |
| `python -m py_compile` (infocap_connector) | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `node --check` (test + fixtures) | ✅ OK |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| SQL/migration · cobertura sem evidência · RAG/LLM decidindo cobertura · WhatsApp/dispatch · acionar seguradora · CPF/segredo exposto/logado · credenciais commitadas · motor antigo copiado | ✅ nenhum |
