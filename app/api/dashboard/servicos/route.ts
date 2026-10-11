import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { porteiroDeConfiguracao, registrarNaAuditoria } from '@/lib/admin/porteiro-de-configuracao';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-0 parte A · F4 — a tela "Serviços" (D-131-0-07/08/10/12).
 *
 * GET → { servicos: <a config dos serviços: o que a corretora mudou + o efetivo>, prontidao: <os 4 passos> }
 * PUT → { servicos?, preferencias_de_seguradoras? } — grava SÓ o manual dos serviços e as seguradoras preferidas.
 *
 * 🔴 O `company_id` vem SEMPRE da sessão — o do corpo é ignorado. Escrever passa pelo porteiro (origem + papel
 * administrativo DA corretora ativa) e fica na auditoria com QUEM mudou. O backend recusa chave fora da lista.
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

async function lerDoBackend(caminho: string): Promise<{ ok: boolean; status: number; corpo: unknown }> {
  try {
    const res = await fetch(`${getBackendUrl()}${caminho}`, { headers: backendHeaders(), cache: 'no-store' });
    return { ok: res.ok, status: res.status, corpo: await res.json().catch(() => ({})) };
  } catch {
    return { ok: false, status: 502, corpo: { error: 'Backend indisponível' } };
  }
}

export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const cid = encodeURIComponent(ctx.companyId);
  const [servicos, prontidao] = await Promise.all([
    lerDoBackend(`/api/servicos-da-corretora?company_id=${cid}`),
    lerDoBackend(`/api/servicos-da-corretora/prontidao?company_id=${cid}`),
  ]);
  if (!servicos.ok) return NextResponse.json(servicos.corpo, { status: servicos.status });
  // a prontidão é só leitura de apoio: se falhar, a tela de serviços abre mesmo assim
  return NextResponse.json({ servicos: servicos.corpo, prontidao: prontidao.ok ? prontidao.corpo : null });
}

export async function PUT(req: NextRequest) {
  const porteiro = await porteiroDeConfiguracao(req);
  if (porteiro instanceof NextResponse) return porteiro;
  const body = await req.json().catch(() => ({}));
  const corpo: Record<string, unknown> = {
    company_id: porteiro.companyId, // da SESSÃO — nunca do cliente
    atualizado_por: porteiro.userId,
  };
  if (body && typeof body === 'object' && 'servicos' in body) corpo.servicos = body.servicos;
  if (body && typeof body === 'object' && 'preferencias_de_seguradoras' in body) {
    corpo.preferencias_de_seguradoras = body.preferencias_de_seguradoras;
  }
  let res: Response;
  try {
    res = await fetch(`${getBackendUrl()}/api/servicos-da-corretora`, {
      method: 'PUT', headers: backendHeaders(), body: JSON.stringify(corpo),
    });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
  await registrarNaAuditoria(porteiro, {
    evento: 'multicalculo_config.write', acao: 'servicos.salvar',
    status: res.ok ? 'ok' : 'erro',
    metadata: {
      servicos: corpo.servicos && typeof corpo.servicos === 'object' ? Object.keys(corpo.servicos as object) : [],
      preferencias_comuns: 'preferencias_de_seguradoras' in corpo,
    },
  });
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}
