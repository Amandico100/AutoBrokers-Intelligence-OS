import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, SessionData } from '@/lib/iron-session';

export const dynamic = 'force-dynamic';

function getAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

async function getCompanyId(supabaseAdmin: ReturnType<typeof getAdminClient>, userId: string) {
  const { data, error } = await supabaseAdmin
    .from('users_v2')
    .select('company_id')
    .eq('id', userId)
    .single();
  if (error || !data?.company_id) return null;
  return data.company_id as string;
}

// Campos que o PATCH mínimo permite atualizar (whitelist; DB valida CHECKs).
const PATCHABLE_FIELDS = ['status', 'priority', 'summary', 'next_step', 'handoff_required', 'handoff_reason'] as const;

/**
 * GET /api/attendance/cases/[caseId]
 * Retorna caso + conversation + messages + corridor_run + corridor_template + dispatch_packets.
 * Garante isolamento por company_id do usuário logado.
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) {
      return NextResponse.json({ error: 'Empresa não encontrada' }, { status: 404 });
    }

    const { data: caseRow, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .select('*')
      .eq('id', caseId)
      .eq('company_id', companyId)
      .maybeSingle();

    if (caseErr) {
      console.error('[ATTENDANCE CASE] fetch error:', caseErr.message);
      return NextResponse.json({ error: 'Erro ao buscar caso' }, { status: 500 });
    }
    if (!caseRow) {
      return NextResponse.json({ error: 'Caso não encontrado' }, { status: 404 });
    }

    // Conversation + messages (canal do cliente espelhado)
    let conversation: any = null;
    let messages: any[] = [];
    if (caseRow.conversation_id) {
      const { data: conv } = await supabaseAdmin
        .from('conversations')
        .select('id, agent_id, session_id, status, title, channel, created_at, updated_at')
        .eq('id', caseRow.conversation_id)
        .maybeSingle();
      conversation = conv || null;
      if (conv) {
        const { data: msgs } = await supabaseAdmin
          .from('messages')
          .select('id, role, content, type, created_at, sender_user_id')
          .eq('conversation_id', conv.id)
          .order('created_at', { ascending: true });
        messages = msgs || [];
      }
    }

    // Último corridor_run do caso + template
    const { data: corridorRun } = await supabaseAdmin
      .from('corridor_runs')
      .select('*')
      .eq('case_id', caseRow.id)
      .order('started_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    let corridorTemplate: any = null;
    if (corridorRun?.corridor_template_id) {
      const { data: tpl } = await supabaseAdmin
        .from('corridor_templates')
        .select(
          'id, corridor_key, subcorridor_key, display_name, insurer_key, line_kind, macro_service, readiness, status_documental, status_operacional, phases, required_slots, optional_slots, guardrails, golden_tests, allowed_channels',
        )
        .eq('id', corridorRun.corridor_template_id)
        .maybeSingle();
      corridorTemplate = tpl || null;
    }

    // Dispatch packets do caso
    const { data: dispatchPackets } = await supabaseAdmin
      .from('dispatch_packets')
      .select('id, status, channel, provider, idempotency_key, missing_data, approval_request_id, created_at, updated_at, approved_at, sent_at')
      .eq('case_id', caseRow.id)
      .order('created_at', { ascending: false });

    return NextResponse.json({
      case: caseRow,
      conversation,
      messages,
      corridor_run: corridorRun || null,
      corridor_template: corridorTemplate,
      dispatch_packets: dispatchPackets || [],
    });
  } catch (error: any) {
    console.error('[ATTENDANCE CASE] GET error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

/**
 * PATCH /api/attendance/cases/[caseId]
 * Atualização mínima e segura (status/priority/summary/next_step/handoff_*).
 * NÃO executa ação externa. Isolado por company_id.
 */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) {
      return NextResponse.json({ error: 'Empresa não encontrada' }, { status: 404 });
    }

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    const update: Record<string, unknown> = {};
    for (const field of PATCHABLE_FIELDS) {
      if (field in body && body[field] !== undefined) update[field] = body[field];
    }
    if (Object.keys(update).length === 0) {
      return NextResponse.json({ error: 'Nenhum campo válido para atualizar.' }, { status: 400 });
    }

    const { data: updated, error } = await supabaseAdmin
      .from('attendance_cases')
      .update(update)
      .eq('id', caseId)
      .eq('company_id', companyId)
      .select('*')
      .maybeSingle();

    if (error) {
      console.error('[ATTENDANCE CASE] patch error:', error.message);
      return NextResponse.json({ error: 'Erro ao atualizar caso' }, { status: 400 });
    }
    if (!updated) {
      return NextResponse.json({ error: 'Caso não encontrado' }, { status: 404 });
    }

    return NextResponse.json({ case: updated });
  } catch (error: any) {
    console.error('[ATTENDANCE CASE] PATCH error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
