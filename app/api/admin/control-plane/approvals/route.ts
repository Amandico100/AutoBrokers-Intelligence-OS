// SPEC-061 §16 — Central de aprovações.
//
// Ler exige `approvals.read`. DECIDIR exige `approvals.decide` e passa pelo
// Command Gateway: a decisão fica registrada com quem, quando e por quê.
import { NextRequest, NextResponse } from 'next/server';
import { exigirPermissao } from '@/lib/admin/control-plane/authority';
import { executarComando } from '@/lib/admin/control-plane/command-gateway';

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
  if (!b) return { ok: false, erro: 'Serviço de controle não configurado.' };
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
    return { ok: false, erro: 'Não foi possível falar com o serviço.' };
  }
}

export async function GET(req: NextRequest) {
  const auth = await exigirPermissao('approvals.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const p = req.nextUrl.searchParams;
  const query = new URLSearchParams({
    status: p.get('status') || 'pending',
    limite: p.get('limite') || '50',
  });
  const cid = p.get('company_id');
  if (cid) query.set('company_id', cid);

  return NextResponse.json(await chamar(`/api/admin/control-plane/approvals?${query}`));
}

export async function POST(req: NextRequest) {
  const corpo = await req.json().catch(() => ({}));
  const id = String(corpo?.approval_id || '');
  const decisao = String(corpo?.decisao || '');
  const companyId = String(corpo?.company_id || '');
  const motivo = typeof corpo?.motivo === 'string' ? corpo.motivo : undefined;

  if (!id || !companyId || !['approved', 'rejected'].includes(decisao)) {
    return NextResponse.json(
      { ok: false, mensagem: 'Informe a aprovação, a corretora e a decisão.' },
      { status: 400 },
    );
  }

  // Recusar sem motivo é o pior dos dois: quem pediu não descobre o que
  // corrigir, e quem decidiu não lembra em uma semana.
  if (decisao === 'rejected' && (motivo ?? '').trim().length < 5) {
    return NextResponse.json(
      { ok: false, mensagem: 'Diga por que está recusando — quem pediu precisa saber o que corrigir.' },
      { status: 400 },
    );
  }

  const recibo = await executarComando({
    actionKey: `approvals.${decisao}`,
    permissionKey: 'approvals.decide',
    targetType: 'approval_request',
    targetId: id,
    companyId,
    reason: motivo,
    antes: { status: 'pending' },
    executar: async (autoridade) => {
      const r = await chamar(`/api/work/approvals/${id}/decide`, {
        method: 'POST',
        body: JSON.stringify({
          company_id: companyId,
          decisao,
          usuario_id: autoridade.userId,
          motivo: motivo ?? null,
        }),
      });
      return {
        ok: Boolean(r?.ok),
        erro: r?.ok ? undefined : String(r?.erro || r?.detail || 'falhou'),
        depois: { status: decisao },
      };
    },
  });

  return NextResponse.json(
    {
      ...recibo,
      mensagem: recibo.ok
        ? decisao === 'approved'
          ? 'Aprovado. A ação segue pelo caminho normal, com as verificações que ela já tinha.'
          : 'Recusado. O motivo ficou registrado.'
        : recibo.mensagem,
    },
    { status: recibo.status },
  );
}
