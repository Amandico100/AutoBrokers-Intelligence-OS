#!/usr/bin/env node
/**
 * 43P2 — Browser Relay Sandbox Harness (offline; nenhum browser/URL/credencial real).
 *
 *   node scripts/attendance-browser-relay-sandbox.test.mjs
 *
 * Garante: adapters mock (can*=false); start gating; observe/act/extract mock;
 * challenge → HITL (OTP mascarado); session expired → challenge; trace/replay sem
 * PII/segredo; cancel terminal; skyvern_lab não chama API.
 */
import {
  getBrowserRelayAdapter,
  getBrowserRelayAdapterRegistry,
  isKnownRelayProvider,
} from '../lib/attendance/browser-relay-adapters.ts';
import {
  startBrowserRelaySandbox,
  applyBrowserRelaySandboxStep,
  buildRelayTrace,
  buildRelayReplay,
  sanitizeRelayRuntimeOutput,
  findRelaySecrets,
} from '../lib/attendance/browser-relay-runtime.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const A = getBrowserRelayAdapter('browserbase');
function startOk(over = {}) {
  return startBrowserRelaySandbox({ portal_id: 'allianz__x', journey: 'login', provider: 'browserbase', portal_available: true, account_present: true, session_status: 'healthy', ...over }, A);
}

console.log('== 43P2 — Browser Relay Sandbox Harness ==');

// [1] adapters.
console.log('\n[1] adapters');
{
  const keys = getBrowserRelayAdapterRegistry().map((a) => a.provider_key);
  for (const k of ['browserbase', 'local_playwright', 'stagehand', 'skyvern_lab', 'mock']) assert(`adapter ${k}`, keys.includes(k));
  for (const a of getBrowserRelayAdapterRegistry()) {
    assert(`${a.provider_key} canOpenRealBrowser=false`, a.canOpenRealBrowser === false);
    assert(`${a.provider_key} canAccessRealUrl=false`, a.canAccessRealUrl === false);
    assert(`${a.provider_key} canUseRealCredential=false`, a.canUseRealCredential === false);
  }
  assert('provider desconhecido → mock', getBrowserRelayAdapter('telegram').provider_key === 'mock');
  assert('isKnownRelayProvider browserbase', isKnownRelayProvider('browserbase') === true);
}

// [2] start gating.
console.log('\n[2] start gating');
{
  const noPortal = startBrowserRelaySandbox({ portal_id: null, provider: 'browserbase', portal_available: false, account_present: false }, A);
  assert('sem portal → failed_sandbox', noPortal.status === 'failed_sandbox' && noPortal.next_step === 'no_portal_definition');
  const noAcct = startBrowserRelaySandbox({ portal_id: 'allianz__x', provider: 'browserbase', portal_available: true, account_present: false }, A);
  assert('sem conta → create_portal_account', noAcct.status === 'draft' && noAcct.next_step === 'create_portal_account');
  const demo = startBrowserRelaySandbox({ portal_id: 'allianz__x', provider: 'browserbase', portal_available: true, account_present: false, allow_demo_without_account: true }, A);
  assert('demo sem conta → running_sandbox', demo.status === 'running_sandbox');
  const expired = startOk({ session_status: 'expired' });
  assert('sessão expirada → challenge_required', expired.status === 'challenge_required' && expired.challenges[0].kind === 'session_expired');
  const ok = startOk();
  assert('conta saudável → running_sandbox', ok.status === 'running_sandbox' && ok.next_step === 'observe');
  assert('start real_action_allowed false', ok.real_action_allowed === false);
  assert('start abriu mock (sem browser real)', ok.events.some((e) => e.type === 'session_opened_mock'));
}

// [3] observe/act/extract mock.
console.log('\n[3] observe/act/extract');
{
  let s = startOk();
  s = applyBrowserRelaySandboxStep(s, { type: 'observe', instruction: 'olhe a tela de login' }, A);
  assert('observe → observing', s.status === 'observing' && s.observed_states.length === 1);
  s = applyBrowserRelaySandboxStep(s, { type: 'act', instruction: 'clique em entrar' }, A);
  assert('act → acting, performed false', s.status === 'acting' && s.actions[0].performed === false);
  s = applyBrowserRelaySandboxStep(s, { type: 'extract', query: 'status da apólice' }, A);
  assert('extract → extracting, dados mock', s.status === 'extracting' && s.extracted_data.length === 1);
  s = applyBrowserRelaySandboxStep(s, { type: 'complete' }, A);
  assert('complete → completed_sandbox', s.status === 'completed_sandbox');
  const after = applyBrowserRelaySandboxStep(s, { type: 'observe' }, A);
  assert('evento após terminal ignorado', after.events.some((e) => e.type === 'event_ignored_terminal'));
}

// [4] challenge handling.
console.log('\n[4] challenge');
{
  let s = startOk();
  const cap = applyBrowserRelaySandboxStep(s, { type: 'challenge', challenge_signal: 'apareceu recaptcha' }, A);
  assert('captcha → challenge_required', cap.status === 'challenge_required' && cap.challenges.slice(-1)[0].kind === 'captcha');
  assert('captcha requires_human, no bypass', cap.challenges.slice(-1)[0].requires_human === true && cap.challenges.slice(-1)[0].bypass_allowed === false);
  const otp = applyBrowserRelaySandboxStep(s, { type: 'challenge', challenge_signal: 'informe o codigo 482913 enviado por sms' }, A);
  assert('otp classificado', otp.challenges.slice(-1)[0].kind === 'otp');
  assert('otp mascarado (sem 482913)', !JSON.stringify(otp).includes('482913'));
}

// [5] cancel.
console.log('\n[5] cancel');
{
  const s = applyBrowserRelaySandboxStep(startOk(), { type: 'cancel' }, A);
  assert('cancel → cancelled', s.status === 'cancelled' && s.outcome === 'cancelled');
}

// [6] trace / replay sanitizados.
console.log('\n[6] trace/replay');
{
  let s = startOk();
  s = applyBrowserRelaySandboxStep(s, { type: 'observe' }, A);
  s = applyBrowserRelaySandboxStep(s, { type: 'challenge', challenge_signal: 'recaptcha' }, A);
  const trace = buildRelayTrace(s);
  assert('trace has_pii false', trace.has_pii === false);
  assert('trace real_action_allowed false', trace.real_action_allowed === false);
  assert('trace challenge captcha', trace.challenges.some((c) => c.kind === 'captcha'));
  const replay = buildRelayReplay(s);
  assert('replay has_pii false', replay.has_pii === false);
  assert('replay timeline numerada', replay.timeline[0].step === 1);
}

// [7] sanitização / sem segredo.
console.log('\n[7] segurança');
{
  const dirty = { relay_id: 'x', cookie: 'sid=abc', nested: { password: 'p', ok: 'v' } };
  const clean = sanitizeRelayRuntimeOutput(dirty);
  assert('sanitize remove cookie/password', findRelaySecrets(clean).length === 0);
  assert('findRelaySecrets detecta storage_state', findRelaySecrets({ a: { storage_state: 'x' } }).length > 0);
  // adapter skyvern_lab mock não chama API
  const sky = getBrowserRelayAdapter('skyvern_lab');
  const r = sky.observe({ relay_id: 'x', portal_id: 'p' }, { instruction: 'olhe' });
  assert('skyvern_lab observe mock', r.mock === true && r.real_action_allowed === false);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
