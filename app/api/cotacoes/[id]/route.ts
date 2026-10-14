import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';

import { UUID, cabecalhosDoBackend, repassar, sessaoDaCorretora } from '../comum';

export const dynamic = 'force-dynamic';

/** SPEC-132-B · B3 — GET /api/cotacoes/<id>: o detalhe (as opções, em qual Agger saiu, "Abrir no Agger"). */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ error: 'Cotação inválida' }, { status: 400 });
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const p = new URLSearchParams({ company_id: s.companyId, user_id: s.userId });
  try {
    const res = await fetch(`${getBackendUrl()}/api/cotacoes/${encodeURIComponent(id)}?${p.toString()}`, {
      headers: cabecalhosDoBackend(),
      cache: 'no-store',
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
