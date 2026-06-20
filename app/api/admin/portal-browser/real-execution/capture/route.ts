// 43P-FINAL-2 — captura de SessionRef após login humano (GATED).
// CDP obtém storageState SÓ em memória e grava direto no Vault (Supabase Vault);
// só a referência opaca (storage_ref) é persistida. Challenge → não captura.
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getCanary, saveCanary } from '@/lib/attendance/portal-admin-context';
import { guardCanary, DEFAULT_CHALLENGE_SELECTORS } from '@/lib/attendance/portal-canary-guard';
import { withBrowserbaseConnectUrl } from '@/lib/attendance/browserbase-session-server';
import { captureStorageStateViaCdp } from '@/lib/attendance/portal-cdp-transport';
import { createSupabaseVaultAdapter } from '@/lib/attendance/portal-supabase-vault';
import { persistSessionRefViaVault } from '@/lib/attendance/portal-session-vault';
import { markChallenge, recordCanaryCapture, sanitizeCanary, findCanarySecrets } from '@/lib/attendance/portal-real-execution-controller';

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

    const vault = createSupabaseVaultAdapter(supabase);
    // CDP + Vault DENTRO do closure: storageState nunca sai do servidor.
    const cdp = await withBrowserbaseConnectUrl(canary.session_id, g.env, async (connectUrl) => {
      const cap = await captureStorageStateViaCdp(connectUrl, { challenge_selectors: DEFAULT_CHALLENGE_SELECTORS });
      if (cap.challenge_detected) return { challenge: cap.challenge_detected, storage_ref: null as string | null, reason: 'challenge_required' };
      if (!cap.ok || !cap.storage_payload) return { challenge: null, storage_ref: null as string | null, reason: cap.reason };
      const w = await persistSessionRefViaVault(
        { company_id: canary.company_id, portal_account_id: canary.portal_account_id, provider: canary.provider, secret_payload: cap.storage_payload },
        vault,
      );
      return { challenge: null, storage_ref: w.ok ? w.storage_ref : null, reason: w.reason };
    });

    if (!cdp.ok) {
      return NextResponse.json({ ok: false, error: `capture_failed:${cdp.reason}`, canary: sanitizeCanary(canary) }, { status: 200 });
    }
    const r = cdp.result as { challenge: string | null; storage_ref: string | null; reason: string };
    if (r.challenge) canary = markChallenge(canary, r.challenge);
    else if (r.storage_ref) canary = recordCanaryCapture(canary, r.storage_ref, 'healthy');
    else canary = { ...canary }; // permanece; razão volta no payload

    await saveCanary(supabase, ctx.companyId, canary);
    const safe = sanitizeCanary(canary);
    if (findCanarySecrets(safe).length > 0) return NextResponse.json({ ok: false, error: 'secret_leak_detected' }, { status: 500 });
    return NextResponse.json({ ok: true, canary: safe, capture_reason: r.reason, real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY CAPTURE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
