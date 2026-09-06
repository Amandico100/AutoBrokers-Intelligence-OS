// SPEC-098 · U2.4 — o Jeito de atender da corretora.
//
// Duas ações, uma porta: PROPOR (o sistema lê o site ou as conversas e sugere)
// e USAR (a administradora aprova, e só então o agente passa a falar assim).
//
// 🔴 A separação é a regra R2: o modelo PROPÕE, a corretora PUBLICA. Propor é
// leitura; aprovar muda como o agente fala com o segurado — por isso aprovar
// exige papel administrativo (`write: true`) e mesma origem.
//
// A rota é fina de propósito: autoriza, resolve a corretora e o usuário a
// partir da SESSÃO e repassa. `company_id` e `user_id` nunca vêm do corpo —
// aceitá-los seria deixar qualquer um mudar a voz de qualquer corretora.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';

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

async function chamar(
  caminho: string,
  corpo: Record<string, unknown>,
  timeoutMs: number,
): Promise<{ status: number; body: any }> {
  const b = backend();
  if (!b) {
    return {
      status: 503,
      body: { ok: false, error: 'Serviço de identidade não configurado.' },
    };
  }

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', 'X-Internal-Key': b.key },
      body: JSON.stringify(corpo),
      cache: 'no-store',
    });
    const body = await r.json().catch(() => ({}));
    return { status: r.status, body };
  } catch (e: any) {
    const abortou = e?.name === 'AbortError';
    return {
      status: abortou ? 504 : 502,
      body: {
        ok: false,
        error: abortou
          ? 'A leitura demorou mais que o esperado. Tente de novo em um minuto.'
          : 'Não foi possível falar com o serviço de identidade.',
      },
    };
  } finally {
    clearTimeout(t);
  }
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: 'Pedido bloqueado.' }, { status: xo.status });

  // Propor e aprovar mudam o perfil da corretora — os dois pedem papel
  // administrativo. Um membro comum vê o jeito; não decide o jeito.
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) {
    return NextResponse.json(
      {
        ok: false,
        error:
          auth.status === 403
            ? 'Só quem administra a corretora pode mudar o jeito de atender.'
            : 'Não autorizado.',
      },
      { status: auth.status },
    );
  }

  const corpo = await req.json().catch(() => ({} as any));
  const acao = corpo?.acao;

  if (acao === 'propor') {
    const origem = corpo?.origem === 'conversas' ? 'conversas' : 'site';
    // Ler o site e ler as conversas são operações longas — o padrão de 10s do
    // fetch derrubaria uma leitura que estava indo bem.
    const r = await chamar(
      '/api/brand/jeito/propor',
      { company_id: auth.ctx.companyId, origem },
      120_000,
    );
    return NextResponse.json(r.body, { status: r.status });
  }

  if (acao === 'aprovar') {
    const r = await chamar(
      '/api/brand/jeito/aprovar',
      {
        company_id: auth.ctx.companyId,
        user_id: auth.ctx.userId,
        ajustes: corpo?.ajustes && typeof corpo.ajustes === 'object' ? corpo.ajustes : {},
      },
      30_000,
    );
    return NextResponse.json(r.body, { status: r.status });
  }

  return NextResponse.json(
    { ok: false, error: 'Ação desconhecida.' },
    { status: 400 },
  );
}
