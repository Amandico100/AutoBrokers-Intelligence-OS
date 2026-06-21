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
      // Readiness GLOBAL de infraestrutura (env+flags+kill switch). A approval é
      // por Portal Account e é avaliada em real-execution/readiness — por isso aqui
      // não bloqueamos por approval (evita falso "no_human_approval" no card global).
      approval_exists: true,
    });
    return NextResponse.json({ ok: true, readiness, real_action_allowed: false });
  } catch (error: any) {
    console.error('[BROWSERBASE READINESS]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
