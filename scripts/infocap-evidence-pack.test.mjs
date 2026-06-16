#!/usr/bin/env node
/**
 * 42I3A — Policy Evidence Pack unit tests (offline, sem rede).
 *
 * Exercita os normalizadores PUROS de lib/attendance/policy-evidence-pack.ts
 * contra fixtures sanitizadas. Roda direto no Node 24 (type-stripping de .ts).
 *
 *   node scripts/infocap-evidence-pack.test.mjs
 *
 * NUNCA usa dados reais. Garante: existência != cobertura, sinais corretos,
 * confiança coerente, cancelada/vencida tratadas, nenhum PII cru.
 */
import {
  buildPolicyEvidencePackFromDocument,
  normalizeEvidencePack,
  evidencePackToCoverageEvidence,
  buildPolicyInterpretationContext,
  coverageSummaryFromPack,
  safeEvidencePackSummary,
} from '../lib/attendance/policy-evidence-pack.ts';
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

// "now" fixo p/ vigência determinística (jun/2026).
const NOW = new Date(Date.UTC(2026, 5, 11));

console.log('== 42I3A — Policy Evidence Pack (offline) ==');

// [1] Detalhe SEM coberturas → existência confirmada, cobertura NÃO.
console.log('\n[1] policy_detail sem coberturas');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_NO_COVERAGE, NOW);
  assert('policy_found = true', pack.policy_found === true);
  assert('coverages_count = 0', pack.coverages_count === 0, `cc=${pack.coverages_count}`);
  assert('confidence = low', pack.confidence === 'low', `conf=${pack.confidence}`);
  // Há texto de ramo ("RESI") mas sem coberturas → sinal é false (não null).
  assert('electrician = false (texto sem match)', pack.assistance_signals.electrician === false, `el=${pack.assistance_signals.electrician}`);
  assert('limitations menciona cobertura não detalhada', pack.limitations.some((l) => /cobertura específica não/i.test(l)));
  const ctx = buildPolicyInterpretationContext({ pack });
  assert('coverage_confirmed = false', ctx.coverage_confirmed === false);
  const ce = evidencePackToCoverageEvidence(pack);
  assert('summary diferencia localizada vs confirmada', /localizada/i.test(ce.coverage_summary) && /não confirmada/i.test(ce.coverage_summary), ce.coverage_summary);
}

// [2] Detalhe COM sinais residencial/elétrico vigente → high + cobertura confirmada.
console.log('\n[2] policy_detail com sinais de assistência residencial/elétrico (vigente)');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_WITH_SIGNALS, NOW);
  assert('residential = true', pack.assistance_signals.residential === true);
  assert('electrician = true', pack.assistance_signals.electrician === true);
  assert('emergency_assistance = true', pack.assistance_signals.emergency_assistance === true);
  assert('coverages_count = 3', pack.coverages_count === 3, `cc=${pack.coverages_count}`);
  assert('coverage_sections preenchidas', pack.coverage_sections.length === 3, `cs=${pack.coverage_sections.length}`);
  assert('active_now = true (vigente)', pack.active_now === true, `an=${pack.active_now}`);
  assert('expired = false', pack.expired === false, `ex=${pack.expired}`);
  assert('confidence = high', pack.confidence === 'high', `conf=${pack.confidence}`);
  assert('human_required = false', pack.human_required === false);
  const ctx = buildPolicyInterpretationContext({ pack, insuredQuestion: 'tenho cobertura de eletricista?' });
  assert('coverage_confirmed = true', ctx.coverage_confirmed === true);
  assert('rules: não inventar cobertura', ctx.rules.some((r) => /NÃO invente/i.test(r)));
  assert('insured_question preservada', ctx.insured_question === 'tenho cobertura de eletricista?');
}

// [3] Detalhe CANCELADO → low, human_required, não confirma cobertura.
console.log('\n[3] policy_detail cancelado');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_CANCELLED, NOW);
  assert('cancelled = true', pack.cancelled === true);
  assert('active_now = false', pack.active_now === false, `an=${pack.active_now}`);
  assert('confidence = low', pack.confidence === 'low', `conf=${pack.confidence}`);
  assert('human_required = true', pack.human_required === true);
  const ce = evidencePackToCoverageEvidence(pack);
  assert('summary alerta cancelamento', /cancelada/i.test(ce.coverage_summary), ce.coverage_summary);
  const ctx = buildPolicyInterpretationContext({ pack });
  assert('coverage_confirmed = false (cancelada)', ctx.coverage_confirmed === false);
}

// [4] Vencida (fimvig no passado) → expired true, active false.
console.log('\n[4] apólice vencida (multiple_matches[1])');
{
  const pack = buildPolicyEvidencePackFromDocument(MULTIPLE_MATCHES_DOCS[1], NOW);
  assert('expired = true', pack.expired === true, `ex=${pack.expired}`);
  assert('active_now = false', pack.active_now === false, `an=${pack.active_now}`);
}

// [5] normalizeEvidencePack round-trip + segurança (sem PII crua).
console.log('\n[5] normalizeEvidencePack + sanitização');
{
  const pack = buildPolicyEvidencePackFromDocument(DETAIL_WITH_SIGNALS, NOW);
  const norm = normalizeEvidencePack(pack);
  assert('normalize preserva confidence', norm.confidence === 'high');
  assert('holder mascarado (iniciais)', /\*\*\*/.test(norm.holder_name_masked || ''), `h=${norm.holder_name_masked}`);
  assert('número mascarado', /^\*\*\*\*/.test(norm.masked_policy_number || ''), `n=${norm.masked_policy_number}`);
  const raw = JSON.stringify(norm) + JSON.stringify(safeEvidencePackSummary(pack));
  assert('não vaza nome cru "Fulano"', !/Fulano/i.test(raw), 'nome cru presente');
  assert('não vaza número de apólice cru', !raw.includes('0001234567'), 'numero cru presente');
  // normalize de pack inválido
  assert('normalize(null) = null', normalizeEvidencePack(null) === null);
  assert('coverageSummary é string', typeof coverageSummaryFromPack(pack) === 'string');
}

// [6] multiple_matches: ordenação esperada (vigente > vencida > cancelada).
console.log('\n[6] ordenação de múltiplas apólices (espelho do backend)');
{
  const packs = MULTIPLE_MATCHES_DOCS.map((d) => buildPolicyEvidencePackFromDocument(d, NOW));
  const active = packs.filter((p) => p.active_now === true);
  const expired = packs.filter((p) => p.expired === true && !p.cancelled);
  const cancelled = packs.filter((p) => p.cancelled);
  assert('1 apólice vigente (97652)', active.length === 1 && active[0].policy_ref === '97652', `active=${active.map((p) => p.policy_ref)}`);
  assert('1 vencida não cancelada (97572)', expired.length === 1 && expired[0].policy_ref === '97572');
  assert('1 cancelada (93643)', cancelled.length === 1 && cancelled[0].policy_ref === '93643');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) {
  for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`);
  process.exit(1);
}
process.exit(0);
