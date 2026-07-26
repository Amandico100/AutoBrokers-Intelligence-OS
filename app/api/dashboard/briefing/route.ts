// SPEC-059 — Centro de Briefing da corretora.
//
// O `company_id` vem da SESSÃO, nunca da query. É a diferença entre um painel
// e um vazamento: se o browser pudesse escolher a corretora, bastaria trocar
// um parâmetro para ler o briefing de outra.
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
  if (!b) return { ok: false, error: 'Serviço de inteligência não configurado.' };
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      ...init,
      headers: {
        'X-Internal-Key': b.key,
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(init?.headers || {}),
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
  const aba = req.nextUrl.searchParams.get('aba') || 'hoje';

  // Cada seção é uma chamada independente: uma falhar não pode esconder as
  // outras. Um painel que some inteiro por causa de uma seção é pior do que
  // um painel com uma seção vazia e um aviso.
  if (aba === 'hoje') {
    const [briefing, findings, recomendacoes] = await Promise.all([
      chamar(`/api/intelligence/briefing/current?company_id=${empresa}&tipo=daily_operational`),
      chamar(`/api/intelligence/findings?company_id=${empresa}&limite=30`),
      chamar(`/api/intelligence/recommendations?company_id=${empresa}&limite=20`),
    ]);
    return NextResponse.json({ ok: true, briefing, findings, recomendacoes });
  }

  if (aba === 'semana') {
    const briefing = await chamar(
      `/api/intelligence/briefing/current?company_id=${empresa}&tipo=weekly_executive`,
    );
    return NextResponse.json({ ok: true, briefing });
  }

  if (aba === 'oportunidades') {
    const recomendacoes = await chamar(
      `/api/intelligence/recommendations?company_id=${empresa}&limite=30`,
    );
    return NextResponse.json({ ok: true, recomendacoes });
  }

  if (aba === 'historico') {
    const [briefings, outcomes] = await Promise.all([
      chamar(`/api/intelligence/briefings?company_id=${empresa}&limite=30`),
      chamar(`/api/intelligence/outcomes?company_id=${empresa}&dias=60`),
    ]);
    return NextResponse.json({ ok: true, briefings, outcomes });
  }

  if (aba === 'preferencias') {
    const perfil = await chamar(`/api/intelligence/preferences?company_id=${empresa}`);
    return NextResponse.json({ ok: true, perfil });
  }

  return NextResponse.json({ ok: false, error: 'aba desconhecida' }, { status: 400 });
}

export async function POST(req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const acao = String(corpo?.acao || '');
  const empresa = auth.ctx.companyId;

  if (acao === 'gerar') {
    const tipo = corpo?.tipo === 'semana' ? 'weekly_executive' : 'daily_operational';
    const r = await chamar(
      `/api/intelligence/briefings/generate?company_id=${encodeURIComponent(empresa)}&tipo=${tipo}`,
      { method: 'POST' },
    );
    return NextResponse.json(r);
  }

  if (acao === 'responder_recomendacao') {
    const r = await chamar(
      `/api/intelligence/recommendations/${encodeURIComponent(String(corpo.id))}/respond`,
      {
        method: 'POST',
        body: JSON.stringify({
          company_id: empresa,
          acao: String(corpo.resposta || 'acknowledge'),
          user_id: auth.ctx.userId,
          comentario: corpo.comentario ?? null,
          dias: Number(corpo.dias || 1),
        }),
      },
    );
    return NextResponse.json(r);
  }

  if (acao === 'responder_finding') {
    const r = await chamar(
      `/api/intelligence/findings/${encodeURIComponent(String(corpo.id))}/respond`,
      {
        method: 'POST',
        body: JSON.stringify({
          company_id: empresa,
          acao: String(corpo.resposta || 'acknowledge'),
          user_id: auth.ctx.userId,
          dias: Number(corpo.dias || 1),
        }),
      },
    );
    return NextResponse.json(r);
  }

  if (acao === 'preferencias') {
    // Escrita de preferência exige quem pode configurar a corretora.
    const escrita = await requireCompanyMember({ write: true });
    if (!escrita.ok) {
      return NextResponse.json({ ok: false, error: escrita.error }, { status: escrita.status });
    }
    const r = await chamar('/api/intelligence/preferences', {
      method: 'PUT',
      body: JSON.stringify({
        company_id: empresa,
        cadencia: String(corpo.cadencia || 'daily'),
        campos: corpo.campos || {},
      }),
    });
    return NextResponse.json(r);
  }

  return NextResponse.json({ ok: false, error: 'ação desconhecida' }, { status: 400 });
}
