import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * GET /api/vault/whatsapp/health
 * Diagnóstico Web→Backend para o Secret Flow. Sem segredo: mostra apenas reachability,
 * status HTTP, host do backend e o corpo (ou um trecho, se não-JSON).
 */
export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ reachable: false, error: 'Não autorizado' }, { status: 401 });

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    return NextResponse.json({ reachable: false, error: 'Chave interna não configurada (ADMIN_API_KEY).' }, { status: 500 });
  }

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json({ reachable: false, error: 'Backend não configurado.' }, { status: 500 });
    }
    throw error;
  }

  let host = '';
  try {
    host = new URL(backendUrl).host;
  } catch {
    host = backendUrl;
  }

  try {
    const res = await fetch(`${backendUrl}/api/whatsapp-integrations/health`, {
      headers: { 'X-AutoBrokers-Internal-Key': internalKey },
    });
    const raw = await res.text();
    let body: unknown;
    try {
      body = raw ? JSON.parse(raw) : {};
    } catch {
      body = raw.slice(0, 200);
    }
    return NextResponse.json({ reachable: res.ok, status: res.status, backend_host: host, body });
  } catch (error) {
    return NextResponse.json({
      reachable: false,
      backend_host: host,
      error: error instanceof Error ? error.message : 'erro desconhecido',
    });
  }
}
