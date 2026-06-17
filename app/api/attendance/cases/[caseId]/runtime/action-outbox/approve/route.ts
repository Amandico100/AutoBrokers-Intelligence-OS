import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';
import {
  approveOutboxEntry,
  buildAuditEvent,
  safeOutboxSummary,
  type ExternalActionOutboxEntry,
  type OutboxAuditEvent,
} from '@/lib/attendance/action-engine';

export const dynamic = 'force-dynamic';

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/action-outbox/approve
 * Aprova (HITL) a entrada → approved_not_sent. NUNCA envia: send_allowed/sent
 * permanecem false. Aprovação ≠ envio.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    let body: { outbox_id?: string; company_id?: string } = {};
    try { body = (await request.json()) as typeof body; } catch { body = {}; }

    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    const supabaseAdmin = getAdminClient();
    let companyId: string | null = null;
    let approver = 'internal';
    if (session.userId) { companyId = await getCompanyId(supabaseAdmin, session.userId); approver = String(session.userId); }
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
    const outbox: ExternalActionOutboxEntry[] = Array.isArray(pmd.external_action_outbox) ? pmd.external_action_outbox : [];
    if (outbox.length === 0) return NextResponse.json({ ok: false, error: 'no_outbox_entry', hint: 'Prepare o outbox antes.' }, { status: 409 });

    const targetId = body.outbox_id || outbox[outbox.length - 1].outbox_id;
    const idx = outbox.findIndex((e) => e.outbox_id === targetId);
    if (idx < 0) return NextResponse.json({ ok: false, error: 'outbox_entry_not_found' }, { status: 404 });

    const approved = approveOutboxEntry(outbox[idx], approver);
    outbox[idx] = approved;

    const audit: OutboxAuditEvent[] = Array.isArray(pmd.external_action_audit_events) ? pmd.external_action_audit_events : [];
    audit.push(buildAuditEvent('approved_not_sent', approved.outbox_id, { note: approved.status }));
    audit.push(buildAuditEvent('send_blocked_by_gate', approved.outbox_id, { blockers: approved.blockers }));

    if (packet?.id) {
      await supabaseAdmin
        .from('dispatch_packets')
        .update({ metadata: { ...pmd, external_action_outbox: outbox, external_action_audit_events: audit.slice(-50) } })
        .eq('id', packet.id)
        .eq('company_id', companyId);
    }
    await supabaseAdmin
      .from('attendance_cases')
      .update({ metadata: mergeObject(caseRow.metadata, { external_action_outbox_summary: safeOutboxSummary(outbox) }) })
      .eq('id', caseId)
      .eq('company_id', companyId);

    console.log(`[ACTION OUTBOX APPROVE] case=${caseId} company=${companyId} outbox=${approved.outbox_id} status=${approved.status} sent=false`);
    return NextResponse.json({
      ok: true,
      outbox_entry: approved,
      audit_events: audit.slice(-8),
      external_action: { allowed: false, send_allowed: false, sent: false, reason: 'approved_but_real_send_disabled_42x2' },
    });
  } catch (error: any) {
    console.error('[ACTION OUTBOX APPROVE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
