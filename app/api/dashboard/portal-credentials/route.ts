import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-020 — Credenciais de portal POR CORRETORA (multi-tenant).
 * O company_id vem SEMPRE da sessão (nunca do cliente) — cada corretora só
 * enxerga/edita as suas credenciais. Senha é cifrada no backend (nunca volta).
 * GET    → { portals: [...global...], credentials: [...da corretora, sem senha...] }
 * POST   → salva/atualiza { portal_key, username, password?, account_label? }
 * DELETE → ?portal_key=&account_label=
 */
function internalKey(): string {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
}
function backendHeaders(): Record<string, string> {
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey() };
}

export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const base = getBackendUrl();
  try {
    const [pRes, cRes] = await Promise.all([
      fetch(`${base}/api/portal/portals`, { headers: backendHeaders(), cache: 'no-store' }),
      fetch(`${base}/api/portal/credentials?company_id=${encodeURIComponent(ctx.companyId)}`, {
        headers: backendHeaders(),
        cache: 'no-store',
      }),
    ]);
    const portals = (await pRes.json().catch(() => ({}))).portals || [];
    const credentials = (await cRes.json().catch(() => ({}))).credentials || [];
    return NextResponse.json({ portals, credentials });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const base = getBackendUrl();
  const res = await fetch(`${base}/api/portal/credentials`, {
    method: 'POST',
    headers: backendHeaders(),
    // company_id da SESSÃO — ignora qualquer company_id que venha do cliente.
    body: JSON.stringify({
      portal_key: body.portal_key,
      username: body.username,
      password: body.password,
      account_label: body.account_label,
      company_id: ctx.companyId,
    }),
  });
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}

export async function DELETE(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const portalKey = req.nextUrl.searchParams.get('portal_key') || '';
  const label = req.nextUrl.searchParams.get('account_label') || 'principal';
  const base = getBackendUrl();
  const res = await fetch(
    `${base}/api/portal/credentials?company_id=${encodeURIComponent(ctx.companyId)}&portal_key=${encodeURIComponent(portalKey)}&account_label=${encodeURIComponent(label)}`,
    { method: 'DELETE', headers: backendHeaders() },
  );
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}
