import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import {
  applyPolicyLookupResultToCasePayload,
  buildMockPolicyLookupResult,
  buildPolicyLookupResult,
  isKnownFixture,
  POLICY_LOOKUP_FIXTURES,
  validatePolicyLookupInput,
  type PolicyLookupCaseData,
  type PolicyLookupInput,
  type PolicyLookupResult,
} from '@/lib/attendance/policy-lookup';
import { lookupInfocapPolicy } from '@/lib/attendance/connectors/infocap-policy-lookup';

export const dynamic = 'force-dynamic';

const NON_RUNTIME_STATUSES = new Set(['handoff', 'closed', 'cancelled']);

/** Merge raso e seguro de jsonb (metadata/diagnostics). */
function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

/** Remove campos sensíveis do caso antes de devolver ao cliente. */
function safeCase(row: any): any {
  if (!row || typeof row !== 'object') return row;
  const { insured_document_ref: _omit, ...rest } = row;
  return rest;
}

/** Persiste um policy_lookup_result nos campos existentes (run + case). Reusado por mock/manual/connector. */
async function persistPolicyLookupResult(
  supabaseAdmin: ReturnType<typeof getAdminClient>,
  caseRow: any,
  companyId: string,
  result: PolicyLookupResult,
  rawPolicyNumber: string | null,
): Promise<{ caseAfter: any; updatedRun: any }> {
  const payload = applyPolicyLookupResultToCasePayload(result, rawPolicyNumber);

  const { data: run } = await supabaseAdmin
    .from('corridor_runs')
    .select('*')
    .eq('case_id', caseRow.id)
    .order('started_at', { ascending: false })
    .limit(1)
    .maybeSingle();

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
      external_action_allowed: false,
      hitl_required: true,
      runtime: { ...prevRuntime, last_step_at: new Date().toISOString(), ...payload.runtimePatch },
    };
    const { data: runAfter } = await supabaseAdmin
      .from('corridor_runs')
      .update({ diagnostics: newDiagnostics, last_agent_action: payload.lastAgentAction, next_step: payload.caseFields.next_step })
      .eq('id', run.id)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();
    if (runAfter) updatedRun = runAfter;
  }

  const newMetadata = mergeObject(caseRow.metadata, {
    attendance_macro_state: payload.metadataPatch.attendance_macro_state,
    policy_lookup: payload.metadataPatch.policy_lookup,
  });
  const { data: caseAfter } = await supabaseAdmin
    .from('attendance_cases')
    .update({
      policy_source: payload.caseFields.policy_source,
      policy_number: payload.caseFields.policy_number,
      policy_snapshot: payload.caseFields.policy_snapshot,
      coverage_evidence: payload.caseFields.coverage_evidence,
      verification_status: payload.caseFields.verification_status,
      next_step: payload.caseFields.next_step,
      metadata: newMetadata,
    })
    .eq('id', caseRow.id)
    .eq('company_id', companyId)
    .select('*')
    .maybeSingle();

  return { caseAfter, updatedRun };
}

/**
 * POST /api/attendance/cases/[caseId]/runtime/policy-lookup
 *
 * Resolvedor MANUAL/MOCK de apólice (42I1). Gera um policy_lookup_result
 * estruturado e grava evidência de cobertura nos campos existentes de
 * attendance_cases. NÃO chama InfoCap real, NÃO usa credenciais, NÃO cria SQL,
 * NÃO envia WhatsApp, NÃO cria approval/dispatch, NÃO retoma o corredor (42B5H).
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

    let body: PolicyLookupInput = {};
    try {
      body = (await request.json()) as PolicyLookupInput;
    } catch {
      body = {};
    }

    const force = body.force === true;
    const mode = (typeof body.mode === 'string' && body.mode.trim()) || (typeof body.source === 'string' && body.source.trim()) || '';
    const modeLc = mode.toLowerCase();
    const isInfocap = modeLc === 'infocap' || modeLc === 'connector';
    const isMock = modeLc === 'mock';

    // validate só vale p/ mock/manual; infocap é resolvido pelo adapter (Vault).
    if (!isInfocap) {
      const validation = validatePolicyLookupInput(body);
      if (!validation.valid) {
        return NextResponse.json({ ok: false, error: validation.error || 'Body inválido' }, { status: 400 });
      }
    }

    // Caso (isolado por company_id)
    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (caseErr) {
      console.error('[POLICY LOOKUP] case error:', caseErr.message);
      return NextResponse.json({ ok: false, error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });

    if (NON_RUNTIME_STATUSES.has(caseRow.status)) {
      return NextResponse.json({ ok: false, error: 'case_not_runtime_editable' }, { status: 409 });
    }

    const macroState = caseRow.metadata?.attendance_macro_state;
    const inPolicyGate = caseRow.status === 'policy_check' || macroState === 'policy_lookup_required';
    if (!inPolicyGate && !force) {
      return NextResponse.json(
        { ok: false, error: 'case_not_in_policy_lookup', hint: 'Caso não está em policy_lookup_required/policy_check. Use force=true para sobrescrever.' },
        { status: 409 },
      );
    }

    // ── 42I2: InfoCap read-only via Vault ──────────────────────────────────
    if (isInfocap) {
      const infocap = await lookupInfocapPolicy({
        companyId,
        caseId: caseRow.id,
        documentRef: typeof caseRow.insured_document_ref === 'string' ? caseRow.insured_document_ref : undefined,
        customerName: typeof caseRow.customer_name === 'string' ? caseRow.customer_name : undefined,
      });
      console.log(
        `[POLICY LOOKUP] case=${caseId} company=${companyId} provider=infocap status=${infocap.status}`,
      );

      if (infocap.status === 'found' && infocap.coverage_evidence && infocap.selected) {
        // Caminho real (inerte por enquanto): mapeia para o contrato e persiste como verified_by_connector.
        const connectorResult: PolicyLookupResult = {
          status: 'policy_evidence_ready',
          source: 'connector',
          source_ref: infocap.source_ref ?? 'infocap',
          queried_document_type: caseRow.metadata?.identity?.document_type ?? null,
          matches: [],
          selected: {
            policy_ref: infocap.selected.policy_ref,
            insurer_key: infocap.selected.insurer_key ?? 'unknown',
            product: infocap.selected.product ?? null,
            line_kind: infocap.selected.line_kind ?? 'unknown',
            policy_status: infocap.selected.policy_status ?? 'unknown',
            masked_policy_number: infocap.selected.masked_policy_number ?? '****',
            holder_name_masked: infocap.selected.holder_name_masked ?? null,
            valid_from: null,
            valid_to: null,
          },
          coverage_evidence: { ...infocap.coverage_evidence },
          verification_status: 'verified_by_connector',
          next_macro_state: 'policy_evidence_ready',
          blockers: [],
          requires_human: false,
          notes: (infocap.notes || []).join(' ') || null,
        };
        const { caseAfter, updatedRun } = await persistPolicyLookupResult(
          supabaseAdmin,
          caseRow,
          companyId,
          connectorResult,
          null,
        );
        return NextResponse.json({
          ok: true,
          case: safeCase(caseAfter || caseRow),
          corridor_run: updatedRun,
          policy_lookup_result: connectorResult,
          external_action: { sent: false, allowed: false },
        });
      }

      // Não encontrado / não configurado / não suportado → NÃO confirma cobertura,
      // NÃO altera verification_status; mantém o caso aguardando validação.
      return NextResponse.json({
        ok: false,
        provider: 'infocap',
        policy_lookup_result: {
          status: infocap.status,
          source: 'infocap',
          verification_status: 'unverified',
          blockers: infocap.blockers || [],
          requires_human: Boolean(infocap.requires_human),
          notes: infocap.notes || [],
        },
        external_action: { sent: false, allowed: false },
      });
    }

    const caseData: PolicyLookupCaseData = {
      customer_name: caseRow.customer_name ?? null,
      insured_name: caseRow.insured_name ?? null,
      document_type: caseRow.metadata?.identity?.document_type ?? null,
    };

    // Construir o resultado (mock ou manual)
    let result;
    let rawPolicyNumber: string | null;
    if (isMock) {
      const fixture = typeof body.fixture === 'string' ? body.fixture.trim() : '';
      if (!isKnownFixture(fixture)) {
        return NextResponse.json(
          { ok: false, error: 'unknown_fixture', available: POLICY_LOOKUP_FIXTURES },
          { status: 422 },
        );
      }
      result = buildMockPolicyLookupResult(fixture, caseData);
      rawPolicyNumber = 'MOCK-ALLIANZ-RES-0001';
    } else {
      result = buildPolicyLookupResult(body, caseData);
      rawPolicyNumber = typeof body.policy_number === 'string' && body.policy_number.trim() ? body.policy_number.trim() : null;
    }

    const { caseAfter, updatedRun } = await persistPolicyLookupResult(
      supabaseAdmin,
      caseRow,
      companyId,
      result,
      rawPolicyNumber,
    );

    // Log seguro: sem CPF/CNPJ/PII.
    console.log(
      `[POLICY LOOKUP] case=${caseId} source=${result.source} status=${result.status} verification=${result.verification_status} macro=${result.next_macro_state}`,
    );

    return NextResponse.json({
      ok: true,
      case: safeCase(caseAfter || caseRow),
      corridor_run: updatedRun,
      policy_lookup_result: result,
      external_action: { sent: false, allowed: false },
    });
  } catch (error: any) {
    console.error('[POLICY LOOKUP] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
