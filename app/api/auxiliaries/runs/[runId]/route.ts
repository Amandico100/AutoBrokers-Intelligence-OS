import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

/** GET /api/auxiliaries/runs/[runId] — execução específica, escopada por empresa (anti-IDOR). */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const { runId } = await params;

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('auxiliary_runs')
    .select('*')
    .eq('id', runId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();

  if (error) {
    console.error('[AUXILIARIES run detail]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar execução' }, { status: 500 });
  }
  if (!data) {
    return NextResponse.json({ error: 'Execução não encontrada' }, { status: 404 });
  }
  return NextResponse.json({ run: data });
}
