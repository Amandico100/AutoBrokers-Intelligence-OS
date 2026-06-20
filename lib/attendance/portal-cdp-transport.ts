// 43P-FINAL-1 — CDP transport server-side (Playwright connectOverCDP) para o
// canary real. NÃO self-contained (server-only); NUNCA importado por testes .mjs.
//
// SEGURANÇA:
// - connectUrl/signingKey ficam SÓ neste closure server-side; nunca retornam.
// - playwright-core é OPCIONAL: import lazy com fallback fail-closed. O build NÃO
//   depende dele. Batch 2: `npm install playwright-core` para ativar o canary real.
// - Esta camada só OBSERVA (read-only): título/host/marcador de auth/challenge.
//   Nunca executa ação de negócio, nunca digita credencial, nunca resolve CAPTCHA.

export interface CdpObservation {
  available: boolean;
  host: string | null;
  page_title: string | null; // bruto; o módulo de skill sanitiza/descarta PII
  auth_marker_present: boolean;
  challenge_detected: string | null;
  reason: string;
}

export interface CdpVerifyInput {
  connect_url: string;          // SEGREDO — fica só aqui (server-side)
  auth_marker_selectors?: string[]; // seletores não sensíveis que indicam login ok
  challenge_selectors?: { kind: string; selector: string }[];
  timeout_ms?: number;
}

/**
 * Carrega playwright-core de forma lazy/opcional. Fail-closed se ausente.
 * Specifier por variável + webpackIgnore: o build NÃO depende do pacote (não
 * resolvido por tsc/webpack); resolve em runtime após `npm install playwright-core`
 * no Batch 2. Sem o pacote → retorna null (canary não abre).
 */
async function loadPlaywright(): Promise<any | null> {
  try {
    const spec = 'playwright-core';
    const mod: any = await import(/* webpackIgnore: true */ spec).catch(() => null);
    return mod?.chromium ? mod : null;
  } catch {
    return null;
  }
}

/**
 * Conecta via CDP a uma sessão Browserbase já aberta (server-side) e coleta APENAS
 * metadados não sensíveis. NUNCA retorna connectUrl/cookies/DOM bruto.
 */
export async function verifyViaCdp(input: CdpVerifyInput): Promise<CdpObservation> {
  const base: CdpObservation = { available: false, host: null, page_title: null, auth_marker_present: false, challenge_detected: null, reason: 'unknown' };
  if (!input.connect_url) return { ...base, reason: 'connect_url_missing' };
  const pw = await loadPlaywright();
  if (!pw) return { ...base, reason: 'playwright_not_available' }; // Batch 2 instala playwright-core

  let browser: any = null;
  try {
    browser = await pw.chromium.connectOverCDP(input.connect_url, { timeout: input.timeout_ms ?? 20000 });
    const contexts = browser.contexts();
    const ctx = contexts[0] ?? (await browser.newContext());
    const pages = ctx.pages();
    const page = pages[0] ?? (await ctx.newPage());

    let host: string | null = null;
    try { host = new URL(page.url()).host; } catch { host = null; }
    let title: string | null = null;
    try { title = await page.title(); } catch { title = null; }

    let authMarker = false;
    for (const sel of input.auth_marker_selectors ?? []) {
      try { if (await page.locator(sel).first().count()) { authMarker = true; break; } } catch { /* ignora */ }
    }
    let challenge: string | null = null;
    for (const c of input.challenge_selectors ?? []) {
      try { if (await page.locator(c.selector).first().count()) { challenge = c.kind; break; } } catch { /* ignora */ }
    }
    return { available: true, host, page_title: title, auth_marker_present: authMarker, challenge_detected: challenge, reason: 'observed' };
  } catch (e: any) {
    return { ...base, reason: `cdp_error:${String(e?.message || 'unknown').slice(0, 60)}` };
  } finally {
    // NÃO fecha o browser remoto aqui (humano ainda pode estar logando); apenas desconecta.
    try { if (browser) await browser.close(); } catch { /* best-effort */ }
  }
}
