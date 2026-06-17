import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';
import {
  buildOutboxEntry,
  evaluateExternalSendPermission,
  getChannelAdapter,
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

function readFlags() {
  return {
    realEnabled: process.env.EXTERNAL_ACTION_REAL_ENABLED === 'true',
    insurerWhatsappRealSend: process.env.INSURER_WHATSAPP_REAL_SEND_ENABLED === 'true',
    // Safe default: kill switch ATIVO a menos que explicitamente desligado.
    killSwitchActive: process.env.EXTERNAL_ACTION_KILL_SWITCH !== 'false',
    rateLimitPerHour: Number(process.env.EXTERNAL_ACTION_RATE_LIMIT_PER_HOUR ?? '20') || 20,
  };
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/action-outbox/prepare
 * Cria uma entrada de outbox (draft/awaiting_approval) e avalia os gates de
 * permissão. NUNCA envia: send_allowed/sent sempre false.
 */
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

    const plan = caseRow.metadata?.external_action_plan ?? null;
    if (!plan) return NextResponse.json({ ok: false, error: 'no_action_plan', hint: 'Gere o action-plan antes.' }, { status: 409 });

    const { data: packet } = await supabaseAdmin
      .from('dispatch_packets')
      .select('id, metadata')
      .eq('company_id', companyId)
      .eq('idempotency_key', `dispatch_dry_run:${caseId}`)
      .maybeSingle();
    const pmd = packet?.metadata && typeof packet.metadata === 'object' ? (packet.metadata as Record<string, any>) : {};
    const execution = pmd.external_action_execution ?? null;

    const entry = buildOutboxEntry({
      case_id: caseId,
      dispatch_packet_id: packet?.id ?? null,
      execution,
      plan,
    });

    // tenant_connection: consulta defensiva (tabela pode não existir/ter linhas).
    let tenantConnectionStatus: string | null = null;
    let credentialRefPresent = false;
    try {
      const { data: tc } = await supabaseAdmin
        .from('tenant_connections')
        .select('status, encrypted_secret_ref')
        .eq('company_id', companyId)
        .eq('status', 'connected')
        .limit(1)
        .maybeSingle();
      if (tc) { tenantConnectionStatus = tc.status; credentialRefPresent = Boolean(tc.encrypted_secret_ref); }
    } catch { /* tabela ausente → segue bloqueado */ }

    const flags = readFlags();
    const adapter = getChannelAdapter(entry.channel);
    const dispatchReadiness = caseRow.metadata?.dispatch_readiness ?? {};
    const coverageState = caseRow.metadata?.action_readiness?.coverage_state ?? plan?.coverage_gate?.state ?? null;

    // Rate-limit: contar entradas na última hora.
    const existingOutbox: ExternalActionOutboxEntry[] = Array.isArray(pmd.external_action_outbox) ? pmd.external_action_outbox : [];
    const hourAgo = Date.now() - 3600_000;
    const usedLastHour = existingOutbox.filter((e) => new Date(e.created_at).getTime() >= hourAgo).length;

    const permission = evaluateExternalSendPermission({
      realEnabled: flags.realEnabled,
      insurerWhatsappRealSend: flags.insurerWhatsappRealSend,
      killSwitchActive: flags.killSwitchActive,
      adapterCanSendReal: adapter.canSendReal,
      tenantConnectionStatus,
      credentialRefPresent,
      actionPlanStatus: plan?.status ?? null,
      executionStatus: execution?.status ?? null,
      coverageState,
      packetState: dispatchReadiness?.packet_state ?? null,
      approvalStatus: null, // ainda não aprovado
      rateLimit: { used: usedLastHour, limit: flags.rateLimitPerHour },
      channelHomologated: false, // nenhum canal homologado no 42X2
      piiViolation: false,
    });

    const audit: OutboxAuditEvent[] = Array.isArray(pmd.external_action_audit_events) ? pmd.external_action_audit_events : [];
    audit.push(buildAuditEvent('outbox_prepared', entry.outbox_id, { note: entry.status }));
    audit.push(buildAuditEvent('approval_requested', entry.outbox_id));
    audit.push(buildAuditEvent('permission_evaluated', entry.outbox_id, { blockers: permission.blockers }));
    if (!adapter.canSendReal) audit.push(buildAuditEvent('adapter_not_real_enabled', entry.outbox_id, { note: adapter.adapter_id }));

    const outbox = [...existingOutbox, entry];
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

    console.log(`[ACTION OUTBOX PREPARE] case=${caseId} company=${companyId} status=${entry.status} send_allowed=false sent=false`);
    return NextResponse.json({
      ok: true,
      outbox_entry: entry,
      permission,
      audit_events: audit.slice(-8),
      external_action: { allowed: false, send_allowed: false, sent: false, reason: 'real_send_disabled_42x2' },
    });
  } catch (error: any) {
    console.error('[ACTION OUTBOX PREPARE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
