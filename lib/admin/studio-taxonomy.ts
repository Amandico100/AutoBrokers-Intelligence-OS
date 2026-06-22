// SPEC-013 Fase B — taxonomia canônica (PURO). NÃO duplica agent_role: classifica a
// FINALIDADE do agente no Studio (autoria) e deriva o tipo de instância no tenant.

export type StudioSourceKind = 'global_core' | 'global_attendance' | 'global_auxiliary' | 'source_subagent';
export const STUDIO_SOURCE_KINDS: StudioSourceKind[] = ['global_core', 'global_attendance', 'global_auxiliary', 'source_subagent'];

export type TenantInstanceKind = 'core' | 'attendance' | 'auxiliary_runtime' | 'tenant_custom';

/** Source kind derivado do role para os Source Agents canônicos (Core/Even). */
export function studioSourceKindForRole(role: string | null | undefined): StudioSourceKind | null {
  if (role === 'core') return 'global_core';
  if (role === 'attendance') return 'global_attendance';
  return null; // auxiliary/subagent são marcados explicitamente
}

/** Tipo da instância no tenant (derivado de role + se é runtime de auxiliar). */
export function tenantInstanceKind(role: string | null | undefined, isAuxiliaryRuntime = false): TenantInstanceKind {
  if (isAuxiliaryRuntime) return 'auxiliary_runtime';
  if (role === 'core') return 'core';
  if (role === 'attendance') return 'attendance';
  return 'tenant_custom';
}

/** Só Source Agent marcado como global_auxiliary pode virar Auxiliar na Galeria. */
export function canPublishAsAuxiliary(studioSourceKind: string | null | undefined): boolean {
  return studioSourceKind === 'global_auxiliary';
}

/** Core e Even nunca podem ser publicados como Auxiliar. */
export function isGlobalChatOrAttendance(studioSourceKind: string | null | undefined): boolean {
  return studioSourceKind === 'global_core' || studioSourceKind === 'global_attendance';
}
