import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getLoginSetup, saveLoginSetup } from '@/lib/attendance/portal-admin-context';
import { findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';
import { applyLoginSetupStep, sanitizeLoginSetup } from '@/lib/attendance/portal-login-setup';

export const dynamic = 'force-dynamic';

/** POST — registra um challenge (CAPTCHA/2FA/OTP) → human_required. Nunca bypass; OTP mascarado. */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });
    if (!body.setup_id) return NextResponse.json({ ok: false, error: 'missing_setup_id' }, { status: 400 });

    let session;
    try { session = await getLoginSetup(supabase, companyId, body.setup_id); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    if (!session) return NextResponse.json({ ok: false, error: 'login_setup_not_found' }, { status: 404 });

    const updated = applyLoginSetupStep(session, { type: 'challenge', challenge_signal: body.challenge_signal ?? null });
    try { await saveLoginSetup(supabase, companyId, updated); } catch { /* best-effort */ }
    return NextResponse.json({ ok: true, login_setup: sanitizeLoginSetup(updated), real_action_allowed: false });
  } catch (error: any) {
    console.error('[LOGIN SETUP CHALLENGE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
