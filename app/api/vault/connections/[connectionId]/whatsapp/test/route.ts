import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin, writeAudit } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * POST /api/vault/connections/[connectionId]/whatsapp/test
 * Validação LOCAL da configuração (descriptografa em memória no backend). NÃO envia mensagem.
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ connectionId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ success: false, error: 'Não autorizado' }, { status: 401 });

  const { connectionId } = await params;

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    return NextResponse.json({ success: false, error: 'Chave interna do backend não configurada.' }, { status: 500 });
  }

  const supabase = getSupabaseAdmin();

  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id, technical_ref_type, technical_ref_id')
    .eq('id', connectionId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (!conn) return NextResponse.json({ success: false, error: 'Conexão não encontrada' }, { status: 404 });
  if (conn.technical_ref_type !== 'integration' || !conn.technical_ref_id) {
    return NextResponse.json(
      { success: false, error: 'Conexão ainda não configurada. Configure com segurança primeiro.' },
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
    const res = await fetch(`${backendUrl}/api/whatsapp-integrations/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({ company_id: ctx.companyId, integration_id: conn.technical_ref_id }),
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }

    await writeAudit(supabase, {
      company_id: ctx.companyId,
      tenant_connection_id: connectionId,
      actor_user_id: ctx.userId,
      event_type: 'whatsapp_tested',
      action: 'test_config',
      status: data.success ? 'success' : 'failed',
      risk_level: 'medium',
      metadata: { dry_run: true },
    });

    if (!res.ok || typeof data.success === 'undefined') {
      const detail =
        typeof data.detail === 'string'
          ? data.detail
          : typeof data.error === 'string'
            ? data.error
            : undefined;
      const snippet = !detail && raw ? ` — resposta do backend: ${raw.slice(0, 160)}` : '';
      return NextResponse.json(
        {
          success: false,
          error: detail || `Backend retornou ${res.status} em /api/whatsapp-integrations/test${snippet}`,
        },
        { status: res.ok ? 502 : res.status },
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    console.error('[VAULT whatsapp test] proxy error', error);
    const msg = error instanceof Error ? error.message : 'erro desconhecido';
    return NextResponse.json({ success: false, error: `Falha ao conectar ao backend: ${msg}` }, { status: 502 });
  }
}
