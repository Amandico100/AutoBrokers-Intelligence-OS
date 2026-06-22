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

/**
 * Same-origin para mutações (defesa em profundidade junto do cookie sameSite=lax).
 * Sem Origin → não bloqueia (alguns clientes legítimos não enviam). Com Origin →
 * o host precisa bater com o Host do servidor.
 */
export function sameOriginOk(p: { origin: string | null; host: string | null }): boolean {
  if (!p.origin) return true;
  if (!p.host) return false;
  try { return new URL(p.origin).host === p.host; } catch { return false; }
}

/**
 * Consistência sessão × banco para usuário tenant. O banco é a fonte de verdade:
 * se a sessão declara uma empresa diferente da de `users_v2`, bloquear.
 */
export function tenantCompanyConsistent(p: { sessionCompanyId: string | null; dbCompanyId: string | null }): boolean {
  if (!p.dbCompanyId) return false; // sem empresa no banco = sem acesso
  if (!p.sessionCompanyId) return true; // sessão sem empresa: usa a do banco
  return p.sessionCompanyId === p.dbCompanyId;
}
