import { NextRequest } from 'next/server';

import { acao } from '../../comum';

export const dynamic = 'force-dynamic';

/** SPEC-131-B · G2 — POST /api/renovacoes/<id>/apresentacao → {token, url}: publica a página de RENOVAÇÃO do cliente. */
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return acao(req, id, 'apresentacao');
}
