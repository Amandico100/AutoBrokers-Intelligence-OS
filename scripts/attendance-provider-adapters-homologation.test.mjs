#!/usr/bin/env node
/**
 * 42X4 — Provider Adapter Homologation Harness (offline, sem rede, sem envio).
 *
 *   node scripts/attendance-provider-adapters-homologation.test.mjs
 *
 * Garante: adapters zapi/evolution_go/meta_cloud/manual; validação de config/payload;
 * mockSend nunca envia; parseSendResponse; checklist com blockers; sem token/destino cru;
 * canSendReal=false sempre; research_status correto por provider.
 */
import {
  getProviderAdapterRegistry,
  getProviderAdapter,
  buildProviderHomologationChecklist,
  summarizeProviderHarness,
  PROVIDER_ERROR_CODES,
} from '../lib/attendance/provider-adapters.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== 42X4 — Provider Adapter Homologation Harness ==');

// [1] Registry.
console.log('\n[1] registry');
{
  const keys = getProviderAdapterRegistry().map((a) => a.provider_key);
  for (const k of ['zapi', 'evolution_go', 'meta_cloud', 'manual']) assert(`adapter ${k} existe`, keys.includes(k));
  for (const a of getProviderAdapterRegistry()) assert(`${a.provider_key}: canSendReal false`, a.canSendReal === false);
  assert('zapi verified', getProviderAdapter('zapi').research_status === 'verified');
  assert('meta_cloud verified', getProviderAdapter('meta_cloud').research_status === 'verified');
  assert('evolution_go partial', getProviderAdapter('evolution_go').research_status === 'partial');
  assert('provider desconhecido → null', getProviderAdapter('telegram') === null);
}

// [2] Z-API.
console.log('\n[2] zapi');
{
  const a = getProviderAdapter('zapi');
  const ctxOk = { destination_ref_masked: '****8888', message_text: 'apólice ****99', credential_present: true };
  assert('config válida', a.validateConfig(ctxOk).valid === true);
  assert('config sem destino → invalid_destination', a.validateConfig({}).errors.includes('invalid_destination'));
  const payload = a.buildTextPayload({ destination_ref_masked: '****8888', message_text: 'CPF 04760897941 teste' }, ctxOk);
  assert('payload Client-Token no header', payload.headers_required.includes('Client-Token'));
  assert('payload endpoint z-api', payload.endpoint_template.includes('api.z-api.io'));
  assert('payload mascara CPF', !JSON.stringify(payload).includes('04760897941'));
  assert('payload sem token cru', !JSON.stringify(payload).toLowerCase().includes('bearer') && !/token=\w/.test(JSON.stringify(payload)));
  assert('validatePayload ok', a.validatePayload(payload).valid === true);
  const mock = a.mockSend(payload);
  assert('mock sent false', mock.sent === false && mock.mock === true);
  assert('mock provider_message_id', typeof mock.provider_message_id === 'string');
  const parsed = a.parseSendResponse({ zaapId: 'z1', messageId: 'm1', id: 'i1' });
  assert('parse zaapId', parsed.provider_message_id === 'z1' && parsed.status === 'accepted');
  const wh = a.parseWebhook({ status: 'DELIVERED', messageId: 'm1' });
  assert('webhook delivered', wh.status === 'delivered');
}

// [3] Meta Cloud.
console.log('\n[3] meta_cloud');
{
  const a = getProviderAdapter('meta_cloud');
  const payload = a.buildTextPayload({ destination_ref_masked: '****8888', message_text: 'oi' }, { destination_ref_masked: '****8888' });
  assert('messaging_product whatsapp', payload.body.messaging_product === 'whatsapp');
  assert('type text', payload.body.type === 'text');
  assert('Authorization header', payload.headers_required.includes('Authorization'));
  assert('endpoint graph.facebook', payload.endpoint_template.includes('graph.facebook.com'));
  assert('validatePayload ok', a.validatePayload(payload).valid === true);
  const outWindow = a.validateConfig({ destination_ref_masked: '****8888', within_24h_window: false });
  assert('fora da janela → template warning', outWindow.warnings.some((w) => w.includes('template_required')));
  const parsed = a.parseSendResponse({ messages: [{ id: 'wamid.X', message_status: 'accepted' }] });
  assert('parse wamid', parsed.provider_message_id === 'wamid.X' && parsed.status === 'accepted');
  const mock = a.mockSend(payload);
  assert('mock sent false', mock.sent === false);
}

// [4] Evolution Go — partial / research_required.
console.log('\n[4] evolution_go');
{
  const a = getProviderAdapter('evolution_go');
  const payload = a.buildTextPayload({ destination_ref_masked: '****8888', message_text: 'oi' }, { destination_ref_masked: '****8888' });
  assert('apikey header', payload.headers_required.includes('apikey'));
  assert('body number', payload.body.number === '****8888');
  const val = a.validatePayload(payload);
  assert('warning endpoint unverified', val.warnings.some((w) => w.includes('research_required')));
  const mock = a.mockSend(payload);
  assert('mock sent false', mock.sent === false);
}

// [5] Manual — nunca envia.
console.log('\n[5] manual');
{
  const a = getProviderAdapter('manual');
  assert('manual canSendReal false', a.canSendReal === false);
  const mock = a.mockSend(a.buildTextPayload({ destination_ref_masked: '****8888', message_text: 'oi' }, {}));
  assert('manual mock status handoff', mock.status === 'manual_handoff' && mock.sent === false);
}

// [6] Checklist com blockers.
console.log('\n[6] checklist');
{
  const cl = buildProviderHomologationChecklist('zapi', { destination_ref_masked: '****8888' });
  assert('checklist ready_for_real_future false', cl.ready_for_real_future === false);
  assert('checklist can_send_real false', cl.can_send_real === false);
  assert('blocker real_credentials_in_vault', cl.blockers.includes('real_credentials_in_vault'));
  assert('blocker kill_switch_tested', cl.blockers.includes('kill_switch_tested'));
  assert('mock_send_passing done', cl.items.find((i) => i.item === 'mock_send_passing').done === true);
  const clEvo = buildProviderHomologationChecklist('evolution_go', { destination_ref_masked: '****8888' });
  assert('evolution_go endpoint_documented blocker', clEvo.items.find((i) => i.item === 'endpoint_documented').blocker === true);
  const clUnknown = buildProviderHomologationChecklist('telegram', {});
  assert('provider desconhecido → unknown_provider blocker', clUnknown.blockers.includes('unknown_provider'));
}

// [7] summarizeProviderHarness (o que o outbox anexa).
console.log('\n[7] harness summary');
{
  const s = summarizeProviderHarness('zapi', { destination_ref_masked: '****8888', message_text: 'oi' });
  assert('summary research verified', s.provider_research_status === 'verified');
  assert('summary can_send_real false', s.can_send_real === false);
  assert('summary mock_capable true', s.provider_mock_capable === true);
  const sUnknown = summarizeProviderHarness('telegram', {});
  assert('unknown → unknown_provider status', sUnknown.provider_validation_status === 'unknown_provider');
}

// [8] Erros provider-neutros presentes.
console.log('\n[8] error mapping');
{
  for (const code of ['invalid_destination', 'auth_missing', 'rate_limited', 'instance_disconnected', 'message_rejected', 'webhook_signature_invalid', 'unknown_provider_error']) {
    assert(`error code ${code}`, PROVIDER_ERROR_CODES.includes(code));
  }
}

// [9] Nenhum vazamento de token/destino cru em todos os payloads.
console.log('\n[9] no leak');
{
  for (const a of getProviderAdapterRegistry()) {
    const payload = a.buildTextPayload({ destination_ref_masked: '****8888', message_text: 'telefone 5544999998888 e CPF 04760897941' }, {});
    const raw = JSON.stringify(payload);
    assert(`${a.provider_key}: sem telefone cru`, !raw.includes('5544999998888'));
    assert(`${a.provider_key}: sem CPF cru`, !raw.includes('04760897941'));
  }
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
