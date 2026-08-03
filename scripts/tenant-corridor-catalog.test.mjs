#!/usr/bin/env node
/** SPEC-063 — catálogo de corredores (puro, offline).
 *
 * O catálogo NÃO é mais `corridor_templates`: ele vem do código que executa
 * (`corridor_playbooks.py`, servido por GET /api/corridors/catalog). Este teste
 * prova só a composição pura: catálogo do código + estado da corretora → cards.
 */
import {
  buildCorridorCatalog,
  corridorIdForTemplateKey,
  foldActivationStatus,
  nextCorridorStatus,
} from '../lib/admin/tenant-corridor-catalog.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-063 — corridor catalog ==\n');

// Dois corredores como o backend os entrega (forma, não conteúdo: a lista real
// vive no Python e nunca é copiada para cá).
const corredores = [
  {
    corridor_id: 'seguradora-a-residencial-whatsapp', playbook_ref: 'seguradora-a-residencial-whatsapp@v1',
    insurer_key: 'seguradora_a', insurer_label: 'Seguradora A', line_kind: 'residencial', line_label: 'Residencial',
    channel: 'whatsapp', channel_label: 'WhatsApp', title: 'Seguradora A · Residencial',
    subservices: [{ key: 's1', label: 'Trabalho 1', outcome: 'abre', referral_kind: null, menu_mapeado: true }],
    outcome_summary: 'abre', handoff_sinistro: true, menu_mapeado: true,
  },
  {
    corridor_id: 'seguradora-b-auto-whatsapp', playbook_ref: 'seguradora-b-auto-whatsapp@v1',
    insurer_key: 'seguradora_b', insurer_label: 'Seguradora B', line_kind: 'auto', line_label: 'Auto',
    channel: 'whatsapp', channel_label: 'WhatsApp', title: 'Seguradora B · Auto',
    subservices: [
      { key: 's2', label: 'Trabalho 2', outcome: 'abre', referral_kind: null, menu_mapeado: true },
      { key: 's3', label: 'Trabalho 3', outcome: 'encaminha', referral_kind: 'formulario', menu_mapeado: true },
    ],
    outcome_summary: 'misto', handoff_sinistro: true, menu_mapeado: true,
  },
];

const cat = buildCorridorCatalog(corredores, { 'seguradora-a-residencial-whatsapp': 'active' });
assert('um card por corredor do código', cat.length === 2);
const byId = Object.fromEntries(cat.map((c) => [c.corridor_id, c]));
assert('ativado aparece ativo', byId['seguradora-a-residencial-whatsapp'].status === 'active');
assert('ativado conta como instalado', byId['seguradora-a-residencial-whatsapp'].installed === true);
assert('nunca ativado aparece DISPONÍVEL (não some)', byId['seguradora-b-auto-whatsapp'].status === 'available');
assert('nunca ativado não conta como instalado', byId['seguradora-b-auto-whatsapp'].installed === false);
assert('o desfecho por subserviço sobrevive à montagem',
  byId['seguradora-b-auto-whatsapp'].subservices.filter((s) => s.outcome === 'encaminha').length === 1);
assert('o card não ganha subserviço que o código não declarou',
  byId['seguradora-a-residencial-whatsapp'].subservices.length === 1);

// pausado
const pausado = buildCorridorCatalog(corredores, { 'seguradora-b-auto-whatsapp': 'paused' });
assert('pausado aparece pausado', pausado[1].status === 'paused' && pausado[1].installed === true);

// N linhas de ativação, uma decisão só
assert('ativo vence pausado', foldActivationStatus(['paused', 'active']) === 'active');
assert('só pausado → pausado', foldActivationStatus(['paused', null]) === 'paused');
assert('sem ativação → null', foldActivationStatus([null, undefined, '']) === null);

// ponte de identificador legado
assert('chave legada aponta para o corredor do código',
  corridorIdForTemplateKey('allianz_residential_assistance') === 'allianz-residencial-whatsapp');
assert('chave desconhecida passa intacta',
  corridorIdForTemplateKey('corredor-qualquer') === 'corredor-qualquer');

// próximos status
assert('activate→active', nextCorridorStatus('activate') === 'active');
assert('resume→active', nextCorridorStatus('resume') === 'active');
assert('pause→paused', nextCorridorStatus('pause') === 'paused');
assert('ação inválida→null', nextCorridorStatus('explode') === null);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
