import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveRuntimeConfig } from '@/lib/attendance/runtime-config-resolver';
import {
  evaluateDispatchReadiness,
  buildDispatchPacket,
  dbStatusForPacketState,
  type DispatchPacketState,
} from '@/lib/attendance/dispatch-readiness';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';

export const dynamic = 'force-dynamic';

const NON_RUNTIME_STATUSES = new Set(['closed', 'cancelled']);

function safeCase(row: any): any {
  if (!row || typeof row !== 'object') return row;
  const { insured_document_ref: _omit, ...rest } = row;
  return rest;
}

function mergeObject(prev: unknown, patch: Record<string, unknown>): Record<string, unknown> {
  const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? (prev as Record<string, unknown>) : {};
  return { ...base, ...patch };
}

const NEXT_STEP: Record<DispatchPacketState, string> = {
  incomplete: 'Pacote de acionamento em rascunho, mas faltam dados do atendimento. Continue a coleta antes de acionar.',
  blocked:
    'Pacote de acionamento preparado, porém bloqueado (risco alto, apólice cancelada/vencida ou cobertura reprovada). Validação humana necessária antes de qualquer providência.',
  hitl_required:
    'Pacote de acionamento preparado em modo rascunho. Antes de acionar, é necessária validação humana da cobertura.',
  ready_for_human_approval:
    'Pacote de acionamento preparado. Aguardando aprovação humana para envio/acionamento.',
};

/**
 * POST /api/attendance/cases/[caseId]/runtime/dispatch-dry-run
 *
 * Prepara um Dispatch Packet em modo DRY-RUN/HITL: avalia readiness, aplica o
 * coverage gate (42I3B) e persiste o packet em dispatch_packets. NUNCA envia
 * WhatsApp/seguradora/prestador. external_action sempre {allowed:false, sent:false}.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;

    let body: Record<string, any> = {};
    try {
      body = await request.json();
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

    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (caseErr) {
      console.error('[DISPATCH DRY-RUN] case error:', caseErr.message);
      return NextResponse.json({ ok: false, error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) return NextResponse.json({ ok: false, error: 'Caso não encontrado' }, { status: 404 });
    if (NON_RUNTIME_STATUSES.has(caseRow.status)) {
      return NextResponse.json({ ok: false, error: 'case_not_runtime_editable' }, { status: 409 });
    }

    const { data: run } = await supabaseAdmin
      .from('corridor_runs')
      .select('*')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (!run?.id) {
      return NextResponse.json({ ok: false, error: 'corridor_run_not_found' }, { status: 409 });
    }

    let template: any = null;
    if (run.corridor_template_id) {
      const { data: tpl } = await supabaseAdmin
        .from('corridor_templates')
        .select('id, corridor_key, subcorridor_key, required_slots, metadata')
        .eq('id', run.corridor_template_id)
        .maybeSingle();
      template = tpl || null;
    }
    const runtimeConfig = resolveRuntimeConfig({ corridorTemplate: template, corridorRun: run, caseRow });

    const coverageReadiness = caseRow.metadata?.coverage_readiness ?? null;
    const evidencePack = caseRow.metadata?.policy_evidence_pack ?? null;

    const readiness = evaluateDispatchReadiness({
      caseRow,
      run,
      coverageReadiness,
      evidencePack,
      requiredSlots: runtimeConfig.slot_priority,
    });
    const generatedAt = new Date().toISOString();
    const packet = buildDispatchPacket({
      caseRow,
      run,
      template,
      evidencePack,
      coverageReadiness,
      readiness,
      generatedAt,
    });
    const dbStatus = dbStatusForPacketState(readiness.packet_state);
    const nextStep = NEXT_STEP[readiness.packet_state];

    // Upsert idempotente do packet dry-run (1 por caso).
    const idempotencyKey = `dispatch_dry_run:${caseRow.id}`;
    const { data: existing } = await supabaseAdmin
      .from('dispatch_packets')
      .select('id')
      .eq('company_id', companyId)
      .eq('idempotency_key', idempotencyKey)
      .maybeSingle();

    const packetRow = {
      company_id: companyId,
      case_id: caseRow.id,
      corridor_run_id: run.id,
      status: dbStatus,
      channel: null,
      provider: null,
      idempotency_key: idempotencyKey,
      payload: packet,
      missing_data: readiness.missing_slots,
      metadata: {
        mode: 'dry_run_hitl',
        packet_state: readiness.packet_state,
        readiness,
        external_action_allowed: false,
        external_action_sent: false,
      },
      updated_at: generatedAt,
    };

    let savedPacket: any = null;
    if (existing?.id) {
      const { data } = await supabaseAdmin
        .from('dispatch_packets')
        .update(packetRow)
        .eq('id', existing.id)
        .eq('company_id', companyId)
        .select('id, status, created_at, updated_at')
        .maybeSingle();
      savedPacket = data || null;
    } else {
      const { data } = await supabaseAdmin
        .from('dispatch_packets')
        .insert(packetRow)
        .select('id, status, created_at, updated_at')
        .maybeSingle();
      savedPacket = data || null;
    }

    // Persistir dispatch_readiness no caso (sem reabrir, sem encerrar, sem externo).
    const newMetadata = mergeObject(caseRow.metadata, {
      dispatch_readiness: {
        packet_state: readiness.packet_state,
        dispatch_allowed: readiness.dispatch_allowed,
        hitl_required: readiness.hitl_required,
        blockers: readiness.blockers,
        warnings: readiness.warnings,
        missing_slots: readiness.missing_slots,
        at: generatedAt,
      },
    });
    const { data: caseAfter } = await supabaseAdmin
      .from('attendance_cases')
      .update({ next_step: nextStep, metadata: newMetadata })
      .eq('id', caseRow.id)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();

    // Diagnostics do run (gate p/ futuros batches) — nunca libera externo.
    const prevDiag =
      run.diagnostics && typeof run.diagnostics === 'object' && !Array.isArray(run.diagnostics)
        ? (run.diagnostics as Record<string, any>)
        : {};
    const prevRuntime =
      prevDiag.runtime && typeof prevDiag.runtime === 'object' && !Array.isArray(prevDiag.runtime)
        ? prevDiag.runtime
        : {};
    await supabaseAdmin
      .from('corridor_runs')
      .update({
        diagnostics: {
          ...prevDiag,
          external_action_allowed: false,
          hitl_required: readiness.hitl_required,
          dispatch_allowed: readiness.dispatch_allowed,
          dispatch_readiness: { packet_state: readiness.packet_state, blockers: readiness.blockers, warnings: readiness.warnings },
          runtime: { ...prevRuntime, last_step_at: generatedAt, dispatch_packet_state: readiness.packet_state },
        },
      })
      .eq('id', run.id)
      .eq('company_id', companyId);

    console.log(
      `[DISPATCH DRY-RUN] case=${caseId} company=${companyId} packet_state=${readiness.packet_state} db_status=${dbStatus} packet_id=${savedPacket?.id ?? 'none'}`,
    );

    return NextResponse.json({
      ok: true,
      case: safeCase(caseAfter || caseRow),
      dispatch_packet: { ...packet, id: savedPacket?.id ?? null, db_status: dbStatus },
      dispatch_readiness: readiness,
      next_step: nextStep,
      external_action: { allowed: false, sent: false, reason: 'mvp_dry_run_hitl' },
    });
  } catch (error: any) {
    console.error('[DISPATCH DRY-RUN] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
