// Tenant Activation 1 — resolução PURA de corredores operáveis por corretora.
// SELF-CONTAINED (testável). Regra SPEC-012: corredor GLOBAL só opera se houver
// ativação em tenant_corridors (status active); corredor tenant-scoped (company_id
// da própria corretora) continua disponível. Espelha o padrão de Auxiliares.

export interface CorridorTemplateLite {
  id: string;
  corridor_key: string;
  subcorridor_key: string | null;
  scope: 'global' | 'tenant' | null;
  company_id: string | null; // tenant-scoped quando preenchido
  is_active: boolean;        // ativo no catálogo (não confunde com ativação por tenant)
}

export interface TenantCorridorActivation {
  company_id: string;
  corridor_template_id: string;
  status: 'active' | 'paused' | string;
}

/** Um corredor é operável para a corretora? */
export function isCorridorOperable(
  tpl: CorridorTemplateLite,
  companyId: string,
  activations: TenantCorridorActivation[],
): boolean {
  if (!tpl.is_active) return false;
  // tenant-scoped: pertence à própria corretora → operável (sem precisar de ativação extra)
  if (tpl.company_id) return tpl.company_id === companyId;
  // global: só opera se houver ativação active para esta corretora
  return activations.some((a) => a.corridor_template_id === tpl.id && a.company_id === companyId && a.status === 'active');
}

/** Filtra os corredores operáveis para a corretora. */
export function resolveOperableCorridors(
  templates: CorridorTemplateLite[],
  companyId: string,
  activations: TenantCorridorActivation[],
): CorridorTemplateLite[] {
  return templates.filter((t) => isCorridorOperable(t, companyId, activations));
}

/**
 * Modo de degradação seguro: se a tabela tenant_corridors AINDA não existe
 * (migration não aplicada), o runtime não pode quebrar. `legacyFallback=true`
 * mantém o comportamento antigo (global ativo disponível) até a migration.
 */
export function resolveCorridorsWithFallback(
  templates: CorridorTemplateLite[],
  companyId: string,
  activations: TenantCorridorActivation[] | null, // null = tabela indisponível
  legacyFallback: boolean,
): { corridors: CorridorTemplateLite[]; mode: 'activated' | 'legacy_fallback' } {
  if (activations === null) {
    if (legacyFallback) return { corridors: templates.filter((t) => t.is_active), mode: 'legacy_fallback' };
    return { corridors: templates.filter((t) => t.is_active && t.company_id === companyId), mode: 'legacy_fallback' };
  }
  return { corridors: resolveOperableCorridors(templates, companyId, activations), mode: 'activated' };
}
