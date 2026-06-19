import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getLoginSetup } from '@/lib/attendance/portal-admin-context';
import { sanitizeLoginSetup } from '@/lib/attendance/portal-login-setup';

export const dynamic = 'force-dynamic';

/** GET — retorna o login setup persistido (sanitizado; sem segredo). */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ setupId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { setupId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let session;
    try { session = await getLoginSetup(supabase, companyId, setupId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    if (!session) return NextResponse.json({ ok: false, error: 'login_setup_not_found' }, { status: 404 });
    return NextResponse.json({ ok: true, login_setup: sanitizeLoginSetup(session), real_action_allowed: false });
  } catch (error: any) {
    console.error('[LOGIN SETUP GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
