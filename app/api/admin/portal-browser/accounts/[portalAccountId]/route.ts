import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, savePortalAccount, removePortalAccount } from '@/lib/attendance/portal-admin-context';
import { sanitizePortalAccountRecord, findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/** PATCH — atualiza label/notes/status de uma conta (não toca refs aqui). */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ portalAccountId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { portalAccountId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });

    let accounts;
    try { accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const idx = accounts.findIndex((a) => a.portal_account_id === portalAccountId);
    if (idx < 0) return NextResponse.json({ ok: false, error: 'account_not_found' }, { status: 404 });

    const prev = accounts[idx];
    const updated = {
      ...prev,
      label: body.label ?? prev.label,
      notes: body.notes !== undefined ? body.notes : prev.notes,
      updated_at: new Date().toISOString(),
    };
    accounts[idx] = updated;
    try { await savePortalAccount(supabase, companyId, updated); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    return NextResponse.json({ ok: true, account: sanitizePortalAccountRecord(updated), real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL ACCOUNT PATCH]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** DELETE — remove uma conta de portal. */
export async function DELETE(_request: NextRequest, { params }: { params: Promise<{ portalAccountId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { portalAccountId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });
    let accounts;
    try { accounts = await removePortalAccount(supabase, companyId, portalAccountId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    return NextResponse.json({ ok: true, removed: portalAccountId, count: accounts.length });
  } catch (error: any) {
    console.error('[PORTAL ACCOUNT DELETE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
