#!/usr/bin/env node
/**
 * 42X2 — External Action Outbox, Permission Gates & Real Adapter Skeleton
 * (offline, sem rede, sem envio externo).
 *
 *   node scripts/attendance-action-outbox.test.mjs
 *
 * Garante: outbox prepara/aprova/cancela; gates de permissão SEMPRE send_allowed=false;
 * kill switch / flag off / sem tenant_connection / adapter não-real bloqueiam;
 * adapter skeleton nunca envia; auditoria sem PII; destino mascarado.
 */
import {
  buildOutboxEntry,
  approveOutboxEntry,
  cancelOutboxEntry,
  evaluateExternalSendPermission,
  getInsurerWhatsAppRealAdapterSkeleton,
  buildAuditEvent,
  safeOutboxSummary,
  startExecutionSession,
} from '../lib/attendance/action-engine.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

function readyPlan(over = {}) {
  return {
    case_id: 'case-1', dispatch_packet_id: 'dp-1', corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician', insurer_key: 'allianz',
    channel_candidates: [], selected_channel: 'insurer_whatsapp', action_goal: 'x', required_data: [], available_data: [], missing_data: [],
    readiness: { packet_state: 'ready_for_human_approval', dispatch_allowed: true }, coverage_gate: { state: 'human_approved', human_required: false },
    hitl_gate: { required: false, reason: null }, planned_steps: [], message_drafts: [{ channel: 'insurer_whatsapp', text: 'Olá, apólice final ****99...' }],
    fallback_steps: [], human_review_required: false, risk_flags: [], allowed_to_prepare: true, status: 'ready_for_human_approval',
    playbook_id: 'allianz_residential_electrician_whatsapp_v1', dry_run: true, external_action_sent: false, ...over,
  };
}

// Contexto "ideal" exceto pelos gates que faltam por design no 42X2.
function idealCtx(over = {}) {
  return {
    realEnabled: true,
    insurerWhatsappRealSend: true,
    killSwitchActive: false,
    adapterCanSendReal: true,
    tenantConnectionStatus: 'connected',
    credentialRefPresent: true,
    actionPlanStatus: 'ready_for_human_approval',
    executionStatus: 'waiting_insurer',
    coverageState: 'human_approved',
    packetState: 'ready_for_human_approval',
    approvalStatus: 'approved',
    rateLimit: { used: 0, limit: 20 },
    channelHomologated: true,
    piiViolation: false,
    ...over,
  };
}

console.log('== 42X2 — External Action Outbox & Permission Gates ==');

// [1] Build outbox.
console.log('\n[1] build outbox');
{
  const blocked = buildOutboxEntry({ case_id: 'c1', dispatch_packet_id: 'dp1', plan: readyPlan({ status: 'hitl_required' }) });
  assert('plano não pronto → blocked', blocked.status === 'blocked', blocked.status);
  assert('blocked: send_allowed false', blocked.send_allowed === false);

  const ready = buildOutboxEntry({ case_id: 'c1', dispatch_packet_id: 'dp1', plan: readyPlan() });
  assert('plano pronto → awaiting_approval', ready.status === 'awaiting_approval', ready.status);
  assert('approval_required true', ready.approval_required === true);
  assert('send_allowed false', ready.send_allowed === false);
  assert('sent false', ready.sent === false);
  assert('blocker real_send_disabled_42x2 presente', ready.blockers.includes('real_send_disabled_42x2'));
  assert('payload can_send_real false', ready.payload_sanitized.can_send_real === false);
}

// [2] approve → approved_not_sent (nunca envia).
console.log('\n[2] approve');
{
  const ready = buildOutboxEntry({ case_id: 'c1', dispatch_packet_id: 'dp1', plan: readyPlan() });
  const approved = approveOutboxEntry(ready, 'user-123');
  assert('approve → approved_not_sent', approved.status === 'approved_not_sent', approved.status);
  assert('approved_by gravado', approved.approved_by === 'user-123');
  assert('approved_at gravado', typeof approved.approved_at === 'string');
  assert('aprovado: send_allowed segue false', approved.send_allowed === false);
  assert('aprovado: sent segue false', approved.sent === false);

  const blocked = buildOutboxEntry({ case_id: 'c1', dispatch_packet_id: 'dp1', plan: readyPlan({ status: 'hitl_required' }) });
  const stillBlocked = approveOutboxEntry(blocked, 'user-123');
  assert('aprovar item blocked não libera', stillBlocked.status === 'blocked', stillBlocked.status);
}

// [3] cancel.
console.log('\n[3] cancel');
{
  const ready = buildOutboxEntry({ case_id: 'c1', dispatch_packet_id: 'dp1', plan: readyPlan() });
  const cancelled = cancelOutboxEntry(ready);
  assert('cancel → cancelled', cancelled.status === 'cancelled');
  assert('cancelado: send_allowed false', cancelled.send_allowed === false);
}

// [4] Permission gates — SEMPRE send_allowed=false.
console.log('\n[4] permission gates');
{
  const ideal = evaluateExternalSendPermission(idealCtx());
  assert('mesmo ctx ideal → send_allowed false', ideal.send_allowed === false);

  const flagOff = evaluateExternalSendPermission(idealCtx({ realEnabled: false }));
  assert('flag off bloqueia', flagOff.send_allowed === false && flagOff.blockers.includes('real_flag_enabled'));

  const kill = evaluateExternalSendPermission(idealCtx({ killSwitchActive: true }));
  assert('kill switch bloqueia', kill.send_allowed === false && kill.blockers.includes('kill_switch_off'));

  const noAdapter = evaluateExternalSendPermission(idealCtx({ adapterCanSendReal: false }));
  assert('adapter canSendReal=false bloqueia', noAdapter.blockers.includes('adapter_can_send_real'));

  const noTc = evaluateExternalSendPermission(idealCtx({ tenantConnectionStatus: null }));
  assert('sem tenant_connection bloqueia', noTc.blockers.includes('tenant_connection_active'));

  const noCred = evaluateExternalSendPermission(idealCtx({ credentialRefPresent: false }));
  assert('sem credential ref bloqueia', noCred.blockers.includes('credential_present'));

  const noApproval = evaluateExternalSendPermission(idealCtx({ approvalStatus: null }));
  assert('sem aprovação bloqueia', noApproval.blockers.includes('approval_exists'));

  const rate = evaluateExternalSendPermission(idealCtx({ rateLimit: { used: 20, limit: 20 } }));
  assert('rate limit estourado bloqueia', rate.blockers.includes('rate_limit_ok'));

  const notHomolog = evaluateExternalSendPermission(idealCtx({ channelHomologated: false }));
  assert('canal não homologado bloqueia', notHomolog.blockers.includes('channel_homologated'));

  const pii = evaluateExternalSendPermission(idealCtx({ piiViolation: true }));
  assert('violação de PII bloqueia', pii.blockers.includes('no_pii_violation'));

  const real42x2 = evaluateExternalSendPermission(idealCtx());
  assert('ctx ideal → reason real_send_disabled_42x2', real42x2.reason === 'real_send_disabled_42x2', real42x2.reason);
}

// [5] Adapter skeleton — nunca envia.
console.log('\n[5] adapter skeleton');
{
  const a = getInsurerWhatsAppRealAdapterSkeleton();
  assert('canSendReal false', a.canSendReal === false);
  assert('valida destino bom', a.validateDestination('5544999998888') === true);
  assert('rejeita destino ruim', a.validateDestination('abc') === false);
  assert('valida provider zapi', a.validateProvider('zapi') === true);
  assert('rejeita provider ruim', a.validateProvider('telegram') === false);

  const noTc = a.send({ destination_ref: '5544999998888', provider: 'zapi', message_text: 'oi', tenant_connection: null });
  assert('send sem tenant_connection → no_tenant_connection', noTc.sent === false && noTc.status === 'no_tenant_connection');

  const blocked = a.send({ destination_ref: '5544999998888', provider: 'zapi', message_text: 'apólice ****99', tenant_connection: { status: 'connected', encrypted_secret_ref: 'ref-1' } });
  assert('send com tudo "ok" → blocked_real_send_disabled', blocked.sent === false && blocked.status === 'blocked_real_send_disabled', blocked.status);
  assert('payload preparado mascara destino', blocked.prepared_payload && blocked.prepared_payload.to_masked === '****8888', JSON.stringify(blocked.prepared_payload));
}

// [6] Auditoria + summary sem PII.
console.log('\n[6] auditoria / PII');
{
  const ev = buildAuditEvent('outbox_prepared', 'obx-1', { note: 'CPF 04760897941 do segurado' });
  assert('audit type ok', ev.type === 'outbox_prepared');
  assert('audit mascara CPF na nota', !JSON.stringify(ev).includes('04760897941'), JSON.stringify(ev));

  // outbox com mensagem contendo CPF → mascarada.
  const exec = startExecutionSession(readyPlan({ message_drafts: [{ channel: 'insurer_whatsapp', text: 'Segurado CPF 04760897941, apólice ****99' }] }));
  const entry = buildOutboxEntry({ case_id: 'c1', dispatch_packet_id: 'dp1', execution: exec, plan: readyPlan(), destination_ref: '5544999998888' });
  const raw = JSON.stringify(entry);
  assert('outbox sem CPF cru', !raw.includes('04760897941'), 'CPF vazou');
  assert('destino mascarado', entry.destination_ref_masked === '****8888', entry.destination_ref_masked);

  const summary = safeOutboxSummary([entry]);
  assert('summary any_sent false', summary.any_sent === false);
  assert('summary any_send_allowed false', summary.any_send_allowed === false);
  assert('summary sem destino cru', !JSON.stringify(summary).includes('5544999998888'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
