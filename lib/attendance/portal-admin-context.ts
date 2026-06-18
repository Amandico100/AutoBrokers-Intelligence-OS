// 43P1 — contexto admin compartilhado + store de portal browser (DB).
// Persistência sem schema novo: tenant_connections.connection_config do
// connection determinístico 'autobrokers_portal_browser' por company.
//   - connection_config.portal_definitions[]  (registry — tenant-scoped no MVP; TODO: promover a global)
//   - connection_config.portal_accounts[]      (contas/refs por corretora)
// Defensivo: se o Vault não estiver migrado, lança 'vault_not_available'.
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';
import type { PortalDefinitionRecord, PortalAccountRecord } from '@/lib/attendance/portal-admin-sanitizers';

const CONN_NAME = 'autobrokers_portal_browser';

export function getPortalSupabaseAdmin(): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

export async function getPortalAdminContext(supabase: SupabaseClient): Promise<{ companyId: string | null; userId: string | null }> {
  const cookieStore = await cookies();
  const adminSession = await getIronSession<AdminSessionData>(cookieStore, adminSessionOptions);
  if (adminSession.adminId) {
    if (adminSession.companyId) return { companyId: adminSession.companyId, userId: adminSession.adminId };
    const { data: u } = await supabase.from('users_v2').select('company_id').eq('id', adminSession.adminId).single();
    return { companyId: u?.company_id ?? null, userId: adminSession.adminId };
  }
  const userSession = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (userSession.userId && userSession.companyId) return { companyId: userSession.companyId, userId: userSession.userId };
  if (userSession.userId) {
    const { data: u } = await supabase.from('users_v2').select('company_id').eq('id', userSession.userId).single();
    return { companyId: u?.company_id ?? null, userId: userSession.userId };
  }
  return { companyId: null, userId: null };
}

interface ConnRow { id: string; connection_config: Record<string, any> | null; }

async function getOrCreateConn(supabase: SupabaseClient, companyId: string): Promise<ConnRow> {
  const { data: existing, error } = await supabase
    .from('tenant_connections')
    .select('id, connection_config')
    .eq('company_id', companyId)
    .eq('name', CONN_NAME)
    .maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (existing) return existing as ConnRow;

  const { data: tpl } = await supabase.from('connector_templates').select('id').eq('slug', 'whatsapp_zapi').maybeSingle();
  if (!tpl?.id) throw new Error('connector_template_missing');
  const { data: created, error: insErr } = await supabase
    .from('tenant_connections')
    .insert({
      company_id: companyId, connector_template_id: tpl.id, name: CONN_NAME, status: 'draft',
      connection_config: { portal_definitions: [], portal_accounts: [] },
      metadata: { purpose: 'portal_browser_registry_43p1' },
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
