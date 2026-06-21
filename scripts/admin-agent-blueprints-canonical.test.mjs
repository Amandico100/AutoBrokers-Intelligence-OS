#!/usr/bin/env node
/** Tenant Activation 1 — blueprints canônicos + effective config (offline, puro). */
import {
  CANONICAL_BLUEPRINTS, getCanonicalBlueprint, getBlueprintByRole,
  renderTemplate, resolveEffectiveConfig, AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT,
  computeAgentConfigUpdate, resetAgentConfigUpdate, sanitizeAgentConfigForDashboard, TENANT_AGENT_CONFIG_NS,
  validateTenantAgentInput, isSafeAvatarUrl, composeSystemPromptWithGuardrails,
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

// [TA2-B] dropdowns, validação e guardrails-after-variables
console.log('\n[TA2-B] validação + dropdowns + guardrails');
{
  // dropdowns: gênero, pronome e tom da Even têm options
  const gender = EVEN_ATTENDANCE_BLUEPRINT.variables.find((v) => v.key === 'attendant_gender');
  assert('gênero é select com 3 opções', gender.input_kind === 'select' && gender.options.length === 3);
  assert('gênero inclui masculino/feminino/neutro', ['feminino', 'masculino', 'neutro'].every((g) => gender.options.some((o) => o.value === g)));
  const pron = EVEN_ATTENDANCE_BLUEPRINT.variables.find((v) => v.key === 'attendant_pronoun');
  assert('pronome é select', pron.input_kind === 'select' && pron.options.some((o) => o.value === 'ele'));
  const coreTone = AUTOBROKERS_CORE_BLUEPRINT.variables.find((v) => v.key === 'tone');
  assert('tom do core é select', coreTone.input_kind === 'select' && coreTone.options.length >= 3);

  // sanitize expõe metadados de UI (input_kind/options) p/ dropdown
  const sani = sanitizeAgentConfigForDashboard(EVEN_ATTENDANCE_BLUEPRINT, 'Resulta', null);
  const sg = sani.editable_variables.find((v) => v.key === 'attendant_gender');
  assert('sanitize entrega options de gênero', sg.input_kind === 'select' && sg.options.length === 3);
  assert('sanitize entrega override-fields com metadados', sani.editable_override_fields.some((f) => f.key === 'voice' && f.input_kind === 'select'));
  assert('voice tem opções de dropdown', sani.editable_override_fields.find((f) => f.key === 'voice').options.length > 0);

  // validação: opção inválida de enum é bloqueada
  const bad = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { variables: { attendant_gender: 'alienígena' } });
  assert('gênero fora da lista é bloqueado', bad.ok === false && bad.errors.some((e) => e.startsWith('attendant_gender')));

  // validação: texto longo bloqueado
  const longText = 'x'.repeat(400);
  const tooLong = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { variables: { opening_message: longText } });
  assert('texto longo é bloqueado', tooLong.ok === false && tooLong.errors.some((e) => e.includes('tamanho_maximo')));

  // validação: template injection bloqueado
  const inj = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { variables: { attendant_name: 'Joana {{company_name}}' } });
  assert('template injection bloqueado', inj.ok === false && inj.errors.some((e) => e.includes('template_injection')));

  // validação: temperatura fora do intervalo
  const temp = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { overrides: { llm_temperature: 5 } });
  assert('temperatura > 1 bloqueada', temp.ok === false && temp.errors.some((e) => e.includes('llm_temperature')));
  const tempOk = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { overrides: { llm_temperature: 0.5 } });
  assert('temperatura 0.5 aceita', tempOk.ok === true && tempOk.clean.overrides.llm_temperature === 0.5);

  // validação: override perigoso (prompt/role) rejeitado
  const danger = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { overrides: { agent_system_prompt: 'HACK', role: 'core' } });
  assert('prompt/role rejeitados na validação', danger.ok === false && danger.errors.some((e) => e.includes('override_nao_permitido')));

  // URL de avatar
  assert('https público é seguro', isSafeAvatarUrl('https://cdn.exemplo.com/a.png') === true);
  assert('http é inseguro', isSafeAvatarUrl('http://cdn.exemplo.com/a.png') === false);
  assert('javascript: é inseguro', isSafeAvatarUrl('javascript:alert(1)') === false);
  assert('localhost é inseguro', isSafeAvatarUrl('https://localhost/a.png') === false);
  assert('IP privado é inseguro', isSafeAvatarUrl('https://192.168.0.1/a.png') === false);
  const badUrl = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { overrides: { avatar_url: 'http://x/a.png' } });
  assert('avatar inseguro bloqueado na validação', badUrl.ok === false && badUrl.errors.some((e) => e.includes('avatar_url')));

  // entrada válida com dropdown passa e limpa
  const good = validateTenantAgentInput(EVEN_ATTENDANCE_BLUEPRINT, { variables: { attendant_name: 'Joana', attendant_gender: 'masculino' }, overrides: { voice: 'masculina-br-natural' } });
  assert('entrada válida passa', good.ok === true && good.clean.variables.attendant_gender === 'masculino' && good.clean.overrides.voice === 'masculina-br-natural');

  // guardrails SEMPRE depois da personalização
  const composed = composeSystemPromptWithGuardrails('TEXTO PERSONALIZADO DA CORRETORA', EVEN_ATTENDANCE_BLUEPRINT.immutable_guardrails);
  assert('guardrails vêm após a personalização', composed.indexOf('TEXTO PERSONALIZADO') < composed.indexOf('REGRAS IMUTAVEIS'));
  assert('prompt efetivo termina com regras prevalecendo', composed.includes('estas regras prevalecem'));
  const effEven = resolveEffectiveConfig({ blueprint: EVEN_ATTENDANCE_BLUEPRINT, company_name: 'Resulta', tenant_variables: { opening_message: 'oi' } });
  assert('system_prompt efetivo tem bloco de regras imutáveis', effEven.system_prompt.includes('REGRAS IMUTAVEIS'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
