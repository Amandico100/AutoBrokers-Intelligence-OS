// SPEC-EXTRA-001.5 · BLOCO D — o que a base de planos cobre, e a fila de curadoria.
//
// 🔴 A BASE É GLOBAL (D-PILOTO-01): o que a apólice da HDI cobre é o mesmo para
// todas as corretoras. Por isso — e ao contrário de TODA rota vizinha deste
// diretório — este arquivo NÃO manda `company_id` para lugar nenhum. A sessão é
// validada (quem não é da casa não entra), mas o dado não é escopado por
// corretora: dois usuários de corretoras diferentes leem a mesma resposta, e é
// isso que o GATE D prova.
//
// Publicar/rejeitar exige papel administrativo (`write: true`, o mesmo critério
// dos vizinhos) e grava como revisor o usuário da SESSÃO — nunca um id vindo do
// corpo: é o nome de quem responde por "guincho até 200 km".
import { NextRequest, NextResponse } from 'next/server';
import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';

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
  if (!b) return { ok: false, error: 'indisponivel' };
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
    return { ok: false, error: 'indisponivel' };
  }
}

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const [cobertura, fila] = await Promise.all([
    chamar('/api/assistance-plans/cobertura'),
    chamar('/api/assistance-plans/fila'),
  ]);
  return NextResponse.json({ ok: true, cobertura, fila });
}

export async function POST(req: NextRequest) {
  const mesmaOrigem = assertSameOrigin(req);
  if (mesmaOrigem) return NextResponse.json(mesmaOrigem, { status: mesmaOrigem.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const out = await chamar('/api/assistance-plans/curadoria', {
    method: 'POST',
    body: JSON.stringify({
      id: corpo?.id,
      acao: corpo?.acao,
      motivo: corpo?.motivo,
      revisado_por: auth.ctx.userId, // 🔴 da SESSÃO, nunca do corpo
    }),
  });
  return NextResponse.json(out);
}
