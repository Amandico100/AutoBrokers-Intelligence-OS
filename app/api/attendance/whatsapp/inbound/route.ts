import { NextRequest, NextResponse } from 'next/server';
import { getAdminClient } from '@/lib/attendance/support-destinations';
import {
  resolveAttendanceCaseForWhatsAppInbound,
  inferSubcorridorFromText,
} from '@/lib/attendance/whatsapp-case-routing';
import { resolveOutboundPolicy, mediaAckMessage, type WhatsAppMediaKind } from '@/lib/attendance/whatsapp-inbound';
import {
  resolvePolicySelectionFromCustomerReply,
  buildPolicyOptionsMessage,
  buildPolicySelectedMessage,
} from '@/lib/attendance/whatsapp-policy-selection';
import { maybePrepareDispatchDraft, callRuntimeInternal } from '@/lib/attendance/whatsapp-orchestration';

export const dynamic = 'force-dynamic';

/**
 * POST /api/attendance/whatsapp/inbound  (INTERNAL — chave Next↔Backend)
 *
 * Bridge entre o webhook WhatsApp do Smith (FastAPI) e o Attendance Runtime (Next).
 * NÃO é um runtime paralelo: faz case routing + persiste inbound + delega ao
 * runtime/reply (mesmo cérebro do dashboard). Outbound é DRY-RUN por padrão.
 * NUNCA envia para seguradora/prestador. NUNCA expõe telefone cru/token/payload.
 *
 * Body: { company_id, agent_id?, user_id?, conversation_id, phone, connected_phone?,
 *         sender_name?, message_id?, text?, media_kind?, environment?, external_send_authorized? }
 */
function generateCaseNumber(): string {
  const now = new Date();
  const y = now.getFullYear();
  const rand = Math.random().toString(36).slice(2, 7).toUpperCase();
  return `WA-${y}-${rand}`;
}

function diag(events: string[], extra: Record<string, unknown> = {}) {
  return { provider: 'z-api', events, ...extra };
}

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

    // Política de outbound (dry-run conservador). Envio real exige a flag explícita
    // WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED=true (default false) — evita envio acidental.
    const outboundRealEnabled = process.env.WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED === 'true';
    const outbound = resolveOutboundPolicy({
      globalDryRun: process.env.ATTENDANCE_WHATSAPP_DRY_RUN !== 'false',
      environment: typeof body.environment === 'string' ? body.environment : null,
      externalSendAuthorized: outboundRealEnabled && body.external_send_authorized === true,
    });

    // Último attendance_case da conversation (company-scoped).
    const { data: existingCase } = await supabaseAdmin
      .from('attendance_cases')
      .select('id, status, verification_status, metadata')
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

    // Handoff humano → registra inbound, NÃO responde automaticamente.
    if (routing.action === 'handoff_block') {
      const content = text || mediaAckMessage(mediaKind);
      await supabaseAdmin
        .from('messages')
        .insert({ conversation_id: conversationId, role: 'user', content, type: mediaKind === 'audio' ? 'voice' : 'text' });
      events.push('handoff_blocked_auto_reply');
      return NextResponse.json({
        ok: true,
        action: 'handoff_block',
        case_id: routing.case_id,
        auto_reply: null,
        outbound: { ...outbound, sent: false },
        diagnostics: diag(events),
      });
    }

    // Mídia sem texto → ack humano seguro (não trava, não vaza URL).
    if (!text && mediaKind !== 'text') {
      await supabaseAdmin
        .from('messages')
        .insert({ conversation_id: conversationId, role: 'user', content: `[${mediaKind}]`, type: mediaKind === 'audio' ? 'voice' : 'text' });
      const ack = mediaAckMessage(mediaKind);
      await supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'assistant', content: ack, type: 'text' });
      events.push('media_ack');
      return NextResponse.json({
        ok: true,
        action: routing.action === 'create_case' ? 'media_pending_case' : 'media_ack',
        case_id: routing.case_id,
        auto_reply: ack,
        outbound: { ...outbound, sent: false, text: ack },
        diagnostics: diag(events, { media_kind: mediaKind }),
      });
    }

    const origin = request.nextUrl.origin;

    // Seleção conversacional de apólice: case aberto em multiple_matches + resposta do cliente.
    const pendingLookup = existingCase?.metadata?.policy_lookup;
    if (
      routing.action === 'reply_existing' &&
      pendingLookup?.status === 'multiple_matches' &&
      Array.isArray(pendingLookup.matches) &&
      pendingLookup.matches.length > 0 &&
      text
    ) {
      const matches = pendingLookup.matches;
      // Registra a mensagem do cliente (não vamos pelo reply neste branch).
      await supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'user', content: text, type: 'text' });
      const sel = resolvePolicySelectionFromCustomerReply(text, matches);
      if (sel.resolved && sel.policy_ref) {
        const picked = matches.find((mm: any) => String(mm.policy_ref) === String(sel.policy_ref));
        const selRes = await callRuntimeInternal(
          origin,
          `/api/attendance/cases/${existingCase!.id}/runtime/policy-select`,
          internalKey,
          { company_id: companyId, source: 'infocap', policy_ref: sel.policy_ref },
        );
        const ok = selRes.ok && selRes.json?.ok;
        let reply = ok
          ? buildPolicySelectedMessage(picked)
          : 'Tive um problema para registrar essa apólice agora. Pode tentar novamente em instantes?';
        let draftState: string | null = null;
        if (ok) {
          const draft = await maybePrepareDispatchDraft({
            origin,
            internalKey,
            companyId,
            caseId: existingCase!.id,
            verificationStatus: selRes.json?.case?.verification_status ?? 'verified_by_connector',
          });
          draftState = draft.packet_state;
          if (draft.message) reply = `${reply} ${draft.message}`;
        }
        await supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'assistant', content: reply, type: 'text' });
        events.push(ok ? 'policy_selection_resolved' : 'policy_selection_failed');
        if (draftState) events.push('dispatch_draft_auto_prepared');
        events.push('outbound_dry_run');
        return NextResponse.json({
          ok: true,
          action: 'policy_selected',
          case_id: existingCase!.id,
          selected_policy_ref: ok ? sel.policy_ref : null,
          dispatch_packet_state: draftState,
          auto_reply: reply,
          outbound: { ...outbound, sent: false, text: reply },
          diagnostics: diag(events, { selection_strategy: sel.strategy }),
        });
      }
      // Ambíguo → pede seleção com lista curta mascarada.
      const optionsMsg = buildPolicyOptionsMessage(matches);
      await supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'assistant', content: optionsMsg, type: 'text' });
      events.push('policy_selection_ambiguous');
      events.push('outbound_dry_run');
      return NextResponse.json({
        ok: true,
        action: 'policy_selection_pending',
        case_id: existingCase!.id,
        auto_reply: optionsMsg,
        outbound: { ...outbound, sent: false, text: optionsMsg },
        diagnostics: diag(events, { selection_strategy: sel.strategy }),
      });
    }

    // create_case → cria attendance_case + corridor_run ligado à conversation existente.
    let caseId = routing.case_id;
    if (routing.action === 'create_case') {
      const subcorridorKey = inferSubcorridorFromText(text) || 'electrician';
      const { data: template } = await supabaseAdmin
        .from('corridor_templates')
        .select('id, required_slots, readiness')
        .eq('corridor_key', 'allianz_residential_assistance')
        .eq('subcorridor_key', subcorridorKey)
        .eq('is_active', true)
        .is('company_id', null)
        .maybeSingle();
      if (!template) {
        return NextResponse.json({ ok: false, error: 'corridor_template_not_found' }, { status: 404 });
      }
      const { data: createdCase, error: caseErr } = await supabaseAdmin
        .from('attendance_cases')
        .insert({
          company_id: companyId,
          conversation_id: conversationId,
          assigned_agent_id: agentId,
          assigned_user_id: userId,
          case_number: generateCaseNumber(),
          status: 'collecting_slots',
          priority: 'normal',
          channel: 'whatsapp',
          customer_phone: phone,
          intent: 'assistance_residential',
          insurer_key: 'allianz',
          line_kind: 'residential',
          macro_service: 'residential_assistance',
          selected_corridor_key: 'allianz_residential_assistance',
          selected_subcorridor_key: subcorridorKey,
          policy_source: 'unknown',
          verification_status: 'unverified',
          risk_level: 'low',
          handoff_required: false,
          summary: 'Atendimento WhatsApp residencial Allianz / Eletricista.',
          next_step: 'Coletar dados mínimos e validar apólice antes de qualquer acionamento externo.',
        })
        .select('id')
        .single();
      if (caseErr || !createdCase) {
        console.error('[WA INBOUND] case insert error:', caseErr?.message);
        return NextResponse.json({ ok: false, error: 'case_create_failed' }, { status: 500 });
      }
      caseId = createdCase.id;
      const requiredKeys: string[] = Array.isArray(template.required_slots)
        ? (template.required_slots as any[]).map((s) => (s && typeof s.key === 'string' ? s.key : null)).filter(Boolean)
        : ['electrical_issue_type', 'risk_indicators', 'affected_area', 'property_address_confirmed', 'policy_evidence_status'];
      await supabaseAdmin.from('corridor_runs').insert({
        company_id: companyId,
        case_id: caseId,
        corridor_template_id: template.id,
        phase: 'collect_slots',
        status: 'active',
        slots: { filled: {}, missing: requiredKeys, conflicts: [] },
        diagnostics: { mvp_mode: 'dry_run_hitl', external_action_allowed: false, hitl_required: true, channel: 'whatsapp' },
        next_step: 'Perguntar uma informação por vez, começando por risco elétrico e área afetada.',
      });
      events.push('case_created');
    }

    if (!caseId) {
      return NextResponse.json({ ok: false, error: 'case_unresolved' }, { status: 500 });
    }

    // 1) Delega ao MESMO runtime do dashboard (reply) via chave interna. Salva user+assistant.
    events.push('runtime_reply_called');
    const replyRes = await callRuntimeInternal(origin, `/api/attendance/cases/${caseId}/runtime/reply`, internalKey, {
      company_id: companyId,
      message: text,
      source: 'whatsapp',
    });
    if (!replyRes.ok) {
      return NextResponse.json({ ok: false, error: 'runtime_reply_failed', case_id: caseId }, { status: 502 });
    }
    let assistantText: string | null = replyRes.json?.next_step?.question ?? null;
    let runtimeStatus: string | null = replyRes.json?.next_step?.status ?? null;
    let macroState: string | null = replyRes.json?.case?.metadata?.attendance_macro_state ?? null;
    let verification: string | null = replyRes.json?.case?.verification_status ?? null;
    let dispatchState: string | null = null;

    // 2) Avanço autônomo: se chegou ao gate de apólice, dispara o lookup InfoCap.
    if (macroState === 'policy_lookup_required') {
      events.push('policy_lookup_auto');
      const lk = await callRuntimeInternal(origin, `/api/attendance/cases/${caseId}/runtime/policy-lookup`, internalKey, {
        company_id: companyId,
        source: 'infocap',
        mode: 'connector',
      });
      const plr = lk.json?.policy_lookup_result;
      const st = plr?.status;
      if (st === 'multiple_matches' && Array.isArray(plr.matches) && plr.matches.length > 0) {
        assistantText = buildPolicyOptionsMessage(plr.matches);
        await supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'assistant', content: assistantText, type: 'text' });
        events.push('policy_lookup_multiple_matches');
      } else if (st === 'found') {
        // Evidência pronta → step para mensagem inteligente + dispatch draft.
        const stp = await callRuntimeInternal(origin, `/api/attendance/cases/${caseId}/runtime/step`, internalKey, { company_id: companyId, source: 'whatsapp' });
        assistantText = stp.json?.step?.question ?? assistantText;
        verification = stp.json?.case?.verification_status ?? verification;
        events.push('policy_lookup_found');
      } else {
        assistantText = lk.json?.next_step ?? assistantText;
        events.push(`policy_lookup_${st || 'unresolved'}`);
      }
    }

    // 3) Hook idempotente de dispatch draft (quando evidência pronta + slots ok).
    const draft = await maybePrepareDispatchDraft({ origin, internalKey, companyId, caseId, verificationStatus: verification });
    if (draft.prepared) {
      dispatchState = draft.packet_state;
      events.push('dispatch_draft_auto_prepared');
      if (draft.message) {
        assistantText = assistantText ? `${assistantText} ${draft.message}` : draft.message;
        await supabaseAdmin.from('messages').insert({ conversation_id: conversationId, role: 'assistant', content: draft.message, type: 'text' });
      }
    }

    events.push(outbound.dry_run ? 'outbound_dry_run' : 'outbound_sent');
    return NextResponse.json({
      ok: true,
      action: routing.action,
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
