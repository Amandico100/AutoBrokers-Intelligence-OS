import { NextRequest, NextResponse } from 'next/server';

import {
  getAdminSupabase,
  hasAdminCookie,
  getTableColumns,
  pickColumns,
  parseJsonField,
  TEMPLATE_FALLBACK_COLS,
} from '@/lib/admin/factory';

export const dynamic = 'force-dynamic';

/** GET /api/admin/auxiliaries/templates/[templateId] — um template. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { templateId } = await params;

  const supabase = getAdminSupabase();
  const { data, error } = await supabase.from('auxiliary_templates').select('*').eq('id', templateId).maybeSingle();
  if (error) return NextResponse.json({ error: 'Erro ao buscar template' }, { status: 500 });
  if (!data) return NextResponse.json({ error: 'Template não encontrado' }, { status: 404 });
  return NextResponse.json({ template: data });
}

/**
 * PATCH /api/admin/auxiliaries/templates/[templateId]
 * Atualiza textos/flags/JSON. O slug é IMUTÁVEL (evita quebrar instalações por slug).
 */
export async function PATCH(req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { templateId } = await params;

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const jsonFields = ['default_config', 'permissions', 'input_schema', 'output_schema'] as const;
  const parsedJson: Record<string, unknown> = {};
  for (const f of jsonFields) {
    if (body[f] === undefined) continue;
    const r = parseJsonField(body[f], f);
    if (r.error) return NextResponse.json({ error: r.error }, { status: 400 });
    parsedJson[f] = r.value ?? {};
  }

  const supabase = getAdminSupabase();

  // Constrói candidate só com os campos enviados (não sobrescreve o que não veio). Slug nunca entra.
  const candidate: Record<string, unknown> = {};
  const strFields = [
    'name',
    'description',
    'short_description',
    'category',
    'icon',
    'status',
    'execution_mode',
    'trigger_type',
    'system_prompt',
  ];
  for (const f of strFields) {
    if (typeof body[f] === 'string') candidate[f] = (body[f] as string).trim() || null;
  }
  for (const f of ['requires_human_approval', 'uses_external_actions', 'is_active']) {
    if (typeof body[f] === 'boolean') candidate[f] = body[f];
  }
  for (const f of jsonFields) {
    if (f in parsedJson) candidate[f] = parsedJson[f];
  }

  if (Object.keys(candidate).length === 0) {
    return NextResponse.json({ error: 'Nada para atualizar.' }, { status: 400 });
  }

  const cols = await getTableColumns(supabase, 'auxiliary_templates', TEMPLATE_FALLBACK_COLS);
  const record = pickColumns(candidate, cols);

  const { data, error } = await supabase
    .from('auxiliary_templates')
    .update(record)
    .eq('id', templateId)
    .select()
    .single();
  if (error) {
    console.error('[ADMIN AUX templates] update', error.message);
    return NextResponse.json({ error: `Erro ao atualizar template (${error.code || 'db'}).` }, { status: 500 });
  }
  return NextResponse.json({ template: data, persisted: Object.keys(record) });
}
