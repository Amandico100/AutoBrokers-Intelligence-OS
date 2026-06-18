import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getSkillRun } from '@/lib/attendance/portal-admin-context';
import { buildRelayTrace } from '@/lib/attendance/browser-relay-runtime';

export const dynamic = 'force-dynamic';

/** POST — trace sanitizado do relay associado ao skill run. */
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
    const trace = run.relay_session ? buildRelayTrace(run.relay_session) : { relay_id: null, has_pii: false, real_action_allowed: false, steps: [] };
    return NextResponse.json({ ok: true, trace, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL SKILL RUN TRACE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
