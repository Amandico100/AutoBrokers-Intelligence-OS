// SPEC-133-A F4 — a ponte Next → backend do canal de WhatsApp, num lugar só.
//
// Estas três funções moravam DENTRO de `app/api/dashboard/whatsapp-channel/route.ts`
// (o hub das corretoras). A SPEC-133-A precisou do MESMO caminho para o QR do
// Quem Cobra Menos no portal admin (`app/api/admin/canais/whatsapp/route.ts`).
// Copiá-las faria duas pontes que envelhecem separadas (CLAUDE.md §5: consolidar
// antes de duplicar) — então elas saíram da rota, sem mudar um caractere do que
// fazem, e as duas rotas importam daqui.
//
// ⛔ Não é um cliente do Evolution: quem fala com o provedor é o backend
// (`backend/app/api/whatsapp_channel.py` → `pairing_orchestrator.py`). Isto só
// carimba a chave interna e repassa.
//
// Server-only: NÃO importar em componente client (a chave interna mora aqui).
import { NextRequest, NextResponse } from 'next/server';

import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const BACKEND_TIMEOUT_MS = 20_000;

export function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

export function correlationId(req: NextRequest): string {
  return req.headers.get('X-Correlation-ID') || crypto.randomUUID();
}

export async function backendRequest(
  path: string,
  key: string,
  correlation: string,
  init: RequestInit = {},
): Promise<NextResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);
  try {
    const backend = getBackendUrl();
    const res = await fetch(`${backend}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-AutoBrokers-Internal-Key': key,
        'X-Correlation-ID': correlation,
        ...(init.headers || {}),
      },
      cache: 'no-store',
      signal: controller.signal,
    });
    const json = await res.json().catch(() => ({ detail: `backend_http_${res.status}` }));
    return NextResponse.json(json, {
      status: res.status,
      headers: { 'X-Correlation-ID': correlation },
    });
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json(
        { detail: 'backend_not_configured', correlation_id: correlation },
        { status: 500, headers: { 'X-Correlation-ID': correlation } },
      );
    }
    if ((error as { name?: string })?.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'backend_timed_out', correlation_id: correlation },
        { status: 504, headers: { 'X-Correlation-ID': correlation } },
      );
    }
    return NextResponse.json(
      { detail: 'backend_unavailable', correlation_id: correlation },
      { status: 502, headers: { 'X-Correlation-ID': correlation } },
    );
  } finally {
    clearTimeout(timer);
  }
}
