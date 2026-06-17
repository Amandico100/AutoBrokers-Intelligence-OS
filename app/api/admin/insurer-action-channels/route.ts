import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';
import {
  buildInsurerChannelConfig,
  sanitizeInsurerChannelConfig,
  validateProviderKey,
  safeChannelConfigSummary,
} from '@/lib/attendance/insurer-channel-registry';
import { listChannelConfigs, saveChannelConfig } from '@/lib/attendance/insurer-channel-store';

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

/** GET — lista as configs de canal de acionamento (sanitizadas). */
export async function GET() {
  try {
    const { companyId, userId } = await getAdminContext();
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let configs;
    try { configs = await listChannelConfigs(supabaseAdmin, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available', configs: [] }, { status: 200 }); }

    return NextResponse.json({
      ok: true,
      configs: configs.map(sanitizeInsurerChannelConfig),
      summary: safeChannelConfigSummary(configs),
      send_real_allowed: false,
    });
  } catch (error: any) {
    console.error('[INSURER CHANNELS GET] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** POST — cria uma config de canal. send_real_allowed sempre false. */
export async function POST(request: NextRequest) {
  try {
    const { companyId, userId } = await getAdminContext();
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }

    if (!body.insurer_key || typeof body.insurer_key !== 'string') {
      return NextResponse.json({ ok: false, error: 'insurer_key obrigatório' }, { status: 400 });
    }
    if (!validateProviderKey(body.provider_key)) {
      return NextResponse.json({ ok: false, error: 'provider_key inválido' }, { status: 400 });
    }

    const config = buildInsurerChannelConfig({
      company_id: companyId,
      insurer_key: body.insurer_key,
      corridor_key: body.corridor_key ?? null,
      subcorridor_key: body.subcorridor_key ?? null,
      provider_key: body.provider_key,
      destination_ref: body.destination_ref ?? null, // mascarado e nunca armazenado cru
      destination_kind: body.destination_kind,
      homologation_status: body.homologation_status,
      playbook_id: body.playbook_id ?? null,
      priority: body.priority,
      is_active: body.is_active,
      notes: body.notes ?? null,
    });

    let configs;
    try { configs = await saveChannelConfig(supabaseAdmin, companyId, config); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }

    console.log(`[INSURER CHANNELS POST] company=${companyId} insurer=${config.insurer_key} provider=${config.provider_key} send_real_allowed=false`);
    return NextResponse.json({
      ok: true,
      config: sanitizeInsurerChannelConfig(config),
      summary: safeChannelConfigSummary(configs),
      send_real_allowed: false,
    });
  } catch (error: any) {
    console.error('[INSURER CHANNELS POST] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
