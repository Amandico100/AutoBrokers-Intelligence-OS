// 43P4 — Secure SessionRef Capture. PURO, self-contained. Recebe SOMENTE uma
// referência opaca (storage_ref) ao storageState criptografado no Vault — NUNCA
// cookies/headers/storageState crus, OTP, token ou senha. Produz uma SessionRef
// mascarada e avalia saúde só por metadados. Nenhum acesso real a portal.

export type CapturedSessionStatus = 'healthy' | 'expired' | 'challenge_required' | 'revoked' | 'unknown';
export type CaptureProvider = 'browserbase' | 'local_playwright' | 'skyvern_lab' | 'unknown';

export interface CapturedSessionRef {
  session_ref_id: string;
  portal_id: string;
  portal_account_id: string | null;
  storage_ref_masked: string; // NUNCA o conteúdo
  provider: CaptureProvider;
  status: CapturedSessionStatus;
  captured_at: string;
  expires_at: string | null;
  last_checked_at: string | null;
}

// Campos crus que NUNCA podem chegar nesta camada.
export const CAPTURE_FORBIDDEN_KEYS = [
  'password', 'senha', 'token', 'client_token', 'access_token', 'cookie', 'cookies',
  'storage_state', 'storagestate', 'otp', 'mfa_code', 'code', 'secret', 'apikey',
  'authorization', 'bearer', 'headers', 'set-cookie',
];

export function findCaptureSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (CAPTURE_FORBIDDEN_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findCaptureSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

function maskRef(ref: string | null | undefined): string {
  if (!ref) return '***';
  const s = String(ref);
  if (s.length <= 6) return '***';
  return `${s.slice(0, 3)}…${s.slice(-3)}`;
}

export interface CaptureSessionInput {
  portal_id: string;
  portal_account_id?: string | null;
  storage_ref: string; // ref opaca ao Vault (nunca o storageState)
  provider?: CaptureProvider;
  status?: CapturedSessionStatus;
  expires_at?: string | null;
}

/** Captura uma SessionRef a partir de ref opaca. LANÇA se receber segredo cru. PURO. */
export function captureSessionRef(input: CaptureSessionInput): CapturedSessionRef {
  const leak = findCaptureSecrets(input);
  if (leak.length > 0) throw new Error(`session_capture_secret_leak:${leak.join(',')}`);
  if (!input.storage_ref) throw new Error('missing_storage_ref');
  const now = new Date().toISOString();
  return {
    session_ref_id: `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    portal_id: input.portal_id,
    portal_account_id: input.portal_account_id ?? null,
    storage_ref_masked: maskRef(input.storage_ref),
    provider: input.provider ?? 'browserbase',
    status: input.status ?? 'healthy',
    captured_at: now,
    expires_at: input.expires_at ?? null,
    last_checked_at: null,
  };
}

export interface SessionVerifyResult {
  status: CapturedSessionStatus;
  usable: boolean;
  requires_human: boolean;
  checked_at: string;
  reason: string;
}

/** Verifica saúde da SessionRef SÓ por metadados (sem acessar a sessão real). PURO. */
export function verifyCapturedSession(ref: CapturedSessionRef, now: number = Date.now()): SessionVerifyResult {
  const checked_at = new Date(now).toISOString();
  if (ref.status === 'revoked') return { status: 'revoked', usable: false, requires_human: true, checked_at, reason: 'revoked' };
  if (ref.status === 'challenge_required') return { status: 'challenge_required', usable: false, requires_human: true, checked_at, reason: 'challenge_required' };
  if (ref.expires_at && new Date(ref.expires_at).getTime() <= now) {
    return { status: 'expired', usable: false, requires_human: true, checked_at, reason: 'expired' };
  }
  if (ref.status === 'healthy') return { status: 'healthy', usable: true, requires_human: false, checked_at, reason: 'healthy' };
  return { status: 'unknown', usable: false, requires_human: true, checked_at, reason: 'needs_check' };
}

/** Versão pública sanitizada (garante ausência de campo sensível). */
export function sanitizeCapturedSessionRef(ref: CapturedSessionRef): Record<string, unknown> {
  return {
    session_ref_id: ref.session_ref_id,
    portal_id: ref.portal_id,
    portal_account_id: ref.portal_account_id ?? null,
    storage_ref_masked: ref.storage_ref_masked,
    provider: ref.provider,
    status: ref.status,
    captured_at: ref.captured_at,
    expires_at: ref.expires_at ?? null,
    last_checked_at: ref.last_checked_at ?? null,
  };
}
