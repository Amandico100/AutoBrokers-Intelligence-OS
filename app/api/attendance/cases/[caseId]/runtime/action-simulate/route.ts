import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';
import { interpretInsurerReply } from '@/lib/attendance/action-engine';

export const dynamic = 'force-dynamic';

const MAX_REPLY = 2000;
const _LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
function maskPii(text: string): string {
  return (text || '').replace(_LONG_DIGITS, '[omitido]');
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/action-simulate
 *
 * Interpreta uma resposta SIMULADA da seguradora (dry-run). NÃO envia nada,
 * NÃO confirma cobertura, NÃO muda readiness. Registra evento sanitizado.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    let body: { simulated_insurer_reply?: string; company_id?: string } = {};
    try { body = (await request.json()) as typeof body; } catch { body = {}; }

    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    const supabaseAdmin = getAdminClient();
    let companyId: string | null = null;
    if (session.userId) companyId = await getCompanyId(supabaseAdmin, session.userId);
    else companyId = resolveInternalCompanyId(request, body);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const reply = typeof body.simulated_insurer_reply === 'string' ? body.simulated_insurer_reply.trim().slice(0, MAX_REPLY) : '';
    if (!reply) return NextResponse.json({ ok: false, error: 'simulated_insurer_reply obrigatório' }, { status: 400 });

    const { data: caseRow } = await supabaseAdmin
      .from('attendance_cases')
      .select('id, policy_snapshot, metadata')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });

    const hasPolicyNumber = Boolean(caseRow.policy_snapshot?.masked_policy_number);
    const interp = interpretInsurerReply(reply, { hasPolicyNumber });

    // Registra evento sanitizado no dispatch_packet dry-run (se houver).
    const event = {
      at: new Date().toISOString(),
      classification: interp.classification,
      next_step: interp.next_step,
      missing_data_request: interp.missing_data_request,
      suggested_channel: interp.suggested_channel,
      reply_excerpt: maskPii(reply).slice(0, 240),
    };
    const { data: packet } = await supabaseAdmin
      .from('dispatch_packets')
      .select('id, metadata')
      .eq('company_id', companyId)
      .eq('idempotency_key', `dispatch_dry_run:${caseId}`)
      .maybeSingle();
    if (packet?.id) {
      const pmd = packet.metadata && typeof packet.metadata === 'object' ? (packet.metadata as Record<string, any>) : {};
      const events = Array.isArray(pmd.action_simulation_events) ? pmd.action_simulation_events : [];
      events.push(event);
      await supabaseAdmin
        .from('dispatch_packets')
        .update({ metadata: { ...pmd, action_simulation_events: events.slice(-20) } })
        .eq('id', packet.id)
        .eq('company_id', companyId);
    }

    console.log(`[ACTION SIMULATE] case=${caseId} company=${companyId} class=${interp.classification} next=${interp.next_step} sent=false`);
    return NextResponse.json({
      ok: true,
      interpretation: {
        classification: interp.classification,
        next_step: interp.next_step,
        missing_data_request: interp.missing_data_request,
        suggested_channel: interp.suggested_channel,
        customer_message: interp.customer_message,
        reasoning: interp.reasoning,
      },
      external_action: { allowed: false, sent: false, reason: 'dry_run_42x0' },
    });
  } catch (error: any) {
    console.error('[ACTION SIMULATE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
