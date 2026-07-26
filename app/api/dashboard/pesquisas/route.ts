// SPEC-060 §30 — Biblioteca de pesquisas da corretora.
//
// `company_id` vem da SESSÃO, nunca da query: se o browser pudesse escolher a
// corretora, bastaria trocar um parâmetro para ler a pesquisa de outra.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';

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

async function chamar(caminho: string, init?: RequestInit) {
  const b = backend();
  if (!b) return { ok: false, error: 'Serviço de pesquisa não configurado.' };
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      ...init,
      headers: {
        'X-Internal-Key': b.key,
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      },
      cache: 'no-store',
    });
    return await r.json();
  } catch {
    return { ok: false, error: 'Não foi possível falar com o serviço.' };
  }
}

export async function GET(req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const empresa = encodeURIComponent(auth.ctx.companyId);
  const aba = req.nextUrl.searchParams.get('aba') || 'recentes';
  const id = req.nextUrl.searchParams.get('id');

  if (id) {
    const [detalhe, fontes] = await Promise.all([
      chamar(`/api/research/${encodeURIComponent(id)}?company_id=${empresa}`),
      chamar(`/api/research/${encodeURIComponent(id)}/sources?company_id=${empresa}`),
    ]);
    return NextResponse.json({ ok: true, detalhe, fontes });
  }

  if (aba === 'monitores') {
    return NextResponse.json(await chamar(`/api/research/monitors?company_id=${empresa}`));
  }

  return NextResponse.json(await chamar(`/api/research?company_id=${empresa}&limite=30`));
}

export async function POST(req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const acao = String(corpo?.acao || '');
  const empresa = auth.ctx.companyId;

  if (acao === 'pesquisar') {
    return NextResponse.json(
      await chamar('/api/research', {
        method: 'POST',
        body: JSON.stringify({
          company_id: empresa,
          pergunta: String(corpo.pergunta || ''),
          modo: corpo.modo || null,
          user_id: auth.ctx.userId,
          origem: 'user',
        }),
      }),
    );
  }

  if (acao === 'monitor_agora') {
    return NextResponse.json(
      await chamar(
        `/api/research/monitors/${encodeURIComponent(String(corpo.id))}/run?company_id=${encodeURIComponent(empresa)}`,
        { method: 'POST' },
      ),
    );
  }

  if (acao === 'monitor_pausar') {
    return NextResponse.json(
      await chamar(`/api/research/monitors/${encodeURIComponent(String(corpo.id))}`, {
        method: 'PATCH',
        body: JSON.stringify({ company_id: empresa, ativo: Boolean(corpo.ativo) }),
      }),
    );
  }

  return NextResponse.json({ ok: false, error: 'ação desconhecida' }, { status: 400 });
}
