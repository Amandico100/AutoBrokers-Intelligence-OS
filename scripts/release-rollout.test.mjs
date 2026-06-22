#!/usr/bin/env node
/** SPEC-013 P4 — rollout: materialização preserva personalização local (puro, offline). */
import { EVEN_ATTENDANCE_BLUEPRINT, computeAgentConfigUpdate } from '../lib/admin/agent-blueprints-canonical.ts';
import { buildArtifactFromSourceAgent, scanForSecrets } from '../lib/admin/blueprint-release.ts';
import { artifactToBlueprint, extractSavedTenantInput, canRolloutTransition, ROLLOUT_STATES, captureAgentSnapshot } from '../lib/admin/release-rollout.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 P4 — release rollout ==\n');

// artefato de release com template EDITADO no Studio
const artifact = buildArtifactFromSourceAgent(EVEN_ATTENDANCE_BLUEPRINT, {
  agent_system_prompt: 'RELEASE TEMPLATE v2: {{attendant_name}} da {{company_name}} atende.',
});
const bp = artifactToBlueprint(artifact, '1.1.0');
assert('artifactToBlueprint mantém role/audience', bp.role === 'attendance' && bp.audience === 'insured_external');
assert('artifactToBlueprint usa template da release', bp.system_prompt_template.includes('RELEASE TEMPLATE v2'));
assert('blueprint_version vem da release', bp.blueprint_version === '1.1.0');

// instância da corretora com personalização local (Joana) + outras chaves de context_package
const tenantCp = { tenant_agent_config: { variables: { attendant_name: 'Joana' }, overrides: {} }, memory: [1, 2], doc_refs: ['x'] };
const input = extractSavedTenantInput(tenantCp);
assert('extrai personalização local salva', input.variables.attendant_name === 'Joana');

const upd = computeAgentConfigUpdate(bp, 'Resulta Seguros', tenantCp, input);
assert('rollout: nome local preservado (Joana)', upd.columns.name === 'Joana');
assert('rollout: prompt usa template da RELEASE', String(upd.columns.agent_system_prompt).includes('RELEASE TEMPLATE v2'));
assert('rollout: prompt renderiza var local + empresa', String(upd.columns.agent_system_prompt).includes('Joana') && String(upd.columns.agent_system_prompt).includes('Resulta Seguros'));
assert('rollout: guardrails seguem presentes', String(upd.columns.agent_system_prompt).includes('REGRAS IMUTAVEIS'));
assert('rollout: context_package preserva outras chaves', Array.isArray(upd.context_package.memory) && Array.isArray(upd.context_package.doc_refs));
assert('rollout: tenant_agent_config preservado', upd.context_package.tenant_agent_config.variables.attendant_name === 'Joana');

// estados/transições
assert('estados definidos', ROLLOUT_STATES.length === 6);
assert('pending→active ok', canRolloutTransition('pending', 'active'));
assert('active→rolled_back ok', canRolloutTransition('active', 'rolled_back'));
assert('rolled_back→qualquer bloqueado', !canRolloutTransition('rolled_back', 'active'));
assert('active→pending bloqueado', !canRolloutTransition('active', 'pending'));

// [hardening] snapshot pré-rollout (rollback seguro inclusive no 1º)
const snap = captureAgentSnapshot({ name: 'Joana', avatar_url: null, llm_temperature: '0.70', agent_system_prompt: 'PROMPT ATUAL', context_package: { tenant_agent_config: { variables: { attendant_name: 'Joana' } }, memory: [1] }, blueprint_version: 'even-attendance-v1', extra: 'ignorado' });
assert('snapshot captura campos do agente', snap.name === 'Joana' && snap.agent_system_prompt === 'PROMPT ATUAL' && snap.blueprint_version === 'even-attendance-v1');
assert('snapshot normaliza llm_temperature', snap.llm_temperature === 0.7);
assert('snapshot preserva context_package', snap.context_package.tenant_agent_config.variables.attendant_name === 'Joana');
assert('snapshot ignora campos extras', !('extra' in snap));
assert('snapshot limpo passa no secret scan', scanForSecrets(snap).length === 0);
assert('snapshot com segredo é detectado', scanForSecrets(captureAgentSnapshot({ context_package: { access_token: 'zzz' } })).some((s) => s.includes('forbidden_secret_field')));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
