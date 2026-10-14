import { NextRequest } from 'next/server';

import { acao } from '../../comum';

export const dynamic = 'force-dynamic';

/** SPEC-132-B · B3 — POST /api/cotacoes/<id>/apresentacao → {url, token}: o link da apresentação de VENDA do cliente. */
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return acao(req, id, 'apresentacao');
}
