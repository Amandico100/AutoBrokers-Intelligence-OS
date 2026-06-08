import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin, writeAudit } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

const ALLOWED_ACTIONS = ['whatsapp_draft_message', 'whatsapp_send_message_dry_run'];

function pickString(obj: unknown, key: string): string | undefined {
  if (obj && typeof obj === 'object') {
    const v = (obj as Record<string, unknown>)[key];
    if (typeof v === 'string' && v.trim()) return v.trim();
  }
  return undefined;
}

/**
 * POST /api/vault/approvals/[approvalId]/execute
 * Executa uma aprovação WhatsApp APROVADA em DRY-RUN (sem envio real). HITL → execução controlada.
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ approvalId: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ success: false, error: 'Não autorizado' }, { status: 401 });

  const { approvalId } = await params;

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    return NextResponse.json({ success: false, error: 'Chave interna do backend não configurada.' }, { status: 500 });
  }

  const supabase = getSupabaseAdmin();

  const { data: ar } = await supabase
    .from('approval_requests')
    .select('id, status, action_type, tenant_connection_id, risk_level, preview, request_payload')
    .eq('id', approvalId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();

  if (!ar) return NextResponse.json({ success: false, error: 'Pedido de aprovação não encontrado' }, { status: 404 });
  if (ar.status !== 'approved') {
    return NextResponse.json(
      { success: false, error: 'Apenas pedidos aprovados podem ser executados.' },
      { status: 409 },
    );
  }
  if (!ALLOWED_ACTIONS.includes(ar.action_type)) {
    return NextResponse.json({ success: false, error: 'Ação não suportada para execução.' }, { status: 400 });
  }
  if (!ar.tenant_connection_id) {
    return NextResponse.json({ success: false, error: 'Aprovação sem conexão vinculada.' }, { status: 400 });
  }

  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id, technical_ref_type, technical_ref_id, company_id')
    .eq('id', ar.tenant_connection_id)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (!conn) return NextResponse.json({ success: false, error: 'Conexão não encontrada' }, { status: 404 });
  if (conn.technical_ref_type !== 'integration' || !conn.technical_ref_id) {
    return NextResponse.json({ success: false, error: 'Conexão WhatsApp não configurada.' }, { status: 400 });
  }

  const toNumber = pickString(ar.request_payload, 'to_number') || pickString(ar.preview, 'to_number');
  const message =
    pickString(ar.request_payload, 'message') ||
    pickString(ar.preview, 'message') ||
    pickString(ar.preview, 'mensagem');
  if (!toNumber || !message) {
    return NextResponse.json(
      { success: false, error: 'Aprovação sem telefone/mensagem para simular.' },
      { status: 400 },
    );
  }
  const toLast4 = toNumber.slice(-4);
  const riskLevel = typeof ar.risk_level === 'string' ? ar.risk_level : 'medium';

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json({ success: false, error: 'Backend de IA não configurado.' }, { status: 500 });
    }
    throw error;
  }

  const markFailed = async (errMsg: string, status: number) => {
    const { data: updated } = await supabase
      .from('approval_requests')
      .update({
        status: 'failed',
        error_message: errMsg.slice(0, 300),
        approval_result: { success: false, dry_run: true },
      })
      .eq('id', approvalId)
      .eq('company_id', ctx.companyId)
      .select('*')
      .single();
    await writeAudit(supabase, {
      company_id: ctx.companyId,
      tenant_connection_id: conn.id,
      approval_request_id: approvalId,
      actor_user_id: ctx.userId,
      event_type: 'whatsapp_dry_run_failed',
      action: 'send_message_dry_run',
      status: 'failed',
      risk_level: riskLevel,
      metadata: { provider: 'z-api', dry_run: true, to_last4: toLast4 },
    });
    return NextResponse.json({ success: false, dry_run: true, approval: updated, error: errMsg }, { status });
  };

  try {
    const res = await fetch(`${backendUrl}/api/whatsapp-integrations/send-dry-run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: ctx.companyId,
        integration_id: conn.technical_ref_id,
        to_number: toNumber,
        message,
      }),
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }

    if (!res.ok || data.success !== true) {
      const detail =
        typeof data.detail === 'string'
          ? data.detail
          : typeof data.error === 'string'
            ? data.error
            : undefined;
      const snippet = !detail && raw ? ` — resposta do backend: ${raw.slice(0, 140)}` : '';
      return markFailed(
        detail || `Backend retornou ${res.status} em /api/whatsapp-integrations/send-dry-run${snippet}`,
        res.ok ? 502 : res.status,
      );
    }

    const { data: updated } = await supabase
      .from('approval_requests')
      .update({
        status: 'executed',
        executed_at: new Date().toISOString(),
        approval_result: { success: true, provider: 'z-api', dry_run: true },
      })
      .eq('id', approvalId)
      .eq('company_id', ctx.companyId)
      .eq('status', 'approved')
      .select('*')
      .single();

    await writeAudit(supabase, {
      company_id: ctx.companyId,
      tenant_connection_id: conn.id,
      approval_request_id: approvalId,
      actor_user_id: ctx.userId,
      event_type: 'whatsapp_dry_run_executed',
      action: 'send_message_dry_run',
      status: 'success',
      risk_level: riskLevel,
      metadata: { provider: 'z-api', dry_run: true, message_length: message.length, to_last4: toLast4 },
    });

    return NextResponse.json({
      success: true,
      dry_run: true,
      approval: updated,
      message: 'Simulação executada. Nenhuma mensagem foi enviada.',
    });
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'erro desconhecido';
    return markFailed(`Falha ao conectar ao backend: ${msg}`, 502);
  }
}
