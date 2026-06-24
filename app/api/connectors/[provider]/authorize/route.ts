import { NextRequest, NextResponse } from 'next/server';
import { randomUUID } from 'crypto';

import { resolveSessionCompany } from '@/lib/vault/server';
import { providerCfg, providerConfigured } from '@/lib/connectors/oauth-providers';

export const dynamic = 'force-dynamic';

/**
 * GET /api/connectors/[provider]/authorize  (C2-P2 frente 2)
 * Inicia o OAuth oficial (Google Drive / Notion). Sem rascunho-lixo: se o provider não estiver
 * habilitado pela plataforma, volta ao Dashboard com aviso claro.
 */
export async function GET(req: NextRequest, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  const dash = new URL('/dashboard/personalizacao/conectores', req.url);
  const cfg = providerCfg(provider);
  if (!cfg) {
    dash.searchParams.set('connector_error', 'unknown');
    return NextResponse.redirect(dash);
  }

  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.redirect(new URL('/login', req.url));

  if (!providerConfigured(provider)) {
    dash.searchParams.set('connector_error', 'not_enabled');
    return NextResponse.redirect(dash);
  }

  const clientId = process.env[cfg.clientIdEnv]!;
  const redirect = process.env[cfg.redirectEnv] || new URL(`/api/connectors/${provider}/callback`, req.url).toString();
  const nonce = randomUUID();

  const authUrl = new URL(cfg.authUrl);
  authUrl.searchParams.set('client_id', clientId);
  authUrl.searchParams.set('redirect_uri', redirect);
  authUrl.searchParams.set('response_type', 'code');
  if (cfg.scopes.length) authUrl.searchParams.set('scope', cfg.scopes.join(' '));
  authUrl.searchParams.set('state', nonce);
  for (const [k, v] of Object.entries(cfg.authParams || {})) authUrl.searchParams.set(k, v);

  const res = NextResponse.redirect(authUrl.toString());
  res.cookies.set('ab_oauth_state', JSON.stringify({ nonce, provider, companyId: ctx.companyId }), {
    httpOnly: true, secure: true, sameSite: 'lax', maxAge: 600, path: '/',
  });
  return res;
}
