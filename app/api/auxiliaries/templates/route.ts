import { NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

/** GET /api/auxiliaries/templates — templates ativos do catálogo global. */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('auxiliary_templates')
    .select('*')
    .eq('is_active', true);

  if (error) {
    console.error('[AUXILIARIES templates]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar templates' }, { status: 500 });
  }
  return NextResponse.json({ templates: data || [] });
}
