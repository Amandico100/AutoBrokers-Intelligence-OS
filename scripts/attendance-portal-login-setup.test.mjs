#!/usr/bin/env node
/**
 * 43P4 — Assisted Real Login Setup & Secure SessionRef Capture (offline).
 *
 *   node scripts/attendance-portal-login-setup.test.mjs
 *
 * Garante: gates (flags/kill/approval/credential); awaiting_approval→approve;
 * challenge → human (OTP mascarado); captura só ref opaca (rejeita cookie/
 * storageState); SessionRef mascarado; nenhuma ação de negócio; sem browser real.
 */
import {
  evaluateLoginSetupGate,
  startLoginSetup,
  approveLoginSetup,
  applyLoginSetupStep,
  sanitizeLoginSetup,
  findLoginSetupSecrets,
} from '../lib/attendance/portal-login-setup.ts';
import {
  captureSessionRef,
  verifyCapturedSession,
  findCaptureSecrets,
  sanitizeCapturedSessionRef,
} from '../lib/attendance/portal-session-capture.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const flagsOff = { global_kill_switch: true, portal_real_action_enabled: false, portal_login_real_enabled: false, portal_session_capture_enabled: false };
const flagsOn = { global_kill_switch: false, portal_real_action_enabled: true, portal_login_real_enabled: true, portal_session_capture_enabled: true };
function ctx(over = {}) { return { flags: flagsOn, account_present: true, credential_present: true, portal_healthy: true, approval_exists: false, ...over }; }
function start(over = {}) { return startLoginSetup({ portal_id: 'allianz__allianznet_corretor_portal_do_corretor', portal_account_id: 'pacct-1', owner_key: 'allianz', provider: 'browserbase', context: ctx(over) }); }

console.log('== 43P4 — Assisted Real Login Setup ==');

// [1] gates.
console.log('\n[1] gates');
{
  const off = evaluateLoginSetupGate(ctx({ flags: flagsOff }));
  assert('flags off → bloqueado', off.allowed === false && off.blockers.includes('global_kill_switch_active') && off.blockers.includes('portal_login_real_disabled'));
  const noCred = evaluateLoginSetupGate(ctx({ credential_present: false }));
  assert('sem credential → bloqueado', noCred.blockers.includes('no_credential_ref'));
  const noAcct = evaluateLoginSetupGate(ctx({ account_present: false }));
  assert('sem conta → bloqueado', noAcct.blockers.includes('no_portal_account'));
  const okNoApproval = evaluateLoginSetupGate(ctx());
  assert('sem approval → bloqueado (gate)', okNoApproval.allowed === false && okNoApproval.blockers.includes('no_human_approval'));
  const full = evaluateLoginSetupGate(ctx({ approval_exists: true }));
  assert('tudo ok → allowed', full.allowed === true && full.blockers.length === 0);
}

// [2] start states.
console.log('\n[2] start');
{
  const off = start({ flags: flagsOff });
  assert('flags off → draft + enable flags', off.status === 'draft' && off.next_step === 'enable_flags_and_kill_switch_off');
  const noAcct = start({ account_present: false });
  assert('sem conta → create_portal_account', noAcct.next_step === 'create_portal_account');
  const noCred = start({ credential_present: false });
  assert('sem credential → add_credential_ref', noCred.next_step === 'add_credential_ref');
  const awaiting = start();
  assert('flags on sem approval → awaiting_approval', awaiting.status === 'awaiting_approval' && awaiting.next_step === 'human_approval_required');
  assert('start real_browser_opened false', awaiting.real_browser_opened === false);
  assert('start business_action_allowed false', awaiting.business_action_allowed === false);
  const ready = start({ approval_exists: true });
  assert('com approval → ready_to_open_browser', ready.status === 'ready_to_open_browser' && ready.next_step === 'open_browser');
}

// [3] approve.
console.log('\n[3] approve');
{
  const awaiting = start();
  const approved = approveLoginSetup(awaiting);
  assert('approve → ready_to_open_browser', approved.status === 'ready_to_open_browser');
  assert('approve remove blocker approval', !approved.blockers.includes('no_human_approval'));
}

// [4] challenge → human, OTP mascarado.
console.log('\n[4] challenge');
{
  const ready = start({ approval_exists: true });
  const ch = applyLoginSetupStep(ready, { type: 'challenge', challenge_signal: 'informe o código 123456' });
  assert('challenge → challenge_required', ch.status === 'challenge_required' && ch.next_step === 'human_challenge_required');
  assert('challenge requires_human, no bypass', ch.challenge.requires_human === true && ch.challenge.bypass_allowed === false);
  assert('challenge kind otp', ch.challenge.kind === 'otp', ch.challenge.kind);
  assert('OTP mascarado', !JSON.stringify(ch).includes('123456'));
}

// [5] captura segura.
console.log('\n[5] captura');
{
  let threw = false;
  try { captureSessionRef({ portal_id: 'p', storage_ref: 's', cookies: [{ name: 'sid', value: 'x' }] }); } catch { threw = true; }
  assert('captura com cookies → lança', threw);
  let threw2 = false;
  try { captureSessionRef({ portal_id: 'p', storage_ref: 's', storage_state: '{}' }); } catch { threw2 = true; }
  assert('captura com storage_state → lança', threw2);
  const cap = captureSessionRef({ portal_id: 'p', portal_account_id: 'pacct-1', storage_ref: 'store://abc123def456', provider: 'browserbase', status: 'healthy', expires_at: new Date(Date.now() + 6048e5).toISOString() });
  assert('storage_ref mascarado', cap.storage_ref_masked.includes('…') && !cap.storage_ref_masked.includes('abc123def456'));
  assert('verify healthy usable', verifyCapturedSession(cap).usable === true);
  assert('findCaptureSecrets detecta', findCaptureSecrets({ a: { cookie: 'x' } }).length > 0);
  assert('sanitize sem ref cru', !JSON.stringify(sanitizeCapturedSessionRef(cap)).includes('abc123def456'));
}

// [6] complete flow → session_verified, sem segredo.
console.log('\n[6] complete');
{
  const ready = start({ approval_exists: true });
  const captured = captureSessionRef({ portal_id: ready.portal_id, portal_account_id: 'pacct-1', storage_ref: 'store://xyz789capture', provider: 'browserbase', status: 'healthy' });
  let s = applyLoginSetupStep(ready, { type: 'open_browser', real_browser_adapter_available: false });
  assert('open → waiting_human_login (sandbox)', s.status === 'waiting_human_login' && s.real_browser_opened === false);
  assert('open marca sandbox (sem browser real)', s.events.some((e) => e.type === 'browser_opened_sandbox'));
  s = applyLoginSetupStep(s, { type: 'human_login' });
  s = applyLoginSetupStep(s, { type: 'complete', captured });
  assert('complete → session_captured', s.status === 'session_captured' && s.session_ref_masked === captured.storage_ref_masked);
  s = applyLoginSetupStep(s, { type: 'verify' });
  assert('verify → session_verified', s.status === 'session_verified');
  assert('session_verified business_action_allowed false', s.business_action_allowed === false && s.real_action_allowed === false);
  assert('complete sem storageState cru', !JSON.stringify(s).includes('xyz789capture'));
  assert('sanitize sem segredo', findLoginSetupSecrets(sanitizeLoginSetup(s)).length === 0);
  // evento após terminal ignorado
  const after = applyLoginSetupStep(s, { type: 'open_browser' });
  assert('evento após terminal ignorado', after.events.some((e) => e.type === 'event_ignored_terminal'));
}

// [7] cancel.
console.log('\n[7] cancel');
{
  const s = applyLoginSetupStep(start({ approval_exists: true }), { type: 'cancel' });
  assert('cancel → cancelled', s.status === 'cancelled');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
