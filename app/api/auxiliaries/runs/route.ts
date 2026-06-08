import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

/** GET /api/auxiliaries/runs — execuções da empresa, mais recentes primeiro. */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('auxiliary_runs')
    .select('*')
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false })
    .limit(50);

  if (error) {
    console.error('[AUXILIARIES runs]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar execuções' }, { status: 500 });
  }
  return NextResponse.json({ runs: data || [] });
}
