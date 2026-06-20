// 43P-FINAL-1 — status dos canaries do tenant (sanitizado; sem segredo).
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listCanaries, listCanaryApprovals } from '@/lib/attendance/portal-admin-context';
import { sanitizeCanary, findCanarySecrets } from '@/lib/attendance/portal-real-execution-controller';

export const dynamic = 'force-dynamic';

export async function GET(_request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!ctx.companyId) return NextResponse.json({ ok: false, error: 'company_scope_required', company_scope_required: true }, { status: 403 });

    const canaries = (await listCanaries(supabase, ctx.companyId)).map((c: any) => sanitizeCanary(c));
    const leak = canaries.flatMap((c) => findCanarySecrets(c));
    if (leak.length > 0) return NextResponse.json({ ok: false, error: 'secret_leak_detected' }, { status: 500 });
    const approvals = (await listCanaryApprovals(supabase, ctx.companyId)).map((a: any) => ({
      portal_account_id: a.portal_account_id, journey: a.journey, mode: a.mode,
      approved_at: a.approved_at, expires_at: a.expires_at, revoked: Boolean(a.revoked),
    }));
    return NextResponse.json({ ok: true, canaries, approvals, real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY STATUS]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
