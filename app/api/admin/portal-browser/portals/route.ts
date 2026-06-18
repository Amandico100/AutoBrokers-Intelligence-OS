import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalDefinitions, savePortalDefinition } from '@/lib/attendance/portal-admin-context';
import { buildPortalDefinitionRecord, validatePortalDefinitionInput, findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/** GET — lista portais (registry). Nenhum portal real é acessado. */
export async function GET() {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });
    let portals;
    try { portals = await listPortalDefinitions(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available', portals: [] }, { status: 200 }); }
    return NextResponse.json({ ok: true, portals, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL PORTALS GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** POST — cadastra um portal (draft por padrão). */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });

    const v = validatePortalDefinitionInput(body);
    if (!v.valid) return NextResponse.json({ ok: false, error: 'invalid_portal', details: v.errors }, { status: 400 });

    const record = buildPortalDefinitionRecord({
      portal_id: body.portal_id, label: body.label, owner_kind: body.owner_kind, owner_key: body.owner_key,
      base_url: body.base_url, login_url: body.login_url ?? null, supported_journeys: body.supported_journeys ?? [],
      auth_methods: body.auth_methods ?? [], browser_strategy: body.browser_strategy, status: body.status, notes: body.notes ?? null,
    });
    let portals;
    try { portals = await savePortalDefinition(supabase, companyId, record); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    console.log(`[PORTAL PORTALS POST] company=${companyId} portal=${record.portal_id} status=${record.status} real_action_allowed=false`);
    return NextResponse.json({ ok: true, portal: record, count: portals.length, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL PORTALS POST]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
