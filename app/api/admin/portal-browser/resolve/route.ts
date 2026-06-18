import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalDefinitions, listPortalAccounts } from '@/lib/attendance/portal-admin-context';
import { resolvePortalForJourney } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/**
 * GET /api/admin/portal-browser/resolve?portal_id=...&owner_key=...&journey=...
 * Diagnóstico: qual portal/conta resolveria para o objetivo. real_action_allowed=false.
 */
export async function GET(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    const { searchParams } = new URL(request.url);
    let definitions; let accounts;
    try {
      definitions = await listPortalDefinitions(supabase, companyId);
      accounts = await listPortalAccounts(supabase, companyId);
    } catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available', resolution: null }, { status: 200 }); }

    const resolution = resolvePortalForJourney(definitions, accounts, {
      company_id: companyId,
      owner_key: searchParams.get('owner_key'),
      portal_id: searchParams.get('portal_id'),
      journey: searchParams.get('journey'),
    });
    return NextResponse.json({ ok: true, resolution, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL RESOLVE GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
