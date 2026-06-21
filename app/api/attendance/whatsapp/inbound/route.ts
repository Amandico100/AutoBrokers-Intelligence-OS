import { NextRequest, NextResponse } from 'next/server';
import { getAdminClient } from '@/lib/attendance/support-destinations';
import { resolveAttendanceCaseForWhatsAppInbound } from '@/lib/attendance/whatsapp-case-routing';
import { mediaAckMessage, type WhatsAppMediaKind } from '@/lib/attendance/whatsapp-inbound';
import { evaluateWhatsAppOutboundGate } from '@/lib/attendance/whatsapp-outbound-gate';
import { evaluateConsent } from '@/lib/attendance/whatsapp-consent';
import { getProductionFlags } from '@/lib/security/production-gates';
import { resolveCorridorsWithFallback, type CorridorTemplateLite, type TenantCorridorActivation } from '@/lib/attendance/tenant-corridor-activation';
import {
  normalizeAttendanceMedia,
  processAttendanceMedia,
  buildMediaEvidenceRecord,
  transcribeAttendanceAudio,
  analyzeAttendanceImage,
  extractAttendanceDocument,
  deriveVisualEvidence,
  buildVisionCustomerReply,
  detectDocumentInfocapConflict,
  buildDocumentCustomerReply,
} from '@/lib/attendance/attendance-media';
import {
  resolvePolicySelectionFromCustomerReply,
  buildPolicyOptionsMessage,
  buildPolicySelectedMessage,
  isPolicySelectionAlreadyResolved,
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

/**
 * Carrega corredores OPERÁVEIS pela corretora (Tenant Activation 1).
 * Regra SPEC-012: corredor GLOBAL só opera se houver ativação em tenant_corridors
 * (status active); tenant-scoped continua disponível. DEFENSIVO: se a tabela
 * tenant_corridors ainda não existir (migration não aplicada), mantém o
 * comportamento legado (global ativo) — não quebra o runtime.
 */
async function loadAvailableCorridors(supabaseAdmin: any, companyId: string): Promise<any[]> {
  const { data } = await supabaseAdmin
    .from('corridor_templates')
    .select('id, corridor_key, subcorridor_key, insurer_key, line_kind, macro_service, service_type, display_name, scope, company_id, required_slots')
    .eq('is_active', true)
    .or(`company_id.is.null,company_id.eq.${companyId}`);
  const templates = Array.isArray(data) ? data : [];

  let activations: TenantCorridorActivation[] | null = null;
  try {
    const { data: acts, error } = await supabaseAdmin
      .from('tenant_corridors')
      .select('company_id, corridor_template_id, status')
      .eq('company_id', companyId);
    activations = error ? null : (Array.isArray(acts) ? acts : []);
  } catch {
    activations = null; // tabela ausente → fallback legado
  }

  const lite: CorridorTemplateLite[] = templates.map((t: any) => ({
    id: t.id, corridor_key: t.corridor_key, subcorridor_key: t.subcorridor_key ?? null,
    scope: t.scope ?? (t.company_id ? 'tenant' : 'global'), company_id: t.company_id ?? null, is_active: true,
  }));
  const { corridors } = resolveCorridorsWithFallback(lite, companyId, activations, true);
  const allowed = new Set(corridors.map((c) => c.id));
  return templates.filter((t: any) => allowed.has(t.id));
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
    let text = typeof body.text === 'string' ? body.text.trim() : '';
    const mediaKind = (typeof body.media_kind === 'string' ? body.media_kind : 'text') as WhatsAppMediaKind;
    const mediaUrl = typeof body.media_url === 'string' ? body.media_url : null;
    const mediaBase64 = typeof body.media_base64 === 'string' ? body.media_base64 : null;
    const mimeType = typeof body.mime_type === 'string' ? body.mime_type : null;
    const location = body.location && typeof body.location === 'object' ? body.location : null;
    if (!companyId || !conversationId || !phone) {
      return NextResponse.json({ ok: false, error: 'missing_minimal_identifiers' }, { status: 400 });
    }

    const supabaseAdmin = getAdminClient();
    const events: string[] = ['inbound_received'];

    const { data: existingCase } = await supabaseAdmin
      .from('attendance_cases')
      .select('id, status, verification_status, selected_corridor_key, policy_source, policy_snapshot, coverage_evidence, metadata')
      .eq('company_id', companyId)
      .eq('conversation_id', conversationId)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    // 42X5B — política CANÔNICA de envio (kill switch + production gates + consent).
    // O webhook backend OBEDECE a este `external_send_allowed`/`dry_run`. Resposta a
    // inbound = não-proativa (consentimento de sessão); opt_out bloqueia.
    const flags = getProductionFlags();
    const outboundRealEnabled = process.env.WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED === 'true';
    const consent = evaluateConsent({
      record: (existingCase?.metadata && typeof existingCase.metadata === 'object' ? (existingCase.metadata as any).consent : null) ?? null,
      is_proactive: false,
      last_inbound_at: new Date().toISOString(),
    });
    const outbound = evaluateWhatsAppOutboundGate({
      global_kill_switch: flags.global_kill_switch,
      attendance_dry_run: process.env.ATTENDANCE_WHATSAPP_DRY_RUN !== 'false',
      outbound_real_enabled: outboundRealEnabled,
      external_action_real_enabled: flags.external_action_real_enabled,
      external_send_authorized: outboundRealEnabled && body.external_send_authorized === true,
      consent_ok: consent.consent_ok,
      approval_ok: false,
      is_proactive: false,
      channel: 'customer_whatsapp',
      environment: typeof body.environment === 'string' ? body.environment : null,
    });

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
    // 42M0: anexa evidência de mídia (sanitizada) ao metadata do caso. Sem payload bruto.
    const appendMediaEvidence = async (cid: string, record: Record<string, unknown>) => {
      const { data } = await supabaseAdmin.from('attendance_cases').select('metadata').eq('id', cid).eq('company_id', companyId).maybeSingle();
      const md = data?.metadata && typeof data.metadata === 'object' && !Array.isArray(data.metadata) ? (data.metadata as Record<string, any>) : {};
      const arr = Array.isArray(md.media_evidence) ? md.media_evidence : [];
      arr.push(record);
      await supabaseAdmin.from('attendance_cases').update({ metadata: { ...md, media_evidence: arr.slice(-10) } }).eq('id', cid).eq('company_id', companyId);
    };

    // Handoff humano → registra inbound, NÃO responde automaticamente.
    if (routing.action === 'handoff_block') {
      await insertUser(text || mediaAckMessage(mediaKind), mediaKind);
      events.push('handoff_blocked_auto_reply');
      return NextResponse.json({ ok: true, action: 'handoff_block', case_id: routing.case_id, auto_reply: null, outbound: { ...outbound, sent: false }, diagnostics: diag(events) });
    }

    // 42M0: Media Evidence Pipeline (áudio reusa AudioService; demais viram evidência).
    const hasMediaPayload = Boolean(mediaUrl || mediaBase64 || location) || (mediaKind !== 'text' && !text);
    if (hasMediaPayload) {
      const normalized = normalizeAttendanceMedia({
        media_kind: mediaKind,
        media_url: mediaUrl,
        media_base64: mediaBase64,
        mime_type: mimeType,
        source_channel: 'whatsapp',
        location: location as any,
      });
      if (normalized.media_kind === 'audio') {
        const tr = await transcribeAttendanceAudio({ companyId, agentId, audioUrl: mediaUrl, audioBase64: mediaBase64 });
        if (tr.ok && tr.text) {
          text = tr.text; // áudio vira mensagem normal → segue o runtime
          events.push('audio_transcribed');
        } else {
          const result = processAttendanceMedia(normalized);
          if (existingCase?.id) await appendMediaEvidence(existingCase.id, buildMediaEvidenceRecord(normalized, result));
          await insertUser('[áudio]', 'audio');
          await insertAssistant(result.safe_customer_reply);
          events.push('media_audio_unavailable', 'outbound_dry_run');
          return NextResponse.json({ ok: true, action: 'media_ack', case_id: existingCase?.id ?? null, media_kind: 'audio', auto_reply: result.safe_customer_reply, outbound: { ...outbound, sent: false, text: result.safe_customer_reply }, diagnostics: diag(events) });
        }
      } else if (!text) {
        // imagem/documento/localização/desconhecido sem texto → evidência + ack seguro.
        const result = processAttendanceMedia(normalized, { location: location as any });
        let mediaExtra: Record<string, unknown> = {};
        // 42M1/42M2: visão/documento reais (reuso Smith), gated por flag; senão ack seguro.
        if (normalized.media_kind === 'image') {
          const v = await analyzeAttendanceImage({ companyId, agentId, caseId: existingCase?.id, imageUrl: mediaUrl, imageBase64: mediaBase64, mimeType });
          if (v.ok && v.visual_summary) {
            const ev = deriveVisualEvidence(v.visual_summary);
            result.status = 'processed';
            result.visual_summary = v.visual_summary;
            result.possible_slots = ev.possible_slots;
            result.confidence = (v.confidence as any) || 'medium';
            if (ev.risk_hint) { result.evidence_notes.push('risco_visual'); result.confidence = 'medium'; }
            result.safe_customer_reply = buildVisionCustomerReply(ev);
            events.push('media_image_vision');
          } else {
            events.push(`media_image_${v.status || 'ack'}`);
          }
        } else if (normalized.media_kind === 'document') {
          const d = await extractAttendanceDocument({ companyId, agentId, caseId: existingCase?.id, documentUrl: mediaUrl, documentBase64: mediaBase64, mimeType });
          if (d.ok && d.summary) {
            const conflict = detectDocumentInfocapConflict(d.possible_policy_info, existingCase?.policy_snapshot);
            result.status = 'processed';
            result.document_summary = d.summary;
            result.evidence_notes.push('documento_resumido');
            if (conflict.conflict) result.evidence_notes.push('document_infocap_conflict');
            result.safe_customer_reply = buildDocumentCustomerReply(d, conflict.conflict);
            // Documento NUNCA confirma cobertura; conflito → registra para validação humana.
            mediaExtra = {
              document_type: d.document_type,
              key_facts: d.key_facts,
              possible_policy_info: d.possible_policy_info,
              conflicts: conflict.conflict ? conflict.reasons : [],
            };
            if (existingCase?.id && conflict.conflict) {
              const md = existingCase.metadata && typeof existingCase.metadata === 'object' ? existingCase.metadata : {};
              await supabaseAdmin.from('attendance_cases').update({ metadata: { ...md, document_infocap_conflict: { reasons: conflict.reasons, at: new Date().toISOString() } } }).eq('id', existingCase.id).eq('company_id', companyId);
            }
            events.push(conflict.conflict ? 'media_document_conflict' : 'media_document_extracted');
          } else {
            events.push(`media_document_${d.status || 'ack'}`);
          }
        } else {
          events.push(`media_${normalized.media_kind}`);
        }
        if (existingCase?.id) await appendMediaEvidence(existingCase.id, { ...buildMediaEvidenceRecord(normalized, result), ...mediaExtra });
        await insertUser(`[${normalized.media_kind}]`, 'text');
        await insertAssistant(result.safe_customer_reply);
        events.push('outbound_dry_run');
        return NextResponse.json({ ok: true, action: 'media_ack', case_id: existingCase?.id ?? null, media_kind: normalized.media_kind, auto_reply: result.safe_customer_reply, outbound: { ...outbound, sent: false, text: result.safe_customer_reply }, diagnostics: diag(events) });
      } else if (existingCase?.id) {
        // mídia (não-áudio) + texto → registra evidência e o texto segue o fluxo.
        const result = processAttendanceMedia(normalized, { location: location as any });
        await appendMediaEvidence(existingCase.id, buildMediaEvidenceRecord(normalized, result));
        events.push(`media_${normalized.media_kind}_with_text`);
      }
    }

    const defaultCorridorKey = process.env.ATTENDANCE_DEFAULT_CORRIDOR_KEY || null;
    const defaultSubcorridorKey = process.env.ATTENDANCE_DEFAULT_SUBCORRIDOR_KEY || null;

    // Seleção conversacional de apólice — SÓ se ainda não resolvida (42W1.2 P0).
    const pendingLookup = existingCase?.metadata?.policy_lookup;
    const selectionPending =
      routing.action === 'reply_existing' &&
      pendingLookup?.status === 'multiple_matches' &&
      Array.isArray(pendingLookup.matches) &&
      pendingLookup.matches.length > 0 &&
      Boolean(text) &&
      !isPolicySelectionAlreadyResolved(existingCase);
    if (selectionPending) {
      const matches = pendingLookup.matches;
      await insertUser(text);
      const sel = resolvePolicySelectionFromCustomerReply(text, matches);
      if (sel.resolved && sel.policy_ref) {
        const picked = matches.find((mm: any) => String(mm.policy_ref) === String(sel.policy_ref));
        const selRes = await invokeRuntimeHandler(selectHandler, { caseId: existingCase!.id, internalKey, body: { company_id: companyId, source: 'infocap', policy_ref: sel.policy_ref } });
        const ok = selRes.ok && selRes.json?.ok;
        if (!ok) {
          const failMsg = 'Tive um problema para registrar essa apólice agora. Pode tentar novamente em instantes?';
          await insertAssistant(failMsg);
          events.push('policy_selection_failed', 'outbound_dry_run');
          return NextResponse.json({ ok: true, action: 'policy_selected', case_id: existingCase!.id, selected_policy_ref: null, auto_reply: failMsg, outbound: { ...outbound, sent: false, text: failMsg }, diagnostics: diag(events, { selection_strategy: sel.strategy }) });
        }
        // Marcador explícito de seleção resolvida (42W1.2 P0/req2).
        const md = (selRes.json?.case?.metadata && typeof selRes.json.case.metadata === 'object') ? selRes.json.case.metadata : {};
        await supabaseAdmin.from('attendance_cases').update({
          metadata: { ...md, policy_selection_status: 'resolved', selected_policy_ref: sel.policy_ref, selected_policy_at: new Date().toISOString(), selected_policy_by: 'customer_reply', selected_policy_strategy: sel.strategy },
        }).eq('id', existingCase!.id).eq('company_id', companyId);

        // Confirmação + continuar runtime (step pergunta o próximo slot) — req3.
        const confirm = buildPolicySelectedMessage(picked);
        await insertAssistant(confirm);
        const stp = await invokeRuntimeHandler(stepHandler, { caseId: existingCase!.id, internalKey, body: { company_id: companyId, source: 'whatsapp' } });
        const stepQ = stp.json?.step?.question ?? null;
        const verification = stp.json?.case?.verification_status ?? 'verified_by_connector';
        const draft = await maybePrepareDispatchDraft({
          verificationStatus: verification,
          runDispatch: () => invokeRuntimeHandler(dispatchHandler, { caseId: existingCase!.id, internalKey, body: { company_id: companyId } }),
        });
        const reply = [confirm, stepQ, draft.message].filter(Boolean).join(' ');
        events.push('policy_selection_resolved');
        if (draft.packet_state) events.push('dispatch_draft_auto_prepared');
        events.push('outbound_dry_run');
        return NextResponse.json({ ok: true, action: 'policy_selected', case_id: existingCase!.id, selected_policy_ref: sel.policy_ref, dispatch_packet_state: draft.packet_state, auto_reply: reply, outbound: { ...outbound, sent: false, text: reply }, diagnostics: diag(events, { selection_strategy: sel.strategy }) });
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
