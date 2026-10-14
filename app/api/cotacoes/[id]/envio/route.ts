import { NextRequest } from 'next/server';

import { acao } from '../../comum';

export const dynamic = 'force-dynamic';

/**
 * SPEC-132-B · B3 — POST /api/cotacoes/<id>/envio  {via?: 'copiar'} → {wa_me_url, texto} | {texto, sem_telefone}.
 * ⛔ O produto NÃO envia: devolve o `wa.me` que o navegador de quem clicou abre no WhatsApp DO APARELHO dele (D-132B-05).
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return acao(req, id, 'envio');
}
