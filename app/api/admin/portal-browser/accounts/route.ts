import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, savePortalAccount, listPortalDefinitions } from '@/lib/attendance/portal-admin-context';
import { buildPortalAccountRecord, buildChallengeProfile, sanitizePortalAccountRecord, findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/** GET — lista contas de portal da corretora (sanitizadas). */
export async function GET() {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });
    let accounts;
    try { accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available', accounts: [] }, { status: 200 }); }
    return NextResponse.json({ ok: true, accounts: accounts.map(sanitizePortalAccountRecord), real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL ACCOUNTS GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** POST — cria conta de portal para a corretora (sem credencial/sessão ainda). */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });
    if (!body.portal_id) return NextResponse.json({ ok: false, error: 'missing_portal_id' }, { status: 400 });
    if (!body.label) return NextResponse.json({ ok: false, error: 'missing_label' }, { status: 400 });

    // Herda o challenge_profile do portal, se existir.
    let challengeProfile;
    try {
      const defs = await listPortalDefinitions(supabase, companyId);
      const def = defs.find((d) => d.portal_id === body.portal_id);
      challengeProfile = def?.challenge_profile ?? buildChallengeProfile(body.auth_methods ?? []);
    } catch { challengeProfile = buildChallengeProfile(body.auth_methods ?? []); }

    const record = buildPortalAccountRecord({ company_id: companyId, portal_id: body.portal_id, label: body.label, challenge_profile: challengeProfile, notes: body.notes ?? null });
    let accounts;
    try { accounts = await savePortalAccount(supabase, companyId, record); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    console.log(`[PORTAL ACCOUNTS POST] company=${companyId} portal=${record.portal_id} account=${record.portal_account_id} status=${record.status}`);
    return NextResponse.json({ ok: true, account: sanitizePortalAccountRecord(record), count: accounts.length, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL ACCOUNTS POST]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
