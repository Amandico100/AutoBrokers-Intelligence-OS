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
  // Visibilidade (SPEC-002 A3): oculta templates 'private' que não sejam da empresa da sessão.
  const templates = (data || []).filter((t) => {
    const dc = t.default_config && typeof t.default_config === 'object' ? (t.default_config as Record<string, unknown>) : {};
    const vis = dc.visibility && typeof dc.visibility === 'object' ? (dc.visibility as Record<string, unknown>) : null;
    if (!vis || vis.type !== 'private') return true;
    return vis.company_id === ctx.companyId;
  });
  return NextResponse.json({ templates });
}
