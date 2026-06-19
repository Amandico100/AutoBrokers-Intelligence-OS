#!/usr/bin/env node
/**
 * 43P4.1 — Browserbase Real Adapter Homologation (offline; sem rede real).
 *
 *   node scripts/attendance-browserbase-real-adapter.test.mjs
 *
 * Garante: env/flags/approval bloqueiam; readiness sanitizado; caminho bloqueado
 * NÃO chama transport (sem rede); caminho permitido (mock) cria sessão sem expor
 * connectUrl/signingKey; close mock; can_open_real_browser=false por padrão.
 */
import {
  validateBrowserbaseEnv,
  evaluateBrowserbaseReadiness,
  createBrowserbaseLoginSession,
  closeBrowserbaseSession,
  sanitizeBrowserbaseSession,
  findBrowserbaseSecrets,
} from '../lib/attendance/browserbase-real-adapter.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const flagsOff = { global_kill_switch: true, portal_real_action_enabled: false, portal_login_real_enabled: false, portal_session_capture_enabled: false, browserbase_real_browser_enabled: false };
const flagsOn = { global_kill_switch: false, portal_real_action_enabled: true, portal_login_real_enabled: true, portal_session_capture_enabled: true, browserbase_real_browser_enabled: true };
const envOn = { BROWSERBASE_API_KEY: 'bb_key_xxx', BROWSERBASE_PROJECT_ID: 'proj_123' };

console.log('== 43P4.1 — Browserbase Real Adapter ==');

// [1] env.
console.log('\n[1] env');
{
  assert('env vazio → ambos false', validateBrowserbaseEnv({}).api_key_present === false && validateBrowserbaseEnv({}).project_id_present === false);
  assert('env presente', validateBrowserbaseEnv(envOn).api_key_present === true && validateBrowserbaseEnv(envOn).project_id_present === true);
}

// [2] readiness bloqueia.
console.log('\n[2] readiness');
{
  const r0 = evaluateBrowserbaseReadiness({ flags: flagsOff, approval_exists: false, env: {} });
  assert('default → can_open false', r0.can_open_real_browser === false);
  assert('env ausente blocker', r0.blockers.includes('browserbase_api_key_missing') && r0.blockers.includes('browserbase_project_id_missing'));
  assert('kill switch blocker', r0.blockers.includes('global_kill_switch_active'));
  assert('browserbase flag blocker', r0.blockers.includes('browserbase_real_browser_disabled'));
  assert('readiness real_action_allowed false', r0.real_action_allowed === false);

  const rNoApproval = evaluateBrowserbaseReadiness({ flags: flagsOn, approval_exists: false, env: envOn });
  assert('sem approval → blocker', rNoApproval.can_open_real_browser === false && rNoApproval.blockers.includes('no_human_approval'));

  const rFull = evaluateBrowserbaseReadiness({ flags: flagsOn, approval_exists: true, env: envOn });
  assert('tudo ok → can_open true', rFull.can_open_real_browser === true && rFull.blockers.length === 0);
  assert('readiness sanitizado (sem segredo)', findBrowserbaseSecrets(rFull).length === 0);
}

// [3] create bloqueado NÃO chama rede.
console.log('\n[3] create bloqueado');
{
  let calls = 0;
  const spy = { createSession: async () => { calls++; return { id: 'x' }; } };
  const blocked = evaluateBrowserbaseReadiness({ flags: flagsOff, approval_exists: false, env: {} });
  const res = await createBrowserbaseLoginSession({ readiness: blocked }, spy);
  assert('bloqueado → opened false', res.opened === false && res.status === 'blocked');
  assert('bloqueado → transport NÃO chamado', calls === 0);
  assert('bloqueado real_action_allowed false', res.real_action_allowed === false);
}

// [4] create permitido (mock) cria sessão sem expor segredo.
console.log('\n[4] create permitido (mock)');
{
  const rFull = evaluateBrowserbaseReadiness({ flags: flagsOn, approval_exists: true, env: envOn });
  const mock = { createSession: async () => ({ id: 'sess_abc', status: 'RUNNING', region: 'us-east-1', expiresAt: '2026-06-19T23:00:00Z', connectUrl: 'wss://connect.browserbase.com?apiKey=bb_key_xxx', signingKey: 'super-secret-signing' }) };
  const res = await createBrowserbaseLoginSession({ readiness: rFull, env: envOn }, mock);
  assert('permitido → opened true', res.opened === true && res.status === 'created');
  assert('captura session_id', res.session_id === 'sess_abc');
  assert('captura status', res.session_status === 'RUNNING');
  assert('NÃO expõe connectUrl', !('connectUrl' in res) && !JSON.stringify(res).includes('connect.browserbase.com'));
  assert('NÃO expõe signingKey', !JSON.stringify(res).includes('super-secret-signing'));
  assert('permitido real_action_allowed false', res.real_action_allowed === false);
}

// [5] sanitize / secrets.
console.log('\n[5] sanitize');
{
  const raw = { id: 'x', status: 'RUNNING', connectUrl: 'wss://...key', signingKey: 'sk', seleniumRemoteUrl: 'http://...', region: 'us' };
  const clean = sanitizeBrowserbaseSession(raw);
  assert('sanitize remove connectUrl/signingKey', findBrowserbaseSecrets(clean).length === 0);
  assert('sanitize mantém id/status/region', clean.id === 'x' && clean.status === 'RUNNING' && clean.region === 'us');
  assert('findBrowserbaseSecrets detecta cookie', findBrowserbaseSecrets({ a: { cookie: 'x' } }).length > 0);
}

// [6] close.
console.log('\n[6] close');
{
  const blocked = evaluateBrowserbaseReadiness({ flags: flagsOff, env: {} });
  let calls = 0;
  const t = { release: async () => { calls++; } };
  const r1 = await closeBrowserbaseSession({ session_id: 'sess_abc', readiness: blocked }, t);
  assert('close bloqueado não chama rede', r1.closed === false && calls === 0);
  const rFull = evaluateBrowserbaseReadiness({ flags: flagsOn, approval_exists: true, env: envOn });
  const r2 = await closeBrowserbaseSession({ session_id: 'sess_abc', readiness: rFull, env: envOn }, t);
  assert('close permitido (mock) → released', r2.closed === true && calls === 1);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
