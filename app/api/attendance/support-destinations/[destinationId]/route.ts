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
 * PATCH /api/attendance/support-destinations/[destinationId]
 * Atualiza campos whitelisted. Isolado por company_id; display_ref recalculado.
 */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ destinationId: string }> }) {
  try {
    const { destinationId } = await params;
    // 🔴 SPEC-EXTRA-001.3 BLOCO G — papel, origem e auditoria.
    //
    // ⚠️ `companyIdDoSeletor` devolve `string | null`: a rota NÃO TINHA o papel
    // disponível nem se quisesse conferi-lo. Por isso o conserto é TROCAR o
    // resolvedor, não acrescentar um `if`.
    const porteiro = await porteiroDeConfiguracao(request);
    if (porteiro instanceof NextResponse) return porteiro;
    const supabaseAdmin = getAdminClient();
    const companyId = porteiro.companyId;

    const { data: existing, error: findErr } = await supabaseAdmin
      .from('human_support_destinations')
      .select('id, destination_type, destination_ref')
      .eq('id', destinationId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (findErr) {
      console.error('[SUPPORT DESTINATIONS] fetch error:', findErr.message);
      return NextResponse.json({ error: 'Erro ao buscar destino' }, { status: 500 });
    }
    if (!existing) return NextResponse.json({ error: 'Destino não encontrado' }, { status: 404 });

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    const { fields, error: vErr } = buildDestinationFields(body, { partial: true });
    if (vErr || !fields) return NextResponse.json({ error: vErr || 'Dados inválidos' }, { status: 400 });
    if (Object.keys(fields).length === 0) {
      return NextResponse.json({ error: 'Nenhum campo válido para atualizar.' }, { status: 400 });
    }

    if ('tenant_connection_id' in fields && fields.tenant_connection_id) {
      const ok = await tenantConnectionBelongsToCompany(supabaseAdmin, fields.tenant_connection_id as string, companyId);
      if (!ok) return NextResponse.json({ error: 'tenant_connection_id inválido para esta corretora.' }, { status: 400 });
    }

    // Recalcula display_ref se o destination_ref mudou.
    if ('destination_ref' in fields) {
      const type = (fields.destination_type as string) || existing.destination_type;
      fields.display_ref = maskDestinationRef(fields.destination_ref as string, type);
    }

    // Apenas um primário ativo por corretora.
    if (fields.is_primary === true) {
      await demoteActivePrimaries(supabaseAdmin, companyId, destinationId);
    }

    const { data, error } = await supabaseAdmin
      .from('human_support_destinations')
      .update(fields)
      .eq('id', destinationId)
      .eq('company_id', companyId)
      .select(DESTINATION_COLUMNS)
      .maybeSingle();

    if (error) {
      if (error.code === '23505') {
        return NextResponse.json(
          { error: 'Já existe um destino primário ativo. Desmarque o atual antes de definir outro.' },
          { status: 409 },
        );
      }
      console.error('[SUPPORT DESTINATIONS] update error:', error.message);
      return NextResponse.json({ error: 'Erro ao atualizar destino' }, { status: 400 });
    }
    if (!data) return NextResponse.json({ error: 'Destino não encontrado' }, { status: 404 });

    console.log(`[SUPPORT DESTINATIONS] updated: id=${destinationId}`);
    await registrarNaAuditoria(porteiro, {
      evento: 'support_destination.write', acao: 'update',
      metadata: { destination_id: destinationId,
                  campos: Object.keys(fields || {}).sort() },
    });
    return NextResponse.json({ destination: serializeDestination(data) });
  } catch (error: any) {
    console.error('[SUPPORT DESTINATIONS] PATCH error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

/**
 * DELETE /api/attendance/support-destinations/[destinationId]
 * Soft delete: is_active=false (+ is_primary=false). Não deleta fisicamente.
 */
export async function DELETE(request: NextRequest, { params }: { params: Promise<{ destinationId: string }> }) {
  try {
    const { destinationId } = await params;
    // 🔴 SPEC-EXTRA-001.3 BLOCO G — papel, origem e auditoria.
    //
    // ⚠️ `companyIdDoSeletor` devolve `string | null`: a rota NÃO TINHA o papel
    // disponível nem se quisesse conferi-lo. Por isso o conserto é TROCAR o
    // resolvedor, não acrescentar um `if`.
    const porteiro = await porteiroDeConfiguracao(request);
    if (porteiro instanceof NextResponse) return porteiro;
    const supabaseAdmin = getAdminClient();
    const companyId = porteiro.companyId;

    const { data, error } = await supabaseAdmin
      .from('human_support_destinations')
      .update({ is_active: false, is_primary: false })
      .eq('id', destinationId)
      .eq('company_id', companyId)
      .select('id')
      .maybeSingle();

    if (error) {
      console.error('[SUPPORT DESTINATIONS] disable error:', error.message);
      return NextResponse.json({ error: 'Erro ao desativar destino' }, { status: 400 });
    }
    if (!data) return NextResponse.json({ error: 'Destino não encontrado' }, { status: 404 });

    console.log(`[SUPPORT DESTINATIONS] disabled: id=${destinationId}`);
    // 🔴 Esta é a mais grave das seis: DESATIVAR o destino deixa a corretora
    // sem para onde mandar handoff — e era o que um `member` comum conseguia.
    await registrarNaAuditoria(porteiro, {
      evento: 'support_destination.write', acao: 'disable',
      metadata: { destination_id: destinationId },
    });
    return NextResponse.json({ ok: true });
  } catch (error: any) {
    console.error('[SUPPORT DESTINATIONS] DELETE error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
