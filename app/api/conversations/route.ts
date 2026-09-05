import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, SessionData } from '@/lib/iron-session';

export const dynamic = 'force-dynamic';

/** Quantas mensagens a conversa abre mostrando (SPEC-096 R10/D.1). */
const PAGINA_DE_MENSAGENS = 60;

/**
 * POST /api/conversations
 *
 * Creates a new conversation for the authenticated user.
 * Requires: smith_user_session cookie
 */
export async function POST(request: NextRequest) {
  try {
    // =============================================
    // AUTHENTICATION CHECK (USER SESSION)
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
    // VALIDATE INPUT
    // =============================================
    const body = await request.json();
    const { title, session_id, agent_id } = body;

    // =============================================
    // GET USER'S COMPANY
    // =============================================
    const { data: userData, error: userError } = await supabaseAdmin
      .from('users_v2')
      .select('company_id')
      .eq('id', userId)
      .single();

    if (userError || !userData?.company_id) {
      return NextResponse.json({ error: 'Empresa do usuário não encontrada' }, { status: 400 });
    }

    // =============================================
    // CREATE CONVERSATION
    // =============================================
    const { data, error } = await supabaseAdmin
      .from('conversations')
      .insert({
        user_id: userId,
        company_id: userData.company_id,
        agent_id: agent_id || null,
        session_id: session_id || null,
        title: title || 'Nova Conversa',
        status: 'active',
      })
      .select()
      .single();

    if (error) {
      console.error('[CONVERSATIONS API] Error creating conversation:', error);
      return NextResponse.json({ error: 'Erro ao criar conversa' }, { status: 500 });
    }

    return NextResponse.json({ conversation: data }, { status: 201 });
  } catch (error: any) {
    console.error('[CONVERSATIONS API] Error:', error);
    return NextResponse.json({ error: 'Erro interno ao criar conversa' }, { status: 500 });
  }
}

/**
 * GET /api/conversations
 *
 * Gets all conversations for the authenticated user.
 * Requires: smith_user_session cookie
 */
export async function GET(request: NextRequest) {
  try {
    // =============================================
    // AUTHENTICATION CHECK (USER SESSION)
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
    // GET QUERY PARAMS
    // =============================================
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get('session_id');

    // =============================================
    // FETCH CONVERSATIONS
    // =============================================
    if (sessionId) {
      // 🔴 SPEC-096 D.1 — a conversa abre com as ÚLTIMAS 60, não inteira.
      //
      // 📊 Medido em 04/09/2026 (`conversations/route.ts:139-146`): esta
      // consulta trazia TODAS as mensagens da conversa, sem limite. A mediana
      // é pequena, mas o p95 é 129 e a maior tem 1.326 — e é justamente o
      // corretor que mais usa o produto que paga o pior tempo de abertura.
      //
      // A conversa é UMA (`session_id` + `user_id`): `limit(1)` diz isso à
      // consulta em vez de deixar o banco varrer.
      const { data: conversation, error } = await supabaseAdmin
        .from('conversations')
        .select('id, agent_id, session_id, status, title, created_at, updated_at')
        .eq('session_id', sessionId)
        .eq('user_id', userId)
        .limit(1)
        .maybeSingle();

      if (error) {
        console.error('[CONVERSATIONS API] Error fetching conversation:', error);
        return NextResponse.json({ error: 'Erro ao buscar conversa' }, { status: 500 });
      }

      if (!conversation) {
        return NextResponse.json({
          conversation: null,
          messages: [],
          has_more: false,
          cursor: null,
        });
      }

      // `order desc limit 61` → uma a mais que a página: é assim que se sabe
      // se existe "carregar anteriores" sem uma segunda consulta de contagem.
      const { data: messages, error: messagesError } = await supabaseAdmin
        .from('messages')
        .select('*')
        .eq('conversation_id', conversation.id)
        .order('created_at', { ascending: false })
        .order('id', { ascending: false }) // 📊 05/09: o cursor é (created_at, id); a página tem de ser ordenada pelas duas
        .limit(PAGINA_DE_MENSAGENS + 1);

      if (messagesError) {
        console.error('[CONVERSATIONS API] Error fetching messages:', messagesError);
      }

      const descendentes = (messages as any[]) || [];
      const temMais = descendentes.length > PAGINA_DE_MENSAGENS;
      const pagina = temMais ? descendentes.slice(0, PAGINA_DE_MENSAGENS) : descendentes;
      // A tela lê do mais antigo para o mais novo.
      const emOrdem = [...pagina].reverse();

      return NextResponse.json({
        conversation,
        messages: emOrdem,
        has_more: temMais,
        // O cursor é a mais ANTIGA já entregue: é dela que parte o `before=`.
        // 🔴 F4/R10 — vai o PAR (created_at, id): duas mensagens do mesmo
        // instante empatam, e um cursor só de relógio decide o empate na
        // sorte — some ou repete uma mensagem, sem ninguém perceber.
        cursor: emOrdem.length > 0 ? `${emOrdem[0].created_at}|${emOrdem[0].id}` : null,
      });
    }

    // Get limit from query params (default 50)
    const limitParam = searchParams.get('limit');
    const limit = limitParam ? parseInt(limitParam, 10) : 50;
    const includeCounts = searchParams.get('include_counts') === 'true';

    // Fetch all conversations for user with agent info
    const { data, error } = await supabaseAdmin
      .from('conversations')
      .select('*, agents(name)')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('[CONVERSATIONS API] Error fetching conversations:', error);
      return NextResponse.json({ error: 'Erro ao buscar conversas' }, { status: 500 });
    }

    // Add message counts if requested
    let conversationsWithCounts = data || [];
    if (includeCounts && data) {
      conversationsWithCounts = await Promise.all(
        data.map(async (conv) => {
          const { count } = await supabaseAdmin
            .from('messages')
            .select('*', { count: 'exact', head: true })
            .eq('conversation_id', conv.id);
          return { ...conv, message_count: count || 0 };
        }),
      );
    }

    return NextResponse.json({ conversations: conversationsWithCounts });
  } catch (error: any) {
    console.error('[CONVERSATIONS API] Error:', error);
    return NextResponse.json({ error: 'Erro interno ao buscar conversas' }, { status: 500 });
  }
}
