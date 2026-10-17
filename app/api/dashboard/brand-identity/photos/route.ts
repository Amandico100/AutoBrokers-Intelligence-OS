// SPEC-130-C · F1 — as FOTOS da corretora. GET membro; POST/PATCH/DELETE/PUT admin + same-origin.
//
// Mesmo desenho da rota vizinha (`../route.ts`): a rota autoriza, resolve a corretora pela SESSÃO e repassa. O
// company_id NUNCA vem do corpo nem da URL — vem da sessão. O backend (`services/brand/fotos.py`) confere de novo o
// tipo pelos BYTES, o teto de 8 e o dono de cada foto; aqui só se barra o óbvio cedo.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

/** 10 MB: uma foto de celular tem 3–6 MB; acima disso é vídeo ou arquivo errado. O backend corta no mesmo número. */
const FOTO_TETO_BYTES = 10 * 1024 * 1024;
/** O tipo declarado só barra cedo o que nem foto é; quem decide são os BYTES, no backend. Vazio passa (HEIC às vezes). */
const FOTO_TIPOS = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'];
const LEGENDA_TETO = 80;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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
  init: RequestInit & { timeoutMs?: number; json?: boolean } = {},
): Promise<{ status: number; body: any }> {
  const b = backend();
  if (!b)
    return { status: 503, body: { ok: false, error: 'Serviço de identidade não configurado.' } };
  const { timeoutMs, json = true, ...resto } = init;
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs ?? 30_000);
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      ...resto,
      signal: controller.signal,
      headers: {
        // multipart: o fetch escreve o Content-Type com a fronteira; forçar JSON quebraria o envio
        ...(json ? { 'Content-Type': 'application/json' } : {}),
        'X-Internal-Key': b.key,
        ...(resto.headers || {}),
      },
      cache: 'no-store',
    });
    const body = await r.json().catch(() => ({}));
    // o backend recusa por HTTPException com `detail`; a tela lê `error` (E14)
    if (
      body &&
      typeof body === 'object' &&
      !body.error &&
      typeof body.detail === 'string' &&
      !r.ok
    ) {
      body.error = body.detail;
    }
    return { status: r.status, body };
  } catch (e: any) {
    const abortou = e?.name === 'AbortError';
    return {
      status: abortou ? 504 : 502,
      body: {
        ok: false,
        error: abortou
          ? 'O envio demorou mais que o esperado. Tente de novo.'
          : 'Não foi possível falar com o serviço de identidade.',
      },
    };
  } finally {
    clearTimeout(t);
  }
}

async function escrita(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo)
    return {
      erro: NextResponse.json({ ok: false, error: xo.error }, { status: xo.status }),
    } as const;
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok)
    return {
      erro: NextResponse.json({ ok: false, error: auth.error }, { status: auth.status }),
    } as const;
  return { ctx: auth.ctx } as const;
}

function idDaFoto(req: NextRequest): string | null {
  const id = (req.nextUrl.searchParams.get('id') || '').trim();
  return UUID.test(id) ? id : null;
}

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const r = await chamar(`/api/brand/photos?company_id=${encodeURIComponent(auth.ctx.companyId)}`, {
    method: 'GET',
    timeoutMs: 20_000,
  });
  return NextResponse.json(r.body, { status: r.status });
}

/** Adicionar uma foto: multipart `foto` (+ `legenda`). */
export async function POST(req: NextRequest) {
  const a = await escrita(req);
  if ('erro' in a) return a.erro;

  const form = await req.formData().catch(() => null);
  const arquivo = form?.get('foto');
  if (!arquivo || typeof arquivo === 'string') {
    return NextResponse.json({ ok: false, error: 'Escolha a foto.' }, { status: 400 });
  }
  if (arquivo.size === 0) {
    return NextResponse.json(
      { ok: false, error: 'O arquivo está vazio. Escolha a foto de novo.' },
      { status: 400 },
    );
  }
  if (arquivo.size > FOTO_TETO_BYTES) {
    return NextResponse.json(
      {
        ok: false,
        error: `A foto tem ${(arquivo.size / (1024 * 1024)).toFixed(1)} MB e o limite é 10 MB. Envie uma versão menor.`,
      },
      { status: 400 },
    );
  }
  if (arquivo.type && !FOTO_TIPOS.includes(arquivo.type.toLowerCase())) {
    return NextResponse.json(
      {
        ok: false,
        error: 'Esse arquivo não é uma foto que dê para usar. Envie JPG, PNG, WebP ou HEIC.',
      },
      { status: 400 },
    );
  }
  const legendaBruta = form?.get('legenda');
  const legenda = typeof legendaBruta === 'string' ? legendaBruta.trim() : '';
  if (legenda.length > LEGENDA_TETO) {
    return NextResponse.json(
      { ok: false, error: `A legenda pode ter até ${LEGENDA_TETO} caracteres.` },
      { status: 400 },
    );
  }

  const corpo = new FormData();
  corpo.append('company_id', a.ctx.companyId);
  if (a.ctx.userId) corpo.append('user_id', String(a.ctx.userId));
  if (legenda) corpo.append('legenda', legenda);
  corpo.append('foto', new Blob([await arquivo.arrayBuffer()]), 'foto');
  const r = await chamar('/api/brand/photos', {
    method: 'POST',
    body: corpo,
    json: false,
    timeoutMs: 60_000,
  });
  return NextResponse.json(r.body, { status: r.status });
}

/** Trocar a legenda de uma foto: `?id=<uuid>` + `{ legenda }`. */
export async function PATCH(req: NextRequest) {
  const a = await escrita(req);
  if ('erro' in a) return a.erro;
  const id = idDaFoto(req);
  if (!id) return NextResponse.json({ ok: false, error: 'Foto não encontrada.' }, { status: 404 });
  const corpo = await req.json().catch(() => ({}));
  const envio: Record<string, unknown> = { company_id: a.ctx.companyId };
  if (corpo && Object.prototype.hasOwnProperty.call(corpo, 'legenda')) {
    const legenda = corpo.legenda == null ? null : String(corpo.legenda);
    if (legenda && legenda.trim().length > LEGENDA_TETO) {
      return NextResponse.json(
        { ok: false, error: `A legenda pode ter até ${LEGENDA_TETO} caracteres.` },
        { status: 400 },
      );
    }
    envio.legenda = legenda;
  }
  const r = await chamar(`/api/brand/photos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(envio),
  });
  return NextResponse.json(r.body, { status: r.status });
}

/** Remover uma foto: `?id=<uuid>`. */
export async function DELETE(req: NextRequest) {
  const a = await escrita(req);
  if ('erro' in a) return a.erro;
  const id = idDaFoto(req);
  if (!id) return NextResponse.json({ ok: false, error: 'Foto não encontrada.' }, { status: 404 });
  const r = await chamar(
    `/api/brand/photos/${id}?company_id=${encodeURIComponent(a.ctx.companyId)}`,
    { method: 'DELETE' },
  );
  return NextResponse.json(r.body, { status: r.status });
}

/** A nova ordem: `{ ids: [uuid, …] }`, de cima para baixo. */
export async function PUT(req: NextRequest) {
  const a = await escrita(req);
  if ('erro' in a) return a.erro;
  const corpo = await req.json().catch(() => ({}));
  const ids = Array.isArray(corpo?.ids) ? corpo.ids.map((x: unknown) => String(x)) : [];
  if (ids.length === 0 || ids.length > 8 || !ids.every((x: string) => UUID.test(x))) {
    return NextResponse.json(
      {
        ok: false,
        error: 'A ordem não confere com as fotos atuais. Recarregue a página e tente de novo.',
      },
      { status: 400 },
    );
  }
  const r = await chamar('/api/brand/photos/order', {
    method: 'PUT',
    body: JSON.stringify({ company_id: a.ctx.companyId, ids }),
  });
  return NextResponse.json(r.body, { status: r.status });
}
