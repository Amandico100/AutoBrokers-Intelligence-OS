// SPEC-061 §8 e §9.1 — governança de papéis administrativos.
//
// Conceder e revogar são escritas administrativas, então passam pelo Command
// Gateway: autoriza, faz, audita, devolve recibo. Nenhuma delas toca a tabela
// diretamente daqui.
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

/** Catálogo de papéis + vínculos vigentes. */
export async function GET(req: NextRequest) {
  // `audit.read` e não `users.manage`: VER quem tem qual papel é leitura de
  // governança. Exigir a permission de escrita para consultar deixaria o
  // auditor — que existe para conferir exatamente isto — sem acesso.
  const auth = await exigirPermissao('audit.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const userId = req.nextUrl.searchParams.get('user_id') || '';
  const [catalogo, vinculos] = await Promise.all([
    chamar('/api/admin/control-plane/roles'),
    chamar(`/api/admin/control-plane/roles/bindings${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`),
  ]);

  return NextResponse.json({ ok: true, catalogo, vinculos });
}

/** Concede ou revoga. */
export async function POST(req: NextRequest) {
  const corpo = await req.json().catch(() => ({}));
  const acao = String(corpo?.acao || '');
  const userId = String(corpo?.user_id || '');
  const roleKey = String(corpo?.role_key || '');
  const reason = typeof corpo?.reason === 'string' ? corpo.reason : undefined;

  if (!userId || !roleKey) {
    return NextResponse.json(
      { ok: false, mensagem: 'Informe a pessoa e o papel.' },
      { status: 400 },
    );
  }

  if (acao === 'conceder') {
    const recibo = await executarComando({
      actionKey: 'roles.grant',
      // Mudar quem pode o quê é gestão de usuários da plataforma.
      permissionKey: 'users.manage',
      targetType: 'admin_user',
      targetId: userId,
      reason,
      executar: async (autoridade) => {
        const r = await chamar('/api/admin/control-plane/roles/grant', {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            role_key: roleKey,
            granted_by_user_id: autoridade.userId,
            reason: reason ?? null,
            expira_em_dias: corpo?.expira_em_dias ?? null,
          }),
        });
        return {
          ok: Boolean(r?.ok),
          erro: r?.ok ? undefined : String(r?.erro || r?.detail || 'falhou'),
          depois: { role_key: roleKey, status: 'active' },
        };
      },
    });
    return NextResponse.json(recibo, { status: recibo.status });
  }

  if (acao === 'revogar') {
    const recibo = await executarComando({
      actionKey: 'roles.revoke',
      permissionKey: 'users.manage',
      targetType: 'admin_user',
      targetId: userId,
      reason,
      antes: { role_key: roleKey, status: 'active' },
      executar: async (autoridade) => {
        const r = await chamar('/api/admin/control-plane/roles/revoke', {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            role_key: roleKey,
            revoked_by_user_id: autoridade.userId,
            reason: reason ?? null,
          }),
        });
        return {
          ok: Boolean(r?.ok),
          erro: r?.ok ? undefined : String(r?.erro || r?.detail || 'falhou'),
          depois: { role_key: roleKey, status: 'revoked' },
        };
      },
    });
    return NextResponse.json(recibo, { status: recibo.status });
  }

  return NextResponse.json({ ok: false, mensagem: 'Ação desconhecida.' }, { status: 400 });
}
