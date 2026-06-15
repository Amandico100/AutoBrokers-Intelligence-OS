import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { diagnoseInfocapConnection } from '@/lib/attendance/connectors/infocap-policy-lookup';

export const dynamic = 'force-dynamic';

const INFOCAP_SLUG = 'infocap';

/**
 * POST /api/attendance/connectors/infocap/secret
 *
 * Secret Flow seguro: recebe credenciais InfoCap (login/senha) APENAS server-side,
 * delega ao backend (que cifra via EncryptionService e grava encrypted_secret_ref),
 * e devolve diagnostics sanitizado. O segredo NUNCA é gravado no Web, logado, nem
 * retornado. NÃO faz chamada real ao InfoCap.
 */
export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) {
    console.error('[INFOCAP SECRET] internal key not configured');
    return NextResponse.json({ ok: false, error: 'Chave interna do backend não configurada.' }, { status: 500 });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const username = typeof body.username === 'string' ? body.username.trim() : '';
  const password = typeof body.password === 'string' ? body.password : '';
  const baseUrl = typeof body.base_url === 'string' ? body.base_url.trim() : '';

  if (!username || !password) {
    return NextResponse.json({ ok: false, error: 'username e password são obrigatórios.' }, { status: 400 });
  }
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    return NextResponse.json({ ok: false, error: 'base_url inválida (use http(s)://...)' }, { status: 400 });
  }

  const supabase = getSupabaseAdmin();

  // Template + conexão InfoCap da corretora
  const { data: tpl } = await supabase
    .from('connector_templates')
    .select('id')
    .eq('slug', INFOCAP_SLUG)
    .eq('is_active', true)
    .maybeSingle();
  if (!tpl?.id) {
    return NextResponse.json({ ok: false, error: 'Template InfoCap não encontrado/ativo.' }, { status: 404 });
  }
  const { data: conn } = await supabase
    .from('tenant_connections')
    .select('id')
    .eq('company_id', ctx.companyId)
    .eq('connector_template_id', tpl.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!conn?.id) {
    return NextResponse.json(
      { ok: false, error: 'Conexão InfoCap não encontrada. Crie a conexão no Vault antes.' },
      { status: 404 },
    );
  }

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
    const res = await fetch(`${backendUrl}/attendance/connectors/infocap/secret`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: ctx.companyId,
        tenant_connection_id: conn.id,
        base_url: baseUrl || undefined,
        username,
        password,
      }),
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }
    if (!res.ok || data.ok !== true) {
      const detail =
        typeof data.detail === 'string' ? data.detail : typeof data.error === 'string' ? data.error : undefined;
      return NextResponse.json(
        { ok: false, error: detail || `Backend retornou ${res.status} ao gravar o segredo InfoCap.` },
        { status: res.ok ? 502 : res.status },
      );
    }

    const diagnostics = await diagnoseInfocapConnection(ctx.companyId);
    // Log sanitizado: SEM login/senha.
    console.log(
      `[INFOCAP SECRET] company=${ctx.companyId} stored=true ready=${diagnostics.ready_for_real_lookup}`,
    );
    return NextResponse.json({
      ok: true,
      diagnostics,
      note: diagnostics.ready_for_real_lookup
        ? 'Conexão InfoCap pronta para lookup real (próximo batch).'
        : 'Credenciais gravadas. Configure base_url para concluir (ready_for_real_lookup).',
    });
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'erro desconhecido';
    console.error('[INFOCAP SECRET] proxy error');
    return NextResponse.json({ ok: false, error: `Falha ao conectar ao backend: ${msg}` }, { status: 502 });
  }
}
