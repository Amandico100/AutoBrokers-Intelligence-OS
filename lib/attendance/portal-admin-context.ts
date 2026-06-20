// 43P1 — contexto admin compartilhado + store de portal browser (DB).
// Persistência sem schema novo: tenant_connections.connection_config do
// connection determinístico 'autobrokers_portal_browser' por company.
//   - connection_config.portal_definitions[]  (registry — tenant-scoped no MVP; TODO: promover a global)
//   - connection_config.portal_accounts[]      (contas/refs por corretora)
// Defensivo: se o Vault não estiver migrado, lança 'vault_not_available'.
import { cookies, headers } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';
import type { PortalDefinitionRecord, PortalAccountRecord } from '@/lib/attendance/portal-admin-sanitizers';
import { PORTAL_BROWSER_CONNECTOR_SLUG } from '@/lib/attendance/portal-admin-sanitizers';

const CONN_NAME = 'autobrokers_portal_browser';

/**
 * 43P1.1 — garante um connector_template próprio `portal_browser`. Cria se
 * faltar (best-effort). NUNCA reaproveita whatsapp_zapi silenciosamente:
 * retorna { id, fallback, warning } e o chamador registra o fallback explícito.
 */
export async function ensurePortalBrowserConnectorTemplate(
  supabase: SupabaseClient,
): Promise<{ id: string | null; slug: string; fallback: boolean; warning?: string }> {
  try {
    const { data: tpl } = await supabase
      .from('connector_templates')
      .select('id')
      .eq('slug', PORTAL_BROWSER_CONNECTOR_SLUG)
      .maybeSingle();
    if (tpl?.id) return { id: tpl.id, slug: PORTAL_BROWSER_CONNECTOR_SLUG, fallback: false };

    // Tenta criar o template canônico.
    const { data: created } = await supabase
      .from('connector_templates')
      .insert({
        slug: PORTAL_BROWSER_CONNECTOR_SLUG,
        name: 'Portal Browser',
        description: 'Automação de portais (browser relay) — cadastro global + contas tenant-private. Sem envio/ação real por padrão.',
        category: 'browser_automation',
        provider: 'autobrokers',
        connector_kind: 'portal_browser',
        auth_type: 'session_ref',
        risk_level: 'high',
        requires_approval_default: true,
        capabilities: ['navigate', 'extract', 'dry_run'],
      })
      .select('id')
      .single();
    if (created?.id) return { id: created.id, slug: PORTAL_BROWSER_CONNECTOR_SLUG, fallback: false };
  } catch { /* segue para fallback explícito */ }

  // Fallback EXPLÍCITO (não silencioso): usa whatsapp_zapi só para satisfazer FK,
  // marcando warning para o admin/relatório.
  try {
    const { data: legacy } = await supabase.from('connector_templates').select('id').eq('slug', 'whatsapp_zapi').maybeSingle();
    if (legacy?.id) {
      console.warn('[PORTAL TEMPLATE] portal_browser ausente — usando fallback whatsapp_zapi (warning explícito).');
      return { id: legacy.id, slug: 'whatsapp_zapi', fallback: true, warning: 'portal_browser_template_missing' };
    }
  } catch { /* ignore */ }
  return { id: null, slug: PORTAL_BROWSER_CONNECTOR_SLUG, fallback: true, warning: 'portal_browser_template_missing' };
}

export function getPortalSupabaseAdmin(): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

// 43P4.2A / 43P4.2A.1 — escopo de company (multi-tenant). Lógica PURA em portal-company-scope.
import { resolvePortalCompanyScope, resolveCompanyListingMode } from '@/lib/attendance/portal-company-scope';
export { resolvePortalCompanyScope, resolveCompanyListingMode } from '@/lib/attendance/portal-company-scope';

export async function getPortalAdminContext(
  supabase: SupabaseClient,
): Promise<{ companyId: string | null; userId: string | null; isMaster: boolean; company_scope_required: boolean }> {
  const cookieStore = await cookies();
  let userId: string | null = null;
  let sessionCompany: string | null = null;
  let isMaster = false; // só master_admin enumera/troca de tenant

  const adminSession = await getIronSession<AdminSessionData>(cookieStore, adminSessionOptions);
  if (adminSession.adminId) {
    userId = adminSession.adminId;
    sessionCompany = adminSession.companyId ?? null;
    // master_admin = admin de plataforma; company_admin fica travado na própria company.
    isMaster = adminSession.role === 'master_admin' && !sessionCompany;
  } else {
    const userSession = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (userSession.userId) { userId = userSession.userId; sessionCompany = userSession.companyId ?? null; }
  }
  if (!userId) return { companyId: null, userId: null, isMaster: false, company_scope_required: false };

  // Escopo solicitado: header X-AutoBrokers-Company OU cookie aj_company
  // (apenas master escolhe a corretora no dashboard; cookie vai em toda chamada).
  let requested: string | null = null;
  try { requested = (await headers()).get('x-autobrokers-company'); } catch { requested = null; }
  if (!requested) { try { requested = cookieStore.get('aj_company')?.value ?? null; } catch { requested = null; } }

  let usersV2Company: string | null = null;
  if (!sessionCompany) {
    try { const { data: u } = await supabase.from('users_v2').select('company_id').eq('id', userId).maybeSingle(); usersV2Company = u?.company_id ?? null; } catch { /* segue */ }
  }
  let requestedExists = false;
  if (!sessionCompany && isMaster && requested) {
    try { const { data: c } = await supabase.from('companies').select('id').eq('id', requested).maybeSingle(); requestedExists = Boolean(c?.id); } catch { /* segue */ }
  }
  let singleCompanyId: string | null = null;
  if (!sessionCompany && !usersV2Company && !(requested && requestedExists)) {
    try { const { data: companies } = await supabase.from('companies').select('id').order('created_at', { ascending: true }).limit(2); if (Array.isArray(companies) && companies.length === 1) singleCompanyId = companies[0].id; } catch { /* segue */ }
  }

  const scope = resolvePortalCompanyScope({
    is_master: isMaster, session_company: sessionCompany, users_v2_company: usersV2Company,
    requested_company: requested, requested_company_exists: requestedExists, single_company_id: singleCompanyId,
  });
  return { companyId: scope.companyId, userId, isMaster: scope.isMaster, company_scope_required: scope.company_scope_required };
}

/**
 * Lista companies (id/nome/status) para o seletor. Coluna real = company_name.
 * `onlyId` restringe a UMA company (tenant admin vê só a própria). Sem dados sensíveis.
 */
export async function listCompaniesForAdmin(supabase: SupabaseClient, onlyId?: string): Promise<Array<{ id: string; name: string | null; status: string | null }>> {
  try {
    let q = supabase.from('companies').select('id, company_name, status').order('created_at', { ascending: true }).limit(200);
    if (onlyId) q = supabase.from('companies').select('id, company_name, status').eq('id', onlyId).limit(1);
    const { data } = await q;
    return Array.isArray(data) ? data.map((c: any) => ({ id: c.id, name: c.company_name ?? null, status: c.status ?? null })) : [];
  } catch { return []; }
}

interface ConnRow { id: string; connection_config: Record<string, any> | null; }

async function getOrCreateConn(supabase: SupabaseClient, companyId: string): Promise<ConnRow> {
  const { data: existing, error } = await supabase
    .from('tenant_connections')
    .select('id, connection_config, connector_template_id')
    .eq('company_id', companyId)
    .eq('name', CONN_NAME)
    .maybeSingle();
  if (error) throw new Error('vault_not_available');

  const tpl = await ensurePortalBrowserConnectorTemplate(supabase);

  if (existing) {
    // 43P1.1 — migração: se a connection do 43P1 aponta para outro template e
    // agora existe o portal_browser canônico, re-aponta (preserva os dados).
    if (tpl.id && !tpl.fallback && (existing as any).connector_template_id && (existing as any).connector_template_id !== tpl.id) {
      try {
        await supabase.from('tenant_connections').update({ connector_template_id: tpl.id }).eq('id', (existing as any).id).eq('company_id', companyId);
      } catch { /* migração best-effort; dados preservados de qualquer forma */ }
    }
    return existing as ConnRow;
  }

  if (!tpl.id) throw new Error('connector_template_missing');
  const { data: created, error: insErr } = await supabase
    .from('tenant_connections')
    .insert({
      company_id: companyId, connector_template_id: tpl.id, name: CONN_NAME, status: 'draft',
      connection_config: { portal_definitions: [], portal_accounts: [] },
      metadata: { purpose: 'portal_browser_registry_43p1', connector_slug: tpl.slug, template_fallback: tpl.fallback, ...(tpl.warning ? { warning: tpl.warning } : {}) },
    })
    .select('id, connection_config')
    .single();
  if (insErr || !created) throw new Error('vault_not_available');
  return created as ConnRow;
}

function readArr<T>(conn: ConnRow, key: string): T[] {
  const cfg = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
  return Array.isArray(cfg[key]) ? (cfg[key] as T[]) : [];
}

async function writeArrays(supabase: SupabaseClient, conn: ConnRow, companyId: string, patch: Record<string, unknown>): Promise<void> {
  const base = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
  const { error } = await supabase
    .from('tenant_connections')
    .update({ connection_config: { ...base, ...patch }, updated_at: new Date().toISOString() })
    .eq('id', conn.id)
    .eq('company_id', companyId);
  if (error) throw new Error('vault_not_available');
}

// --- Portal definitions -----------------------------------------------------
export async function listPortalDefinitions(supabase: SupabaseClient, companyId: string): Promise<PortalDefinitionRecord[]> {
  const { data, error } = await supabase
    .from('tenant_connections').select('connection_config')
    .eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return [];
  return readArr<PortalDefinitionRecord>({ id: '', connection_config: data.connection_config }, 'portal_definitions');
}

export async function savePortalDefinition(supabase: SupabaseClient, companyId: string, def: PortalDefinitionRecord): Promise<PortalDefinitionRecord[]> {
  const conn = await getOrCreateConn(supabase, companyId);
  const defs = readArr<PortalDefinitionRecord>(conn, 'portal_definitions');
  const idx = defs.findIndex((d) => d.portal_id === def.portal_id);
  if (idx >= 0) defs[idx] = def; else defs.push(def);
  await writeArrays(supabase, conn, companyId, { portal_definitions: defs });
  return defs;
}

export async function removePortalDefinition(supabase: SupabaseClient, companyId: string, portalId: string): Promise<PortalDefinitionRecord[]> {
  const conn = await getOrCreateConn(supabase, companyId);
  const defs = readArr<PortalDefinitionRecord>(conn, 'portal_definitions').filter((d) => d.portal_id !== portalId);
  await writeArrays(supabase, conn, companyId, { portal_definitions: defs });
  return defs;
}

// --- Portal accounts --------------------------------------------------------
export async function listPortalAccounts(supabase: SupabaseClient, companyId: string): Promise<PortalAccountRecord[]> {
  const { data, error } = await supabase
    .from('tenant_connections').select('connection_config')
    .eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return [];
  return readArr<PortalAccountRecord>({ id: '', connection_config: data.connection_config }, 'portal_accounts');
}

export async function savePortalAccount(supabase: SupabaseClient, companyId: string, acc: PortalAccountRecord): Promise<PortalAccountRecord[]> {
  const conn = await getOrCreateConn(supabase, companyId);
  const accs = readArr<PortalAccountRecord>(conn, 'portal_accounts');
  const idx = accs.findIndex((a) => a.portal_account_id === acc.portal_account_id);
  if (idx >= 0) accs[idx] = acc; else accs.push(acc);
  await writeArrays(supabase, conn, companyId, { portal_accounts: accs });
  return accs;
}

export async function removePortalAccount(supabase: SupabaseClient, companyId: string, accountId: string): Promise<PortalAccountRecord[]> {
  const conn = await getOrCreateConn(supabase, companyId);
  const accs = readArr<PortalAccountRecord>(conn, 'portal_accounts').filter((a) => a.portal_account_id !== accountId);
  await writeArrays(supabase, conn, companyId, { portal_accounts: accs });
  return accs;
}

// --- Relay sessions (43P2) — sandbox, mantém as últimas N ----------------------
const RELAY_KEEP = 25;

export async function getRelaySession(supabase: SupabaseClient, companyId: string, relayId: string): Promise<any | null> {
  const { data, error } = await supabase
    .from('tenant_connections').select('connection_config')
    .eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return null;
  const arr = readArr<any>({ id: '', connection_config: data.connection_config }, 'relay_sessions');
  return arr.find((r) => r?.relay_id === relayId) ?? null;
}

export async function saveRelaySession(supabase: SupabaseClient, companyId: string, session: any): Promise<void> {
  const conn = await getOrCreateConn(supabase, companyId);
  const arr = readArr<any>(conn, 'relay_sessions');
  const idx = arr.findIndex((r) => r?.relay_id === session.relay_id);
  if (idx >= 0) arr[idx] = session; else arr.push(session);
  const trimmed = arr.slice(-RELAY_KEEP);
  await writeArrays(supabase, conn, companyId, { relay_sessions: trimmed });
}

// --- Skill runs (43P3) — dry-run, mantém os últimos N ----------------------
export async function getSkillRun(supabase: SupabaseClient, companyId: string, runId: string): Promise<any | null> {
  const { data, error } = await supabase
    .from('tenant_connections').select('connection_config')
    .eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return null;
  const arr = readArr<any>({ id: '', connection_config: data.connection_config }, 'skill_runs');
  return arr.find((r) => r?.run_id === runId) ?? null;
}

export async function saveSkillRun(supabase: SupabaseClient, companyId: string, run: any): Promise<void> {
  const conn = await getOrCreateConn(supabase, companyId);
  const arr = readArr<any>(conn, 'skill_runs');
  const idx = arr.findIndex((r) => r?.run_id === run.run_id);
  if (idx >= 0) arr[idx] = run; else arr.push(run);
  await writeArrays(supabase, conn, companyId, { skill_runs: arr.slice(-RELAY_KEEP) });
}

// --- Login setups (43P4) — assistido, mantém os últimos N ------------------
export async function getLoginSetup(supabase: SupabaseClient, companyId: string, setupId: string): Promise<any | null> {
  const { data, error } = await supabase
    .from('tenant_connections').select('connection_config')
    .eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return null;
  const arr = readArr<any>({ id: '', connection_config: data.connection_config }, 'login_setups');
  return arr.find((r) => r?.setup_id === setupId) ?? null;
}

export async function saveLoginSetup(supabase: SupabaseClient, companyId: string, setup: any): Promise<void> {
  const conn = await getOrCreateConn(supabase, companyId);
  const arr = readArr<any>(conn, 'login_setups');
  const idx = arr.findIndex((r) => r?.setup_id === setup.setup_id);
  if (idx >= 0) arr[idx] = setup; else arr.push(setup);
  await writeArrays(supabase, conn, companyId, { login_setups: arr.slice(-RELAY_KEEP) });
}

// 43P-FINAL-1 — approvals de canary (tenant-scoped) e canaries.
export async function listCanaryApprovals(supabase: SupabaseClient, companyId: string): Promise<any[]> {
  const { data, error } = await supabase.from('tenant_connections').select('connection_config').eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return [];
  return readArr<any>({ id: '', connection_config: data.connection_config }, 'canary_approvals');
}
export async function saveCanaryApproval(supabase: SupabaseClient, companyId: string, approval: any): Promise<void> {
  const conn = await getOrCreateConn(supabase, companyId);
  const arr = readArr<any>(conn, 'canary_approvals');
  const idx = arr.findIndex((r) => r?.portal_account_id === approval.portal_account_id && r?.journey === approval.journey);
  if (idx >= 0) arr[idx] = approval; else arr.push(approval);
  await writeArrays(supabase, conn, companyId, { canary_approvals: arr.slice(-RELAY_KEEP) });
}
export async function getCanary(supabase: SupabaseClient, companyId: string, canaryId: string): Promise<any | null> {
  const { data, error } = await supabase.from('tenant_connections').select('connection_config').eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return null;
  return readArr<any>({ id: '', connection_config: data.connection_config }, 'canaries').find((r) => r?.canary_id === canaryId) ?? null;
}
export async function listCanaries(supabase: SupabaseClient, companyId: string): Promise<any[]> {
  const { data, error } = await supabase.from('tenant_connections').select('connection_config').eq('company_id', companyId).eq('name', CONN_NAME).maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return [];
  return readArr<any>({ id: '', connection_config: data.connection_config }, 'canaries');
}
export async function saveCanary(supabase: SupabaseClient, companyId: string, canary: any): Promise<void> {
  const conn = await getOrCreateConn(supabase, companyId);
  const arr = readArr<any>(conn, 'canaries');
  const idx = arr.findIndex((r) => r?.canary_id === canary.canary_id);
  if (idx >= 0) arr[idx] = canary; else arr.push(canary);
  await writeArrays(supabase, conn, companyId, { canaries: arr.slice(-RELAY_KEEP) });
}
