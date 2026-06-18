import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getRelaySession } from '@/lib/attendance/portal-admin-context';
import { sanitizeRelayRuntimeOutput } from '@/lib/attendance/browser-relay-runtime';

export const dynamic = 'force-dynamic';

/** GET — retorna a sessão de relay sandbox persistida (sanitizada). */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ relayId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { relayId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let session;
    try { session = await getRelaySession(supabase, companyId, relayId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    if (!session) return NextResponse.json({ ok: false, error: 'relay_not_found' }, { status: 404 });
    return NextResponse.json({ ok: true, relay: sanitizeRelayRuntimeOutput(session), real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL RELAY GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
