// SPEC-058 — painel da Factory no Portal Admin.
//
// Rota de PLATAFORMA: o catálogo, as instalações e as oportunidades são visão
// de quem opera o produto, não de uma corretora. Por isso exige master admin,
// e nenhum parâmetro de tenant vem do cliente.
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

function backend(): { url: string; key: string } | null {
  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) return null;
  return { url, key };
}

async function buscar(caminho: string) {
  const b = backend();
  if (!b) return { ok: false, error: 'Serviço da Factory não configurado.' };
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      headers: { 'X-Internal-Key': b.key },
      cache: 'no-store',
    });
    return await r.json();
  } catch {
    return { ok: false, error: 'Não foi possível falar com o serviço.' };
  }
}

export async function GET(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const aba = req.nextUrl.searchParams.get('aba') || 'oportunidades';

  // As três chamadas são independentes: uma falhar não pode esconder as outras.
  // Um painel que some inteiro porque uma seção falhou é pior que um painel
  // com uma seção vazia e um aviso.
  if (aba === 'tudo') {
    const [oportunidades, catalogo, instalacoes] = await Promise.all([
      buscar('/api/factory/oportunidades'),
      buscar('/api/factory/catalogo'),
      buscar('/api/factory/instalacoes'),
    ]);
    return NextResponse.json({ ok: true, oportunidades, catalogo, instalacoes });
  }

  const rotas: Record<string, string> = {
    oportunidades: '/api/factory/oportunidades',
    catalogo: '/api/factory/catalogo',
    instalacoes: '/api/factory/instalacoes',
  };
  const caminho = rotas[aba];
  if (!caminho) return NextResponse.json({ ok: false, error: 'aba desconhecida' }, { status: 400 });

  return NextResponse.json(await buscar(caminho));
}
