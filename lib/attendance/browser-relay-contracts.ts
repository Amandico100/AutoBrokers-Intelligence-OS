// 43P0 — Browser Relay contracts. PURO, self-contained. NENHUM browser real.
// Modela a sessão de relay (recon/sandbox/dry_run), eventos, challenges (CAPTCHA/
// 2FA → HITL, nunca bypass), trace e o gate de promoção para ação real.
// external_action_sent/real_action_allowed são SEMPRE false neste estágio.

export type BrowserRelayMode = 'recon' | 'sandbox' | 'dry_run' | 'real_future';
export type BrowserProvider = 'browserbase' | 'local_playwright' | 'skyvern';
export type BrowserRelayStatus =
  | 'created'
  | 'waiting_session'
  | 'running'
  | 'challenge_required'
  | 'waiting_human'
  | 'completed_dry_run'
  | 'failed'
  | 'cancelled';

export type PortalChallengeKind = 'captcha' | 'otp' | 'mfa_app' | 'certificate' | 'token' | 'account_locked' | 'unknown';

export interface PortalChallenge {
  kind: PortalChallengeKind;
  requires_human: true; // SEMPRE
  bypass_allowed: false; // SEMPRE
  detected_hint: string; // dica mascarada, NUNCA o token/OTP em si
}

export interface BrowserRelayEvent {
  at: string;
  type: string;
  note?: string | null; // mascarado
  page_ref?: string | null; // referência/URL-pattern, sem query sensível
}

export interface BrowserRelaySession {
  relay_session_id: string;
  mode: BrowserRelayMode;
  portal_id: string;
  portal_skill_id: string | null;
  action_candidate_id: string | null;
  browser_provider: BrowserProvider;
  status: BrowserRelayStatus;
  events: BrowserRelayEvent[];
  challenge: PortalChallenge | null;
  trace_ref: string | null; // referência ao trace (NUNCA screenshots crus)
  replay_ref: string | null;
  outputs: Record<string, unknown> | null; // sanitizado
  external_action_sent: false; // SEMPRE
}

export interface PortalTraceSummary {
  relay_session_id: string;
  portal_id: string;
  event_count: number;
  challenge_kind: PortalChallengeKind | null;
  last_status: BrowserRelayStatus;
  trace_ref: string | null;
  has_pii: false; // sanitizado por construção
}

// --- mascaramento -----------------------------------------------------------
const _LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
const _OTP = /\b\d{4,8}\b/g;
function maskRelay(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).replace(_LONG_DIGITS, '[omitido]').replace(_OTP, '[otp]').slice(0, 280);
}
function relayId(): string {
  return `relay-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export interface CreateRelaySessionInput {
  portal_id: string;
  portal_skill_id?: string | null;
  action_candidate_id?: string | null;
  browser_provider?: BrowserProvider;
  mode?: BrowserRelayMode;
}

/** Cria uma BrowserRelaySession. Default sandbox; nunca real_future neste batch. */
export function createBrowserRelaySession(input: CreateRelaySessionInput): BrowserRelaySession {
  const now = new Date().toISOString();
  // 43P0 trava qualquer modo "real_future" → rebaixa para sandbox.
  const requested = input.mode ?? 'sandbox';
  const mode: BrowserRelayMode = requested === 'real_future' ? 'sandbox' : requested;
  return {
    relay_session_id: relayId(),
    mode,
    portal_id: input.portal_id,
    portal_skill_id: input.portal_skill_id ?? null,
    action_candidate_id: input.action_candidate_id ?? null,
    browser_provider: input.browser_provider ?? 'browserbase',
    status: 'created',
    events: [{ at: now, type: 'session_created', note: `mode=${mode}` }],
    challenge: null,
    trace_ref: null,
    replay_ref: null,
    outputs: null,
    external_action_sent: false,
  };
}

const CHALLENGE_MAP: Record<string, PortalChallengeKind> = {
  captcha: 'captcha', recaptcha: 'captcha', hcaptcha: 'captcha',
  otp: 'otp', 'one-time': 'otp', codigo: 'otp',
  '2fa': 'mfa_app', mfa: 'mfa_app', authenticator: 'mfa_app',
  certificate: 'certificate', certificado: 'certificate', e_cnpj: 'certificate',
  token: 'token',
  locked: 'account_locked', bloquea: 'account_locked', blocked: 'account_locked',
};

/**
 * Classifica um sinal de challenge. SEMPRE exige humano e NUNCA permite bypass.
 * O hint é mascarado (sem OTP/token cru). PURO.
 */
export function classifyChallenge(signal: string): PortalChallenge {
  const s = (signal || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  let kind: PortalChallengeKind = 'unknown';
  for (const [needle, k] of Object.entries(CHALLENGE_MAP)) {
    if (s.includes(needle)) { kind = k; break; }
  }
  return { kind, requires_human: true, bypass_allowed: false, detected_hint: maskRelay(signal) ?? 'challenge' };
}

export interface RelayEventInput {
  type: 'navigated' | 'observed' | 'extracted' | 'challenge_detected' | 'human_note' | 'session_loaded' | 'dry_run_step' | 'cancel' | 'completed';
  note?: string;
  page_ref?: string;
  challenge_signal?: string;
}

const TERMINAL: BrowserRelayStatus[] = ['completed_dry_run', 'failed', 'cancelled'];

/** Aplica um evento à sessão de relay (PURO). NUNCA envia/executa real. */
export function applyRelayEvent(session: BrowserRelaySession, event: RelayEventInput): BrowserRelaySession {
  const now = new Date().toISOString();
  const s: BrowserRelaySession = { ...session, events: [...session.events], external_action_sent: false };
  if (TERMINAL.includes(s.status)) {
    s.events.push({ at: now, type: 'event_ignored_terminal', note: event.type });
    return s;
  }
  switch (event.type) {
    case 'cancel':
      s.status = 'cancelled';
      s.events.push({ at: now, type: 'cancelled' });
      return s;
    case 'challenge_detected': {
      const ch = classifyChallenge(event.challenge_signal || event.note || 'challenge');
      s.status = 'challenge_required';
      s.challenge = ch;
      s.events.push({ at: now, type: 'challenge_detected', note: ch.kind, page_ref: maskRelay(event.page_ref) });
      return s;
    }
    case 'session_loaded':
      s.status = 'running';
      s.events.push({ at: now, type: 'session_loaded', note: maskRelay(event.note) });
      return s;
    case 'navigated':
    case 'observed':
    case 'extracted':
    case 'dry_run_step':
      s.status = 'running';
      s.events.push({ at: now, type: event.type, note: maskRelay(event.note), page_ref: maskRelay(event.page_ref) });
      return s;
    case 'human_note':
      s.events.push({ at: now, type: 'human_note', note: maskRelay(event.note) });
      return s;
    case 'completed':
      // No 43P0 só existe conclusão dry-run (nunca real).
      s.status = 'completed_dry_run';
      s.events.push({ at: now, type: 'completed_dry_run' });
      return s;
    default:
      s.events.push({ at: now, type: 'unknown_event' });
      return s;
  }
}

/** Resumo de trace seguro (sem PII/screenshot cru). */
export function buildTraceSummary(session: BrowserRelaySession): PortalTraceSummary {
  return {
    relay_session_id: session.relay_session_id,
    portal_id: session.portal_id,
    event_count: session.events.length,
    challenge_kind: session.challenge?.kind ?? null,
    last_status: session.status,
    trace_ref: session.trace_ref ?? null,
    has_pii: false,
  };
}

// --- Promotion gate (sandbox → real) ----------------------------------------
export interface PromotionGateContext {
  portal_status: string | null; // PortalDefinition.status
  skill_promotion: string | null; // PortalSkill.promotion_status
  has_credential_ref: boolean;
  has_session_ref: boolean;
  session_healthy: boolean;
  dry_run_passed: boolean;
  trace_available: boolean;
  replay_available: boolean;
  eval_passed: boolean;
  approval_exists: boolean;
  kill_switch_off: boolean;
  real_flag_enabled: boolean; // PORTAL_REAL_ACTION_ENABLED
}

export interface PromotionGateResult {
  real_action_allowed: false; // SEMPRE false no 43P0
  gates: Record<string, boolean>;
  blockers: string[];
  reason: string;
}

/**
 * Avalia o gate de promoção para ação real. No 43P0 o resultado é SEMPRE
 * real_action_allowed=false (tipo literal), mas modela cada gate para o futuro.
 */
export function evaluatePortalPromotionGate(ctx: PromotionGateContext): PromotionGateResult {
  const gates: Record<string, boolean> = {
    real_flag_enabled: ctx.real_flag_enabled === true,
    portal_approved: ctx.portal_status === 'approved_future',
    skill_approved: ctx.skill_promotion === 'approved_future',
    credential_present: ctx.has_credential_ref === true,
    session_present: ctx.has_session_ref === true,
    session_healthy: ctx.session_healthy === true,
    dry_run_passed: ctx.dry_run_passed === true,
    trace_available: ctx.trace_available === true,
    replay_available: ctx.replay_available === true,
    eval_passed: ctx.eval_passed === true,
    approval_exists: ctx.approval_exists === true,
    kill_switch_off: ctx.kill_switch_off === true,
  };
  const blockers = Object.entries(gates).filter(([, ok]) => !ok).map(([k]) => k);
  return {
    real_action_allowed: false,
    gates,
    blockers,
    reason: blockers.length > 0 ? `blocked_by:${blockers.join(',')}` : 'real_action_disabled_43p0',
  };
}
