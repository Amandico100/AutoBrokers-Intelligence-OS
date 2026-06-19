// 43P4 — Assisted Real Login Setup state machine. PURO, self-contained.
// Estrutura para o CORRETOR fazer login UMA vez, com aprovação humana e captura
// segura de SessionRef. NUNCA faz login automático, NUNCA executa ação de negócio,
// NUNCA expõe cookie/storageState/OTP. Abertura de browser REAL é gated por flags
// + approval + kill switch off + adapter homologado (inexistente aqui → simulado).

import type { CapturedSessionRef } from '@/lib/attendance/portal-session-capture';

export type LoginSetupStatus =
  | 'draft'
  | 'awaiting_approval'
  | 'ready_to_open_browser'
  | 'browser_opened'
  | 'waiting_human_login'
  | 'challenge_required'
  | 'session_captured'
  | 'session_verified'
  | 'failed'
  | 'cancelled';

export type LoginChallengeKind = 'captcha' | 'otp' | 'mfa_app' | 'certificate' | 'account_locked' | 'unknown';

export interface LoginSetupEvent {
  at: string;
  type: string;
  note?: string | null; // mascarado
}

export interface LoginSetupGateFlags {
  global_kill_switch: boolean; // true = bloqueia
  portal_real_action_enabled: boolean;
  portal_login_real_enabled: boolean;
  portal_session_capture_enabled: boolean;
}

export interface LoginSetupSession {
  setup_id: string;
  portal_id: string;
  portal_account_id: string | null;
  owner_key: string | null;
  journey: 'login';
  provider: string;
  status: LoginSetupStatus;
  next_step: string;
  blockers: string[];
  approval_required: true;
  approval_exists: boolean;
  events: LoginSetupEvent[];
  challenge: { kind: LoginChallengeKind; requires_human: true; bypass_allowed: false; hint: string | null } | null;
  session_ref_masked: string | null;
  session_status: string | null;
  real_browser_opened: false; // SEMPRE false neste batch (sem adapter homologado)
  business_action_allowed: false; // SEMPRE false (login setup ≠ ação de negócio)
  real_action_allowed: false;
}

const _LONG = /\d[\d.\-/\s]{9,}\d/g;
const _OTP = /\b\d{4,8}\b/g;
function mask(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).replace(_LONG, '[num]').replace(_OTP, '[otp]').slice(0, 240);
}
function setupId(): string { return `login-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`; }

const CHALLENGE_MAP: Record<string, LoginChallengeKind> = {
  captcha: 'captcha', recaptcha: 'captcha', otp: 'otp', codigo: 'otp', '2fa': 'mfa_app', mfa: 'mfa_app',
  authenticator: 'mfa_app', certificado: 'certificate', certificate: 'certificate', bloquea: 'account_locked', locked: 'account_locked',
};
function classify(signal: string): LoginChallengeKind {
  const s = (signal || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  for (const [k, v] of Object.entries(CHALLENGE_MAP)) if (s.includes(k)) return v;
  return 'unknown';
}

export interface LoginSetupGateResult {
  allowed: boolean; // pode abrir browser real (precisa flags+approval+saúde)
  session_capture_allowed: boolean;
  blockers: string[];
}

export interface LoginSetupContext {
  flags: LoginSetupGateFlags;
  account_present: boolean;
  credential_present: boolean;
  portal_healthy: boolean;
  approval_exists: boolean;
}

/** Gate de login setup. Falha fechado. PURO. */
export function evaluateLoginSetupGate(ctx: LoginSetupContext): LoginSetupGateResult {
  const blockers: string[] = [];
  if (ctx.flags.global_kill_switch) blockers.push('global_kill_switch_active');
  if (!ctx.flags.portal_real_action_enabled) blockers.push('portal_real_action_disabled');
  if (!ctx.flags.portal_login_real_enabled) blockers.push('portal_login_real_disabled');
  if (!ctx.flags.portal_session_capture_enabled) blockers.push('portal_session_capture_disabled');
  if (!ctx.account_present) blockers.push('no_portal_account');
  if (!ctx.credential_present) blockers.push('no_credential_ref');
  if (!ctx.portal_healthy) blockers.push('portal_not_healthy');
  if (!ctx.approval_exists) blockers.push('no_human_approval');
  return { allowed: blockers.length === 0, session_capture_allowed: blockers.length === 0, blockers };
}

export interface StartLoginSetupInput {
  portal_id: string;
  portal_account_id?: string | null;
  owner_key?: string | null;
  provider?: string;
  context: LoginSetupContext;
}

/** Inicia o login setup. Decide estado pelo gate; NUNCA abre browser real. PURO. */
export function startLoginSetup(input: StartLoginSetupInput): LoginSetupSession {
  const now = new Date().toISOString();
  const gate = evaluateLoginSetupGate(input.context);
  const s: LoginSetupSession = {
    setup_id: setupId(),
    portal_id: input.portal_id,
    portal_account_id: input.portal_account_id ?? null,
    owner_key: input.owner_key ?? null,
    journey: 'login',
    provider: input.provider ?? 'browserbase',
    status: 'draft',
    next_step: 'init',
    blockers: gate.blockers,
    approval_required: true,
    approval_exists: input.context.approval_exists,
    events: [{ at: now, type: 'login_setup_created' }],
    challenge: null,
    session_ref_masked: null,
    session_status: null,
    real_browser_opened: false,
    business_action_allowed: false,
    real_action_allowed: false,
  };

  // Pré-requisitos de conta/credencial/portal faltando → não prossegue.
  const hardMissing = gate.blockers.filter((b) => ['no_portal_account', 'no_credential_ref', 'portal_not_healthy'].includes(b));
  if (hardMissing.length > 0) {
    s.status = 'draft';
    s.next_step = hardMissing.includes('no_portal_account') ? 'create_portal_account' : hardMissing.includes('no_credential_ref') ? 'add_credential_ref' : 'fix_portal_health';
    return s;
  }
  // Flags/kill switch desligando → fica em draft aguardando habilitação segura.
  const flagBlocked = gate.blockers.some((b) => b.includes('kill_switch') || b.includes('disabled'));
  if (flagBlocked) {
    s.status = 'draft';
    s.next_step = 'enable_flags_and_kill_switch_off';
    return s;
  }
  // Falta só aprovação → awaiting_approval.
  if (!input.context.approval_exists) {
    s.status = 'awaiting_approval';
    s.next_step = 'human_approval_required';
    return s;
  }
  // Tudo ok → pronto para abrir (a abertura real é gated/simulada em applyLoginSetupStep).
  s.status = 'ready_to_open_browser';
  s.next_step = 'open_browser';
  return s;
}

/** Aprova o setup (HITL). PURO. */
export function approveLoginSetup(session: LoginSetupSession): LoginSetupSession {
  const now = new Date().toISOString();
  if (session.status !== 'awaiting_approval') return session;
  return { ...session, approval_exists: true, status: 'ready_to_open_browser', next_step: 'open_browser', blockers: session.blockers.filter((b) => b !== 'no_human_approval'), events: [...session.events, { at: now, type: 'approved' }], real_action_allowed: false, business_action_allowed: false, real_browser_opened: false };
}

const TERMINAL: LoginSetupStatus[] = ['session_verified', 'failed', 'cancelled'];

export interface LoginSetupStepInput {
  type: 'open_browser' | 'human_login' | 'challenge' | 'complete' | 'verify' | 'cancel';
  challenge_signal?: string | null;
  captured?: CapturedSessionRef | null; // já mascarado (vem da camada de captura)
  // flag indicando se há adapter de browser REAL homologado (43P4: false)
  real_browser_adapter_available?: boolean;
}

/**
 * Aplica um passo. A abertura de browser REAL exige real_browser_adapter_available
 * (inexistente no 43P4) → permanece SIMULADA (sandbox), sem rede e sem login real.
 */
export function applyLoginSetupStep(session: LoginSetupSession, step: LoginSetupStepInput): LoginSetupSession {
  const now = new Date().toISOString();
  const s: LoginSetupSession = { ...session, events: [...session.events], real_action_allowed: false, business_action_allowed: false, real_browser_opened: false };
  if (TERMINAL.includes(s.status)) {
    s.events.push({ at: now, type: 'event_ignored_terminal', note: step.type });
    return s;
  }
  switch (step.type) {
    case 'cancel':
      s.status = 'cancelled'; s.next_step = 'done';
      s.events.push({ at: now, type: 'cancelled' });
      return s;
    case 'open_browser': {
      if (s.status !== 'ready_to_open_browser') { s.events.push({ at: now, type: 'open_browser_ignored', note: s.status }); return s; }
      // 43P4: sem adapter real homologado → abertura SIMULADA (nenhum browser/URL real).
      s.status = 'browser_opened';
      s.next_step = 'waiting_human_login';
      s.events.push({ at: now, type: step.real_browser_adapter_available ? 'browser_open_blocked_no_real_adapter' : 'browser_opened_sandbox', note: 'nenhum browser real aberto' });
      // imediatamente entra em waiting_human_login (mock)
      s.status = 'waiting_human_login';
      s.events.push({ at: now, type: 'waiting_human_login' });
      return s;
    }
    case 'human_login':
      if (s.status !== 'waiting_human_login') { s.events.push({ at: now, type: 'human_login_ignored', note: s.status }); return s; }
      s.events.push({ at: now, type: 'human_login_signal', note: mask(step.challenge_signal) });
      return s;
    case 'challenge': {
      const kind = classify(step.challenge_signal || 'challenge');
      s.status = 'challenge_required'; s.next_step = 'human_challenge_required';
      s.challenge = { kind, requires_human: true, bypass_allowed: false, hint: mask(step.challenge_signal) };
      s.events.push({ at: now, type: 'challenge_required', note: kind });
      return s;
    }
    case 'complete': {
      if (!step.captured) { s.events.push({ at: now, type: 'complete_ignored_no_capture' }); return s; }
      s.status = 'session_captured';
      s.next_step = 'verify';
      s.session_ref_masked = step.captured.storage_ref_masked;
      s.session_status = step.captured.status;
      s.events.push({ at: now, type: 'session_captured', note: step.captured.session_ref_id });
      return s;
    }
    case 'verify':
      if (s.status !== 'session_captured') { s.events.push({ at: now, type: 'verify_ignored', note: s.status }); return s; }
      s.status = 'session_verified'; s.next_step = 'done';
      s.events.push({ at: now, type: 'session_verified', note: s.session_status });
      return s;
    default:
      s.events.push({ at: now, type: 'unknown_step' });
      return s;
  }
}

const FORBIDDEN = ['password', 'senha', 'token', 'client_token', 'cookie', 'cookies', 'storage_state', 'storagestate', 'otp', 'secret', 'apikey', 'authorization', 'bearer'];
export function findLoginSetupSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (FORBIDDEN.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findLoginSetupSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

export function sanitizeLoginSetup(session: LoginSetupSession): Record<string, unknown> {
  const walk = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === 'object') {
      const o: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (FORBIDDEN.includes(k.toLowerCase())) continue;
        o[k] = walk(val);
      }
      return o;
    }
    return v;
  };
  return walk(session) as Record<string, unknown>;
}
