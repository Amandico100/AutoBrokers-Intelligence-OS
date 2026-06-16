import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { sanitizePolicySnapshot } from '@/lib/attendance/policy-lookup';
import { loadInfocapPolicyDetail, lookupInfocapPolicy } from '@/lib/attendance/connectors/infocap-policy-lookup';
import {
  normalizeEvidencePack,
  evidencePackToCoverageEvidence,
  buildPolicyInterpretationContext,
  safeEvidencePackSummary,
  evaluateCoverageReadiness,
} from '@/lib/attendance/policy-evidence-pack';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';

export const dynamic = 'force-dynamic';

const NON_RUNTIME_STATUSES = new Set(['handoff', 'closed', 'cancelled']);

/** Próximo passo após selecionar e registrar a apólice (42I3A req.7). */
const NEXT_STEP_AFTER_SELECT =
  'Apólice selecionada e registrada. Próximo passo: confirmar endereço do atendimento e dados mínimos para acionamento.';

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

function safeCase(row: any): any {
  if (!row || typeof row !== 'object') return row;
  const { insured_document_ref: _omit, ...rest } = row;
  return rest;
}

/** Extrai um codfil seguro (número) das refs do cliente armazenadas/lookup. */
function pickCodfil(...sources: any[]): number | undefined {
  for (const src of sources) {
    const v = src?.codfil;
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && v.trim() && Number.isFinite(Number(v))) return Number(v);
  }
  return undefined;
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/policy-select
 *
 * Seleciona uma apólice (policy_ref) entre os matches da InfoCap, carrega o
 * DETALHE via conector (backend → /documento), monta o Policy Evidence Pack e
 * persiste como verified_by_connector / policy_evidence_ready. NUNCA confirma
 * cobertura sem itens/coberturas no documento. NÃO envia WhatsApp, NÃO dispara
 * dispatch/approval, NÃO aciona seguradora/prestador. Sem PII/segredo.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;

    let body: { source?: string; policy_ref?: string; company_id?: string } = {};
    try {
      body = (await request.json()) as { source?: string; policy_ref?: string; company_id?: string };
    } catch {
      body = {};
    }

    // Auth: sessão (dashboard) OU chave interna (bridge WhatsApp 42W1). Aditivo.
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    const supabaseAdmin = getAdminClient();
    let companyId: string | null = null;
    if (session.userId) {
      companyId = await getCompanyId(supabaseAdmin, session.userId);
    } else {
      companyId = resolveInternalCompanyId(request, body);
      if (!companyId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });
    }
    if (!companyId) return NextResponse.json({ ok: false, error: 'Empresa não encontrada' }, { status: 404 });
    const source = (body.source || 'infocap').toLowerCase();
    if (source !== 'infocap' && source !== 'connector') {
      return NextResponse.json({ ok: false, error: 'source deve ser infocap/connector' }, { status: 400 });
    }
    const policyRef = typeof body.policy_ref === 'string' ? body.policy_ref.trim() : '';
    if (!policyRef) {
      return NextResponse.json({ ok: false, error: 'policy_ref é obrigatório' }, { status: 400 });
    }

    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (caseErr) {
      console.error('[POLICY SELECT] case error:', caseErr.message);
      return NextResponse.json({ ok: false, error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });
    if (NON_RUNTIME_STATUSES.has(caseRow.status)) {
      return NextResponse.json({ ok: false, error: 'case_not_runtime_editable' }, { status: 409 });
    }

    // 1. Validar que policy_ref veio de uma lista anterior de matches; senão, recarregar pelo conector.
    const prevLookup = caseRow.metadata?.policy_lookup;
    let knownRefs: string[] = Array.isArray(prevLookup?.matches)
      ? prevLookup.matches.map((m: any) => String(m?.policy_ref)).filter(Boolean)
      : [];
    let clientRef = prevLookup?.client_ref ?? null;

    if (!knownRefs.includes(policyRef)) {
      // Recarrega matches frescos pelo conector para validar a seleção.
      const refresh = await lookupInfocapPolicy({
        companyId,
        caseId: caseRow.id,
        documentRef: typeof caseRow.insured_document_ref === 'string' ? caseRow.insured_document_ref : undefined,
        customerName: typeof caseRow.customer_name === 'string' ? caseRow.customer_name : undefined,
      });
      const refreshRefs = Array.isArray(refresh.matches)
        ? refresh.matches.map((m: any) => String(m?.policy_ref)).filter(Boolean)
        : [];
      knownRefs = refreshRefs;
      clientRef = refresh.client_ref ?? clientRef;
      const selfFound =
        refresh.status === 'found' && refresh.selected?.policy_ref === policyRef;
      if (!refreshRefs.includes(policyRef) && !selfFound) {
        return NextResponse.json(
          {
            ok: false,
            error: 'policy_ref_not_in_matches',
            hint: 'policy_ref não corresponde a nenhuma apólice retornada pela InfoCap para este caso.',
            policy_select_result: { status: 'invalid_policy_ref', source: 'infocap', requires_human: true },
          },
          { status: 409 },
        );
      }
    }

    // 2. Carregar detalhe da apólice selecionada.
    const codfil = pickCodfil(clientRef);
    const detail = await loadInfocapPolicyDetail({ companyId, policyRef, codfil });
    console.log(
      `[POLICY SELECT] case=${caseId} company=${companyId} provider=infocap status=${detail.status} selected_policy_ref=${policyRef}`,
    );

    if (detail.status !== 'found' || !detail.policy_evidence_pack) {
      // Não confirma cobertura; mantém o caso aguardando, registra diagnóstico seguro.
      const safeSummary = {
        provider: 'infocap',
        stage: 'policy_select',
        status: detail.status,
        selected_policy_ref: policyRef,
        blockers: detail.blockers || [],
        at: new Date().toISOString(),
      };
      const newMeta = mergeObject(caseRow.metadata, { policy_select: safeSummary });
      await supabaseAdmin
        .from('attendance_cases')
        .update({ metadata: newMeta })
        .eq('id', caseRow.id)
        .eq('company_id', companyId);
      return NextResponse.json({
        ok: false,
        provider: 'infocap',
        policy_select_result: {
          status: detail.status,
          source: 'infocap',
          selected_policy_ref: policyRef,
          verification_status: 'unverified',
          blockers: detail.blockers || [],
          requires_human: true,
        },
        external_action: { sent: false, allowed: false },
      });
    }

    // 3. Normalizar pack + montar evidência/contexto.
    const pack = normalizeEvidencePack(detail.policy_evidence_pack);
    if (!pack) {
      return NextResponse.json({ ok: false, error: 'invalid_evidence_pack' }, { status: 502 });
    }
    const verifiedAt = detail.verified_at || new Date().toISOString();
    const coverageEvidence = evidencePackToCoverageEvidence(pack, detail.source_ref || 'infocap:documento', verifiedAt);
    const interpretation = buildPolicyInterpretationContext({ pack });
    const packSummary = safeEvidencePackSummary(pack);
    // Coverage Readiness Gate (42I3B): decide se pode seguir p/ acionamento.
    const readiness = evaluateCoverageReadiness({
      coverage_confirmed: interpretation.coverage_confirmed,
      human_required: pack.human_required,
      confidence: pack.confidence,
      cancelled: pack.cancelled,
      expired: pack.expired,
      active_now: pack.active_now,
      coverages_count: pack.coverages_count,
      insurer: pack.insurer_detected,
      product: pack.product_detected,
    });

    const policySnapshot = {
      ...sanitizePolicySnapshot({
        insurer_key: pack.insurer_detected,
        product: pack.product_detected,
        line_kind: pack.line_kind_detected,
        policy_status: pack.policy_status,
        masked_policy_number: pack.masked_policy_number,
        valid_from: pack.valid_from,
        valid_to: pack.valid_to,
        source: 'connector',
      }),
      active_now: pack.active_now,
      expired: pack.expired,
      coverages_count: pack.coverages_count,
      cancelled: pack.cancelled,
      assistance_signals: pack.assistance_signals,
      coverage_sections: pack.coverage_sections,
      policy_ref: pack.policy_ref,
      evidence_confidence: pack.confidence,
    };

    // 4. Persistir no caso + último run.
    const newMetadata = mergeObject(caseRow.metadata, {
      attendance_macro_state: 'policy_evidence_ready',
      policy_evidence_pack: packSummary,
      policy_interpretation_context: interpretation,
      coverage_readiness: readiness,
      policy_select: {
        provider: 'infocap',
        status: 'selected',
        selected_policy_ref: policyRef,
        confidence: pack.confidence,
        readiness_state: readiness.state,
        dispatch_allowed: readiness.dispatch_allowed,
        at: verifiedAt,
      },
    });

    const { data: caseAfter } = await supabaseAdmin
      .from('attendance_cases')
      .update({
        policy_source: 'connector',
        policy_number: null,
        policy_snapshot: policySnapshot,
        coverage_evidence: coverageEvidence,
        verification_status: 'verified_by_connector',
        next_step: NEXT_STEP_AFTER_SELECT,
        metadata: newMetadata,
      })
      .eq('id', caseRow.id)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();

    const { data: run } = await supabaseAdmin
      .from('corridor_runs')
      .select('id, diagnostics')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    let updatedRun: any = run || null;
    if (run?.id) {
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
          last_agent_action: 'policy_select:connector_verified',
          next_step: NEXT_STEP_AFTER_SELECT,
          diagnostics: {
            ...prevDiag,
            external_action_allowed: false,
            hitl_required: readiness.human_required,
            dispatch_allowed: readiness.dispatch_allowed,
            coverage_readiness: { state: readiness.state, dispatch_allowed: readiness.dispatch_allowed, reasons: readiness.reasons },
            runtime: {
              ...prevRuntime,
              last_step_at: new Date().toISOString(),
              macro_state: 'policy_evidence_ready',
              coverage_evidence_ready: true,
              coverage_readiness: readiness.state,
              policy_evidence_pack: packSummary,
            },
          },
        })
        .eq('id', run.id)
        .eq('company_id', companyId)
        .select('*')
        .maybeSingle();
      if (runAfter) updatedRun = runAfter;
    }

    return NextResponse.json({
      ok: true,
      case: safeCase(caseAfter || caseRow),
      corridor_run: updatedRun,
      policy_select_result: {
        status: 'policy_evidence_ready',
        source: 'connector',
        selected_policy_ref: policyRef,
        verification_status: 'verified_by_connector',
        confidence: pack.confidence,
        coverage_confirmed: interpretation.coverage_confirmed,
        requires_human: pack.human_required,
        coverage_readiness: readiness,
        assistant_message: readiness.message,
        policy_evidence_pack: pack,
        policy_interpretation_context: interpretation,
      },
      external_action: { sent: false, allowed: false },
    });
  } catch (error: any) {
    console.error('[POLICY SELECT] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
