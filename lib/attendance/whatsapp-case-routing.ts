// WhatsApp → Attendance Case routing (42W0) — decisão PURA, sem I/O.
//
// Decide o que fazer com um inbound de WhatsApp: responder um case aberto,
// criar um novo case, bloquear auto-resposta (handoff humano) ou ignorar.
// O atendimento externo SEMPRE vai para o Attendance Agent (nunca o Core interno).

export type CaseRoutingAction = 'reply_existing' | 'create_case' | 'handoff_block' | 'ignore';

export interface CaseRoutingDecision {
  action: CaseRoutingAction;
  reason: string;
  case_id: string | null;
  conversation_id: string | null;
}

// Status finais de um attendance_case (não recebem continuação no mesmo case).
const FINAL_CASE_STATUSES = new Set(['closed', 'cancelled']);

export interface CaseRoutingInput {
  /** attendance_case mais recente vinculado à conversation (ou null). */
  existingCase: { id: string; status: string } | null;
  /** conversation existente do telefone/company/agent (ou null). */
  conversationId: string | null;
  /** evento é texto processável? (mídia pura ainda cria/870 roteia, mas com ack). */
  hasProcessableText: boolean;
}

/**
 * Decide o roteamento do inbound. PURO.
 * - case aberto (não final, não handoff) → reply_existing.
 * - case em handoff → handoff_block (registra inbound, não responde automático).
 * - case final ou inexistente → create_case (novo atendimento).
 */
export function resolveAttendanceCaseForWhatsAppInbound(input: CaseRoutingInput): CaseRoutingDecision {
  const c = input.existingCase;
  if (c && c.status === 'handoff') {
    return { action: 'handoff_block', reason: 'case_in_human_handoff', case_id: c.id, conversation_id: input.conversationId };
  }
  if (c && !FINAL_CASE_STATUSES.has(c.status)) {
    return { action: 'reply_existing', reason: 'open_case_continuation', case_id: c.id, conversation_id: input.conversationId };
  }
  if (c && FINAL_CASE_STATUSES.has(c.status)) {
    return { action: 'create_case', reason: 'previous_case_closed_new_attendance', case_id: null, conversation_id: input.conversationId };
  }
  return { action: 'create_case', reason: 'no_existing_case', case_id: null, conversation_id: input.conversationId };
}

/** Subcorredor inferido com segurança a partir do texto (só quando claro). */
export function inferSubcorridorFromText(text?: string | null): string | null {
  const t = (text || '').toLowerCase();
  if (!t) return null;
  const electricalHit = /\b(luz|energia|el[ée]tric|eletric|disjuntor|tomada|curto|fia[çc]|lâmpada|lampada)\b/.test(t);
  const residentialHit = /\b(casa|apartamento|resid[êe]ncia|im[óo]vel|em casa)\b/.test(t);
  if (electricalHit) return 'electrician';
  if (residentialHit) return 'electrician'; // MVP: corredor residencial/eletricista
  return null;
}
