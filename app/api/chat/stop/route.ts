import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseAdmin, resolveSessionCompany } from '@/lib/auxiliaries/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-096 · R8 — PARAR É UM PEDIDO EXPLÍCITO, NÃO UM `abort()` DE BROWSER
 *
 * Fechar a aba não cancela a geração: ela corre numa task do servidor e
 * termina de gravar (é o que garante que a resposta não se perde quando o
 * corretor troca de tela). "Parar" é o único jeito de encerrar de verdade — e
 * ele PRESERVA o parcial, marcado como interrompido.
 */
export async function POST(req: NextRequest) {
  try {
    // 🔴 F1 — a MESMA identidade do turno, pelo MESMO helper.
    //
    // A chave do Stop no backend é `companyId:client_request_id`
    // (`chat.py:471`). Se esta rota dissesse uma corretora e o `/chat/stream`
    // dissesse outra — e diriam, porque `session.companyId` é a empresa
    // primária e `resolveSessionCompany` honra a ATIVA do seletor — o Stop
    // procuraria numa chave que ninguém escreveu: 404 sempre, e o corretor
    // apertaria "Parar" sem parar nada. `companyId` nulo, pior: 422.
    const identidade = await resolveSessionCompany();
    if (!identidade) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const body = await req.json().catch(() => ({}));
    const clientRequestId = (body as any)?.client_request_id;

    if (!clientRequestId) {
      return NextResponse.json(
        { error: 'CLIENT_REQUEST_ID_OBRIGATORIO', message: 'Diga qual envio parar.' },
        { status: 400 },
      );
    }

    // 🔴 R15 — parar é um ato sobre O TURNO DE ALGUÉM.
    //
    // Sem conferir o dono, quem tivesse (ou adivinhasse) um
    // `client_request_id` derrubaria a resposta que OUTRO corretor está lendo,
    // de outra corretora inclusive. E não haveria rastro: um Stop bem-sucedido
    // é indistinguível de um usuário que desistiu.
    //
    // O caminho é o mesmo do resto do produto (S.3): a mensagem leva ao id da
    // conversa, e a conversa diz de quem é. Não achou = 404, a mesma resposta
    // de "esse turno não existe" — quem não é dono não descobre que existe.
    const supabaseAdmin = getSupabaseAdmin();

    const { data: mensagensDoTurno } = await supabaseAdmin
      .from('messages')
      .select('conversation_id')
      .eq('payload->>client_request_id', clientRequestId)
      .limit(10);

    const conversas = Array.from(
      new Set(((mensagensDoTurno as any[]) || []).map((m) => m.conversation_id).filter(Boolean)),
    );

    let ehDono = false;
    if (conversas.length > 0) {
      const { data: minha } = await supabaseAdmin
        .from('conversations')
        .select('id')
        .in('id', conversas)
        .eq('user_id', identidade.userId)
        .limit(1)
        .maybeSingle();
      ehDono = Boolean((minha as any)?.id);
    }

    if (!ehDono) {
      return NextResponse.json({ error: 'Turno não encontrado' }, { status: 404 });
    }

    let backendUrl: string;
    try {
      backendUrl = getBackendUrl(req);
    } catch (error) {
      if (error instanceof BackendUrlError) {
        return NextResponse.json({ error: error.code }, { status: 500 });
      }
      throw error;
    }

    const chaveInterna =
      process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';

    const resposta = await fetch(`${backendUrl}/chat/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Key': chaveInterna,
      },
      body: JSON.stringify({
        client_request_id: clientRequestId,
        userId: identidade.userId,
        companyId: identidade.companyId,
      }),
    });

    // 404 aqui não é falha da tela: o browser já abortou localmente e o parcial
    // já está gravado. Devolvemos o status do backend sem transformar em erro.
    const dados = await resposta.json().catch(() => ({}));
    return NextResponse.json(dados, { status: resposta.status });
  } catch (error) {
    console.error('[CHAT STOP] Erro:', error);
    return NextResponse.json({ error: 'CHAT_STOP_FAILED' }, { status: 500 });
  }
}
