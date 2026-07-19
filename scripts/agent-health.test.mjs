#!/usr/bin/env node
/** SPEC-013 FB-2 — divergências/saúde de agentes (puro, offline). */
import { buildAgentDivergences, isHealthy, effectiveCoreModel } from '../lib/admin/agent-health.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 FB-2 — agent health ==\n');

// canônico saudável: 1 core + 1 attendance nomeado Even
const ok = buildAgentDivergences([
  { id: 'c', name: 'AutoBrokers', agent_role: 'core', is_active: true },
  { id: 'e', name: 'Even', agent_role: 'attendance', is_active: false },
]);
assert('saudável sem divergências críticas', isHealthy(ok) && ok.length === 0);

// SPEC-039 F3: o nome do atendimento é de CADA corretora — o sistema NUNCA
// força "Even". Um atendimento com qualquer nome NÃO gera divergência de nome.
const sergio = buildAgentDivergences([
  { id: 'c', name: 'AutoBrokers', agent_role: 'core', is_active: true },
  { id: 'e', name: 'SERGIO', agent_role: 'attendance', is_active: false },
]);
assert('nome do atendimento NÃO é mais normalizado p/ Even', !sergio.some((d) => d.kind === 'attendance_name_not_even'));
assert('atendimento com nome próprio é healthy', isHealthy(sergio) && sergio.length === 0);

// faltando core/attendance
const missing = buildAgentDivergences([{ id: 'e', name: 'Even', agent_role: 'attendance', is_active: false }]);
assert('missing_core detectado + não saudável', missing.some((d) => d.kind === 'missing_core') && !isHealthy(missing));

// duplicata
const dup = buildAgentDivergences([
  { id: 'c1', name: 'AutoBrokers', agent_role: 'core', is_active: true },
  { id: 'c2', name: 'AutoBrokers 2', agent_role: 'core', is_active: true },
  { id: 'e', name: 'Even', agent_role: 'attendance', is_active: false },
]);
assert('duplicate_core detectado + não saudável', dup.some((d) => d.kind === 'duplicate_core') && !isHealthy(dup));

// agente de teste legado → ação archive (e nunca para core/even)
const test = buildAgentDivergences([
  { id: 'c', name: 'AutoBrokers', agent_role: 'core', is_active: true },
  { id: 'e', name: 'Even', agent_role: 'attendance', is_active: false },
  { id: 't', name: 'TESTE Runtime Smith Agent', agent_role: 'subagent', is_active: false },
]);
assert('agente de teste gera legacy_test_agent + ação archive', test.some((d) => d.kind === 'legacy_test_agent' && d.action === 'archive_agent' && d.agent_id === 't'));
assert('teste não derruba saúde canônica', isHealthy(test));

// modelo efetivo do Core
assert('core mini → gpt-4o efetivo', effectiveCoreModel('gpt-4o-mini') === 'gpt-4o');
assert('core já forte mantém', effectiveCoreModel('gpt-4.1') === 'gpt-4.1');
assert('core sem modelo → gpt-4o', effectiveCoreModel(null) === 'gpt-4o');

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
