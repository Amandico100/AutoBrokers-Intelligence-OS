#!/usr/bin/env node
/**
 * 42W0 — WhatsApp inbound normalization, buffer, dedupe-key, case routing,
 * webhook auth e outbound policy (offline, sem rede).
 *
 *   node scripts/whatsapp-inbound.test.mjs
 *
 * NUNCA usa dados reais. Garante: telefone mascarado + hash, sem PII crua,
 * buffer consolidado em ordem, classificação de mídia, auth do webhook,
 * dry-run conservador e roteamento de case correto.
 */
import {
  normalizeZapiInbound,
  maskPhone,
  phoneHash,
  safeName,
  classifyInboundEvent,
  consolidateBufferedMessages,
  hasMinimalIdentifiers,
  resolveWebhookAuthMode,
  checkWebhookAuth,
  resolveOutboundPolicy,
  mediaAckMessage,
} from '../lib/attendance/whatsapp-inbound.ts';
import {
  resolveAttendanceCaseForWhatsAppInbound,
  inferSubcorridorFromText,
} from '../lib/attendance/whatsapp-case-routing.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const PHONE = '5544998887766';
const payloadText = { connectedPhone: '5544111112222', phone: PHONE, senderName: 'João da Silva', messageId: 'MID-1', momment: 123, text: { message: 'Estou sem luz' } };

console.log('== 42W0 — WhatsApp inbound (offline) ==');

// [1] Normalização + mascaramento.
console.log('\n[1] normalização + máscara');
{
  const n = normalizeZapiInbound(payloadText, { companyId: 'co-1', agentId: 'ag-1' });
  assert('provider z-api', n.provider === 'z-api');
  assert('message_id capturado', n.message_id === 'MID-1');
  assert('texto extraído', n.text === 'Estou sem luz');
  assert('telefone mascarado (sem cru)', n.from_phone_masked === '5544****66', n.from_phone_masked);
  assert('hash determinístico 16 hex', /^[0-9a-f]{16}$/.test(n.from_phone_hash), n.from_phone_hash);
  assert('nome seguro só primeiro nome', n.from_name_safe === 'João', n.from_name_safe);
  assert('company/agent propagados', n.company_id === 'co-1' && n.agent_id === 'ag-1');
  const raw = JSON.stringify(n);
  assert('não vaza telefone cru', !raw.includes(PHONE), 'telefone cru presente');
  assert('não vaza sobrenome completo', !raw.includes('da Silva'), 'sobrenome presente');
}

// [2] Hash estável e mask helpers.
console.log('\n[2] hash/mask helpers');
{
  assert('phoneHash estável', phoneHash(PHONE) === phoneHash('+55 (44) 99888-7766'));
  assert('mask curta', maskPhone('123') === '****');
  assert('safeName vazio → null', safeName('') === null);
}

// [3] Classificação de evento.
console.log('\n[3] classificação de evento');
{
  assert('texto', classifyInboundEvent(payloadText) === 'text');
  assert('áudio', classifyInboundEvent({ audio: { audioUrl: 'x' } }) === 'audio');
  assert('imagem', classifyInboundEvent({ image: { imageUrl: 'x' } }) === 'image');
  assert('grupo → status (ignora)', classifyInboundEvent({ isGroup: true, text: { message: 'x' } }) === 'status');
  assert('fromMe → status (ignora)', classifyInboundEvent({ fromMe: true }) === 'status');
  assert('vazio', classifyInboundEvent({}) === 'empty');
  assert('ack de áudio é humano', /áudio/i.test(mediaAckMessage('audio')));
}

// [4] Identificadores mínimos.
console.log('\n[4] identificadores mínimos');
{
  assert('payload completo ok', hasMinimalIdentifiers(payloadText) === true);
  assert('sem phone rejeita', hasMinimalIdentifiers({ connectedPhone: 'x' }) === false);
  assert('sem connectedPhone rejeita', hasMinimalIdentifiers({ phone: 'x' }) === false);
}

// [5] Consolidação de buffer (ordem temporal).
console.log('\n[5] buffer consolidado');
{
  const c = consolidateBufferedMessages(['Oi', 'estou sem luz', 'só na cozinha']);
  assert('junta com newline em ordem', c === 'Oi\nestou sem luz\nsó na cozinha', JSON.stringify(c));
  assert('ignora vazios', consolidateBufferedMessages(['a', '', '  ', 'b']) === 'a\nb');
  assert('não-array → vazio', consolidateBufferedMessages(null) === '');
}

// [6] Webhook auth.
console.log('\n[6] webhook auth');
{
  assert('mode default disabled', resolveWebhookAuthMode('xxx') === 'disabled');
  assert('mode shared_secret', resolveWebhookAuthMode('shared_secret') === 'shared_secret');
  assert('disabled sempre ok', checkWebhookAuth({ mode: 'disabled' }).ok === true);
  assert('shared_secret correto ok', checkWebhookAuth({ mode: 'shared_secret', expectedSecret: 's', providedSecret: 's' }).ok === true);
  assert('shared_secret errado falha', checkWebhookAuth({ mode: 'shared_secret', expectedSecret: 's', providedSecret: 'x' }).ok === false);
  assert('shared_secret faltando falha', checkWebhookAuth({ mode: 'shared_secret', expectedSecret: 's' }).ok === false);
  assert('signature ausente falha', checkWebhookAuth({ mode: 'provider_signature', hasProviderSignature: false }).ok === false);
}

// [7] Outbound policy (dry-run conservador).
console.log('\n[7] outbound policy');
{
  assert('default → dry-run', resolveOutboundPolicy({}).dry_run === true);
  assert('global dry-run', resolveOutboundPolicy({ globalDryRun: true, externalSendAuthorized: true }).dry_run === true);
  assert('sandbox → dry-run', resolveOutboundPolicy({ environment: 'sandbox', externalSendAuthorized: true }).dry_run === true);
  assert('integration dry-run', resolveOutboundPolicy({ integrationDryRun: true, externalSendAuthorized: true }).dry_run === true);
  const live = resolveOutboundPolicy({ environment: 'production', externalSendAuthorized: true });
  assert('produção + autorizado → envia', live.dry_run === false && live.external_send_allowed === true);
  assert('não autorizado → dry-run', resolveOutboundPolicy({ environment: 'production' }).dry_run === true);
}

// [8] Case routing.
console.log('\n[8] case routing');
{
  const open = resolveAttendanceCaseForWhatsAppInbound({ existingCase: { id: 'c1', status: 'collecting_slots' }, conversationId: 'cv1', hasProcessableText: true });
  assert('case aberto → reply_existing', open.action === 'reply_existing' && open.case_id === 'c1', open.action);
  const handoff = resolveAttendanceCaseForWhatsAppInbound({ existingCase: { id: 'c1', status: 'handoff' }, conversationId: 'cv1', hasProcessableText: true });
  assert('case handoff → handoff_block', handoff.action === 'handoff_block', handoff.action);
  const closed = resolveAttendanceCaseForWhatsAppInbound({ existingCase: { id: 'c1', status: 'closed' }, conversationId: 'cv1', hasProcessableText: true });
  assert('case fechado → create_case', closed.action === 'create_case', closed.action);
  const none = resolveAttendanceCaseForWhatsAppInbound({ existingCase: null, conversationId: null, hasProcessableText: true });
  assert('sem case → create_case', none.action === 'create_case', none.action);
}

// [9] Inferência de subcorredor (só quando claro).
console.log('\n[9] inferência de subcorredor');
{
  assert('sem luz → electrician', inferSubcorridorFromText('estou sem luz na cozinha') === 'electrician');
  assert('vago → null', inferSubcorridorFromText('preciso de ajuda') === null);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
