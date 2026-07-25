// SPEC-057 — identidade da corretora. GET membro; PATCH/POST admin + same-origin.
//
// A rota é fina de propósito: autoriza, resolve o tenant a partir da sessão e
// repassa. O company_id NUNCA vem do corpo — vem da sessão. Aceitá-lo do
// cliente seria entregar a identidade de qualquer corretora a quem soubesse
// digitar um UUID.
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
  init: RequestInit & { timeoutMs?: number } = {},
): Promise<{ ok: boolean; status: number; body: any }> {
  const b = backend();
  if (!b) {
    return {
      ok: false,
      status: 503,
      body: { ok: false, error: 'Serviço de identidade não configurado.' },
    };
  }

  const controller = new AbortController();
  // Captura busca site e redes; o padrão de 10s do fetch derrubaria toda
  // captura legítima e o corretor veria "falhou" numa operação que estava indo.
  const t = setTimeout(() => controller.abort(), init.timeoutMs ?? 90_000);
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      ...init,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Key': b.key,
        ...(init.headers || {}),
      },
      cache: 'no-store',
    });
    const body = await r.json().catch(() => ({}));
    return { ok: r.ok, status: r.status, body };
  } catch (e: any) {
    const abortou = e?.name === 'AbortError';
    return {
      ok: false,
      status: abortou ? 504 : 502,
      body: {
        ok: false,
        error: abortou
          ? 'A captura demorou mais que o esperado. O site pode estar lento — tente de novo.'
          : 'Não foi possível falar com o serviço de identidade.',
      },
    };
  } finally {
    clearTimeout(t);
  }
}

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const r = await chamar(
    `/api/brand/profile?company_id=${encodeURIComponent(auth.ctx.companyId)}`,
    { method: 'GET', timeoutMs: 20_000 },
  );
  return NextResponse.json(r.body, { status: r.status });
}

export async function PATCH(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const r = await chamar('/api/brand/profile', {
    method: 'PATCH',
    timeoutMs: 20_000,
    body: JSON.stringify({
      company_id: auth.ctx.companyId,
      user_id: auth.ctx.userId ?? null,
      values: corpo?.values && typeof corpo.values === 'object' ? corpo.values : {},
    }),
  });
  return NextResponse.json(r.body, { status: r.status });
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const r = await chamar('/api/brand/capture', {
    method: 'POST',
    body: JSON.stringify({
      company_id: auth.ctx.companyId,
      force: corpo?.force === true,
    }),
  });
  return NextResponse.json(r.body, { status: r.status });
}
