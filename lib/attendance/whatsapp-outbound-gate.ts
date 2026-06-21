// 42X5B — política CANÔNICA de envio WhatsApp outbound. SELF-CONTAINED (DI).
// Resolve TODA a ambiguidade entre flags num único lugar. O backend (webhook
// Python) obedece ao `external_send_allowed`/`dry_run` que o bridge Next retorna,
// então esta é a fonte única da verdade de envio. Falha fechado: qualquer
// requisito ausente → dry_run (nunca envia).
//
// Flags compostas pelo chamador (env + production-gates):
//   global_kill_switch              (GLOBAL_KILL_SWITCH)
//   attendance_dry_run             (ATTENDANCE_WHATSAPP_DRY_RUN !== 'false')
//   outbound_real_enabled          (WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED)
//   external_action_real_enabled   (EXTERNAL_ACTION_REAL_ENABLED — production gate)
//   insurer_whatsapp_real_enabled  (INSURER_WHATSAPP_REAL_SEND_ENABLED — só canal seguradora)

export interface WhatsAppOutboundContext {
  global_kill_switch: boolean;
  attendance_dry_run: boolean;
  outbound_real_enabled: boolean;
  external_action_real_enabled: boolean;
  insurer_whatsapp_real_enabled?: boolean;
  external_send_authorized: boolean; // autorização explícita por requisição
  consent_ok: boolean;               // do evaluator de consentimento
  approval_ok: boolean;              // HITL para envio proativo
  is_proactive: boolean;            // proativo/campanha vs resposta a inbound
  channel?: 'customer_whatsapp' | 'insurer_whatsapp' | string | null;
  environment?: string | null;       // 'sandbox' força dry-run
}

export interface WhatsAppOutboundDecision {
  dry_run: boolean;
  external_send_allowed: boolean;
  blockers: string[];
}

export function evaluateWhatsAppOutboundGate(ctx: WhatsAppOutboundContext): WhatsAppOutboundDecision {
  const blockers: string[] = [];
  if (ctx.global_kill_switch) blockers.push('global_kill_switch_active');
  if ((ctx.environment || '').toLowerCase() === 'sandbox') blockers.push('sandbox_environment');
  if (ctx.attendance_dry_run) blockers.push('attendance_dry_run_on');
  if (!ctx.outbound_real_enabled) blockers.push('whatsapp_outbound_real_disabled');
  if (!ctx.external_action_real_enabled) blockers.push('external_action_real_disabled');
  if (ctx.channel === 'insurer_whatsapp' && !ctx.insurer_whatsapp_real_enabled) blockers.push('insurer_whatsapp_real_send_disabled');
  if (!ctx.external_send_authorized) blockers.push('external_send_not_authorized');
  if (!ctx.consent_ok) blockers.push('consent_missing');
  if (ctx.is_proactive && !ctx.approval_ok) blockers.push('approval_required');

  const allowed = blockers.length === 0;
  return { dry_run: !allowed, external_send_allowed: allowed, blockers };
}
