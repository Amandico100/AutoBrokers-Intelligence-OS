#!/usr/bin/env node
/**
 * 42X3 — Provider-Agnostic Insurer Channel Registry (offline, sem rede, sem envio).
 *
 *   node scripts/attendance-insurer-channel-registry.test.mjs
 *
 * Garante: registry provider-agnostic; capabilities; config sanitizada (sem
 * destino cru); config mais específica vence; outbox usa config; sem config →
 * manual; payloads por provider não enviam/não vazam; homologation states;
 * send_real_allowed=false sempre.
 */
import {
  getInsurerMessagingProviderRegistry,
  resolveProviderCapabilities,
  validateProviderKey,
  buildInsurerChannelConfig,
  sanitizeInsurerChannelConfig,
  resolveActiveInsurerChannelConfig,
  evaluateInsurerChannelHomologation,
  buildProviderPayload,
  safeChannelConfigSummary,
} from '../lib/attendance/insurer-channel-registry.ts';
import { buildOutboxEntry } from '../lib/attendance/action-engine.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== 42X3 — Insurer Channel Registry ==');

// [1] Provider registry.
console.log('\n[1] provider registry');
{
  const reg = getInsurerMessagingProviderRegistry();
  const keys = reg.map((p) => p.provider_key);
  for (const k of ['zapi', 'evolution_go', 'meta_cloud', 'manual', 'future_custom']) {
    assert(`registry contém ${k}`, keys.includes(k));
  }
  assert('zapi available', reg.find((p) => p.provider_key === 'zapi').status === 'available');
  assert('evolution_go future', reg.find((p) => p.provider_key === 'evolution_go').status === 'future');
  assert('meta_cloud future', reg.find((p) => p.provider_key === 'meta_cloud').status === 'future');
  assert('manual real_send_supported_future false', reg.find((p) => p.provider_key === 'manual').real_send_supported_future === false);
  assert('validateProviderKey zapi true', validateProviderKey('zapi') === true);
  assert('validateProviderKey desconhecido false', validateProviderKey('telegram') === false);
}

// [2] Capability matrix.
console.log('\n[2] capabilities');
{
  const zapi = resolveProviderCapabilities('zapi');
  assert('zapi text+media+webhook+group', zapi.supports_text && zapi.supports_media && zapi.supports_webhook && zapi.supports_group);
  assert('zapi sem template', zapi.supports_template === false);
  const meta = resolveProviderCapabilities('meta_cloud');
  assert('meta template true', meta.supports_template === true);
  assert('meta group false', meta.supports_group === false);
  const manual = resolveProviderCapabilities('manual');
  assert('manual sem text', manual.supports_text === false);
  const unknown = resolveProviderCapabilities('telegram');
  assert('provider desconhecido found false', unknown.found === false);
}

// [3] Config build/sanitize — destino nunca cru.
console.log('\n[3] config build/sanitize');
{
  const cfg = buildInsurerChannelConfig({
    company_id: 'co-1', insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician',
    provider_key: 'zapi', destination_ref: '5544999998888',
  });
  assert('channel insurer_whatsapp', cfg.channel === 'insurer_whatsapp');
  assert('send_real_allowed false', cfg.send_real_allowed === false);
  assert('destino mascarado ****8888', cfg.destination_ref_masked === '****8888', cfg.destination_ref_masked);
  assert('config sem destino cru', !JSON.stringify(cfg).includes('5544999998888'), 'destino vazou');
  const san = sanitizeInsurerChannelConfig(cfg);
  assert('sanitize sem destino cru', !JSON.stringify(san).includes('5544999998888'));
  assert('sanitize send_real_allowed false', san.send_real_allowed === false);
}

// [4] resolveActive — mais específica vence; sem match → null.
console.log('\n[4] resolveActive');
{
  const insurerOnly = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'zapi', destination_ref: '111', priority: 100 });
  const corridor = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', provider_key: 'zapi', destination_ref: '222', priority: 100 });
  const sub = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician', provider_key: 'meta_cloud', destination_ref: '333', priority: 100 });
  const configs = [insurerOnly, corridor, sub];
  const ctx = { insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician' };
  const best = resolveActiveInsurerChannelConfig(configs, ctx);
  assert('subcorredor vence', best && best.config_id === sub.config_id, best?.config_id);

  const ctx2 = { insurer_key: 'allianz', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'hydraulic' };
  const best2 = resolveActiveInsurerChannelConfig(configs, ctx2);
  assert('sem sub match → corredor vence', best2 && best2.config_id === corridor.config_id, best2?.config_id);

  const none = resolveActiveInsurerChannelConfig(configs, { insurer_key: 'porto', corridor_key: null, subcorridor_key: null });
  assert('seguradora sem config → null', none === null);

  const inactive = resolveActiveInsurerChannelConfig([buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'zapi', destination_ref: '1', is_active: false })], { insurer_key: 'allianz' });
  assert('config inativa ignorada → null', inactive === null);
}

// [5] Outbox usa config; sem config → manual.
console.log('\n[5] outbox + config');
{
  const cfg = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'zapi', destination_ref: '5544999998888' });
  const payload = buildProviderPayload(cfg.provider_key, { destination_ref_masked: cfg.destination_ref_masked, message_text: 'apólice ****99' });
  const entry = buildOutboxEntry({
    case_id: 'c1', dispatch_packet_id: 'dp1',
    plan: { status: 'ready_for_human_approval', selected_channel: 'human_broker_manual', message_drafts: [{ channel: 'human_broker_manual', text: 'oi' }], playbook_id: 'pb', insurer_key: 'allianz' },
    channel: cfg.channel, provider: cfg.provider_key, destination_ref_masked: cfg.destination_ref_masked, provider_payload: payload, config_id: cfg.config_id,
  });
  assert('entry channel da config', entry.channel === 'insurer_whatsapp', entry.channel);
  assert('entry provider zapi', entry.provider === 'zapi');
  assert('entry destino mascarado', entry.destination_ref_masked === '****8888', entry.destination_ref_masked);
  assert('entry config_id', entry.payload_sanitized.config_id === cfg.config_id);
  assert('entry provider_payload presente', entry.payload_sanitized.provider_payload && entry.payload_sanitized.provider_payload.provider === 'zapi');
  assert('entry send_allowed false', entry.send_allowed === false);
  assert('entry sem destino cru', !JSON.stringify(entry).includes('5544999998888'));

  // Sem config → manual.
  const noCfg = buildOutboxEntry({
    case_id: 'c1', dispatch_packet_id: 'dp1',
    plan: { status: 'ready_for_human_approval', selected_channel: 'human_broker_manual', message_drafts: [{ channel: 'human_broker_manual', text: 'oi' }], playbook_id: 'pb' },
  });
  assert('sem config → human_broker_manual', noCfg.channel === 'human_broker_manual', noCfg.channel);
}

// [6] Payload builders — não enviam, não vazam.
console.log('\n[6] payload builders');
{
  const ctx = { destination_ref_masked: '****8888', message_text: 'CPF 04760897941 apólice' };
  for (const p of ['zapi', 'evolution_go', 'meta_cloud', 'manual']) {
    const pl = buildProviderPayload(p, ctx);
    assert(`${p}: dry_run true`, pl.dry_run === true);
    assert(`${p}: sent false`, pl.sent === false);
    assert(`${p}: sem CPF`, !JSON.stringify(pl).includes('04760897941'), JSON.stringify(pl));
    assert(`${p}: destino mascarado`, JSON.stringify(pl).includes('****8888'));
  }
  const unknown = buildProviderPayload('telegram', ctx);
  assert('provider desconhecido supported false', unknown.supported === false);
}

// [7] Homologation states — nenhum libera real.
console.log('\n[7] homologation');
{
  const manual = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'manual' });
  assert('manual → sandbox_ready', evaluateInsurerChannelHomologation(manual).state === 'sandbox_ready');

  const noDest = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'zapi' });
  assert('zapi sem destino → destination_missing', evaluateInsurerChannelHomologation(noDest).state === 'destination_missing');

  const noCred = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'zapi', destination_ref: '5544999998888' });
  assert('zapi com destino sem credencial → missing_credentials', evaluateInsurerChannelHomologation(noCred, { credentialPresent: false }).state === 'missing_credentials');

  const ok = evaluateInsurerChannelHomologation(noCred, { credentialPresent: true });
  assert('zapi destino+credencial → sandbox_ready', ok.state === 'sandbox_ready', ok.state);
  assert('homologation send_real_allowed false', ok.send_real_allowed === false);

  const unknown = buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'future_custom', destination_ref: '5544999998888' });
  assert('homologation sempre tem blocker real_send_disabled_42x3', evaluateInsurerChannelHomologation(unknown, { credentialPresent: true }).blockers.includes('real_send_disabled_42x3'));
}

// [8] Summary sem PII.
console.log('\n[8] summary');
{
  const cfgs = [
    buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'allianz', provider_key: 'zapi', destination_ref: '5544999998888' }),
    buildInsurerChannelConfig({ company_id: 'co', insurer_key: 'porto', provider_key: 'meta_cloud', destination_ref: '5511888887777' }),
  ];
  const sum = safeChannelConfigSummary(cfgs);
  assert('summary count 2', sum.count === 2);
  assert('summary any_send_real_allowed false', sum.any_send_real_allowed === false);
  assert('summary sem destino cru', !JSON.stringify(sum).includes('5544999998888') && !JSON.stringify(sum).includes('5511888887777'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
