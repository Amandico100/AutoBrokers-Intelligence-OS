import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, listPortalDefinitions, savePortalDefinition, removePortalDefinition } from '@/lib/attendance/portal-admin-context';
import { buildPortalDefinitionRecord, validatePortalDefinitionInput, findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';

export const dynamic = 'force-dynamic';

/** PATCH — atualiza um portal preservando portal_id/created_at. */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ portalId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { portalId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });

    let defs;
    try { defs = await listPortalDefinitions(supabase, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const prev = defs.find((d) => d.portal_id === portalId);
    if (!prev) return NextResponse.json({ ok: false, error: 'portal_not_found' }, { status: 404 });

    const merged = {
      portal_id: prev.portal_id,
      label: body.label ?? prev.label,
      owner_kind: body.owner_kind ?? prev.owner_kind,
      owner_key: body.owner_key ?? prev.owner_key,
      base_url: body.base_url ?? prev.base_url,
      login_url: body.login_url !== undefined ? body.login_url : prev.login_url,
      supported_journeys: body.supported_journeys ?? prev.supported_journeys,
      auth_methods: body.auth_methods ?? prev.auth_methods,
      browser_strategy: body.browser_strategy ?? prev.browser_strategy,
      status: body.status ?? prev.status,
      notes: body.notes !== undefined ? body.notes : prev.notes,
      created_at: prev.created_at,
    };
    const v = validatePortalDefinitionInput(merged);
    if (!v.valid) return NextResponse.json({ ok: false, error: 'invalid_portal', details: v.errors }, { status: 400 });

    const record = buildPortalDefinitionRecord(merged);
    let result;
    try { result = await savePortalDefinition(supabase, companyId, record); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    return NextResponse.json({ ok: true, portal: record, count: result.length, real_action_allowed: false });
  } catch (error: any) {
    console.error('[PORTAL PORTALS PATCH]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** DELETE — remove um portal. */
export async function DELETE(_request: NextRequest, { params }: { params: Promise<{ portalId: string }> }) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { portalId } = await params;
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });
    let defs;
    try { defs = await removePortalDefinition(supabase, companyId, portalId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    return NextResponse.json({ ok: true, removed: portalId, count: defs.length });
  } catch (error: any) {
    console.error('[PORTAL PORTALS DELETE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
