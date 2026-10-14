import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin } from '@/lib/admin/admin-auth';
import { getBackendUrl } from '@/lib/backend-url';
import { UUID, cabecalhosDoBackend, repassar, sessaoDaCorretora } from '@/app/api/renovacoes/comum';

/**
 * SPEC-132-B · B3 — o que as rotas de `/api/cotacoes` têm em comum. A sessão, a chave interna e o repasse são OS DA
 * aba Renovações (uma régua só: `requireCompanyMember`, o vínculo ATIVO com a corretora).
 *
 * 🔴 `company_id` e `user_id` vêm SEMPRE da sessão — nunca do navegador. O backend é interno e filtra de novo.
 * ⛔ Nenhuma destas rotas envia nada ao cliente: o envio devolve um `wa.me` que o navegador de quem clicou abre.
 */
export { UUID, cabecalhosDoBackend, repassar, sessaoDaCorretora };

/** As duas ações (POST): mesma origem + sessão. O corpo do navegador é IGNORADO — só `via` passa adiante. */
export async function acao(req: NextRequest, id: string, caminho: 'apresentacao' | 'envio') {
  if (!UUID.test(id)) return NextResponse.json({ error: 'Cotação inválida' }, { status: 400 });
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const corpo = await req.json().catch(() => ({}));
  const via = caminho === 'envio' && corpo?.via === 'copiar' ? 'copiar' : undefined;
  try {
    const res = await fetch(`${getBackendUrl()}/api/cotacoes/${encodeURIComponent(id)}/${caminho}`, {
      method: 'POST',
      headers: cabecalhosDoBackend(),
      cache: 'no-store',
      body: JSON.stringify({
        company_id: s.companyId, // da SESSÃO — nunca do cliente
        user_id: s.userId, // da SESSÃO — nunca do cliente
        ...(via ? { via } : {}),
      }),
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
