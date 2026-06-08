import { NextRequest, NextResponse } from 'next/server';

import {
  resolveSessionCompany,
  getSupabaseAdmin,
  payloadHasSecret,
  isPlainObject,
  writeAudit,
  CONNECTION_STATUSES,
  SECRET_REJECTION_MESSAGE,
} from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/** GET /api/vault/connections — conexões da empresa logada. */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('tenant_connections')
    .select('*')
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false });

  if (error) {
    console.error('[VAULT connections list]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar conexões' }, { status: 500 });
  }
  return NextResponse.json({ connections: data || [] });
}

/** POST /api/vault/connections — cria conexão da empresa (sem segredo). */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  if (payloadHasSecret(body)) {
    return NextResponse.json({ error: SECRET_REJECTION_MESSAGE }, { status: 400 });
  }

  const slug = typeof body.connector_template_slug === 'string' ? body.connector_template_slug : '';
  const name = typeof body.name === 'string' ? body.name.trim() : '';
  if (!slug || !name) {
    return NextResponse.json(
      { error: 'connector_template_slug e name são obrigatórios.' },
      { status: 400 },
    );
  }

  const status =
    typeof body.status === 'string' && (CONNECTION_STATUSES as readonly string[]).includes(body.status)
      ? body.status
      : 'draft';

  const supabase = getSupabaseAdmin();

  const { data: tpl, error: tplError } = await supabase
    .from('connector_templates')
    .select('id, slug, is_active, risk_level')
    .eq('slug', slug)
    .eq('is_active', true)
    .maybeSingle();

  if (tplError) {
    console.error('[VAULT connections create] template lookup', tplError.message);
    return NextResponse.json({ error: 'Erro ao validar template.' }, { status: 500 });
  }
  if (!tpl) {
    return NextResponse.json({ error: 'Template de conector inválido ou inativo.' }, { status: 400 });
  }

  const insert = {
    company_id: ctx.companyId,
    connector_template_id: tpl.id,
    name,
    status,
    health_status: 'unknown',
    technical_ref_type:
      typeof body.technical_ref_type === 'string' ? body.technical_ref_type : null,
    technical_ref_id: typeof body.technical_ref_id === 'string' ? body.technical_ref_id : null,
    connection_config: isPlainObject(body.connection_config) ? body.connection_config : {},
    metadata: isPlainObject(body.metadata) ? body.metadata : {},
    owner_user_id: ctx.userId,
  };

  const { data, error } = await supabase
    .from('tenant_connections')
    .insert(insert)
    .select('*')
    .single();

  if (error) {
    console.error('[VAULT connections create]', error.message);
    return NextResponse.json({ error: 'Erro ao criar conexão.' }, { status: 500 });
  }

  await writeAudit(supabase, {
    company_id: ctx.companyId,
    tenant_connection_id: data.id,
    actor_user_id: ctx.userId,
    event_type: 'connection_created',
    action: `template=${slug}`,
    status,
    risk_level: tpl.risk_level,
  });

  return NextResponse.json({ connection: data }, { status: 201 });
}
