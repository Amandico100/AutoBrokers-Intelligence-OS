import { NextRequest, NextResponse } from 'next/server';

import {
  resolveSessionCompany,
  getSupabaseAdmin,
  payloadHasSecret,
  isPlainObject,
  writeAudit,
  CONNECTION_STATUSES,
  HEALTH_STATUSES,
  SECRET_REJECTION_MESSAGE,
} from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/** GET /api/vault/connections/[connectionId] — conexão da empresa (escopada). */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  const { connectionId } = await params;
  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from('tenant_connections')
    .select('*')
    .eq('id', connectionId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();

  if (error) {
    console.error('[VAULT connection get]', error.message);
    return NextResponse.json({ error: 'Erro ao buscar conexão' }, { status: 500 });
  }
  if (!data) return NextResponse.json({ error: 'Conexão não encontrada' }, { status: 404 });
  return NextResponse.json({ connection: data });
}

/** PATCH /api/vault/connections/[connectionId] — atualiza campos seguros. */
export async function PATCH(req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
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

  const supabase = getSupabaseAdmin();

  // Confirma posse antes de atualizar (anti-IDOR).
  const { data: existing } = await supabase
    .from('tenant_connections')
    .select('id')
    .eq('id', connectionId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (!existing) return NextResponse.json({ error: 'Conexão não encontrada' }, { status: 404 });

  const patch: Record<string, unknown> = {};
  if (typeof body.name === 'string') patch.name = body.name.trim();
  if (typeof body.status === 'string') {
    if (!(CONNECTION_STATUSES as readonly string[]).includes(body.status)) {
      return NextResponse.json({ error: 'status inválido.' }, { status: 400 });
    }
    patch.status = body.status;
  }
  if (typeof body.health_status === 'string') {
    if (!(HEALTH_STATUSES as readonly string[]).includes(body.health_status)) {
      return NextResponse.json({ error: 'health_status inválido.' }, { status: 400 });
    }
    patch.health_status = body.health_status;
  }
  if (isPlainObject(body.connection_config)) patch.connection_config = body.connection_config;
  if (isPlainObject(body.metadata)) patch.metadata = body.metadata;

  if (Object.keys(patch).length === 0) {
    return NextResponse.json({ error: 'Nenhum campo válido para atualizar.' }, { status: 400 });
  }

  const { data, error } = await supabase
    .from('tenant_connections')
    .update(patch)
    .eq('id', connectionId)
    .eq('company_id', ctx.companyId)
    .select('*')
    .single();

  if (error) {
    console.error('[VAULT connection patch]', error.message);
    return NextResponse.json({ error: 'Erro ao atualizar conexão.' }, { status: 500 });
  }

  await writeAudit(supabase, {
    company_id: ctx.companyId,
    tenant_connection_id: connectionId,
    actor_user_id: ctx.userId,
    event_type: 'connection_updated',
    action: Object.keys(patch).join(','),
    status: typeof patch.status === 'string' ? patch.status : null,
  });

  return NextResponse.json({ connection: data });
}

/**
 * DELETE /api/vault/connections/[connectionId]  (C-FIX-2)
 * mode: 'archive' (preserva histórico, some da lista ativa) |
 *       'disconnect' (remove segredo, status disconnected) |
 *       'delete' (hard-delete SOMENTE rascunho vazio: sem segredo, sem permissões, sem aprovações).
 */
export async function DELETE(req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const { connectionId } = await params;
  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { body = {}; }
  const mode = typeof body.mode === 'string' ? body.mode : 'archive';

  const supabase = getSupabaseAdmin();
  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id, status, encrypted_secret_ref, metadata')
    .eq('id', connectionId).eq('company_id', ctx.companyId).maybeSingle();
  if (!conn) return NextResponse.json({ error: 'Conexão não encontrada' }, { status: 404 });

  const nowIso = new Date().toISOString();

  if (mode === 'disconnect') {
    const { error } = await supabase.from('tenant_connections')
      .update({ encrypted_secret_ref: null, status: 'disconnected', health_status: 'unknown', updated_at: nowIso })
      .eq('id', connectionId).eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao desconectar.' }, { status: 500 });
    await writeAudit(supabase, { company_id: ctx.companyId, tenant_connection_id: connectionId, actor_user_id: ctx.userId, event_type: 'connection_revoked', action: 'disconnect', status: 'disconnected' });
    return NextResponse.json({ ok: true, status: 'disconnected' });
  }

  if (mode === 'delete') {
    // Só permite hard-delete de rascunho vazio: sem segredo, sem permissões, sem aprovações.
    if (conn.encrypted_secret_ref) {
      return NextResponse.json({ error: 'Esta conexão tem credencial salva. Use Desconectar ou Arquivar.' }, { status: 409 });
    }
    const { count: grants } = await supabase.from('permission_grants').select('id', { count: 'exact', head: true }).eq('tenant_connection_id', connectionId);
    const { count: approvals } = await supabase.from('approval_requests').select('id', { count: 'exact', head: true }).eq('tenant_connection_id', connectionId);
    if ((grants ?? 0) > 0 || (approvals ?? 0) > 0) {
      return NextResponse.json({ error: 'Esta conexão tem histórico/permissões. Arquive em vez de excluir.' }, { status: 409 });
    }
    const { error } = await supabase.from('tenant_connections').delete().eq('id', connectionId).eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao excluir rascunho.' }, { status: 500 });
    return NextResponse.json({ ok: true, deleted: true });
  }

  // default: archive (preserva histórico)
  const meta = (conn.metadata && typeof conn.metadata === 'object' && !Array.isArray(conn.metadata)) ? { ...(conn.metadata as Record<string, unknown>) } : {};
  meta.archived = { at: nowIso, by: ctx.userId };
  const { error } = await supabase.from('tenant_connections')
    .update({ status: 'archived', metadata: meta, updated_at: nowIso })
    .eq('id', connectionId).eq('company_id', ctx.companyId);
  if (error) return NextResponse.json({ error: 'Erro ao arquivar.' }, { status: 500 });
  await writeAudit(supabase, { company_id: ctx.companyId, tenant_connection_id: connectionId, actor_user_id: ctx.userId, event_type: 'connection_updated', action: 'archive', status: 'archived' });
  return NextResponse.json({ ok: true, status: 'archived' });
}
