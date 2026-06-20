// 43P-FINAL-2A — gestão da SessionRef da Portal Account (health/expiração/revogação).
// Read-only de metadados (não acessa portal real). Sanitizado.
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, savePortalAccount } from '@/lib/attendance/portal-admin-context';
import { sanitizePortalAccountRecord } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

type Action = 'verify' | 'revoke' | 'mark_expired' | 'request_relogin';

export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required' }, { status: 403 });

    const body = await request.json().catch(() => ({}));
    const portalAccountId = String(body.portal_account_id ?? '').trim();
    const action = String(body.action ?? '') as Action;
    if (!portalAccountId) return NextResponse.json({ ok: false, error: 'portal_account_id_required' }, { status: 400 });
    if (!['verify', 'revoke', 'mark_expired', 'request_relogin'].includes(action)) return NextResponse.json({ ok: false, error: 'invalid_action' }, { status: 400 });

    const accounts = await listPortalAccounts(supabase, ctx.companyId);
    const acc = accounts.find((a: any) => a.portal_account_id === portalAccountId);
    if (!acc) return NextResponse.json({ ok: false, error: 'portal_account_not_found_in_tenant' }, { status: 404 });
    if (!acc.session_ref) return NextResponse.json({ ok: false, error: 'no_session_ref' }, { status: 409 });

    const nowIso = new Date().toISOString();
    const sref = acc.session_ref;
    if (action === 'verify') {
      // Saúde por METADADOS (sem acessar portal). Expiração vence.
      if (sref.expires_at && Date.parse(sref.expires_at) <= Date.now()) sref.status = 'expired';
      else if (sref.status === 'healthy' || sref.status === 'unknown') sref.status = sref.status === 'healthy' ? 'healthy' : 'unknown';
      sref.last_verified_at = nowIso;
    } else if (action === 'revoke') {
      sref.status = 'revoked';
    } else if (action === 'mark_expired') {
      sref.status = 'expired';
    } else if (action === 'request_relogin') {
      sref.status = 'reauth_required';
    }
    sref.updated_at = nowIso;
    await savePortalAccount(supabase, ctx.companyId, acc);

    return NextResponse.json({ ok: true, account: sanitizePortalAccountRecord(acc), real_action_allowed: false });
  } catch (error: any) {
    console.error('[SESSION-REF MGMT]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
