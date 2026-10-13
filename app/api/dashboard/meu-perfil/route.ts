import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';
import { canWriteTenantConfig } from '@/lib/admin/admin-auth-policy';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-B G3 — "Meu perfil": o MEU WhatsApp de trabalho e a MINHA ausência (D-131-41, D-131-08).
 *
 * GET    → { whatsapp_trabalho: {numero, confirmado_em, confirmado, disponivel}, ausencias, cubro, pessoas, eu,
 *            pode_gerir_todos }
 * PUT    { numero, confirmo: true }    grava o WhatsApp de trabalho DA PESSOA DA SESSÃO · { numero: null } apaga
 * POST   { substituto_user_id, de, ate, user_id? }   marca a ausência (a minha; `user_id` de outra pessoa só o admin)
 * DELETE ?id=                           apaga uma ausência (a minha; a de outra pessoa só o admin)
 *
 * 🔴 `company_id`, `user_id` e `por_user_id` vêm SEMPRE da sessão — nunca do corpo (o `user_id` do corpo só vale para o
 * admin marcar a ausência de outra pessoa, e o backend confere o papel de novo, no banco).
 * ⛔ O WhatsApp de trabalho é só o NÚMERO: nada em `integrations`, nenhum pareamento. O número de atendimento da corretora
 * e o do Quem Cobra Menos são outros e não mudam. ⛔ O número nunca vai para log nem para a auditoria.
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

const BASE = '/api/contas-da-corretora/perfil';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function repassar(res: Response) {
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}

/** Escrever: mesma origem + vínculo ATIVO com a corretora da sessão (a própria pessoa — sem exigir papel de admin). */
async function quemEscreve(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  return auth.ctx;
}

export async function GET() {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const { companyId, userId, role, isOwner } = auth.ctx;
  try {
    const res = await fetch(
      `${getBackendUrl()}${BASE}?company_id=${encodeURIComponent(companyId)}&user_id=${encodeURIComponent(userId)}`,
      { headers: backendHeaders(), cache: 'no-store' },
    );
    const j = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json(j, { status: res.status });
    return NextResponse.json({ ...j, eu: userId, pode_gerir_todos: canWriteTenantConfig({ role, isOwner }) });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}

export async function PUT(req: NextRequest) {
  const ctx = await quemEscreve(req);
  if (ctx instanceof NextResponse) return ctx;
  const body = await req.json().catch(() => ({}));
  const numero = body?.numero === null ? null : typeof body?.numero === 'string' ? body.numero : undefined;
  if (numero === undefined) return NextResponse.json({ error: 'Digite o número.' }, { status: 400 });
  try {
    const res = await fetch(`${getBackendUrl()}${BASE}/whatsapp-de-trabalho`, {
      method: 'PUT',
      headers: backendHeaders(),
      body: JSON.stringify({
        company_id: ctx.companyId, // da SESSÃO
        user_id: ctx.userId, // 🔴 só o MEU número: o dono do número é sempre quem está logado
        por_user_id: ctx.userId,
        numero,
        confirmo: body?.confirmo === true,
      }),
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  const ctx = await quemEscreve(req);
  if (ctx instanceof NextResponse) return ctx;
  const body = await req.json().catch(() => ({}));
  const dono = typeof body?.user_id === 'string' && UUID.test(body.user_id) ? body.user_id : ctx.userId;
  if (!UUID.test(String(body?.substituto_user_id || ''))) {
    return NextResponse.json({ error: 'Escolha quem vai cobrir a ausência.' }, { status: 400 });
  }
  try {
    const res = await fetch(`${getBackendUrl()}${BASE}/ausencias`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({
        company_id: ctx.companyId,
        user_id: dono,
        substituto_user_id: body.substituto_user_id,
        de: String(body?.de || ''),
        ate: String(body?.ate || ''),
        por_user_id: ctx.userId, // o backend confere: a própria pessoa, ou o admin desta corretora
      }),
    });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}

export async function DELETE(req: NextRequest) {
  const ctx = await quemEscreve(req);
  if (ctx instanceof NextResponse) return ctx;
  const id = req.nextUrl.searchParams.get('id') || '';
  if (!UUID.test(id)) return NextResponse.json({ error: 'Ausência inválida' }, { status: 400 });
  try {
    const q = `company_id=${encodeURIComponent(ctx.companyId)}&id=${encodeURIComponent(id)}&por_user_id=${encodeURIComponent(ctx.userId)}`;
    const res = await fetch(`${getBackendUrl()}${BASE}/ausencias?${q}`, { method: 'DELETE', headers: backendHeaders() });
    return repassar(res);
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
