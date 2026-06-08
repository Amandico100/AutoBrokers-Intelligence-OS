import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/auxiliaries/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * POST /api/auxiliaries/resumo-atendimentos/run
 * Autentica, resolve company_id no servidor (anti-IDOR) e delega a execução LLM ao backend FastAPI.
 * Body: { conversation_id?: string }
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) {
    return NextResponse.json({ success: false, error: 'Não autorizado' }, { status: 401 });
  }

  let body: { conversation_id?: unknown } = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const conversationId =
    typeof body?.conversation_id === 'string' && body.conversation_id.trim()
      ? body.conversation_id.trim()
      : null;

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json(
        { success: false, error: 'Backend de IA não configurado.' },
        { status: 500 },
      );
    }
    throw error;
  }

  try {
    const response = await fetch(`${backendUrl}/api/auxiliaries/resumo-atendimentos/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        // company_id derivado da sessão no servidor — NUNCA do client
        company_id: ctx.companyId,
        user_id: ctx.userId,
        conversation_id: conversationId,
      }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: data?.detail || data?.error || 'Falha na execução do Auxiliar.' },
        { status: response.status },
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    console.error('[AUXILIARIES resumo run] proxy error:', error);
    return NextResponse.json(
      { success: false, error: 'Falha ao conectar ao backend de IA.' },
      { status: 500 },
    );
  }
}
