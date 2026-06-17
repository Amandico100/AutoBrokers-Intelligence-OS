import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';
import {
  resolveActiveInsurerChannelConfig,
  sanitizeInsurerChannelConfig,
  evaluateInsurerChannelHomologation,
} from '@/lib/attendance/insurer-channel-registry';
import { listChannelConfigs } from '@/lib/attendance/insurer-channel-store';

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

/**
 * GET /api/admin/insurer-action-channels/resolve?insurer_key=&corridor_key=&subcorridor_key=
 * Diagnóstico: mostra qual config venceria para o contexto (sanitizada).
 */
export async function GET(request: NextRequest) {
  try {
    const { companyId, userId } = await getAdminContext();
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    const { searchParams } = new URL(request.url);
    const ctx = {
      insurer_key: searchParams.get('insurer_key'),
      corridor_key: searchParams.get('corridor_key'),
      subcorridor_key: searchParams.get('subcorridor_key'),
    };

    let configs;
    try { configs = await listChannelConfigs(supabaseAdmin, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available', resolved: null }, { status: 200 }); }

    const resolved = resolveActiveInsurerChannelConfig(configs, ctx);
    return NextResponse.json({
      ok: true,
      context: ctx,
      resolved: resolved ? sanitizeInsurerChannelConfig(resolved) : null,
      homologation: resolved ? evaluateInsurerChannelHomologation(resolved) : null,
      fallback: resolved ? null : 'human_broker_manual',
      send_real_allowed: false,
    });
  } catch (error: any) {
    console.error('[INSURER CHANNELS RESOLVE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
