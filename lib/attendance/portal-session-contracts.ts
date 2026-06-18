// 43P0 — CredentialRef & SessionRef contracts. PURO, self-contained.
// NUNCA carrega segredo: senha/token/cookie/storageState/OTP ficam no Vault e
// só são referenciados por uma ref opaca. Sanitização garante que nada sensível
// vaze para prompt/contexto/resposta pública.

export type CredentialRefStatus = 'missing' | 'configured' | 'needs_rotation' | 'revoked';
export type SessionRefStatus = 'healthy' | 'expired' | 'challenge_required' | 'revoked' | 'unknown';
export type BrowserProvider = 'browserbase' | 'local_playwright' | 'skyvern' | 'other';

export interface CredentialRef {
  credential_ref_id: string;
  company_id: string;
  portal_id: string;
  account_label: string; // rótulo legível, NUNCA o usuário/senha
  vault_ref: string; // referência opaca ao segredo no Vault
  status: CredentialRefStatus;
  last_verified_at?: string | null;
}

export interface SessionRef {
  session_ref_id: string;
  company_id: string;
  portal_id: string;
  credential_ref_id?: string | null;
  storage_ref: string; // referência opaca ao storageState criptografado (NUNCA o conteúdo)
  browser_provider: BrowserProvider;
  status: SessionRefStatus;
  expires_at?: string | null;
  last_health_check_at?: string | null;
}

// Campos que NUNCA podem existir nestes contratos.
export const SESSION_FORBIDDEN_KEYS = [
  'password', 'senha', 'username', 'user', 'login', 'token', 'client_token',
  'cookie', 'cookies', 'storage_state', 'storagestate', 'otp', 'mfa_code',
  'captcha_token', 'authorization', 'secret', 'private_key', 'certificate_pem', 'bearer',
];

function maskRef(ref: string | null | undefined): string | null {
  if (!ref) return null;
  const s = String(ref);
  if (s.length <= 6) return '***';
  return `${s.slice(0, 3)}…${s.slice(-3)}`;
}

/** Procura recursivamente campos proibidos (segredo/credencial). PURO. */
export function findSessionForbiddenKeys(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (SESSION_FORBIDDEN_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findSessionForbiddenKeys(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

export interface BuildCredentialRefInput {
  credential_ref_id?: string;
  company_id: string;
  portal_id: string;
  account_label: string;
  vault_ref: string;
  status?: CredentialRefStatus;
}

/** Cria uma CredentialRef. Rejeita (lança) se o input contiver segredo cru. */
export function buildCredentialRef(input: BuildCredentialRefInput): CredentialRef {
  const leak = findSessionForbiddenKeys(input);
  if (leak.length > 0) throw new Error(`credential_ref_secret_leak:${leak.join(',')}`);
  return {
    credential_ref_id: input.credential_ref_id ?? `cred-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    company_id: input.company_id,
    portal_id: input.portal_id,
    account_label: input.account_label,
    vault_ref: input.vault_ref,
    status: input.status ?? 'configured',
    last_verified_at: null,
  };
}

export interface BuildSessionRefInput {
  session_ref_id?: string;
  company_id: string;
  portal_id: string;
  credential_ref_id?: string | null;
  storage_ref: string;
  browser_provider: BrowserProvider;
  status?: SessionRefStatus;
  expires_at?: string | null;
}

/** Cria uma SessionRef. Rejeita (lança) se o input contiver cookie/storageState cru. */
export function buildSessionRef(input: BuildSessionRefInput): SessionRef {
  const leak = findSessionForbiddenKeys(input);
  if (leak.length > 0) throw new Error(`session_ref_secret_leak:${leak.join(',')}`);
  return {
    session_ref_id: input.session_ref_id ?? `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    company_id: input.company_id,
    portal_id: input.portal_id,
    credential_ref_id: input.credential_ref_id ?? null,
    storage_ref: input.storage_ref,
    browser_provider: input.browser_provider,
    status: input.status ?? 'unknown',
    expires_at: input.expires_at ?? null,
    last_health_check_at: null,
  };
}

/** Versão sanitizada para resposta pública: vault_ref/storage_ref mascarados, sem segredo. */
export function sanitizeCredentialRef(ref: CredentialRef): Record<string, unknown> {
  return {
    credential_ref_id: ref.credential_ref_id,
    company_id: ref.company_id,
    portal_id: ref.portal_id,
    account_label: ref.account_label,
    vault_ref_masked: maskRef(ref.vault_ref),
    status: ref.status,
    last_verified_at: ref.last_verified_at ?? null,
  };
}

export function sanitizeSessionRef(ref: SessionRef): Record<string, unknown> {
  return {
    session_ref_id: ref.session_ref_id,
    company_id: ref.company_id,
    portal_id: ref.portal_id,
    credential_ref_id: ref.credential_ref_id ?? null,
    storage_ref_masked: maskRef(ref.storage_ref),
    browser_provider: ref.browser_provider,
    status: ref.status,
    expires_at: ref.expires_at ?? null,
    last_health_check_at: ref.last_health_check_at ?? null,
  };
}

export interface SessionHealthResult {
  status: SessionRefStatus;
  usable: boolean;
  requires_human: boolean;
  reason: string;
}

/**
 * Avalia a saúde de uma SessionRef SEM acessar a sessão real (apenas metadados:
 * status + expiração). Em 43P0 nunca há acesso real ao storageState.
 */
export function evaluateSessionHealth(ref: SessionRef, now: number = Date.now()): SessionHealthResult {
  if (ref.status === 'revoked') return { status: 'revoked', usable: false, requires_human: true, reason: 'session_revoked' };
  if (ref.status === 'challenge_required') return { status: 'challenge_required', usable: false, requires_human: true, reason: 'challenge_required' };
  if (ref.expires_at && new Date(ref.expires_at).getTime() <= now) {
    return { status: 'expired', usable: false, requires_human: true, reason: 'session_expired' };
  }
  if (ref.status === 'healthy') return { status: 'healthy', usable: true, requires_human: false, reason: 'session_healthy' };
  return { status: 'unknown', usable: false, requires_human: true, reason: 'session_unknown_needs_health_check' };
}
