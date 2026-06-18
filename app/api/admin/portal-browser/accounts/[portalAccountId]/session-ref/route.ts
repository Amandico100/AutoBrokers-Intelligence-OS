import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, savePortalAccount } from '@/lib/attendance/portal-admin-context';
import { buildSessionRefRecord, deriveAccountStatus, sanitizePortalAccountRecord, findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/** POST — anexa um SessionRef (mock/opaco). Rejeita cookie/storageState cru. NUNCA acessa portal. */
export async function POST(request: NextRequest, { params }: { params: Promise<{ portalAccountId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { portalAccountId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body', hint: 'envie apenas storage_ref opaco' }, { status: 400 });
    if (!body.storage_ref) return NextResponse.json({ ok: false, error: 'missing_storage_ref' }, { status: 400 });

    let accounts;
    try { accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const idx = accounts.findIndex((a) => a.portal_account_id === portalAccountId);
    if (idx < 0) return NextResponse.json({ ok: false, error: 'account_not_found' }, { status: 404 });

    let sessRef;
    try { sessRef = buildSessionRefRecord({ company_id: companyId, portal_id: accounts[idx].portal_id, storage_ref: body.storage_ref, provider: body.provider, status: body.status ?? 'unknown', expires_at: body.expires_at ?? null }); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'invalid_session' }, { status: 400 }); }

    const updated = { ...accounts[idx], session_ref: sessRef, updated_at: new Date().toISOString() };
    updated.status = deriveAccountStatus(updated);
    accounts[idx] = updated;
    try { await savePortalAccount(supabase, companyId, updated); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    return NextResponse.json({ ok: true, account: sanitizePortalAccountRecord(updated), real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL SESSION-REF POST]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
