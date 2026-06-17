#!/usr/bin/env node
/**
 * 42M0 — Media Evidence Pipeline (offline, sem rede).
 *
 *   node scripts/attendance-media.test.mjs
 *
 * Garante: normalização sem URL/base64/PII; roteamento por tipo; mídia vira
 * evidência mas NÃO confirma cobertura; áudio fail-safe (flag off); Q&A de oferta de mídia.
 */
import {
  normalizeAttendanceMedia,
  processAttendanceMedia,
  buildMediaEvidenceRecord,
  transcribeAttendanceAudio,
} from '../lib/attendance/attendance-media.ts';
import { classifyAttendanceQuestion, isAnswerableQuestion, answerPolicyQuestionDeterministic, buildPolicyQAContext } from '../lib/attendance/policy-qa.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const SECRET_URL = 'https://cdn.zapi.io/AUDIO/secret-token-12345/file.ogg';
const SECRET_B64 = 'data:audio/ogg;base64,QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVowMTIzNDU2Nzg5';

console.log('== 42M0 — Media Evidence Pipeline ==');

// [1] Normalização + classificação por mime.
console.log('\n[1] normalização');
{
  const a = normalizeAttendanceMedia({ media_url: SECRET_URL, mime_type: 'audio/ogg', source_channel: 'whatsapp' });
  assert('áudio detectado por mime', a.media_kind === 'audio');
  assert('safe_ref não é a URL', a.safe_ref && !a.safe_ref.includes('secret-token'), a.safe_ref);
  assert('has_payload true', a.has_payload === true);
  const img = normalizeAttendanceMedia({ media_url: 'https://x/y.jpg', mime_type: 'image/jpeg' });
  assert('imagem por mime', img.media_kind === 'image');
  const doc = normalizeAttendanceMedia({ media_url: 'https://x/y.pdf', mime_type: 'application/pdf' });
  assert('documento por mime', doc.media_kind === 'document');
  const loc = normalizeAttendanceMedia({ location: { lat: -23.5, lng: -46.6 } });
  assert('localização', loc.media_kind === 'location');
  const b = normalizeAttendanceMedia({ media_kind: 'audio', media_base64: SECRET_B64 });
  assert('size_hint do base64', typeof b.size_hint === 'string');
}

// [2] Sem PII/URL/base64 no objeto normalizado.
console.log('\n[2] sem PII');
{
  const a = normalizeAttendanceMedia({ media_url: SECRET_URL, media_base64: SECRET_B64, mime_type: 'audio/ogg', location: { lat: -23.5, lng: -46.6, address_hint: 'Rua Secreta 123' } });
  const raw = JSON.stringify(a);
  assert('não vaza URL', !raw.includes('secret-token'));
  assert('não vaza base64', !raw.includes('QUJDREVG'));
  assert('não vaza coordenadas', !raw.includes('-23.5') && !raw.includes('-46.6'));
  assert('não vaza endereço', !raw.includes('Rua Secreta 123'));
  assert('redaction declarada', Array.isArray(a.redaction) && a.redaction.length > 0);
}

// [3] Roteamento por tipo + NÃO confirma cobertura.
console.log('\n[3] roteamento');
{
  const audio = processAttendanceMedia(normalizeAttendanceMedia({ media_kind: 'audio', media_url: SECRET_URL, mime_type: 'audio/ogg' }));
  assert('áudio → pending + backend_transcribe', audio.status === 'pending' && audio.processing_route === 'backend_transcribe');
  const image = processAttendanceMedia(normalizeAttendanceMedia({ media_kind: 'image', media_url: 'https://x/y.jpg', mime_type: 'image/jpeg' }));
  assert('imagem → pending + vision_future', image.status === 'pending' && image.processing_route === 'vision_future');
  const doc = processAttendanceMedia(normalizeAttendanceMedia({ media_kind: 'document', media_url: 'https://x/y.pdf', mime_type: 'application/pdf' }));
  assert('documento → pending + document_future', doc.status === 'pending' && doc.processing_route === 'document_future');
  const loc = processAttendanceMedia(normalizeAttendanceMedia({ location: { lat: -23.5, lng: -46.6 } }), { location: { address_hint: 'bairro X' } });
  assert('localização → processed + slot', loc.status === 'processed' && loc.possible_slots.property_location_provided === true);
  assert('localização summary sem coordenadas', !/-23\.5|-46\.6/.test(JSON.stringify(loc)));
  for (const r of [audio, image, doc, loc]) {
    assert(`${r.media_kind}: limita cobertura`, r.limitations.some((l) => /não confirma cobertura/i.test(l)));
    assert(`${r.media_kind}: tem resposta humana`, typeof r.safe_customer_reply === 'string' && r.safe_customer_reply.length > 0);
  }
  assert('imagem reply não vaza URL', !/http/.test(image.safe_customer_reply));
}

// [4] Evidence record sanitizado.
console.log('\n[4] evidence record');
{
  const n = normalizeAttendanceMedia({ media_kind: 'image', media_url: SECRET_URL, mime_type: 'image/jpeg' });
  const rec = buildMediaEvidenceRecord(n, processAttendanceMedia(n));
  const raw = JSON.stringify(rec);
  assert('record sem URL/base64', !raw.includes('secret-token') && !raw.includes('QUJDREVG'));
  assert('record tem media_kind/provenance/status', rec.media_kind === 'image' && typeof rec.provenance === 'string' && typeof rec.status === 'string');
  assert('record tem processed_at', typeof rec.processed_at === 'string');
}

// [5] Áudio fail-safe (flag off → sem rede).
console.log('\n[5] transcrição fail-safe');
{
  const r = await transcribeAttendanceAudio({ companyId: 'co-1', audioUrl: SECRET_URL });
  assert('flag off → media_disabled', r.ok === false && r.reason === 'media_disabled', JSON.stringify(r));
}

// [6] Q&A de oferta de mídia.
console.log('\n[6] Q&A oferta de mídia');
{
  const c = classifyAttendanceQuestion('posso te mandar uma foto do disjuntor?').category;
  assert('"posso mandar foto" → media_offer_question', c === 'media_offer_question', c);
  assert('media_offer é answerable', isAnswerableQuestion('media_offer_question') === true);
  const a = answerPolicyQuestionDeterministic('media_offer_question', buildPolicyQAContext({}, {}));
  assert('responde que pode mandar', /pode sim|pode me mandar/i.test(a.answer), a.answer);
  assert('cita evidência', /evid[êe]ncia/i.test(a.answer));
  assert('mantém limite de cobertura', /cobertura ainda depende|valida/i.test(a.answer), a.answer);
  // áudio em texto não vira media_offer
  assert('"estou sem luz" não é media_offer', classifyAttendanceQuestion('estou sem luz só na cozinha').category !== 'media_offer_question');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
