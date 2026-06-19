import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getLoginSetup, saveLoginSetup, listPortalAccounts, savePortalAccount } from '@/lib/attendance/portal-admin-context';
import { findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';
import { applyLoginSetupStep, approveLoginSetup, sanitizeLoginSetup } from '@/lib/attendance/portal-login-setup';
import { captureSessionRef, sanitizeCapturedSessionRef } from '@/lib/attendance/portal-session-capture';

export const dynamic = 'force-dynamic';

/**
 * POST — conclui o login assistido: (aprova se preciso) → abre browser sandbox →
 * captura SessionRef opaca → verifica. Aceita SOMENTE storage_ref opaco
 * (cookie/storageState cru → 400). NUNCA expõe segredo; nenhuma ação de negócio.
 */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body', hint: 'envie apenas storage_ref opaco' }, { status: 400 });
    if (!body.setup_id) return NextResponse.json({ ok: false, error: 'missing_setup_id' }, { status: 400 });
    if (!body.storage_ref) return NextResponse.json({ ok: false, error: 'missing_storage_ref' }, { status: 400 });

    let session: any = null;
    try { session = await getLoginSetup(supabase, companyId, body.setup_id); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    if (!session) return NextResponse.json({ ok: false, error: 'login_setup_not_found' }, { status: 404 });

    // Aprova se chegou aprovação agora.
    if (session.status === 'awaiting_approval' && body.approval_exists === true) session = approveLoginSetup(session);
    if (session.status !== 'ready_to_open_browser') {
      return NextResponse.json({ ok: false, error: 'not_ready', status: session.status, blockers: session.blockers }, { status: 409 });
    }

    // Captura segura (apenas ref opaca). Lança se vier segredo.
    let captured;
    try {
      captured = captureSessionRef({
        portal_id: session.portal_id, portal_account_id: session.portal_account_id,
        storage_ref: body.storage_ref, provider: body.provider ?? 'browserbase',
        status: 'healthy', expires_at: body.expires_at ?? null,
      });
    } catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'invalid_session_capture' }, { status: 400 }); }

    // Fluxo: open (sandbox) → human_login → complete(capture) → verify.
    let s = applyLoginSetupStep(session, { type: 'open_browser', real_browser_adapter_available: false });
    s = applyLoginSetupStep(s, { type: 'human_login' });
    s = applyLoginSetupStep(s, { type: 'complete', captured });
    s = applyLoginSetupStep(s, { type: 'verify' });

    try { await saveLoginSetup(supabase, companyId, s); } catch { /* best-effort */ }

    // Anexa a SessionRef mascarada à conta de portal (continuidade), sem segredo cru.
    try {
      const accounts = await listPortalAccounts(supabase, companyId);
      const idx = accounts.findIndex((a) => a.portal_account_id === session.portal_account_id);
      if (idx >= 0) {
        const acc = accounts[idx];
        acc.session_ref = { session_ref_id: captured.session_ref_id, storage_ref_masked: captured.storage_ref_masked, provider: captured.provider, status: captured.status, expires_at: captured.expires_at ?? null, last_checked_at: captured.captured_at } as any;
        acc.status = 'healthy';
        acc.updated_at = new Date().toISOString();
        await savePortalAccount(supabase, companyId, acc);
      }
    } catch { /* best-effort */ }

    return NextResponse.json({ ok: true, login_setup: sanitizeLoginSetup(s), session_ref: sanitizeCapturedSessionRef(captured), real_action_allowed: false, business_action_allowed: false });
  } catch (error: any) {
    console.error('[LOGIN SETUP COMPLETE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
