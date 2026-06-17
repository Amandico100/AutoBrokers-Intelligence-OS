#!/usr/bin/env node
/**
 * 42X0 — Global External Action Engine (offline, sem rede, sem envio externo).
 *
 *   node scripts/attendance-action-engine.test.mjs
 *
 * Garante: plano dry-run por gate (incomplete/blocked/hitl/ready); canais
 * candidatos; playbook Allianz eletricista + draft mascarado; interpretação de
 * resposta da seguradora; nada enviado; sem PII.
 */
import {
  evaluateChannelCandidates,
  buildExternalActionPlan,
  interpretInsurerReply,
  safeActionPlanSummary,
  getPlaybook,
  buildInsurerMessageDraft,
} from '../lib/attendance/action-engine.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const FULL_SLOTS = { affected_area: 'cozinha', electrical_issue_type: 'sem energia', property_address_confirmed: { status: 'confirmed' } };
function caseRow(over = {}) {
  return {
    id: 'case-1',
    insured_document_ref: '04760897941',
    customer_phone: '5544998887766',
    insured_address: { city: 'São Paulo', state: 'SP', street: 'Rua Secreta 123' },
    selected_corridor_key: 'allianz_residential_assistance',
    selected_subcorridor_key: 'electrician',
    insurer_key: 'allianz',
    risk_level: 'low',
    policy_snapshot: { insurer_key: 'allianz', masked_policy_number: '****99', product: 'Residencial' },
    metadata: {
      coverage_readiness: { state: 'human_validation_required', human_required: true },
      dispatch_readiness: { packet_state: 'hitl_required', dispatch_allowed: false },
    },
    ...over,
  };
}
const channels = evaluateChannelCandidates({ human_destination: true });
const dp = { id: 'dp-1', metadata: { packet_state: 'hitl_required' } };

console.log('== 42X0 — Global External Action Engine ==');

// [1] Canais candidatos.
console.log('\n[1] canais');
{
  assert('whatsapp prioridade 1', channels[0].channel === 'insurer_whatsapp');
  assert('whatsapp não enviável agora', channels[0].available_now === false);
  assert('fallback manual disponível', channels.find((c) => c.channel === 'human_broker_manual').available_now === true);
  assert('0800 é future', channels.find((c) => c.channel === 'insurer_phone_0800').current_mode === 'future');
}

// [2] Gate hitl_required.
console.log('\n[2] plano hitl_required');
{
  const p = buildExternalActionPlan({ caseRow: caseRow(), dispatchPacket: dp, filledSlots: FULL_SLOTS, channels });
  assert('status hitl_required', p.status === 'hitl_required', p.status);
  assert('human_review_required', p.human_review_required === true);
  assert('não prepara draft ainda', p.message_drafts.length === 0);
  assert('external_action_sent false', p.external_action_sent === false);
  assert('dry_run true', p.dry_run === true);
}

// [3] Gate incomplete (faltam slots).
console.log('\n[3] plano incomplete');
{
  const p = buildExternalActionPlan({ caseRow: caseRow(), dispatchPacket: { id: 'dp', metadata: { packet_state: 'incomplete' } }, filledSlots: { affected_area: 'cozinha' }, channels });
  assert('status incomplete', p.status === 'incomplete', p.status);
  assert('missing inclui electrical_issue_type', p.missing_data.includes('electrical_issue_type'), p.missing_data.join(','));
  assert('sem draft', p.message_drafts.length === 0);
}

// [4] Gate ready_for_human_approval (coverage human_approved).
console.log('\n[4] plano ready_for_human_approval');
{
  const c = caseRow({ verification_status: 'verified_by_human', metadata: { coverage_readiness: { state: 'human_approved', human_required: false }, dispatch_readiness: { packet_state: 'ready_for_human_approval', dispatch_allowed: true } } });
  const p = buildExternalActionPlan({ caseRow: c, dispatchPacket: { id: 'dp', metadata: { packet_state: 'ready_for_human_approval' } }, filledSlots: FULL_SLOTS, channels });
  assert('status ready_for_human_approval', p.status === 'ready_for_human_approval', p.status);
  assert('allowed_to_prepare true', p.allowed_to_prepare === true);
  assert('gera draft', p.message_drafts.length === 1);
  assert('draft cita final mascarado', /\*\*\*\*99/.test(p.message_drafts[0].text), p.message_drafts[0].text);
  assert('draft NÃO vaza CPF', !p.message_drafts[0].text.includes('04760897941'));
  assert('draft NÃO vaza telefone', !p.message_drafts[0].text.includes('5544998887766'));
  assert('draft NÃO vaza endereço cru', !/Rua Secreta 123/.test(p.message_drafts[0].text));
  assert('external_action_sent false', p.external_action_sent === false);
}

// [5] Gate blocked (risco alto).
console.log('\n[5] plano blocked');
{
  const p = buildExternalActionPlan({ caseRow: caseRow({ risk_level: 'high' }), dispatchPacket: dp, filledSlots: FULL_SLOTS, channels });
  assert('status blocked', p.status === 'blocked', p.status);
  assert('risk_flag high_risk', p.risk_flags.includes('high_risk'));
  assert('human_review_required', p.human_review_required === true);
}

// [6] Playbook Allianz eletricista + draft.
console.log('\n[6] playbook');
{
  const pb = getPlaybook({ insurerKey: 'allianz', corridorKey: 'allianz_residential_assistance', subcorridorKey: 'electrician', channel: 'insurer_whatsapp' });
  assert('playbook allianz eletricista', pb.playbook_id === 'allianz_residential_electrician_whatsapp_v1');
  assert('playbook proíbe envio sem HITL', pb.forbidden_actions.some((f) => /sem adapter|HITL/i.test(f)));
  const draft = buildInsurerMessageDraft(pb, { insurer: 'allianz', masked_policy_number: '****99', affected_area: 'cozinha', problem: 'falta de energia' });
  assert('draft humanizado com Allianz', /Allianz/.test(draft));
  assert('draft sem cheiro/faísca afirmado como risco', /sem sinais de fumaça/i.test(draft));
  const generic = getPlaybook({ insurerKey: 'porto', corridorKey: 'porto_auto', subcorridorKey: 'pneu' });
  assert('fallback genérico manual', generic.channel === 'human_broker_manual');
}

// [7] Interpretação de resposta da seguradora.
console.log('\n[7] interpretação de resposta');
{
  assert('"recebido, protocolo X" → accepted', interpretInsurerReply('Recebido, geramos o protocolo 123.').classification === 'accepted');
  assert('"qual o número da apólice?" → asks_for_missing_data', interpretInsurerReply('Qual o número da apólice?').classification === 'asks_for_missing_data');
  assert('"acesse o portal" → redirects_channel', interpretInsurerReply('Por favor, abra um chamado no portal.').classification === 'redirects_channel');
  assert('"não fazemos assistência" → unavailable', interpretInsurerReply('Não atendemos assistência por aqui.').classification === 'unavailable');
  assert('"envie a apólice" → requests_document', interpretInsurerReply('Envie a apólice em PDF.').classification === 'requests_document');
  assert('"isso tem cobertura?" → coverage_question', interpretInsurerReply('Isso está coberto na apólice?').classification === 'coverage_question');
  assert('CPF pedido → ask_human (sensível)', interpretInsurerReply('Informe o CPF do segurado.').next_step === 'ask_human');
  assert('endereço pedido → ask_insured', interpretInsurerReply('Confirme o endereço do imóvel.').next_step === 'ask_insured');
  const amb = interpretInsurerReply('hmmm ok talvez');
  assert('ambíguo → human_required/ask_human', amb.classification === 'unknown' && amb.next_step === 'ask_human');
  assert('vazio → unknown', interpretInsurerReply('').classification === 'unknown');
  // customer_message nunca pede CPF cru
  assert('msg de CPF não pede dado cru ao cliente', !/cpf/i.test(interpretInsurerReply('Informe o CPF do segurado.').customer_message || ''));
}

// [8] Summary sanitizado (sem PII).
console.log('\n[8] summary sem PII');
{
  const p = buildExternalActionPlan({ caseRow: caseRow({ metadata: { coverage_readiness: { state: 'human_approved', human_required: false }, dispatch_readiness: { packet_state: 'ready_for_human_approval', dispatch_allowed: true } } }), dispatchPacket: dp, filledSlots: FULL_SLOTS, channels });
  const raw = JSON.stringify(safeActionPlanSummary(p));
  assert('summary sem CPF', !raw.includes('04760897941'));
  assert('summary sem telefone', !raw.includes('5544998887766'));
  assert('summary tem status + sent=false', /status/.test(raw) && /"external_action_sent":false/.test(raw));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
