import { NextResponse } from 'next/server';

import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-0-B2 L3 — o QR da linha do usuário, lido de novo pela tela a cada 4 s enquanto a pessoa aponta o celular.
 *
 * GET → { qr: "data:image/png;base64,…" | null, estado }
 *
 * 🔴 `company_id` e `user_id` vêm SEMPRE da sessão — o pedido não é lido (nem query, nem corpo): o QR de uma pessoa
 *    nunca chega a outra.
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

export async function GET() {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const { companyId, userId } = auth.ctx;
  const qs = new URLSearchParams({ company_id: companyId, user_id: userId });
  try {
    const res = await fetch(`${getBackendUrl()}/api/linha-do-usuario/qr?${qs.toString()}`, {
      method: 'GET',
      headers: backendHeaders(),
      cache: 'no-store',
    });
    const j = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const corpo = res.ok
      ? { qr: texto(j.qr), estado: texto(j.estado) }
      : { detail: texto(j.detail), error: texto(j.error), estado: texto(j.estado) };
    return NextResponse.json(corpo, { status: res.status, headers: SEM_CACHE });
  } catch {
    return NextResponse.json({ error: FORA_DO_AR }, { status: 502, headers: SEM_CACHE });
  }
}
