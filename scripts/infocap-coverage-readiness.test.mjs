#!/usr/bin/env node
/**
 * 42I3B — Coverage Readiness Gate + reasoning + snapshot note (offline).
 *
 *   node scripts/infocap-coverage-readiness.test.mjs
 *
 * Valida o gate de cobertura (apólice localizada vs cobertura confirmada),
 * a mensagem humana determinística, o bloqueio de dispatch e a nota do
 * snapshot connector (não pode dizer mock/manual). Sem rede, sem PII real.
 */
import {
  buildPolicyEvidencePackFromDocument,
  coverageReadinessFromPack,
  evaluateCoverageReadiness,
  buildCoverageReasoningMessage,
  humanizeInsurer,
  humanizeProduct,
} from '../lib/attendance/policy-evidence-pack.ts';
import { sanitizePolicySnapshot } from '../lib/attendance/policy-lookup.ts';
import {
  MULTIPLE_MATCHES_DOCS,
  DETAIL_NO_COVERAGE,
  DETAIL_WITH_SIGNALS,
  DETAIL_CANCELLED,
} from './fixtures/infocap-policy.fixtures.mjs';

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

const NOW = new Date(Date.UTC(2026, 5, 11));
console.log('== 42I3B — Coverage Readiness Gate (offline) ==');

// [1] Apólice localizada SEM cobertura → human_validation_required, dispatch bloqueado.
console.log('\n[1] localizada sem cobertura → human_validation_required');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_NO_COVERAGE, NOW);
  const r = coverageReadinessFromPack(pack);
  assert('state = human_validation_required', r.state === 'human_validation_required', `state=${r.state}`);
  assert('coverage_confirmed = false', r.coverage_confirmed === false);
  assert('human_required = true', r.human_required === true);
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
  assert('message diferencia localizada vs cobertura', /existência da apólice/i.test(r.message) && /validação humana/i.test(r.message), r.message);
  assert('message não afirma cobertura elétrica', /não trouxe os itens de cobertura/i.test(r.message), r.message);
}

// [2] Apólice com sinais elétricos/residenciais vigente → coverage_confirmed, dispatch liberado.
console.log('\n[2] sinais de assistência elétrica → coverage_confirmed');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_WITH_SIGNALS, NOW);
  const r = coverageReadinessFromPack(pack);
  assert('state = coverage_confirmed', r.state === 'coverage_confirmed', `state=${r.state}`);
  assert('coverage_confirmed = true', r.coverage_confirmed === true);
  assert('human_required = false', r.human_required === false);
  assert('dispatch_allowed = true', r.dispatch_allowed === true);
  assert('message menciona acionamento', /preparar o acionamento/i.test(r.message), r.message);
}

// [3] Apólice vencida → blocked + human_required.
console.log('\n[3] vencida → blocked');
{
  const pack = buildPolicyEvidencePackFromDocument(MULTIPLE_MATCHES_DOCS[1], NOW);
  const r = coverageReadinessFromPack(pack);
  assert('state = blocked', r.state === 'blocked', `state=${r.state}`);
  assert('human_required = true', r.human_required === true);
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
  assert('reasons inclui policy_expired', r.reasons.includes('policy_expired'), r.reasons.join(','));
}

// [4] Apólice cancelada → blocked + human_required.
console.log('\n[4] cancelada → blocked');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_CANCELLED, NOW);
  const r = coverageReadinessFromPack(pack);
  assert('state = blocked', r.state === 'blocked', `state=${r.state}`);
  assert('reasons inclui policy_cancelled', r.reasons.includes('policy_cancelled'), r.reasons.join(','));
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
  assert('message indica validação humana', /validação humana/i.test(r.message), r.message);
}

// [5] multiple_matches → human_required.
console.log('\n[5] multiple_matches → human_validation_required');
{
  const r = evaluateCoverageReadiness({
    coverage_confirmed: false,
    confidence: 'medium',
    multiple_matches: true,
    insurer: 'ALLI',
    product: 'RESI',
  });
  assert('state = human_validation_required', r.state === 'human_validation_required', `state=${r.state}`);
  assert('reasons inclui multiple_policies', r.reasons.includes('multiple_policies'), r.reasons.join(','));
  assert('dispatch_allowed = false', r.dispatch_allowed === false);
}

// [6] Snapshot connector NÃO contém nota mock/manual; mock/manual contém.
console.log('\n[6] snapshot note por origem');
{
  const conn = sanitizePolicySnapshot({ source: 'connector', insurer_key: 'ALLI', product: 'RESI' });
  assert('connector note não diz mock/manual', !/mock\/manual/i.test(String(conn.note)), String(conn.note));
  assert('connector note menciona InfoCap/connector', /InfoCap\/connector/i.test(String(conn.note)), String(conn.note));
  assert('connector note: sem payload bruto', /não contém payload bruto/i.test(String(conn.note)), String(conn.note));
  assert('connector preserva source', conn.source === 'connector');
  const infocap = sanitizePolicySnapshot({ source: 'infocap' });
  assert('infocap também usa nota connector', /InfoCap\/connector/i.test(String(infocap.note)));
  const mock = sanitizePolicySnapshot({ source: 'snapshot' });
  assert('mock/snapshot mantém nota mock/manual', /mock\/manual/i.test(String(mock.note)), String(mock.note));
}

// [7] Humanizadores de seguradora/produto.
console.log('\n[7] humanizar seguradora/produto');
{
  assert('ALLI → Allianz', humanizeInsurer('ALLI') === 'Allianz');
  assert('RESI → Residencial', humanizeProduct('RESI') === 'Residencial');
  assert('desconhecida → title case', humanizeInsurer('xyz seguros') === 'Xyz Seguros', humanizeInsurer('xyz seguros'));
}

// [8] Reasoning message não vaza PII e cita "Allianz Residencial".
console.log('\n[8] reasoning message segura');
{
  const msg = buildCoverageReasoningMessage({ state: 'human_validation_required', human_required: true }, { insurer: 'ALLI', product: 'RESI', active_now: true });
  assert('cita Allianz Residencial', /Allianz Residencial/.test(msg), msg);
  assert('não vaza dígitos longos', !/\d{6,}/.test(msg), msg);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) {
  for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`);
  process.exit(1);
}
process.exit(0);
