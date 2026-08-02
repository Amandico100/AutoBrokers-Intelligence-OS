// SPEC-064 Bloco C/D — o catálogo de Auxiliares desta corretora.
//
// O catálogo é GLOBAL: Resulta, AutoFleet, Amandus e as próximas veem os
// mesmos Auxiliares. O que muda por corretora é o que ela ligou, o que ela
// conectou e como ela personalizou.
//
// Antes esta rota devolvia `listTenantAuxiliaries`, que não lia nenhum dos
// campos de catálogo (headline, categorias, estado, conectores exigidos) — a
// tela recebia nome e descrição técnica e não tinha como mostrar o que o
// corretor ganha nem por que não dá para ligar.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { catalogoDaCorretora } from '@/lib/auxiliaries/catalog';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const out = await catalogoDaCorretora(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out);
}
