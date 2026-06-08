import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin, writeAudit } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * POST /api/vault/connections/[connectionId]/whatsapp/configure
 * Secret Flow seguro: recebe credenciais, delega ao backend (que cifra e grava em integrations),
 * e atualiza a tenant_connection para referenciar a integração. O token NUNCA fica no Next.
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ success: false, error: 'Não autorizado' }, { status: 401 });

  const { connectionId } = await params;

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    console.error('[VAULT whatsapp configure] internal key not configured');
    return NextResponse.json({ success: false, error: 'Chave interna do backend não configurada.' }, { status: 500 });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const identifier = typeof body.identifier === 'string' ? body.identifier.trim() : '';
  const instanceId = typeof body.instance_id === 'string' ? body.instance_id.trim() : '';
  const token = typeof body.token === 'string' ? body.token.trim() : '';
  const clientToken = typeof body.client_token === 'string' && body.client_token.trim() ? body.client_token.trim() : null;
  const baseUrl = typeof body.base_url === 'string' && body.base_url.trim() ? body.base_url.trim() : undefined;

  if (!identifier || !instanceId || !token) {
    return NextResponse.json(
      { success: false, error: 'Telefone, Instance ID e Token são obrigatórios.' },
      { status: 400 },
    );
  }

  const supabase = getSupabaseAdmin();

  // Conexão pertence à empresa?
  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id, connector_template_id, company_id')
    .eq('id', connectionId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (!conn) return NextResponse.json({ success: false, error: 'Conexão não encontrada' }, { status: 404 });

  // É template de WhatsApp?
  const { data: tpl } = await supabase
    .from('connector_templates')
    .select('slug')
    .eq('id', conn.connector_template_id)
    .maybeSingle();
  if (!tpl || tpl.slug !== 'whatsapp_zapi') {
    return NextResponse.json({ success: false, error: 'Esta conexão não é do tipo WhatsApp.' }, { status: 400 });
  }

  // Resolve agente (do payload, validado, ou o agente principal da empresa).
  let agentId: string | null =
    typeof body.agent_id === 'string' && body.agent_id ? body.agent_id : null;
  if (agentId) {
    const { data: ag } = await supabase
      .from('agents')
      .select('id')
      .eq('id', agentId)
      .eq('company_id', ctx.companyId)
      .maybeSingle();
    if (!ag) return NextResponse.json({ success: false, error: 'Agente inválido.' }, { status: 400 });
  } else {
    const { data: ags } = await supabase
      .from('agents')
      .select('id, is_subagent, allow_direct_chat')
      .eq('company_id', ctx.companyId)
      .eq('is_active', true)
      .order('created_at', { ascending: true });
    const primary = (ags || []).find((a) => !a.is_subagent || a.allow_direct_chat);
    agentId = primary?.id || null;
  }
  if (!agentId) {
    return NextResponse.json(
      { success: false, error: 'Nenhum agente ativo para vincular o WhatsApp.' },
      { status: 400 },
    );
  }

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json({ success: false, error: 'Backend de IA não configurado.' }, { status: 500 });
    }
    throw error;
  }

  try {
    const res = await fetch(`${backendUrl}/api/whatsapp-integrations/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: ctx.companyId,
        agent_id: agentId,
        provider: 'z-api',
        identifier,
        instance_id: instanceId,
        token,
        client_token: clientToken,
        base_url: baseUrl,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data?.integration) {
      return NextResponse.json(
        { success: false, error: data?.detail || data?.error || 'Falha ao configurar a conexão.' },
        { status: res.status || 500 },
      );
    }

    const integration = data.integration as Record<string, unknown>;
    const identifierMasked = typeof integration.identifier_masked === 'string' ? integration.identifier_masked : '';

    const { data: updated } = await supabase
      .from('tenant_connections')
      .update({
        technical_ref_type: 'integration',
        technical_ref_id: integration.id,
        status: 'connected',
        health_status: 'unknown',
        connection_config: {
          provider: 'z-api',
          identifier_last4: identifierMasked.replace('...', ''),
          has_client_token: Boolean(integration.has_client_token),
        },
        metadata: { configured_via: 'vault', safe_secret_flow: true },
        updated_at: new Date().toISOString(),
      })
      .eq('id', connectionId)
      .eq('company_id', ctx.companyId)
      .select('*')
      .single();

    await writeAudit(supabase, {
      company_id: ctx.companyId,
      tenant_connection_id: connectionId,
      actor_user_id: ctx.userId,
      event_type: 'whatsapp_configured',
      action: 'configure_zapi',
      status: 'connected',
      risk_level: 'high',
      metadata: { provider: 'z-api' },
    });

    return NextResponse.json({ success: true, connection: updated });
  } catch (error) {
    console.error('[VAULT whatsapp configure] proxy error', error);
    return NextResponse.json({ success: false, error: 'Falha ao conectar ao backend.' }, { status: 500 });
  }
}
