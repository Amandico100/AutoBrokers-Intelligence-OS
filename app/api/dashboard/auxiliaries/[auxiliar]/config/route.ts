// SPEC-064 Bloco F — a corretora ajusta o Auxiliar dela.
//
// Esta rota não existia. `tenant_auxiliaries.config` era gravado na instalação
// e nunca mais — e `tenant_auxiliary_revisions`, a tabela do histórico, tinha
// ZERO referências em código.
//
// A rota identifica o Auxiliar por `slug`, e não por `templateId`, porque o
// slug é o que o corretor e o chat conhecem. O `company_id` NUNCA vem do
// client.
//
// O SEGMENTO da URL, porém, chama-se `[auxiliar]`: a rota irmã (install/pause/
// resume) ocupa a mesma posição e recebe um UUID. O Next.js exige um único nome
// de parâmetro por posição — dois nomes impedem a montagem da tabela de rotas e
// derrubam TODAS as rotas do servidor com 500. Foi o que aconteceu em
// 02/08/2026. A URL é a mesma; muda só a chave.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { gravarConfigDaCorretora, historicoDeConfig } from '@/lib/auxiliaries/config-store';

export const dynamic = 'force-dynamic';

/** GET — o histórico de mudanças desta corretora neste Auxiliar. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ auxiliar: string }> }) {
  const { auxiliar: slug } = await params;
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const out = await historicoDeConfig(auth.supabase, auth.ctx.companyId, slug);
  return NextResponse.json(out, { status: out.ok ? 200 : 404 });
}

/** PATCH — grava a sobreposição da corretora, com revisão. */
export async function PATCH(req: NextRequest, { params }: { params: Promise<{ auxiliar: string }> }) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });

  const { auxiliar: slug } = await params;
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const body = await req.json().catch(() => ({}));
  const mudancas = body?.config;
  if (!mudancas || typeof mudancas !== 'object' || Array.isArray(mudancas)) {
    return NextResponse.json({ ok: false, error: 'config_invalida' }, { status: 400 });
  }

  const out = await gravarConfigDaCorretora(auth.supabase, {
    companyId: auth.ctx.companyId,
    slug,
    mudancas: mudancas as Record<string, unknown>,
    porQuem: auth.ctx.userId,
    motivo: typeof body?.motivo === 'string' ? body.motivo : undefined,
  });

  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
