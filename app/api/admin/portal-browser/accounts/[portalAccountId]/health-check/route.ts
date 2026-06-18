import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, savePortalAccount } from '@/lib/attendance/portal-admin-context';
import { mockHealthCheck, sanitizePortalAccountRecord } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/** POST — health-check MOCK (sem browser/portal real). Reavalia a SessionRef por metadados. */
export async function POST(_request: NextRequest, { params }: { params: Promise<{ portalAccountId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { portalAccountId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let accounts;
    try { accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const idx = accounts.findIndex((a) => a.portal_account_id === portalAccountId);
    if (idx < 0) return NextResponse.json({ ok: false, error: 'account_not_found' }, { status: 404 });

    const health = mockHealthCheck(accounts[idx]);
    const updated = { ...accounts[idx], status: health.status, last_health_check_at: health.checked_at, updated_at: health.checked_at };
    if (updated.session_ref) updated.session_ref = { ...updated.session_ref, status: health.session_status, last_checked_at: health.checked_at };
    accounts[idx] = updated;
    try { await savePortalAccount(supabase, companyId, updated); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }

    console.log(`[PORTAL HEALTH-CHECK] company=${companyId} account=${portalAccountId} status=${health.status} (mock)`);
    return NextResponse.json({ ok: true, health, account: sanitizePortalAccountRecord(updated), mock: true, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL HEALTH-CHECK POST]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
