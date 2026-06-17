#!/usr/bin/env node
/**
 * 42M2 — Real Document Extraction (offline, sem rede).
 *
 *   node scripts/attendance-document-extraction.test.mjs
 *
 * Garante: conflito documento×InfoCap detectável; documento NÃO confirma cobertura;
 * respostas controladas; gated off → fail-safe; sem PII/URL/base64.
 */
import {
  extractAttendanceDocument,
  detectDocumentInfocapConflict,
  buildDocumentCustomerReply,
} from '../lib/attendance/attendance-media.ts';
import { classifyAttendanceQuestion, answerPolicyQuestionDeterministic, buildPolicyQAContext } from '../lib/attendance/policy-qa.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== 42M2 — Real Document Extraction ==');

// [1] Gated off → fail-safe (sem rede).
console.log('\n[1] gated off');
{
  const d = await extractAttendanceDocument({ companyId: 'co-1', documentUrl: 'https://x/apolice.pdf', mimeType: 'application/pdf' });
  assert('document off → unsupported', d.ok === false && d.reason === 'document_extraction_disabled', JSON.stringify(d));
  const d2 = await extractAttendanceDocument({ companyId: 'co-1' });
  assert('sem documento → unsupported', d2.ok === false);
}

// [2] Conflito documento × InfoCap.
console.log('\n[2] conflito documento × InfoCap');
{
  const snap = { insurer_key: 'Allianz', product: 'Residencial', masked_policy_number: '****99' };
  const same = detectDocumentInfocapConflict({ insurer: 'Allianz', masked_policy_number: '****99' }, snap);
  assert('mesma seguradora/apólice → sem conflito', same.conflict === false, JSON.stringify(same));
  const diffIns = detectDocumentInfocapConflict({ insurer: 'Porto Seguro' }, snap);
  assert('seguradora divergente → conflito', diffIns.conflict === true && diffIns.reasons.includes('insurer_mismatch'));
  const diffNum = detectDocumentInfocapConflict({ insurer: 'Allianz', masked_policy_number: '****53' }, snap);
  assert('apólice divergente → conflito', diffNum.conflict === true && diffNum.reasons.includes('policy_number_mismatch'));
  assert('sem snapshot → sem conflito', detectDocumentInfocapConflict({ insurer: 'X' }, null).conflict === false);
}

// [3] Respostas controladas (NÃO confirma cobertura).
console.log('\n[3] respostas controladas');
{
  const ok = buildDocumentCustomerReply({ ok: true, summary: '...', possible_policy_info: {} }, false);
  assert('processed: evidência auxiliar', /evid[êe]ncia auxiliar/i.test(ok));
  assert('processed: cobertura depende de validação', /cobertura continua dependendo/i.test(ok));
  assert('processed: NÃO confirma', !/cobertura confirmada|est[áa] coberto|pode acionar/i.test(ok));
  const elec = buildDocumentCustomerReply({ ok: true, summary: '...', possible_policy_info: { document_mentions_assistance_electrician: true } }, false);
  assert('menção elétrica → termos gerais + validar', /termos gerais/i.test(elec) && /validar/i.test(elec));
  assert('menção elétrica NÃO confirma', !/sim,? cobre|cobertura confirmada/i.test(elec));
  const conf = buildDocumentCustomerReply({ ok: true, summary: '...' }, true);
  assert('conflito → validação humana', /divergir|validação/i.test(conf));
}

// [4] Q&A documento — "o PDF diz que cobre, posso acionar?" NÃO confirma.
console.log('\n[4] Q&A documento');
{
  const c = classifyAttendanceQuestion('o PDF diz que cobre, então posso acionar?').category;
  assert('"PDF diz que cobre" → coverage (não media_offer)', c === 'policy_coverage_question', c);
  const ctx = buildPolicyQAContext({ policy_source: 'connector', verification_status: 'verified_by_connector', policy_snapshot: { insurer_key: 'Allianz', active_now: true }, metadata: { policy_interpretation_context: { coverage_confirmed: false }, coverage_readiness: { human_required: true } } }, {});
  const a = answerPolicyQuestionDeterministic('policy_coverage_question', ctx);
  assert('coverage NÃO confirma mesmo citando PDF', !/sim,? (cobre|pode acionar)/i.test(a.answer) && /valida/i.test(a.answer), a.answer);
  assert('"posso mandar o PDF?" → media_offer', classifyAttendanceQuestion('posso te enviar o documento em pdf?').category === 'media_offer_question');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
