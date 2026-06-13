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

    // Camada de segurança: risco elétrico alto interrompe a coleta normal (42B5E).
    const safety = evaluateRuntimeSafetyDecision({ caseRow, targetSlot, extraction, filledSlots: newFilled });

    if (safety.triggered) {
      safetyTriggered = true;
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
