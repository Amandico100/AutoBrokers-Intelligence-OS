import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin } from '@/lib/admin/admin-auth';
import { getBackendUrl } from '@/lib/backend-url';

import { UUID, cabecalhosDoBackend, repassar, sessaoDaCorretora } from '../../comum';
import { corpoDasRespostas } from '../../respostas';

export const dynamic = 'force-dynamic';

/**
 * SPEC-129-D · conserto K2 — POST /api/renovacoes/<id>/respostas-de-vida
 *   {fumante?, renda_mensal?, esporte_radical?, profissao_texto?} → {estado, frase}
 * As respostas do CLIENTE a uma renovação de vida pendente (o comercial digita). `company_id`/`user_id` da SESSÃO.
 * ⛔ Nada é enviado a ninguém e nenhum cálculo começa aqui: a próxima madrugada calcula.
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ error: 'Renovação inválida' }, { status: 400 });
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const corpo = await req.json().catch(() => ({}));
  try {
    const res = await fetch(`${getBackendUrl()}/api/renovacoes/${encodeURIComponent(id)}/respostas-de-vida`, {
      method: 'POST',
      headers: cabecalhosDoBackend(),
      cache: 'no-store',
      body: JSON.stringify(corpoDasRespostas(corpo, s)),
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
