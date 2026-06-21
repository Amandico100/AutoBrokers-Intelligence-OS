#!/usr/bin/env node
/** Tenant Activation 2 (0.5) — atribuição de custo (offline, puro). */
import { buildUsageAttribution, isAttributable, attributionDimensions } from '../lib/admin/finops-usage-context.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== Tenant Activation 2 — FinOps attribution ==\n');

{
  const a = buildUsageAttribution({ company_id: 'C1', agent_id: 'A1', corridor_run_id: 'R1', tool_name: 'policy_lookup', model: 'gpt-4o-mini' });
  assert('company+agent obrigatórios presentes', a.company_id === 'C1' && a.agent_id === 'A1');
  assert('corridor_run_id propagado', a.corridor_run_id === 'R1');
  assert('campos ausentes viram null', a.auxiliary_run_id === null && a.attendance_case_id === null);
  assert('é atribuível (tem company)', isAttributable(a) === true);
  const dims = attributionDimensions(a);
  assert('dimensões: company+agent+corridor', dims.includes('company') && dims.includes('agent') && dims.includes('corridor') && !dims.includes('auxiliary'));
}
{
  const aux = buildUsageAttribution({ company_id: 'C1', agent_id: 'A2', auxiliary_run_id: 'AUX1' });
  assert('auxiliar → dimensão auxiliary', attributionDimensions(aux).includes('auxiliary'));
}
{
  const noCompany = buildUsageAttribution({ company_id: '' });
  assert('sem company → não atribuível', isAttributable(noCompany) === false);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
