#!/usr/bin/env node
/** 42X5B — política canônica de envio WhatsApp (offline, puro). */
import { evaluateWhatsAppOutboundGate } from '../lib/attendance/whatsapp-outbound-gate.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

// contexto "tudo liberado" (resposta a inbound, não-proativo)
const allOn = {
  global_kill_switch: false, attendance_dry_run: false, outbound_real_enabled: true,
  external_action_real_enabled: true, insurer_whatsapp_real_enabled: true,
  external_send_authorized: true, consent_ok: true, approval_ok: true,
  is_proactive: false, channel: 'customer_whatsapp', environment: 'production',
};

console.log('== 42X5B — WhatsApp Outbound Gate ==\n');

assert('tudo on → envia', (() => { const d = evaluateWhatsAppOutboundGate(allOn); return d.external_send_allowed === true && d.dry_run === false && d.blockers.length === 0; })());
assert('kill switch → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, global_kill_switch: true }).external_send_allowed === false);
assert('dry_run flag → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, attendance_dry_run: true }).dry_run === true);
assert('outbound_real off → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, outbound_real_enabled: false }).external_send_allowed === false);
assert('external_action off → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, external_action_real_enabled: false }).blockers.includes('external_action_real_disabled'));
assert('sem autorização explícita → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, external_send_authorized: false }).external_send_allowed === false);
assert('sem consentimento → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, consent_ok: false }).blockers.includes('consent_missing'));
assert('proativo sem approval → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, is_proactive: true, approval_ok: false }).blockers.includes('approval_required'));
assert('proativo com approval → envia', evaluateWhatsAppOutboundGate({ ...allOn, is_proactive: true, approval_ok: true }).external_send_allowed === true);
assert('sandbox → dry-run', evaluateWhatsAppOutboundGate({ ...allOn, environment: 'sandbox' }).dry_run === true);
assert('canal seguradora sem flag → bloqueia', evaluateWhatsAppOutboundGate({ ...allOn, channel: 'insurer_whatsapp', insurer_whatsapp_real_enabled: false }).blockers.includes('insurer_whatsapp_real_send_disabled'));
// default seguro: tudo off → dry-run
assert('tudo off → dry-run (falha fechado)', (() => { const d = evaluateWhatsAppOutboundGate({ global_kill_switch: true, attendance_dry_run: true, outbound_real_enabled: false, external_action_real_enabled: false, external_send_authorized: false, consent_ok: false, approval_ok: false, is_proactive: false }); return d.external_send_allowed === false && d.dry_run === true; })());

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
