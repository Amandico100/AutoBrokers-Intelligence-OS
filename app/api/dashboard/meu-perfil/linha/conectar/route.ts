import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-0-B2 L3 — "Conectar meu WhatsApp": pede ao backend uma conexão NOVA da linha da pessoa da sessão e devolve
 * o primeiro QR. Quem prova a posse do número é quem lê o QR com o próprio celular.
 *
 * POST → { tentativa_id, qr | null, estado? }   (cheio → status do backend + { estado: 'limite', detail })
 *
 * 🔴 `company_id` e `user_id` vêm SEMPRE da sessão — o corpo do pedido não é lido.
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

const SEM_CACHE = { 'Cache-Control': 'no-store' };
const FORA_DO_AR = 'Não conseguimos falar com o AutoBrokers agora. Tente de novo em instantes.';

function texto(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v : null;
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const { companyId, userId } = auth.ctx;
  try {
    const res = await fetch(`${getBackendUrl()}/api/linha-do-usuario/conectar`, {
      method: 'POST',
      headers: backendHeaders(),
      cache: 'no-store',
      body: JSON.stringify({ company_id: companyId, user_id: userId }),
    });
    const j = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const corpo = res.ok
      ? { tentativa_id: texto(j.tentativa_id), qr: texto(j.qr), estado: texto(j.estado) }
      : { detail: texto(j.detail), error: texto(j.error), estado: texto(j.estado) };
    return NextResponse.json(corpo, { status: res.status, headers: SEM_CACHE });
  } catch {
    return NextResponse.json({ error: FORA_DO_AR }, { status: 502, headers: SEM_CACHE });
  }
}
