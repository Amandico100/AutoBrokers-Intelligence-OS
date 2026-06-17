#!/usr/bin/env node
/**
 * 42M1 — Vision & Document Extraction (offline, sem rede).
 *
 *   node scripts/attendance-media-vision-document.test.mjs
 *
 * Garante: derivação visual (issue/risco/área); resposta controlada (não ecoa
 * resumo cru, não confirma cobertura); vision/document gated off → fail-safe;
 * sem PII; Q&A de mídia (a foto ajuda? / enviei a apólice).
 */
import {
  deriveVisualEvidence,
  buildVisionCustomerReply,
  analyzeAttendanceImage,
  extractAttendanceDocument,
} from '../lib/attendance/attendance-media.ts';
import { classifyAttendanceQuestion } from '../lib/attendance/policy-qa.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== 42M1 — Vision & Document Extraction ==');

// [1] Derivação visual (mock de resumo do vision).
console.log('\n[1] deriveVisualEvidence');
{
  const elec = deriveVisualEvidence('A imagem mostra um quadro de disjuntores com um disjuntor desarmado na cozinha.');
  assert('detecta elétrico', elec.possible_issue_type === 'electrician');
  assert('sugere área (cozinha)', elec.possible_slots.suggested_affected_area === 'cozinha', JSON.stringify(elec.possible_slots));
  assert('sem risco aqui', elec.risk_hint === false);
  const risk = deriveVisualEvidence('Há fumaça e sinais de queimado próximo à tomada.');
  assert('detecta risco', risk.risk_hint === true);
  const plumb = deriveVisualEvidence('Vazamento de água embaixo da pia com cano molhado.');
  assert('detecta hidráulico', plumb.possible_issue_type === 'plumber');
  const doc = deriveVisualEvidence('Parece a foto de uma apólice/documento.');
  assert('detecta documento', doc.possible_issue_type === 'document');
  const none = deriveVisualEvidence('Uma parede branca.');
  assert('sem issue', none.possible_issue_type === null);
}

// [2] Resposta controlada (não ecoa resumo cru, não confirma cobertura).
console.log('\n[2] buildVisionCustomerReply');
{
  const elec = deriveVisualEvidence('quadro de disjuntores na cozinha');
  const reply = buildVisionCustomerReply(elec, 'Em qual área da casa?');
  assert('menciona análise', /analisei a imagem/i.test(reply));
  assert('menciona problema elétrico', /el[ée]trico/i.test(reply));
  assert('NÃO confirma cobertura', /cobertura ainda depende/i.test(reply) && !/cobertura confirmada|est[áa] coberto/i.test(reply), reply);
  assert('inclui retomada', /Para eu continuar:/i.test(reply));
  const risk = buildVisionCustomerReply(deriveVisualEvidence('fumaça e faísca'), null);
  assert('risco → orientação de segurança', /desligue o disjuntor/i.test(risk), risk);
  // não vaza resumo cru do LLM
  assert('não ecoa texto cru', !risk.includes('fumaça e faísca'));
}

// [3] Vision/Document gated off → fail-safe (sem rede).
console.log('\n[3] gated off');
{
  const v = await analyzeAttendanceImage({ companyId: 'co-1', imageUrl: 'https://x/y.jpg' });
  assert('vision off → unsupported', v.ok === false && v.reason === 'vision_disabled', JSON.stringify(v));
  const d = await extractAttendanceDocument({ companyId: 'co-1', documentUrl: 'https://x/y.pdf' });
  assert('document off → unsupported', d.ok === false && d.reason === 'document_extraction_disabled', JSON.stringify(d));
  const v2 = await analyzeAttendanceImage({ companyId: 'co-1' });
  assert('sem imagem → unsupported', v2.ok === false);
}

// [4] Q&A de mídia ampliado.
console.log('\n[4] Q&A mídia');
{
  const c = (m) => classifyAttendanceQuestion(m).category;
  assert('"posso te mandar uma foto?" → media_offer', c('posso te mandar uma foto?') === 'media_offer_question');
  assert('"a foto ajuda?" → media_offer', c('a foto ajuda no atendimento?') === 'media_offer_question');
  assert('"o documento serve?" → media_offer', c('o documento serve?') === 'media_offer_question');
  assert('"enviei a apólice" → media_offer', c('enviei a apólice em foto') === 'media_offer_question');
  assert('"é na cozinha" → slot_answer', c('é na cozinha') === 'slot_answer');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
