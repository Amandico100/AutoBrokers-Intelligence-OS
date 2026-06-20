// 43P4.2A / 43P4.2A.1 — escopo de company (multi-tenant). SELF-CONTAINED
// (sem imports de runtime) para ser testável offline via .mjs.
//
// "Master" = AdminSessionData.role === 'master_admin' (admin de plataforma).
// company_admin e usuário comum NUNCA enumeram/trocam de tenant: ficam
// travados na própria company da sessão.
//
// Precedência de escopo:
//   1. Sessão já vinculada a uma company (tenant travado) → ignora override.
//   2. Master com company_id solicitado e VÁLIDO → usa o escolhido.
//   3. users_v2.company_id do próprio usuário.
//   4. Única company existente (piloto single-tenant).
// Master sem escopo resolvível → company_scope_required (não adivinha tenant).

export interface PortalCompanyScopeInput {
  is_master: boolean;
  session_company: string | null;
  users_v2_company: string | null;
  requested_company: string | null;
  requested_company_exists: boolean;
  single_company_id: string | null;
}

export interface PortalCompanyScope {
  companyId: string | null;
  isMaster: boolean;
  company_scope_required: boolean;
}

export function resolvePortalCompanyScope(input: PortalCompanyScopeInput): PortalCompanyScope {
  if (input.session_company) {
    // Tenant travado na sessão: NUNCA aceita override de outro tenant.
    return { companyId: input.session_company, isMaster: false, company_scope_required: false };
  }
  let companyId: string | null = null;
  if (input.is_master) {
    if (input.requested_company && input.requested_company_exists) companyId = input.requested_company;
    else if (input.users_v2_company) companyId = input.users_v2_company;
    else if (input.single_company_id) companyId = input.single_company_id;
  } else {
    // Não-master sem company na sessão NUNCA escolhe tenant via header/cookie.
    if (input.users_v2_company) companyId = input.users_v2_company;
    else if (input.single_company_id) companyId = input.single_company_id;
  }
  return { companyId, isMaster: input.is_master, company_scope_required: !companyId && input.is_master };
}

// 43P4.2A.1 — P1: decide o MODO de enumeração de companies (anti-vazamento
// multi-tenant). Apenas master enumera a lista global; tenant vê só a própria.
export type CompanyListingMode = 'all' | 'own' | 'none';
export function resolveCompanyListingMode(input: { is_master: boolean; company_id: string | null }): CompanyListingMode {
  if (input.is_master) return 'all';
  if (input.company_id) return 'own';
  return 'none';
}
