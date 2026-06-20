#!/usr/bin/env node
/** 43P-FINAL-1 — skill read-only session_login_verify (offline, puro). */
import { runSessionLoginVerify, getSessionLoginVerifyContract, toSafePageLabel, findSkillOutputSecrets } from '../lib/attendance/portal-read-only-skill.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const contract = getSessionLoginVerifyContract(['portal.allianznet.com.br']);
const okObs = { host: 'portal.allianznet.com.br', page_title: 'Área do Corretor', auth_marker_present: true, challenge_detected: null };

console.log('== 43P-FINAL-1 — Read-Only Skill session_login_verify ==\n');

assert('contract é read_only', contract.mode === 'read_only');
assert('contract proíbe ações de negócio', contract.forbidden_actions.includes('fetch_policy') && contract.forbidden_actions.includes('open_claim'));

// [1] caminho feliz.
{
  const r = runSessionLoginVerify({ portal_id: 'P1', session_state: 'healthy', has_session_ref: true, authorized: true, observation: okObs, contract });
  assert('autenticado ok', r.ok === true && r.authenticated === true);
  assert('safe_page_label preservado', r.safe_page_label === 'Área do Corretor');
  assert('output sem segredo/PII', findSkillOutputSecrets(r).length === 0);
  assert('real_action_allowed false', r.real_action_allowed === false);
}

// [2] sem SessionRef bloqueia.
assert('sem session_ref bloqueia', runSessionLoginVerify({ portal_id: 'P1', session_state: 'healthy', has_session_ref: false, authorized: true, observation: okObs, contract }).blockers.includes('session_ref_missing'));
// [3] sem authorization bloqueia.
assert('sem authorization bloqueia', runSessionLoginVerify({ portal_id: 'P1', session_state: 'healthy', has_session_ref: true, authorized: false, observation: okObs, contract }).blockers.includes('not_authorized'));
// [4] estado não-healthy bloqueia.
assert('expired bloqueia', runSessionLoginVerify({ portal_id: 'P1', session_state: 'expired', has_session_ref: true, authorized: true, observation: okObs, contract }).blockers.includes('session_state_expired'));
// [5] host fora da allowlist bloqueia.
assert('host fora da allowlist bloqueia', runSessionLoginVerify({ portal_id: 'P1', session_state: 'healthy', has_session_ref: true, authorized: true, observation: { ...okObs, host: 'evil.com' }, contract }).blockers.includes('host_not_allowed'));
// [6] challenge bloqueia.
assert('challenge bloqueia', runSessionLoginVerify({ portal_id: 'P1', session_state: 'healthy', has_session_ref: true, authorized: true, observation: { ...okObs, challenge_detected: 'captcha' }, contract }).blockers.includes('challenge_captcha'));

// [7] sanitização de page label (PII / dígitos longos descartados).
assert('título com CPF é descartado', toSafePageLabel('Apólice 123456789 de João') === null);
assert('título com @ (email) descartado', toSafePageLabel('joao@x.com') === null);
assert('título com dígitos longos descartado', toSafePageLabel('Proposta 987654321') === null);
assert('título limpo preservado', toSafePageLabel('Painel do Corretor') === 'Painel do Corretor');

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
