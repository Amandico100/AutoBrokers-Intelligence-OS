import { NextRequest, NextResponse } from 'next/server';

import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { providerCfg, publicBaseUrl } from '@/lib/connectors/oauth-providers';

export const dynamic = 'force-dynamic';

/**
 * GET /api/connectors/[provider]/callback  (C2-P2 frente 2)
 * Recebe o code do OAuth oficial, troca por token server-side e grava CIFRADO no Vault
 * (via backend), marcando a conexão da corretora como connected. Token nunca vai ao browser/logs.
 */
export async function GET(req: NextRequest, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  const base = publicBaseUrl(req);
  const dash = new URL('/dashboard/personalizacao/conectores', base);
  const cfg = providerCfg(provider);
  if (!cfg) { dash.searchParams.set('connector_error', 'unknown'); return NextResponse.redirect(dash); }

  const url = new URL(req.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const oauthErr = url.searchParams.get('error');

  const fail = (reason: string) => {
    dash.searchParams.set('connector_error', reason);
    const r = NextResponse.redirect(dash);
    r.cookies.delete('ab_oauth_state');
    return r;
  };

  if (oauthErr || !code) return fail('cancelled');

  // valida state (anti-CSRF) contra o cookie httpOnly
  let st: { nonce?: string; provider?: string; companyId?: string; ownerUserId?: string | null } | null = null;
  try { const c = req.cookies.get('ab_oauth_state')?.value; st = c ? JSON.parse(c) : null; } catch { st = null; }
  if (!st || st.nonce !== state || st.provider !== provider || !st.companyId) return fail('state');

  const clientId = process.env[cfg.clientIdEnv];
  const clientSecret = process.env[cfg.clientSecretEnv];
  if (!clientId || !clientSecret) return fail('not_enabled');
  const redirect = process.env[cfg.redirectEnv] || `${base}/api/connectors/${provider}/callback`;

  // troca code -> token (server-side)
  let tok: Record<string, any> = {};
  try {
    let tokenRes: Response;
    if (cfg.tokenAuth === 'basic') {
      const basic = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
      tokenRes = await fetch(cfg.tokenUrl, {
        method: 'POST',
        headers: { Authorization: `Basic ${basic}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ grant_type: 'authorization_code', code, redirect_uri: redirect }),
      });
    } else {
      const form = new URLSearchParams({ grant_type: 'authorization_code', code, redirect_uri: redirect, client_id: clientId, client_secret: clientSecret });
      tokenRes = await fetch(cfg.tokenUrl, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form.toString() });
    }
    tok = await tokenRes.json().catch(() => ({}));
    if (!tokenRes.ok || !tok.access_token) return fail('token');
  } catch { return fail('token'); }

  // grava CIFRADO via backend (Vault/Fernet); token nunca persiste no Web
  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) return fail('internal_key');
  let backendUrl: string;
  try { backendUrl = getBackendUrl(req); }
  catch (e) { if (e instanceof BackendUrlError) return fail('backend'); throw e; }

  try {
    const storeRes = await fetch(`${backendUrl}/connectors/oauth/store`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: st.companyId,
        slug: cfg.slug,
        access_token: tok.access_token,
        refresh_token: tok.refresh_token ?? null,
        expires_in: tok.expires_in ?? null,
        scope: typeof tok.scope === 'string' ? tok.scope : (cfg.scopes.join(' ') || null),
        account_label: tok.workspace_name || tok.bot_id || null,
        // SPEC-044: conexão pessoal (owner do state assinado) ou da corretora.
        owner_user_id: st.ownerUserId || null,
        name: st.ownerUserId ? `${cfg.label} — pessoal` : `${cfg.label} — corretora`,
      }),
    });
    if (!storeRes.ok) return fail('store');
  } catch { return fail('store'); }

  dash.searchParams.set('connected', cfg.slug);
  const res = NextResponse.redirect(dash);
  res.cookies.delete('ab_oauth_state');
  return res;
}
