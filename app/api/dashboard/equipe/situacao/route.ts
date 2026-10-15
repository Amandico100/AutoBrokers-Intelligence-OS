import { NextResponse } from 'next/server';

import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * SPEC-131-B G3 — a coluna SITUAÇÃO de Personalização → Equipe (D-131-07, revê D-131-0-06): de cada pessoa ATIVA, o
 * Agger (conectado? senha recusada? falta?), o WhatsApp de trabalho (conectado, informado ou não — o NÚMERO não sai) e a ausência
 * ativa. Cada pessoa conecta SÓ o próprio Agger, em Meu perfil; o admin VÊ quem falta e pede para conectar — nunca
 * digita o login de outra pessoa.
 *
 * GET → { pessoas: [{ user_id, nome, primeiro_nome, funcoes, agger: {situacao, rotulo, conectado},
 *                     whatsapp_trabalho_confirmado: boolean | null,
 *                     whatsapp_trabalho_origem: 'linha' | 'digitado' | null, ausencia: {ate, substituto} | null }] }
 *       (SPEC-131-0-B3: a origem diz se a pessoa CONECTOU o WhatsApp ou só informou o número; o BFF repassa sem
 *        inventar, e o número continua sem sair)
 *
 * 🔴 Só o papel administrativo DA corretora ativa lê (a mesma régua de escrever a configuração). `company_id` da sessão.
 */
function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

export async function GET() {
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });
  try {
    const res = await fetch(
      `${getBackendUrl()}/api/contas-da-corretora/equipe/situacao?company_id=${encodeURIComponent(auth.ctx.companyId)}`,
      { headers: backendHeaders(), cache: 'no-store' },
    );
    const j = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json(j, { status: res.status });
    return NextResponse.json({ ...j, eu: auth.ctx.userId });
  } catch {
    return NextResponse.json({ error: 'Backend indisponível' }, { status: 502 });
  }
}
