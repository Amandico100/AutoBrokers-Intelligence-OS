// 43P-FINAL-1 — Portal Browser Real Execution Controller. SELF-CONTAINED
// (sem imports de runtime → testável offline via .mjs; colabora por DI).
// Orquestra o ciclo de vida do canary de LOGIN ASSISTIDO real, falha fechado.
// Segredos (connectUrl/signingKey/cookies/storageState) NUNCA entram na session
// nem são retornados — ficam apenas no closure do transport (server-side, request).

export type CanaryState =
  | 'draft' | 'awaiting_approval' | 'ready_for_canary' | 'browser_opened'
  | 'waiting_human_login' | 'challenge_required' | 'session_capture_pending'
  | 'session_captured' | 'session_verified' | 'failed' | 'aborted' | 'expired' | 'closed';

export interface CanaryEvent { at: string; state: CanaryState; note: string; }

// Resultado da skill read-only (computado pelo módulo de skill; aqui é só anexado).
export interface CanarySkillResultLike {
  ok: boolean; authenticated: boolean; safe_page_label: string | null;
  session_state: string; blockers: string[]; real_action_allowed: false;
}

export interface CanarySession {
  canary_id: string;
  company_id: string;
  portal_id: string;
  portal_account_id: string;
  journey: string;
  mode: 'read_only_canary';
  provider: string;
  state: CanaryState;
  session_id: string | null;       // id Browserbase (não-segredo)
  session_status: string | null;
  region: string | null;
  expires_at: string | null;
  storage_ref: string | null;      // referência opaca do Vault
  session_ref_masked: string | null;
  session_health: 'healthy' | 'expired' | 'challenge_required' | 'unknown' | null;
  challenge_kind: string | null;
  observation: { host: string | null; safe_page_label: string | null; auth_marker_present: boolean; challenge_detected: string | null } | null;
  skill_result: CanarySkillResultLike | null;
  events: CanaryEvent[];
  blockers: string[];
  real_action_allowed: false;
  created_at: string;
  updated_at: string;
}

function now(): string { return new Date().toISOString(); }
function evt(s: CanarySession, state: CanaryState, note: string): CanarySession {
  const e: CanaryEvent = { at: now(), state, note };
  return { ...s, state, events: [...s.events, e], updated_at: e.at };
}
function fail(s: CanarySession, note: string, blocker?: string): CanarySession {
  const out = evt(s, 'failed', note);
  return { ...out, blockers: blocker ? [...out.blockers, blocker] : out.blockers };
}
function maskRef(ref: string | null | undefined): string {
  if (!ref) return '***';
  const s = String(ref);
  return s.length <= 6 ? '***' : `${s.slice(0, 3)}…${s.slice(-3)}`;
}

export interface InitCanaryInput {
  canary_id: string; company_id: string; portal_id: string; portal_account_id: string;
  journey?: string; provider?: string;
}
export function initCanary(input: InitCanaryInput): CanarySession {
  const t = now();
  return {
    canary_id: input.canary_id, company_id: input.company_id, portal_id: input.portal_id,
    portal_account_id: input.portal_account_id, journey: input.journey ?? 'login', mode: 'read_only_canary',
    provider: input.provider ?? 'browserbase', state: 'draft', session_id: null, session_status: null,
    region: null, expires_at: null, storage_ref: null, session_ref_masked: null, session_health: null,
    challenge_kind: null, observation: null, skill_result: null, events: [{ at: t, state: 'draft', note: 'canary_initialized' }],
    blockers: [], real_action_allowed: false, created_at: t, updated_at: t,
  };
}

export function markAwaitingApproval(s: CanarySession): CanarySession {
  if (s.state !== 'draft') return fail(s, 'invalid_transition_awaiting_approval', 'invalid_transition');
  return evt(s, 'awaiting_approval', 'awaiting_human_approval');
}

/** Aplica o resultado da autorização por tenant/approval/gates. */
export function applyAuthorization(s: CanarySession, authorized: boolean, blockers: string[]): CanarySession {
  if (s.state !== 'awaiting_approval' && s.state !== 'draft') return fail(s, 'invalid_transition_authorize', 'invalid_transition');
  if (!authorized) { const o = evt(s, 'awaiting_approval', 'authorization_denied'); return { ...o, blockers }; }
  return evt({ ...s, blockers: [] }, 'ready_for_canary', 'authorized_for_canary');
}

export interface CanaryBrowserOpenResult { ok: boolean; session_id: string | null; session_status: string | null; region: string | null; expires_at: string | null; blockers: string[]; reason: string; }
export interface CanaryBrowserTransport {
  open: () => Promise<CanaryBrowserOpenResult>; // wraps createBrowserbaseLoginSession; connectUrl fica no closure do transport
  close: (sessionId: string) => Promise<{ closed: boolean }>;
}

/** Abre o browser real SÓ se autorizado e readiness permitir. Sem rede caso contrário. */
export async function openCanaryBrowser(s: CanarySession, readinessCanOpen: boolean, transport: CanaryBrowserTransport): Promise<CanarySession> {
  if (s.state !== 'ready_for_canary') return fail(s, 'invalid_transition_open', 'invalid_transition');
  if (!readinessCanOpen) return fail(s, 'browser_blocked_by_gate', 'browserbase_not_ready'); // NÃO chama transport
  const r = await transport.open();
  if (!r.ok) { const o = fail(s, `browser_open_failed:${r.reason}`); return { ...o, blockers: [...o.blockers, ...r.blockers] }; }
  const opened = evt({ ...s, session_id: r.session_id, session_status: r.session_status, region: r.region, expires_at: r.expires_at }, 'browser_opened', 'browser_opened');
  return evt(opened, 'waiting_human_login', 'waiting_human_login'); // humano digita credenciais
}

export function markChallenge(s: CanarySession, kind: string): CanarySession {
  if (s.state !== 'waiting_human_login' && s.state !== 'browser_opened') return fail(s, 'invalid_transition_challenge', 'invalid_transition');
  return evt({ ...s, challenge_kind: kind }, 'challenge_required', `challenge_${kind}`); // NUNCA persiste OTP/segredo
}
export function resolveChallenge(s: CanarySession): CanarySession {
  if (s.state !== 'challenge_required') return fail(s, 'invalid_transition_resolve_challenge', 'invalid_transition');
  return evt({ ...s, challenge_kind: null }, 'waiting_human_login', 'challenge_resolved_by_human');
}

// Vault DI (mesma forma de PortalSessionVaultAdapter; aqui definido local p/ self-containment).
export interface CanaryVaultAdapter {
  available: () => Promise<boolean>;
  write: (input: { company_id: string; portal_account_id: string; provider: string; secret_payload: unknown }) => Promise<{ ok: boolean; storage_ref: string | null; reason: string }>;
}
export const canaryFailClosedVault: CanaryVaultAdapter = { available: async () => false, write: async () => ({ ok: false, storage_ref: null, reason: 'vault_unavailable' }) };

export interface CanaryCaptureInput {
  storage_payload: unknown; status?: 'healthy' | 'expired' | 'challenge_required' | 'unknown';
}
/** Captura após login humano. storageState real vai SÓ pro Vault (falha fechada). */
export async function captureCanarySession(s: CanarySession, input: CanaryCaptureInput, vault: CanaryVaultAdapter = canaryFailClosedVault): Promise<CanarySession> {
  if (s.state !== 'waiting_human_login') return fail(s, 'invalid_transition_capture', 'invalid_transition');
  const pending = evt(s, 'session_capture_pending', 'capturing_session');
  const ok = await vault.available();
  if (!ok) return fail(pending, 'capture_failed:vault_unavailable', 'vault_unavailable');
  const w = await vault.write({ company_id: s.company_id, portal_account_id: s.portal_account_id, provider: s.provider, secret_payload: input.storage_payload });
  if (!w.ok || !w.storage_ref) return fail(pending, `capture_failed:${w.reason}`, w.reason);
  // storage_ref nunca pode parecer segredo.
  if (/cookie|storagestate|connecturl|signingkey|token|authorization/i.test(w.storage_ref)) return fail(pending, 'capture_failed:vault_ref_unsafe', 'vault_ref_unsafe');
  return evt({ ...pending, storage_ref: w.storage_ref, session_ref_masked: maskRef(w.storage_ref), session_health: input.status ?? 'healthy' }, 'session_captured', 'session_captured');
}

/**
 * Registra a captura quando o storageState JÁ foi gravado no Vault server-side
 * (rota CDP+Vault) e só temos a referência opaca. NÃO recebe segredo.
 */
export function recordCanaryCapture(s: CanarySession, storageRef: string | null, status: 'healthy' | 'expired' | 'challenge_required' | 'unknown' = 'healthy'): CanarySession {
  if (s.state !== 'waiting_human_login') return fail(s, 'invalid_transition_record_capture', 'invalid_transition');
  if (!storageRef) return fail(evt(s, 'session_capture_pending', 'capturing_session'), 'capture_failed:no_storage_ref', 'no_storage_ref');
  if (/cookie|storagestate|connecturl|signingkey|token|authorization/i.test(storageRef)) return fail(s, 'capture_failed:vault_ref_unsafe', 'vault_ref_unsafe');
  const pending = evt(s, 'session_capture_pending', 'capturing_session');
  return evt({ ...pending, storage_ref: storageRef, session_ref_masked: maskRef(storageRef), session_health: status }, 'session_captured', 'session_captured');
}

/** Anexa a observação CDP sanitizada (sem segredo/DOM bruto). */
export function setCanaryObservation(s: CanarySession, obs: { host: string | null; safe_page_label: string | null; auth_marker_present: boolean; challenge_detected: string | null }): CanarySession {
  return { ...s, observation: obs, updated_at: now() };
}

/** Verifica a SessionRef por metadados (sem ler conteúdo). */
export function verifyCanarySession(s: CanarySession, nowMs: number = Date.now()): CanarySession {
  if (s.state !== 'session_captured') return fail(s, 'invalid_transition_verify', 'invalid_transition');
  if (s.session_health === 'challenge_required') { const o = fail(s, 'verify_failed:challenge_required', 'challenge_required'); return o; }
  if (s.expires_at && Date.parse(s.expires_at) <= nowMs) { const o = fail(s, 'verify_failed:expired', 'expired'); return { ...o, session_health: 'expired' }; }
  if (s.session_health !== 'healthy') { const o = fail(s, 'verify_failed:needs_check', 'needs_check'); return { ...o, session_health: 'unknown' }; }
  return evt({ ...s, session_health: 'healthy' }, 'session_verified', 'session_verified');
}

/** Anexa o resultado da skill read-only (computada pelo módulo de skill via DI). SÓ com sessão verificada. */
export function attachReadOnlySkillResult(s: CanarySession, skillResult: CanarySkillResultLike): CanarySession {
  if (s.state !== 'session_verified') return fail(s, 'invalid_transition_skill', 'invalid_transition');
  if (skillResult.real_action_allowed !== false) return fail(s, 'skill_not_read_only', 'skill_not_read_only');
  return { ...s, skill_result: skillResult, updated_at: now() };
}

export async function abortCanary(s: CanarySession, close?: (sessionId: string) => Promise<{ closed: boolean }>): Promise<CanarySession> {
  if (s.session_id && close) { try { await close(s.session_id); } catch { /* fecha best-effort */ } }
  return evt(s, 'aborted', 'canary_aborted');
}
export function expireCanary(s: CanarySession): CanarySession { return evt({ ...s, session_health: 'expired' }, 'expired', 'canary_expired'); }
export function closeCanary(s: CanarySession): CanarySession { return evt(s, 'closed', 'canary_closed'); }

const CANARY_FORBIDDEN = ['connecturl', 'connect_url', 'signingkey', 'signing_key', 'cookie', 'cookies', 'storagestate', 'storage_state', 'token', 'authorization', 'apikey', 'api_key', 'seleniumremoteurl', 'liveurl', 'otp', 'password'];
export function findCanarySecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (CANARY_FORBIDDEN.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findCanarySecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

/** Visão segura do canary para frontend (sem segredo; storage_ref só mascarado). */
export function sanitizeCanary(s: CanarySession): Record<string, unknown> {
  return {
    canary_id: s.canary_id, company_id: s.company_id, portal_id: s.portal_id, portal_account_id: s.portal_account_id,
    journey: s.journey, mode: s.mode, provider: s.provider, state: s.state, session_id: s.session_id,
    session_status: s.session_status, region: s.region, expires_at: s.expires_at,
    session_ref_masked: s.session_ref_masked, session_health: s.session_health, challenge_kind: s.challenge_kind,
    observation: s.observation, skill_result: s.skill_result, events: s.events, blockers: s.blockers, real_action_allowed: false,
    created_at: s.created_at, updated_at: s.updated_at,
  };
}
