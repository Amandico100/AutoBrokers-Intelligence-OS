import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';
import { canWriteTenantConfig } from '@/lib/admin/admin-auth-policy';
import { getBackendUrl } from '@/lib/backend-url';

/**
 * SPEC-131-B · G2 — o que as rotas de `/api/renovacoes` têm em comum.
 *
 * 🔴 `company_id` e `user_id` vêm SEMPRE da sessão (`requireCompanyMember`: o vínculo ATIVO com a corretora, a mesma
 * régua das outras telas) — nunca do navegador. O backend é interno (chave Next↔backend) e filtra de novo.
 * ⛔ Nenhuma destas rotas envia nada ao cliente: o envio devolve um `wa.me` que o navegador de quem clicou abre.
 */
export type Sessao = { companyId: string; userId: string; admin: boolean };

export function cabecalhosDoBackend(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function sessaoDaCorretora(): Promise<Sessao | NextResponse> {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: 'Não autorizado' }, { status: auth.status });
  return {
    companyId: auth.ctx.companyId,
    userId: auth.ctx.userId,
    admin: canWriteTenantConfig({ role: auth.ctx.role, isOwner: auth.ctx.isOwner }),
  };
}

/** As duas ações (POST): mesma origem + sessão. O corpo do navegador é IGNORADO — só `via` passa adiante. */
export async function acao(req: NextRequest, id: string, caminho: 'apresentacao' | 'envio') {
  if (!UUID.test(id)) return NextResponse.json({ error: 'Renovação inválida' }, { status: 400 });
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const s = await sessaoDaCorretora();
  if (s instanceof NextResponse) return s;
  const corpo = await req.json().catch(() => ({}));
  const via = caminho === 'envio' && corpo?.via === 'copiar' ? 'copiar' : undefined;
  try {
    const res = await fetch(`${getBackendUrl()}/api/renovacoes/${encodeURIComponent(id)}/${caminho}`, {
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

export async function repassar(res: Response) {
  const j = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detalhe = typeof j?.detail === 'string' ? j.detail : null;
    return NextResponse.json({ error: detalhe || 'Não deu certo agora. Tente de novo.' }, { status: res.status });
  }
  return NextResponse.json(j, { status: res.status, headers: { 'Cache-Control': 'no-store' } });
}
