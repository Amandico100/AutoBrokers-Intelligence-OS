import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalDefinitions, listPortalAccounts, saveRelaySession } from '@/lib/attendance/portal-admin-context';
import { resolvePortalCanonical } from '@/lib/attendance/portal-admin-sanitizers';
import { getGlobalPortalCatalogSeed } from '@/lib/attendance/portal-global-catalog';
import { findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';
import { getBrowserRelayAdapter, isKnownRelayProvider } from '@/lib/attendance/browser-relay-adapters';
import { startBrowserRelaySandbox } from '@/lib/attendance/browser-relay-runtime';

export const dynamic = 'force-dynamic';

/** POST — inicia uma sessão de Browser Relay SANDBOX. Nenhum browser real. */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });

    const provider = isKnownRelayProvider(body.provider) ? body.provider : 'mock';
    const adapter = getBrowserRelayAdapter(provider);

    let definitions; let accounts;
    try { definitions = await listPortalDefinitions(supabase, companyId); accounts = await listPortalAccounts(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }

    const resolution = resolvePortalCanonical(getGlobalPortalCatalogSeed(), definitions, accounts, {
      company_id: companyId, portal_id: body.portal_id ?? null, owner_key: body.owner_key ?? null, journey: body.journey ?? null,
    });
    const account = accounts.find((a) => a.portal_account_id === body.portal_account_id)
      || accounts.find((a) => a.portal_id === resolution.portal_id);

    const session = startBrowserRelaySandbox({
      portal_id: resolution.portal_id,
      portal_account_id: account?.portal_account_id ?? body.portal_account_id ?? null,
      journey: body.journey ?? null,
      provider,
      portal_available: resolution.portal_available,
      account_present: Boolean(account),
      session_status: account?.session_ref?.status ?? null,
      session_ref_masked: account?.session_ref?.storage_ref_masked ?? null,
      allow_demo_without_account: body.allow_demo_without_account === true,
    }, adapter);

    try { await saveRelaySession(supabase, companyId, session); } catch { /* persist best-effort */ }

    console.log(`[PORTAL RELAY START] company=${companyId} portal=${resolution.portal_id} provider=${provider} status=${session.status} real_action_allowed=false`);
    return NextResponse.json({ ok: true, relay: session, resolution, adapter: { provider_key: adapter.provider_key, canOpenRealBrowser: adapter.canOpenRealBrowser }, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL RELAY START]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
