// 43P-FINAL-1 — aborta/encerra um canary (fecha sessão best-effort, gated).
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getCanary, saveCanary } from '@/lib/attendance/portal-admin-context';
import { getProductionFlags } from '@/lib/security/production-gates';
import { evaluateBrowserbaseReadiness, closeBrowserbaseSession } from '@/lib/attendance/browserbase-real-adapter';
import { abortCanary, sanitizeCanary } from '@/lib/attendance/portal-real-execution-controller';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required' }, { status: 403 });

    const body = await request.json().catch(() => ({}));
    const canaryId = String(body.canary_id ?? '').trim();
    if (!canaryId) return NextResponse.json({ ok: false, error: 'canary_id_required' }, { status: 400 });

    const canary = await getCanary(supabase, ctx.companyId, canaryId);
    if (!canary) return NextResponse.json({ ok: false, error: 'canary_not_found' }, { status: 404 });

    const flags = getProductionFlags();
    const readiness = evaluateBrowserbaseReadiness({
      flags: {
        global_kill_switch: flags.global_kill_switch,
        portal_real_action_enabled: flags.portal_real_action_enabled,
        portal_login_real_enabled: flags.portal_login_real_enabled,
        portal_session_capture_enabled: flags.portal_session_capture_enabled,
        browserbase_real_browser_enabled: flags.browserbase_real_browser_enabled,
      },
      approval_exists: true,
    });

    const aborted = await abortCanary(canary, async (sessionId: string) => {
      const r = await closeBrowserbaseSession({ session_id: sessionId, readiness });
      return { closed: r.closed };
    });
    await saveCanary(supabase, ctx.companyId, aborted);
    return NextResponse.json({ ok: true, canary: sanitizeCanary(aborted), real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY ABORT]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
