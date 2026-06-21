// TA2-B — políticas de autorização PURAS (testáveis offline, sem I/O).
// Centralizam quem pode o quê; as rotas só decodificam a sessão e chamam estas.

/** Papéis tenant que podem ESCREVER configuração da própria corretora. */
export const TENANT_WRITE_ROLES = ['owner', 'admin', 'admin_company', 'master_admin'];

/** master_admin de plataforma = role master_admin SEM company travada. */
export function isPlatformMaster(p: { role: string | null; companyId: string | null }): boolean {
  return p.role === 'master_admin' && !p.companyId;
}

/** Usuário tenant pode escrever (editar AutoBrokers/Even) na própria corretora? */
export function canWriteTenantConfig(p: { role: string | null; isOwner: boolean }): boolean {
  return Boolean(p.isOwner || (p.role && TENANT_WRITE_ROLES.includes(p.role)));
}

/** Admin pode LER/ESPELHAR a config de `targetCompanyId` no Portal Admin? */
export function canAdminReadCompany(p: { role: string | null; sessionCompanyId: string | null; targetCompanyId: string }): boolean {
  if (isPlatformMaster({ role: p.role, companyId: p.sessionCompanyId })) return true;
  // company_admin só a própria company.
  return p.role === 'company_admin' && !!p.sessionCompanyId && p.sessionCompanyId === p.targetCompanyId;
}

/** Apenas master pode provisionar/alterar estrutura de qualquer corretora. */
export function canProvisionTenant(p: { role: string | null; companyId: string | null }): boolean {
  return isPlatformMaster(p);
}
