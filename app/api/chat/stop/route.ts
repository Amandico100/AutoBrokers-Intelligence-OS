import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { sessionOptions, SessionData } from '@/lib/iron-session';
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
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);

    if (!session?.userId) {
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
        userId: session.userId,
        companyId: session.companyId ?? null,
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
