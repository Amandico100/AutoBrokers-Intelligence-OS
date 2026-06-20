#!/usr/bin/env node
/**
 * 43P4.2A / 43P4.2A.1 — Portal Admin Company Scope + P1 enumeration (offline, puro).
 *   node scripts/attendance-portal-company-scope.test.mjs
 *
 * Escopo: tenant travado ignora override; master escolhe tenant válido; inválido
 * NÃO vira escopo; não-master não troca tenant; piloto single-company; master sem
 * escopo → company_scope_required.
 * P1: master enumera 'all'; tenant 'own'; sem escopo 'none'.
 */
import { resolvePortalCompanyScope, resolveCompanyListingMode } from '../lib/attendance/portal-company-scope.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond) { if (cond) { pass++; console.log(`  ✓ ${name}`); } else { fail++; failures.push(name); console.log(`  ✗ ${name}`); } }

const base = { is_master: false, session_company: null, users_v2_company: null, requested_company: null, requested_company_exists: false, single_company_id: null };

console.log('== 43P4.2A.1 — Portal Company Scope + P1 ==\n');

// [1] Sessão com company (tenant travado) ignora override.
{
  const r = resolvePortalCompanyScope({ ...base, is_master: true, session_company: 'C1', requested_company: 'C2', requested_company_exists: true });
  assert('tenant travado usa sessão', r.companyId === 'C1' && r.companyId !== 'C2');
  assert('tenant travado não é master', r.isMaster === false);
  assert('tenant travado não exige escopo', r.company_scope_required === false);
}

// [2] Master escolhe tenant via company válido.
{
  const r = resolvePortalCompanyScope({ ...base, is_master: true, requested_company: 'C9', requested_company_exists: true });
  assert('master usa company solicitada válida', r.companyId === 'C9');
  assert('master flag isMaster', r.isMaster === true);
  assert('master com escopo não exige seleção', r.company_scope_required === false);
}

// [3] Company solicitada inválida NÃO vira escopo.
{
  const r = resolvePortalCompanyScope({ ...base, is_master: true, requested_company: 'C-FAKE', requested_company_exists: false });
  assert('company inválida não é usada', r.companyId === null);
  assert('master sem escopo → company_scope_required', r.company_scope_required === true);
}

// [4] NÃO-master NUNCA escolhe tenant via header/cookie.
{
  const r = resolvePortalCompanyScope({ ...base, is_master: false, requested_company: 'C2', requested_company_exists: true });
  assert('não-master ignora override', r.companyId === null);
  assert('não-master não exige escopo', r.company_scope_required === false);
}

// [5] users_v2 resolve; override do master tem precedência.
{
  assert('users_v2 resolve company', resolvePortalCompanyScope({ ...base, is_master: true, users_v2_company: 'CU' }).companyId === 'CU');
  assert('override > users_v2', resolvePortalCompanyScope({ ...base, is_master: true, users_v2_company: 'CU', requested_company: 'C9', requested_company_exists: true }).companyId === 'C9');
}

// [6] Piloto single-company resolve (master e não-master).
{
  assert('single company (master) resolve', resolvePortalCompanyScope({ ...base, is_master: true, single_company_id: 'CSOLO' }).companyId === 'CSOLO');
  assert('single company (não-master) resolve', resolvePortalCompanyScope({ ...base, is_master: false, single_company_id: 'CSOLO' }).companyId === 'CSOLO');
}

// [7] Master multi-tenant sem escolha → exige seleção.
{
  const r = resolvePortalCompanyScope({ ...base, is_master: true });
  assert('master sem nada → company_scope_required', r.company_scope_required === true && r.companyId === null);
}

// [8] P1 — modo de enumeração de companies.
{
  assert('master → enumera all', resolveCompanyListingMode({ is_master: true, company_id: null }) === 'all');
  assert('tenant com company → own', resolveCompanyListingMode({ is_master: false, company_id: 'C1' }) === 'own');
  assert('sem escopo → none', resolveCompanyListingMode({ is_master: false, company_id: null }) === 'none');
  // Resulta vê só Resulta, nunca Autofleet:
  assert('tenant Resulta nunca enumera global', resolveCompanyListingMode({ is_master: false, company_id: 'RESULTA' }) !== 'all');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
