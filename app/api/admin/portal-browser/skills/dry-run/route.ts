import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts, saveSkillRun } from '@/lib/attendance/portal-admin-context';
import { findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';
import { getPortalSkill } from '@/lib/attendance/portal-skills';
import { getPortalMapForPortal } from '@/lib/attendance/portal-maps';
import { getBrowserRelayAdapter, isKnownRelayProvider } from '@/lib/attendance/browser-relay-adapters';
import { startBrowserRelaySandbox, applyBrowserRelaySandboxStep } from '@/lib/attendance/browser-relay-runtime';
import { runPortalSkillDryRun, sanitizePortalSkillRun } from '@/lib/attendance/portal-skill-runner';

export const dynamic = 'force-dynamic';

/** POST — roda uma Portal Skill em DRY-RUN sobre o Browser Relay Sandbox. Nenhum portal real. */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });
    if (!body.portal_id) return NextResponse.json({ ok: false, error: 'missing_portal_id' }, { status: 400 });

    const skillKey = body.skill_key || 'login_check';
    const skill = getPortalSkill(body.portal_id, skillKey);
    if (!skill) return NextResponse.json({ ok: false, error: 'skill_not_found', hint: 'portal/skill_key sem skill definida' }, { status: 404 });
    const map = getPortalMapForPortal(body.portal_id, skill.journey);

    const provider = isKnownRelayProvider(body.provider) ? body.provider : 'mock';
    const adapter = getBrowserRelayAdapter(provider);

    let accounts;
    try { accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const account = accounts.find((a) => a.portal_account_id === body.portal_account_id)
      || accounts.find((a) => a.portal_id === body.portal_id);

    const run = runPortalSkillDryRun({
      skill, map,
      portal_id: body.portal_id,
      portal_account_id: account?.portal_account_id ?? body.portal_account_id ?? null,
      account_present: Boolean(account),
      credential_present: Boolean(account?.credential_ref),
      session_status: account?.session_ref?.status ?? null,
      provider,
      inject_challenge: typeof body.inject_challenge === 'string' ? body.inject_challenge : null,
    }, { adapter, startRelay: startBrowserRelaySandbox, applyStep: applyBrowserRelaySandboxStep });

    try { await saveSkillRun(supabase, companyId, run); } catch { /* best-effort */ }

    console.log(`[PORTAL SKILL DRY-RUN] company=${companyId} portal=${body.portal_id} skill=${skillKey} status=${run.status} passed=${run.eval?.passed} real_action_allowed=false`);
    return NextResponse.json({ ok: true, run: sanitizePortalSkillRun(run), eval: run.eval, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL SKILL DRY-RUN]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
