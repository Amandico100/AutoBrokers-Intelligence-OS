#!/usr/bin/env node
/**
 * 42W1 — Seleção conversacional de apólice (offline, sem rede, sem LLM).
 *
 *   node scripts/whatsapp-policy-selection.test.mjs
 *
 * Garante: ordinal/número/policy_ref/final/data resolvem; ambíguo não seleciona;
 * só aceita ref presente nos matches; mensagens humanas sem número cru.
 */
import {
  resolvePolicySelectionFromCustomerReply,
  buildPolicyOptionsMessage,
  buildPolicySelectedMessage,
  isPolicySelectionAlreadyResolved,
} from '../lib/attendance/whatsapp-policy-selection.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const MATCHES = [
  { policy_ref: '97652', insurer_key: 'ALLI', product: 'Residencial', masked_policy_number: '****99', valid_to: '31/10/2026', active_now: true, cancelled: false },
  { policy_ref: '97572', insurer_key: 'ALLI', product: 'Residencial', masked_policy_number: '****53', valid_to: '22/10/2025', active_now: false, cancelled: false },
  { policy_ref: '93643', insurer_key: 'ALLI', product: 'Auto', masked_policy_number: '****48', valid_to: '01/03/2024', active_now: false, cancelled: true },
];

console.log('== 42W1 — Seleção conversacional de apólice ==');

// [1] Ordinal / número.
console.log('\n[1] ordinal/número');
{
  assert('"a primeira" → 97652', resolvePolicySelectionFromCustomerReply('a primeira', MATCHES).policy_ref === '97652');
  assert('"2" → 97572', resolvePolicySelectionFromCustomerReply('2', MATCHES).policy_ref === '97572');
  assert('"opção 3" → 93643', resolvePolicySelectionFromCustomerReply('pode ser a opção 3', MATCHES).policy_ref === '93643');
  assert('"segunda" → 97572', resolvePolicySelectionFromCustomerReply('quero a segunda', MATCHES).policy_ref === '97572');
  const oor = resolvePolicySelectionFromCustomerReply('a quinta', MATCHES);
  assert('"a quinta" (fora do range) → não resolve', oor.resolved === false && oor.ambiguous === true, oor.reason);
}

// [2] policy_ref explícito.
console.log('\n[2] policy_ref explícito');
{
  const r = resolvePolicySelectionFromCustomerReply('é a 97652', MATCHES);
  assert('"97652" → resolve explicit_ref', r.resolved && r.policy_ref === '97652' && r.strategy === 'explicit_ref', r.strategy);
  const bad = resolvePolicySelectionFromCustomerReply('é a 11111', MATCHES);
  assert('ref inexistente → não resolve', bad.resolved === false, bad.reason);
}

// [3] Final mascarado.
console.log('\n[3] final mascarado');
{
  assert('"final 99" → 97652', resolvePolicySelectionFromCustomerReply('a de final 99', MATCHES).policy_ref === '97652');
  assert('"termina em 53" → 97572', resolvePolicySelectionFromCustomerReply('a que termina em 53', MATCHES).policy_ref === '97572');
}

// [4] Data/ano.
console.log('\n[4] data/ano');
{
  assert('"vence em 31/10/2026" → 97652', resolvePolicySelectionFromCustomerReply('a que vence em 31/10/2026', MATCHES).policy_ref === '97652');
  // 2026 só aparece em uma apólice → resolve
  assert('"a de 2026" → 97652', resolvePolicySelectionFromCustomerReply('a de 2026', MATCHES).policy_ref === '97652');
}

// [5] Afirmativo single.
console.log('\n[5] afirmativo com 1 opção');
{
  const one = [MATCHES[0]];
  assert('"pode ser essa" + 1 opção → resolve', resolvePolicySelectionFromCustomerReply('pode ser essa', one).policy_ref === '97652');
  const amb = resolvePolicySelectionFromCustomerReply('pode ser', MATCHES);
  assert('"pode ser" + várias → não resolve', amb.resolved === false, amb.reason);
}

// [6] Ambíguo / vazio.
console.log('\n[6] ambíguo/vazio');
{
  assert('texto vago → não resolve', resolvePolicySelectionFromCustomerReply('não sei', MATCHES).resolved === false);
  assert('vazio → não resolve', resolvePolicySelectionFromCustomerReply('', MATCHES).resolved === false);
  assert('sem matches → não resolve', resolvePolicySelectionFromCustomerReply('a primeira', []).resolved === false);
}

// [7] Mensagens humanas (sem número cru).
console.log('\n[7] mensagens humanas');
{
  const list = buildPolicyOptionsMessage(MATCHES);
  assert('lista numerada', /1\)/.test(list) && /2\)/.test(list) && /3\)/.test(list));
  assert('lista usa final mascarado', /final \*\*\*\*99/.test(list), list);
  assert('lista marca vencida/cancelada', /vencida/.test(list) && /cancelada/.test(list));
  assert('lista não vaza policy_ref cru', !/97652/.test(list), 'ref cru na lista');
  const sel = buildPolicySelectedMessage(MATCHES[0]);
  assert('selecionado menciona final mascarado', /final \*\*\*\*99/.test(sel), sel);
  assert('selecionado menciona vigente', /vigente/i.test(sel), sel);
  assert('selecionado não vaza ref', !/97652/.test(sel), 'ref cru');
}

// [8] 42W1.2 P0: gate de seleção já resolvida.
console.log('\n[8] isPolicySelectionAlreadyResolved');
{
  assert('case novo → false', isPolicySelectionAlreadyResolved({ verification_status: 'unverified' }) === false);
  assert('policy_source connector → true', isPolicySelectionAlreadyResolved({ policy_source: 'connector' }) === true);
  assert('verified_by_connector → true', isPolicySelectionAlreadyResolved({ verification_status: 'verified_by_connector' }) === true);
  assert('verified_by_human → true', isPolicySelectionAlreadyResolved({ verification_status: 'verified_by_human' }) === true);
  assert('policy_snapshot.policy_ref → true', isPolicySelectionAlreadyResolved({ policy_snapshot: { policy_ref: '97652' } }) === true);
  assert('coverage_evidence connector → true', isPolicySelectionAlreadyResolved({ coverage_evidence: { source: 'connector' } }) === true);
  assert('metadata.policy_selection_status → true', isPolicySelectionAlreadyResolved({ metadata: { policy_selection_status: 'resolved' } }) === true);
  assert('metadata.policy_select.selected_policy_ref → true', isPolicySelectionAlreadyResolved({ metadata: { policy_select: { selected_policy_ref: '97652' } } }) === true);
  assert('null → false', isPolicySelectionAlreadyResolved(null) === false);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
