// 43P2 — Browser Relay Runtime Sandbox. PURO, self-contained. NENHUM browser
// real, URL real ou credencial real. Conduz uma sessão de relay em sandbox
// usando um BrowserRelayProviderAdapter (injetado — DI, sem cross-import em
// runtime) e produz trace/replay sanitizados. real_action_allowed sempre false.

import type { BrowserRelayProviderAdapter, RelayProviderKey } from '@/lib/attendance/browser-relay-adapters';

export type RelayRuntimeStatus =
  | 'draft'
  | 'ready'
  | 'running_sandbox'
  | 'observing'
  | 'acting'
  | 'extracting'
  | 'challenge_required'
  | 'waiting_human'
  | 'completed_sandbox'
  | 'failed_sandbox'
  | 'cancelled';

export type RelayChallengeKind = 'captcha' | 'otp' | 'mfa_app' | 'certificate' | 'account_locked' | 'session_expired' | 'unknown';

export interface RelayRuntimeEvent {
  at: string;
  type: string;
  note?: string | null; // mascarado
  provider?: RelayProviderKey | null;
}

export interface RelayRuntimeSession {
  relay_id: string;
  portal_id: string | null;
  portal_account_id: string | null;
  journey: string | null;
  provider: RelayProviderKey;
  mode: 'sandbox';
  status: RelayRuntimeStatus;
  next_step: string;
  blockers: string[];
  events: RelayRuntimeEvent[];
  observed_states: Array<Record<string, unknown>>;
  actions: Array<Record<string, unknown>>;
  extracted_data: Array<Record<string, unknown>>;
  challenges: Array<{ kind: RelayChallengeKind; requires_human: true; bypass_allowed: false; hint: string | null }>;
  redactions: string[];
  outcome: string | null;
  real_action_allowed: false;
  external_action_sent: false;
}

const _LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
const _OTP = /\b\d{4,8}\b/g;
function maskRelay(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).replace(_LONG_DIGITS, '[omitido]').replace(_OTP, '[otp]').slice(0, 280);
}
function relayId(): string {
  return `prelay-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

const CHALLENGE_MAP: Record<string, RelayChallengeKind> = {
  captcha: 'captcha', recaptcha: 'captcha', hcaptcha: 'captcha',
  otp: 'otp', codigo: 'otp', 'one-time': 'otp',
  '2fa': 'mfa_app', mfa: 'mfa_app', authenticator: 'mfa_app',
  certificate: 'certificate', certificado: 'certificate', e_cnpj: 'certificate',
  locked: 'account_locked', bloquea: 'account_locked', blocked: 'account_locked',
  expired: 'session_expired', expirada: 'session_expired', expirou: 'session_expired',
};
function classifyRelayChallenge(signal: string): RelayChallengeKind {
  // Insensível a acento (ex.: "código" → "codigo").
  const s = (signal || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  for (const [needle, kind] of Object.entries(CHALLENGE_MAP)) if (s.includes(needle)) return kind;
  return 'unknown';
}

const TERMINAL: RelayRuntimeStatus[] = ['completed_sandbox', 'failed_sandbox', 'cancelled'];

export interface StartRelayInput {
  portal_id: string | null;
  portal_account_id?: string | null;
  journey?: string | null;
  provider: RelayProviderKey;
  // pré-condições resolvidas pela rota (a partir de resolvePortalCanonical + conta):
  portal_available: boolean;
  account_present: boolean;
  session_status?: string | null; // healthy|expired|challenge_required|unknown
  session_ref_masked?: string | null;
  allow_demo_without_account?: boolean;
}

/**
 * Inicia a sessão de relay sandbox. Usa o adapter (DI) só se chegar a
 * running_sandbox. NUNCA abre browser real. PURO.
 */
export function startBrowserRelaySandbox(input: StartRelayInput, adapter: BrowserRelayProviderAdapter): RelayRuntimeSession {
  const now = new Date().toISOString();
  const s: RelayRuntimeSession = {
    relay_id: relayId(),
    portal_id: input.portal_id,
    portal_account_id: input.portal_account_id ?? null,
    journey: input.journey ?? null,
    provider: input.provider,
    mode: 'sandbox',
    status: 'draft',
    next_step: 'init',
    blockers: [],
    events: [{ at: now, type: 'relay_created', note: `provider=${input.provider}`, provider: input.provider }],
    observed_states: [],
    actions: [],
    extracted_data: [],
    challenges: [],
    redactions: [],
    outcome: null,
    real_action_allowed: false,
    external_action_sent: false,
  };

  if (!input.portal_available || !input.portal_id) {
    s.status = 'failed_sandbox'; s.next_step = 'no_portal_definition'; s.blockers.push('no_portal_definition');
    s.events.push({ at: now, type: 'blocked', note: 'no_portal_definition' });
    return s;
  }
  if (!input.account_present && !input.allow_demo_without_account) {
    s.status = 'draft'; s.next_step = 'create_portal_account'; s.blockers.push('no_portal_account');
    s.events.push({ at: now, type: 'blocked', note: 'create_portal_account' });
    return s;
  }
  if (input.session_status === 'expired' || input.session_status === 'challenge_required') {
    s.status = 'challenge_required'; s.next_step = 'human_challenge_required';
    s.challenges.push({ kind: input.session_status === 'expired' ? 'session_expired' : 'unknown', requires_human: true, bypass_allowed: false, hint: input.session_status });
    s.events.push({ at: now, type: 'challenge_required', note: input.session_status });
    return s;
  }

  // OK → abre sessão mock no adapter (sem browser real).
  const created = adapter.createSession({ relay_id: s.relay_id, portal_id: input.portal_id, journey: input.journey ?? null, session_ref_masked: input.session_ref_masked ?? null });
  s.status = 'running_sandbox';
  s.next_step = 'observe';
  s.events.push({ at: now, type: 'session_opened_mock', note: created.reason, provider: input.provider });
  if (input.allow_demo_without_account && !input.account_present) s.redactions.push('demo_without_account');
  return s;
}

export interface RelayStepInput {
  type: 'observe' | 'act' | 'extract' | 'challenge' | 'human_note' | 'cancel' | 'complete';
  instruction?: string | null;
  selector_hint?: string | null;
  query?: string | null;
  challenge_signal?: string | null;
}

/** Aplica um passo à sessão sandbox usando o adapter (DI). PURO. NUNCA real. */
export function applyBrowserRelaySandboxStep(
  session: RelayRuntimeSession,
  step: RelayStepInput,
  adapter: BrowserRelayProviderAdapter,
): RelayRuntimeSession {
  const now = new Date().toISOString();
  const s: RelayRuntimeSession = {
    ...session,
    events: [...session.events], observed_states: [...session.observed_states], actions: [...session.actions],
    extracted_data: [...session.extracted_data], challenges: [...session.challenges], redactions: [...session.redactions],
    real_action_allowed: false, external_action_sent: false,
  };
  if (TERMINAL.includes(s.status)) {
    s.events.push({ at: now, type: 'event_ignored_terminal', note: step.type });
    return s;
  }
  const sess = { relay_id: s.relay_id, portal_id: s.portal_id ?? '', journey: s.journey, session_ref_masked: null };

  switch (step.type) {
    case 'cancel':
      s.status = 'cancelled'; s.next_step = 'done'; s.outcome = 'cancelled';
      s.events.push({ at: now, type: 'cancelled' });
      return s;
    case 'complete':
      s.status = 'completed_sandbox'; s.next_step = 'done'; s.outcome = 'completed_dry_run';
      s.events.push({ at: now, type: 'completed_sandbox' });
      return s;
    case 'human_note':
      s.events.push({ at: now, type: 'human_note', note: maskRelay(step.instruction) });
      return s;
    case 'observe': {
      const r = adapter.observe(sess, { instruction: step.instruction, selector_hint: step.selector_hint });
      s.status = 'observing'; s.next_step = 'act_or_extract';
      s.observed_states.push({ at: now, ...(r.data ?? {}) });
      s.events.push({ at: now, type: 'observe', note: maskRelay(r.reason), provider: s.provider });
      return s;
    }
    case 'act': {
      const r = adapter.act(sess, { instruction: step.instruction, selector_hint: step.selector_hint });
      s.status = 'acting'; s.next_step = 'observe_or_extract';
      s.actions.push({ at: now, instruction: maskRelay(step.instruction), performed: false, ...(r.data ?? {}) });
      s.events.push({ at: now, type: 'act', note: maskRelay(r.reason), provider: s.provider });
      return s;
    }
    case 'extract': {
      const r = adapter.extract(sess, { query: step.query });
      s.status = 'extracting'; s.next_step = 'complete_or_continue';
      s.extracted_data.push({ at: now, query: maskRelay(step.query), ...(r.data ?? {}) });
      s.events.push({ at: now, type: 'extract', note: maskRelay(r.reason), provider: s.provider });
      return s;
    }
    case 'challenge': {
      const kind = classifyRelayChallenge(step.challenge_signal || step.instruction || 'challenge');
      s.status = 'challenge_required'; s.next_step = 'human_challenge_required';
      s.challenges.push({ kind, requires_human: true, bypass_allowed: false, hint: maskRelay(step.challenge_signal || step.instruction) });
      s.events.push({ at: now, type: 'challenge_required', note: kind });
      return s;
    }
    default:
      s.events.push({ at: now, type: 'unknown_step' });
      return s;
  }
}

// --- trace / replay ---------------------------------------------------------
export interface RelayTrace {
  relay_id: string;
  portal_id: string | null;
  journey: string | null;
  provider: RelayProviderKey;
  steps: RelayRuntimeEvent[];
  observed_states_count: number;
  actions_count: number;
  extracted_count: number;
  challenges: Array<{ kind: RelayChallengeKind; requires_human: true }>;
  outcome: string | null;
  has_pii: false;
  real_action_allowed: false;
}

export function buildRelayTrace(session: RelayRuntimeSession): RelayTrace {
  return {
    relay_id: session.relay_id,
    portal_id: session.portal_id,
    journey: session.journey,
    provider: session.provider,
    steps: session.events.map((e) => ({ at: e.at, type: e.type, note: maskRelay(e.note), provider: e.provider ?? null })),
    observed_states_count: session.observed_states.length,
    actions_count: session.actions.length,
    extracted_count: session.extracted_data.length,
    challenges: session.challenges.map((c) => ({ kind: c.kind, requires_human: true })),
    outcome: session.outcome,
    has_pii: false,
    real_action_allowed: false,
  };
}

export interface RelayReplay {
  relay_id: string;
  provider: RelayProviderKey;
  timeline: Array<{ step: number; at: string; type: string; note: string | null }>;
  final_status: RelayRuntimeStatus;
  has_pii: false;
}

export function buildRelayReplay(session: RelayRuntimeSession): RelayReplay {
  return {
    relay_id: session.relay_id,
    provider: session.provider,
    timeline: session.events.map((e, i) => ({ step: i + 1, at: e.at, type: e.type, note: maskRelay(e.note) })),
    final_status: session.status,
    has_pii: false,
  };
}

/** Garante saída sanitizada (sem chaves de segredo) para resposta pública. */
export function sanitizeRelayRuntimeOutput(output: unknown): unknown {
  const FORBIDDEN = ['password', 'senha', 'token', 'client_token', 'cookie', 'cookies', 'storage_state', 'storagestate', 'otp', 'secret', 'apikey', 'authorization', 'bearer'];
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
    if (typeof v === 'string') return maskRelay(v);
    return v;
  };
  return walk(output);
}

export function findRelaySecrets(obj: unknown, path = ''): string[] {
  const FORBIDDEN = ['password', 'senha', 'client_token', 'cookie', 'cookies', 'storage_state', 'storagestate', 'secret', 'apikey', 'authorization', 'bearer', 'private_key'];
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (FORBIDDEN.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findRelaySecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}
