#!/usr/bin/env node
/** 43P-FINAL-1 — Portal Real Execution Controller (offline, DI mocks, sem rede). */
import {
  initCanary, markAwaitingApproval, applyAuthorization, openCanaryBrowser, markChallenge,
  resolveChallenge, captureCanarySession, verifyCanarySession, attachReadOnlySkillResult,
  abortCanary, sanitizeCanary, findCanarySecrets,
} from '../lib/attendance/portal-real-execution-controller.ts';
import { runSessionLoginVerify, getSessionLoginVerifyContract } from '../lib/attendance/portal-read-only-skill.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const realVault = { available: async () => true, write: async () => ({ ok: true, storage_ref: 'vault://ref/xyz', reason: 'stored' }) };
const initInput = { canary_id: 'cny1', company_id: 'C1', portal_id: 'P1', portal_account_id: 'A1' };

console.log('== 43P-FINAL-1 — Real Execution Controller ==\n');

// [1] Bloqueado: openCanaryBrowser sem readiness NÃO chama transport.
{
  let calls = 0;
  const spy = { open: async () => { calls++; return { ok: true, session_id: 's', session_status: 'RUNNING', region: 'us', expires_at: null, blockers: [], reason: 'ok' }; }, close: async () => ({ closed: true }) };
  let s = applyAuthorization(markAwaitingApproval(initCanary(initInput)), true, []);
  assert('autorizado → ready_for_canary', s.state === 'ready_for_canary');
  s = await openCanaryBrowser(s, false, spy); // readiness false
  assert('readiness off → failed', s.state === 'failed');
  assert('readiness off → transport NÃO chamado', calls === 0);
}

// [2] Authorization negada não vai para ready.
{
  const s = applyAuthorization(markAwaitingApproval(initCanary(initInput)), false, ['approval_missing']);
  assert('negado não fica ready', s.state !== 'ready_for_canary');
  assert('negado mantém blockers', s.blockers.includes('approval_missing'));
}

// [3] Fluxo completo (mock): open → human → capture → verify → skill.
{
  const transport = { open: async () => ({ ok: true, session_id: 'sess_abc', session_status: 'RUNNING', region: 'us', expires_at: new Date(Date.now() + 3600_000).toISOString(), blockers: [], reason: 'ok' }), close: async () => ({ closed: true }) };
  let s = applyAuthorization(markAwaitingApproval(initCanary(initInput)), true, []);
  s = await openCanaryBrowser(s, true, transport);
  assert('open → waiting_human_login', s.state === 'waiting_human_login');
  assert('captura session_id (não-segredo)', s.session_id === 'sess_abc');
  // challenge + resolve
  s = markChallenge(s, 'otp');
  assert('challenge → challenge_required', s.state === 'challenge_required' && s.challenge_kind === 'otp');
  s = resolveChallenge(s);
  assert('resolve → waiting_human_login', s.state === 'waiting_human_login');
  // capture com vault real (mock)
  s = await captureCanarySession(s, { storage_payload: { cookies: [{ name: 'x', value: 'SECRET' }] }, status: 'healthy' }, realVault);
  assert('capture → session_captured', s.state === 'session_captured');
  assert('storage_ref opaca presente', s.storage_ref === 'vault://ref/xyz');
  s = verifyCanarySession(s);
  assert('verify → session_verified', s.state === 'session_verified');
  // skill read-only computada pelo módulo real e anexada via DI
  const skillResult = runSessionLoginVerify({ portal_id: s.portal_id, session_state: 'healthy', has_session_ref: true, authorized: true, observation: { host: 'portal.allianznet.com.br', page_title: 'Área do Corretor', auth_marker_present: true, challenge_detected: null }, contract: getSessionLoginVerifyContract(['portal.allianznet.com.br']) });
  s = attachReadOnlySkillResult(s, skillResult);
  assert('skill autenticado', s.skill_result && s.skill_result.authenticated === true);
  // Segurança: nada de segredo em lugar nenhum do canary.
  assert('canary sem segredo (SECRET não aparece)', !JSON.stringify(s).includes('SECRET'));
  assert('findCanarySecrets vazio', findCanarySecrets(sanitizeCanary(s)).length === 0);
}

// [4] Vault ausente → capture falha fechada.
{
  const transport = { open: async () => ({ ok: true, session_id: 'sess_abc', session_status: 'RUNNING', region: 'us', expires_at: null, blockers: [], reason: 'ok' }), close: async () => ({ closed: true }) };
  let s = applyAuthorization(markAwaitingApproval(initCanary(initInput)), true, []);
  s = await openCanaryBrowser(s, true, transport);
  s = await captureCanarySession(s, { storage_payload: { cookies: [] }, status: 'healthy' }); // sem vault → failClosed
  assert('sem vault → capture failed', s.state === 'failed');
  assert('sem vault → blocker vault_unavailable', s.blockers.includes('vault_unavailable'));
}

// [5] Transição inválida bloqueada.
{
  const s = verifyCanarySession(initCanary(initInput)); // pular direto p/ verify
  assert('verify fora de ordem → failed', s.state === 'failed' && s.blockers.includes('invalid_transition'));
}

// [6] SessionRef expirada não verifica.
{
  const transport = { open: async () => ({ ok: true, session_id: 'x', session_status: 'RUNNING', region: 'us', expires_at: new Date(Date.now() - 1000).toISOString(), blockers: [], reason: 'ok' }), close: async () => ({ closed: true }) };
  let s = applyAuthorization(markAwaitingApproval(initCanary(initInput)), true, []);
  s = await openCanaryBrowser(s, true, transport);
  s = await captureCanarySession(s, { storage_payload: {}, status: 'healthy' }, realVault);
  s = verifyCanarySession(s, Date.now());
  assert('sessão expirada → failed', s.state === 'failed' && s.blockers.includes('expired'));
}

// [7] abort fecha sessão (mock) e marca aborted.
{
  let closed = 0;
  const transport = { open: async () => ({ ok: true, session_id: 'sx', session_status: 'RUNNING', region: 'us', expires_at: null, blockers: [], reason: 'ok' }), close: async () => ({ closed: true }) };
  let s = applyAuthorization(markAwaitingApproval(initCanary(initInput)), true, []);
  s = await openCanaryBrowser(s, true, transport);
  s = await abortCanary(s, async () => { closed++; return { closed: true }; });
  assert('abort → aborted', s.state === 'aborted');
  assert('abort fechou sessão', closed === 1);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
