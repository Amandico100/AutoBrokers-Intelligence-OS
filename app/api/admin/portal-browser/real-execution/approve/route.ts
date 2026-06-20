// 43P-FINAL-1 — aprovação de canary read-only por TENANT + PORTAL ACCOUNT.
// Approval expira (obrigatório), é por company+account, nunca global/indefinida.
// Tenant admin só aprova a própria company; master opera a corretora selecionada.
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, saveCanaryApproval } from '@/lib/attendance/portal-admin-context';

export const dynamic = 'force-dynamic';

const MAX_TTL_MS = 60 * 60 * 1000; // 1h máx (sem approval longa/indefinida)

export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required' }, { status: 403 });

    const body = await request.json().catch(() => ({}));
    const portalAccountId = String(body.portal_account_id ?? '').trim();
    const journey = String(body.journey ?? 'login').trim();
    if (!portalAccountId) return NextResponse.json({ ok: false, error: 'portal_account_id_required' }, { status: 400 });

    // Conta precisa existir NESTE tenant (isolamento).
    const accounts = await listPortalAccounts(supabase, ctx.companyId);
    const acc = accounts.find((a: any) => a.portal_account_id === portalAccountId);
    if (!acc) return NextResponse.json({ ok: false, error: 'portal_account_not_found_in_tenant' }, { status: 404 });

    const ttl = Math.min(Number(body.ttl_ms) || MAX_TTL_MS, MAX_TTL_MS);
    const nowIso = new Date().toISOString();
    const approval = {
      company_id: ctx.companyId,
      portal_id: acc.portal_id,
      portal_account_id: portalAccountId,
      journey,
      mode: 'read_only_canary',
      approved_by: ctx.userId,
      approved_at: nowIso,
      expires_at: new Date(Date.now() + ttl).toISOString(),
      purpose: typeof body.purpose === 'string' ? body.purpose.slice(0, 200) : 'canary_login_verify',
      revoked: false,
    };
    await saveCanaryApproval(supabase, ctx.companyId, approval);
    return NextResponse.json({ ok: true, approval, real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY APPROVE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** Revoga a approval de um portal account. */
export async function DELETE(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required' }, { status: 403 });
    const portalAccountId = new URL(request.url).searchParams.get('portal_account_id') ?? '';
    const journey = new URL(request.url).searchParams.get('journey') ?? 'login';
    if (!portalAccountId) return NextResponse.json({ ok: false, error: 'portal_account_id_required' }, { status: 400 });
    const accounts = await listPortalAccounts(supabase, ctx.companyId);
    const acc = accounts.find((a: any) => a.portal_account_id === portalAccountId);
    await saveCanaryApproval(supabase, ctx.companyId, {
      company_id: ctx.companyId, portal_id: acc?.portal_id ?? null, portal_account_id: portalAccountId,
      journey, mode: 'read_only_canary', approved_by: ctx.userId, approved_at: new Date().toISOString(),
      expires_at: new Date().toISOString(), purpose: 'revoked', revoked: true,
    });
    return NextResponse.json({ ok: true, revoked: true });
  } catch (error: any) {
    console.error('[CANARY APPROVE DELETE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
