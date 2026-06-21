#!/usr/bin/env node
/** TA2-B — checklist de prontidão (puro, offline). */
import { buildReadiness } from '../lib/admin/tenant-readiness.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-B — readiness ==\n');

// vazio: nada pronto, produção NÃO pronta
const empty = buildReadiness({});
assert('itens gerados', empty.total >= 10);
assert('produção NÃO pronta sem nada', empty.production_ready === false);
assert('dados pendente sem company_name', empty.items.find((i) => i.key === 'dados').status === 'pending');
assert('há itens críticos', empty.items.some((i) => i.critical));

// tudo configurado → produção pronta
const full = buildReadiness({
  company_name: 'Resulta', core_provisioned: true, even_provisioned: true,
  core_personalized: true, even_personalized: true, even_active: true,
  team_count: 3, handoff_defined: true, active_corridors: 2, installed_auxiliaries: 1,
  whatsapp_connected: true, knowledge_configured: true, approvers_defined: true,
});
assert('produção pronta quando críticos ok', full.production_ready === true);
assert('corredor ativo conta', full.items.find((i) => i.key === 'corredor').status === 'ready');
assert('auxiliar instalado vira ready', full.items.find((i) => i.key === 'auxiliar').status === 'ready');

// crítico faltando bloqueia produção (even inativa)
const noEven = buildReadiness({ company_name: 'X', core_provisioned: true, even_provisioned: true, core_personalized: true, even_personalized: true, even_active: false, team_count: 1, handoff_defined: true, active_corridors: 1, whatsapp_connected: true });
assert('even inativa bloqueia produção', noEven.production_ready === false);
assert('even_ativa pendente', noEven.items.find((i) => i.key === 'even_ativa').status === 'pending');

// whatsapp desconectado bloqueia produção
const noWa = buildReadiness({ company_name: 'X', core_provisioned: true, even_provisioned: true, core_personalized: true, even_personalized: true, even_active: true, team_count: 1, handoff_defined: true, active_corridors: 1, whatsapp_connected: false });
assert('whatsapp desconectado bloqueia produção', noWa.production_ready === false);

// auxiliar sem instalação = opcional (not_applicable), não bloqueia
const aux0 = buildReadiness({ company_name: 'X', core_provisioned: true, even_provisioned: true, core_personalized: true, even_personalized: true, even_active: true, team_count: 1, handoff_defined: true, active_corridors: 1, whatsapp_connected: true, installed_auxiliaries: 0 });
assert('auxiliar 0 = opcional', aux0.items.find((i) => i.key === 'auxiliar').status === 'not_applicable');
assert('produção pronta mesmo sem auxiliar', aux0.production_ready === true);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
