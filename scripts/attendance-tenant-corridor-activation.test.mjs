#!/usr/bin/env node
/** Tenant Activation 1 — corredores operáveis por tenant (offline, puro). */
import { isCorridorOperable, resolveOperableCorridors, resolveCorridorsWithFallback } from '../lib/attendance/tenant-corridor-activation.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const gAllianz = { id: 'g1', corridor_key: 'allianz_residential_assistance', subcorridor_key: null, scope: 'global', company_id: null, is_active: true };
const gEletric = { id: 'g2', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician', scope: 'global', company_id: null, is_active: true };
const gAuto = { id: 'g3', corridor_key: 'allianz_auto', subcorridor_key: null, scope: 'global', company_id: null, is_active: true };
const tPriv = { id: 't1', corridor_key: 'resulta_custom', subcorridor_key: null, scope: 'tenant', company_id: 'C_RESULTA', is_active: true };
const templates = [gAllianz, gEletric, gAuto, tPriv];

const activations = [
  { company_id: 'C_RESULTA', corridor_template_id: 'g1', status: 'active' },
  { company_id: 'C_RESULTA', corridor_template_id: 'g2', status: 'active' },
  { company_id: 'C_RESULTA', corridor_template_id: 'g3', status: 'paused' },
];

console.log('== Tenant Activation 1 — Tenant Corridor Activation ==\n');

// global só opera se ativado
assert('global ativado opera', isCorridorOperable(gAllianz, 'C_RESULTA', activations) === true);
assert('global eletricista ativado opera', isCorridorOperable(gEletric, 'C_RESULTA', activations) === true);
assert('global pausado NÃO opera', isCorridorOperable(gAuto, 'C_RESULTA', activations) === false);
assert('global sem ativação NÃO opera (outra empresa)', isCorridorOperable(gAllianz, 'C_OUTRA', activations) === false);
// tenant-scoped
assert('tenant-scoped opera p/ dono', isCorridorOperable(tPriv, 'C_RESULTA', activations) === true);
assert('tenant-scoped NÃO vaza p/ outra', isCorridorOperable(tPriv, 'C_OUTRA', activations) === false);

// resolveOperableCorridors
{
  const op = resolveOperableCorridors(templates, 'C_RESULTA', activations).map((t) => t.id).sort();
  assert('Resulta opera g1,g2,t1 (não g3 pausado)', JSON.stringify(op) === JSON.stringify(['g1', 'g2', 't1']));
  const opOutra = resolveOperableCorridors(templates, 'C_OUTRA', activations);
  assert('outra empresa não opera nada (sem ativação)', opOutra.length === 0);
}

// degradação segura: table_missing (pré-migration) vs error (fail-closed) vs ok
{
  const pre = resolveCorridorsWithFallback(templates, 'C_OUTRA', [], 'table_missing');
  assert('table_missing → legacy (globais ativos)', pre.mode === 'legacy_fallback' && pre.corridors.some((c) => c.id === 'g1'));
  const ok = resolveCorridorsWithFallback(templates, 'C_RESULTA', activations, 'ok');
  assert('status ok → activated', ok.mode === 'activated' && ok.corridors.length === 3);
  // FAIL-CLOSED: erro operacional NÃO reabre globais; só tenant-scoped da própria empresa.
  const err = resolveCorridorsWithFallback(templates, 'C_RESULTA', [], 'error');
  assert('error → fail_closed (sem globais)', err.mode === 'fail_closed' && !err.corridors.some((c) => c.scope === 'global'));
  assert('error → mantém tenant-scoped próprio', err.corridors.some((c) => c.id === 't1'));
  const errOutra = resolveCorridorsWithFallback(templates, 'C_OUTRA', [], 'error');
  assert('error p/ empresa sem tenant-scoped → nada', errOutra.corridors.length === 0);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
