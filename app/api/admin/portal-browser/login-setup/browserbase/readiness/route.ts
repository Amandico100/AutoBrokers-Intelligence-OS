import { NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { getProductionFlags } from '@/lib/security/production-gates';
import { evaluateBrowserbaseReadiness } from '@/lib/attendance/browserbase-real-adapter';

export const dynamic = 'force-dynamic';

/** GET — readiness do Browserbase real (gated). Sem segredos; can_open_real_browser=false por padrão. */
export async function GET() {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });

    const flags = getProductionFlags();
    const readiness = evaluateBrowserbaseReadiness({
      flags: {
        global_kill_switch: flags.global_kill_switch,
        portal_real_action_enabled: flags.portal_real_action_enabled,
        portal_login_real_enabled: flags.portal_login_real_enabled,
        portal_session_capture_enabled: flags.portal_session_capture_enabled,
        browserbase_real_browser_enabled: flags.browserbase_real_browser_enabled,
      },
      approval_exists: false,
    });
    return NextResponse.json({ ok: true, readiness, real_action_allowed: false });
  } catch (error: any) {
    console.error('[BROWSERBASE READINESS]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
