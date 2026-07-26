// SPEC-061 §9.3 — leitura da trilha administrativa.
//
// Somente leitura: a trilha é append-only por trigger no banco, e não existe
// caminho de escrita partindo da tela. Quem grava é o Command Gateway, como
// efeito de uma ação — nunca alguém "adicionando um evento".
import { NextRequest, NextResponse } from 'next/server';
import { exigirPermissao } from '@/lib/admin/control-plane/authority';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const auth = await exigirPermissao('audit.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) {
    return NextResponse.json({ ok: false, erro: 'Serviço de controle não configurado.' });
  }

  const p = req.nextUrl.searchParams;
  const query = new URLSearchParams({ limite: p.get('limite') || '100' });
  for (const campo of ['company_id', 'actor_user_id', 'risco'] as const) {
    const v = p.get(campo);
    if (v) query.set(campo, v);
  }

  try {
    const r = await fetch(`${url}/api/admin/control-plane/audit?${query}`, {
      headers: { 'X-Internal-Key': key },
      cache: 'no-store',
    });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ ok: false, erro: 'Não foi possível falar com o serviço.' });
  }
}
