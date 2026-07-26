// SPEC-061 §13 — a caixa "O que precisa de mim".
//
// As permissions vão daqui para o backend porque o BFF já as resolveu nesta
// requisição. Reconsultar lá dentro faria duas leituras da mesma autoridade e
// abriria a chance de as duas discordarem no meio do caminho.
import { NextRequest, NextResponse } from 'next/server';
import { exigirPermissao } from '@/lib/admin/control-plane/authority';

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

export async function GET(req: NextRequest) {
  const auth = await exigirPermissao('admin.inbox.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const b = backend();
  if (!b) {
    return NextResponse.json({
      ok: true,
      itens: [],
      total: 0,
      naoLidos: 0,
      // Distinguir "nada precisa de você" de "não consegui olhar" é o mesmo
      // princípio do monitor de pesquisa: nunca afirmar sobre o que não foi lido.
      mensagem: 'Não consegui consultar agora — o serviço de controle não está configurado.',
    });
  }

  try {
    const r = await fetch(`${b.url}/api/admin/control-plane/inbox`, {
      method: 'POST',
      headers: { 'X-Internal-Key': b.key, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_user_id: auth.autoridade.userId,
        permissions: Array.from(auth.autoridade.permissions),
        // O dono passa em qualquer permission; sem esta flag, a caixa dele
        // viria vazia justamente quando o backend acabou de voltar e a lista
        // ainda não foi recarregada.
        pode_tudo: Boolean(auth.autoridade.podeTudo),
        limite: Number(req.nextUrl.searchParams.get('limite') || 50),
      }),
      cache: 'no-store',
    });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({
      ok: false,
      itens: [],
      mensagem: 'Não consegui consultar agora. Tente de novo em instantes.',
    });
  }
}

/** Estado pessoal: li, reconheci, adiei, dispensei. */
export async function POST(req: NextRequest) {
  const auth = await exigirPermissao('admin.inbox.manage');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const b = backend();
  if (!b) return NextResponse.json({ ok: false, erro: 'Serviço não configurado.' }, { status: 503 });

  const corpo = await req.json().catch(() => ({}));
  try {
    const r = await fetch(`${b.url}/api/admin/control-plane/inbox/mark`, {
      method: 'POST',
      headers: { 'X-Internal-Key': b.key, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_user_id: auth.autoridade.userId,
        fonte: String(corpo?.fonte || ''),
        chave: String(corpo?.chave || ''),
        estado: String(corpo?.estado || ''),
        adiar_ate: corpo?.adiar_ate ?? null,
        nota: corpo?.nota ?? null,
      }),
      cache: 'no-store',
    });
    return NextResponse.json(await r.json(), { status: r.status });
  } catch {
    return NextResponse.json({ ok: false, erro: 'Não foi possível salvar.' }, { status: 502 });
  }
}
