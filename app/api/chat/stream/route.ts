import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseAdmin, resolveSessionCompany } from '@/lib/auxiliaries/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

// Força a rota a ser dinâmica para suportar streaming
export const dynamic = 'force-dynamic';

/**
 * SPEC-096 · S.1 + A.2 — O BFF DO TURNO
 *
 * 🔴 O que esta rota deixou de ser (📊 medido em 04/09/2026, `e1494ab`,
 * `stream/route.ts:10-40`): um proxy CEGO. Ela lia `await req.json()` e
 * repassava o corpo inteiro ao backend — `companyId`, `userId` e `agentId`
 * inclusive. Quem tivesse QUALQUER cookie válido escolhia, pelo corpo, de qual
 * corretora sairia o cérebro e para qual iria o crédito. Nada travava; a
 * resposta era 200 (CLAUDE.md §9.5 — o defeito que responde é o silencioso).
 *
 * Agora (R1): a identidade vem da SESSÃO e SÓ dela. O corpo do browser não tem
 * voz sobre quem é quem — `companyId`/`userId`/`agentId` que venham nele são
 * ignorados sem erro, porque um 400 aqui só ensinaria o atacante a tirá-los.
 *
 * E (A.2/R3): a PERGUNTA é gravada pelo SERVIDOR, com `await`, ANTES do fetch
 * ao backend. 📊 §1.3: a gravação era do browser, sem await, em paralelo com o
 * stream — uma falha no meio deixava a pergunta sem registro e a resposta órfã.
 */
export async function POST(req: NextRequest) {
  try {
    // ─────────────────────────────────────────────────────────────────────
    // 1. IDENTIDADE — da sessão, nunca do corpo (R1)
    // ─────────────────────────────────────────────────────────────────────
    // 🔴 F1 — o MESMO helper que o resto do produto usa (`resolveSessionCompany`,
    // `lib/auxiliaries/server.ts:31`). Ele honra a empresa ATIVA do seletor
    // multi-empresa (SPEC-047), validando o vínculo em `company_members` a cada
    // requisição, e só cai em `users_v2.company_id` quando não há escolha.
    //
    // Ler `users_v2.company_id` cru aqui e `session.companyId` no Stop fazia as
    // duas rotas responderem corretoras DIFERENTES para o mesmo corretor — e a
    // chave do Stop no backend é `companyId:client_request_id` (`chat.py:471`):
    // divergiu, o Stop procura numa gaveta que não é a dele e devolve 404.
    const identidade = await resolveSessionCompany();
    if (!identidade) {
      // ⛔ Sem sessão (ou sem empresa) nem se chama o backend: o crédito é de alguém.
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }
    const { userId, companyId } = identidade;

    const body = await req.json();
    const {
      chatInput,
      sessionId,
      client_request_id: clientRequestId,
      imageUrl,
      fileUrl,
      fileName,
      options,
      assistantMessageId,
    } = body || {};

    // ─────────────────────────────────────────────────────────────────────
    // 2. UM TURNO — o id do envio é obrigatório (R3)
    // ─────────────────────────────────────────────────────────────────────
    if (!clientRequestId) {
      return NextResponse.json(
        {
          error: 'CLIENT_REQUEST_ID_OBRIGATORIO',
          message: 'Cada envio precisa de um identificador próprio.',
        },
        { status: 400 },
      );
    }

    const supabaseAdmin = getSupabaseAdmin();

    // ─────────────────────────────────────────────────────────────────────
    // 3. A CONVERSA — por (session_id, user_id); o agente é DELA
    // ─────────────────────────────────────────────────────────────────────
    let conversa: { id: string; agent_id: string | null } | null = null;

    if (sessionId) {
      const { data } = await supabaseAdmin
        .from('conversations')
        .select('id, agent_id')
        .eq('session_id', sessionId)
        .eq('user_id', userId)
        .maybeSingle();
      conversa = (data as any) || null;
    }

    // O agente NUNCA vem do corpo: é o primeiro agente ativo da corretora da
    // sessão (a mesma consulta de /api/agents).
    const primeiroAgenteAtivo = async (): Promise<string | null> => {
      const { data: agente } = await supabaseAdmin
        .from('agents')
        .select('id')
        .eq('company_id', companyId)
        .eq('is_active', true)
        .limit(1)
        .maybeSingle();
      return (agente as any)?.id ?? null;
    };

    if (!conversa) {
      const agenteId = await primeiroAgenteAtivo();

      const { data: nova, error: erroConversa } = await supabaseAdmin
        .from('conversations')
        .insert({
          user_id: userId,
          company_id: companyId,
          agent_id: agenteId,
          session_id: sessionId || null,
          title: typeof chatInput === 'string' ? chatInput.slice(0, 50) : 'Nova Conversa',
          // 📊 F3 — 668 conversas 'open' contra 59 'active': quem escreve a
          // maioria é o backend, e ele escreve 'open'. Duas palavras para o
          // mesmo estado transformam qualquer filtro por status numa meia
          // verdade, então a tela passa a falar a palavra do banco.
          status: 'open',
        })
        .select('id, agent_id')
        .single();

      if (erroConversa || !nova) {
        // 🔴 F3 — `conversations.session_id` é UNIQUE GLOBAL. Se o session_id
        // já existe em OUTRA corretora, o insert bate no índice e um 500 aqui
        // seria um oráculo de existência: quem chutasse session_ids saberia
        // quais existem pela diferença entre 500 e 200. A resposta é a mesma
        // de "essa conversa não é sua": 404.
        if ((erroConversa as any)?.code === '23505') {
          return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 });
        }
        console.error('[CHAT STREAM] Erro ao criar conversa:', erroConversa);
        return NextResponse.json({ error: 'Erro ao criar conversa' }, { status: 500 });
      }
      conversa = nova as any;
    }

    // 🔴 R4 — uma conversa com `agent_id` nulo fica nula PARA SEMPRE.
    //
    // 📊 Quem foi criado num momento em que a corretora ainda não tinha agente
    // ativo (ou por um caminho que não preenchia o campo) nunca mais recebia
    // um: o BFF mandava `agentId: null`, o backend não tinha a quem perguntar,
    // e a conversa respondia vazio para sempre. Resolve-se AGORA — e grava-se,
    // para o turno seguinte não repetir a consulta.
    if (!conversa!.agent_id) {
      const agenteId = await primeiroAgenteAtivo();
      if (agenteId) {
        conversa!.agent_id = agenteId;
        await supabaseAdmin
          .from('conversations')
          .update({ agent_id: agenteId })
          .eq('id', conversa!.id);
      }
      // Sem nenhum agente ativo na corretora, não se inventa um: o backend
      // responde com um `notice` que a tela sabe mostrar (R4).
    }

    // ─────────────────────────────────────────────────────────────────────
    // 4. A PERGUNTA — gravada AQUI, com await, ANTES do fetch (A.2)
    // ─────────────────────────────────────────────────────────────────────
    const conteudo =
      typeof chatInput === 'string' && chatInput.length > 0
        ? chatInput
        : imageUrl
          ? '[Imagem]'
          : '';

    let userMessageId: string | null = null;
    const { data: gravada, error: erroGravacao } = await supabaseAdmin
      .from('messages')
      .insert({
        conversation_id: conversa!.id,
        role: 'user',
        content: conteudo,
        type: 'text',
        image_url: imageUrl || null,
        payload: {
          client_request_id: clientRequestId,
          turn: { submitted_at: new Date().toISOString() },
        },
      })
      .select('id')
      .single();

    if (erroGravacao) {
      // 🔴 R3 — 23505 é o índice único parcial (conversation_id,
      // client_request_id) dizendo "esta pergunta já existe". Isso é uma
      // RETENTATIVA de resposta, não uma segunda pergunta e não um erro:
      // reaproveita a linha e segue.
      if ((erroGravacao as any).code === '23505') {
        const { data: existente } = await supabaseAdmin
          .from('messages')
          .select('id')
          .eq('conversation_id', conversa!.id)
          // 🔴 F2 — o índice único é (conversation_id, role, client_request_id):
          // a PERGUNTA e a RESPOSTA do mesmo turno carregam o mesmo
          // `client_request_id`. Sem o `role`, este SELECT casaria as duas,
          // `maybeSingle()` erraria por linha duplicada e o `user_message_id`
          // sairia null — a resposta nasceria órfã da pergunta.
          .eq('role', 'user')
          .eq('payload->>client_request_id', clientRequestId)
          .maybeSingle();
        userMessageId = (existente as any)?.id ?? null;
      } else {
        console.error('[CHAT STREAM] Erro ao gravar a pergunta:', erroGravacao);
        return NextResponse.json({ error: 'Erro ao gravar a pergunta' }, { status: 500 });
      }
    } else {
      userMessageId = (gravada as any)?.id ?? null;
    }

    // ─────────────────────────────────────────────────────────────────────
    // 5. O BACKEND — modo painel, com X-Internal-Key (S.2)
    // ─────────────────────────────────────────────────────────────────────
    let backendUrl: string;
    try {
      backendUrl = getBackendUrl(req);
    } catch (error) {
      if (error instanceof BackendUrlError) {
        return NextResponse.json(
          {
            error: error.code,
            message: 'Configure NEXT_PUBLIC_API_URL or NEXT_PUBLIC_BACKEND_URL with the public API URL.',
          },
          { status: 500 },
        );
      }
      throw error;
    }

    const chaveInterna =
      process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';

    const response = await fetch(`${backendUrl}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Key': chaveInterna,
      },
      body: JSON.stringify({
        chatInput,
        sessionId,
        companyId,
        userId,
        agentId: conversa!.agent_id || undefined,
        client_request_id: clientRequestId,
        user_message_id: userMessageId,
        assistantMessageId,
        imageUrl,
        fileUrl,
        fileName,
        options,
        channel: 'web',
      }),
      // @ts-ignore - 'duplex' é necessário para streaming em algumas versões do Node
      duplex: 'half',
    });

    if (!response.ok) {
      console.error(`[CHAT STREAM] Erro no backend: ${response.status} ${response.statusText}`);
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        {
          error: errorData.detail || errorData.error || `Backend error: ${response.statusText}`,
          status: response.status,
        },
        { status: response.status },
      );
    }

    if (!response.body) {
      return NextResponse.json({ error: 'No response body' }, { status: 500 });
    }

    // 🔴 `X-Accel-Buffering: no` é repassado AQUI. 📊 §1.6: o proxy montava
    // headers novos e engolia o do backend — atrás de um Nginx que bufferiza,
    // o primeiro token só chega quando a resposta inteira termina, e o chat
    // parece travado até responder de uma vez.
    return new NextResponse(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch (error) {
    console.error('[CHAT STREAM] Erro fatal:', error);
    return NextResponse.json(
      {
        error: 'CHAT_STREAM_PROXY_FAILED',
        message: 'Falha ao conectar o Web ao backend de IA.',
      },
      { status: 500 },
    );
  }
}
