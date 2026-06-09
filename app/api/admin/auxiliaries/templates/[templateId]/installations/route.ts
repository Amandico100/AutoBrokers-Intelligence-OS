import { NextRequest, NextResponse } from 'next/server';

import { getAdminSupabase, hasAdminCookie } from '@/lib/admin/factory';

export const dynamic = 'force-dynamic';

/** GET /api/admin/auxiliaries/templates/[templateId]/installations — corretoras com este template. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { templateId } = await params;

  const supabase = getAdminSupabase();
  const { data: rows, error } = await supabase
    .from('tenant_auxiliaries')
    .select('*')
    .eq('template_id', templateId);
  if (error) {
    console.error('[ADMIN AUX installations]', error.message);
    return NextResponse.json({ error: 'Erro ao listar instalações' }, { status: 500 });
  }

  const list = rows || [];
  const companyIds = Array.from(
    new Set(list.map((r) => (typeof r.company_id === 'string' ? r.company_id : '')).filter(Boolean)),
  );
  const nameById: Record<string, string> = {};
  if (companyIds.length > 0) {
    const { data: comps } = await supabase
      .from('companies')
      .select('id, company_name')
      .in('id', companyIds);
    for (const c of comps || []) nameById[c.id] = c.company_name || c.id;
  }

  const installations = list.map((r) => ({
    id: r.id,
    company_id: r.company_id,
    company_name: nameById[r.company_id as string] || (r.company_id as string),
    status: r.status,
    created_at: r.created_at ?? null,
  }));

  return NextResponse.json({ installations });
}
