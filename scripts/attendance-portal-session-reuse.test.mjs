#!/usr/bin/env node
/** 43P-FINAL-2A — reuso de SessionRef após canary encerrado (offline, DI, sem rede). */
import { reuseSessionRefForReadOnly, findReuseSecrets } from '../lib/attendance/portal-session-reuse.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const healthy = { storage_ref: 'vault://ref/abc', status: 'healthy', expires_at: new Date(Date.now() + 3600_000).toISOString(), portal_id: 'P1', portal_account_id: 'A1' };
const okAuthz = { authorized: true, blockers: [] };
const SECRET = { cookies: [{ name: 'x', value: 'SUPER-SECRET' }], origins: [] };

// deps padrão: vault retorna o segredo; restore observa autenticado; skill ok.
const goodDeps = {
  vaultRead: async () => ({ ok: true, secret_payload: SECRET, reason: 'read' }),
  restoreAndObserve: async (payload) => {
    // o segredo chega aqui (em memória) — prova do fluxo
    if (!payload) return { ok: false, observation: null, reason: 'no_payload' };
    return { ok: true, observation: { host: 'portal.allianznet.com.br', safe_page_label: 'Área do Corretor', auth_marker_present: true, challenge_detected: null }, reason: 'restored' };
  },
  runSkill: (obs) => ({ ok: true, authenticated: Boolean(obs?.auth_marker_present), safe_page_label: obs?.safe_page_label ?? null, session_state: 'healthy', blockers: [], real_action_allowed: false }),
};

console.log('== 43P-FINAL-2A — SessionRef Reuse ==\n');

// [1] Reuso feliz (independe do canary original).
{
  let payloadSeen = false;
  const deps = { ...goodDeps, restoreAndObserve: async (p) => { payloadSeen = Boolean(p); return goodDeps.restoreAndObserve(p); } };
  const r = await reuseSessionRefForReadOnly(healthy, okAuthz, deps);
  assert('reuso ok', r.ok === true && r.reused === true);
  assert('segredo transitou para o restore (memória)', payloadSeen === true);
  assert('skill autenticado', r.skill_result?.authenticated === true);
  assert('resultado SEM segredo (SUPER-SECRET ausente)', !JSON.stringify(r).includes('SUPER-SECRET'));
  assert('findReuseSecrets vazio', findReuseSecrets(r).length === 0);
  assert('real_action_allowed false', r.real_action_allowed === false);
}

// [2] Não autorizado bloqueia.
{
  const r = await reuseSessionRefForReadOnly(healthy, { authorized: false, blockers: ['approval_missing'] }, goodDeps);
  assert('não autorizado → bloqueado', r.ok === false && r.blockers.includes('approval_missing'));
}

// [3] SessionRef revogada não reutiliza.
{
  const r = await reuseSessionRefForReadOnly({ ...healthy, status: 'revoked' }, okAuthz, goodDeps);
  assert('revogada → bloqueada', r.ok === false && r.reason === 'session_revoked');
}

// [4] SessionRef expirada exige re-login.
{
  const r = await reuseSessionRefForReadOnly({ ...healthy, expires_at: new Date(Date.now() - 1000).toISOString() }, okAuthz, goodDeps);
  assert('expirada → bloqueada', r.ok === false && r.reason === 'session_expired');
}

// [5] reauth_required bloqueia.
{
  const r = await reuseSessionRefForReadOnly({ ...healthy, status: 'reauth_required' }, okAuthz, goodDeps);
  assert('reauth_required → bloqueada', r.ok === false && r.reason === 'reauth_required');
}

// [6] Vault read falha → bloqueado (fail closed).
{
  const deps = { ...goodDeps, vaultRead: async () => ({ ok: false, secret_payload: null, reason: 'vault_unavailable' }) };
  const r = await reuseSessionRefForReadOnly(healthy, okAuthz, deps);
  assert('vault read falha → bloqueado', r.ok === false && r.blockers.includes('vault_unavailable'));
}

// [7] storage_ref ausente bloqueia.
{
  const r = await reuseSessionRefForReadOnly({ ...healthy, storage_ref: null }, okAuthz, goodDeps);
  assert('sem storage_ref → bloqueado', r.ok === false && r.reason === 'storage_ref_missing');
}

// [8] Challenge no restore → reused mas challenge.
{
  const deps = { ...goodDeps, restoreAndObserve: async () => ({ ok: true, observation: { host: 'portal.x', safe_page_label: null, auth_marker_present: false, challenge_detected: 'captcha' }, reason: 'restored' }) };
  const r = await reuseSessionRefForReadOnly(healthy, okAuthz, deps);
  assert('challenge → não ok, reused true', r.ok === false && r.reused === true && r.session_state === 'challenge_required');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
