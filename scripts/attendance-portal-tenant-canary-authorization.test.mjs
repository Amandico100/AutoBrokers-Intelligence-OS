#!/usr/bin/env node
/** 43P-FINAL-1 — autorização de canary por tenant/approval (offline, puro). */
import { evaluateTenantCanaryAuthorization, deriveCanaryReadinessFlags } from '../lib/attendance/portal-tenant-canary-authorization.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const future = new Date(Date.now() + 3600_000).toISOString();
const past = new Date(Date.now() - 1000).toISOString();
const goodApproval = { company_id: 'C1', portal_id: 'P1', portal_account_id: 'A1', journey: 'login', mode: 'read_only_canary', approved_by: 'admin@x', approved_at: new Date().toISOString(), expires_at: future };
const baseCtx = {
  company_id: 'C1', portal_id: 'P1', portal_account_id: 'A1', journey: 'login',
  is_master: true, operator_company_id: null,
  global_kill_switch: false, global_flag_enabled: true, readiness_can_open: true,
  approval: goodApproval,
};

console.log('== 43P-FINAL-1 — Tenant Canary Authorization ==\n');

assert('tudo ok → autorizado', evaluateTenantCanaryAuthorization(baseCtx).authorized === true);
assert('kill switch vence approval', evaluateTenantCanaryAuthorization({ ...baseCtx, global_kill_switch: true }).blockers.includes('global_kill_switch_active'));
assert('flag global off bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, global_flag_enabled: false }).authorized === false);
assert('readiness off bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, readiness_can_open: false }).blockers.includes('browserbase_not_ready'));
assert('sem approval bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: null }).blockers.includes('approval_missing'));
assert('approval expirada bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, expires_at: past } }).blockers.includes('approval_expired'));
assert('approval sem expiry bloqueia (sem global indefinida)', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, expires_at: null } }).blockers.includes('approval_no_expiry'));
assert('approval revogada bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, revoked: true } }).blockers.includes('approval_revoked'));
assert('approval de outro tenant bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, company_id: 'C2' } }).blockers.includes('approval_company_mismatch'));
assert('approval de outra conta bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, portal_account_id: 'A2' } }).blockers.includes('approval_account_mismatch'));
assert('mode inválido bloqueia', evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, mode: 'business_action' } }).blockers.includes('approval_mode_invalid'));
// Isolamento tenant: operador não-master de outra company não opera C1.
assert('tenant cross-company bloqueado', evaluateTenantCanaryAuthorization({ ...baseCtx, is_master: false, operator_company_id: 'C2' }).blockers.includes('cross_tenant_denied'));
assert('tenant da própria company ok', evaluateTenantCanaryAuthorization({ ...baseCtx, is_master: false, operator_company_id: 'C1' }).authorized === true);
assert('real_action_allowed sempre false', evaluateTenantCanaryAuthorization(baseCtx).real_action_allowed === false);

// [43P-FINAL-2A patch] readiness account-aware: start_allowed + flags granulares.
console.log('\n[patch] canary readiness account-aware');
{
  // flags off (kill switch on + flags off) → start_allowed false
  const off = evaluateTenantCanaryAuthorization({ ...baseCtx, global_kill_switch: true, global_flag_enabled: false });
  assert('flags off → start_allowed false', off.authorized === false);
  const dOff = deriveCanaryReadinessFlags(off.blockers);
  assert('flags off → kill_switch_off false', dOff.kill_switch_off === false);
  assert('flags off → flags_ok false', dOff.flags_ok === false);

  // flags on + sem approval → start_allowed false, approval_valid false, gates ok
  const noAppr = evaluateTenantCanaryAuthorization({ ...baseCtx, approval: null });
  assert('flags on sem approval → start_allowed false', noAppr.authorized === false);
  const dNo = deriveCanaryReadinessFlags(noAppr.blockers);
  assert('sem approval → approval_valid false', dNo.approval_valid === false);
  assert('sem approval → kill_switch_off true', dNo.kill_switch_off === true);
  assert('sem approval → flags_ok true', dNo.flags_ok === true);

  // tudo ok → start_allowed true + todos os flags true
  const ok = evaluateTenantCanaryAuthorization(baseCtx);
  assert('tudo ok → start_allowed true', ok.authorized === true);
  const dOk = deriveCanaryReadinessFlags(ok.blockers);
  assert('tudo ok → approval_valid/flags_ok/kill_switch_off/browserbase_ready true', dOk.approval_valid && dOk.flags_ok && dOk.kill_switch_off && dOk.browserbase_ready);

  // expirada / revogada → approval_valid false
  assert('expirada → approval_valid false', deriveCanaryReadinessFlags(evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, expires_at: past } }).blockers).approval_valid === false);
  assert('revogada → approval_valid false', deriveCanaryReadinessFlags(evaluateTenantCanaryAuthorization({ ...baseCtx, approval: { ...goodApproval, revoked: true } }).blockers).approval_valid === false);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
