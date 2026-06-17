import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';

export const dynamic = 'force-dynamic';

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/action-approve-dry-run
 *
 * Marca o plano como aprovado para FUTURA execução (dry-run). NÃO envia nada.
 * O envio real exigirá adapter + permissão + flag (42X1+). external_action.sent=false.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    let body: { reason?: string; company_id?: string } = {};
    try { body = (await request.json()) as typeof body; } catch { body = {}; }

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

    const plan = caseRow.metadata?.external_action_plan;
    if (!plan) return NextResponse.json({ ok: false, error: 'no_action_plan', hint: 'Gere o plano (action-plan) antes de aprovar.' }, { status: 409 });
    if (plan.status !== 'ready_for_human_approval') {
      return NextResponse.json({ ok: false, error: 'plan_not_ready', plan_status: plan.status }, { status: 409 });
    }

    const approval = { approved_for_dry_run: true, approved_at: new Date().toISOString(), reason: typeof body.reason === 'string' ? body.reason.slice(0, 300) : null, by: 'human' };
    const newPlan = { ...plan, dry_run_approval: approval, external_action_sent: false };
    await supabaseAdmin
      .from('attendance_cases')
      .update({ metadata: mergeObject(caseRow.metadata, { external_action_plan: newPlan }) })
      .eq('id', caseId)
      .eq('company_id', companyId);

    console.log(`[ACTION APPROVE] case=${caseId} company=${companyId} approved_for_dry_run=true sent=false`);
    return NextResponse.json({
      ok: true,
      approval,
      note: 'Aprovado para futura execução (dry-run). Nenhuma ação externa foi enviada.',
      external_action: { allowed: false, sent: false, reason: 'dry_run_approval_only' },
    });
  } catch (error: any) {
    console.error('[ACTION APPROVE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
