import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

const INFOCAP_SLUG = 'infocap';

/**
 * POST /api/attendance/connectors/infocap/test  (C-FIX-2)
 * Testa a conexão InfoCap usando o segredo JÁ salvo (não re-digita login/senha).
 * Atualiza o status real (connected / error / configuring) no backend.
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) return NextResponse.json({ ok: false, error: 'Chave interna não configurada.' }, { status: 500 });

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { body = {}; }
  const requestedConnId = typeof body.tenant_connection_id === 'string' ? body.tenant_connection_id.trim() : '';

  const supabase = getSupabaseAdmin();
  const { data: tpl } = await supabase.from('connector_templates').select('id').eq('slug', INFOCAP_SLUG).eq('is_active', true).maybeSingle();
  if (!tpl?.id) return NextResponse.json({ ok: false, error: 'Template InfoCap não encontrado.' }, { status: 404 });

  let connId = requestedConnId;
  if (!connId) {
    const { data } = await supabase.from('tenant_connections').select('id')
      .eq('company_id', ctx.companyId).eq('connector_template_id', tpl.id).neq('status', 'archived')
      .order('created_at', { ascending: true }).limit(1).maybeSingle();
    connId = data?.id ?? '';
  }
  if (!connId) return NextResponse.json({ ok: false, error: 'Conexão InfoCap não encontrada.' }, { status: 404 });

  let backendUrl: string;
  try { backendUrl = getBackendUrl(req); }
  catch (e) {
    if (e instanceof BackendUrlError) return NextResponse.json({ ok: false, error: 'Backend de IA não configurado.' }, { status: 500 });
    throw e;
  }

  try {
    const res = await fetch(`${backendUrl}/attendance/connectors/infocap/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({ company_id: ctx.companyId, tenant_connection_id: connId }),
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.ok ? 200 : res.status });
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'erro';
    return NextResponse.json({ ok: false, error: `Falha ao testar: ${msg}` }, { status: 502 });
  }
}
