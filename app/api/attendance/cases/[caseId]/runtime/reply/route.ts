import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { normalizeSlots } from '@/lib/attendance/handoff-dossier';
import {
  computeRuntimeStep,
  extractSlotValue,
  clarificationForSlot,
  selectNextSlot,
  RUNTIME_ENGINE,
} from '@/lib/attendance/corridor-runtime';
import { resolveRuntimeConfig } from '@/lib/attendance/runtime-config-resolver';
import { evaluateRuntimeSafetyDecision } from '@/lib/attendance/runtime-safety-policy';
import { evaluateFirstResponseIntake } from '@/lib/attendance/runtime-intake-policy';
import { macroGateOverride, MACRO_STATES } from '@/lib/attendance/attendance-macro-state';
import {
  extractDocument,
  maskDocument,
  IDENTITY_CLARIFY,
  IDENTITY_NEXT_STEP,
  POLICY_LOOKUP_MESSAGE,
  POLICY_NEXT_STEP,
} from '@/lib/attendance/runtime-identity-policy';

/** Merge raso e seguro de attendance_cases.metadata (jsonb). */
function mergeCaseMetadata(caseRow: any, patch: Record<string, unknown>): Record<string, unknown> {
  const prev =
    caseRow?.metadata && typeof caseRow.metadata === 'object' && !Array.isArray(caseRow.metadata)
      ? (caseRow.metadata as Record<string, unknown>)
      : {};
  return { ...prev, ...patch };
}

export const dynamic = 'force-dynamic';

const NON_RUNTIME_STATUSES = new Set(['closed', 'cancelled', 'handoff']);
const MAX_MESSAGE_LENGTH = 2000;

/** Slot alvo: diagnostics.runtime.selected_slot → last_agent_action ask:<slot> → próximo faltante. */
function resolveTargetSlot(
  run: any,
  filled: Record<string, unknown>,
  slotPriority: readonly string[],
): string | null {
  const diagSlot = run?.diagnostics?.runtime?.selected_slot;
  if (typeof diagSlot === 'string' && diagSlot) return diagSlot;
  const action = typeof run?.last_agent_action === 'string' ? run.last_agent_action : '';
  if (action.startsWith('ask:')) {
    const slot = action.slice('ask:'.length).trim();
    if (slot) return slot;
  }
  return selectNextSlot(filled, slotPriority);
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/reply
 *
 * Recebe a resposta do cliente, registra como messages.role='user', preenche o
 * slot que estava sendo perguntado (extração segura) e, se possível, gera a
 * próxima pergunta via o mesmo helper do 42B5B.
 *
 * NÃO envia WhatsApp. NÃO cria dispatch_packet. NÃO cria approval_request.
 * NÃO valida apólice / consulta InfoCap. NÃO confirma cobertura.
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
    const rawMessage = typeof body.message === 'string' ? body.message.trim() : '';
    if (!rawMessage) return NextResponse.json({ ok: false, error: 'Mensagem obrigatória' }, { status: 400 });
    if (rawMessage.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json({ ok: false, error: 'Mensagem muito longa' }, { status: 400 });
    }
    const source = typeof body.source === 'string' && body.source.trim() ? body.source.trim() : 'dashboard';
    const force = body.force === true;

    // 1. Caso
    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (caseErr) {
      console.error('[CORRIDOR REPLY] case error:', caseErr.message);
      return NextResponse.json({ ok: false, error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });

    if (NON_RUNTIME_STATUSES.has(caseRow.status)) {
      return NextResponse.json({ ok: false, error: 'case_not_runtime_editable' }, { status: 409 });
    }

    // 2. Último corridor_run
    const { data: run } = await supabaseAdmin
      .from('corridor_runs')
      .select('*')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    // Última pergunta do agente (para dedupe) ANTES de inserir a nova user message.
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

    // 2b. Inserir user message
    let userMessageId: string | null = null;
    if (caseRow.conversation_id) {
      const { data: inserted, error: msgErr } = await supabaseAdmin
        .from('messages')
        .insert({ conversation_id: caseRow.conversation_id, role: 'user', content: rawMessage, type: 'text' })
        .select('id')
        .maybeSingle();
      if (msgErr) console.error('[CORRIDOR REPLY] user message error:', msgErr.message);
      else userMessageId = inserted?.id ?? null;
    }

    // corridor_template (best-effort) → Runtime Config Resolver (slot_priority sem hardcode)
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

    const slots = normalizeSlots(run?.slots);

    // Pergunta ativa do agente (slot ou gate).
    const diagSelected = run?.diagnostics?.runtime?.selected_slot;
    const lastAction = typeof run?.last_agent_action === 'string' ? run.last_agent_action : '';
    const hasActiveQuestion =
      (typeof diagSelected === 'string' && diagSelected.length > 0) || lastAction.startsWith('ask:');
    const activeAsk = lastAction.startsWith('ask:')
      ? lastAction.slice('ask:'.length)
      : typeof diagSelected === 'string'
        ? diagSelected
        : '';

    // ---- Gate de IDENTIDADE (42B5G): resposta a uma pergunta de CPF/CNPJ ----
    if (activeAsk === 'identity_document') {
      const doc = extractDocument(rawMessage);
      const baseRuntimeDiag = (() => {
        const prevDiag =
          run?.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
            ? (run.diagnostics as Record<string, any>)
            : {};
        const prevRuntime =
          prevDiag.runtime && typeof prevDiag.runtime === 'object' && !Array.isArray(prevDiag.runtime)
            ? prevDiag.runtime
            : {};
        return { prevDiag, prevRuntime };
      })();

      if (!doc.valid || !doc.ref) {
        // Documento não reconhecido → reesclarecer (sem virar loop ruidoso).
        let assistantMessageId: string | null = null;
        if (caseRow.conversation_id && (force || lastAssistantContent !== IDENTITY_CLARIFY)) {
          const { data: ins } = await supabaseAdmin
            .from('messages')
            .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: IDENTITY_CLARIFY, type: 'text' })
            .select('id')
            .maybeSingle();
          assistantMessageId = ins?.id ?? null;
        }
        if (run) {
          await supabaseAdmin
            .from('corridor_runs')
            .update({
              next_step: IDENTITY_NEXT_STEP,
              last_agent_action: 'ask:identity_document',
              diagnostics: {
                ...baseRuntimeDiag.prevDiag,
                runtime: {
                  ...baseRuntimeDiag.prevRuntime,
                  last_step_at: new Date().toISOString(),
                  selected_slot: 'identity_document',
                  macro_state: MACRO_STATES.IDENTITY_REQUIRED,
                  external_action_allowed: false,
                  channel: source,
                  engine: RUNTIME_ENGINE,
                },
              },
            })
            .eq('id', run.id)
            .eq('company_id', companyId);
        }
        await supabaseAdmin
          .from('attendance_cases')
          .update({ next_step: IDENTITY_NEXT_STEP, metadata: mergeCaseMetadata(caseRow, { attendance_macro_state: MACRO_STATES.IDENTITY_REQUIRED }) })
          .eq('id', caseRow.id)
          .eq('company_id', companyId);

        console.log(`[CORRIDOR REPLY] case=${caseId} identity=invalid user_msg=${userMessageId}`);
        return NextResponse.json({
          ok: true,
          case: caseRow,
          corridor_run: run || null,
          intake: { target_slot: 'identity_document', kind: 'identity_clarify', filled: false, status: 'identity_required', extracted_value: null, confidence: 'low', conflicts: [] },
          next_step: { selected_slot: 'identity_document', question: IDENTITY_CLARIFY, status: 'identity_required', message_id: assistantMessageId },
          messages: { user_message_id: userMessageId, assistant_message_id: assistantMessageId },
          external_action_allowed: false,
        });
      }

      // Documento válido → grava insured_document_ref + tipo; avança para policy_lookup_required.
      let assistantMessageId: string | null = null;
      if (caseRow.conversation_id && (force || lastAssistantContent !== POLICY_LOOKUP_MESSAGE)) {
        const { data: ins } = await supabaseAdmin
          .from('messages')
          .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: POLICY_LOOKUP_MESSAGE, type: 'text' })
          .select('id')
          .maybeSingle();
        assistantMessageId = ins?.id ?? null;
      }

      let updatedRunId: any = run || null;
      if (run) {
        const { data: runAfter } = await supabaseAdmin
          .from('corridor_runs')
          .update({
            next_step: POLICY_NEXT_STEP,
            last_agent_action: 'policy_lookup:pending',
            diagnostics: {
              ...baseRuntimeDiag.prevDiag,
              external_action_allowed: false,
              hitl_required: true,
              runtime: {
                ...baseRuntimeDiag.prevRuntime,
                last_step_at: new Date().toISOString(),
                selected_slot: null,
                macro_state: MACRO_STATES.POLICY_LOOKUP_REQUIRED,
                identity_captured: true,
                external_action_allowed: false,
                channel: source,
                engine: RUNTIME_ENGINE,
                safety_notes: ['Apólice ainda NÃO verificada. Dispatch real bloqueado até verificação por fonte confiável.'],
              },
            },
          })
          .eq('id', run.id)
          .eq('company_id', companyId)
          .select('*')
          .maybeSingle();
        if (runAfter) updatedRunId = runAfter;
      }

      const { data: caseAfter } = await supabaseAdmin
        .from('attendance_cases')
        .update({
          insured_document_ref: doc.ref,
          status: 'policy_check',
          next_step: POLICY_NEXT_STEP,
          metadata: mergeCaseMetadata(caseRow, {
            attendance_macro_state: MACRO_STATES.POLICY_LOOKUP_REQUIRED,
            identity: { document_type: doc.type, captured_at: new Date().toISOString() },
          }),
        })
        .eq('id', caseRow.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();

      console.log(`[CORRIDOR REPLY] case=${caseId} identity=${maskDocument(doc.ref)} macro=policy_lookup_required user_msg=${userMessageId}`);
      return NextResponse.json({
        ok: true,
        case: caseAfter || caseRow,
        corridor_run: updatedRunId,
        intake: { target_slot: 'identity_document', kind: 'identity_captured', filled: true, status: 'policy_lookup_required', extracted_value: { document_type: doc.type }, confidence: 'high', conflicts: [] },
        next_step: { selected_slot: null, question: POLICY_LOOKUP_MESSAGE, status: 'policy_lookup_required', message_id: assistantMessageId },
        messages: { user_message_id: userMessageId, assistant_message_id: assistantMessageId },
        external_action_allowed: false,
      });
    }

    if (!hasActiveQuestion) {
      const intake = evaluateFirstResponseIntake({ message: rawMessage, filledSlots: slots.filled });
      if (intake.applies) {
        const newFilled = { ...slots.filled };
        const newMissing = [...slots.missing];
        const caseUpdate: Record<string, unknown> = {};
        const safetyNotes: string[] = [];
        let assistantMessage = intake.assistant_message;
        let lastAgentAction = intake.last_agent_action;
        let selectedForDiag: string | null = intake.prime_slot;
        let runPhase: string | null = null;
        let safetyTriggered = false;

        if (intake.kind === 'high_risk_described') {
          const riskExtraction = extractSlotValue('risk_indicators', rawMessage);
          const safety = evaluateRuntimeSafetyDecision({
            caseRow,
            targetSlot: 'risk_indicators',
            extraction: riskExtraction,
            filledSlots: slots.filled,
          });
          if (safety.triggered) {
            safetyTriggered = true;
            newFilled.risk_indicators = riskExtraction.value;
            const idx = newMissing.indexOf('risk_indicators');
            if (idx >= 0) newMissing.splice(idx, 1);
            caseUpdate.status = 'handoff';
            caseUpdate.priority = safety.priority;
            caseUpdate.risk_level = safety.risk_level;
            caseUpdate.handoff_required = safety.handoff_required;
            caseUpdate.handoff_reason = safety.handoff_reason;
            assistantMessage = safety.assistant_message;
            lastAgentAction = 'safety_handoff:first_response';
            selectedForDiag = null;
            runPhase = 'handoff';
            safetyNotes.push(safety.safety_note, 'Ação externa bloqueada neste MVP (dry-run/HITL).');
          }
        } else if (intake.kind === 'problem_already_described') {
          if (caseRow.status === 'new' || caseRow.status === 'triage') caseUpdate.status = 'collecting_slots';
        }

        if (intake.should_update_problem_description && intake.problem_description) {
          newFilled.problem_description = intake.problem_description;
        }
        caseUpdate.next_step = intake.next_step;
        if (!safetyTriggered) {
          safetyNotes.push(
            'Ação externa bloqueada neste MVP (dry-run/HITL).',
            'Não confirmar cobertura sem evidência de apólice.',
          );
        }

        // Inserir UMA mensagem assistant (com dedupe)
        let assistantMessageId: string | null = null;
        const shouldInsertAssistant =
          Boolean(caseRow.conversation_id) && Boolean(assistantMessage) && (force || lastAssistantContent !== assistantMessage);
        if (shouldInsertAssistant && assistantMessage) {
          const { data: inserted, error: aErr } = await supabaseAdmin
            .from('messages')
            .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: assistantMessage, type: 'text' })
            .select('id')
            .maybeSingle();
          if (aErr) console.error('[CORRIDOR REPLY] intake assistant message error:', aErr.message);
          else assistantMessageId = inserted?.id ?? null;
        }

        // Persistir no corridor_run (slots + diagnostics + next_step + last_agent_action)
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
              selected_slot: selectedForDiag,
              question_generated: Boolean(assistantMessage),
              external_action_allowed: false,
              channel: source,
              engine: RUNTIME_ENGINE,
              slot_priority_source: runtimeConfig.slot_priority_source,
              intake_policy: { applied: true, kind: intake.kind },
              safety_decision: safetyTriggered ? { triggered: true, reason: 'high_risk_electrical' } : { triggered: false },
              safety_notes: safetyNotes,
            },
          };
          const runUpdate: Record<string, unknown> = {
            slots: { filled: newFilled, missing: newMissing, conflicts: slots.conflicts },
            diagnostics: newDiagnostics,
            next_step: intake.next_step,
            last_agent_action: lastAgentAction,
          };
          if (runPhase) runUpdate.phase = runPhase;
          const { data: runAfter } = await supabaseAdmin
            .from('corridor_runs')
            .update(runUpdate)
            .eq('id', run.id)
            .eq('company_id', companyId)
            .select('*')
            .maybeSingle();
          if (runAfter) updatedRun = runAfter;
        }

        const { data: caseAfter } = await supabaseAdmin
          .from('attendance_cases')
          .update(caseUpdate)
          .eq('id', caseRow.id)
          .eq('company_id', companyId)
          .select('*')
          .maybeSingle();

        console.log(
          `[CORRIDOR REPLY] case=${caseId} intake_kind=${intake.kind} safety=${safetyTriggered} user_msg=${userMessageId} assistant_msg=${assistantMessageId}`,
        );

        return NextResponse.json({
          ok: true,
          case: caseAfter || { ...caseRow, ...caseUpdate },
          corridor_run: updatedRun,
          intake: {
            target_slot: null,
            kind: intake.kind,
            filled: false,
            status: intake.kind,
            extracted_value: null,
            confidence: 'low',
            conflicts: [],
          },
          next_step: {
            selected_slot: selectedForDiag,
            question: assistantMessage,
            status: intake.kind,
            message_id: assistantMessageId,
          },
          messages: { user_message_id: userMessageId, assistant_message_id: assistantMessageId },
          external_action_allowed: false,
        });
      }
    }

    const targetSlot = resolveTargetSlot(run, slots.filled, runtimeConfig.slot_priority);

    // Sem slot alvo: nada pendente. Computa estado e retorna.
    if (!targetSlot) {
      const step = computeRuntimeStep({ caseRow, run: run || null, slotPriority: runtimeConfig.slot_priority });
      await supabaseAdmin
        .from('attendance_cases')
        .update({ next_step: step.nextStep, ...(step.caseStatusUpdate ? { status: step.caseStatusUpdate } : {}) })
        .eq('id', caseRow.id)
        .eq('company_id', companyId);
      return NextResponse.json({
        ok: true,
        case: caseRow,
        corridor_run: run || null,
        intake: { target_slot: null, filled: false, status: 'no_slot_pending', extracted_value: null, confidence: 'low', conflicts: [] },
        next_step: { selected_slot: step.selectedSlot, question: step.question, status: step.stepStatus, message_id: null },
        messages: { user_message_id: userMessageId, assistant_message_id: null },
        external_action_allowed: false,
      });
    }

    // 4. Extração segura
    const extraction = extractSlotValue(targetSlot, rawMessage);

    // 5-7. Atualizar slots (preservando os demais)
    const newFilled = { ...slots.filled };
    let newMissing = [...slots.missing];
    let newConflicts = slots.conflicts.filter(
      (c: any) => !(c && typeof c === 'object' && c.slot === targetSlot),
    );

    if (extraction.ambiguous) {
      if (!newMissing.includes(targetSlot)) newMissing.push(targetSlot);
      newConflicts.push({ slot: targetSlot, reason: 'ambiguous_reply', raw: rawMessage.slice(0, 200) });
    } else {
      newFilled[targetSlot] = extraction.value;
      newMissing = newMissing.filter((k) => k !== targetSlot);
      if (extraction.conflictReason) {
        newConflicts.push({ slot: targetSlot, reason: extraction.conflictReason, raw: rawMessage.slice(0, 200) });
      }
    }
    const newSlots = { filled: newFilled, missing: newMissing, conflicts: newConflicts };

    const safetyNotes: string[] = [];
    const caseUpdate: Record<string, unknown> = {};

    let nextSlot: string | null;
    let nextQuestion: string | null;
    let nextStatus: string;
    let nextStepText: string;
    let nextPhase: string | null;
    let lastAgentAction: string;
    let safetyTriggered = false;
    let macroState: string = MACRO_STATES.CORRIDOR_COLLECTING_SLOTS;

    // Camada de segurança: risco elétrico alto interrompe a coleta normal (42B5E).
    const safety = evaluateRuntimeSafetyDecision({ caseRow, targetSlot, extraction, filledSlots: newFilled });

    if (safety.triggered) {
      safetyTriggered = true;
      macroState = MACRO_STATES.HANDOFF;
      caseUpdate.risk_level = safety.risk_level;
      caseUpdate.priority = safety.priority;
      caseUpdate.handoff_required = safety.handoff_required;
      caseUpdate.handoff_reason = safety.handoff_reason;
      caseUpdate.status = 'handoff';
      safetyNotes.push(safety.safety_note, 'Ação externa bloqueada neste MVP (dry-run/HITL).');
      nextSlot = null;
      nextQuestion = safety.assistant_message;
      nextStatus = 'safety_handoff';
      nextStepText = safety.next_step;
      nextPhase = 'handoff';
      lastAgentAction = safety.last_agent_action;
    } else {
      // 10. Próxima pergunta (fluxo normal / clarificação)
      const caseForCompute = { ...caseRow };
      const runForCompute = { ...(run || {}), slots: newSlots };
      const step = computeRuntimeStep({
        caseRow: caseForCompute,
        run: runForCompute,
        slotPriority: runtimeConfig.slot_priority,
      });
      safetyNotes.push(...step.safetyNotes);

      if (extraction.ambiguous) {
        // Re-perguntar o mesmo slot com clarificação.
        nextSlot = targetSlot;
        nextQuestion = clarificationForSlot(targetSlot);
        nextStatus = 'needs_clarification';
        nextStepText = nextQuestion;
        nextPhase = null;
        lastAgentAction = `clarify:${targetSlot}`;
      } else {
        nextSlot = step.selectedSlot;
        nextQuestion = step.question;
        nextStatus = step.stepStatus;
        nextStepText = step.nextStep;
        nextPhase = step.runPhaseUpdate;
        if (step.caseStatusUpdate) caseUpdate.status = step.caseStatusUpdate;
        lastAgentAction = nextQuestion ? `ask:${nextSlot}` : 'slots_complete';

        // Macro gate (42B5G): identidade/apólice antes de continuar o corredor.
        // Tem precedência sobre a coleta normal de slots (mas não sobre safety).
        const gate = macroGateOverride({ caseRow: { ...caseRow, ...caseUpdate }, filledSlots: newFilled });
        if (gate) {
          nextSlot = gate.selected_slot;
          nextQuestion = gate.question;
          nextStatus = gate.status;
          nextStepText = gate.next_step;
          nextPhase = null;
          lastAgentAction = gate.last_agent_action;
          macroState = gate.macro_state;
          if (gate.case_status) caseUpdate.status = gate.case_status;
        }
      }
    }

    // 11. Inserir assistant message (com dedupe)
    let assistantMessageId: string | null = null;
    const shouldInsertAssistant =
      Boolean(caseRow.conversation_id) && Boolean(nextQuestion) && (force || lastAssistantContent !== nextQuestion);
    if (shouldInsertAssistant && nextQuestion) {
      const { data: inserted, error: aErr } = await supabaseAdmin
        .from('messages')
        .insert({ conversation_id: caseRow.conversation_id, role: 'assistant', content: nextQuestion, type: 'text' })
        .select('id')
        .maybeSingle();
      if (aErr) console.error('[CORRIDOR REPLY] assistant message error:', aErr.message);
      else assistantMessageId = inserted?.id ?? null;
    }

    // 5/8. Persistir slots + diagnostics no run
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
          last_filled_slot: extraction.ambiguous ? null : targetSlot,
          selected_slot: nextSlot,
          question_generated: Boolean(nextQuestion),
          external_action_allowed: false,
          channel: source,
          engine: RUNTIME_ENGINE,
          slot_priority_source: runtimeConfig.slot_priority_source,
          macro_state: macroState,
          safety_decision: safetyTriggered
            ? { triggered: true, reason: 'high_risk_electrical' }
            : { triggered: false },
          safety_notes: safetyNotes,
        },
      };
      const runUpdate: Record<string, unknown> = {
        slots: newSlots,
        diagnostics: newDiagnostics,
        next_step: nextStepText,
        last_agent_action: lastAgentAction,
      };
      if (nextPhase) runUpdate.phase = nextPhase;
      const { data: runAfter, error: runErr } = await supabaseAdmin
        .from('corridor_runs')
        .update(runUpdate)
        .eq('id', run.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();
      if (runErr) console.error('[CORRIDOR REPLY] run update error:', runErr.message);
      else if (runAfter) updatedRun = runAfter;
    }

    // 9. Atualizar caso
    caseUpdate.next_step = nextStepText;
    caseUpdate.metadata = mergeCaseMetadata(caseRow, { attendance_macro_state: macroState });
    const { data: caseAfter, error: caseUpdErr } = await supabaseAdmin
      .from('attendance_cases')
      .update(caseUpdate)
      .eq('id', caseRow.id)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();
    if (caseUpdErr) console.error('[CORRIDOR REPLY] case update error:', caseUpdErr.message);

    // Log seguro: sem telefone/mensagem/slots completos.
    console.log(
      `[CORRIDOR REPLY] case=${caseId} target_slot=${targetSlot} filled=${!extraction.ambiguous} next_slot=${nextSlot} user_msg=${userMessageId} assistant_msg=${assistantMessageId}`,
    );

    return NextResponse.json({
      ok: true,
      case: caseAfter || { ...caseRow, ...caseUpdate },
      corridor_run: updatedRun,
      intake: {
        target_slot: targetSlot,
        filled: !extraction.ambiguous,
        extracted_value: extraction.ambiguous ? null : extraction.value,
        confidence: extraction.ambiguous ? 'low' : extraction.confidence,
        conflicts: newConflicts.filter((c: any) => c && c.slot === targetSlot),
      },
      next_step: {
        selected_slot: nextSlot,
        question: nextQuestion,
        status: nextStatus,
        macro_state: macroState,
        message_id: assistantMessageId,
      },
      messages: { user_message_id: userMessageId, assistant_message_id: assistantMessageId },
      external_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[CORRIDOR REPLY] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
