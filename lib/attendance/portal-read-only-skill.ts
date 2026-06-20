// 43P-FINAL-1 — primeira Portal Skill REAL read-only: session_login_verify.
// SELF-CONTAINED. Apenas confirma estado pós-login (autenticado/healthy) com
// rótulo de página sanitizado. NUNCA navega para negócio, submete formulário,
// consulta CPF/apólice, baixa documento, abre sinistro/assistência ou envia nada.

export interface ReadOnlySkillContract {
  skill_key: 'session_login_verify';
  mode: 'read_only';
  required_session_state: 'healthy';
  host_allowlist: string[]; // hosts permitidos para o portal
  forbidden_actions: string[];
  min_quality_for_canary: 'sandbox_validated';
}

export function getSessionLoginVerifyContract(hostAllowlist: string[]): ReadOnlySkillContract {
  return {
    skill_key: 'session_login_verify',
    mode: 'read_only',
    required_session_state: 'healthy',
    host_allowlist: hostAllowlist,
    forbidden_actions: [
      'submit_form', 'navigate_business_flow', 'query_cpf', 'fetch_policy',
      'download_document', 'open_claim', 'open_assistance', 'send_message', 'mutate_state',
    ],
    min_quality_for_canary: 'sandbox_validated',
  };
}

// Observação coletada server-side (via CDP). Apenas metadados não sensíveis.
export interface PageObservation {
  host: string | null;
  page_title: string | null; // título bruto (pode conter PII → será sanitizado/descartado)
  auth_marker_present: boolean; // marcador visual não sensível de autenticação
  challenge_detected?: string | null; // captcha|otp|mfa|null
}

export interface SessionLoginVerifyInput {
  portal_id: string;
  session_state: 'healthy' | 'expired' | 'challenge_required' | string;
  has_session_ref: boolean;
  authorized: boolean; // gate + approval + tenant já validados
  observation: PageObservation | null;
  contract: ReadOnlySkillContract;
  observed_at?: string;
}

export interface SessionLoginVerifyOutput {
  ok: boolean;
  authenticated: boolean;
  portal_id: string;
  safe_page_label: string | null;
  session_state: 'healthy' | 'expired' | 'challenge_required' | 'unknown';
  observed_at: string;
  blockers: string[];
  real_action_allowed: false;
}

const PII_HINTS = ['cpf', 'cnpj', 'apólice', 'apolice', 'policy', 'rg', 'nascimento', '@'];

/** Rótulo de página seguro: descarta se contém indício de PII ou dígitos longos. */
export function toSafePageLabel(title: string | null | undefined): string | null {
  if (!title) return null;
  const t = String(title).trim();
  if (!t) return null;
  const strip = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const lower = strip(t);
  if (PII_HINTS.some((h) => lower.includes(strip(h)))) return null;
  if (/\d{5,}/.test(t)) return null; // sequência longa de dígitos → descarta
  return t.slice(0, 80);
}

export function runSessionLoginVerify(input: SessionLoginVerifyInput): SessionLoginVerifyOutput {
  const observedAt = input.observed_at ?? new Date().toISOString();
  const blockers: string[] = [];
  if (!input.authorized) blockers.push('not_authorized');
  if (!input.has_session_ref) blockers.push('session_ref_missing');
  if (input.contract.mode !== 'read_only') blockers.push('skill_not_read_only');
  if (input.session_state !== 'healthy') blockers.push(`session_state_${input.session_state}`);

  const obs = input.observation;
  // Host allowlist é obrigatório.
  if (obs?.host && input.contract.host_allowlist.length > 0 && !input.contract.host_allowlist.includes(obs.host)) {
    blockers.push('host_not_allowed');
  }
  if (obs?.challenge_detected) blockers.push(`challenge_${obs.challenge_detected}`);

  const base: SessionLoginVerifyOutput = {
    ok: false, authenticated: false, portal_id: input.portal_id,
    safe_page_label: null, session_state: 'unknown', observed_at: observedAt,
    blockers, real_action_allowed: false,
  };
  if (blockers.length > 0) return base;

  return {
    ok: true,
    authenticated: Boolean(obs?.auth_marker_present),
    portal_id: input.portal_id,
    safe_page_label: toSafePageLabel(obs?.page_title),
    session_state: 'healthy',
    observed_at: observedAt,
    blockers: [],
    real_action_allowed: false,
  };
}

const OUT_FORBIDDEN = ['cookie', 'cookies', 'storagestate', 'storage_state', 'connecturl', 'signingkey', 'token', 'authorization', 'apikey', 'api_key', 'dom', 'html', 'cpf', 'cnpj'];
export function findSkillOutputSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (OUT_FORBIDDEN.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findSkillOutputSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}
