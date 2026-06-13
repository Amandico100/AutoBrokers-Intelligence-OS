import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { buildHandoffDossier, formatHandoffMarkdown } from '@/lib/attendance/handoff-dossier';

export const dynamic = 'force-dynamic';

// Colunas seguras dos destinos (SEM destination_ref cru).
const DESTINATION_SAFE_COLS =
  'id, name, destination_type, channel_provider, display_ref, is_primary, fallback_enabled, silence_minutes, priority_order, is_active';

/**
 * GET /api/attendance/cases/[caseId]/handoff-dossier
 * Gera um dossiê estruturado + markdown copiável a partir do caso.
 * READ-ONLY: não envia mensagem, não cria approval_request, não cria dispatch.
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) return NextResponse.json({ error: 'Empresa não encontrada' }, { status: 404 });

    // Caso (isolado por company_id)
    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select(
        'id, case_number, status, priority, channel, customer_name, customer_phone, intent, insurer_key, line_kind, macro_service, selected_corridor_key, selected_subcorridor_key, policy_source, policy_number, verification_status, coverage_evidence, risk_level, handoff_required, handoff_reason, summary, next_step, conversation_id, created_at, updated_at',
      )
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();

    if (caseErr) {
      console.error('[HANDOFF DOSSIER] case error:', caseErr.message);
      return NextResponse.json({ error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ error: 'Caso não encontrado' }, { status: 404 });

    // Mensagens (espelho do canal do cliente)
    let messages: any[] = [];
    if (caseRow.conversation_id) {
      const { data: msgs } = await supabaseAdmin
        .from('messages')
        .select('id, role, content, created_at')
        .eq('conversation_id', caseRow.conversation_id)
        .order('created_at', { ascending: true });
      messages = msgs || [];
    }

    // Último corridor_run + template
    const { data: run } = await supabaseAdmin
      .from('corridor_runs')
      .select('id, corridor_template_id, phase, status, slots, diagnostics, next_step')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    let template: any = null;
    if (run?.corridor_template_id) {
      const { data: tpl } = await supabaseAdmin
        .from('corridor_templates')
        .select('id, display_name, corridor_key, subcorridor_key, readiness')
        .eq('id', run.corridor_template_id)
        .maybeSingle();
      template = tpl || null;
    }

    // Dispatch packets do caso
    const { data: dispatchPackets } = await supabaseAdmin
      .from('dispatch_packets')
      .select('id, status')
      .eq('case_id', caseRow.id)
      .order('created_at', { ascending: false });

    // Destinos humanos ATIVOS da corretora (sem destination_ref cru)
    const { data: destinations } = await supabaseAdmin
      .from('human_support_destinations')
      .select(DESTINATION_SAFE_COLS)
      .eq('company_id', companyId)
      .eq('is_active', true)
      .order('is_primary', { ascending: false })
      .order('priority_order', { ascending: true });

    const dossier: any = buildHandoffDossier({
      caseRow,
      messages,
      run: run || null,
      template,
      dispatchPackets: dispatchPackets || [],
      destinations: destinations || [],
      generatedAt: new Date().toISOString(),
    });
    dossier.markdown = formatHandoffMarkdown(dossier);

    console.log(
      `[HANDOFF DOSSIER] case=${caseId} company=${companyId} hasDestination=${dossier.support_destination.configured} message_count=${dossier.messages.message_count}`,
    );

    return NextResponse.json({ dossier });
  } catch (error: any) {
    console.error('[HANDOFF DOSSIER] error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
