// SPEC-060 §31 — painel de pesquisa no Portal Admin.
//
// Rota de PLATAFORMA: providers, fontes, custos, ruído e segurança são visão
// de quem opera o produto, não de uma corretora.
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
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const aba = req.nextUrl.searchParams.get('aba') || 'visao';

  if (aba === 'visao') {
    const [overview, providers] = await Promise.all([
      chamar('/api/admin/research/overview?dias=30'),
      chamar('/api/admin/research/providers'),
    ]);
    return NextResponse.json({ ok: true, overview, providers });
  }
  if (aba === 'fontes') {
    return NextResponse.json(await chamar('/api/admin/research/sources?limite=120'));
  }
  if (aba === 'monitores') {
    return NextResponse.json(await chamar('/api/admin/research/monitors?limite=100'));
  }
  if (aba === 'custos') {
    const [custos, seguranca] = await Promise.all([
      chamar('/api/admin/research/costs?dias=30'),
      chamar('/api/admin/research/security?dias=30'),
    ]);
    return NextResponse.json({ ok: true, custos, seguranca });
  }
  return NextResponse.json({ ok: false, error: 'aba desconhecida' }, { status: 400 });
}

export async function POST(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  if (String(corpo?.acao || '') === 'semear_fontes') {
    return NextResponse.json(
      await chamar('/api/admin/research/sources/seed', { method: 'POST' }),
    );
  }
  return NextResponse.json({ ok: false, error: 'ação desconhecida' }, { status: 400 });
}
