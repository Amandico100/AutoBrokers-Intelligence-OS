import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { porteiroDeConfiguracao, registrarNaAuditoria } from '@/lib/admin/porteiro-de-configuracao';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-133-A.1 F3 — o "Agger da corretora" na tela de conexões (D-133A1-03/04).
 *
 * GET  → { conta: { situacao, rotulo, usuario (mascarado), tem_senha, ultimo_uso, janela, acoes… } }
 * POST → { acao: 'conectar' | 'trocar_senha' | 'pausar' | 'religar' | 'desconectar' | 'janela', usuario?, senha?, janela? }
 *
 * 🔴 O `company_id` vem SEMPRE da sessão — o do corpo é ignorado. Escrever passa pelo porteiro (origem + papel
 * administrativo DA corretora ativa). A senha só atravessa para o backend, que cifra no cofre; nunca volta, nunca
 * vai para log nem para a auditoria.
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

const ACOES = new Set(['conectar', 'trocar_senha', 'pausar', 'religar', 'desconectar', 'janela']);

export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  try {
    const res = await fetch(
      `${getBackendUrl()}/api/portal/agger-da-corretora?company_id=${encodeURIComponent(ctx.companyId)}`,
      { headers: backendHeaders(), cache: 'no-store' },
    );
    return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
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
  let res: Response;
  try {
    res = await fetch(`${getBackendUrl()}/api/portal/agger-da-corretora`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({
        acao,
        usuario: typeof body?.usuario === 'string' ? body.usuario : undefined,
        senha: typeof body?.senha === 'string' ? body.senha : undefined,
        janela: body?.janela && typeof body.janela === 'object' ? body.janela : undefined,
        company_id: porteiro.companyId, // da SESSÃO — nunca do cliente
      }),
    });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
  await registrarNaAuditoria(porteiro, {
    evento: 'portal_credential.write', acao: `agger_da_corretora.${acao}`,
    status: res.ok ? 'ok' : 'erro',
    // ⛔ nunca a senha, nunca o login: só O QUE mudou.
    metadata: { portal_key: 'agger', tem_senha: Boolean(body?.senha) },
  });
  return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
}
