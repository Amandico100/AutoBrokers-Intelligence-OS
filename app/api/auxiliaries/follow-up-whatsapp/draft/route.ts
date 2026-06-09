import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/auxiliaries/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * POST /api/auxiliaries/follow-up-whatsapp/draft
 * Autentica, resolve company_id no servidor (anti-IDOR) e delega a geração do rascunho ao backend.
 * Body: { conversation_id?: string; objective?: string }. NÃO envia mensagem.
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ success: false, error: 'Não autorizado' }, { status: 401 });

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    console.error('[AUXILIARIES follow-up draft] internal key not configured');
    return NextResponse.json(
      { success: false, error: 'Chave interna do backend não configurada.' },
      { status: 500 },
    );
  }

  let body: { conversation_id?: unknown; objective?: unknown } = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const conversationId =
    typeof body?.conversation_id === 'string' && body.conversation_id.trim()
      ? body.conversation_id.trim()
      : null;
  const objective = typeof body?.objective === 'string' ? body.objective.trim().slice(0, 500) : '';

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json({ success: false, error: 'Backend de IA não configurado.' }, { status: 500 });
    }
    throw error;
  }

  try {
    const response = await fetch(`${backendUrl}/api/auxiliaries/follow-up-whatsapp/draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: ctx.companyId,
        user_id: ctx.userId,
        conversation_id: conversationId,
        objective,
      }),
    });

    const data = await response.json().catch(() => ({}));

    if (
      response.status === 402 ||
      data?.detail === 'insufficient_credits' ||
      data?.error === 'insufficient_credits'
    ) {
      return NextResponse.json(
        {
          success: false,
          error: 'insufficient_credits',
          message: 'Sua corretora não possui créditos suficientes para executar este auxiliar.',
        },
        { status: 402 },
      );
    }

    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: data?.detail || data?.error || 'Falha ao gerar o rascunho.' },
        { status: response.status },
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    console.error('[AUXILIARIES follow-up draft] proxy error:', error);
    return NextResponse.json(
      { success: false, error: 'Falha ao conectar ao backend de IA.' },
      { status: 500 },
    );
  }
}
