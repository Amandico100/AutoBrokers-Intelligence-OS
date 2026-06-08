import { NextRequest, NextResponse } from 'next/server';

import {
  resolveSessionCompany,
  getSupabaseAdmin,
  payloadHasSecret,
  isPlainObject,
  writeAudit,
  RISK_LEVELS,
  SECRET_REJECTION_MESSAGE,
} from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/** GET /api/vault/approvals — pedidos de aprovação da empresa (HITL). */
export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('approval_requests')
    .select('*')
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false })
    .limit(50);

  if (error) {
    console.error('[VAULT approvals list]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar aprovações' }, { status: 500 });
  }
  return NextResponse.json({ approvals: data || [] });
}

/** POST /api/vault/approvals — cria pedido de aprovação (status pending). */
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

  const actionType = typeof body.action_type === 'string' ? body.action_type : '';
  const subjectType = typeof body.subject_type === 'string' ? body.subject_type : '';
  if (!actionType || !subjectType) {
    return NextResponse.json(
      { error: 'action_type e subject_type são obrigatórios.' },
      { status: 400 },
    );
  }

  const supabase = getSupabaseAdmin();

  // Valida posse de referências opcionais (anti-IDOR).
  let tenantConnectionId: string | null = null;
  if (typeof body.tenant_connection_id === 'string' && body.tenant_connection_id) {
    const { data: conn } = await supabase
      .from('tenant_connections')
      .select('id')
      .eq('id', body.tenant_connection_id)
      .eq('company_id', ctx.companyId)
      .maybeSingle();
    if (!conn) return NextResponse.json({ error: 'Conexão inválida.' }, { status: 400 });
    tenantConnectionId = body.tenant_connection_id;
  }

  let permissionGrantId: string | null = null;
  if (typeof body.permission_grant_id === 'string' && body.permission_grant_id) {
    const { data: grant } = await supabase
      .from('permission_grants')
      .select('id')
      .eq('id', body.permission_grant_id)
      .eq('company_id', ctx.companyId)
      .maybeSingle();
    if (!grant) return NextResponse.json({ error: 'Permissão inválida.' }, { status: 400 });
    permissionGrantId = body.permission_grant_id;
  }

  const riskLevel =
    typeof body.risk_level === 'string' && (RISK_LEVELS as readonly string[]).includes(body.risk_level)
      ? body.risk_level
      : 'medium';

  const { data, error } = await supabase
    .from('approval_requests')
    .insert({
      company_id: ctx.companyId,
      tenant_connection_id: tenantConnectionId,
      permission_grant_id: permissionGrantId,
      subject_type: subjectType,
      subject_id: typeof body.subject_id === 'string' ? body.subject_id : null,
      action_type: actionType,
      status: 'pending',
      risk_level: riskLevel,
      preview: isPlainObject(body.preview) ? body.preview : {},
      request_payload: isPlainObject(body.request_payload) ? body.request_payload : {},
      requested_by_user_id: ctx.userId,
    })
    .select('*')
    .single();

  if (error) {
    console.error('[VAULT approvals create]', error.message);
    return NextResponse.json({ error: 'Erro ao criar pedido de aprovação.' }, { status: 500 });
  }

  await writeAudit(supabase, {
    company_id: ctx.companyId,
    tenant_connection_id: tenantConnectionId,
    approval_request_id: data.id,
    actor_user_id: ctx.userId,
    event_type: 'approval_requested',
    action: actionType,
    status: 'pending',
    risk_level: riskLevel,
  });

  return NextResponse.json({ approval: data }, { status: 201 });
}
