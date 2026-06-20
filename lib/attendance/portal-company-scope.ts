// 43P4.2A — resolução PURA de escopo de company (multi-tenant). SELF-CONTAINED
// (sem imports de runtime) para ser testável offline via .mjs.
//
// Precedência:
//   1. Sessão já vinculada a uma company (tenant travado) → ignora override.
//   2. Master admin com company_id solicitado e VÁLIDO → usa o escolhido.
//   3. users_v2.company_id do próprio usuário.
//   4. Única company existente (piloto single-tenant).
// Admin sem escopo resolvível → company_scope_required (não adivinha tenant).

export interface PortalCompanyScopeInput {
  is_admin: boolean;
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
  let isMaster = false;
  if (input.is_admin) {
    isMaster = true;
    if (input.requested_company && input.requested_company_exists) companyId = input.requested_company;
    else if (input.users_v2_company) companyId = input.users_v2_company;
    else if (input.single_company_id) companyId = input.single_company_id;
  } else {
    // Usuário comum sem company na sessão NUNCA escolhe tenant via header.
    if (input.users_v2_company) companyId = input.users_v2_company;
    else if (input.single_company_id) companyId = input.single_company_id;
  }
  return { companyId, isMaster, company_scope_required: !companyId && input.is_admin };
}
