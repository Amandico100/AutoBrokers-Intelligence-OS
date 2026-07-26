// SPEC-059 §26 — Central de Inteligência no Portal Admin.
//
// Rota de PLATAFORMA: sinais, regras, qualidade e demanda agregada são visão
// de quem opera o produto. Exige master admin, e nenhum `company_id` vem do
// cliente sem passar por filtro explícito.
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

async function chamar(caminho: string, init?: RequestInit) {
  const b = backend();
  if (!b) return { ok: false, error: 'Serviço de inteligência não configurado.' };
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
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const aba = req.nextUrl.searchParams.get('aba') || 'visao';
  const empresa = req.nextUrl.searchParams.get('company_id');
  const filtro = empresa ? `&company_id=${encodeURIComponent(empresa)}` : '';

  if (aba === 'visao') {
    const [overview, memoria] = await Promise.all([
      chamar('/api/admin/intelligence/overview?dias=7'),
      chamar('/api/admin/intelligence/memory-health'),
    ]);
    return NextResponse.json({ ok: true, overview, memoria });
  }
  if (aba === 'sinais') {
    return NextResponse.json(await chamar(`/api/admin/intelligence/signals?limite=100${filtro}`));
  }
  if (aba === 'findings') {
    const [findings, briefings] = await Promise.all([
      chamar(`/api/admin/intelligence/findings?limite=100${filtro}`),
      chamar(`/api/admin/intelligence/briefings?limite=40${filtro}`),
    ]);
    return NextResponse.json({ ok: true, findings, briefings });
  }
  if (aba === 'demanda') {
    const [clusters, candidatos] = await Promise.all([
      chamar('/api/admin/intelligence/demand-clusters?limite=60'),
      chamar('/api/admin/intelligence/knowledge-candidates?limite=40'),
    ]);
    return NextResponse.json({ ok: true, clusters, candidatos });
  }
  if (aba === 'regras') {
    const [regras, qualidade] = await Promise.all([
      chamar('/api/admin/intelligence/rules'),
      chamar('/api/admin/intelligence/quality?dias=30'),
    ]);
    return NextResponse.json({ ok: true, regras, qualidade });
  }
  return NextResponse.json({ ok: false, error: 'aba desconhecida' }, { status: 400 });
}

export async function POST(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const acao = String(corpo?.acao || '');

  if (acao === 'regra') {
    return NextResponse.json(
      await chamar(`/api/admin/intelligence/rules/${encodeURIComponent(String(corpo.rule_key))}`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: corpo.status ?? null,
          configuracao: corpo.configuracao ?? null,
          ator: auth.ctx.adminId,
        }),
      }),
    );
  }

  if (acao === 'replay') {
    return NextResponse.json(
      await chamar('/api/admin/intelligence/replay', {
        method: 'POST',
        body: JSON.stringify({
          company_id: String(corpo.company_id || ''),
          rule_keys: corpo.rule_keys ?? null,
        }),
      }),
    );
  }

  if (acao === 'cluster') {
    return NextResponse.json(
      await chamar(
        `/api/admin/intelligence/demand-clusters/${encodeURIComponent(String(corpo.id))}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            status: corpo.status ?? null,
            nota: corpo.nota ?? null,
            outcome: corpo.outcome ?? null,
            ator: auth.ctx.adminId,
          }),
        },
      ),
    );
  }

  if (acao === 'fundir') {
    return NextResponse.json(
      await chamar('/api/admin/intelligence/demand-clusters/merge', {
        method: 'POST',
        body: JSON.stringify({
          origem_id: String(corpo.origem_id),
          destino_id: String(corpo.destino_id),
          ator: auth.ctx.adminId,
        }),
      }),
    );
  }

  return NextResponse.json({ ok: false, error: 'ação desconhecida' }, { status: 400 });
}
