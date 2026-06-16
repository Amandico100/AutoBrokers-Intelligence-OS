#!/usr/bin/env node
/**
 * 42B6 — Dispatch Readiness + Packet Builder unit tests (offline, sem rede).
 *
 *   node scripts/dispatch-readiness.test.mjs
 *
 * Valida o coverage gate de acionamento, estados do packet, mapeamento de
 * status do banco, bloqueio HITL e ausência de PII no packet. Sem envio externo.
 */
import {
  evaluateDispatchReadiness,
  buildDispatchPacket,
  dbStatusForPacketState,
} from '../lib/attendance/dispatch-readiness.ts';

let pass = 0;
let fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) {
    pass += 1;
    console.log(`  ✓ ${name}`);
  } else {
    fail += 1;
    failures.push({ name, detail });
    console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

const AT = '2026-06-16T00:00:00.000Z';
const EVIDENCE = { insurer_detected: 'Allianz', product_detected: 'Residencial', policy_ref: '97652', masked_policy_number: '****52', policy_status: 'Vigente' };

function baseCase(over = {}) {
  return {
    id: 'case-1',
    case_number: 'CASE-0001',
    company_id: 'co-1',
    customer_phone: '+5511999998888',
    insured_document_ref: '04760897941',
    insured_address: { city: 'São Paulo', state: 'SP', street: 'Rua Secreta 123' },
    verification_status: 'verified_by_connector',
    status: 'collecting_slots',
    risk_level: 'low',
    selected_subcorridor_key: 'electrician',
    coverage_evidence: { coverage_summary: 'Apólice localizada; cobertura não confirmada.' },
    metadata: { policy_select: { selected_policy_ref: '97652' }, policy_evidence_pack: EVIDENCE },
    ...over,
  };
}
const fullSlots = { filled: { affected_area: 'cozinha', electrical_issue_type: 'sem energia', property_address_confirmed: { status: 'confirmed' } }, missing: [], conflicts: [] };
function run(slots = fullSlots) {
  return { id: 'run-1', slots };
}

console.log('== 42B6 — Dispatch Readiness Gate (offline) ==');

// [1] cobertura não confirmada → hitl_required, dispatch bloqueado.
console.log('\n[1] coverage não confirmada → hitl_required');
{
  const cr = { state: 'human_validation_required', coverage_confirmed: false, human_required: true, dispatch_allowed: false };
  const r = evaluateDispatchReadiness({ caseRow: baseCase(), run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('packet_state = hitl_required', r.packet_state === 'hitl_required', r.packet_state);
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
  assert('hitl_required = true', r.hitl_required === true);
  assert('warning coverage_not_confirmed', r.warnings.includes('coverage_not_confirmed') || r.warnings.includes('human_validation_required'), r.warnings.join(','));
  assert('db status = awaiting_approval', dbStatusForPacketState(r.packet_state) === 'awaiting_approval');
}

// [2] coverage_confirmed + tudo pronto → ready_for_human_approval, dispatch liberado.
console.log('\n[2] coverage_confirmed → ready_for_human_approval');
{
  const cr = { state: 'coverage_confirmed', coverage_confirmed: true, human_required: false, dispatch_allowed: true };
  const r = evaluateDispatchReadiness({ caseRow: baseCase(), run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('packet_state = ready_for_human_approval', r.packet_state === 'ready_for_human_approval', r.packet_state);
  assert('dispatch_allowed = true', r.dispatch_allowed === true);
  assert('hitl_required = true (precisa aprovação)', r.hitl_required === true);
  assert('db status = ready_for_approval', dbStatusForPacketState(r.packet_state) === 'ready_for_approval');
}

// [3] slots faltando → incomplete.
console.log('\n[3] slots faltando → incomplete');
{
  const cr = { state: 'coverage_confirmed', coverage_confirmed: true, human_required: false, dispatch_allowed: true };
  const partial = { filled: { affected_area: 'cozinha' }, missing: [], conflicts: [] };
  const r = evaluateDispatchReadiness({ caseRow: baseCase(), run: run(partial), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('packet_state = incomplete', r.packet_state === 'incomplete', r.packet_state);
  assert('missing_slots inclui electrical_issue_type', r.missing_slots.includes('electrical_issue_type'), r.missing_slots.join(','));
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
  assert('hitl_required = false (só coletar)', r.hitl_required === false);
  assert('db status = missing_data', dbStatusForPacketState(r.packet_state) === 'missing_data');
}

// [4] apólice cancelada/vencida (coverage blocked) → blocked.
console.log('\n[4] cancelada/vencida → blocked');
{
  const cr = { state: 'blocked', coverage_confirmed: false, human_required: true, dispatch_allowed: false };
  const r = evaluateDispatchReadiness({ caseRow: baseCase(), run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('packet_state = blocked', r.packet_state === 'blocked', r.packet_state);
  assert('blocker policy_cancelled_or_expired', r.blockers.includes('policy_cancelled_or_expired'), r.blockers.join(','));
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
}

// [5] risco alto → blocked.
console.log('\n[5] risco alto → blocked');
{
  const cr = { state: 'coverage_confirmed', coverage_confirmed: true, human_required: false, dispatch_allowed: true };
  const r = evaluateDispatchReadiness({ caseRow: baseCase({ risk_level: 'high' }), run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('packet_state = blocked', r.packet_state === 'blocked', r.packet_state);
  assert('blocker high_risk_or_handoff', r.blockers.includes('high_risk_or_handoff'), r.blockers.join(','));
}

// [6] humano aprovou cobertura → ready_for_human_approval.
console.log('\n[6] human_approved → ready_for_human_approval');
{
  const cr = { state: 'human_approved', dispatch_allowed: true, human_required: false };
  const r = evaluateDispatchReadiness({ caseRow: baseCase({ verification_status: 'verified_by_human' }), run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('coverage_confirmed = true', r.coverage_confirmed === true);
  assert('packet_state = ready_for_human_approval', r.packet_state === 'ready_for_human_approval', r.packet_state);
  assert('dispatch_allowed = true', r.dispatch_allowed === true);
}

// [7] humano reprovou → blocked.
console.log('\n[7] human_rejected → blocked');
{
  const cr = { state: 'human_rejected', dispatch_allowed: false, human_required: true };
  const r = evaluateDispatchReadiness({ caseRow: baseCase(), run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  assert('packet_state = blocked', r.packet_state === 'blocked', r.packet_state);
  assert('blocker coverage_rejected_by_human', r.blockers.includes('coverage_rejected_by_human'), r.blockers.join(','));
}

// [8] Packet sanitizado: sem PII crua, external_action sempre false.
console.log('\n[8] packet sanitizado + sem PII');
{
  const cr = { state: 'human_validation_required', coverage_confirmed: false, human_required: true, dispatch_allowed: false };
  const c = baseCase();
  const r = evaluateDispatchReadiness({ caseRow: c, run: run(), coverageReadiness: cr, evidencePack: EVIDENCE });
  const packet = buildDispatchPacket({ caseRow: c, run: run(), evidencePack: EVIDENCE, coverageReadiness: cr, readiness: r, generatedAt: AT });
  const raw = JSON.stringify(packet);
  assert('external_action_allowed = false', packet.external_action_allowed === false);
  assert('external_action_sent = false', packet.external_action_sent === false);
  assert('status = hitl_required', packet.status === 'hitl_required', String(packet.status));
  assert('não vaza CPF', !raw.includes('04760897941'), 'CPF presente');
  assert('não vaza telefone cru', !raw.includes('999998888'), 'telefone cru presente');
  assert('contato mascarado presente', typeof packet.customer_contact_ref === 'string' && /\*\*\*\*/.test(packet.customer_contact_ref), String(packet.customer_contact_ref));
  assert('não vaza rua/numero', !/Rua Secreta 123/.test(raw), 'endereço cru presente');
  assert('address_summary parcial (cidade/UF)', packet.address_summary === 'São Paulo / SP', String(packet.address_summary));
  assert('service_type electrician', packet.service_type === 'electrician');
  assert('selected_policy_ref presente', packet.selected_policy_ref === '97652');
  assert('masked_policy_number mascarado', packet.masked_policy_number === '****52');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) {
  for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`);
  process.exit(1);
}
process.exit(0);
