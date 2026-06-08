import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

/** GET /api/auxiliaries/installed — Auxiliares instalados da empresa do usuário. */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('tenant_auxiliaries')
    .select('*')
    .eq('company_id', ctx.companyId);

  if (error) {
    console.error('[AUXILIARIES installed]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar Auxiliares instalados' }, { status: 500 });
  }
  return NextResponse.json({ installed: data || [] });
}
