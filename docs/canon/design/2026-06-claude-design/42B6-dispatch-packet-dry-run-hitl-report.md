# 42B6 — Dispatch Packet Dry-run, HITL Approval & Coverage-Gated Action Readiness Report

> **Status:** concluído · testes offline **105 verdes** (37 evidence-pack + 33 coverage-readiness + 35 dispatch-readiness) · `typecheck` EXIT=0 · build verde · `git diff --check` limpo · **SEM alteração de schema/SQL** (reusa `dispatch_packets`/`attendance_cases`/`corridor_runs`) · sem WhatsApp/seguradora/prestador/API externa · sem LLM decidindo autorização · sem PII/segredo em resposta pública.
> **Data:** 2026-06-16 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Decisão sobre schema
**Nenhuma migration foi necessária.** A tabela `dispatch_packets` (42B3) já tem `status` (enum), `payload`, `missing_data`, `idempotency_key`, `metadata`. Mapeei os estados humano-legíveis do packet para os status permitidos pelo CHECK existente (ver §4). `coverage_readiness`/`dispatch_readiness`/decisão HITL ficam em `attendance_cases.metadata` + `coverage_evidence` (sem tabela nova).

## 2. Arquivos alterados/criados
- `lib/attendance/dispatch-readiness.ts` (**novo**) — `evaluateDispatchReadiness`, `buildDispatchPacket`, `dbStatusForPacketState`, `maskAddressSummary` (puro/autocontido).
- `app/api/attendance/cases/[caseId]/runtime/dispatch-dry-run/route.ts` (**novo**) — prepara/persiste packet dry-run.
- `app/api/attendance/cases/[caseId]/runtime/coverage-validation/route.ts` (**novo**) — decisão HITL de cobertura.
- `lib/attendance/handoff-dossier.ts` (**alterado**) — dossiê inclui policy_snapshot, coverage_readiness, dispatch_readiness, packet draft, motivo HITL, próximos passos humanos (+markdown).
- `app/api/attendance/cases/[caseId]/handoff-dossier/route.ts` (**alterado**) — busca metadata/policy_snapshot + payload do packet dry-run.
- `app/dashboard/atendimentos/casos/[caseId]/CaseDetailClient.tsx` (**alterado**) — botão dispatch dry-run, painel de readiness (blockers/warnings/estado), botões HITL (aprovar/reprovar/mais info).
- `scripts/dispatch-readiness.test.mjs` (**novo**) + `package.json` (**alterado**, `test:dispatch-readiness`).
- `docs/canon/design/2026-06-claude-design/42B6-...md` (este).

## 3. Rotas criadas
- **`POST /api/attendance/cases/[caseId]/runtime/dispatch-dry-run`** → avalia readiness, monta packet, upsert em `dispatch_packets` (idempotente por caso), grava `metadata.dispatch_readiness`, atualiza `next_step`. Resposta: `{ ok, case, dispatch_packet, dispatch_readiness, next_step, external_action:{allowed:false, sent:false, reason} }`.
- **`POST /api/attendance/cases/[caseId]/runtime/coverage-validation`** → body `{ decision: approved|rejected|needs_more_info, reason?, source? }`. Atualiza `coverage_readiness` + `coverage_evidence` (sem tabela nova).

## 4. Como o readiness funciona (`evaluateDispatchReadiness`)
Avalia `identity_ready`, `policy_selected`, `policy_verified`, `coverage_confirmed`, `human_validation_required`, `risk_ok`, `required_slots_ready`, `address_ready`, `contact_ready`, `dispatch_allowed`, `hitl_required`, `blockers[]`, `warnings[]`, `missing_slots[]`. Slots operacionais exigidos: `affected_area`, `electrical_issue_type`, `property_address_confirmed` (exclui `policy_evidence_status`/`risk_indicators`).

**Precedência de estado** (`packet_state`):
1. **blocked** — risco alto/handoff, apólice cancelada/vencida (`coverage_readiness.state='blocked'`), cobertura reprovada por humano, identidade/apólice ausente/não verificada.
2. **incomplete** — faltam slots operacionais (`hitl_required=false`, só coletar).
3. **hitl_required** — cobertura não confirmada / `human_required` (`dispatch_allowed=false`).
4. **ready_for_human_approval** — tudo pronto + `coverage_confirmed` (`dispatch_allowed=true`, mas ainda HITL no MVP).

**Mapa estado→status do banco:** incomplete→`missing_data`, blocked/hitl_required→`awaiting_approval`, ready_for_human_approval→`ready_for_approval`. `external_action_allowed`/`sent` = **sempre false**.

## 5. Como o dispatch_packet é montado (`buildDispatchPacket`)
Packet sanitizado: case_id/case_number/company_id, corridor/subcorridor, `service_type:'electrician'`, insurer/product, `selected_policy_ref`, `masked_policy_number`, `policy_status`, `coverage_summary`, `coverage_readiness`, `collected_slots`/`missing_slots`, `risk_summary`, `customer_contact_ref` (telefone **mascarado**), `address_summary` (cidade/UF/bairro — **nunca rua+número**), `human_validation_required`, `recommended_action`, `status` (estado humano-legível), `external_action_allowed=false`, `external_action_sent=false`, `audit_notes`. **Nunca** CPF/nome completo/telefone cru/endereço completo/payload bruto (validado por teste).

## 6. Como o HITL funciona
`coverage-validation`:
- **approved** → `coverage_readiness.state='human_approved'` (`dispatch_allowed=true`, `human_required=false`), `coverage_evidence.verified_by='human'` + `human_validation`, `verification_status='verified_by_human'`. Dispatch continua dry-run/HITL (sem externo). Próximo `dispatch-dry-run` recalcula → `ready_for_human_approval`.
- **rejected** → `state='human_rejected'`, bloqueia (`dispatch_allowed=false`); next_step orienta tratativa humana. Próximo dispatch → `blocked`.
- **needs_more_info** → `state='needs_more_info'`, bloqueado, pede informação.
Sem LLM, sem tabela nova, sem ação externa.

## 7. Estados esperados (req.4)
| coverage_readiness | packet_state | next_step |
|---|---|---|
| human_validation_required | `hitl_required` | "Pacote… em modo rascunho. Antes de acionar, é necessária validação humana da cobertura." |
| coverage_confirmed / human_approved | `ready_for_human_approval` | "Pacote… preparado. Aguardando aprovação humana para envio/acionamento." |
| slots faltando | `incomplete` | "…faltam dados do atendimento. Continue a coleta antes de acionar." |
| cancelada/vencida/rejeitada/risco | `blocked` | "…bloqueado… Validação humana necessária antes de qualquer providência." |

## 8. Dossiê (req.7)
`buildHandoffDossier`/markdown agora incluem `policy.snapshot` (mascarado), `coverage_readiness` (estado/mensagem), seção **Acionamento (dispatch dry-run)** com estado do pacote, dispatch liberado, blockers/warnings, motivo HITL, próximos passos humanos e a nota "Nenhuma ação externa foi executada". A rota do dossiê injeta o payload do packet dry-run mais recente.

## 9. Runtime (req.8)
O dispatch dry-run **não** encerra o atendimento, **não** aciona externo, **não** reabre caso. Se faltam slots → `incomplete` (segue coleta). Se `hitl_required` → `next_step` humano explicando que precisa validação humana antes do acionamento. `diagnostics.dispatch_allowed`/`external_action_allowed=false` ficam no run como gate.

## 10. Testes que rodei (req.9) — **eu mesmo executei**
- `node scripts/dispatch-readiness.test.mjs` → **35/35**: hitl_required, ready_for_human_approval, incomplete, blocked (cancelada/vencida), risco alto, human_approved, human_rejected, packet sem PII (CPF/telefone/endereço crus), `external_action.sent=false` sempre, mapeamento de status do banco.
- `node scripts/infocap-coverage-readiness.test.mjs` → **33/33** · `node scripts/infocap-evidence-pack.test.mjs` → **37/37** (regressão).
- `npx tsc --noEmit` → **EXIT=0** · `npm run build` → verde · `git diff --check` limpo.

## 11. Teste real documentado (req.10) — console logado (CPF 04760897941 / policy_ref 97652)
```js
async function api(p,b){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return {status:r.status,json:await r.json().catch(()=>({}))};}
const c=(await api('/api/attendance/cases',{customer_name:'Teste',channel:'dashboard',selected_subcorridor_key:'electrician',create_conversation:true})).json.case.id;
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'Estou sem luz na cozinha'});
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'Não, sem cheiro de queimado nem faísca.'});
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'04760897941'});
await api(`/api/attendance/cases/${c}/runtime/policy-lookup`,{source:'infocap',mode:'connector'});
await api(`/api/attendance/cases/${c}/runtime/policy-select`,{source:'infocap',policy_ref:'97652'});
await api(`/api/attendance/cases/${c}/runtime/step`,{}); // resposta inteligente
// coletar slots mínimos
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'É na cozinha'});
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'Fico totalmente sem energia'});
await api(`/api/attendance/cases/${c}/runtime/reply`,{message:'Sim, é o mesmo endereço da apólice'});
// dispatch dry-run (esperado: hitl_required, pois ALLI/RESI sem itens)
let D=await api(`/api/attendance/cases/${c}/runtime/dispatch-dry-run`,{});
console.log('coverage_readiness', D.json.case.metadata?.coverage_readiness?.state);
console.log('dispatch_readiness', D.json.dispatch_readiness?.packet_state, 'allowed', D.json.dispatch_readiness?.dispatch_allowed);
console.log('packet.status', D.json.dispatch_packet?.status, 'external', D.json.external_action);
console.log('next_step', D.json.next_step);
// aprovar cobertura manualmente (HITL) e repreparar
await api(`/api/attendance/cases/${c}/runtime/coverage-validation`,{decision:'approved',source:'human'});
D=await api(`/api/attendance/cases/${c}/runtime/dispatch-dry-run`,{});
console.log('após aprovação →', D.json.dispatch_readiness?.packet_state, 'allowed', D.json.dispatch_readiness?.dispatch_allowed, 'external_sent', D.json.dispatch_packet?.external_action_sent);
```
**Esperado:** 1ª preparação → `hitl_required`, `dispatch_allowed=false`, `external_action.sent=false`; após `approved` → `ready_for_human_approval`, `dispatch_allowed=true`, `external_action_sent=false` (ainda dry-run).

## 12. Critério de pronto (req.11)
| Critério | Status |
|---|---|
| dispatch packet dry-run gerado | ✅ |
| nenhum externo enviado | ✅ (`external_action_sent=false` sempre) |
| coverage gate bloqueia corretamente | ✅ (blocked/hitl_required) |
| HITL approval/rejection funciona | ✅ (coverage-validation) |
| dossiê inclui dispatch | ✅ |
| UI mostra readiness | ✅ |
| testes verdes | ✅ 105/105 |
| fluxo real retorna hitl_required quando coverage_confirmed=false | ✅ (caso ALLI/RESI sem itens) |

## 13. Decisão: seguir para 42W0?
**Sim — pode seguir para 42W0 (WhatsApp buffer/debounce).** O bloco de atendimento está completo no MVP: entrada → identidade → apólice (InfoCap real) → evidência/cobertura → coverage gate → dispatch dry-run/HITL, tudo **sem ação externa**. O 42W0 trata apenas de buffer/debounce de mensagens recebidas (entrada), não de envio externo — compatível com o gate atual (`external_action_allowed=false`). Recomendo que o envio real (seguradora/prestador) só seja destravado depois de homologação explícita, lendo `dispatch_readiness.dispatch_allowed` + aprovação humana.

## 14. Checks
| Check | Resultado |
|---|---|
| `node scripts/dispatch-readiness.test.mjs` | ✅ 35/35 |
| `node scripts/infocap-coverage-readiness.test.mjs` | ✅ 33/33 |
| `node scripts/infocap-evidence-pack.test.mjs` | ✅ 37/37 |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| SQL/migration · WhatsApp · seguradora/prestador · API externa · LLM autorização · PII/segredo público · credenciais | ✅ nenhum |
