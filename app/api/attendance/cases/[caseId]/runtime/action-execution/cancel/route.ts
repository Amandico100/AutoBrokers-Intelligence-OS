import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';
import { applyExecutionEvent, safeExecutionSessionSummary } from '@/lib/attendance/action-engine';

export const dynamic = 'force-dynamic';

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

/** POST — cancela a sessão de execução sandbox. NUNCA envia externo. */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    const supabaseAdmin = getAdminClient();
    let companyId: string | null = null;
    if (session.userId) companyId = await getCompanyId(supabaseAdmin, session.userId);
    else companyId = resolveInternalCompanyId(request, body);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const { data: caseRow } = await supabaseAdmin
      .from('attendance_cases')
      .select('id, metadata')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });

    const { data: packet } = await supabaseAdmin
      .from('dispatch_packets')
      .select('id, metadata')
      .eq('company_id', companyId)
      .eq('idempotency_key', `dispatch_dry_run:${caseId}`)
      .maybeSingle();
    const pmd = packet?.metadata && typeof packet.metadata === 'object' ? (packet.metadata as Record<string, any>) : {};
    const current = pmd.external_action_execution;
    if (!current) return NextResponse.json({ ok: false, error: 'no_execution_session' }, { status: 409 });

    const updated = applyExecutionEvent(current, { event_type: 'cancel' });
    if (packet?.id) {
      await supabaseAdmin
        .from('dispatch_packets')
        .update({ metadata: { ...pmd, external_action_execution: updated, execution_events: updated.events.slice(-30) } })
        .eq('id', packet.id)
        .eq('company_id', companyId);
    }
    await supabaseAdmin
      .from('attendance_cases')
      .update({ metadata: mergeObject(caseRow.metadata, { external_action_execution_summary: safeExecutionSessionSummary(updated) }) })
      .eq('id', caseId)
      .eq('company_id', companyId);

    return NextResponse.json({ ok: true, execution: updated, external_action: { allowed: false, sent: false } });
  } catch (error: any) {
    console.error('[ACTION EXEC CANCEL] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
