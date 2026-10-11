import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany } from '@/lib/vault/server';
import { porteiroDeConfiguracao, registrarNaAuditoria, type PorteiroOk } from '@/lib/admin/porteiro-de-configuracao';
import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';
import { canWriteTenantConfig } from '@/lib/admin/admin-auth-policy';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-0 parte A · F3 — os "Aggers da equipe" (D-131-0-05/06/29): o Agger de cada PESSOA ao lado do Agger da
 * corretora.
 *
 * GET  → { pessoas: [{ user_id, nome, papel, funcoes, agger: { situacao, rotulo, usuario (mascarado), acoes… } }],
 *          eu, pode_gerir_todos }
 * POST → { acao: 'conectar' | 'trocar_senha' | 'pausar' | 'religar' | 'desconectar', dono_user_id, usuario?, senha? }
 *
 * 🔴 Quem pode ESCREVER (D-131-0-06): o admin da corretora (o porteiro — origem + papel administrativo da corretora
 * ativa) por qualquer pessoa da equipe, OU a própria pessoa pelo Agger DELA (`dono_user_id` = o usuário da sessão).
 * Qualquer outro caso → 403. O backend confere de novo, no banco (`conta_do_robo._pode_mexer`).
 * 🔴 `company_id` e `por_user_id` vêm SEMPRE da sessão — nunca do corpo. A senha só atravessa para o backend, que cifra;
 * nunca volta, nunca vai para log nem para a auditoria.
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

const ACOES = new Set(['conectar', 'trocar_senha', 'pausar', 'religar', 'desconectar']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  // só para a TELA esconder os botões que a pessoa não pode usar — quem decide é o POST (e o backend)
  let podeGerirTodos = false;
  try {
    const auth = await requireCompanyMember({ write: false });
    podeGerirTodos = auth.ok && auth.ctx.companyId === ctx.companyId
      && canWriteTenantConfig({ role: auth.ctx.role, isOwner: auth.ctx.isOwner });
  } catch {
    podeGerirTodos = false;
  }
  try {
    const res = await fetch(
      `${getBackendUrl()}/api/portal/aggers-da-equipe?company_id=${encodeURIComponent(ctx.companyId)}`,
      { headers: backendHeaders(), cache: 'no-store' },
    );
    const j = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json(j, { status: res.status });
    return NextResponse.json({ ...j, eu: ctx.userId, pode_gerir_todos: podeGerirTodos });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}

/** O admin passa pelo porteiro; a própria pessoa passa por origem + vínculo ATIVO com a corretora (sem papel de admin). */
async function quemPode(req: NextRequest, donoUserId: string): Promise<PorteiroOk | NextResponse> {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  if (auth.ctx.userId === donoUserId) {
    return {
      companyId: auth.ctx.companyId, userId: auth.ctx.userId, role: auth.ctx.role,
      isOwner: auth.ctx.isOwner, supabase: auth.supabase,
    };
  }
  // outra pessoa: só o admin da corretora (o porteiro — a mesma régua das outras telas de configuração)
  return porteiroDeConfiguracao(req);
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const acao = String(body?.acao || '');
  const dono = String(body?.dono_user_id || '');
  if (!ACOES.has(acao)) return NextResponse.json({ error: 'Ação desconhecida' }, { status: 400 });
  if (!UUID.test(dono)) return NextResponse.json({ error: 'Pessoa inválida' }, { status: 400 });
  const quem = await quemPode(req, dono);
  if (quem instanceof NextResponse) return quem;
  let res: Response;
  try {
    res = await fetch(`${getBackendUrl()}/api/portal/aggers-da-equipe`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({
        acao,
        dono_user_id: dono,
        usuario: typeof body?.usuario === 'string' ? body.usuario : undefined,
        senha: typeof body?.senha === 'string' ? body.senha : undefined,
        company_id: quem.companyId, // da SESSÃO — nunca do cliente
        por_user_id: quem.userId, // da SESSÃO — nunca do cliente
      }),
    });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
  await registrarNaAuditoria(quem, {
    evento: 'portal_credential.write', acao: `aggers_da_equipe.${acao}`,
    status: res.ok ? 'ok' : 'erro',
    // ⛔ nunca a senha, nunca o login: só O QUE mudou e DE QUEM é o Agger.
    metadata: { portal_key: 'agger', uso: 'membro', dono_user_id: dono, tem_senha: Boolean(body?.senha) },
  });
  const j = await res.json().catch(() => ({}));
  return NextResponse.json(j, { status: res.status });
}
