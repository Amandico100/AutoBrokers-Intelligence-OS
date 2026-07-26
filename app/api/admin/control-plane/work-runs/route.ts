// SPEC-061 §15 — Central de Trabalhos.
//
// Leitura exige `work_runs.read`. As ações (reprocessar, cancelar) exigem
// permissions próprias e passam pelo Command Gateway — nunca daqui direto.
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
  const auth = await exigirPermissao('work_runs.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const p = req.nextUrl.searchParams;
  const query = new URLSearchParams({
    dias: p.get('dias') || '7',
    limite: p.get('limite') || '50',
  });
  for (const campo of ['company_id', 'estado'] as const) {
    const v = p.get(campo);
    if (v) query.set(campo, v);
  }

  return NextResponse.json(await chamar(`/api/admin/control-plane/work-runs?${query}`));
}

/** Reprocessar ou cancelar. Cada uma com a sua permission. */
export async function POST(req: NextRequest) {
  const corpo = await req.json().catch(() => ({}));
  const acao = String(corpo?.acao || '');
  const runId = String(corpo?.run_id || '');
  const companyId = corpo?.company_id ? String(corpo.company_id) : undefined;
  const reason = typeof corpo?.reason === 'string' ? corpo.reason : undefined;

  if (!runId) {
    return NextResponse.json({ ok: false, mensagem: 'Informe o trabalho.' }, { status: 400 });
  }

  // Reprocessar e cancelar são permissions DIFERENTES: quem desbloqueia
  // trabalho não é necessariamente quem pode desistir dele.
  // Os endpoints reais vivem sob `/api/work` — a autoridade da SPEC-055 — e
  // recebem `company_id` como query, não no corpo. Escrever o caminho de
  // memória foi como a primeira versão apontou para `/api/work-runs/...`,
  // que não existe.
  if (!companyId) {
    return NextResponse.json(
      { ok: false, mensagem: 'Informe a corretora do trabalho.' },
      { status: 400 },
    );
  }
  const q = new URLSearchParams({ company_id: companyId });

  const mapa: Record<string, { permission: string; caminho: string; feito: string }> = {
    reprocessar: {
      permission: 'work_runs.retry',
      caminho: `/api/work/runs/${runId}/retry?${q}`,
      feito: 'Trabalho recolocado na fila. As etapas já concluídas são preservadas.',
    },
    cancelar: {
      permission: 'work_runs.cancel',
      caminho: `/api/work/runs/${runId}/cancel?${q}`,
      feito: 'Cancelamento pedido. O trabalho para na próxima etapa — ação externa em curso não é interrompida pela metade.',
    },
  };

  const alvo = mapa[acao];
  if (!alvo) {
    return NextResponse.json({ ok: false, mensagem: 'Ação desconhecida.' }, { status: 400 });
  }

  const recibo = await executarComando({
    actionKey: `work_runs.${acao}`,
    permissionKey: alvo.permission,
    targetType: 'work_run',
    targetId: runId,
    companyId,
    reason,
    executar: async (autoridade) => {
      const r = await chamar(`${alvo.caminho}&usuario_id=${encodeURIComponent(autoridade.userId)}`, {
        method: 'POST',
      });
      return {
        ok: Boolean(r?.ok),
        erro: r?.ok ? undefined : String(r?.erro || r?.detail || 'falhou'),
        depois: { acao },
      };
    },
  });

  return NextResponse.json(
    { ...recibo, mensagem: recibo.ok ? alvo.feito : recibo.mensagem },
    { status: recibo.status },
  );
}
