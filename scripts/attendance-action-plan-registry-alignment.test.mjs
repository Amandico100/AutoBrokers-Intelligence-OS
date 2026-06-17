#!/usr/bin/env node
/**
 * 42X3.1 — Registry-aware Action Plan ↔ Execution ↔ Outbox alignment (offline).
 *
 *   node scripts/attendance-action-plan-registry-alignment.test.mjs
 *
 * Garante: sem config → manual; config zapi/evolution/meta → action plan usa o
 * provider; subcorredor vence; inativa ignorada; execution usa o provider do
 * plano; outbox reusa o mesmo config_id; sem mismatch; send_allowed=false; sem
 * destino cru; payload provider-specific dry_run.
 */
import {
  evaluateChannelCandidates,
  buildExternalActionPlan,
  startExecutionSession,
  buildOutboxEntry,
} from '../lib/attendance/action-engine.ts';
import {
  buildInsurerChannelConfig,
  resolveActiveInsurerChannelConfig,
  buildProviderPayload,
  getInsurerMessagingProvider,
} from '../lib/attendance/insurer-channel-registry.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const caseRow = {
  id: 'c1', insurer_key: 'allianz', selected_corridor_key: 'allianz_residential_assistance', selected_subcorridor_key: 'electrician', risk_level: 'low',
  policy_snapshot: { masked_policy_number: '****99', insurer_key: 'allianz' },
  metadata: { coverage_readiness: { state: 'human_approved', human_required: false }, dispatch_readiness: { packet_state: 'ready_for_human_approval', dispatch_allowed: true } },
};
const filled = { affected_area: 'cozinha', electrical_issue_type: 'sem energia' };

function toLite(cfg) {
  return {
    config_id: cfg.config_id, provider_key: cfg.provider_key,
    provider_label: getInsurerMessagingProvider(cfg.provider_key)?.label ?? cfg.provider_key,
    channel: cfg.channel, destination_ref_masked: cfg.destination_ref_masked,
    homologation_status: cfg.homologation_status, provider_payload: null,
  };
}
function planWith(lite) {
  const avail = lite?.channel === 'insurer_whatsapp' ? { insurer_whatsapp: true, human_destination: true } : { human_destination: true };
  const channels = evaluateChannelCandidates(avail);
  return buildExternalActionPlan({ caseRow, dispatchPacket: { id: 'dp1', metadata: { packet_state: 'ready_for_human_approval' } }, filledSlots: filled, channels, activeChannelConfig: lite ?? null });
}
function cfg(provider, over = {}) {
  return buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician', provider_key: provider, destination_ref: '5544999998888', ...over });
}

console.log('== 42X3.1 — Action Plan / Execution / Outbox alignment ==');

// [1] Sem config → manual.
console.log('\n[1] sem config → manual');
{
  const plan = planWith(null);
  assert('selected_channel human_broker_manual', plan.selected_channel === 'human_broker_manual', plan.selected_channel);
  assert('channel_config_source fallback_manual', plan.channel_config_source === 'fallback_manual', plan.channel_config_source);
  assert('selected_provider_key null', plan.selected_provider_key === null);
  assert('status ready_for_human_approval', plan.status === 'ready_for_human_approval', plan.status);
}

// [2] zapi → insurer_whatsapp + provider zapi.
console.log('\n[2] zapi');
{
  const c = cfg('zapi');
  const plan = planWith(toLite(c));
  assert('selected_channel insurer_whatsapp', plan.selected_channel === 'insurer_whatsapp', plan.selected_channel);
  assert('selected_provider_key zapi', plan.selected_provider_key === 'zapi');
  assert('selected_config_id casa', plan.selected_config_id === c.config_id);
  assert('selected_destination ****8888', plan.selected_destination_ref_masked === '****8888', plan.selected_destination_ref_masked);
  assert('channel_config_source registry', plan.channel_config_source === 'registry');
  assert('candidate insurer_whatsapp enriquecido', plan.channel_candidates.find((ch) => ch.channel === 'insurer_whatsapp')?.provider_key === 'zapi');
  assert('sem destino cru no plano', !JSON.stringify(plan).includes('5544999998888'));
}

// [3] evolution_go / [4] meta_cloud.
console.log('\n[3/4] evolution_go / meta_cloud');
{
  const ev = planWith(toLite(cfg('evolution_go')));
  assert('evolution_go provider', ev.selected_provider_key === 'evolution_go' && ev.selected_channel === 'insurer_whatsapp');
  const meta = planWith(toLite(cfg('meta_cloud')));
  assert('meta_cloud provider', meta.selected_provider_key === 'meta_cloud' && meta.selected_channel === 'insurer_whatsapp');
}

// [5] subcorredor vence; [6] inativa ignorada.
console.log('\n[5/6] resolução');
{
  const corridorCfg = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', provider_key: 'zapi', destination_ref: '111' });
  const subCfg = cfg('meta_cloud');
  const best = resolveActiveInsurerChannelConfig([corridorCfg, subCfg], { insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician' });
  const plan = planWith(toLite(best));
  assert('subcorredor (meta_cloud) vence', plan.selected_provider_key === 'meta_cloud', plan.selected_provider_key);

  const inactive = resolveActiveInsurerChannelConfig([cfg('zapi', { is_active: false })], { insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician' });
  const plan2 = planWith(inactive ? toLite(inactive) : null);
  assert('config inativa → manual', plan2.selected_channel === 'human_broker_manual');
}

// [7] Execution usa o provider do plano.
console.log('\n[7] execution alinhada');
{
  const zapiPlan = planWith(toLite(cfg('zapi')));
  const exec = startExecutionSession(zapiPlan);
  assert('exec não-erro', !('error' in exec));
  assert('exec channel insurer_whatsapp', exec.channel === 'insurer_whatsapp');
  assert('exec adapter zapi_sandbox', exec.adapter === 'zapi_sandbox', exec.adapter);

  const manualExec = startExecutionSession(planWith(null));
  assert('exec manual adapter human_manual_sandbox', manualExec.adapter === 'human_manual_sandbox', manualExec.adapter);

  const metaExec = startExecutionSession(planWith(toLite(cfg('meta_cloud'))));
  assert('exec meta adapter meta_cloud_sandbox', metaExec.adapter === 'meta_cloud_sandbox', metaExec.adapter);
}

// [8] Outbox reusa o mesmo config_id do plano; sem mismatch.
console.log('\n[8] outbox reuse');
{
  const c = cfg('zapi');
  const plan = planWith(toLite(c));
  // payload como a rota faz após o plano:
  plan.selected_provider_payload = buildProviderPayload(plan.selected_provider_key, { destination_ref_masked: plan.selected_destination_ref_masked, message_text: plan.message_drafts[0]?.text });
  const outboxChannel = plan.selected_channel === 'insurer_whatsapp' ? 'insurer_whatsapp' : 'human_broker_manual';
  const entry = buildOutboxEntry({
    case_id: 'c1', dispatch_packet_id: 'dp1', plan,
    channel: outboxChannel, provider: plan.selected_provider_key, destination_ref_masked: plan.selected_destination_ref_masked,
    provider_payload: plan.selected_provider_payload, config_id: plan.selected_config_id,
  });
  assert('outbox config_id == plan', entry.payload_sanitized.config_id === plan.selected_config_id);
  assert('outbox channel == plan', entry.channel === plan.selected_channel);
  assert('outbox provider zapi', entry.provider === 'zapi');
  assert('sem mismatch (channel igual)', outboxChannel === plan.selected_channel);
  assert('outbox send_allowed false', entry.send_allowed === false);
  assert('outbox sem destino cru', !JSON.stringify(entry).includes('5544999998888'));
}

// [9] Payload provider-specific dry_run.
console.log('\n[9] payload');
{
  const plan = planWith(toLite(cfg('zapi')));
  const payload = buildProviderPayload(plan.selected_provider_key, { destination_ref_masked: plan.selected_destination_ref_masked, message_text: plan.message_drafts[0]?.text });
  assert('payload provider zapi', payload.provider === 'zapi');
  assert('payload dry_run true', payload.dry_run === true);
  assert('payload sent false', payload.sent === false);
  assert('payload to_masked ****8888', payload.to_masked === '****8888');
}

// [10] send_real_allowed / sent false sempre.
console.log('\n[10] sempre bloqueado');
{
  const plan = planWith(toLite(cfg('zapi')));
  assert('plano external_action_sent false', plan.external_action_sent === false);
  assert('plano dry_run true', plan.dry_run === true);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
