// SPEC-013 B1 (PURO, testável) — regras de publicação de Auxiliar Global a partir de
// Source Agent do Studio + lifecycle de instalação por tenant. Reusa o motor existente
// (SPEC-002: auxiliary_templates.default_config.runtime + tenant_auxiliaries.config.runtime).

/** Só Source Agent do Blueprint Studio marcado como global_auxiliary pode virar Auxiliar Global.
 *  Core/Even (global_core/global_attendance) e source_subagent NUNCA podem. */
export function canPublishAgentAsGlobalAuxiliary(p: { companyKind: string | null; studioSourceKind: string | null }): boolean {
  return p.companyKind === 'platform_blueprint_studio' && p.studioSourceKind === 'global_auxiliary';
}

/** Motivo legível do bloqueio (para UI/erros). */
export function publishBlockReason(p: { companyKind: string | null; studioSourceKind: string | null }): string | null {
  if (p.companyKind !== 'platform_blueprint_studio') return 'fonte_precisa_ser_studio';
  if (p.studioSourceKind === 'global_core' || p.studioSourceKind === 'global_attendance') return 'core_ou_even_nao_publicavel';
  if (p.studioSourceKind === 'source_subagent') return 'subagent_nao_publicavel';
  if (p.studioSourceKind !== 'global_auxiliary') return 'fonte_precisa_ser_global_auxiliary';
  return null;
}

// --- Lifecycle de tenant_auxiliaries (status honesto) --------------------------
export type TenantAuxStatus = 'active' | 'paused' | 'awaiting_runtime' | 'uninstalled' | 'error';
export const TENANT_AUX_STATES: TenantAuxStatus[] = ['active', 'paused', 'awaiting_runtime', 'uninstalled', 'error'];

export type TenantAuxAction = 'pause' | 'resume' | 'uninstall';

/** Próximo status a partir da ação (puro). null = ação inválida para o status atual. */
export function nextTenantAuxStatus(current: TenantAuxStatus, action: TenantAuxAction): TenantAuxStatus | null {
  if (action === 'pause') return (current === 'active' || current === 'awaiting_runtime') ? 'paused' : null;
  if (action === 'resume') return current === 'paused' ? 'active' : null;
  if (action === 'uninstall') return current === 'uninstalled' ? null : 'uninstalled';
  return null;
}

/** Rótulo honesto para a UI tenant. */
export function tenantAuxStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'active': return 'Pronto';
    case 'paused': return 'Pausado';
    case 'awaiting_runtime': return 'Aguardando configuração';
    case 'uninstalled': return 'Removido';
    case 'error': return 'Erro';
    default: return 'Instalado';
  }
}
