import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';
import { listChannelConfigs } from '@/lib/attendance/insurer-channel-store';
import {
  getProviderAdapter,
  buildProviderHomologationChecklist,
  summarizeProviderHarness,
} from '@/lib/attendance/provider-adapters';

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
 * POST /api/admin/insurer-action-channels/[configId]/homologation-check
 * Roda o harness de homologação do adapter do provider da config. NUNCA envia.
 */
export async function POST(_request: NextRequest, { params }: { params: Promise<{ configId: string }> }) {
  try {
    const { configId } = await params;
    const { companyId, userId } = await getAdminContext();
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let configs;
    try { configs = await listChannelConfigs(supabaseAdmin, companyId); }
    catch (e: any) { return NextResponse.json({ ok: false, error: e?.message || 'vault_not_available' }, { status: 200 }); }
    const config = configs.find((c) => c.config_id === configId);
    if (!config) return NextResponse.json({ ok: false, error: 'config_not_found' }, { status: 404 });

    const adapter = getProviderAdapter(config.provider_key);
    if (!adapter) {
      return NextResponse.json({
        ok: true,
        provider: config.provider_key,
        research_status: 'research_required',
        can_send_real: false,
        config_validation: { valid: false, errors: ['unknown_provider_error'], warnings: [] },
        blockers: ['unknown_provider'],
      });
    }

    const ctx = {
      destination_ref_masked: config.destination_ref_masked,
      message_text: 'Mensagem de homologação (sandbox).',
      credential_present: false, // presence-check apenas; segredo nunca lido neste batch
      phone_number_id_present: false,
      within_24h_window: true,
    };

    const configValidation = adapter.validateConfig(ctx);
    const payload = adapter.buildTextPayload({ destination_ref_masked: config.destination_ref_masked, message_text: ctx.message_text }, ctx);
    const payloadValidation = adapter.validatePayload(payload);
    const mock = adapter.mockSend(payload, ctx);
    const checklist = buildProviderHomologationChecklist(config.provider_key, ctx);
    const summary = summarizeProviderHarness(config.provider_key, ctx);

    console.log(`[HOMOLOGATION CHECK] company=${companyId} config=${configId} provider=${config.provider_key} can_send_real=false`);
    return NextResponse.json({
      ok: true,
      provider: config.provider_key,
      label: adapter.label,
      research_status: adapter.research_status,
      docs_url: adapter.docs_url,
      can_send_real: false,
      config_validation: configValidation,
      payload_validation: payloadValidation,
      // payload é sanitizado por construção (destino mascarado, só nomes de header).
      payload_preview: payload,
      mock_send: mock,
      checklist,
      summary,
      blockers: checklist.blockers,
    });
  } catch (error: any) {
    console.error('[HOMOLOGATION CHECK] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
