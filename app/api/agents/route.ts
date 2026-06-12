import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, SessionData } from '@/lib/iron-session';

export const dynamic = 'force-dynamic';

// Papéis que NÃO pertencem ao chat principal (Core interno da corretora).
// Attendance/corridor/connector/system são voltados a outros runtimes (SPEC-004/005).
const NON_CORE_CHAT_ROLES = new Set(['attendance', 'corridor', 'connector', 'system']);

/**
 * Decide se um agente pertence ao chat principal (AutoBrokers Core).
 * Inclui agentes legados (sem agent_role) e agentes com agent_role='core'.
 * Exclui explicitamente papéis não-Core. Backward-compatible.
 */
function isCoreChatAgent(role: unknown): boolean {
  if (role === null || role === undefined) return true; // legado: sem papel declarado
  if (typeof role !== 'string') return true;            // tipo inesperado: trata como legado
  const r = role.trim().toLowerCase();
  if (r === '' || r === 'core') return true;
  if (NON_CORE_CHAT_ROLES.has(r)) return false;
  return false; // qualquer outro papel declarado não entra no chat Core
}

/**
 * GET /api/agents
 *
 * Lists active CORE-chat agents for the logged-in user's company.
 * Excludes Attendance/corridor/connector/system agents (SPEC-005 boundary).
 * Requires: smith_user_session cookie
 */
export async function GET(request: NextRequest) {
  try {
    // =============================================
    // AUTHENTICATION CHECK
    // =============================================
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);

    if (!session.userId) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const userId = session.userId;

    // =============================================
    // SERVICE ROLE CLIENT
    // =============================================
    const supabaseAdmin = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      { auth: { persistSession: false } },
    );

    // =============================================
    // GET USER'S COMPANY
    // =============================================
    const { data: userData, error: userError } = await supabaseAdmin
      .from('users_v2')
      .select('company_id')
      .eq('id', userId)
      .single();

    if (userError || !userData?.company_id) {
      return NextResponse.json({ error: 'Empresa não encontrada' }, { status: 404 });
    }

    // =============================================
    // FETCH ACTIVE AGENTS
    // =============================================
    const SELECT_WITH_ROLE = 'id, name, is_subagent, allow_direct_chat, agent_role, agent_audience, blueprint_version';
    const SELECT_LEGACY = 'id, name, is_subagent, allow_direct_chat';

    let agents: any[] | null = null;
    let agentsError: any = null;

    ({ data: agents, error: agentsError } = await supabaseAdmin
      .from('agents')
      .select(SELECT_WITH_ROLE)
      .eq('company_id', userData.company_id)
      .eq('is_active', true)
      .order('created_at', { ascending: true }));

    // Resiliência a schema: se as colunas de papel não existirem em algum ambiente,
    // cai para a seleção legada (todos tratados como Core) — chat nunca quebra.
    if (agentsError) {
      console.warn('[AGENTS API] role columns unavailable, using legacy select');
      ({ data: agents, error: agentsError } = await supabaseAdmin
        .from('agents')
        .select(SELECT_LEGACY)
        .eq('company_id', userData.company_id)
        .eq('is_active', true)
        .order('created_at', { ascending: true }));
    }

    if (agentsError) {
      console.error('[AGENTS API] Error:', agentsError);
      return NextResponse.json({ error: 'Erro ao buscar agentes' }, { status: 500 });
    }

    const allAgents = agents || [];

    // 1) Esconde subagents sem allow_direct_chat (comportamento legado preservado).
    // 2) Mantém apenas agentes de papel Core/legado no chat principal (boundary SPEC-005).
    const chatAgents = allAgents
      .filter((a: any) => !a.is_subagent || a.allow_direct_chat)
      .filter((a: any) => isCoreChatAgent(a.agent_role));

    // Observabilidade segura: apenas contagens (sem prompt/config/token/PII).
    console.log(`[AGENTS API] core-chat agents: ${chatAgents.length}/${allAgents.length}`);

    return NextResponse.json({ agents: chatAgents });
  } catch (error: any) {
    console.error('[AGENTS API] Error:', error);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
