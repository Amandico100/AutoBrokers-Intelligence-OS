import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';

export const dynamic = 'force-dynamic';

const NON_RUNTIME_STATUSES = new Set(['closed', 'cancelled']);
const DECISIONS = new Set(['approved', 'rejected', 'needs_more_info']);
const MAX_REASON = 500;

function safeCase(row: any): any {
  if (!row || typeof row !== 'object') return row;
  const { insured_document_ref: _omit, ...rest } = row;
  return rest;
}

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/coverage-validation
 *
 * Decisão HITL de cobertura (humana). Atualiza coverage_readiness + coverage_evidence
 * (sem nova tabela). NUNCA envia externo, NUNCA usa LLM para decidir. O dispatch
 * permanece dry-run/HITL — esta rota só registra a decisão humana de cobertura.
 *
 * Body: { decision: 'approved'|'rejected'|'needs_more_info', reason?, source? }
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

    let body: { decision?: string; reason?: string; source?: string } = {};
    try {
      body = (await request.json()) as typeof body;
    } catch {
      body = {};
    }
    const decision = typeof body.decision === 'string' ? body.decision.trim().toLowerCase() : '';
    if (!DECISIONS.has(decision)) {
      return NextResponse.json({ ok: false, error: 'decision inválida (approved|rejected|needs_more_info)' }, { status: 400 });
    }
    const reason = typeof body.reason === 'string' ? body.reason.trim().slice(0, MAX_REASON) : '';

    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (caseErr) {
      console.error('[COVERAGE VALIDATION] case error:', caseErr.message);
      return NextResponse.json({ ok: false, error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });
    if (NON_RUNTIME_STATUSES.has(caseRow.status)) {
      return NextResponse.json({ ok: false, error: 'case_not_runtime_editable' }, { status: 409 });
    }

    const prevReadiness =
      caseRow.metadata?.coverage_readiness && typeof caseRow.metadata.coverage_readiness === 'object'
        ? (caseRow.metadata.coverage_readiness as Record<string, any>)
        : null;
    const prevEvidence =
      caseRow.coverage_evidence && typeof caseRow.coverage_evidence === 'object' && !Array.isArray(caseRow.coverage_evidence)
        ? (caseRow.coverage_evidence as Record<string, any>)
        : null;
    if (!prevEvidence) {
      return NextResponse.json(
        { ok: false, error: 'no_coverage_to_validate', hint: 'Selecione uma apólice (policy-select) antes de validar cobertura.' },
        { status: 409 },
      );
    }

    const at = new Date().toISOString();
    const humanValidation = { decision, reason: reason || null, by: 'human', at };

    let nextState: string;
    let dispatchAllowed: boolean;
    let humanRequired: boolean;
    let nextStep: string;
    let readinessMessage: string;
    const caseUpdate: Record<string, unknown> = {};

    if (decision === 'approved') {
      nextState = 'human_approved';
      dispatchAllowed = true;
      humanRequired = false;
      readinessMessage =
        'Cobertura validada manualmente por um humano. Posso preparar o acionamento (ainda aguardando aprovação humana de envio, sem ação externa).';
      nextStep = 'Cobertura validada por um humano. Pacote pode ser preparado para aprovação de envio (sem ação externa neste MVP).';
      // Eleva a verificação para humana (status confiável).
      caseUpdate.verification_status = 'verified_by_human';
    } else if (decision === 'rejected') {
      nextState = 'human_rejected';
      dispatchAllowed = false;
      humanRequired = true;
      readinessMessage = 'Cobertura reprovada na validação humana. Não vou acionar; o caso segue para tratativa humana/alternativa.';
      nextStep = 'Cobertura reprovada na validação humana. Não acionar; encaminhar para tratativa humana ou alternativa com o segurado.';
    } else {
      nextState = 'needs_more_info';
      dispatchAllowed = false;
      humanRequired = true;
      readinessMessage = 'A validação humana pediu mais informações antes de confirmar a cobertura.';
      nextStep = 'Validação humana solicitou mais informações antes de confirmar a cobertura. Coletar o que falta e revalidar.';
    }

    const newReadiness = {
      ...(prevReadiness || {}),
      state: nextState,
      dispatch_allowed: dispatchAllowed,
      human_required: humanRequired,
      message: readinessMessage,
      human_validation: humanValidation,
    };
    const newEvidence = {
      ...prevEvidence,
      verified_by: decision === 'approved' ? 'human' : prevEvidence.verified_by,
      human_required: humanRequired,
      human_validation: humanValidation,
    };

    const newMetadata = mergeObject(caseRow.metadata, { coverage_readiness: newReadiness });
    caseUpdate.metadata = newMetadata;
    caseUpdate.coverage_evidence = newEvidence;
    caseUpdate.next_step = nextStep;

    const { data: caseAfter } = await supabaseAdmin
      .from('attendance_cases')
      .update(caseUpdate)
      .eq('id', caseRow.id)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();

    // Atualiza diagnostics do último run (gate; nunca libera externo).
    const { data: run } = await supabaseAdmin
      .from('corridor_runs')
      .select('id, diagnostics')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (run?.id) {
      const prevDiag =
        run.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
          ? (run.diagnostics as Record<string, any>)
          : {};
      await supabaseAdmin
        .from('corridor_runs')
        .update({
          next_step: nextStep,
          diagnostics: {
            ...prevDiag,
            external_action_allowed: false,
            dispatch_allowed: dispatchAllowed,
            coverage_human_decision: { decision, at },
          },
        })
        .eq('id', run.id)
        .eq('company_id', companyId);
    }

    console.log(`[COVERAGE VALIDATION] case=${caseId} company=${companyId} decision=${decision} state=${nextState}`);

    return NextResponse.json({
      ok: true,
      case: safeCase(caseAfter || caseRow),
      coverage_validation: {
        decision,
        state: nextState,
        dispatch_allowed: dispatchAllowed,
        human_required: humanRequired,
        message: readinessMessage,
      },
      next_step: nextStep,
      external_action: { allowed: false, sent: false },
    });
  } catch (error: any) {
    console.error('[COVERAGE VALIDATION] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
