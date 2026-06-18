import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getRelaySession, saveRelaySession } from '@/lib/attendance/portal-admin-context';
import { findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';
import { getBrowserRelayAdapter } from '@/lib/attendance/browser-relay-adapters';
import { applyBrowserRelaySandboxStep } from '@/lib/attendance/browser-relay-runtime';

export const dynamic = 'force-dynamic';

const VALID_STEPS = new Set(['observe', 'act', 'extract', 'challenge', 'human_note', 'cancel', 'complete']);

/** POST — aplica um passo (observe/act/extract/challenge/...) à sessão sandbox. */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });
    if (!body.relay_id) return NextResponse.json({ ok: false, error: 'missing_relay_id' }, { status: 400 });
    if (!VALID_STEPS.has(body.type)) return NextResponse.json({ ok: false, error: 'invalid_step_type' }, { status: 400 });

    let session;
    try { session = await getRelaySession(supabase, companyId, body.relay_id); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    if (!session) return NextResponse.json({ ok: false, error: 'relay_not_found' }, { status: 404 });

    const adapter = getBrowserRelayAdapter(session.provider);
    const updated = applyBrowserRelaySandboxStep(session, {
      type: body.type, instruction: body.instruction ?? null, selector_hint: body.selector_hint ?? null,
      query: body.query ?? null, challenge_signal: body.challenge_signal ?? null,
    }, adapter);

    try { await saveRelaySession(supabase, companyId, updated); } catch { /* best-effort */ }
    return NextResponse.json({ ok: true, relay: updated, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL RELAY STEP]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
