// SPEC-061 §12 — a Home executiva.
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

  if (!url || !key) {
    // §12.2 — nunca "tudo saudável" quando não se conseguiu ler.
    return NextResponse.json({
      ok: true,
      estado_geral: {
        tom: 'incerto',
        texto:
          'Não consegui falar com o serviço de controle. O que aparece abaixo está incompleto — não é um retrato de tudo.',
      },
      fontes_indisponiveis: ['serviço de controle'],
      precisa_de_decisao: [],
      corretoras_em_risco: [],
      operacao: {},
      numeros: [],
    });
  }

  try {
    const r = await fetch(`${url}/api/admin/control-plane/home`, {
      method: 'POST',
      headers: { 'X-Internal-Key': key, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        permissions: Array.from(auth.autoridade.permissions),
        pode_tudo: Boolean(auth.autoridade.podeTudo),
        dias: Number(req.nextUrl.searchParams.get('dias') || 7),
      }),
      cache: 'no-store',
    });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({
      ok: true,
      estado_geral: {
        tom: 'incerto',
        texto: 'Não consegui consultar agora. Tente atualizar em instantes.',
      },
      fontes_indisponiveis: ['serviço de controle'],
      precisa_de_decisao: [],
      corretoras_em_risco: [],
      operacao: {},
      numeros: [],
    });
  }
}
