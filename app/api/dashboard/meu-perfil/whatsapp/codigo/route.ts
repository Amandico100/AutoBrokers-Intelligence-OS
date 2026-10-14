import { NextRequest, NextResponse } from 'next/server';

import { assertSameOrigin, requireCompanyMember } from '@/lib/admin/admin-auth';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-132-C C1 (D-132C-02) — "Usar o AutoBrokers pelo WhatsApp": o código de 6 dígitos que a PRÓPRIA pessoa manda do
 * celular dela ao número do AutoBrokers ("ATIVAR 123456"). Quem prova a posse é quem manda: nada é enviado antes.
 *
 * POST → { ok, codigo, texto, expira_em, validade_minutos, wa_me_url | null, numero_assistente | null }
 *
 * 🔴 `company_id` e `user_id` vêm SEMPRE da sessão — nunca do corpo (o código vincula o membro DA SESSÃO).
 * ⛔ O código nunca vai para log; só o hash fica no banco (o backend calcula).
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  const { companyId, userId } = auth.ctx;
  try {
    const res = await fetch(`${getBackendUrl()}/api/contas-da-corretora/perfil/whatsapp-de-trabalho/codigo`, {
      method: 'POST',
      headers: backendHeaders(),
      cache: 'no-store',
      body: JSON.stringify({ company_id: companyId, user_id: userId, por_user_id: userId }),
    });
    const j = await res.json().catch(() => ({}));
    return NextResponse.json(j, { status: res.status, headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
