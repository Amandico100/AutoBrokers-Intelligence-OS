import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';
import {
  buildInsurerChannelConfig,
  sanitizeInsurerChannelConfig,
  validateProviderKey,
} from '@/lib/attendance/insurer-channel-registry';
import { listChannelConfigs, saveChannelConfig, removeChannelConfig } from '@/lib/attendance/insurer-channel-store';

export const dynamic = 'force-dynamic';

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

async function getAdminContext(): Promise<{ companyId: string | null; userId: string | null }> {
  const cookieStore = await cookies();
  const adminSession = await getIronSession<AdminSessionData>(cookieStore, adminSessionOptions);
  if (adminSession.adminId) {
    if (adminSession.companyId) return { companyId: adminSession.companyId, userId: adminSession.adminId };
    const { data: u } = await supabaseAdmin.from('users_v2').select('company_id').eq('id', adminSession.adminId).single();
    return { companyId: u?.company_id ?? null, userId: adminSession.adminId };
  }
  const userSession = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (userSession.userId && userSession.companyId) return { companyId: userSession.companyId, userId: userSession.userId };
  if (userSession.userId) {
    const { data: u } = await supabaseAdmin.from('users_v2').select('company_id').eq('id', userSession.userId).single();
    return { companyId: u?.company_id ?? null, userId: userSession.userId };
  }
  return { companyId: null, userId: null };
}

/** PATCH — atualiza uma config existente. send_real_allowed continua false. */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ configId: string }> }) {
  try {
    const { configId } = await params;
    const { companyId, userId } = await getAdminContext();
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (body.provider_key !== undefined && !validateProviderKey(body.provider_key)) {
      return NextResponse.json({ ok: false, error: 'provider_key inválido' }, { status: 400 });
    }

    let existing;
    try { existing = await listChannelConfigs(supabaseAdmin, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const prev = existing.find((c) => c.config_id === configId);
    if (!prev) return NextResponse.json({ ok: false, error: 'config_not_found' }, { status: 404 });

    // Reconstrói preservando config_id/created_at; destino cru (se enviado) é remascarado.
    const updated = buildInsurerChannelConfig({
      config_id: prev.config_id,
      company_id: companyId,
      insurer_key: body.insurer_key ?? prev.insurer_key,
      corridor_key: body.corridor_key !== undefined ? body.corridor_key : prev.corridor_key,
      subcorridor_key: body.subcorridor_key !== undefined ? body.subcorridor_key : prev.subcorridor_key,
      provider_key: body.provider_key ?? prev.provider_key,
      destination_ref: body.destination_ref ?? null,
      destination_ref_masked: body.destination_ref ? null : prev.destination_ref_masked,
      destination_kind: body.destination_kind ?? prev.destination_kind,
      homologation_status: body.homologation_status ?? prev.homologation_status,
      playbook_id: body.playbook_id !== undefined ? body.playbook_id : prev.playbook_id,
      priority: body.priority ?? prev.priority,
      is_active: body.is_active !== undefined ? body.is_active : prev.is_active,
      notes: body.notes !== undefined ? body.notes : prev.notes,
      mode: body.mode ?? prev.mode,
      created_at: prev.created_at,
    });

    let configs;
    try { configs = await saveChannelConfig(supabaseAdmin, companyId, updated); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }

    return NextResponse.json({ ok: true, config: sanitizeInsurerChannelConfig(updated), count: configs.length, send_real_allowed: false });
  } catch (error: any) {
    console.error('[INSURER CHANNELS PATCH] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** DELETE — remove a config. */
export async function DELETE(request: NextRequest, { params }: { params: Promise<{ configId: string }> }) {
  try {
    const { configId } = await params;
    const { companyId, userId } = await getAdminContext();
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let configs;
    try { configs = await removeChannelConfig(supabaseAdmin, companyId, configId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }

    return NextResponse.json({ ok: true, removed: configId, count: configs.length });
  } catch (error: any) {
    console.error('[INSURER CHANNELS DELETE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
