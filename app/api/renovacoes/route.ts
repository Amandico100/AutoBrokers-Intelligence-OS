import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';

import { cabecalhosDoBackend, repassar, sessaoDaCorretora } from './comum';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-B · G2 — GET /api/renovacoes?escopo=minhas|todas&estado=&ramo=&de=&ate=&seguradora=&q=
 *
 * As renovações da corretora DA SESSÃO, na forma da aba Renovações. Sem `escopo`, o padrão é pelo papel: quem
 * administra a corretora vê "todas"; o comercial vê as "minhas" (dono ou responsável = eu).
 */
const FILTROS = ['estado', 'ramo', 'de', 'ate', 'seguradora', 'q'] as const;

export async function GET(req: NextRequest) {
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const entrada = req.nextUrl.searchParams;
  const pedido = entrada.get('escopo');
  const escopo = pedido === 'minhas' || pedido === 'todas' ? pedido : s.admin ? 'todas' : 'minhas';
  const p = new URLSearchParams({ company_id: s.companyId, user_id: s.userId, escopo });
  for (const k of FILTROS) {
    const v = (entrada.get(k) || '').trim();
    if (v) p.set(k, v.slice(0, 120));
  }
  try {
    const res = await fetch(`${getBackendUrl()}/api/renovacoes?${p.toString()}`, {
      headers: cabecalhosDoBackend(),
      cache: 'no-store',
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
