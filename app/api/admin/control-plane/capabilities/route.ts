// SPEC-061 §10.4 — Skills, ferramentas e os poderes que as governam.
import { NextResponse } from 'next/server';
import { exigirPermissao } from '@/lib/admin/control-plane/authority';

export const dynamic = 'force-dynamic';

export async function GET() {
  const auth = await exigirPermissao('skills.read');
  if (!auth.ok) return NextResponse.json(auth, { status: auth.status });

  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) {
    return NextResponse.json({ ok: false, erro: 'Serviço de controle não configurado.' });
  }

  try {
    const r = await fetch(`${url}/api/admin/control-plane/capabilities`, {
      headers: { 'X-Internal-Key': key },
      cache: 'no-store',
    });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ ok: false, erro: 'Não foi possível falar com o serviço.' });
  }
}
