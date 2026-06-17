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
import {
  resolveActiveInsurerChannelConfig,
  buildProviderPayload,
  getInsurerMessagingProvider,
} from '@/lib/attendance/insurer-channel-registry';
import { listChannelConfigs } from '@/lib/attendance/insurer-channel-store';
import { summarizeProviderHarness } from '@/lib/attendance/provider-adapters';

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

    // 42X3.1 — REUSA a config já resolvida no ExternalActionPlan (alinhamento
    // plan→execution→outbox). Só re-resolve no registry se o plano não trouxer.
    const warnings: string[] = [];
    let outboxChannel: 'insurer_whatsapp' | 'human_broker_manual' | null = null;
    let outboxProvider: string | null = null;
    let outboxDestinationMasked: string | null = null;
    let outboxConfigId: string | null = null;
    let providerPayload: Record<string, unknown> | null = null;

    if (plan?.selected_config_id && plan?.selected_provider_key) {
      // Caminho preferido: tudo vem do plano (mesma config/canal/provider).
      outboxChannel = plan.selected_channel === 'insurer_whatsapp' ? 'insurer_whatsapp' : 'human_broker_manual';
      outboxProvider = plan.selected_provider_key;
      outboxDestinationMasked = plan.selected_destination_ref_masked ?? null;
      outboxConfigId = plan.selected_config_id;
      providerPayload = plan.selected_provider_payload
        ?? buildProviderPayload(plan.selected_provider_key, {
          destination_ref_masked: plan.selected_destination_ref_masked,
          message_text: execution?.prepared_message ?? plan?.message_drafts?.[0]?.text ?? null,
        });
    } else {
      // Fallback: resolve no registry (compat com planos antigos sem config).
      let activeConfig = null;
      try {
        const configs = await listChannelConfigs(supabaseAdmin, companyId);
        activeConfig = resolveActiveInsurerChannelConfig(configs, {
          insurer_key: plan?.insurer_key ?? caseRow.metadata?.action_readiness?.insurer_key ?? null,
          corridor_key: plan?.corridor_key ?? null,
          subcorridor_key: plan?.subcorridor_key ?? null,
        });
      } catch { /* vault ausente → segue sem config (manual) */ }
      const configProvider = activeConfig ? getInsurerMessagingProvider(activeConfig.provider_key) : null;
      outboxChannel = configProvider?.channel === 'insurer_whatsapp' ? 'insurer_whatsapp' : configProvider?.channel === 'manual' ? 'human_broker_manual' : null;
      outboxProvider = activeConfig?.provider_key ?? null;
      outboxDestinationMasked = activeConfig?.destination_ref_masked ?? null;
      outboxConfigId = activeConfig?.config_id ?? null;
      providerPayload = activeConfig
        ? buildProviderPayload(activeConfig.provider_key, {
            destination_ref_masked: activeConfig.destination_ref_masked,
            message_text: execution?.prepared_message ?? plan?.message_drafts?.[0]?.text ?? null,
          })
        : null;
      // Se o plano apontou um canal e o outbox resolveu outro, registra divergência.
      if (plan?.selected_channel && outboxChannel && plan.selected_channel !== outboxChannel) {
        warnings.push('channel_plan_outbox_mismatch');
      }
    }

    // 42X4 — valida o provider via harness de homologação (sandbox; sem rede).
    const providerValidation = outboxProvider
      ? summarizeProviderHarness(outboxProvider, {
          destination_ref_masked: outboxDestinationMasked,
          message_text: execution?.prepared_message ?? plan?.message_drafts?.[0]?.text ?? null,
        })
      : null;

    const entry = buildOutboxEntry({
      case_id: caseId,
      dispatch_packet_id: packet?.id ?? null,
      execution,
      plan,
      channel: outboxChannel,
      provider: outboxProvider,
      destination_ref_masked: outboxDestinationMasked,
      provider_payload: providerPayload,
      config_id: outboxConfigId,
      provider_validation: providerValidation ? { ...providerValidation } : null,
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
    if (warnings.includes('channel_plan_outbox_mismatch')) audit.push(buildAuditEvent('outbox_prepared', entry.outbox_id, { note: 'channel_plan_outbox_mismatch' }));

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
      warnings,
      audit_events: audit.slice(-8),
      external_action: { allowed: false, send_allowed: false, sent: false, reason: 'real_send_disabled_42x2' },
    });
  } catch (error: any) {
    console.error('[ACTION OUTBOX PREPARE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
