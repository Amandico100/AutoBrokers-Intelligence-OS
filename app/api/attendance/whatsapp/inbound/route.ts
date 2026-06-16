import { NextRequest, NextResponse } from 'next/server';
import { getAdminClient } from '@/lib/attendance/support-destinations';
import { resolveAttendanceCaseForWhatsAppInbound } from '@/lib/attendance/whatsapp-case-routing';
import { resolveOutboundPolicy, mediaAckMessage, type WhatsAppMediaKind } from '@/lib/attendance/whatsapp-inbound';
import {
  resolvePolicySelectionFromCustomerReply,
  buildPolicyOptionsMessage,
  buildPolicySelectedMessage,
} from '@/lib/attendance/whatsapp-policy-selection';
import { maybePrepareDispatchDraft } from '@/lib/attendance/whatsapp-orchestration';
import { invokeRuntimeHandler } from '@/lib/attendance/runtime-invoke';
import {
  resolveAttendanceIntentAndCorridor,
  buildAttendanceCaseFieldsFromResolvedIntent,
  type AvailableCorridor,
} from '@/lib/attendance/attendance-intent-resolver';
// Handlers de runtime (invocados IN-PROCESS — sem self-fetch, ver runtime-invoke).
import { POST as replyHandler } from '@/app/api/attendance/cases/[caseId]/runtime/reply/route';
import { POST as lookupHandler } from '@/app/api/attendance/cases/[caseId]/runtime/policy-lookup/route';
import { POST as selectHandler } from '@/app/api/attendance/cases/[caseId]/runtime/policy-select/route';
import { POST as stepHandler } from '@/app/api/attendance/cases/[caseId]/runtime/step/route';
import { POST as dispatchHandler } from '@/app/api/attendance/cases/[caseId]/runtime/dispatch-dry-run/route';

export const dynamic = 'force-dynamic';

function generateCaseNumber(): string {
  return `WA-${new Date().getFullYear()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`;
}

function diag(events: string[], extra: Record<string, unknown> = {}) {
  return { provider: 'z-api', events, ...extra };
}

/** Carrega corredores ativos (global + tenant) como fonte do resolver. */
async function loadAvailableCorridors(supabaseAdmin: any, companyId: string): Promise<any[]> {
  const { data } = await supabaseAdmin
    .from('corridor_templates')
    .select('id, corridor_key, subcorridor_key, insurer_key, line_kind, macro_service, service_type, display_name, scope, company_id, required_slots')
    .eq('is_active', true)
    .or(`company_id.is.null,company_id.eq.${companyId}`);
  return Array.isArray(data) ? data : [];
}

function toAvailable(rows: any[]): AvailableCorridor[] {
  return rows.map((r) => ({
    corridor_key: r.corridor_key,
    subcorridor_key: r.subcorridor_key ?? null,
    insurer_key: r.insurer_key ?? null,
    line_kind: r.line_kind ?? null,
    macro_service: r.macro_service ?? null,
    service_type: r.service_type ?? null,
    display_name: r.display_name ?? null,
    scope: r.scope ?? (r.company_id ? 'tenant' : 'global'),
  }));
}

function requiredKeysFromTemplate(tpl: any): string[] {
  return Array.isArray(tpl?.required_slots)
    ? (tpl.required_slots as any[]).map((s) => (s && typeof s.key === 'string' ? s.key : null)).filter(Boolean)
    : ['electrical_issue_type', 'risk_indicators', 'affected_area', 'property_address_confirmed', 'policy_evidence_status'];
}

async function createCorridorRun(supabaseAdmin: any, companyId: string, caseId: string, tpl: any) {
  await supabaseAdmin.from('corridor_runs').insert({
    company_id: companyId,
    case_id: caseId,
    corridor_template_id: tpl.id,
    phase: 'collect_slots',
    status: 'active',
    slots: { filled: {}, missing: requiredKeysFromTemplate(tpl), conflicts: [] },
    diagnostics: { mvp_mode: 'dry_run_hitl', external_action_allowed: false, hitl_required: true, channel: 'whatsapp' },
    next_step: 'Perguntar uma informação por vez, começando por risco elétrico e área afetada.',
  });
}

/**
 * POST /api/attendance/whatsapp/inbound  (INTERNAL — chave Next↔Backend)
 *
 * Bridge GLOBAL (42W1.1): canal WhatsApp → Attendance Runtime, para QUALQUER
 * corredor. Resolve intenção/corredor por registry (corridor_templates), cai em
 * triagem quando não há corredor, e orquestra o runtime IN-PROCESS (sem self-fetch).
 * NUNCA envia para seguradora/prestador. Outbound DRY-RUN por padrão.
 */
export async function POST(request: NextRequest) {
  try {
    const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
    const providedKey = request.headers.get('x-autobrokers-internal-key');
    if (!internalKey || !providedKey || providedKey !== internalKey) {
      return NextResponse.json({ ok: false, error: 'unauthorized_internal' }, { status: 401 });
    }

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }
    const companyId = typeof body.company_id === 'string' ? body.company_id : '';
    const conversationId = typeof body.conversation_id === 'string' ? body.conversation_id : '';
    const agentId = typeof body.agent_id === 'string' ? body.agent_id : null;
    const userId = typeof body.user_id === 'string' ? body.user_id : null;
    const phone = typeof body.phone === 'string' ? body.phone : '';
    const text = typeof body.text === 'string' ? body.text.trim() : '';
    const mediaKind = (typeof body.media_kind === 'string' ? body.media_kind : 'text') as WhatsAppMediaKind;
    if (!companyId || !conversationId || !phone) {
      return NextResponse.json({ ok: false, error: 'missing_minimal_identifiers' }, { status: 400 });
    }

    const supabaseAdmin = getAdminClient();
    const events: string[] = ['inbound_received'];

    const outboundRealEnabled = process.env.WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED === 'true';
    const outbound = resolveOutboundPolicy({
      globalDryRun: process.env.ATTENDANCE_WHATSAPP_DRY_RUN !== 'false',
      environment: typeof body.environment === 'string' ? body.environment : null,
      externalSendAuthorized: outboundRealEnabled && body.external_send_authorized === true,
    });

    const { data: existingCase } = await supabaseAdmin
      .from('attendance_cases')
      .select('id, status, verification_status, selected_corridor_key, metadata')
      .eq('company_id', companyId)
      .eq('conversation_id', conversationId)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    const routing = resolveAttendanceCaseForWhatsAppInbound({
      existingCase: existingCase ? { id: existingCase.id, status: existingCase.status } : null,
      conversationId,
      hasProcessableText: Boolean(text),
    });
    events.push(`case_routing:${routing.action}`);

    const insertUser = (content: string, kind: WhatsAppMediaKind = 'text') =>
      supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'user', content, type: kind === 'audio' ? 'voice' : 'text' });
    const insertAssistant = (content: string) =>
      supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'assistant', content, type: 'text' });

    // Handoff humano → registra inbound, NÃO responde automaticamente.
    if (routing.action === 'handoff_block') {
      await insertUser(text || mediaAckMessage(mediaKind), mediaKind);
      events.push('handoff_blocked_auto_reply');
      return NextResponse.json({ ok: true, action: 'handoff_block', case_id: routing.case_id, auto_reply: null, outbound: { ...outbound, sent: false }, diagnostics: diag(events) });
    }

    // Mídia sem texto → ack humano seguro (não trava, não vaza URL). 42M0 fará a mídia completa.
    if (!text && mediaKind !== 'text') {
      await insertUser(`[${mediaKind}]`, mediaKind);
      const ack = mediaAckMessage(mediaKind);
      await insertAssistant(ack);
      events.push('media_ack');
      return NextResponse.json({ ok: true, action: 'media_ack', case_id: existingCase?.id ?? null, auto_reply: ack, outbound: { ...outbound, sent: false, text: ack }, diagnostics: diag(events, { media_kind: mediaKind }) });
    }

    const defaultCorridorKey = process.env.ATTENDANCE_DEFAULT_CORRIDOR_KEY || null;
    const defaultSubcorridorKey = process.env.ATTENDANCE_DEFAULT_SUBCORRIDOR_KEY || null;

    // Seleção conversacional de apólice (case aberto em multiple_matches).
    const pendingLookup = existingCase?.metadata?.policy_lookup;
    if (
      routing.action === 'reply_existing' &&
      pendingLookup?.status === 'multiple_matches' &&
      Array.isArray(pendingLookup.matches) &&
      pendingLookup.matches.length > 0 &&
      text
    ) {
      const matches = pendingLookup.matches;
      await insertUser(text);
      const sel = resolvePolicySelectionFromCustomerReply(text, matches);
      if (sel.resolved && sel.policy_ref) {
        const picked = matches.find((mm: any) => String(mm.policy_ref) === String(sel.policy_ref));
        const selRes = await invokeRuntimeHandler(selectHandler, { caseId: existingCase!.id, internalKey, body: { company_id: companyId, source: 'infocap', policy_ref: sel.policy_ref } });
        const ok = selRes.ok && selRes.json?.ok;
        let reply = ok ? buildPolicySelectedMessage(picked) : 'Tive um problema para registrar essa apólice agora. Pode tentar novamente em instantes?';
        let draftState: string | null = null;
        if (ok) {
          const draft = await maybePrepareDispatchDraft({
            verificationStatus: selRes.json?.case?.verification_status ?? 'verified_by_connector',
            runDispatch: () => invokeRuntimeHandler(dispatchHandler, { caseId: existingCase!.id, internalKey, body: { company_id: companyId } }),
          });
          draftState = draft.packet_state;
          if (draft.message) reply = `${reply} ${draft.message}`;
        }
        await insertAssistant(reply);
        events.push(ok ? 'policy_selection_resolved' : 'policy_selection_failed');
        if (draftState) events.push('dispatch_draft_auto_prepared');
        events.push('outbound_dry_run');
        return NextResponse.json({ ok: true, action: 'policy_selected', case_id: existingCase!.id, selected_policy_ref: ok ? sel.policy_ref : null, dispatch_packet_state: draftState, auto_reply: reply, outbound: { ...outbound, sent: false, text: reply }, diagnostics: diag(events, { selection_strategy: sel.strategy }) });
      }
      const optionsMsg = buildPolicyOptionsMessage(matches);
      await insertAssistant(optionsMsg);
      events.push('policy_selection_ambiguous', 'outbound_dry_run');
      return NextResponse.json({ ok: true, action: 'policy_selection_pending', case_id: existingCase!.id, auto_reply: optionsMsg, outbound: { ...outbound, sent: false, text: optionsMsg }, diagnostics: diag(events, { selection_strategy: sel.strategy }) });
    }

    // Resolver global de intenção/corredor — para create_case OU upgrade de triagem.
    let caseId = routing.case_id;
    const isTriageExisting = routing.action === 'reply_existing' && existingCase != null && !existingCase.selected_corridor_key;

    if (routing.action === 'create_case' || isTriageExisting) {
      const corridorRows = await loadAvailableCorridors(supabaseAdmin, companyId);
      const resolved = resolveAttendanceIntentAndCorridor({
        text,
        availableCorridors: toAvailable(corridorRows),
        defaultCorridorKey,
        defaultSubcorridorKey,
      });
      const fields = buildAttendanceCaseFieldsFromResolvedIntent(resolved, { channel: 'whatsapp' });
      const matchedTpl = resolved.selected_corridor_key
        ? corridorRows.find((r) => r.corridor_key === resolved.selected_corridor_key && (r.subcorridor_key ?? null) === (resolved.selected_subcorridor_key ?? null))
        : null;
      events.push(`intent:${resolved.intent}`, `corridor:${resolved.selected_corridor_key || 'triage'}`);

      if (routing.action === 'create_case') {
        const { data: createdCase, error: caseErr } = await supabaseAdmin
          .from('attendance_cases')
          .insert({
            company_id: companyId,
            conversation_id: conversationId,
            assigned_agent_id: agentId,
            assigned_user_id: userId,
            case_number: generateCaseNumber(),
            status: fields.status,
            priority: 'normal',
            channel: 'whatsapp',
            customer_phone: phone,
            intent: fields.intent,
            insurer_key: fields.insurer_key,
            line_kind: fields.line_kind,
            macro_service: fields.macro_service,
            selected_corridor_key: fields.selected_corridor_key,
            selected_subcorridor_key: fields.selected_subcorridor_key,
            policy_source: 'unknown',
            verification_status: 'unverified',
            risk_level: 'low',
            handoff_required: false,
            summary: fields.summary,
            next_step: fields.next_step,
            metadata: { channel: 'whatsapp', resolved_intent: { intent: resolved.intent, confidence: resolved.confidence, reason: resolved.reason } },
          })
          .select('id')
          .single();
        if (caseErr || !createdCase) {
          console.error('[WA INBOUND] case insert error:', caseErr?.message);
          return NextResponse.json({ ok: false, error: 'case_create_failed' }, { status: 500 });
        }
        const newCaseId: string = createdCase.id;
        caseId = newCaseId;
        if (matchedTpl) {
          await createCorridorRun(supabaseAdmin, companyId, newCaseId, matchedTpl);
          events.push('case_created');
        } else {
          // Triagem: sem corredor → sem run falso. Pergunta esclarecedora.
          await insertUser(text);
          await insertAssistant(fields.next_step);
          events.push('triage_created', 'outbound_dry_run');
          return NextResponse.json({ ok: true, action: 'triage', case_id: caseId, intent: resolved.intent, auto_reply: fields.next_step, outbound: { ...outbound, sent: false, text: fields.next_step }, diagnostics: diag(events) });
        }
      } else if (isTriageExisting) {
        if (matchedTpl && resolved.selected_corridor_key) {
          await supabaseAdmin
            .from('attendance_cases')
            .update({
              status: 'collecting_slots',
              intent: fields.intent,
              insurer_key: fields.insurer_key,
              line_kind: fields.line_kind,
              macro_service: fields.macro_service,
              selected_corridor_key: fields.selected_corridor_key,
              selected_subcorridor_key: fields.selected_subcorridor_key,
              summary: fields.summary,
              next_step: fields.next_step,
            })
            .eq('id', existingCase!.id)
            .eq('company_id', companyId);
          await createCorridorRun(supabaseAdmin, companyId, existingCase!.id, matchedTpl);
          caseId = existingCase!.id;
          events.push('triage_upgraded');
          // segue para o reply (que registra a mensagem e conduz o intake)
        } else {
          // continua em triagem → re-pergunta.
          await insertUser(text);
          await insertAssistant(fields.next_step);
          events.push('triage_reask', 'outbound_dry_run');
          return NextResponse.json({ ok: true, action: 'triage_pending', case_id: existingCase!.id, intent: resolved.intent, auto_reply: fields.next_step, outbound: { ...outbound, sent: false, text: fields.next_step }, diagnostics: diag(events) });
        }
      }
    }

    if (!caseId) {
      return NextResponse.json({ ok: false, error: 'case_unresolved' }, { status: 500 });
    }

    // 1) Runtime reply IN-PROCESS (mesmo cérebro do dashboard). Salva user+assistant.
    events.push('runtime_reply_called');
    const replyRes = await invokeRuntimeHandler(replyHandler, { caseId, internalKey, body: { company_id: companyId, message: text, source: 'whatsapp' } });
    if (!replyRes.ok) {
      return NextResponse.json({ ok: false, error: 'runtime_reply_failed', case_id: caseId, detail: replyRes.json?.error ?? null }, { status: 502 });
    }
    let assistantText: string | null = replyRes.json?.next_step?.question ?? null;
    const runtimeStatus: string | null = replyRes.json?.next_step?.status ?? null;
    const macroState: string | null = replyRes.json?.case?.metadata?.attendance_macro_state ?? null;
    let verification: string | null = replyRes.json?.case?.verification_status ?? null;
    let dispatchState: string | null = null;

    // 2) Avanço autônomo: gate de apólice → lookup InfoCap.
    if (macroState === 'policy_lookup_required') {
      events.push('policy_lookup_auto');
      const lk = await invokeRuntimeHandler(lookupHandler, { caseId, internalKey, body: { company_id: companyId, source: 'infocap', mode: 'connector' } });
      const plr = lk.json?.policy_lookup_result;
      const st = plr?.status;
      if (st === 'multiple_matches' && Array.isArray(plr.matches) && plr.matches.length > 0) {
        assistantText = buildPolicyOptionsMessage(plr.matches);
        await insertAssistant(assistantText);
        events.push('policy_lookup_multiple_matches');
      } else if (st === 'found') {
        const stp = await invokeRuntimeHandler(stepHandler, { caseId, internalKey, body: { company_id: companyId, source: 'whatsapp' } });
        assistantText = stp.json?.step?.question ?? assistantText;
        verification = stp.json?.case?.verification_status ?? verification;
        events.push('policy_lookup_found');
      } else {
        assistantText = lk.json?.next_step ?? assistantText;
        events.push(`policy_lookup_${st || 'unresolved'}`);
      }
    }

    // 3) Dispatch draft idempotente quando evidência pronta.
    const draft = await maybePrepareDispatchDraft({
      verificationStatus: verification,
      runDispatch: () => invokeRuntimeHandler(dispatchHandler, { caseId: caseId as string, internalKey, body: { company_id: companyId } }),
    });
    if (draft.prepared) {
      dispatchState = draft.packet_state;
      events.push('dispatch_draft_auto_prepared');
      if (draft.message) {
        assistantText = assistantText ? `${assistantText} ${draft.message}` : draft.message;
        await insertAssistant(draft.message);
      }
    }

    events.push(outbound.dry_run ? 'outbound_dry_run' : 'outbound_sent');
    return NextResponse.json({
      ok: true,
      action: routing.action === 'create_case' ? 'create_case' : 'reply_existing',
      case_id: caseId,
      runtime_status: runtimeStatus,
      macro_state: macroState,
      dispatch_packet_state: dispatchState,
      auto_reply: assistantText,
      outbound: { ...outbound, sent: false, text: assistantText },
      diagnostics: diag(events),
    });
  } catch (error: any) {
    console.error('[WA INBOUND] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'internal_error' }, { status: 500 });
  }
}
