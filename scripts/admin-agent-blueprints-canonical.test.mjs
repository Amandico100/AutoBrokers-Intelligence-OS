#!/usr/bin/env node
/** Tenant Activation 1 — blueprints canônicos + effective config (offline, puro). */
import {
  CANONICAL_BLUEPRINTS, getCanonicalBlueprint, getBlueprintByRole,
  renderTemplate, resolveEffectiveConfig, AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT,
  computeAgentConfigUpdate, resetAgentConfigUpdate, sanitizeAgentConfigForDashboard, TENANT_AGENT_CONFIG_NS,
} from '../lib/admin/agent-blueprints-canonical.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== Tenant Activation 1 — Canonical Blueprints ==\n');

assert('2 blueprints canônicos', CANONICAL_BLUEPRINTS.length === 2);
assert('core por role', getBlueprintByRole('core')?.blueprint_key === 'autobrokers-core-v1');
assert('attendance por role', getBlueprintByRole('attendance')?.blueprint_key === 'even-attendance-v1');
assert('core: marca travada AutoBrokers', AUTOBROKERS_CORE_BLUEPRINT.brand_locked_name === 'AutoBrokers');
assert('core: allow_direct_chat + role core', AUTOBROKERS_CORE_BLUEPRINT.allow_direct_chat === true && AUTOBROKERS_CORE_BLUEPRINT.role === 'core' && AUTOBROKERS_CORE_BLUEPRINT.audience === 'broker_internal');
assert('even: padrão feminino + inativa', EVEN_ATTENDANCE_BLUEPRINT.default_display_name === 'Even' && EVEN_ATTENDANCE_BLUEPRINT.default_active === false && EVEN_ATTENDANCE_BLUEPRINT.audience === 'insured_external');

// render
assert('renderTemplate substitui var', renderTemplate('Olá {{x}}!', { x: 'mundo' }) === 'Olá mundo!');
assert('renderTemplate var ausente vira vazio', renderTemplate('a{{y}}b', {}) === 'ab');

// Effective config — CORE
{
  const eff = resolveEffectiveConfig({ blueprint: AUTOBROKERS_CORE_BLUEPRINT, company_name: 'Resulta Seguros', tenant_variables: { tone: 'objetivo', company_name: 'HACK' } });
  assert('core display = AutoBrokers da {empresa}', eff.display_name === 'AutoBrokers da Resulta Seguros');
  assert('core prompt cita a empresa', eff.system_prompt.includes('Resulta Seguros'));
  assert('company_name NÃO é editável pelo tenant (HACK ignorado)', eff.variables_used.company_name === 'Resulta Seguros');
  assert('core role/audience preservados', eff.role === 'core' && eff.audience === 'broker_internal');
}

// Effective config — EVEN com personalização (Even → Joana, masculino)
{
  const eff = resolveEffectiveConfig({ blueprint: EVEN_ATTENDANCE_BLUEPRINT, company_name: 'Autofleet', tenant_variables: { attendant_name: 'Joana', attendant_gender: 'feminino', tone: 'acolhedor' } });
  assert('even display = nome escolhido', eff.display_name === 'Joana');
  assert('even prompt usa nome/empresa', eff.system_prompt.includes('Joana') && eff.system_prompt.includes('Autofleet'));
  const eff2 = resolveEffectiveConfig({ blueprint: EVEN_ATTENDANCE_BLUEPRINT, company_name: 'ABC', tenant_variables: { attendant_name: 'João', attendant_gender: 'masculino', attendant_pronoun: 'ele' } });
  assert('even masculino aplicado', eff2.display_name === 'João' && eff2.system_prompt.includes('masculino') && eff2.variables_used.attendant_pronoun === 'ele');
}

// Overrides: whitelist aplicada, fora da whitelist rejeitado
{
  const eff = resolveEffectiveConfig({ blueprint: EVEN_ATTENDANCE_BLUEPRINT, company_name: 'X', tenant_overrides: { avatar_url: 'http://a', agent_system_prompt: 'HACK', role: 'core', llm_model: 'gpt-premium' } });
  assert('override seguro aplicado (avatar_url)', eff.applied_overrides.includes('avatar_url'));
  assert('override MATERIALIZADO (avatar_url no objeto)', eff.avatar_url === 'http://a' && eff.overrides_applied.avatar_url === 'http://a');
  assert('override perigoso rejeitado (agent_system_prompt/role/llm_model)', eff.rejected_overrides.includes('agent_system_prompt') && eff.rejected_overrides.includes('role') && eff.rejected_overrides.includes('llm_model'));
  assert('llm_model não vira premium silenciosamente', eff.llm_model === EVEN_ATTENDANCE_BLUEPRINT.default_llm_model);
  // voz materializada + llm_temperature só no core (whitelist)
  const effVoice = resolveEffectiveConfig({ blueprint: EVEN_ATTENDANCE_BLUEPRINT, company_name: 'X', tenant_overrides: { voice: 'feminina-br-1' } });
  assert('voz materializada', effVoice.voice === 'feminina-br-1');
  const effTemp = resolveEffectiveConfig({ blueprint: AUTOBROKERS_CORE_BLUEPRINT, company_name: 'X', tenant_overrides: { llm_temperature: 0.2 } });
  assert('llm_temperature materializado no core', effTemp.llm_temperature === 0.2);
}

assert('blueprint_version presente', getCanonicalBlueprint('autobrokers-core-v1')?.blueprint_version === 'v1');

// [TA2-A] persistência / sanitização da config por tenant
console.log('\n[TA2-A] persistência de config');
{
  // Even: muda nome → coluna name + prompt re-renderizado; preserva context_package existente.
  const existingCp = { some_other_key: { keep: true }, memory: [1, 2] };
  const upd = computeAgentConfigUpdate(EVEN_ATTENDANCE_BLUEPRINT, 'Autofleet', existingCp, { variables: { attendant_name: 'Joana' }, overrides: { avatar_url: 'http://a', llm_temperature: 0.3 } });
  assert('Even: coluna name = Joana', upd.columns.name === 'Joana');
  assert('Even: agent_system_prompt re-renderizado cita Joana', String(upd.columns.agent_system_prompt).includes('Joana'));
  assert('avatar_url vira coluna', upd.columns.avatar_url === 'http://a');
  assert('llm_temperature vira coluna', upd.columns.llm_temperature === 0.3);
  assert('context_package preserva chaves existentes', upd.context_package.some_other_key && Array.isArray(upd.context_package.memory));
  assert('context_package grava namespace tenant', Boolean(upd.context_package[TENANT_AGENT_CONFIG_NS]));
  assert('namespace guarda variável escolhida', upd.context_package[TENANT_AGENT_CONFIG_NS].variables.attendant_name === 'Joana');

  // Core: name NÃO vira coluna (marca travada).
  const updCore = computeAgentConfigUpdate(AUTOBROKERS_CORE_BLUEPRINT, 'Resulta Seguros', {}, { variables: { tone: 'objetivo' } });
  assert('Core: name NÃO é alterado (marca travada)', !('name' in updCore.columns));
  assert('Core: prompt cita a empresa', String(updCore.columns.agent_system_prompt).includes('Resulta Seguros'));

  // sanitize: nunca expõe agent_system_prompt como campo editável
  const sani = sanitizeAgentConfigForDashboard(EVEN_ATTENDANCE_BLUEPRINT, 'Autofleet', upd.context_package);
  assert('sanitize: display_name = Joana', sani.display_name === 'Joana');
  assert('sanitize: NÃO expõe prompt', !JSON.stringify(sani).includes('atendente de assistencia e sinistro'));
  assert('sanitize: lista variáveis editáveis', sani.editable_variables.some((v) => v.key === 'attendant_name' && v.value === 'Joana'));

  // reset: remove o namespace, volta ao padrão
  const rst = resetAgentConfigUpdate(EVEN_ATTENDANCE_BLUEPRINT, 'Autofleet', upd.context_package);
  assert('reset: remove namespace tenant', !(TENANT_AGENT_CONFIG_NS in rst.context_package));
  assert('reset: preserva outras chaves', rst.context_package.some_other_key && Array.isArray(rst.context_package.memory));
  assert('reset: name volta a Even', rst.columns.name === 'Even');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
