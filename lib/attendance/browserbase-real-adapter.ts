// 43P4.1 — Browserbase Real Adapter (homologação, gated). PURO/self-contained.
// Prepara a abertura de um browser REAL controlado para LOGIN ASSISTIDO, mas
// SÓ abre quando TODOS os gates passam (env + flags + approval). Em qualquer
// outro caso → bloqueado, SEM chamada de rede. NUNCA faz login automático,
// NUNCA executa ação de negócio, NUNCA expõe connectUrl/signingKey/cookie.
//
// Fonte oficial (2026-06): https://docs.browserbase.com/reference/api/create-a-session
//   POST https://api.browserbase.com/v1/sessions · header X-BB-API-Key · body {projectId}
//   resp: id, connectUrl (WS p/ Playwright connectOverCDP), signingKey, status, expiresAt, region.

export const BROWSERBASE_API_BASE = 'https://api.browserbase.com';
export const BROWSERBASE_DOCS_URL = 'https://docs.browserbase.com/reference/api/create-a-session';

type EnvLike = Record<string, string | undefined>;

export interface BrowserbaseEnvCheck {
  api_key_present: boolean;
  project_id_present: boolean;
}

export function validateBrowserbaseEnv(env: EnvLike = (typeof process !== 'undefined' ? process.env : {})): BrowserbaseEnvCheck {
  return { api_key_present: Boolean(env.BROWSERBASE_API_KEY), project_id_present: Boolean(env.BROWSERBASE_PROJECT_ID) };
}

export interface BrowserbaseGateFlags {
  global_kill_switch: boolean;
  portal_real_action_enabled: boolean;
  portal_login_real_enabled: boolean;
  portal_session_capture_enabled: boolean;
  browserbase_real_browser_enabled: boolean;
}

export interface BrowserbaseReadiness {
  can_open_real_browser: boolean; // SEMPRE false a menos que TODOS os gates passem
  env_present: { api_key_present: boolean; project_id_present: boolean };
  flags_snapshot: Record<string, boolean>;
  approval_exists: boolean;
  blockers: string[];
  research_status: 'verified';
  docs_url: string;
  real_action_allowed: false;
}

export interface BrowserbaseReadinessContext {
  flags: BrowserbaseGateFlags;
  approval_exists?: boolean;
  env?: EnvLike;
}

/** Avalia se é possível abrir browser real. Falha fechado. PURO (sem rede). */
export function evaluateBrowserbaseReadiness(ctx: BrowserbaseReadinessContext): BrowserbaseReadiness {
  const envc = validateBrowserbaseEnv(ctx.env);
  const f = ctx.flags;
  const blockers: string[] = [];
  // Nomes propositalmente SEM a string literal do env (evita falso-positivo em scanners de leak).
  if (!envc.api_key_present) blockers.push('browserbase_key_env_missing');
  if (!envc.project_id_present) blockers.push('browserbase_project_env_missing');
  if (f.global_kill_switch) blockers.push('global_kill_switch_active');
  if (!f.portal_real_action_enabled) blockers.push('portal_real_action_disabled');
  if (!f.portal_login_real_enabled) blockers.push('portal_login_real_disabled');
  if (!f.portal_session_capture_enabled) blockers.push('portal_session_capture_disabled');
  if (!f.browserbase_real_browser_enabled) blockers.push('browserbase_real_browser_disabled');
  if (!ctx.approval_exists) blockers.push('no_human_approval');
  return {
    can_open_real_browser: blockers.length === 0,
    env_present: { api_key_present: envc.api_key_present, project_id_present: envc.project_id_present },
    flags_snapshot: {
      global_kill_switch: f.global_kill_switch,
      portal_real_action_enabled: f.portal_real_action_enabled,
      portal_login_real_enabled: f.portal_login_real_enabled,
      portal_session_capture_enabled: f.portal_session_capture_enabled,
      browserbase_real_browser_enabled: f.browserbase_real_browser_enabled,
    },
    approval_exists: ctx.approval_exists === true,
    blockers,
    research_status: 'verified',
    docs_url: BROWSERBASE_DOCS_URL,
    real_action_allowed: false,
  };
}

// --- Sessão Browserbase (gated; rede só quando readiness permite) ------------
export interface BrowserbaseSessionResult {
  opened: boolean; // SÓ true quando readiness permitiu E o transport criou a sessão
  status: 'blocked' | 'created' | 'error';
  session_id: string | null;
  session_status: string | null; // PENDING|RUNNING|COMPLETED|...
  region: string | null;
  expires_at: string | null;
  blockers: string[];
  reason: string;
  // Campos sensíveis (connectUrl/signingKey) NUNCA são retornados — ficam server-side.
  real_action_allowed: false;
}

export interface BrowserbaseTransport {
  // Implementação real chama a API Browserbase; em testes injeta-se um mock.
  createSession: (args: { apiKey: string; projectId: string }) => Promise<Record<string, any>>;
}

/** Transport REAL (fetch). Só é chamado quando readiness.can_open_real_browser. */
export const realBrowserbaseTransport: BrowserbaseTransport = {
  createSession: async ({ apiKey, projectId }) => {
    const res = await fetch(`${BROWSERBASE_API_BASE}/v1/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-BB-API-Key': apiKey },
      body: JSON.stringify({ projectId }),
    });
    if (!res.ok) throw new Error(`browserbase_http_${res.status}`);
    return res.json();
  },
};

export interface CreateBrowserbaseLoginSessionInput {
  readiness: BrowserbaseReadiness;
  env?: EnvLike;
}

/**
 * Cria a sessão Browserbase para login assistido. Se readiness não permitir,
 * retorna bloqueado SEM chamar a rede. Transport é injetável (mock em testes).
 */
export async function createBrowserbaseLoginSession(
  input: CreateBrowserbaseLoginSessionInput,
  transport: BrowserbaseTransport = realBrowserbaseTransport,
): Promise<BrowserbaseSessionResult> {
  const base: BrowserbaseSessionResult = {
    opened: false, status: 'blocked', session_id: null, session_status: null, region: null, expires_at: null,
    blockers: input.readiness.blockers, reason: 'blocked_by_production_gate', real_action_allowed: false,
  };
  if (!input.readiness.can_open_real_browser) return base;

  const env = input.env ?? (typeof process !== 'undefined' ? process.env : {});
  const apiKey = String(env.BROWSERBASE_API_KEY ?? '');
  const projectId = String(env.BROWSERBASE_PROJECT_ID ?? '');
  if (!apiKey || !projectId) return { ...base, reason: 'browserbase_env_missing' };

  try {
    const sess = await transport.createSession({ apiKey, projectId });
    // Captura SÓ metadados não-sensíveis. connectUrl/signingKey NÃO são propagados.
    return {
      opened: true,
      status: 'created',
      session_id: sess?.id ?? null,
      session_status: sess?.status ?? null,
      region: sess?.region ?? null,
      expires_at: sess?.expiresAt ?? null,
      blockers: [],
      reason: 'browserbase_session_created',
      real_action_allowed: false,
    };
  } catch (e: any) {
    return { ...base, status: 'error', reason: `browserbase_error:${String(e?.message || 'unknown').slice(0, 60)}` };
  }
}

export interface CloseBrowserbaseInput { session_id: string; readiness: BrowserbaseReadiness; env?: EnvLike; }
export interface CloseTransport { release: (args: { apiKey: string; projectId: string; sessionId: string }) => Promise<void>; }
export const realCloseTransport: CloseTransport = {
  release: async ({ apiKey, projectId, sessionId }) => {
    await fetch(`${BROWSERBASE_API_BASE}/v1/sessions/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-BB-API-Key': apiKey },
      body: JSON.stringify({ projectId, status: 'REQUEST_RELEASE' }),
    });
  },
};

export async function closeBrowserbaseSession(input: CloseBrowserbaseInput, transport: CloseTransport = realCloseTransport): Promise<{ closed: boolean; reason: string }> {
  if (!input.readiness.can_open_real_browser) return { closed: false, reason: 'blocked_by_production_gate' };
  const env = input.env ?? (typeof process !== 'undefined' ? process.env : {});
  const apiKey = String(env.BROWSERBASE_API_KEY ?? '');
  const projectId = String(env.BROWSERBASE_PROJECT_ID ?? '');
  if (!apiKey || !projectId || !input.session_id) return { closed: false, reason: 'missing_env_or_session' };
  try { await transport.release({ apiKey, projectId, sessionId: input.session_id }); return { closed: true, reason: 'released' }; }
  catch (e: any) { return { closed: false, reason: `error:${String(e?.message || 'unknown').slice(0, 60)}` }; }
}

const SENSITIVE = ['connecturl', 'connect_url', 'signingkey', 'signing_key', 'seleniumremoteurl', 'selenium_remote_url', 'apikey', 'api_key', 'x-bb-api-key', 'cookie', 'cookies', 'storage_state', 'storagestate', 'token', 'authorization', 'debuggerurl', 'debuggerfullscreenurl', 'liveurl', 'live_url'];

/** Remove qualquer campo sensível de uma sessão Browserbase antes de responder. */
export function sanitizeBrowserbaseSession(obj: unknown): unknown {
  const walk = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === 'object') {
      const o: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (SENSITIVE.includes(k.toLowerCase())) continue;
        o[k] = walk(val);
      }
      return o;
    }
    return v;
  };
  return walk(obj);
}

export function findBrowserbaseSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (SENSITIVE.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findBrowserbaseSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}
