import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

import { requireMasterAdmin } from '@/lib/admin/admin-auth';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * Prompt Efetivo (SPEC-018 S4) — diagnóstico READ-ONLY de autoridade, só Master.
 *
 * GET ?action=agents&company_id=X            → agentes da empresa (para o seletor)
 * GET ?company_id=X&agent_id=Y               → diagnóstico via backend Smith
 *
 * A chave interna Next↔Backend nunca chega ao browser; o backend já devolve
 * prompts REDIGIDOS (nunca o texto cru do cliente).
 */

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

export async function GET(request: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ error: auth.error }, { status: auth.status });

  const sp = request.nextUrl.searchParams;
  const companyId = sp.get('company_id');
  if (!companyId) {
    return NextResponse.json({ error: 'company_id é obrigatório' }, { status: 400 });
  }

  if (sp.get('action') === 'agents') {
    const { data, error } = await supabaseAdmin
      .from('agents')
      .select('id, name, agent_role, is_active')
      .eq('company_id', companyId)
      .order('created_at', { ascending: true });
    if (error) {
      console.error('[ADMIN PROMPT-EFFECTIVE] agents error:', error);
      return NextResponse.json({ error: 'Erro ao listar agentes' }, { status: 500 });
    }
    return NextResponse.json({ agents: data || [] });
  }

  const agentId = sp.get('agent_id');
  if (!agentId) {
    return NextResponse.json({ error: 'agent_id é obrigatório' }, { status: 400 });
  }
  const key = internalKey();
  if (!key) {
    return NextResponse.json({ error: 'Chave interna não configurada.' }, { status: 500 });
  }

  try {
    const backend = getBackendUrl();
    const res = await fetch(
      `${backend}/api/authority/prompt-effective?company_id=${encodeURIComponent(companyId)}&agent_id=${encodeURIComponent(agentId)}`,
      { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
    );
    const json = await res.json().catch(() => ({}));
    return NextResponse.json(json, { status: res.status });
  } catch (e) {
    if (e instanceof BackendUrlError) {
      return NextResponse.json({ error: 'Backend não configurado.' }, { status: 500 });
    }
    return NextResponse.json({ error: 'Falha ao consultar o Prompt Efetivo.' }, { status: 502 });
  }
}
