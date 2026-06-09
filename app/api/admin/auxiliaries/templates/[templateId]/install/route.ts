import { NextRequest, NextResponse } from 'next/server';

import {
  getAdminSupabase,
  hasAdminCookie,
  getTableColumns,
  pickColumns,
  parseJsonField,
  TENANT_FALLBACK_COLS,
} from '@/lib/admin/factory';

export const dynamic = 'force-dynamic';

/**
 * POST /api/admin/auxiliaries/templates/[templateId]/install
 * Instala o template em uma corretora (cria tenant_auxiliaries). Idempotente por (company, slug).
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { templateId } = await params;

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const companyId = typeof body.companyId === 'string' ? body.companyId.trim() : '';
  if (!companyId) return NextResponse.json({ error: 'Selecione uma corretora.' }, { status: 400 });

  const cfg = parseJsonField(body.config, 'config');
  if (cfg.error) return NextResponse.json({ error: cfg.error }, { status: 400 });
  const perms = parseJsonField(body.permissions, 'permissions');
  if (perms.error) return NextResponse.json({ error: perms.error }, { status: 400 });

  const supabase = getAdminSupabase();

  const { data: template } = await supabase
    .from('auxiliary_templates')
    .select('id, slug, name')
    .eq('id', templateId)
    .maybeSingle();
  if (!template) return NextResponse.json({ error: 'Template não encontrado' }, { status: 404 });

  const { data: company } = await supabase
    .from('companies')
    .select('id, company_name')
    .eq('id', companyId)
    .maybeSingle();
  if (!company) return NextResponse.json({ error: 'Corretora não encontrada' }, { status: 404 });

  // Dedupe por (company_id, slug).
  const { data: dup } = await supabase
    .from('tenant_auxiliaries')
    .select('id, status')
    .eq('company_id', companyId)
    .eq('slug', template.slug)
    .limit(1);
  if (dup && dup.length > 0) {
    return NextResponse.json({ installed: dup[0], already: true });
  }

  const displayName = (typeof body.name === 'string' && body.name.trim()) || template.name;
  const candidate: Record<string, unknown> = {
    company_id: companyId,
    template_id: templateId,
    slug: template.slug,
    name: displayName,
    display_name: displayName,
    status: typeof body.status === 'string' && body.status.trim() ? body.status.trim() : 'active',
    config: cfg.value ?? {},
    permissions: perms.value ?? {},
  };

  const cols = await getTableColumns(supabase, 'tenant_auxiliaries', TENANT_FALLBACK_COLS);
  const record = pickColumns(candidate, cols);

  const { data, error } = await supabase.from('tenant_auxiliaries').insert([record]).select().single();
  if (error) {
    console.error('[ADMIN AUX install]', error.message);
    return NextResponse.json({ error: `Erro ao instalar (${error.code || 'db'}).` }, { status: 500 });
  }
  return NextResponse.json({ installed: data, already: false }, { status: 201 });
}
