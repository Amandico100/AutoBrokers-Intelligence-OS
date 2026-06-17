#!/usr/bin/env node
/**
 * 42X1 — External Action Execution sandbox (offline, sem rede, sem envio externo).
 *
 *   node scripts/attendance-action-execution.test.mjs
 *
 * Garante: plan→session; estados; recuperação inteligente; canSendReal=false;
 * external_action_sent=false; sem PII nos eventos/summary.
 */
import {
  startExecutionSession,
  applyExecutionEvent,
  getChannelAdapter,
  recoverExternalExecutionStep,
  safeExecutionSessionSummary,
  interpretInsurerReply,
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

console.log('== 42X1 — External Action Execution (sandbox) ==');

// [1] Adapters — nenhum envia real.
console.log('\n[1] adapters');
{
  for (const ch of ['insurer_whatsapp', 'human_broker_manual', 'insurer_portal', 'insurer_phone_0800', 'insurer_email', 'insurer_api']) {
    assert(`${ch}: canSendReal=false`, getChannelAdapter(ch).canSendReal === false);
  }
  assert('whatsapp → sandbox', getChannelAdapter('insurer_whatsapp').mode === 'sandbox');
  assert('portal → real_future', getChannelAdapter('insurer_portal').mode === 'real_future');
}

// [2] Start — plan não pronto bloqueia.
console.log('\n[2] start');
{
  const notReady = startExecutionSession(readyPlan({ status: 'hitl_required' }));
  assert('plan não pronto → error', 'error' in notReady, JSON.stringify(notReady));
  const s = startExecutionSession(readyPlan());
  assert('plan pronto → session', !('error' in s));
  assert('status waiting_insurer', s.status === 'waiting_insurer', s.status);
  assert('external_action_sent false', s.external_action_sent === false);
  assert('prepared_message presente', typeof s.prepared_message === 'string' && s.prepared_message.length > 0);
  assert('evento simulated_send (não enviado)', s.events.some((e) => e.type === 'simulated_send'));
  assert('next_required_input', s.next_required_input === 'simulated_insurer_reply');
}

// [3] Estados a partir de respostas da seguradora.
console.log('\n[3] estados');
{
  const base = startExecutionSession(readyPlan());
  const accepted = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Recebido, protocolo 999.' }, { hasPolicyNumber: true });
  assert('aceito → completed_sandbox', accepted.status === 'completed_sandbox', accepted.status);
  const cpf = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Informe o CPF do segurado.' }, { hasPolicyNumber: true });
  assert('CPF → waiting_human + review', cpf.status === 'waiting_human' && cpf.human_review_required === true, cpf.status);
  const pol = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Qual o número da apólice?' }, { hasPolicyNumber: true });
  assert('apólice (disponível) → waiting_insurer', pol.status === 'waiting_insurer', pol.status);
  const addr = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Confirme o endereço do imóvel.' }, { hasPolicyNumber: true });
  assert('endereço → waiting_insured', addr.status === 'waiting_insured', addr.status);
  const portal = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Abra pelo portal.' }, { hasPolicyNumber: true });
  assert('portal → waiting_human + suggested_channel', portal.status === 'waiting_human' && portal.suggested_channel === 'insurer_portal', portal.status);
  const doc = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Envie a apólice em PDF.' }, { hasPolicyNumber: true });
  assert('documento → waiting_insured', doc.status === 'waiting_insured', doc.status);
  const cov = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Isso tem cobertura?' }, { hasPolicyNumber: true });
  assert('cobertura → waiting_human', cov.status === 'waiting_human', cov.status);
  const unav = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Não atendemos assistência por aqui.' }, { hasPolicyNumber: true });
  assert('indisponível → waiting_human', unav.status === 'waiting_human' && unav.suggested_channel === 'human_broker_manual', unav.status);
  const amb = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'hmm talvez' }, { hasPolicyNumber: true });
  assert('ambíguo → waiting_human', amb.status === 'waiting_human', amb.status);
}

// [4] Eventos de cancel / insured / terminal.
console.log('\n[4] cancel/insured/terminal');
{
  const base = startExecutionSession(readyPlan());
  const cancelled = applyExecutionEvent(base, { event_type: 'cancel' });
  assert('cancel → cancelled', cancelled.status === 'cancelled');
  const ins = applyExecutionEvent(base, { event_type: 'insured_answer', text: 'meu endereço é Rua X' });
  assert('insured_answer → waiting_insurer', ins.status === 'waiting_insurer');
  const done = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'Recebido.' });
  const after = applyExecutionEvent(done, { event_type: 'simulated_insurer_reply', text: 'qualquer coisa' });
  assert('evento após terminal é ignorado', after.status === 'completed_sandbox' && after.events.some((e) => e.type === 'event_ignored_terminal'));
}

// [5] Sem PII nos eventos/summary; sent=false.
console.log('\n[5] sem PII');
{
  const base = startExecutionSession(readyPlan());
  const withCpf = applyExecutionEvent(base, { event_type: 'simulated_insurer_reply', text: 'O CPF é 04760897941 confirme' }, { hasPolicyNumber: true });
  const raw = JSON.stringify(withCpf);
  assert('CPF mascarado nos eventos', !raw.includes('04760897941'), 'CPF vazou');
  assert('summary sent=false', safeExecutionSessionSummary(withCpf).external_action_sent === false);
  const sumRaw = JSON.stringify(safeExecutionSessionSummary(withCpf));
  assert('summary sem CPF', !sumRaw.includes('04760897941'));
}

// [6] recoverExternalExecutionStep direto.
console.log('\n[6] recovery');
{
  const r = recoverExternalExecutionStep(interpretInsurerReply('Qual o número da apólice?'), { hasPolicyNumber: false });
  assert('apólice sem ter → waiting_human', r.next_status === 'waiting_human', r.next_status);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
