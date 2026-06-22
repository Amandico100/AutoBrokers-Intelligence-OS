// SPEC-013 Fase B — classificação canônica de empresa (PURO, testável).
// Separa empresas-cliente de empresas-plataforma (Studio / Knowledge), garantindo
// que o Studio nunca seja confundido com corretora cliente. Usa o MESMO motor Smith;
// a classificação só governa fluxos (listagem, provisionamento, dashboard tenant).

export type CompanyKind = 'client' | 'platform_knowledge' | 'platform_blueprint_studio';
export const COMPANY_KINDS: CompanyKind[] = ['client', 'platform_knowledge', 'platform_blueprint_studio'];

// Default seguro: ausência de classificação = cliente (compatibilidade pré-migração).
export const DEFAULT_COMPANY_KIND: CompanyKind = 'client';

export function normalizeCompanyKind(raw: unknown): CompanyKind {
  return (typeof raw === 'string' && (COMPANY_KINDS as string[]).includes(raw)) ? (raw as CompanyKind) : DEFAULT_COMPANY_KIND;
}

export function isPlatformCompany(kind: unknown): boolean {
  return normalizeCompanyKind(kind).startsWith('platform_');
}
export function isClientCompany(kind: unknown): boolean {
  return normalizeCompanyKind(kind) === 'client';
}
export function isBlueprintStudio(kind: unknown): boolean {
  return normalizeCompanyKind(kind) === 'platform_blueprint_studio';
}
export function isGlobalKnowledge(kind: unknown): boolean {
  return normalizeCompanyKind(kind) === 'platform_knowledge';
}

// --- Decisões de fluxo (todas derivam da classificação) ---
/** Só cliente aparece na listagem normal de corretoras / pode operar no Dashboard tenant. */
export function visibleInClientListing(kind: unknown): boolean { return isClientCompany(kind); }
export function canUseTenantDashboard(kind: unknown): boolean { return isClientCompany(kind); }
/** Só cliente recebe provisionamento comercial automático (Core+Even via fluxo normal). */
export function shouldAutoProvisionOnCreate(kind: unknown): boolean { return isClientCompany(kind); }
/** Studio/Knowledge não recebem WhatsApp, Portal Browser, corridors operacionais, créditos de cliente. */
export function allowsClientOperations(kind: unknown): boolean { return isClientCompany(kind); }
/** Empresas-plataforma só podem ser acessadas/editadas por master admin. */
export function requiresMasterOnly(kind: unknown): boolean { return isPlatformCompany(kind); }
