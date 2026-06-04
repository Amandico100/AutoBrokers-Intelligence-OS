import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * POST /api/chat
 *
 * Proxy simples para o backend Python (/chat).
 * Usado pelo Widget embeddable que espera resposta JSON completa.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

    // Timeout de 90s — LLMs podem demorar, mas não devem travar infinitamente
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90_000);

    let response: Response;
    try {
      response = await fetch(`${backendUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (fetchError: any) {
      clearTimeout(timeout);
      // AbortError = timeout disparou
      if (fetchError.name === 'AbortError') {
        console.error('❌ [API CHAT] Timeout de 90s atingido');
        return NextResponse.json(
          { error: 'O serviço de IA demorou demais para responder. Tente novamente.' },
          { status: 504 },
        );
      }
      throw fetchError; // re-throw para cair no catch externo
    }

    clearTimeout(timeout);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Erro no processamento da IA' },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('❌ [API CHAT] Erro no proxy:', error);
    return NextResponse.json(
      { error: 'Falha interna ao conectar com o serviço de IA' },
      { status: 500 },
    );
  }
}
