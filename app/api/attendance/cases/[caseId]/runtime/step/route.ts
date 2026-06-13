import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { computeRuntimeStep, RUNTIME_ENGINE } from '@/lib/attendance/corridor-runtime';
import { resolveRuntimeConfig } from '@/lib/attendance/runtime-config-resolver';

export const dynamic = 'force-dynamic';

// Casos que NÃO podem ser editados pelo runtime (não reabrir/forçar automaticamente).
const NON_RUNTIME_STATUSES = new Set(['closed', 'cancelled', 'handoff']);

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
      case: caseAfter || caseRow,
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
