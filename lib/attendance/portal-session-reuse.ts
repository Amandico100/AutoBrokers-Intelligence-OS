// 43P-FINAL-2A — reuso seguro de SessionRef (independente do canary original).
// SELF-CONTAINED (DI) → testável offline. Prova o ciclo:
//   Portal Account → SessionRef → Vault read (memória) → nova sessão →
//   restore autenticado → observação read-only → skill → descarte do segredo.
// O segredo (storageState) NUNCA aparece no resultado/log; só transita em memória.

export interface ReuseSessionRef {
  storage_ref: string | null;   // ref opaca COMPLETA (server-side)
  status: string;               // healthy|expired|challenge_required|reauth_required|revoked|unknown
  expires_at: string | null;
  portal_id: string;
  portal_account_id: string;
}

export interface ReuseAuthz { authorized: boolean; blockers: string[] }

export interface ReuseObservation { host: string | null; safe_page_label: string | null; auth_marker_present: boolean; challenge_detected: string | null }

export interface ReuseDeps {
  // Lê o segredo do Vault (server-side, em memória).
  vaultRead: (storageRef: string) => Promise<{ ok: boolean; secret_payload: unknown | null; reason: string }>;
  // Abre nova sessão Browserbase e restaura o estado; retorna SÓ observação sanitizada.
  restoreAndObserve: (storagePayload: unknown) => Promise<{ ok: boolean; observation: ReuseObservation | null; reason: string }>;
  // Skill read-only sobre a observação; retorna output já sem segredo/PII.
  runSkill: (observation: ReuseObservation | null) => { ok: boolean; authenticated: boolean; safe_page_label: string | null; session_state: string; blockers: string[]; real_action_allowed: false };
}

export interface ReuseResult {
  ok: boolean;
  reused: boolean;
  reason: string;
  session_state: string;
  observation: ReuseObservation | null;
  skill_result: { ok: boolean; authenticated: boolean; safe_page_label: string | null; session_state: string; blockers: string[]; real_action_allowed: false } | null;
  blockers: string[];
  real_action_allowed: false;
}

export async function reuseSessionRefForReadOnly(
  sessionRef: ReuseSessionRef | null,
  authz: ReuseAuthz,
  deps: ReuseDeps,
  now: number = Date.now(),
): Promise<ReuseResult> {
  const fail = (reason: string, blockers: string[] = [], session_state = 'unknown'): ReuseResult =>
    ({ ok: false, reused: false, reason, session_state, observation: null, skill_result: null, blockers, real_action_allowed: false });

  if (!authz.authorized) return fail('not_authorized', authz.blockers);
  if (!sessionRef) return fail('session_ref_missing');
  if (sessionRef.status === 'revoked') return fail('session_revoked', ['session_revoked'], 'revoked');
  if (sessionRef.status === 'reauth_required') return fail('reauth_required', ['reauth_required'], 'reauth_required');
  if (sessionRef.expires_at && Date.parse(sessionRef.expires_at) <= now) return fail('session_expired', ['session_expired'], 'expired');
  if (sessionRef.status !== 'healthy') return fail('session_not_healthy', [`session_${sessionRef.status}`], sessionRef.status);
  if (!sessionRef.storage_ref) return fail('storage_ref_missing');

  // 1) Lê o segredo do Vault (em memória).
  const v = await deps.vaultRead(sessionRef.storage_ref);
  if (!v.ok || !v.secret_payload) return fail(`vault_read_failed:${v.reason}`, ['vault_unavailable']);

  // 2) Nova sessão + restore + observação (segredo só transita aqui).
  const r = await deps.restoreAndObserve(v.secret_payload);
  if (!r.ok) return fail(`restore_failed:${r.reason}`, ['restore_failed'], 'unknown');
  if (r.observation?.challenge_detected) {
    return { ok: false, reused: true, reason: 'challenge_required', session_state: 'challenge_required', observation: r.observation, skill_result: null, blockers: [`challenge_${r.observation.challenge_detected}`], real_action_allowed: false };
  }

  // 3) Skill read-only.
  const skill = deps.runSkill(r.observation);

  const result: ReuseResult = {
    ok: skill.ok, reused: true, reason: skill.ok ? 'reused_ok' : 'skill_blocked',
    session_state: 'healthy', observation: r.observation, skill_result: skill, blockers: skill.blockers, real_action_allowed: false,
  };
  // Defesa: o resultado NUNCA pode conter segredo.
  if (findReuseSecrets(result).length > 0) return fail('secret_leak_blocked', ['secret_leak']);
  return result;
}

const REUSE_FORBIDDEN = ['storagestate', 'storage_state', 'cookie', 'cookies', 'connecturl', 'connect_url', 'signingkey', 'signing_key', 'token', 'authorization', 'apikey', 'api_key', 'secret_payload'];
export function findReuseSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (REUSE_FORBIDDEN.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findReuseSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}
