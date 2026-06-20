// 43P-FINAL-2 — executa a skill read-only session_login_verify sobre a sessão
// verificada (GATED). Usa a observação CDP já sanitizada; output sem PII/segredo.
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getCanary, saveCanary } from '@/lib/attendance/portal-admin-context';
import { guardCanary } from '@/lib/attendance/portal-canary-guard';
import { runSessionLoginVerify, getSessionLoginVerifyContract, findSkillOutputSecrets } from '@/lib/attendance/portal-read-only-skill';
import { attachReadOnlySkillResult, sanitizeCanary, findCanarySecrets } from '@/lib/attendance/portal-real-execution-controller';

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
    let canary = await getCanary(supabase, ctx.companyId, canaryId);
    if (!canary) return NextResponse.json({ ok: false, error: 'canary_not_found' }, { status: 404 });

    const g = await guardCanary(supabase, { companyId: ctx.companyId, userId: ctx.userId, isMaster: ctx.isMaster }, canary.portal_account_id, canary.journey);
    if (!g.authz.authorized) {
      return NextResponse.json({ ok: true, canary: sanitizeCanary(canary), authorization: { authorized: false, blockers: g.authz.blockers }, real_action_allowed: false });
    }

    const contract = getSessionLoginVerifyContract(g.hostAllowlist);
    const obs = canary.observation;
    const skillResult = runSessionLoginVerify({
      portal_id: canary.portal_id,
      session_state: canary.session_health === 'healthy' ? 'healthy' : (canary.session_health ?? 'unknown'),
      has_session_ref: Boolean(canary.storage_ref),
      authorized: true,
      observation: obs ? { host: obs.host, page_title: obs.safe_page_label, auth_marker_present: obs.auth_marker_present, challenge_detected: obs.challenge_detected } : null,
      contract,
    });
    if (findSkillOutputSecrets(skillResult).length > 0) return NextResponse.json({ ok: false, error: 'skill_output_leak' }, { status: 500 });

    canary = attachReadOnlySkillResult(canary, skillResult);
    await saveCanary(supabase, ctx.companyId, canary);
    const safe = sanitizeCanary(canary);
    if (findCanarySecrets(safe).length > 0) return NextResponse.json({ ok: false, error: 'secret_leak_detected' }, { status: 500 });
    return NextResponse.json({ ok: true, canary: safe, skill_result: skillResult, real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY RUN-SKILL]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
