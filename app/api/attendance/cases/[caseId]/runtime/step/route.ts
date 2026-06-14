import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import {
  computeRuntimeStep,
  RUNTIME_ENGINE,
  isCoverageEvidenceReady,
  POLICY_EVIDENCE_SATISFIED,
} from '@/lib/attendance/corridor-runtime';
import { resolveRuntimeConfig } from '@/lib/attendance/runtime-config-resolver';
import { normalizeSlots } from '@/lib/attendance/handoff-dossier';
import { evaluateRuntimeSafetyDecision } from '@/lib/attendance/runtime-safety-policy';
import {
  macroGateOverride,
  isPolicyEvidenceReady,
  RESUME_AFTER_POLICY_PREFIX,
  MACRO_STATES,
} from '@/lib/attendance/attendance-macro-state';

export const dynamic = 'force-dynamic';

// Casos que NÃO podem ser editados pelo runtime (não reabrir/forçar automaticamente).
const NON_RUNTIME_STATUSES = new Set(['closed', 'cancelled', 'handoff']);

/** Remove campos sensíveis do caso antes de devolver ao cliente. */
function safeCase(row: any): any {
  if (!row || typeof row !== 'object') return row;
  const { insured_document_ref: _omit, ...rest } = row;
  return rest;
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/step
 *
 * Executa UM passo determinístico do corredor: escolhe o próximo slot faltante,
 * gera uma pergunta humana, registra a pergunta como mensagem do agente (se houver
 * conversation), atualiza next_step/status do caso e diagnostics do corridor_run.
 *
 * NÃO envia WhatsApp. NÃO cria dispatch_packet. NÃO cria approval_request.
 * NÃO aciona seguradora/portal/InfoCap. NÃO confirma cobertura. external_action_allowed=false.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Empresa não encontrada' }, { status: 404 });

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }
    const source = typeof body.source === 'string' && body.source.trim() ? body.source.trim() : 'dashboard';
    const force = body.force === true;

    // 1. Caso (isolado por company_id)
    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();

    if (caseErr) {
      console.error('[CORRIDOR RUNTIME] case error:', caseErr.message);
      return NextResponse.json({ ok: false, error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });

    // Guarda: não reabrir closed/cancelled nem tirar handoff automaticamente.
    if (NON_RUNTIME_STATUSES.has(caseRow.status)) {
      return NextResponse.json(
        {
          ok: false,
          step: {
            status: 'case_not_runtime_editable',
            selected_slot: null,
            question: null,
            external_action_allowed: false,
          },
        },
        { status: 409 },
      );
    }

    // 2. Último corridor_run do caso
    const { data: run } = await supabaseAdmin
      .from('corridor_runs')
      .select('*')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    // 3. corridor_template (best-effort; resolve slot_priority sem hardcode)
    let template: any = null;
    if (run?.corridor_template_id) {
      const { data: tpl } = await supabaseAdmin
        .from('corridor_templates')
        .select('id, corridor_key, subcorridor_key, required_slots, metadata')
        .eq('id', run.corridor_template_id)
        .maybeSingle();
      template = tpl || null;
    }
    const runtimeConfig = resolveRuntimeConfig({ corridorTemplate: template, corridorRun: run || null, caseRow });

    // 4. Mensagens (para evitar repetir a mesma pergunta)
    let lastAssistantContent: string | null = null;
    if (caseRow.conversation_id) {
      const { data: msgs } = await supabaseAdmin
        .from('messages')
        .select('role, content, created_at')
        .eq('conversation_id', caseRow.conversation_id)
        .order('created_at', { ascending: false })
        .limit(10);
      const lastAssistant = (msgs || []).find((m: any) => m.role === 'assistant');
      lastAssistantContent = lastAssistant && typeof lastAssistant.content === 'string' ? lastAssistant.content : null;
    }

    // Camada de segurança: risco elétrico alto interrompe a coleta normal (42B5E).
    const filledSlots = normalizeSlots(run?.slots).filled;
    const safety = evaluateRuntimeSafetyDecision({ caseRow, filledSlots });
    if (safety.triggered) {
      let safetyMessageId: string | null = null;
      const shouldInsertSafety =
        Boolean(caseRow.conversation_id) && (force || lastAssistantContent !== safety.assistant_message);
      if (shouldInsertSafety) {
        const { data: inserted, error: msgErr } = await supabaseAdmin
          .from('messages')
          .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: safety.assistant_message, type: 'text' })
          .select('id')
          .maybeSingle();
        if (msgErr) console.error('[CORRIDOR RUNTIME] safety message error:', msgErr.message);
        else safetyMessageId = inserted?.id ?? null;
      }

      let updatedRunSafety: any = run || null;
      if (run) {
        const prevDiag =
          run.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
            ? (run.diagnostics as Record<string, any>)
            : {};
        const prevRuntime =
          prevDiag.runtime && typeof prevDiag.runtime === 'object' && !Array.isArray(prevDiag.runtime)
            ? prevDiag.runtime
            : {};
        const newDiagnostics = {
          ...prevDiag,
          mvp_mode: prevDiag.mvp_mode || 'dry_run_hitl',
          hitl_required: true,
          external_action_allowed: false,
          runtime: {
            ...prevRuntime,
            last_step_at: new Date().toISOString(),
            selected_slot: null,
            question_generated: shouldInsertSafety,
            external_action_allowed: false,
            channel: source,
            engine: RUNTIME_ENGINE,
            slot_priority_source: runtimeConfig.slot_priority_source,
            safety_decision: { triggered: true, reason: safety.reason },
            safety_notes: [safety.safety_note, 'Ação externa bloqueada neste MVP (dry-run/HITL).'],
          },
        };
        const { data: runAfter } = await supabaseAdmin
          .from('corridor_runs')
          .update({ diagnostics: newDiagnostics, next_step: safety.next_step, last_agent_action: safety.last_agent_action, phase: 'handoff' })
          .eq('id', run.id)
          .eq('company_id', companyId)
          .select('*')
          .maybeSingle();
        if (runAfter) updatedRunSafety = runAfter;
      }

      const { data: caseAfterSafety } = await supabaseAdmin
        .from('attendance_cases')
        .update({
          status: 'handoff',
          priority: safety.priority,
          risk_level: safety.risk_level,
          handoff_required: safety.handoff_required,
          handoff_reason: safety.handoff_reason,
          next_step: safety.next_step,
        })
        .eq('id', caseRow.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();

      console.log(
        `[CORRIDOR RUNTIME] case=${caseId} safety_handoff=true reason=${safety.reason} message_id=${safetyMessageId}`,
      );

      return NextResponse.json({
        ok: true,
        case: safeCase(caseAfterSafety || caseRow),
        corridor_run: updatedRunSafety,
        step: {
          selected_slot: null,
          question: safety.assistant_message,
          status: 'safety_handoff',
          external_action_allowed: false,
          message_id: safetyMessageId,
          next_step: safety.next_step,
          safety_notes: [safety.safety_note],
        },
      });
    }

    // Retomada do corredor após policy lookup (42B5H): evidência de apólice pronta
    // → resolver o gate de apólice e voltar a coletar slots do corredor.
    if (isPolicyEvidenceReady(caseRow)) {
      const resumeStep = computeRuntimeStep({ caseRow, run: run || null, slotPriority: runtimeConfig.slot_priority });
      const resumeQuestion = resumeStep.question ? `${RESUME_AFTER_POLICY_PREFIX}${resumeStep.question}` : null;
      const resumeNextStep = resumeStep.question ? resumeQuestion! : resumeStep.nextStep;

      let resumeMessageId: string | null = null;
      const shouldInsertResume =
        Boolean(caseRow.conversation_id) && Boolean(resumeQuestion) && (force || lastAssistantContent !== resumeQuestion);
      if (shouldInsertResume && resumeQuestion) {
        const { data: inserted, error: msgErr } = await supabaseAdmin
          .from('messages')
          .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: resumeQuestion, type: 'text' })
          .select('id')
          .maybeSingle();
        if (msgErr) console.error('[CORRIDOR RUNTIME] resume message error:', msgErr.message);
        else resumeMessageId = inserted?.id ?? null;
      }

      // 42B5K.1: persistir policy_evidence_status satisfeito (evidência pronta).
      const resumeSlots = normalizeSlots(run?.slots);
      const resumeFilled = { ...resumeSlots.filled };
      let resumeMissing = [...resumeSlots.missing];
      if (isCoverageEvidenceReady(caseRow) && !resumeFilled.policy_evidence_status) {
        resumeFilled.policy_evidence_status = { ...POLICY_EVIDENCE_SATISFIED };
        resumeMissing = resumeMissing.filter((k) => k !== 'policy_evidence_status');
      }

      let updatedRunResume: any = run || null;
      if (run) {
        const prevDiag =
          run.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
            ? (run.diagnostics as Record<string, any>)
            : {};
        const prevRuntime =
          prevDiag.runtime && typeof prevDiag.runtime === 'object' && !Array.isArray(prevDiag.runtime)
            ? prevDiag.runtime
            : {};
        const newDiagnostics = {
          ...prevDiag,
          mvp_mode: prevDiag.mvp_mode || 'dry_run_hitl',
          hitl_required: true,
          external_action_allowed: false,
          runtime: {
            ...prevRuntime,
            last_step_at: new Date().toISOString(),
            macro_state: MACRO_STATES.CORRIDOR_COLLECTING_SLOTS,
            resumed_after_policy_lookup: true,
            coverage_evidence_ready: true,
            selected_slot: resumeStep.selectedSlot,
            question_generated: Boolean(resumeQuestion),
            external_action_allowed: false,
            channel: source,
            engine: RUNTIME_ENGINE,
            slot_priority_source: runtimeConfig.slot_priority_source,
          },
        };
        const { data: runAfter } = await supabaseAdmin
          .from('corridor_runs')
          .update({
            slots: { filled: resumeFilled, missing: resumeMissing, conflicts: resumeSlots.conflicts },
            diagnostics: newDiagnostics,
            phase: 'collect_slots',
            next_step: resumeNextStep,
            last_agent_action: resumeStep.question ? `ask:${resumeStep.selectedSlot}` : 'resume_after_policy_lookup',
          })
          .eq('id', run.id)
          .eq('company_id', companyId)
          .select('*')
          .maybeSingle();
        if (runAfter) updatedRunResume = runAfter;
      }

      const prevMeta =
        caseRow.metadata && typeof caseRow.metadata === 'object' && !Array.isArray(caseRow.metadata)
          ? (caseRow.metadata as Record<string, unknown>)
          : {};
      const { data: caseAfterResume } = await supabaseAdmin
        .from('attendance_cases')
        .update({
          status: 'collecting_slots',
          next_step: resumeNextStep,
          metadata: { ...prevMeta, attendance_macro_state: MACRO_STATES.CORRIDOR_COLLECTING_SLOTS },
        })
        .eq('id', caseRow.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();

      console.log(
        `[CORRIDOR RUNTIME] case=${caseId} resumed_after_policy_lookup=true selected_slot=${resumeStep.selectedSlot} message_id=${resumeMessageId}`,
      );

      return NextResponse.json({
        ok: true,
        case: safeCase(caseAfterResume || caseRow),
        corridor_run: updatedRunResume,
        step: {
          selected_slot: resumeStep.selectedSlot,
          question: resumeQuestion,
          status: resumeStep.question ? 'resumed_collecting_slots' : 'no_missing_slots',
          macro_state: MACRO_STATES.CORRIDOR_COLLECTING_SLOTS,
          external_action_allowed: false,
          message_id: resumeMessageId,
          next_step: resumeNextStep,
          resumed_after_policy_lookup: true,
        },
      });
    }

    // Macro gate (42B5G): identidade/apólice antes de continuar o corredor.
    const gate = macroGateOverride({ caseRow, filledSlots });
    if (gate) {
      let gateMessageId: string | null = null;
      if (caseRow.conversation_id && (force || lastAssistantContent !== gate.question)) {
        const { data: ins } = await supabaseAdmin
          .from('messages')
          .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: gate.question, type: 'text' })
          .select('id')
          .maybeSingle();
        gateMessageId = ins?.id ?? null;
      }
      let updatedRunGate: any = run || null;
      if (run) {
        const prevDiag =
          run.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
            ? (run.diagnostics as Record<string, any>)
            : {};
        const prevRuntime =
          prevDiag.runtime && typeof prevDiag.runtime === 'object' && !Array.isArray(prevDiag.runtime)
            ? prevDiag.runtime
            : {};
        const { data: runAfter } = await supabaseAdmin
          .from('corridor_runs')
          .update({
            next_step: gate.next_step,
            last_agent_action: gate.last_agent_action,
            diagnostics: {
              ...prevDiag,
              external_action_allowed: false,
              hitl_required: true,
              runtime: {
                ...prevRuntime,
                last_step_at: new Date().toISOString(),
                selected_slot: gate.selected_slot,
                macro_state: gate.macro_state,
                external_action_allowed: false,
                channel: source,
                engine: RUNTIME_ENGINE,
                slot_priority_source: runtimeConfig.slot_priority_source,
              },
            },
          })
          .eq('id', run.id)
          .eq('company_id', companyId)
          .select('*')
          .maybeSingle();
        if (runAfter) updatedRunGate = runAfter;
      }
      const { data: caseAfterGate } = await supabaseAdmin
        .from('attendance_cases')
        .update({
          next_step: gate.next_step,
          ...(gate.case_status ? { status: gate.case_status } : {}),
        })
        .eq('id', caseRow.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();

      console.log(`[CORRIDOR RUNTIME] case=${caseId} macro_gate=${gate.macro_state} message_id=${gateMessageId}`);
      return NextResponse.json({
        ok: true,
        case: safeCase(caseAfterGate || caseRow),
        corridor_run: updatedRunGate,
        step: {
          selected_slot: gate.selected_slot,
          question: gate.question,
          status: gate.status,
          macro_state: gate.macro_state,
          external_action_allowed: false,
          message_id: gateMessageId,
          next_step: gate.next_step,
        },
      });
    }

    // 5-7. Calcular passo (puro), usando a prioridade de slots resolvida
    const step = computeRuntimeStep({ caseRow, run: run || null, slotPriority: runtimeConfig.slot_priority });

    // 8. Gravar pergunta como message role='assistant' (sem duplicar pergunta recente)
    let messageId: string | null = null;
    const shouldInsertMessage =
      Boolean(caseRow.conversation_id) &&
      Boolean(step.question) &&
      (force || lastAssistantContent !== step.question);
    if (shouldInsertMessage && step.question) {
      const { data: inserted, error: msgErr } = await supabaseAdmin
        .from('messages')
        .insert({
          conversation_id: caseRow.conversation_id,
          role: 'assistant',
          content: step.question,
          type: 'text',
        })
        .select('id')
        .maybeSingle();
      if (msgErr) {
        console.error('[CORRIDOR RUNTIME] message insert error:', msgErr.message);
      } else {
        messageId = inserted?.id ?? null;
      }
    }

    // 11. Atualizar diagnostics do corridor_run (merge, preservando dados anteriores)
    let updatedRun: any = run || null;
    if (run) {
      const prevDiag =
        run.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
          ? (run.diagnostics as Record<string, any>)
          : {};
      const prevRuntime =
        prevDiag.runtime && typeof prevDiag.runtime === 'object' && !Array.isArray(prevDiag.runtime)
          ? prevDiag.runtime
          : {};
      const newDiagnostics = {
        ...prevDiag,
        mvp_mode: prevDiag.mvp_mode || 'dry_run_hitl',
        hitl_required: true,
        external_action_allowed: false,
        runtime: {
          ...prevRuntime,
          last_step_at: new Date().toISOString(),
          selected_slot: step.selectedSlot,
          question_generated: Boolean(step.question),
          external_action_allowed: false,
          channel: source,
          engine: RUNTIME_ENGINE,
          slot_priority_source: runtimeConfig.slot_priority_source,
          coverage_evidence_ready: isCoverageEvidenceReady(caseRow),
          safety_notes: step.safetyNotes,
        },
      };

      const runUpdate: Record<string, unknown> = {
        diagnostics: newDiagnostics,
        next_step: step.nextStep,
        last_agent_action: step.question ? `ask:${step.selectedSlot}` : 'slots_complete',
      };
      if (step.runPhaseUpdate) runUpdate.phase = step.runPhaseUpdate;

      const { data: runAfter, error: runErr } = await supabaseAdmin
        .from('corridor_runs')
        .update(runUpdate)
        .eq('id', run.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();
      if (runErr) {
        console.error('[CORRIDOR RUNTIME] run update error:', runErr.message);
      } else if (runAfter) {
        updatedRun = runAfter;
      }
    }

    // 9-10. Atualizar caso: next_step (e status quando permitido)
    const caseUpdate: Record<string, unknown> = { next_step: step.nextStep };
    if (step.caseStatusUpdate) caseUpdate.status = step.caseStatusUpdate;

    const { data: caseAfter, error: caseUpdErr } = await supabaseAdmin
      .from('attendance_cases')
      .update(caseUpdate)
      .eq('id', caseRow.id)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();
    if (caseUpdErr) {
      console.error('[CORRIDOR RUNTIME] case update error:', caseUpdErr.message);
    }

    // Log seguro: sem telefone/PII/conteúdo.
    console.log(
      `[CORRIDOR RUNTIME] case=${caseId} selected_slot=${step.selectedSlot} status=${step.stepStatus} message_id=${messageId}`,
    );

    // 12. Resposta
    return NextResponse.json({
      ok: true,
      case: safeCase(caseAfter || caseRow),
      corridor_run: updatedRun,
      step: {
        selected_slot: step.selectedSlot,
        question: step.question,
        status: step.stepStatus,
        external_action_allowed: false,
        message_id: messageId,
        next_step: step.nextStep,
        safety_notes: step.safetyNotes,
      },
    });
  } catch (error: any) {
    console.error('[CORRIDOR RUNTIME] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
