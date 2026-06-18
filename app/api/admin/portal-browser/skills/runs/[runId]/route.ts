import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getSkillRun } from '@/lib/attendance/portal-admin-context';
import { sanitizePortalSkillRun } from '@/lib/attendance/portal-skill-runner';

export const dynamic = 'force-dynamic';

/** GET — retorna um skill run persistido (sanitizado). */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ runId: string }> }) {
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
    return NextResponse.json({ ok: true, run: sanitizePortalSkillRun(run), eval: run.eval ?? null, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL SKILL RUN GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
