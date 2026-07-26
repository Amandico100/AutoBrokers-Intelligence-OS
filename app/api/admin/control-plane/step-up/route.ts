// SPEC-061 §7.4 — confirmação de identidade.
//
// A senha viaja daqui para o backend e NÃO é registrada em lugar nenhum: nem
// em log, nem na trilha, nem em cache. O único efeito que sobra é a data da
// confirmação.
import { NextRequest, NextResponse } from 'next/server';
import { resolverAutoridade } from '@/lib/admin/control-plane/authority';

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

/** A confirmação ainda vale? Usado pela tela para decidir se pede a senha. */
export async function GET() {
  const a = await resolverAutoridade();
  if (!a) return NextResponse.json({ ok: false, error: 'no_admin_session' }, { status: 401 });

  const b = backend();
  if (!b) return NextResponse.json({ ok: true, confirmado: false });

  try {
    const r = await fetch(
      `${b.url}/api/admin/control-plane/step-up?user_id=${encodeURIComponent(a.userId)}`,
      { headers: { 'X-Internal-Key': b.key }, cache: 'no-store' },
    );
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ ok: true, confirmado: false });
  }
}

export async function POST(req: NextRequest) {
  const a = await resolverAutoridade();
  if (!a) return NextResponse.json({ ok: false, error: 'no_admin_session' }, { status: 401 });

  const b = backend();
  if (!b) {
    return NextResponse.json(
      { ok: false, mensagem: 'Serviço de controle não configurado.' },
      { status: 503 },
    );
  }

  const corpo = await req.json().catch(() => ({}));
  const senha = String(corpo?.senha || '');
  if (!senha) {
    return NextResponse.json({ ok: false, mensagem: 'Informe sua senha.' }, { status: 400 });
  }

  try {
    const r = await fetch(`${b.url}/api/admin/control-plane/step-up`, {
      method: 'POST',
      headers: { 'X-Internal-Key': b.key, 'Content-Type': 'application/json' },
      // A senha vai no corpo, sobre HTTPS, e não em query string: query string
      // aparece em log de proxy e em histórico de navegador.
      body: JSON.stringify({ user_id: a.userId, senha }),
      cache: 'no-store',
    });
    const j = await r.json().catch(() => ({}));
    return NextResponse.json(
      r.ok ? j : { ok: false, mensagem: j?.detail || 'Senha incorreta.' },
      { status: r.ok ? 200 : 401 },
    );
  } catch {
    return NextResponse.json(
      { ok: false, mensagem: 'Não foi possível confirmar agora.' },
      { status: 502 },
    );
  }
}
