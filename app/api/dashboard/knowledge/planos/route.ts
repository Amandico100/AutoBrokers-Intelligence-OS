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

// 🔴 SPEC-EXTRA-001.5.1 (D2) — `r.ok` É O QUE FALTAVA, E CUSTOU O PRODUTO.
//
// 📊 18–19/09/2026: `/api/assistance-plans/fila` respondia **500** em produção.
// Esta função fazia `return await r.json()` sem olhar o status, e o `catch`
// devolvia `{ok:false, error}` — um objeto SEM `itens`. Lá na frente,
// `fila.itens || []` transformava os dois casos numa lista vazia, e a tela
// escrevia "Nada esperando revisão" com o contador do topo dizendo 60.
//
// ⚠️ A tela mentindo é pior que a tela quebrada: quem lê "nada esperando"
// fecha a aba e vai embora; quem lê "não consegui carregar" chama alguém.
//
// ⛔ O CORPO DO ERRO NÃO VIAJA. Só o status. Um 500 de FastAPI pode trazer
// traceback, e traceback em tela é vazamento (CLAUDE.md §7, §13.3).
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
    if (!r.ok) return { ok: false, status: r.status, error: 'servico_com_erro' };
    const j = await r.json().catch(() => null);
    if (!j || typeof j !== 'object') {
      return { ok: false, status: r.status, error: 'resposta_ilegivel' };
    }
    return j;
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
