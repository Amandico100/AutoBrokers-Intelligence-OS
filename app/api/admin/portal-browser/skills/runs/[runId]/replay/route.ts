import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getSkillRun } from '@/lib/attendance/portal-admin-context';
import { buildRelayReplay } from '@/lib/attendance/browser-relay-runtime';

export const dynamic = 'force-dynamic';

/** POST — replay sanitizado do relay associado ao skill run. */
export async function POST(_request: NextRequest, { params }: { params: Promise<{ runId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { runId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let run;
    try { run = await getSkillRun(supabase, companyId, runId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    if (!run) return NextResponse.json({ ok: false, error: 'run_not_found' }, { status: 404 });
    const replay = run.relay_session ? buildRelayReplay(run.relay_session) : { relay_id: null, timeline: [], final_status: run.status, has_pii: false };
    return NextResponse.json({ ok: true, replay, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL SKILL RUN REPLAY]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
