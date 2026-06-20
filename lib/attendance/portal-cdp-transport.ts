// 43P-FINAL-2 — CDP transport server-side (Playwright connectOverCDP). NÃO
// self-contained (server-only); NUNCA importado por testes .mjs.
//
// SEGURANÇA:
// - Recebe connectUrl APENAS como argumento em memória (do withBrowserbaseConnectUrl);
//   nunca persiste/loga/retorna connectUrl.
// - observeViaCdp: read-only (host/título/marcador/challenge).
// - captureStorageStateViaCdp: obtém storageState SÓ em memória; quem chama deve
//   gravá-lo direto no Vault dentro do mesmo closure e descartar.
// - Nunca executa ação de negócio, nunca digita credencial, nunca resolve CAPTCHA.

export interface CdpObservation {
  available: boolean;
  host: string | null;
  page_title: string | null; // bruto; o módulo de skill sanitiza/descarta PII
  auth_marker_present: boolean;
  challenge_detected: string | null;
  reason: string;
}

export interface CdpOptions {
  auth_marker_selectors?: string[];
  challenge_selectors?: { kind: string; selector: string }[];
  timeout_ms?: number;
}

async function loadPlaywright(): Promise<any | null> {
  try {
    const spec = 'playwright-core';
    const mod: any = await import(/* webpackIgnore: true */ spec).catch(() => null);
    return mod?.chromium ? mod : null;
  } catch {
    return null;
  }
}

async function connectFirstPage(pw: any, connectUrl: string, timeout: number): Promise<{ browser: any; page: any }> {
  const browser = await pw.chromium.connectOverCDP(connectUrl, { timeout });
  const ctx = browser.contexts()[0] ?? (await browser.newContext());
  const page = ctx.pages()[0] ?? (await ctx.newPage());
  return { browser, page };
}
async function detect(page: any, opts: CdpOptions): Promise<{ host: string | null; title: string | null; authMarker: boolean; challenge: string | null }> {
  let host: string | null = null; try { host = new URL(page.url()).host; } catch { host = null; }
  let title: string | null = null; try { title = await page.title(); } catch { title = null; }
  let authMarker = false;
  for (const sel of opts.auth_marker_selectors ?? []) { try { if (await page.locator(sel).first().count()) { authMarker = true; break; } } catch { /* ignora */ } }
  let challenge: string | null = null;
  for (const c of opts.challenge_selectors ?? []) { try { if (await page.locator(c.selector).first().count()) { challenge = c.kind; break; } } catch { /* ignora */ } }
  return { host, title, authMarker, challenge };
}

/** Observa a sessão (read-only). NÃO retorna segredo/DOM bruto. */
export async function observeViaCdp(connectUrl: string, opts: CdpOptions = {}): Promise<CdpObservation> {
  const base: CdpObservation = { available: false, host: null, page_title: null, auth_marker_present: false, challenge_detected: null, reason: 'unknown' };
  if (!connectUrl) return { ...base, reason: 'connect_url_missing' };
  const pw = await loadPlaywright();
  if (!pw) return { ...base, reason: 'playwright_not_available' };
  let browser: any = null;
  try {
    const c = await connectFirstPage(pw, connectUrl, opts.timeout_ms ?? 20000);
    browser = c.browser;
    const d = await detect(c.page, opts);
    return { available: true, host: d.host, page_title: d.title, auth_marker_present: d.authMarker, challenge_detected: d.challenge, reason: 'observed' };
  } catch (e: any) {
    return { ...base, reason: `cdp_error:${String(e?.message || 'unknown').slice(0, 60)}` };
  } finally {
    try { if (browser) await browser.close(); } catch { /* desconecta best-effort; não encerra a sessão remota */ }
  }
}

export interface CdpCaptureResult {
  ok: boolean;
  challenge_detected: string | null;
  host: string | null;
  page_title: string | null;
  storage_payload: unknown | null; // SÓ em memória — quem chama grava no Vault e descarta
  reason: string;
}

/** Captura storageState SÓ em memória. Se houver challenge, NÃO captura. */
export async function captureStorageStateViaCdp(connectUrl: string, opts: CdpOptions = {}): Promise<CdpCaptureResult> {
  const base: CdpCaptureResult = { ok: false, challenge_detected: null, host: null, page_title: null, storage_payload: null, reason: 'unknown' };
  if (!connectUrl) return { ...base, reason: 'connect_url_missing' };
  const pw = await loadPlaywright();
  if (!pw) return { ...base, reason: 'playwright_not_available' };
  let browser: any = null;
  try {
    const c = await connectFirstPage(pw, connectUrl, opts.timeout_ms ?? 20000);
    browser = c.browser;
    const d = await detect(c.page, opts);
    if (d.challenge) return { ...base, challenge_detected: d.challenge, host: d.host, page_title: d.title, reason: 'challenge_required' };
    const ctx = c.page.context();
    const storage = await ctx.storageState(); // SEGREDO — fica só aqui
    return { ok: true, challenge_detected: null, host: d.host, page_title: d.title, storage_payload: storage, reason: 'captured' };
  } catch (e: any) {
    return { ...base, reason: `cdp_error:${String(e?.message || 'unknown').slice(0, 60)}` };
  } finally {
    try { if (browser) await browser.close(); } catch { /* best-effort */ }
  }
}
