#!/usr/bin/env node
/**
 * 43P4.2A — Portal Admin Company Scope (offline, puro).
 *   node scripts/attendance-portal-company-scope.test.mjs
 *
 * Garante: tenant travado na sessão ignora override; master admin escolhe tenant
 * via company válido; company inválido NÃO vira escopo; usuário comum não escolhe
 * tenant; piloto single-company resolve; admin sem escopo → company_scope_required.
 */
import { resolvePortalCompanyScope } from '../lib/attendance/portal-company-scope.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond) { if (cond) { pass++; console.log(`  ✓ ${name}`); } else { fail++; failures.push(name); console.log(`  ✗ ${name}`); } }

const base = { is_admin: false, session_company: null, users_v2_company: null, requested_company: null, requested_company_exists: false, single_company_id: null };

console.log('== 43P4.2A — Portal Company Scope ==\n');

// [1] Sessão com company (tenant travado) ignora override.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true, session_company: 'C1', requested_company: 'C2', requested_company_exists: true });
  assert('tenant travado usa sessão', r.companyId === 'C1');
  assert('tenant travado ignora override', r.companyId !== 'C2');
  assert('tenant travado não é master', r.isMaster === false);
  assert('tenant travado não exige escopo', r.company_scope_required === false);
}

// [2] Master admin escolhe tenant via company válido.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true, requested_company: 'C9', requested_company_exists: true });
  assert('master usa company solicitada válida', r.companyId === 'C9');
  assert('master flag isMaster', r.isMaster === true);
  assert('master com escopo não exige seleção', r.company_scope_required === false);
}

// [3] Company solicitada inválida NÃO vira escopo.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true, requested_company: 'C-FAKE', requested_company_exists: false });
  assert('company inválida não é usada', r.companyId === null);
  assert('admin sem escopo → company_scope_required', r.company_scope_required === true);
}

// [4] Usuário comum NUNCA escolhe tenant via header.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: false, requested_company: 'C2', requested_company_exists: true });
  assert('usuário comum ignora override', r.companyId === null);
  assert('usuário comum não exige escopo admin', r.company_scope_required === false);
}

// [5] users_v2 resolve quando não há sessão/override.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true, users_v2_company: 'CU' });
  assert('users_v2 resolve company', r.companyId === 'CU');
}

// [6] Override do master tem precedência sobre users_v2.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true, users_v2_company: 'CU', requested_company: 'C9', requested_company_exists: true });
  assert('override > users_v2', r.companyId === 'C9');
}

// [7] Piloto single-company resolve.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true, single_company_id: 'CSOLO' });
  assert('single company (piloto) resolve', r.companyId === 'CSOLO');
  const ru = resolvePortalCompanyScope({ ...base, is_admin: false, single_company_id: 'CSOLO' });
  assert('single company também p/ usuário comum', ru.companyId === 'CSOLO');
}

// [8] Admin multi-tenant sem escolha → exige seleção.
{
  const r = resolvePortalCompanyScope({ ...base, is_admin: true });
  assert('admin sem nada → company_scope_required', r.company_scope_required === true && r.companyId === null);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
