// 43P-FINAL-2A — reuso de SessionRef (independente do canary): abre NOVA sessão
// Browserbase, restaura o estado autenticado da Portal Account (Vault) e roda a
// skill read-only. GATED. storageState/connectUrl só em memória; nunca expostos.
import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalAccounts } from '@/lib/attendance/portal-admin-context';
import { guardCanary, DEFAULT_CHALLENGE_SELECTORS } from '@/lib/attendance/portal-canary-guard';
import { createSupabaseVaultAdapter } from '@/lib/attendance/portal-supabase-vault';
import { readSessionRefViaVault } from '@/lib/attendance/portal-session-vault';
import { createBrowserbaseSessionServer, withBrowserbaseConnectUrl, closeBrowserbaseSessionServer } from '@/lib/attendance/browserbase-session-server';
import { restoreStorageStateViaCdp } from '@/lib/attendance/portal-cdp-transport';
import { reuseSessionRefForReadOnly, findReuseSecrets } from '@/lib/attendance/portal-session-reuse';
import { runSessionLoginVerify, getSessionLoginVerifyContract, toSafePageLabel } from '@/lib/attendance/portal-read-only-skill';

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
    const sref = acc.session_ref;
    if (!sref) return NextResponse.json({ ok: false, error: 'no_session_ref' }, { status: 409 });

    const g = await guardCanary(supabase, { companyId: ctx.companyId, userId: ctx.userId, isMaster: ctx.isMaster }, portalAccountId, journey);
    const vault = createSupabaseVaultAdapter(supabase);
    const contract = getSessionLoginVerifyContract(g.hostAllowlist);

    const result = await reuseSessionRefForReadOnly(
      { storage_ref: sref.storage_ref ?? null, status: sref.status, expires_at: sref.expires_at ?? null, portal_id: acc.portal_id, portal_account_id: portalAccountId },
      { authorized: g.authz.authorized, blockers: g.authz.blockers },
      {
        vaultRead: async (storageRef) => readSessionRefViaVault({ company_id: ctx.companyId as string, portal_account_id: portalAccountId, storage_ref: storageRef }, vault),
        restoreAndObserve: async (storagePayload) => {
          // Nova sessão Browserbase (server-side); connectUrl só em memória.
          let sessionId: string | null = null;
          try {
            const meta = await createBrowserbaseSessionServer(g.env, undefined, { canary_id: 'reuse', portal_id: acc.portal_id, mode: 'read_only_canary' });
            sessionId = meta.session_id;
          } catch (e: any) { return { ok: false, observation: null, reason: `open_failed:${String(e?.message || '').slice(0, 30)}` }; }
          if (!sessionId) return { ok: false, observation: null, reason: 'open_failed' };
          const cdp = await withBrowserbaseConnectUrl(sessionId, g.env, async (connectUrl) => {
            const rr = await restoreStorageStateViaCdp(connectUrl, storagePayload, { challenge_selectors: DEFAULT_CHALLENGE_SELECTORS });
            return { host: rr.host, safe_page_label: toSafePageLabel(rr.page_title), auth_marker_present: rr.auth_marker_present, challenge_detected: rr.challenge_detected, available: rr.ok };
          });
          await closeBrowserbaseSessionServer(sessionId, g.env).catch(() => {});
          if (!cdp.ok || !cdp.result) return { ok: false, observation: null, reason: cdp.reason };
          const o = cdp.result as { host: string | null; safe_page_label: string | null; auth_marker_present: boolean; challenge_detected: string | null };
          return { ok: true, observation: { host: o.host, safe_page_label: o.safe_page_label, auth_marker_present: o.auth_marker_present, challenge_detected: o.challenge_detected }, reason: 'restored' };
        },
        runSkill: (observation) => runSessionLoginVerify({
          portal_id: acc.portal_id, session_state: 'healthy', has_session_ref: true, authorized: true,
          observation: observation ? { host: observation.host, page_title: observation.safe_page_label, auth_marker_present: observation.auth_marker_present, challenge_detected: observation.challenge_detected } : null,
          contract,
        }),
      },
    );

    if (findReuseSecrets(result).length > 0) return NextResponse.json({ ok: false, error: 'secret_leak_detected' }, { status: 500 });
    return NextResponse.json({ ok: result.ok, reuse: result, authorization: { authorized: g.authz.authorized, blockers: g.authz.blockers }, real_action_allowed: false });
  } catch (error: any) {
    console.error('[CANARY REUSE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
