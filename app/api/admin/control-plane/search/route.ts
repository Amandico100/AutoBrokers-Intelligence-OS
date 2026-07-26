// SPEC-061 §11.3 — busca global governada.
//
// As permissions vão daqui: a busca só procura no que a pessoa pode ver, e
// devolve DESTINO, nunca conteúdo. Uma busca que devolvesse trecho de conversa
// seria um vazamento com aparência de conveniência.
import { NextRequest, NextResponse } from 'next/server';
import { exigirPermissao } from '@/lib/admin/control-plane/authority';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const auth = await exigirPermissao('admin.overview.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) return NextResponse.json({ ok: true, resultados: [] });

  try {
    const r = await fetch(`${url}/api/admin/control-plane/search`, {
      method: 'POST',
      headers: { 'X-Internal-Key': key, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        termo: req.nextUrl.searchParams.get('q') || '',
        permissions: Array.from(auth.autoridade.permissions),
        pode_tudo: Boolean(auth.autoridade.podeTudo),
      }),
      cache: 'no-store',
    });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ ok: true, resultados: [] });
  }
}
