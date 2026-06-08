import { NextRequest, NextResponse } from 'next/server';
import type { SupabaseClient } from '@supabase/supabase-js';

import {
  resolveSessionCompany,
  getSupabaseAdmin,
  payloadHasSecret,
  writeAudit,
  RISK_LEVELS,
  SECRET_REJECTION_MESSAGE,
} from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

async function ownsConnection(supabase: SupabaseClient, companyId: string, connectionId: string) {
  const { data } = await supabase
    .from('tenant_connections')
    .select('id')
    .eq('id', connectionId)
    .eq('company_id', companyId)
    .maybeSingle();
  return Boolean(data);
}

/** GET — lista permission_grants da conexão (escopada por empresa). */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const { connectionId } = await params;
  const supabase = getSupabaseAdmin();
  if (!(await ownsConnection(supabase, ctx.companyId, connectionId))) {
    return NextResponse.json({ error: 'Conexão não encontrada' }, { status: 404 });
  }

  const { data, error } = await supabase
    .from('permission_grants')
    .select('*')
    .eq('tenant_connection_id', connectionId)
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false });

  if (error) {
    console.error('[VAULT permissions list]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar permissões' }, { status: 500 });
  }
  return NextResponse.json({ permissions: data || [] });
}

/** POST — cria permission_grant para a conexão. */
export async function POST(req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const { connectionId } = await params;

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  if (payloadHasSecret(body)) {
    return NextResponse.json({ error: SECRET_REJECTION_MESSAGE }, { status: 400 });
  }

  const subjectType = typeof body.subject_type === 'string' ? body.subject_type : '';
  if (!subjectType) {
    return NextResponse.json({ error: 'subject_type é obrigatório.' }, { status: 400 });
  }

  const supabase = getSupabaseAdmin();
  if (!(await ownsConnection(supabase, ctx.companyId, connectionId))) {
    return NextResponse.json({ error: 'Conexão não encontrada' }, { status: 404 });
  }

  const allowedActions = Array.isArray(body.allowed_actions)
    ? body.allowed_actions.filter((a): a is string => typeof a === 'string')
    : [];
  const riskLevel =
    typeof body.risk_level === 'string' && (RISK_LEVELS as readonly string[]).includes(body.risk_level)
      ? body.risk_level
      : 'medium';
  const requiresApproval = typeof body.requires_approval === 'boolean' ? body.requires_approval : true;
  const subjectId = typeof body.subject_id === 'string' ? body.subject_id : null;

  const { data, error } = await supabase
    .from('permission_grants')
    .insert({
      company_id: ctx.companyId,
      tenant_connection_id: connectionId,
      subject_type: subjectType,
      subject_id: subjectId,
      allowed_actions: allowedActions,
      requires_approval: requiresApproval,
      risk_level: riskLevel,
      status: 'active',
      created_by_user_id: ctx.userId,
    })
    .select('*')
    .single();

  if (error) {
    console.error('[VAULT permissions create]', error.message);
    return NextResponse.json({ error: 'Erro ao criar permissão.' }, { status: 500 });
  }

  await writeAudit(supabase, {
    company_id: ctx.companyId,
    tenant_connection_id: connectionId,
    actor_user_id: ctx.userId,
    event_type: 'permission_granted',
    action: `${subjectType}:${allowedActions.join('|')}`,
    risk_level: riskLevel,
  });

  return NextResponse.json({ permission: data }, { status: 201 });
}
