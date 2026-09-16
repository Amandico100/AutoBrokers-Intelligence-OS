import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import {
  DESTINATION_COLUMNS,
  buildDestinationFields,
  demoteActivePrimaries,
  getAdminClient,
  SEM_CORRETORA_NA_SESSAO,
  companyIdDoSeletor,
  maskDestinationRef,
  serializeDestination,
  tenantConnectionBelongsToCompany,
} from '@/lib/attendance/support-destinations';
import { porteiroDeConfiguracao, registrarNaAuditoria } from '@/lib/admin/porteiro-de-configuracao';

export const dynamic = 'force-dynamic';

/**
 * GET /api/attendance/support-destinations
 * Lista destinos humanos de suporte da corretora do usuário logado.
 * Query: active=true|false|all, type, provider. Nunca retorna destination_ref cru.
 */
export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

    const supabaseAdmin = getAdminClient();
    // A corretora do SELETOR (SPEC-098). Vínculo caiu → 403, nunca a primária.
    const companyId = await companyIdDoSeletor();
    if (!companyId) return NextResponse.json({ error: SEM_CORRETORA_NA_SESSAO }, { status: 403 });

    const { searchParams } = new URL(request.url);
    const active = searchParams.get('active');
    const type = searchParams.get('type');
    const provider = searchParams.get('provider');

    let query = supabaseAdmin
      .from('human_support_destinations')
      .select(DESTINATION_COLUMNS)
      .eq('company_id', companyId)
      .order('is_primary', { ascending: false })
      .order('priority_order', { ascending: true })
      .order('created_at', { ascending: true });

    if (active === 'false') query = query.eq('is_active', false);
    else if (active !== 'all') query = query.eq('is_active', true);
    if (type) query = query.eq('destination_type', type);
    if (provider) query = query.eq('channel_provider', provider);

    const { data, error } = await query;
    if (error) {
      console.error('[SUPPORT DESTINATIONS] list error:', error.message);
      return NextResponse.json({ error: 'Erro ao buscar destinos' }, { status: 500 });
    }

    const destinations = (data || []).map(serializeDestination);
    console.log(`[SUPPORT DESTINATIONS] list: ${destinations.length} destinations`);
    return NextResponse.json({ destinations });
  } catch (error: any) {
    console.error('[SUPPORT DESTINATIONS] GET error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

/**
 * POST /api/attendance/support-destinations
 * Cria um destino. company_id derivado do usuário; display_ref calculado no server.
 */
export async function POST(request: NextRequest) {
  try {
    // 🔴 SPEC-EXTRA-001.3 BLOCO G — papel, origem e auditoria.
    //
    // ⚠️ `companyIdDoSeletor` devolve `string | null`: a rota NÃO TINHA o papel
    // disponível nem se quisesse conferi-lo. Por isso o conserto é TROCAR o
    // resolvedor, não acrescentar um `if`.
    const porteiro = await porteiroDeConfiguracao(request);
    if (porteiro instanceof NextResponse) return porteiro;
    const supabaseAdmin = getAdminClient();
    const companyId = porteiro.companyId;

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    const { fields, error: vErr } = buildDestinationFields(body, { partial: false });
    if (vErr || !fields) return NextResponse.json({ error: vErr || 'Dados inválidos' }, { status: 400 });

    // tenant_connection_id (opcional) deve pertencer à mesma corretora.
    if (fields.tenant_connection_id) {
      const ok = await tenantConnectionBelongsToCompany(supabaseAdmin, fields.tenant_connection_id as string, companyId);
      if (!ok) return NextResponse.json({ error: 'tenant_connection_id inválido para esta corretora.' }, { status: 400 });
    }

    // display_ref mascarado no server.
    const ref = fields.destination_ref as string;
    fields.display_ref = maskDestinationRef(ref, fields.destination_type as string);

    // Apenas um primário ativo por corretora.
    if (fields.is_primary === true) {
      await demoteActivePrimaries(supabaseAdmin, companyId);
    }

    const record = { ...fields, company_id: companyId };
    const { data, error } = await supabaseAdmin
      .from('human_support_destinations')
      .insert([record])
      .select(DESTINATION_COLUMNS)
      .single();

    if (error) {
      if (error.code === '23505') {
        return NextResponse.json(
          { error: 'Já existe um destino primário ativo. Desmarque o atual antes de definir outro.' },
          { status: 409 },
        );
      }
      console.error('[SUPPORT DESTINATIONS] create error:', error.message);
      return NextResponse.json({ error: 'Erro ao criar destino' }, { status: 500 });
    }

    console.log(
      `[SUPPORT DESTINATIONS] created: id=${data.id} type=${data.destination_type} provider=${data.channel_provider}`,
    );
    // ⛔ A auditoria nunca leva `destination_ref` cru — só o TIPO e o id.
    await registrarNaAuditoria(porteiro, {
      evento: 'support_destination.write', acao: 'create',
      metadata: { destination_id: data.id, destination_type: data.destination_type,
                  is_primary: Boolean(data.is_primary) },
    });
    return NextResponse.json({ destination: serializeDestination(data) }, { status: 201 });
  } catch (error: any) {
    console.error('[SUPPORT DESTINATIONS] POST error:', error?.message);
    return NextResponse.json({ error: 'Erro interno ao criar destino' }, { status: 500 });
  }
}
