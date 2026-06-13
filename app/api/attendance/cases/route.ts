import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { generateCaseNumber } from '@/lib/attendance/case-number';

export const dynamic = 'force-dynamic';

// Colunas seguras retornadas na listagem (sem prompt/config/credencial).
const CASE_LIST_COLUMNS =
  'id, case_number, status, priority, channel, customer_name, customer_phone, intent, insurer_key, line_kind, macro_service, selected_corridor_key, selected_subcorridor_key, verification_status, risk_level, summary, next_step, created_at, updated_at, conversation_id, assigned_agent_id';

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

/**
 * GET /api/attendance/cases
 * Lista casos de atendimento da corretora do usuário logado.
 * Query: status?, limit?, q? (busca simples em customer_name/case_number).
 */
export async function GET(request: NextRequest) {
  try {
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

    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status');
    const q = (searchParams.get('q') || '').trim();
    const limitParam = searchParams.get('limit');
    const limit = Math.min(Math.max(parseInt(limitParam || '50', 10) || 50, 1), 200);

    let query = supabaseAdmin
      .from('attendance_cases')
      .select(CASE_LIST_COLUMNS)
      .eq('company_id', companyId)
      .order('updated_at', { ascending: false })
      .limit(limit);

    if (status) query = query.eq('status', status);
    // Sanitiza q para não quebrar a sintaxe do PostgREST .or() (remove vírgulas/parênteses/curingas).
    const safeQ = q.replace(/[,()%*]/g, '').trim();
    if (safeQ) query = query.or(`customer_name.ilike.%${safeQ}%,case_number.ilike.%${safeQ}%`);

    const { data: cases, error } = await query;
    if (error) {
      console.error('[ATTENDANCE CASES] list error:', error.message);
      return NextResponse.json({ error: 'Erro ao buscar casos' }, { status: 500 });
    }

    console.log(`[ATTENDANCE CASES] list: ${(cases || []).length} cases`);
    return NextResponse.json({ cases: cases || [] });
  } catch (error: any) {
    console.error('[ATTENDANCE CASES] GET error:', error?.message);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}

/**
 * POST /api/attendance/cases
 * Cria um caso manual/dry-run: caso + conversation (opcional) + corridor_run inicial.
 * NÃO envia WhatsApp, NÃO aciona seguradora, NÃO executa ação externa.
 */
export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }
    const userId = session.userId;

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, userId);
    if (!companyId) {
      return NextResponse.json({ error: 'Empresa não encontrada' }, { status: 400 });
    }

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    const customerName = typeof body.customer_name === 'string' ? body.customer_name.trim() : null;
    const customerPhone = typeof body.customer_phone === 'string' ? body.customer_phone.trim() : null;
    const problemDescription =
      typeof body.problem_description === 'string' ? body.problem_description.trim() : '';
    const channel = typeof body.channel === 'string' && body.channel.trim() ? body.channel.trim() : 'dashboard';
    const priority = typeof body.priority === 'string' && body.priority.trim() ? body.priority.trim() : 'normal';
    const subcorridorKey =
      typeof body.selected_subcorridor_key === 'string' && body.selected_subcorridor_key.trim()
        ? body.selected_subcorridor_key.trim()
        : 'electrician';
    const createConversation = body.create_conversation !== false;

    // --- Attendance Agent da empresa (opcional; null se ainda não existir) ---
    let attendanceAgentId: string | null = null;
    const { data: agentsData, error: agentsErr } = await supabaseAdmin
      .from('agents')
      .select('id, slug')
      .eq('company_id', companyId)
      .eq('is_active', true)
      .eq('agent_role', 'attendance');
    if (!agentsErr && agentsData && agentsData.length > 0) {
      const sandbox = agentsData.find((a: any) => a.slug === 'attendance-sandbox');
      attendanceAgentId = (sandbox || agentsData[0]).id;
    }

    // --- Template global Allianz Residencial / subcorredor ---
    const { data: template, error: templateErr } = await supabaseAdmin
      .from('corridor_templates')
      .select('id, corridor_key, subcorridor_key, display_name, readiness, required_slots, is_active')
      .eq('corridor_key', 'allianz_residential_assistance')
      .eq('subcorridor_key', subcorridorKey)
      .eq('is_active', true)
      .is('company_id', null)
      .maybeSingle();

    if (templateErr) {
      console.error('[ATTENDANCE CASES] template error:', templateErr.message);
      return NextResponse.json({ error: 'Erro ao buscar corredor' }, { status: 500 });
    }
    if (!template) {
      return NextResponse.json(
        { error: `Corredor não encontrado: allianz_residential_assistance/${subcorridorKey}` },
        { status: 404 },
      );
    }

    // --- Conversation (opcional) ---
    let conversationId: string | null = null;
    if (createConversation) {
      const { data: conv, error: convErr } = await supabaseAdmin
        .from('conversations')
        .insert({
          user_id: userId,
          company_id: companyId,
          agent_id: attendanceAgentId,
          session_id: crypto.randomUUID(),
          title: `Atendimento - ${customerName || 'Cliente'}`,
          status: 'active',
          channel: 'dashboard',
        })
        .select('id')
        .single();
      if (convErr) {
        console.error('[ATTENDANCE CASES] conversation error:', convErr.message);
        return NextResponse.json({ error: 'Erro ao criar conversa' }, { status: 500 });
      }
      conversationId = conv.id;
    }

    // --- attendance_cases ---
    const caseNumber = generateCaseNumber();
    const { data: createdCase, error: caseErr } = await supabaseAdmin
      .from('attendance_cases')
      .insert({
        company_id: companyId,
        conversation_id: conversationId,
        assigned_agent_id: attendanceAgentId,
        assigned_user_id: userId,
        case_number: caseNumber,
        status: 'collecting_slots',
        priority,
        channel,
        customer_name: customerName,
        customer_phone: customerPhone,
        intent: 'assistance_residential',
        insurer_key: 'allianz',
        line_kind: 'residential',
        macro_service: 'residential_assistance',
        selected_corridor_key: 'allianz_residential_assistance',
        selected_subcorridor_key: subcorridorKey,
        policy_source: 'unknown',
        verification_status: 'unverified',
        risk_level: 'low',
        handoff_required: false,
        summary: 'Atendimento residencial Allianz / Eletricista iniciado em modo sandbox.',
        next_step: 'Coletar dados mínimos e validar apólice antes de qualquer acionamento externo.',
      })
      .select('*')
      .single();

    if (caseErr) {
      console.error('[ATTENDANCE CASES] case insert error:', caseErr.message);
      return NextResponse.json({ error: 'Erro ao criar caso' }, { status: 500 });
    }

    // --- corridor_run inicial (slots filled/missing a partir do template) ---
    const requiredKeys: string[] = Array.isArray(template.required_slots)
      ? (template.required_slots as any[])
          .map((s) => (s && typeof s.key === 'string' ? s.key : null))
          .filter((k): k is string => Boolean(k))
      : [
          'problem_description',
          'electrical_issue_type',
          'risk_indicators',
          'affected_area',
          'property_address_confirmed',
          'policy_evidence_status',
          'contact_name',
          'contact_phone',
        ];

    const filled: Record<string, unknown> = {};
    if (problemDescription) filled.problem_description = problemDescription;
    if (customerName) filled.contact_name = customerName;
    if (customerPhone) filled.contact_phone = customerPhone;
    const missing = requiredKeys.filter((k) => !(k in filled));

    const { data: corridorRun, error: runErr } = await supabaseAdmin
      .from('corridor_runs')
      .insert({
        company_id: companyId,
        case_id: createdCase.id,
        corridor_template_id: template.id,
        phase: 'collect_slots',
        status: 'active',
        slots: { filled, missing, conflicts: [] },
        diagnostics: {
          mvp_mode: 'dry_run_hitl',
          template_readiness: template.readiness ?? null,
          external_action_allowed: false,
          hitl_required: true,
        },
        next_step: 'Perguntar uma informação por vez, começando por risco elétrico e área afetada.',
      })
      .select('*')
      .single();

    if (runErr) {
      console.error('[ATTENDANCE CASES] run insert error:', runErr.message);
      // Caso já criado; retorna o caso sem run para não perder o registro.
      return NextResponse.json(
        { case: createdCase, corridor_run: null, corridor_template: template, error: 'Erro ao iniciar corredor' },
        { status: 207 },
      );
    }

    console.log(
      `[ATTENDANCE CASES] created case ${createdCase.id} run ${corridorRun.id} subcorridor ${subcorridorKey}`,
    );

    return NextResponse.json(
      { case: createdCase, corridor_run: corridorRun, corridor_template: template, conversation_id: conversationId },
      { status: 201 },
    );
  } catch (error: any) {
    console.error('[ATTENDANCE CASES] POST error:', error?.message);
    return NextResponse.json({ error: 'Erro interno ao criar caso' }, { status: 500 });
  }
}
