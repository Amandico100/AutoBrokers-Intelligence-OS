import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';

import { UUID, cabecalhosDoBackend, repassar, sessaoDaCorretora } from '../comum';

export const dynamic = 'force-dynamic';

/** SPEC-131-B · G2 — GET /api/renovacoes/<id>: o detalhe (cálculos, linha do tempo, próximo passo, "Abrir no Agger"). */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ error: 'Renovação inválida' }, { status: 400 });
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const p = new URLSearchParams({ company_id: s.companyId, user_id: s.userId });
  try {
    const res = await fetch(`${getBackendUrl()}/api/renovacoes/${encodeURIComponent(id)}?${p.toString()}`, {
      headers: cabecalhosDoBackend(),
      cache: 'no-store',
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
