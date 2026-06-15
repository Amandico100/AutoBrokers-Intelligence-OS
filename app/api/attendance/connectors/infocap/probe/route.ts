import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

const INFOCAP_SLUG = 'infocap';

/**
 * POST /api/attendance/connectors/infocap/probe
 *
 * Diagnóstico read-only: testa múltiplos endpoints InfoCap (CPF/nome) e devolve
 * SÓ o shape (nomes de chaves/contagens/status) — nunca valores/PII/segredo.
 * Delega ao backend (que decifra o segredo). Não confirma cobertura, não persiste.
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    return NextResponse.json({ ok: false, error: 'Chave interna do backend não configurada.' }, { status: 500 });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const queryType = body.query_type === 'name' ? 'name' : 'cpf';
  const query = typeof body.query === 'string' ? body.query.trim() : '';
  const codfil = typeof body.codfil === 'number' ? body.codfil : 1;
  if (!query) {
    return NextResponse.json({ ok: false, error: 'query é obrigatória (CPF ou nome).' }, { status: 400 });
  }

  const supabase = getSupabaseAdmin();
  const { data: tpl } = await supabase
    .from('connector_templates')
    .select('id')
    .eq('slug', INFOCAP_SLUG)
    .eq('is_active', true)
    .maybeSingle();
  if (!tpl?.id) return NextResponse.json({ ok: false, error: 'Template InfoCap não encontrado.' }, { status: 404 });
  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id')
    .eq('company_id', ctx.companyId)
    .eq('connector_template_id', tpl.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!conn?.id) return NextResponse.json({ ok: false, error: 'Conexão InfoCap não encontrada.' }, { status: 404 });

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json({ ok: false, error: 'Backend de IA não configurado.' }, { status: 500 });
    }
    throw error;
  }

  try {
    const res = await fetch(`${backendUrl}/attendance/connectors/infocap/probe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: ctx.companyId,
        tenant_connection_id: conn.id,
        query_type: queryType,
        query,
        codfil,
      }),
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }
    if (!res.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : typeof data.error === 'string' ? data.error : undefined;
      return NextResponse.json({ ok: false, error: detail || `Backend retornou ${res.status}` }, { status: res.ok ? 502 : res.status });
    }
    // data já é diagnóstico sanitizado (sem valores/PII).
    console.log(`[INFOCAP PROBE] company=${ctx.companyId} query_type=${queryType} winner=${Boolean((data as any).winner_endpoint)}`);
    return NextResponse.json(data);
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'erro desconhecido';
    return NextResponse.json({ ok: false, error: `Falha ao conectar ao backend: ${msg}` }, { status: 502 });
  }
}
