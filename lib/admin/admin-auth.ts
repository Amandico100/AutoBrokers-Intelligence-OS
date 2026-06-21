// TA2-B — wrappers de autorização server-side (iron-session). Nunca confiam só na
// presença do cookie: decodificam e validam papel real. Decisões puras em
// admin-auth-policy.ts. Usado pelas rotas admin (master) e tenant (dashboard).
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { adminSessionOptions, sessionOptions, type AdminSessionData, type SessionData } from '@/lib/iron-session';
import { canAdminReadCompany, canProvisionTenant, canWriteTenantConfig, isPlatformMaster } from '@/lib/admin/admin-auth-policy';

export function supabaseService(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, { auth: { persistSession: false } });
}

export type AuthFail = { ok: false; status: number; error: string };

interface AdminCtx { adminId: string; role: AdminSessionData['role'] | null; companyId: string | null; isMaster: boolean }

export async function getAdminContext(): Promise<AdminCtx | null> {
  const c = await cookies();
  const s = await getIronSession<AdminSessionData>(c, adminSessionOptions);
  if (!s.adminId) return null;
  const companyId = s.companyId ?? null;
  return { adminId: s.adminId, role: s.role ?? null, companyId, isMaster: isPlatformMaster({ role: s.role ?? null, companyId }) };
}

/** Exige master admin de plataforma (provisionamento, ações cross-tenant). */
export async function requireMasterAdmin(): Promise<{ ok: true; ctx: AdminCtx } | AuthFail> {
  const ctx = await getAdminContext();
  if (!ctx) return { ok: false, status: 401, error: 'no_admin_session' };
  if (!canProvisionTenant({ role: ctx.role, companyId: ctx.companyId })) return { ok: false, status: 403, error: 'master_required' };
  return { ok: true, ctx };
}

/** Exige admin autorizado a LER a empresa alvo (master OU company_admin da própria). */
export async function requireAdminForCompany(targetCompanyId: string): Promise<{ ok: true; ctx: AdminCtx } | AuthFail> {
  const ctx = await getAdminContext();
  if (!ctx) return { ok: false, status: 401, error: 'no_admin_session' };
  if (!canAdminReadCompany({ role: ctx.role, sessionCompanyId: ctx.companyId, targetCompanyId })) return { ok: false, status: 403, error: 'forbidden_company' };
  return { ok: true, ctx };
}

export interface TenantCtx { userId: string; companyId: string; role: string | null; isOwner: boolean }

/**
 * Resolve o usuário tenant pela sessão; company_id e papel vêm do banco (canônico).
 * `write:true` exige papel administrativo da própria corretora.
 */
export async function requireCompanyMember(opts: { write: boolean }): Promise<{ ok: true; ctx: TenantCtx; supabase: SupabaseClient } | AuthFail> {
  const c = await cookies();
  const s = await getIronSession<SessionData>(c, sessionOptions);
  if (!s.userId) return { ok: false, status: 401, error: 'no_session' };
  const supabase = supabaseService();
  const { data } = await supabase.from('users_v2').select('company_id, role, is_owner').eq('id', s.userId).maybeSingle();
  const companyId = (s.companyId ?? data?.company_id) ?? null;
  if (!companyId) return { ok: false, status: 404, error: 'no_company' };
  const role = (data?.role as string | null) ?? null;
  const isOwner = Boolean(data?.is_owner);
  if (opts.write && !canWriteTenantConfig({ role, isOwner })) return { ok: false, status: 403, error: 'admin_required' };
  return { ok: true, ctx: { userId: s.userId, companyId, role, isOwner }, supabase };
}
