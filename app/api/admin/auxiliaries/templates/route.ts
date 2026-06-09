import { NextRequest, NextResponse } from 'next/server';

import {
  getAdminSupabase,
  hasAdminCookie,
  getTableColumns,
  pickColumns,
  parseJsonField,
  TEMPLATE_FALLBACK_COLS,
  SLUG_RE,
} from '@/lib/admin/factory';

export const dynamic = 'force-dynamic';

/** GET /api/admin/auxiliaries/templates — lista todos os templates globais (ativos e inativos). */
export async function GET() {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const supabase = getAdminSupabase();
  let res = await supabase.from('auxiliary_templates').select('*').order('created_at', { ascending: true });
  if (res.error) res = await supabase.from('auxiliary_templates').select('*');
  if (res.error) {
    console.error('[ADMIN AUX templates] list', res.error.message);
    return NextResponse.json({ error: 'Erro ao listar templates' }, { status: 500 });
  }
  return NextResponse.json({ templates: res.data || [] });
}

/** POST /api/admin/auxiliaries/templates — cria um template global (resiliente ao schema). */
export async function POST(req: NextRequest) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const s = (k: string) => (typeof body[k] === 'string' ? (body[k] as string).trim() : '');
  const slug = s('slug').toLowerCase();
  const name = s('name');
  if (!name) return NextResponse.json({ error: 'Nome é obrigatório.' }, { status: 400 });
  if (!slug || !SLUG_RE.test(slug)) {
    return NextResponse.json({ error: 'Slug inválido. Use minúsculas e hífens (ex.: meu-auxiliar).' }, { status: 400 });
  }

  // Validação de campos JSON.
  const jsonFields = ['default_config', 'permissions', 'input_schema', 'output_schema'] as const;
  const parsed: Record<string, unknown> = {};
  for (const f of jsonFields) {
    const r = parseJsonField(body[f], f);
    if (r.error) return NextResponse.json({ error: r.error }, { status: 400 });
    parsed[f] = r.value ?? {};
  }

  const supabase = getAdminSupabase();

  // Slug único.
  const { data: existing } = await supabase
    .from('auxiliary_templates')
    .select('id')
    .eq('slug', slug)
    .limit(1);
  if (existing && existing.length > 0) {
    return NextResponse.json({ error: 'Já existe um template com este slug.' }, { status: 409 });
  }

  const candidate: Record<string, unknown> = {
    slug,
    name,
    description: s('description') || null,
    short_description: s('short_description') || null,
    category: s('category') || null,
    icon: s('icon') || null,
    status: s('status') || 'active',
    execution_mode: s('execution_mode') || 'manual',
    trigger_type: s('trigger_type') || 'manual',
    requires_human_approval: typeof body.requires_human_approval === 'boolean' ? body.requires_human_approval : true,
    uses_external_actions: typeof body.uses_external_actions === 'boolean' ? body.uses_external_actions : false,
    system_prompt: s('system_prompt') || null,
    version: 1,
    is_active: typeof body.is_active === 'boolean' ? body.is_active : true,
    default_config: parsed.default_config,
    permissions: parsed.permissions,
    input_schema: parsed.input_schema,
    output_schema: parsed.output_schema,
  };

  const cols = await getTableColumns(supabase, 'auxiliary_templates', TEMPLATE_FALLBACK_COLS);
  const record = pickColumns(candidate, cols);

  const { data, error } = await supabase.from('auxiliary_templates').insert([record]).select().single();
  if (error) {
    console.error('[ADMIN AUX templates] create', error.message);
    return NextResponse.json({ error: `Erro ao criar template (${error.code || 'db'}).` }, { status: 500 });
  }
  return NextResponse.json({ template: data, persisted: Object.keys(record) }, { status: 201 });
}
