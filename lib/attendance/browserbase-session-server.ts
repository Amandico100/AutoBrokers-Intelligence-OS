// 43P-FINAL-2 — acesso server-side à sessão Browserbase. SELF-CONTAINED (DI).
// Persiste SÓ session_id + metadados não-sensíveis. O connectUrl é obtido em
// memória (GET /v1/sessions/{id}) APENAS no request que precisa do CDP, passado
// a um callback e descartado — NUNCA retornado, persistido ou logado.
//
// Browserbase API (verificado em 43P4.1 + docs/reference/api/get-a-session):
//   POST  /v1/sessions            → { id, connectUrl, signingKey, status, region, expiresAt }
//   GET   /v1/sessions/{id}       → { id, status, region, expiresAt, connectUrl? }
//   POST  /v1/sessions/{id}       { status:'REQUEST_RELEASE' } → encerra

export const BB_API_BASE = 'https://api.browserbase.com';

export interface BBServerEnv { BROWSERBASE_API_KEY?: string; BROWSERBASE_PROJECT_ID?: string }
export interface BBSessionMeta { session_id: string | null; status: string | null; region: string | null; expires_at: string | null }

export interface BBServerTransport {
  create: (a: { apiKey: string; projectId: string; metadata?: Record<string, unknown> }) => Promise<Record<string, any>>;
  get: (a: { apiKey: string; sessionId: string }) => Promise<Record<string, any>>;
  close: (a: { apiKey: string; projectId: string; sessionId: string }) => Promise<Record<string, any>>;
}

export const realBBServerTransport: BBServerTransport = {
  create: async ({ apiKey, projectId, metadata }) => {
    const res = await fetch(`${BB_API_BASE}/v1/sessions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-BB-API-Key': apiKey },
      body: JSON.stringify(metadata ? { projectId, userMetadata: metadata } : { projectId }),
    });
    if (!res.ok) throw new Error(`browserbase_http_${res.status}`);
    return res.json();
  },
  get: async ({ apiKey, sessionId }) => {
    const res = await fetch(`${BB_API_BASE}/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'GET', headers: { 'X-BB-API-Key': apiKey },
    });
    if (!res.ok) throw new Error(`browserbase_http_${res.status}`);
    return res.json();
  },
  close: async ({ apiKey, projectId, sessionId }) => {
    const res = await fetch(`${BB_API_BASE}/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-BB-API-Key': apiKey },
      body: JSON.stringify({ projectId, status: 'REQUEST_RELEASE' }),
    });
    return res.ok ? res.json().catch(() => ({})) : {};
  },
};

function metaFrom(raw: Record<string, any>): BBSessionMeta {
  return { session_id: raw?.id ?? null, status: raw?.status ?? null, region: raw?.region ?? null, expires_at: raw?.expiresAt ?? raw?.expires_at ?? null };
}
function extractConnectUrl(raw: Record<string, any>): string | null {
  return raw?.connectUrl ?? raw?.connect_url ?? null; // SEGREDO — só em memória
}

export async function createBrowserbaseSessionServer(env: BBServerEnv, transport: BBServerTransport = realBBServerTransport, metadata?: Record<string, unknown>): Promise<BBSessionMeta> {
  const apiKey = String(env.BROWSERBASE_API_KEY ?? ''); const projectId = String(env.BROWSERBASE_PROJECT_ID ?? '');
  if (!apiKey || !projectId) throw new Error('browserbase_env_missing');
  const raw = await transport.create({ apiKey, projectId, metadata });
  return metaFrom(raw); // connectUrl/signingKey descartados
}

export async function getBrowserbaseSessionMeta(sessionId: string, env: BBServerEnv, transport: BBServerTransport = realBBServerTransport): Promise<BBSessionMeta> {
  const apiKey = String(env.BROWSERBASE_API_KEY ?? '');
  if (!apiKey || !sessionId) throw new Error('browserbase_env_or_session_missing');
  return metaFrom(await transport.get({ apiKey, sessionId }));
}

/**
 * Obtém o connectUrl em MEMÓRIA pelo session_id, executa `fn` (CDP) e descarta o
 * connectUrl. O connectUrl NUNCA é retornado/persistido. Resultado de `fn` é
 * varrido contra segredos antes de retornar.
 */
export async function withBrowserbaseConnectUrl<T>(
  sessionId: string, env: BBServerEnv, fn: (connectUrl: string) => Promise<T>, transport: BBServerTransport = realBBServerTransport,
): Promise<{ ok: boolean; reason: string; result: T | null }> {
  const apiKey = String(env.BROWSERBASE_API_KEY ?? '');
  if (!apiKey || !sessionId) return { ok: false, reason: 'browserbase_env_or_session_missing', result: null };
  let raw: Record<string, any>;
  try { raw = await transport.get({ apiKey, sessionId }); } catch (e: any) { return { ok: false, reason: `browserbase_get_failed:${String(e?.message || 'unknown').slice(0, 40)}`, result: null }; }
  const connectUrl = extractConnectUrl(raw);
  if (!connectUrl) return { ok: false, reason: 'connect_url_unavailable', result: null };
  let result: T;
  try { result = await fn(connectUrl); } catch (e: any) { return { ok: false, reason: `cdp_callback_failed:${String(e?.message || 'unknown').slice(0, 40)}`, result: null }; }
  // Defesa: o resultado nunca pode conter segredo.
  if (findServerSecrets(result).length > 0) return { ok: false, reason: 'secret_leak_blocked', result: null };
  return { ok: true, reason: 'ok', result };
}

export async function closeBrowserbaseSessionServer(sessionId: string, env: BBServerEnv, transport: BBServerTransport = realBBServerTransport): Promise<{ closed: boolean }> {
  const apiKey = String(env.BROWSERBASE_API_KEY ?? ''); const projectId = String(env.BROWSERBASE_PROJECT_ID ?? '');
  if (!apiKey || !projectId || !sessionId) return { closed: false };
  try { await transport.close({ apiKey, projectId, sessionId }); return { closed: true }; } catch { return { closed: false }; }
}

export const BB_SECRET_KEYS = ['connecturl', 'connect_url', 'signingkey', 'signing_key', 'seleniumremoteurl', 'debuggerurl', 'debuggerfullscreenurl', 'wsurl', 'ws_url', 'cookie', 'cookies', 'storagestate', 'storage_state', 'token', 'authorization', 'apikey', 'api_key', 'x-bb-api-key'];
export function findServerSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (BB_SECRET_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findServerSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}
