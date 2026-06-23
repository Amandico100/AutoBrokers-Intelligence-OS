// SPEC-014 C1 — Cockpit de Capabilities por corretora (master). Lê a matriz governada (registry)
// + estado real (flags de runtime, conexões do Vault, entitlements) e permite sincronizar os
// acessos do runtime à matriz. Read-only no diagnóstico; POST faz ações seguras (same-origin+master).
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService, assertSameOrigin } from '@/lib/admin/admin-auth';
import {
  CAPABILITY_CATALOG, resolveAgentCapabilities, type TenantEntitlement, type AgentRole,
} from '@/lib/capabilities/registry';

export const dynamic = 'force-dynamic';

// provider da capability → slug(s) de connector_template do Vault
const PROVIDER_SLUGS: Record<string, string[]> = {
  infocap: ['infocap'],
  zapi: ['zapi', 'whatsapp'],
  'mcp:google-drive': ['google_drive'],
  'mcp:google-calendar': ['google_calendar'],
  'mcp:slack': ['slack'],
  notion: ['notion'],
  portal_browser: ['insurance_portal', 'browserbase'],
};

function buildEntitlements(connectedSlugs: Set<string>, entRows: Record<string, boolean>): TenantEntitlement[] {
  return CAPABILITY_CATALOG.map((cap) => {
    const slugs = cap.provider ? (PROVIDER_SLUGS[cap.provider] ?? []) : [];
    const connection_present = slugs.length === 0 ? false : slugs.some((s) => connectedSlugs.has(s));
    const enabled = cap.key in entRows ? entRows[cap.key] : true;
    return { capability_key: cap.key, enabled, connection_present };
  });
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const supabase = supabaseService();

  // runtime flags reais
  const { data: agentsRaw } = await supabase.from('agents')
    .select('id, name, agent_role, is_active, allow_web_search').eq('company_id', companyId);
  const agents = (agentsRaw ?? []) as any[];
  const cores = agents.filter((a) => a.agent_role === 'core');
  const evens = agents.filter((a) => a.agent_role === 'attendance');

  // conexões do Vault (slugs conectados)
  const connectedSlugs = new Set<string>();
  try {
    const { data: conns } = await supabase.from('tenant_connections')
      .select('status, connector_templates(slug)').eq('company_id', companyId);
    for (const c of (conns ?? []) as any[]) {
      const slug = c?.connector_templates?.slug;
      const ok = ['connected', 'active', 'healthy'].includes(String(c?.status || '').toLowerCase());
      if (slug && ok) connectedSlugs.add(String(slug));
    }
  } catch { /* tabela/relação ausente → sem conexões */ }

  // entitlements governados (graceful se a tabela ainda não foi aplicada)
  const entRows: Record<string, boolean> = {};
  let entitlements_table = true;
  try {
    const { data: ents, error } = await supabase.from('tenant_capability_entitlements')
      .select('capability_key, enabled').eq('company_id', companyId);
    if (error) entitlements_table = false;
    for (const e of (ents ?? []) as any[]) entRows[e.capability_key] = e.enabled !== false;
  } catch { entitlements_table = false; }

  const ent = buildEntitlements(connectedSlugs, entRows);
  const resolve = (role: AgentRole) => resolveAgentCapabilities(role, ent);

  return NextResponse.json({
    ok: true,
    company_id: companyId,
    entitlements_table,
    runtime: {
      core_web_search: cores.some((c) => c.allow_web_search === true),
      core_count: cores.length,
      even_web_search_any: evens.some((e) => e.allow_web_search === true),
      even_count: evens.length,
    },
    connected_slugs: Array.from(connectedSlugs),
    core: resolve('core'),
    attendance: resolve('attendance'),
    auxiliary: resolve('auxiliary'),
  });
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const supabase = supabaseService();

  const body = await req.json().catch(() => ({}));
  const action = typeof body.action === 'string' ? body.action : '';

  if (action === 'sync_runtime_flags') {
    // Alinha os flags de runtime à matriz: Core com busca web; Even sem busca web aberta.
    const nowIso = new Date().toISOString();
    const { data: cores } = await supabase.from('agents').update({ allow_web_search: true, updated_at: nowIso })
      .eq('company_id', companyId).eq('agent_role', 'core').not('name', 'ilike', '%sandbox%').select('id');
    const { data: evens } = await supabase.from('agents').update({ allow_web_search: false, updated_at: nowIso })
      .eq('company_id', companyId).eq('agent_role', 'attendance').select('id');
    return NextResponse.json({ ok: true, action, cores_web_on: (cores ?? []).length, even_web_off: (evens ?? []).length });
  }

  if (action === 'set_entitlement') {
    const key = typeof body.capability_key === 'string' ? body.capability_key : '';
    const enabled = body.enabled !== false;
    if (!CAPABILITY_CATALOG.some((c) => c.key === key)) {
      return NextResponse.json({ ok: false, error: 'capability_desconhecida' }, { status: 400 });
    }
    try {
      const { error } = await supabase.from('tenant_capability_entitlements')
        .upsert({ company_id: companyId, capability_key: key, enabled, updated_at: new Date().toISOString() },
          { onConflict: 'company_id,capability_key' });
      if (error) return NextResponse.json({ ok: false, error: 'tabela_nao_aplicada', detail: 'Aplique SPEC-014-01.' }, { status: 409 });
    } catch {
      return NextResponse.json({ ok: false, error: 'tabela_nao_aplicada', detail: 'Aplique SPEC-014-01.' }, { status: 409 });
    }
    return NextResponse.json({ ok: true, action, capability_key: key, enabled });
  }

  return NextResponse.json({ ok: false, error: 'acao_invalida' }, { status: 400 });
}
