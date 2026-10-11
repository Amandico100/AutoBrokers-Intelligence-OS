import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { porteiroDeConfiguracao, registrarNaAuditoria } from '@/lib/admin/porteiro-de-configuracao';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-0 F2 — "Quem é quem no sistema de gestão" (D-131-0-03/30/31).
 *
 * GET  ?o=vinculos (padrão)  → { vinculos, membros, regra, padrao }
 * GET  ?o=sugestoes          → { status, produtores: [{codigo_produtor, nome_produtor, papel_cru, vinculo, sugestao}], membros }
 * POST { acao: 'vincular', user_id, codigo_produtor, codfil?, nome_produtor?, papel_cru? }
 * POST { acao: 'desvincular', id }
 * POST { acao: 'regra', regra }            (regra null = voltar ao padrão do sistema)
 * POST { acao: 'medir', dias? }            → a régua (só contagens; nunca nome de cliente)
 *
 * 🔴 O `company_id` vem SEMPRE da sessão — o do corpo é ignorado. Ler: membro da corretora ativa
 * (`resolveSessionCompany`). Escrever e medir: o porteiro (origem + papel administrativo DA corretora ativa) e a
 * auditoria (só O QUE mudou: nunca nome de produtor nem de pessoa).
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

const BASE = '/api/contas-da-corretora/sistema-de-gestao';
const ACOES = new Set(['vincular', 'desvincular', 'regra', 'medir']);

async function repassar(res: Response) {
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const cid = encodeURIComponent(ctx.companyId);
  const o = req.nextUrl.searchParams.get('o') || 'vinculos';
  try {
    if (o === 'sugestoes') {
      const res = await fetch(`${getBackendUrl()}${BASE}/sugestoes?company_id=${cid}`, {
        headers: backendHeaders(),
        cache: 'no-store',
      });
      return repassar(res);
    }
    const [v, r] = await Promise.all([
      fetch(`${getBackendUrl()}${BASE}/vinculos?company_id=${cid}&sistema=infocap`, {
        headers: backendHeaders(),
        cache: 'no-store',
      }),
      fetch(`${getBackendUrl()}${BASE}/regra?company_id=${cid}&sistema=infocap`, {
        headers: backendHeaders(),
        cache: 'no-store',
      }),
    ]);
    if (!v.ok) return repassar(v);
    const vj = await v.json().catch(() => ({}));
    const rj = r.ok ? await r.json().catch(() => ({})) : {};
    return NextResponse.json({ ...vj, regra: rj?.regra ?? null, padrao: rj?.padrao ?? null });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  const porteiro = await porteiroDeConfiguracao(req);
  if (porteiro instanceof NextResponse) return porteiro;
  const body = await req.json().catch(() => ({}));
  const acao = String(body?.acao || '');
  if (!ACOES.has(acao)) return NextResponse.json({ error: 'Ação desconhecida' }, { status: 400 });
  const companyId = porteiro.companyId; // da SESSÃO — nunca do cliente
  const url = getBackendUrl();
  let res: Response;
  try {
    if (acao === 'vincular') {
      res = await fetch(`${url}${BASE}/vincular`, {
        method: 'POST',
        headers: backendHeaders(),
        body: JSON.stringify({
          company_id: companyId,
          sistema: 'infocap',
          user_id: String(body?.user_id || ''),
          codfil: Number(body?.codfil) || 1,
          codigo_produtor: String(body?.codigo_produtor ?? ''),
          nome_produtor: typeof body?.nome_produtor === 'string' ? body.nome_produtor : undefined,
          papel_cru: typeof body?.papel_cru === 'string' ? body.papel_cru : undefined,
          por_user_id: porteiro.userId,
        }),
      });
    } else if (acao === 'desvincular') {
      const id = encodeURIComponent(String(body?.id || ''));
      res = await fetch(`${url}${BASE}/vincular?company_id=${encodeURIComponent(companyId)}&id=${id}`, {
        method: 'DELETE',
        headers: backendHeaders(),
      });
    } else if (acao === 'regra') {
      res = await fetch(`${url}${BASE}/regra`, {
        method: 'PUT',
        headers: backendHeaders(),
        body: JSON.stringify({
          company_id: companyId,
          sistema: 'infocap',
          regra: body?.regra ?? null,
          por_user_id: porteiro.userId,
        }),
      });
    } else {
      res = await fetch(`${url}${BASE}/medir`, {
        method: 'POST',
        headers: backendHeaders(),
        body: JSON.stringify({ company_id: companyId, dias: Number(body?.dias) || 30 }),
      });
    }
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
  if (acao !== 'medir') {
    await registrarNaAuditoria(porteiro, {
      evento: 'sistema_de_gestao.write',
      acao: `quem_e_quem.${acao}`,
      status: res.ok ? 'ok' : 'erro',
      // ⛔ nunca nome de produtor nem de pessoa: só o código e quem foi ligado.
      metadata: {
        sistema: 'infocap',
        codigo_produtor: acao === 'vincular' ? String(body?.codigo_produtor ?? '') : undefined,
        user_id: acao === 'vincular' ? String(body?.user_id || '') : undefined,
        vinculo_id: acao === 'desvincular' ? String(body?.id || '') : undefined,
        voltou_ao_padrao: acao === 'regra' ? body?.regra == null : undefined,
      },
    });
  }
  return repassar(res);
}
