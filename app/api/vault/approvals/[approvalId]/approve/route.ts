import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin, writeAudit } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/** POST /api/vault/approvals/[approvalId]/approve — aprova um pedido pending. */
export async function POST(req: NextRequest, { params }: { params: Promise<{ approvalId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const { approvalId } = await params;

  let reason: string | undefined;
  try {
    const body = await req.json();
    if (body && typeof body.reason === 'string') reason = body.reason;
  } catch {
    reason = undefined;
  }

  const supabase = getSupabaseAdmin();

  const { data: ar } = await supabase
    .from('approval_requests')
    .select('id, status, tenant_connection_id, risk_level, action_type')
    .eq('id', approvalId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();

  if (!ar) return NextResponse.json({ error: 'Pedido de aprovação não encontrado' }, { status: 404 });
  if (ar.status !== 'pending') {
    return NextResponse.json(
      { error: 'Apenas pedidos pendentes podem ser aprovados.' },
      { status: 409 },
    );
  }

  const { data, error } = await supabase
    .from('approval_requests')
    .update({
      status: 'approved',
      approved_by_user_id: ctx.userId,
      approved_at: new Date().toISOString(),
      approval_result: { approved_by: ctx.userId, reason: reason ?? null },
    })
    .eq('id', approvalId)
    .eq('company_id', ctx.companyId)
    .eq('status', 'pending')
    .select('*')
    .single();

  if (error) {
    console.error('[VAULT approval approve]', error.message);
    return NextResponse.json({ error: 'Erro ao aprovar pedido.' }, { status: 500 });
  }

  await writeAudit(supabase, {
    company_id: ctx.companyId,
    tenant_connection_id: ar.tenant_connection_id ?? null,
    approval_request_id: approvalId,
    actor_user_id: ctx.userId,
    event_type: 'approval_approved',
    action: ar.action_type ?? null,
    status: 'approved',
    risk_level: ar.risk_level ?? null,
  });

  return NextResponse.json({ approval: data });
}
