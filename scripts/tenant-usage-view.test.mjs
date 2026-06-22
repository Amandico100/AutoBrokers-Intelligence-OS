#!/usr/bin/env node
/** TA2-C — agregação de uso/custos (puro, offline). */
import { buildUsageView } from '../lib/admin/tenant-usage-view.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-C — usage view ==\n');

const v = buildUsageView({ balance_brl: 100.5, alert_80: true, alert_100: false, rows: [
  { agent_label: 'AutoBrokers', model_name: 'gpt-4o-mini', cost_brl: 1.20, tokens: 1000 },
  { agent_label: 'AutoBrokers', model_name: 'gpt-4o-mini', cost_brl: 0.80, tokens: 500 },
  { agent_label: 'Even', model_name: 'gpt-4o-mini', cost_brl: 2.00, tokens: 2000 },
  { agent_label: 'Even', model_name: 'gpt-4o', cost_brl: 5.00, tokens: 800 },
] });

assert('saldo preservado', v.balance_brl === 100.5 && v.alert_80 === true && v.alert_100 === false);
assert('total do período somado', v.period_total_brl === 9.0 && v.period_tokens === 4300);
assert('agrupa por agente', v.by_agent.length === 2);
assert('Even é o maior gasto (ordenado)', v.by_agent[0].key === 'Even' && v.by_agent[0].cost_brl === 7.0);
assert('AutoBrokers agregado', v.by_agent.find((g) => g.key === 'AutoBrokers').cost_brl === 2.0 && v.by_agent.find((g) => g.key === 'AutoBrokers').tokens === 1500);
assert('agrupa por modelo', v.by_model.length === 2 && v.by_model.find((g) => g.key === 'gpt-4o-mini').cost_brl === 4.0);
assert('has_data verdadeiro', v.has_data === true);

const empty = buildUsageView({ balance_brl: 0, alert_80: false, alert_100: false, rows: [] });
assert('sem dados: zeros honestos', empty.has_data === false && empty.period_total_brl === 0 && empty.by_agent.length === 0);

// valores inválidos não quebram (NaN ignorado)
const dirty = buildUsageView({ balance_brl: NaN, alert_80: false, alert_100: false, rows: [{ agent_label: 'X', model_name: null, cost_brl: NaN, tokens: NaN }] });
assert('NaN tratado como 0', dirty.period_total_brl === 0 && dirty.period_tokens === 0);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
