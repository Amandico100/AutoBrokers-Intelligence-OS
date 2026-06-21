#!/usr/bin/env node
/** TA2-B — catálogo de corredores (puro, offline). */
import { buildCorridorCatalog, nextCorridorStatus, corridorRequirements } from '../lib/admin/tenant-corridor-catalog.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-B — corridor catalog ==\n');

const templates = [
  { id: 't1', scope: 'global', corridor_key: 'allianz_residential_assistance', subcorridor_key: null, display_name: 'Allianz Residencial — Assistência', insurer_key: 'allianz', line_kind: 'residencial', macro_service: 'assistencia', service_type: 'whatsapp', readiness: null, requires_action_engine: false, requires_dispatch_packet: false, allowed_channels: ['whatsapp'], is_active: true },
  { id: 't2', scope: 'global', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician', display_name: 'Allianz Residencial — Eletricista', insurer_key: 'allianz', line_kind: 'residencial', macro_service: 'assistencia', service_type: 'portal', readiness: 'needs_portal', requires_action_engine: true, requires_dispatch_packet: true, allowed_channels: ['portal'], is_active: true },
  { id: 't3', scope: 'global', corridor_key: 'porto_auto', subcorridor_key: null, display_name: 'Porto Auto', insurer_key: 'porto', line_kind: 'auto', macro_service: 'sinistro', service_type: null, readiness: null, requires_action_engine: false, requires_dispatch_packet: false, allowed_channels: [], is_active: true },
  { id: 't4', scope: 'global', corridor_key: 'inactive', subcorridor_key: null, display_name: 'Inativo', insurer_key: 'x', line_kind: null, macro_service: null, service_type: null, readiness: null, requires_action_engine: false, requires_dispatch_packet: false, allowed_channels: [], is_active: false },
];
const acts = [{ corridor_template_id: 't1', status: 'active' }, { corridor_template_id: 't2', status: 'paused' }];

const cat = buildCorridorCatalog(templates, acts);
assert('template inativo é filtrado', cat.length === 3);
const byId = Object.fromEntries(cat.map((c) => [c.template_id, c]));
assert('t1 ativo', byId.t1.status === 'active' && byId.t1.installed === true);
assert('t2 pausado', byId.t2.status === 'paused' && byId.t2.installed === true);
assert('t3 disponível (não instalado)', byId.t3.status === 'available' && byId.t3.installed === false);
assert('t1 requer canal WhatsApp', byId.t1.requirements.includes('Canal WhatsApp conectado'));
assert('t2 requer portal + aprovação', byId.t2.requirements.includes('Portal da seguradora conectado') && byId.t2.requirements.includes('Ação externa requer aprovação'));
assert('ordenado por título', cat[0].title.localeCompare(cat[1].title) <= 0);

// próximos status
assert('activate→active', nextCorridorStatus('activate') === 'active');
assert('resume→active', nextCorridorStatus('resume') === 'active');
assert('pause→paused', nextCorridorStatus('pause') === 'paused');
assert('ação inválida→null', nextCorridorStatus('explode') === null);

// requisitos dedupe
const reqs = corridorRequirements({ allowed_channels: ['portal'], service_type: 'portal', requires_action_engine: false, readiness: 'needs_portal' });
assert('requisitos sem duplicar portal', reqs.filter((r) => r === 'Portal da seguradora conectado').length === 1);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
