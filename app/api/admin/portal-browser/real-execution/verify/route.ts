// 43P-FINAL-2 — verifica a sessão capturada (GATED). Observa via CDP (read-only),
// guarda observação sanitizada e valida a SessionRef por metadados.
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getCanary, saveCanary } from '@/lib/attendance/portal-admin-context';
import { guardCanary, DEFAULT_CHALLENGE_SELECTORS } from '@/lib/attendance/portal-canary-guard';
import { withBrowserbaseConnectUrl } from '@/lib/attendance/browserbase-session-server';
import { observeViaCdp } from '@/lib/attendance/portal-cdp-transport';
import { toSafePageLabel } from '@/lib/attendance/portal-read-only-skill';
import { setCanaryObservation, verifyCanarySession, markChallenge, sanitizeCanary, findCanarySecrets } from '@/lib/attendance/portal-real-execution-controller';

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

    // Observa via CDP (read-only). connectUrl só em memória.
    const cdp = await withBrowserbaseConnectUrl(canary.session_id, g.env, async (connectUrl) => {
      const obs = await observeViaCdp(connectUrl, { challenge_selectors: DEFAULT_CHALLENGE_SELECTORS, auth_marker_selectors: [] });
      return {
        host: obs.host,
        safe_page_label: toSafePageLabel(obs.page_title), // título bruto descartado se tiver PII
        auth_marker_present: obs.auth_marker_present,
        challenge_detected: obs.challenge_detected,
        available: obs.available,
      };
    });

    if (cdp.ok && cdp.result) {
      const o = cdp.result as { host: string | null; safe_page_label: string | null; auth_marker_present: boolean; challenge_detected: string | null; available: boolean };
      canary = setCanaryObservation(canary, { host: o.host, safe_page_label: o.safe_page_label, auth_marker_present: o.auth_marker_present, challenge_detected: o.challenge_detected });
      if (o.challenge_detected && (canary.state === 'waiting_human_login' || canary.state === 'browser_opened')) {
        canary = markChallenge(canary, o.challenge_detected);
      }
    }
    // Validação por metadados (expiração/status) → session_verified.
    canary = verifyCanarySession(canary);

    await saveCanary(supabase, ctx.companyId, canary);
    const safe = sanitizeCanary(canary);
    if (findCanarySecrets(safe).length > 0) return NextResponse.json({ ok: false, error: 'secret_leak_detected' }, { status: 500 });
    return NextResponse.json({ ok: true, canary: safe, cdp_reason: cdp.reason, real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY VERIFY]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
