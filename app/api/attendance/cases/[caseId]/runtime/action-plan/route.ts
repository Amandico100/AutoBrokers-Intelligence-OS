import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';
import { normalizeSlots } from '@/lib/attendance/handoff-dossier';
import {
  evaluateChannelCandidates,
  buildExternalActionPlan,
  safeActionPlanSummary,
  type ChannelAvailability,
} from '@/lib/attendance/action-engine';

export const dynamic = 'force-dynamic';

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}
function safeCase(row: any): any {
  if (!row || typeof row !== 'object') return row;
  const { insured_document_ref: _omit, ...rest } = row;
  return rest;
}

async function resolveAuth(request: NextRequest, body: any) {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
  const supabaseAdmin = getAdminClient();
  let companyId: string | null = null;
  if (session.userId) companyId = await getCompanyId(supabaseAdmin, session.userId);
  else companyId = resolveInternalCompanyId(request, body);
  return { supabaseAdmin, companyId };
}

/** Avalia disponibilidade de canais (DB best-effort). No 42X0, canais da seguradora ficam dry-run/future. */
async function channelAvailability(supabaseAdmin: any, companyId: string): Promise<ChannelAvailability> {
  let humanDestination = false;
  try {
    const { data } = await supabaseAdmin
      .from('human_support_destinations')
      .select('id')
      .eq('company_id', companyId)
      .eq('is_active', true)
      .limit(1);
    humanDestination = Array.isArray(data) && data.length > 0;
  } catch {
    humanDestination = false;
  }
  // Conexões de seguradora (whatsapp/portal/api) ainda não modeladas p/ acionamento → not_configured.
  return { human_destination: humanDestination };
}

async function loadContext(supabaseAdmin: any, companyId: string, caseId: string) {
  const { data: caseRow } = await supabaseAdmin
    .from('attendance_cases')
    .select('*')
    .eq('id', caseId)
    .eq('company_id', companyId)
    .maybeSingle();
  if (!caseRow) return { caseRow: null, run: null, packet: null };
  const { data: run } = await supabaseAdmin
    .from('corridor_runs')
    .select('id, slots, diagnostics')
    .eq('case_id', caseId)
    .order('started_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  const { data: packet } = await supabaseAdmin
    .from('dispatch_packets')
    .select('id, status, metadata')
    .eq('company_id', companyId)
    .eq('idempotency_key', `dispatch_dry_run:${caseId}`)
    .maybeSingle();
  return { caseRow, run: run || null, packet: packet || null };
}

/** POST — gera/atualiza o ExternalActionPlan (dry-run). NUNCA envia externo. */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    const { supabaseAdmin, companyId } = await resolveAuth(request, body);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const { caseRow, run, packet } = await loadContext(supabaseAdmin, companyId, caseId);
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });

    const avail = await channelAvailability(supabaseAdmin, companyId);
    const channels = evaluateChannelCandidates(avail);
    const plan = buildExternalActionPlan({
      caseRow,
      dispatchPacket: packet || { id: null, metadata: {} },
      filledSlots: normalizeSlots(run?.slots).filled,
      channels,
    });

    // Persistência (sem schema novo): plano no dispatch_packet (se houver) + case.metadata.
    const summary = safeActionPlanSummary(plan);
    const newMeta = mergeObject(caseRow.metadata, { external_action_plan: plan, action_readiness: summary });
    const { data: caseAfter } = await supabaseAdmin
      .from('attendance_cases')
      .update({ metadata: newMeta })
      .eq('id', caseId)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();
    if (packet?.id) {
      const pmd = packet.metadata && typeof packet.metadata === 'object' ? packet.metadata : {};
      await supabaseAdmin
        .from('dispatch_packets')
        .update({ metadata: { ...pmd, external_action_plan: plan } })
        .eq('id', packet.id)
        .eq('company_id', companyId);
    }

    console.log(`[ACTION PLAN] case=${caseId} company=${companyId} status=${plan.status} channel=${plan.selected_channel} sent=false`);
    return NextResponse.json({
      ok: true,
      case: safeCase(caseAfter || caseRow),
      action_plan: plan,
      external_action: { allowed: false, sent: false, reason: 'dry_run_42x0' },
    });
  } catch (error: any) {
    console.error('[ACTION PLAN] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}

/** GET — retorna o plano persistido (sanitizado). */
export async function GET(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const { supabaseAdmin, companyId } = await resolveAuth(request, {});
    if (!companyId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });
    const { data: caseRow } = await supabaseAdmin
      .from('attendance_cases')
      .select('metadata')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });
    const plan = caseRow.metadata?.external_action_plan ?? null;
    return NextResponse.json({ ok: true, action_plan: plan, external_action: { allowed: false, sent: false } });
  } catch (error: any) {
    console.error('[ACTION PLAN GET] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
