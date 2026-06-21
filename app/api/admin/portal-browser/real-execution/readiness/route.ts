// 43P-FINAL-2A patch — readiness do canary ESPECÍFICA por Portal Account.
// Reaproveita a MESMA lógica canônica do start (guardCanary → readiness + authz):
// não duplica regras. Retorna só booleanos seguros (sem segredo).
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { guardCanary } from '@/lib/attendance/portal-canary-guard';
import { deriveCanaryReadinessFlags } from '@/lib/attendance/portal-tenant-canary-authorization';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required' }, { status: 403 });

    const url = new URL(request.url);
    const portalAccountId = (url.searchParams.get('portal_account_id') || '').trim();
    const journey = (url.searchParams.get('journey') || 'login').trim();
    if (!portalAccountId) return NextResponse.json({ ok: false, error: 'portal_account_id_required' }, { status: 400 });

    const g = await guardCanary(supabase, { companyId: ctx.companyId, userId: ctx.userId, isMaster: ctx.isMaster }, portalAccountId, journey);
    const blockers = g.authz.blockers;
    const env_ok = Boolean(g.readiness.env_present?.api_key_present && g.readiness.env_present?.project_id_present);
    const flags = deriveCanaryReadinessFlags(blockers);

    return NextResponse.json({
      ok: true,
      portal_account_id: portalAccountId,
      account_found: Boolean(g.acc),
      env_ok,
      kill_switch_off: flags.kill_switch_off,
      flags_ok: flags.flags_ok,
      browserbase_ready: flags.browserbase_ready,
      approval_valid: flags.approval_valid,
      start_allowed: g.authz.authorized,
      blockers,
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[CANARY READINESS]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
