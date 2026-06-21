#!/usr/bin/env node
/** TA2-B — visão de seguradoras (puro, offline). */
import { buildInsurerView } from '../lib/admin/tenant-insurers-view.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-B — insurers view ==\n');

const contacts = [
  { insurer_key: 'allianz', display_name: 'Allianz', scope: 'global', is_active: true, source: 'x', glass_service_portal_url: 'https://vidros', notes: null,
    channels: [
      { channel: 'assistencia_whatsapp', kind: 'whatsapp', raw: '1', primary_digits: '5511999', has_menu: false, available: true },
      { channel: 'sinistro_auto', kind: 'phone', raw: '2', primary_digits: '0800111', has_menu: true, available: true },
      { channel: 'vidros', kind: 'phone', raw: null, primary_digits: null, has_menu: false, available: false },
    ] },
  { insurer_key: 'porto', display_name: 'Porto', scope: 'global', is_active: true, source: 'x', glass_service_portal_url: null, notes: null, channels: [] },
];
const corridorItems = [
  { template_id: 't1', title: 'Allianz Res', insurer_key: 'allianz', line_kind: 'res', macro_service: 'assist', subcorridor_key: null, status: 'active', installed: true, requirements: [], next_step: '' },
  { template_id: 't2', title: 'Allianz Elet', insurer_key: 'allianz', line_kind: 'res', macro_service: 'assist', subcorridor_key: 'electrician', status: 'paused', installed: true, requirements: [], next_step: '' },
  { template_id: 't3', title: 'Porto', insurer_key: 'porto', line_kind: 'auto', macro_service: 'sin', subcorridor_key: null, status: 'available', installed: false, requirements: [], next_step: '' },
];

const view = buildInsurerView(contacts, corridorItems);
const byKey = Object.fromEntries(view.map((v) => [v.insurer_key, v]));
assert('2 seguradoras', view.length === 2);
assert('allianz tem 1 corredor ativo (paused não conta)', byKey.allianz.active_corridors === 1 && byKey.allianz.has_active_corridor === true);
assert('porto sem corredor ativo', byKey.porto.has_active_corridor === false);
assert('só canais disponíveis aparecem', byKey.allianz.channels.length === 2);
assert('whatsapp presente com número', byKey.allianz.channels.some((c) => c.kind === 'whatsapp' && c.number === '5511999'));
assert('vidros indisponível filtrado', !byKey.allianz.channels.some((c) => c.label.toLowerCase().includes('vidros')));
assert('portal de vidros preservado', byKey.allianz.glass_service_portal_url === 'https://vidros');
assert('ordenado por nome', view[0].display_name === 'Allianz');

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
