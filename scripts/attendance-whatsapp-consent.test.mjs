#!/usr/bin/env node
/** 42X5B — consentimento/opt-in WhatsApp (offline, puro). */
import { evaluateConsent, isWithinSessionWindow } from '../lib/attendance/whatsapp-consent.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const nowIso = new Date().toISOString();
const oldIso = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();

console.log('== 42X5B — WhatsApp Consent ==\n');

// opt_out sempre bloqueia
assert('opt_out bloqueia resposta', evaluateConsent({ record: { status: 'opted_out' }, is_proactive: false, last_inbound_at: nowIso }).consent_ok === false);
assert('opt_out bloqueia proativo', evaluateConsent({ record: { status: 'opted_out' }, is_proactive: true }).consent_ok === false);

// resposta a inbound dentro da janela → permitida (sessão), mesmo sem record
assert('resposta na janela → permitida', evaluateConsent({ record: null, is_proactive: false, last_inbound_at: nowIso }).consent_ok === true);
assert('resposta fora da janela sem opt-in → bloqueia', evaluateConsent({ record: null, is_proactive: false, last_inbound_at: oldIso }).consent_ok === false);
assert('resposta fora da janela com opt-in → permitida', evaluateConsent({ record: { status: 'opted_in' }, is_proactive: false, last_inbound_at: oldIso }).consent_ok === true);

// proativo exige opt-in explícito
assert('proativo sem opt-in → bloqueia', evaluateConsent({ record: null, is_proactive: true }).consent_ok === false);
assert('proativo com opt-in → permitido', evaluateConsent({ record: { status: 'opted_in' }, is_proactive: true }).consent_ok === true);
assert('proativo com sessão mas sem opt-in → bloqueia', evaluateConsent({ record: { status: 'session' }, is_proactive: true, last_inbound_at: nowIso }).consent_ok === false);

// janela de sessão
assert('isWithinSessionWindow recente true', isWithinSessionWindow({ record: null, is_proactive: false, last_inbound_at: nowIso }) === true);
assert('isWithinSessionWindow antigo false', isWithinSessionWindow({ record: null, is_proactive: false, last_inbound_at: oldIso }) === false);
assert('isWithinSessionWindow sem inbound false', isWithinSessionWindow({ record: null, is_proactive: false }) === false);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
