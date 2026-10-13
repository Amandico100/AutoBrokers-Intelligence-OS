import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';

import { cabecalhosDoBackend, repassar, sessaoDaCorretora } from './comum';
import { CABECALHO_DA_BUSCA, pedidoDaLista } from './pedido';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-B · G2 — GET /api/renovacoes?escopo=minhas|todas&estado=&ramo=&de=&ate=&seguradora=
 *
 * As renovações da corretora DA SESSÃO, na forma da aba Renovações. Sem `escopo`, o padrão é pelo papel: quem
 * administra a corretora vê "todas"; o comercial vê as "minhas" (dono ou responsável = eu).
 *
 * 🔴 A busca ("Nome ou CPF") NÃO vem na query: chega no cabeçalho `x-renovacoes-busca` e vai ao backend no
 * cabeçalho `x-busca` (juiz J-B1 — a query string acaba no log de acesso). `q` na query é ignorado. Ver `pedido.ts`.
 */
export async function GET(req: NextRequest) {
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const { consulta, cabecalhos } = pedidoDaLista(req.nextUrl.searchParams, req.headers.get(CABECALHO_DA_BUSCA), s);
  try {
    const res = await fetch(`${getBackendUrl()}/api/renovacoes?${consulta}`, {
      headers: { ...cabecalhosDoBackend(), ...cabecalhos },
      cache: 'no-store',
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
