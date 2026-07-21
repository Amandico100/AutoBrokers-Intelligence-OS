// TA2-B — wrappers de autorização server-side (iron-session). Nunca confiam só na
// presença do cookie: decodificam e validam papel real. Decisões puras em
// admin-auth-policy.ts. Usado pelas rotas admin (master) e tenant (dashboard).
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { adminSessionOptions, sessionOptions, type AdminSessionData, type SessionData } from '@/lib/iron-session';
import { canAdminReadCompany, canProvisionTenant, canWriteTenantConfig, isPlatformMaster, sameOriginOk, tenantCompanyConsistent } from '@/lib/admin/admin-auth-policy';

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

/**
 * TA2-C 0.1 — confirma que o admin AINDA existe na fonte canônica (admin_users).
 * Garante que remoção de acesso tenha efeito imediato (a sessão sozinha não basta).
 */
async function adminPrincipalExists(supabase: SupabaseClient, adminId: string): Promise<boolean> {
  try { const { data } = await supabase.from('admin_users').select('id').eq('id', adminId).maybeSingle(); return Boolean(data?.id); }
  catch { return false; }
}

/** Exige master admin de plataforma (provisionamento, ações cross-tenant). Valida no banco. */
export async function requireMasterAdmin(): Promise<{ ok: true; ctx: AdminCtx; supabase: SupabaseClient } | AuthFail> {
  const ctx = await getAdminContext();
  if (!ctx) return { ok: false, status: 401, error: 'no_admin_session' };
  if (!canProvisionTenant({ role: ctx.role, companyId: ctx.companyId })) return { ok: false, status: 403, error: 'master_required' };
  const supabase = supabaseService();
  if (!(await adminPrincipalExists(supabase, ctx.adminId))) return { ok: false, status: 403, error: 'admin_revoked' };
  return { ok: true, ctx, supabase };
}

/** Exige admin autorizado a LER a empresa alvo (master OU company_admin da própria). Valida no banco. */
export async function requireAdminForCompany(targetCompanyId: string): Promise<{ ok: true; ctx: AdminCtx; supabase: SupabaseClient } | AuthFail> {
  const ctx = await getAdminContext();
  if (!ctx) return { ok: false, status: 401, error: 'no_admin_session' };
  if (!canAdminReadCompany({ role: ctx.role, sessionCompanyId: ctx.companyId, targetCompanyId })) return { ok: false, status: 403, error: 'forbidden_company' };
  const supabase = supabaseService();
  if (!(await adminPrincipalExists(supabase, ctx.adminId))) return { ok: false, status: 403, error: 'admin_revoked' };
  return { ok: true, ctx, supabase };
}

export interface TenantCtx { userId: string; companyId: string; role: string | null; isOwner: boolean }

/**
 * Resolve o usuário tenant. TA2-C 0.2: o BANCO é a fonte de verdade de empresa e
 * papel; papel removido tem efeito imediato. `write:true` exige papel
 * administrativo da própria corretora.
 *
 * SPEC-047/048 (multi-empresa): se a sessão tem empresa ATIVA (seletor), ela
 * vale — validada em company_members A CADA request, com papel/is_owner DO
 * VÍNCULO daquela empresa (o mesmo usuário pode ser dono numa e membro na
 * outra). Sem escolha, vale a primária (users_v2.company_id). Era ESTE seam
 * ignorar o seletor que fazia os dados de uma corretora vazarem na outra.
 */
export async function requireCompanyMember(opts: { write: boolean }): Promise<{ ok: true; ctx: TenantCtx; supabase: SupabaseClient } | AuthFail> {
  const c = await cookies();
  const s = await getIronSession<SessionData>(c, sessionOptions);
  if (!s.userId) return { ok: false, status: 401, error: 'no_session' };
  const supabase = supabaseService();

  const active = s.activeCompanyId || null;
  if (active) {
    const { data: member } = await supabase
      .from('company_members')
      .select('company_id, role, is_owner')
      .eq('user_id', s.userId)
      .eq('company_id', active)
      .eq('status', 'active')
      .maybeSingle();
    if (!member?.company_id) return { ok: false, status: 403, error: 'no_membership_active_company' };
    const role = (member.role as string | null) ?? null;
    const isOwner = Boolean(member.is_owner);
    if (opts.write && !canWriteTenantConfig({ role, isOwner })) return { ok: false, status: 403, error: 'admin_required' };
    return { ok: true, ctx: { userId: s.userId, companyId: member.company_id, role, isOwner }, supabase };
  }

  const { data } = await supabase.from('users_v2').select('company_id, role, is_owner').eq('id', s.userId).maybeSingle();
  const dbCompanyId = (data?.company_id as string | null) ?? null;
  if (!dbCompanyId) return { ok: false, status: 404, error: 'no_company' };
  if (!tenantCompanyConsistent({ sessionCompanyId: s.companyId ?? null, dbCompanyId })) {
    return { ok: false, status: 403, error: 'session_company_divergent' };
  }
  const role = (data?.role as string | null) ?? null;
  const isOwner = Boolean(data?.is_owner);
  if (opts.write && !canWriteTenantConfig({ role, isOwner })) return { ok: false, status: 403, error: 'admin_required' };
  return { ok: true, ctx: { userId: s.userId, companyId: dbCompanyId, role, isOwner }, supabase };
}

/** TA2-C 0.3 — same-origin para mutações (defesa em profundidade). Retorna AuthFail ou null. */
export function assertSameOrigin(req: { headers: { get(name: string): string | null } }): AuthFail | null {
  const origin = req.headers.get('origin');
  const host = req.headers.get('host') ?? req.headers.get('x-forwarded-host');
  if (!sameOriginOk({ origin, host })) return { ok: false, status: 403, error: 'cross_origin_blocked' };
  return null;
}
