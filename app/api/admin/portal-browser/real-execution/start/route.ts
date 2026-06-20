// 43P-FINAL-1 — inicia um canary de login real (GATED). Sem env/flags/approval,
// falha fechado SEM abrir browser/rede. Wiring pronto para o Batch 2.
import { NextRequest, NextResponse } from 'next/server';
import {
  getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, listCanaryApprovals, saveCanary,
} from '@/lib/attendance/portal-admin-context';
import { getProductionFlags } from '@/lib/security/production-gates';
import { evaluateBrowserbaseReadiness, createBrowserbaseLoginSession, closeBrowserbaseSession } from '@/lib/attendance/browserbase-real-adapter';
import { evaluateTenantCanaryAuthorization } from '@/lib/attendance/portal-tenant-canary-authorization';
import {
  initCanary, markAwaitingApproval, applyAuthorization, openCanaryBrowser, sanitizeCanary, findCanarySecrets,
  type CanaryBrowserTransport,
} from '@/lib/attendance/portal-real-execution-controller';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required' }, { status: 403 });

    const body = await request.json().catch(() => ({}));
    const portalAccountId = String(body.portal_account_id ?? '').trim();
    const journey = String(body.journey ?? 'login').trim();
    if (!portalAccountId) return NextResponse.json({ ok: false, error: 'portal_account_id_required' }, { status: 400 });

    const accounts = await listPortalAccounts(supabase, ctx.companyId);
    const acc = accounts.find((a: any) => a.portal_account_id === portalAccountId);
    if (!acc) return NextResponse.json({ ok: false, error: 'portal_account_not_found_in_tenant' }, { status: 404 });

    const flags = getProductionFlags();
    const readiness = evaluateBrowserbaseReadiness({
      flags: {
        global_kill_switch: flags.global_kill_switch,
        portal_real_action_enabled: flags.portal_real_action_enabled,
        portal_login_real_enabled: flags.portal_login_real_enabled,
        portal_session_capture_enabled: flags.portal_session_capture_enabled,
        browserbase_real_browser_enabled: flags.browserbase_real_browser_enabled,
      },
      approval_exists: true, // approval verificada abaixo por tenant
    });

    const approvals = await listCanaryApprovals(supabase, ctx.companyId);
    const approval = approvals.find((a: any) => a.portal_account_id === portalAccountId && a.journey === journey) ?? null;

    const authz = evaluateTenantCanaryAuthorization({
      company_id: ctx.companyId, portal_id: acc.portal_id, portal_account_id: portalAccountId, journey,
      is_master: ctx.isMaster, operator_company_id: ctx.companyId,
      global_kill_switch: flags.global_kill_switch,
      global_flag_enabled: flags.portal_login_real_enabled && flags.browserbase_real_browser_enabled,
      readiness_can_open: readiness.can_open_real_browser,
      approval,
    });

    const canaryId = `cny-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
    let canary = applyAuthorization(
      markAwaitingApproval(initCanary({ canary_id: canaryId, company_id: ctx.companyId, portal_id: acc.portal_id, portal_account_id: portalAccountId, journey })),
      authz.authorized, authz.blockers,
    );

    // Browser transport real (gated). connectUrl fica server-side; NUNCA retornado.
    const transport: CanaryBrowserTransport = {
      open: async () => {
        const r = await createBrowserbaseLoginSession({ readiness });
        return { ok: r.opened, session_id: r.session_id, session_status: r.session_status, region: r.region, expires_at: r.expires_at, blockers: r.blockers, reason: r.reason };
      },
      close: async (sessionId: string) => {
        const r = await closeBrowserbaseSession({ session_id: sessionId, readiness });
        return { closed: r.closed };
      },
    };

    // openCanaryBrowser NÃO chama a rede se readiness.can_open_real_browser=false.
    canary = await openCanaryBrowser(canary, readiness.can_open_real_browser, transport);

    await saveCanary(supabase, ctx.companyId, canary);

    const safe = sanitizeCanary(canary);
    const leak = findCanarySecrets(safe);
    if (leak.length > 0) return NextResponse.json({ ok: false, error: 'secret_leak_detected' }, { status: 500 });

    return NextResponse.json({
      ok: true,
      canary: safe,
      authorization: { authorized: authz.authorized, blockers: authz.blockers },
      browserbase_readiness: readiness,
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[CANARY START]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
