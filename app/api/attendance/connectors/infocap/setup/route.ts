import { NextRequest, NextResponse } from 'next/server';

import {
  resolveSessionCompany,
  getSupabaseAdmin,
  writeAudit,
  payloadHasSecret,
  SECRET_REJECTION_MESSAGE,
} from '@/lib/vault/server';
import { diagnoseInfocapConnection } from '@/lib/attendance/connectors/infocap-policy-lookup';

export const dynamic = 'force-dynamic';

const INFOCAP_SLUG = 'infocap';

/**
 * POST /api/attendance/connectors/infocap/setup
 *
 * Ativa/valida a conexão InfoCap EXISTENTE da corretora, atualizando apenas
 * METADADOS NÃO-SECRETOS (connection_config.base_url) e movendo o status para
 * 'configuring'. NÃO recebe nem grava login/senha/token (rejeita segredo no body)
 * e NÃO cria encrypted_secret_ref, porque ainda NÃO existe um fluxo seguro de
 * segredo para InfoCap (ver relatório 42I2.0B). Não faz chamada real ao InfoCap.
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  // Defesa: nunca aceitar login/senha/token/api_key/secret no corpo.
  if (payloadHasSecret(body)) {
    return NextResponse.json({ ok: false, error: SECRET_REJECTION_MESSAGE }, { status: 400 });
  }

  const baseUrl = typeof body.base_url === 'string' ? body.base_url.trim() : '';
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    return NextResponse.json({ ok: false, error: 'base_url inválida (use http(s)://...)' }, { status: 400 });
  }

  const supabase = getSupabaseAdmin();

  // Template global InfoCap
  const { data: tpl } = await supabase
    .from('connector_templates')
    .select('id')
    .eq('slug', INFOCAP_SLUG)
    .eq('is_active', true)
    .maybeSingle();
  if (!tpl?.id) {
    return NextResponse.json({ ok: false, error: 'Template InfoCap não encontrado/ativo.' }, { status: 404 });
  }

  // Conexão existente da corretora
  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id, status, connection_config')
    .eq('company_id', ctx.companyId)
    .eq('connector_template_id', tpl.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!conn?.id) {
    return NextResponse.json(
      { ok: false, error: 'Conexão InfoCap não encontrada. Crie a conexão no Vault antes de configurar.' },
      { status: 404 },
    );
  }

  // Atualiza apenas metadados não-secretos.
  const prevConfig =
    conn.connection_config && typeof conn.connection_config === 'object' && !Array.isArray(conn.connection_config)
      ? (conn.connection_config as Record<string, unknown>)
      : {};
  const newConfig = baseUrl ? { ...prevConfig, base_url: baseUrl } : prevConfig;

  // Sem segredo seguro disponível → não promovemos para 'connected'.
  const nextStatus = conn.status === 'connected' ? 'connected' : 'configuring';

  const { error: updErr } = await supabase
    .from('tenant_connections')
    .update({
      connection_config: newConfig,
      status: nextStatus,
      updated_at: new Date().toISOString(),
    })
    .eq('id', conn.id)
    .eq('company_id', ctx.companyId);
  if (updErr) {
    console.error('[INFOCAP SETUP] update error:', updErr.message);
    return NextResponse.json({ ok: false, error: 'Erro ao atualizar conexão.' }, { status: 500 });
  }

  await writeAudit(supabase, {
    company_id: ctx.companyId,
    tenant_connection_id: conn.id,
    actor_user_id: ctx.userId,
    event_type: 'connection_configured',
    action: 'infocap_setup_metadata',
    status: nextStatus,
    risk_level: 'medium',
    metadata: { provider: 'infocap', base_url_set: Boolean(baseUrl) },
  });

  const diagnostics = await diagnoseInfocapConnection(ctx.companyId);

  console.log(
    `[INFOCAP SETUP] company=${ctx.companyId} base_url_set=${Boolean(baseUrl)} status=${nextStatus} ready=${diagnostics.ready_for_real_lookup}`,
  );

  return NextResponse.json({
    ok: true,
    diagnostics,
    note: diagnostics.ready_for_real_lookup
      ? 'Conexão InfoCap pronta.'
      : 'Metadados atualizados. Credenciais (login/senha) ainda precisam ser gravadas por um fluxo seguro de segredo InfoCap, que não existe ainda (ver relatório 42I2.0B). Sem isso, ready_for_real_lookup permanece false.',
  });
}
