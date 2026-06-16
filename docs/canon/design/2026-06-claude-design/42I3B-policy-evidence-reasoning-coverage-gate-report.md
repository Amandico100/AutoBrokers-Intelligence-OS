# 42I3B — Policy Evidence Reasoning, Coverage Gate & E2E Hardening Report

> **Status:** concluído · testes offline **70 verdes** (37 evidence-pack + 33 coverage-readiness) · `typecheck` EXIT=0 · `node --check` OK · build verde · `git diff --check` limpo · **TS/Next runtime + helpers puros + UI + testes + docs** (sem SQL/migration, sem motor LLM paralelo, sem RAG decidindo cobertura, sem WhatsApp/dispatch real, sem acionar seguradora, sem inventar cobertura, sem PII/segredo exposto) · sem deploy automático.
> **Data:** 2026-06-16 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Contexto do teste real (42I3A em produção)
CPF real → `multiple_matches` (3 apólices) → `policy-select 97652` → HTTP 200 → `verified_by_connector` / `policy_source=connector` / `coverage_evidence` + `policy_snapshot` + `policy_interpretation_context` presentes. Coverage real: ALLI/RESI vigente, `confidence=low`, `human_required=true`, `residential=true`, `coverage_sections_count=0`, `coverage_confirmed=false`. Este batch fecha os 4 problemas observados.

## 2. Arquivos alterados/criados
- `lib/attendance/policy-evidence-pack.ts` (**alterado**) — Coverage Readiness Gate: `evaluateCoverageReadiness`, `coverageReadinessFromPack`, `buildCoverageReasoningMessage`, `humanizeInsurer`/`humanizeProduct`.
- `lib/attendance/policy-lookup.ts` (**alterado**) — `sanitizePolicySnapshot` agora escolhe a **nota por origem** (connector/infocap ≠ mock/manual).
- `app/api/attendance/cases/[caseId]/runtime/policy-select/route.ts` (**alterado**) — calcula e persiste `coverage_readiness` (+ `message`), surfaça no response e nos diagnostics; snapshot já sai com nota connector.
- `app/api/attendance/cases/[caseId]/runtime/step/route.ts` (**alterado**) — resume usa a **resposta inteligente determinística** (mensagem do `coverage_readiness`) em vez do prefixo genérico; persiste readiness/`dispatch_allowed` nos diagnostics.
- `app/dashboard/atendimentos/casos/[caseId]/AttendanceConversationSimulator.tsx` (**alterado**) — painel de evidência da apólice + chip de coverage readiness + mensagem.
- `scripts/infocap-coverage-readiness.test.mjs` (**novo**) + `package.json` (**alterado**, `test:infocap-readiness`).
- `docs/canon/design/2026-06-claude-design/42I3B-...md` (este).

## 3. Snapshot real corrigido (req.1)
`sanitizePolicySnapshot` passou a ser **source-aware**: para `source='connector'`/`'infocap'` a nota é *"Snapshot sanitizado de apólice localizada via InfoCap/connector. Não contém payload bruto."*; mock/manual mantêm a nota antiga. Isso corrige tanto o `policy-select` quanto o caminho `found` do `policy-lookup` (ambos usam o mesmo helper). `source`, `masked_policy_number`, `insurer_key`, `product`, `policy_status`, vigência continuam preservados; o `policy_select` ainda adiciona `assistance_signals`, `coverage_sections`, `confidence` e `policy_ref`. Nunca grava payload bruto. Coberto por teste ([6]).

## 4. policy_interpretation_context conectado ao runtime (req.2, 3)
No `runtime/step`, quando `isPolicyEvidenceReady(case)` (logo após `policy-select`), o runtime lê `metadata.coverage_readiness.message` (mensagem determinística derivada do `policy_interpretation_context`/pack) e a usa como **resposta do agente**, concatenada à próxima pergunta de slot. Nada de payload bruto/CPF/nome/token é enviado a LLM — a mensagem é **determinística e humanizada** (decisão de cobertura nunca vem de LLM/RAG). O contexto persistido inclui insurer/product/vigência/status, `coverage_confirmed`, `confidence`, `human_required`, `assistance_signals`, `gaps`/`limitations` e a pergunta do segurado.

### Exemplos de resposta do agente (determinística)
- **coverage_confirmed=false** (caso real): *"Localizei uma apólice Allianz Residencial vigente na InfoCap. O documento confirma a existência da apólice, mas não trouxe os itens de cobertura detalhados para eu afirmar automaticamente a assistência elétrica. Vou continuar coletando os dados do atendimento, mas antes de acionar será necessária validação humana da cobertura."*
- **coverage_confirmed=true**: *"Localizei uma apólice Allianz Residencial vigente e encontrei evidência de assistência elétrica/residencial nos detalhes. Vou seguir com os dados do atendimento para preparar o acionamento."*
- **blocked (cancelada/vencida)**: *"Localizei uma apólice Allianz Residencial, mas ela não está apta para acionamento automático (cancelada ou fora de vigência). Vou registrar e encaminhar para validação humana antes de qualquer providência."*

> Por que determinístico e não LLM aqui: o `runtime-llm-fallback` é gated e conservador (só off-topic/clarificação, nunca cobertura). Decidir/descrever cobertura por LLM violaria os guardrails (ADR-003/SPEC-005). A mensagem é montada por helper puro a partir da evidência. Se no futuro quisermos uma redação por LLM, o `policy_interpretation_context` já está pronto e sanitizado para alimentar o Attendance Agent — fica como evolução opcional, sem bloquear o MVP.

## 5. Coverage Readiness Gate (req.4) — `evaluateCoverageReadiness`
Helper puro. Estados:
- **`coverage_confirmed`** — `coverage_confirmed=true`, `human_required=false`, confidence high/medium → `dispatch_allowed=true`.
- **`policy_located_only`** — localizada, com alguma cobertura, sem exigir humano.
- **`human_validation_required`** — `human_required`, confidence low, `coverages_count=0`, múltiplas ou não confirmada → `dispatch_allowed=false`.
- **`blocked`** — cancelada/vencida → `dispatch_allowed=false`, `human_required=true`.

**Regras aplicadas:** se `coverage_confirmed=false` ou `human_required=true` → continua coleta de slots operacionais, **mas `dispatch_allowed=false`** (o futuro dispatch_packet sairá draft/hitl). Cancelada/vencida → `blocked`, não segue para acionamento. Persistido em `metadata.coverage_readiness` (estado, flags, reasons, message) e em `diagnostics.dispatch_allowed`/`diagnostics.coverage_readiness` — pronto para o 42B6 ler o gate. `external_action_allowed` permanece `false` em todo o MVP.

## 6. Runtime após seleção (req.5)
`verified_by_connector` + `policy_evidence_ready` → o `step` **não** repete CPF/apólice (gate de identidade/apólice satisfeito), emite a mensagem inteligente, satisfaz `policy_evidence_status`, transita para `corridor_collecting_slots` e segue a coleta operacional. `metadata.coverage_readiness` é preservado (merge) ao longo do fluxo.

## 7. Attendance Agent / LLM (req.6)
Mantido o `runtime-llm-fallback` apenas para off-topic/clarificação. Para a **resposta de cobertura**, implementada **resposta determinística humanizada** (sem motor paralelo, sem RAG decidindo cobertura). Reportado aqui explicitamente: não foi seguro/necessário usar LLM neste ponto; o contexto sanitizado está pronto caso se queira ligar a redação por LLM depois.

## 8. UI / Simulador (req.7)
Painel "Evidência da apólice (InfoCap)" com chip de **coverage readiness** (Cobertura confirmada / Apólice localizada / Validação humana necessária / Bloqueado), resumo do evidence pack (seguradora, produto, nº mascarado, status, vigência, coberturas, confiança, validação humana, dispatch liberado) e a **mensagem inteligente**. Após selecionar, a resposta do step aparece no chat (não pergunta seca).

## 9. Testes que rodei (req.8) — **eu mesmo executei**
- `node scripts/infocap-coverage-readiness.test.mjs` → **33/33**: localizada sem cobertura→human_validation_required; sinais elétricos→coverage_confirmed (dispatch liberado); vencida→blocked; cancelada→blocked; multiple_matches→human_required; snapshot connector sem nota mock/manual (+infocap+mock); humanizadores; reasoning sem PII.
- `node scripts/infocap-evidence-pack.test.mjs` → **37/37** (regressão 42I3A).
- `npx tsc --noEmit` → **EXIT=0**. `node --check` → OK. `npm run build` → verde.
- Mock/manual preservados (snapshot mock mantém a nota antiga; goldens não regridem).

## 10. Teste real documentado (req.9) — console logado
```js
async function api(path, body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});return {status:r.status,json:await r.json().catch(()=>({}))};}
// 1) cria caso
const c=(await api('/api/attendance/cases',{customer_name:'Teste',channel:'dashboard',selected_subcorridor_key:'electrician',create_conversation:true})).json.case.id;
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'Estou sem luz na cozinha',source:'dashboard'});
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'Não, sem cheiro de queimado nem faísca.',source:'dashboard'});
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'<CPF REAL>',source:'dashboard'});
// 2) lookup → multiple_matches
const L=await api(`/api/attendance/cases/${c}/runtime/policy-lookup`,{source:'infocap',mode:'connector'});
console.log('lookup', L.json.policy_lookup_result.status, L.json.policy_lookup_result.matches?.map(m=>m.policy_ref));
// 3) select 97652 → policy_evidence_ready + coverage_readiness
const S=await api(`/api/attendance/cases/${c}/runtime/policy-select`,{source:'infocap',policy_ref:'97652'});
console.log('select', S.json.policy_select_result.status, S.json.policy_select_result.coverage_readiness?.state, S.json.policy_select_result.assistant_message);
// 4) step → resposta inteligente, sem repetir CPF
const T=await api(`/api/attendance/cases/${c}/runtime/step`,{source:'dashboard'});
console.log('verification', T.json.case.verification_status);
console.log('policy_source', T.json.case.policy_source);
console.log('macro', T.json.case.metadata?.attendance_macro_state);
console.log('coverage_readiness', T.json.case.metadata?.coverage_readiness?.state, 'dispatch_allowed', T.json.case.metadata?.coverage_readiness?.dispatch_allowed);
console.log('assistant/next_step', T.json.step?.question || T.json.case.next_step);
```
**Esperado (caso real ALLI/RESI sem itens):** select→`policy_evidence_ready`, `coverage_readiness.state='human_validation_required'`, `dispatch_allowed=false`; step→`verified_by_connector`/`connector`/`corridor_collecting_slots`, mensagem explicando apólice localizada vs cobertura não confirmada + próximo slot (endereço), **sem pedir CPF de novo**.

## 11. Critério de pronto (req.10)
| Critério | Status |
|---|---|
| policy-select real passa | ✅ (42I3A em prod) |
| evidence pack persiste | ✅ |
| policy_interpretation_context é usado | ✅ (step → mensagem determinística) |
| coverage_readiness persistido | ✅ (`metadata.coverage_readiness` + diagnostics) |
| agente não repete CPF | ✅ (gate satisfeito; resume) |
| explica localizada vs confirmada | ✅ (mensagens + testes) |
| dispatch automático bloqueado se human_required | ✅ (`dispatch_allowed=false`, `external_action_allowed=false`) |
| build/testes verdes | ✅ |

## 12. Decisão: seguir para 42B6?
**Sim — pode seguir para 42B6 (Dispatch Packet dry-run/HITL).** O gate já entrega o sinal que o 42B6 precisa: `metadata.coverage_readiness.dispatch_allowed` + `diagnostics.dispatch_allowed`. Regra para o 42B6: montar o packet sempre em **draft/hitl_required**, e **só** habilitar preparação de acionamento quando `coverage_readiness.state='coverage_confirmed'` (`dispatch_allowed=true`); caso contrário exigir validação humana. Nenhuma ação externa real no MVP.

## 13. Checks
| Check | Resultado |
|---|---|
| `node scripts/infocap-coverage-readiness.test.mjs` | ✅ 33/33 |
| `node scripts/infocap-evidence-pack.test.mjs` | ✅ 37/37 |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `node --check` | ✅ OK |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| SQL/migration · LLM paralelo · RAG cobertura · WhatsApp/dispatch real · acionar seguradora · inventar cobertura · PII/segredo exposto | ✅ nenhum |
