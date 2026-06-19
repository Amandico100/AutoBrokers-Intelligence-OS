import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalDefinitions, listPortalAccounts, saveLoginSetup } from '@/lib/attendance/portal-admin-context';
import { findRequestSecrets, resolvePortalCanonical } from '@/lib/attendance/portal-admin-sanitizers';
import { getGlobalPortalCatalogSeed } from '@/lib/attendance/portal-global-catalog';
import { startLoginSetup, sanitizeLoginSetup } from '@/lib/attendance/portal-login-setup';
import { getProductionFlags, evaluatePortalRealActionGate } from '@/lib/security/production-gates';
import { evaluateBrowserbaseReadiness } from '@/lib/attendance/browserbase-real-adapter';

export const dynamic = 'force-dynamic';

/** POST — inicia o login assistido (gated). NUNCA abre browser/login real automaticamente. */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });
    if (!body.portal_id && !body.owner_key) return NextResponse.json({ ok: false, error: 'missing_portal_id_or_owner_key' }, { status: 400 });

    let definitions; let accounts;
    try { definitions = await listPortalDefinitions(supabase, companyId); accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }

    const resolution = resolvePortalCanonical(getGlobalPortalCatalogSeed(), definitions, accounts, {
      company_id: companyId, portal_id: body.portal_id ?? null, owner_key: body.owner_key ?? null, journey: 'login',
    });
    const account = accounts.find((a) => a.portal_account_id === body.portal_account_id)
      || accounts.find((a) => a.portal_id === resolution.portal_id);

    const flags = getProductionFlags();
    const session = startLoginSetup({
      portal_id: resolution.portal_id ?? body.portal_id,
      portal_account_id: account?.portal_account_id ?? body.portal_account_id ?? null,
      owner_key: body.owner_key ?? null,
      provider: body.provider ?? 'browserbase',
      context: {
        flags: {
          global_kill_switch: flags.global_kill_switch,
          portal_real_action_enabled: flags.portal_real_action_enabled,
          portal_login_real_enabled: flags.portal_login_real_enabled,
          portal_session_capture_enabled: flags.portal_session_capture_enabled,
        },
        account_present: Boolean(account),
        credential_present: Boolean(account?.credential_ref),
        portal_healthy: account?.status === 'healthy',
        approval_exists: body.approval_exists === true,
      },
    });

    try { await saveLoginSetup(supabase, companyId, session); } catch { /* best-effort */ }
    const production_gate = evaluatePortalRealActionGate({ flags, session_capture: true, portal_status: resolution.portal_source });
    // 43P4.1 — readiness do Browserbase real (gated; sem rede). Útil quando mode=real_canary.
    const browserbase_readiness = evaluateBrowserbaseReadiness({
      flags: {
        global_kill_switch: flags.global_kill_switch,
        portal_real_action_enabled: flags.portal_real_action_enabled,
        portal_login_real_enabled: flags.portal_login_real_enabled,
        portal_session_capture_enabled: flags.portal_session_capture_enabled,
        browserbase_real_browser_enabled: flags.browserbase_real_browser_enabled,
      },
      approval_exists: body.approval_exists === true,
    });
    console.log(`[LOGIN SETUP START] company=${companyId} portal=${session.portal_id} status=${session.status} mode=${body.mode ?? 'sandbox'} real_browser_opened=false`);
    return NextResponse.json({ ok: true, login_setup: sanitizeLoginSetup(session), production_gate, browserbase_readiness, real_action_allowed: false });
  } catch (error: any) {
    console.error('[LOGIN SETUP START]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
