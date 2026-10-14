import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';

import { cabecalhosDoBackend, repassar, sessaoDaCorretora } from './comum';
import { CABECALHO_DA_BUSCA, pedidoDaLista } from './pedido';

export const dynamic = 'force-dynamic';

/**
 * SPEC-132-B · B3 — GET /api/cotacoes?escopo=minhas|todas&estado=calculando|pronta|sem_resposta
 *
 * As cotações da corretora DA SESSÃO (os últimos 90 dias), na forma da aba Cotações. Sem `escopo`, o padrão é pelo
 * papel: quem administra vê "todas"; o comercial vê as "minhas" (as que ele pediu).
 *
 * 🔴 A busca ("Nome, placa ou CPF") NÃO vem na query: chega no cabeçalho `x-cotacoes-busca` e vai ao backend no
 * cabeçalho `x-busca`. `q` na query é ignorado. Ver `pedido.ts`.
 */
export async function GET(req: NextRequest) {
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const { consulta, cabecalhos } = pedidoDaLista(req.nextUrl.searchParams, req.headers.get(CABECALHO_DA_BUSCA), s);
  try {
    const res = await fetch(`${getBackendUrl()}/api/cotacoes?${consulta}`, {
      headers: { ...cabecalhosDoBackend(), ...cabecalhos },
      cache: 'no-store',
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
