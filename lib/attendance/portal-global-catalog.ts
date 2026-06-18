// 43P1.2 — acessor do Global Portal Catalog (seed gerado a partir do intake
// oficial). Sem credencial/PII. real_action_allowed sempre false.
import type { PortalDefinitionRecord } from '@/lib/attendance/portal-admin-sanitizers';
import { PORTAL_GLOBAL_CATALOG_SEED, PORTAL_GLOBAL_CATALOG_STATS, PORTAL_GLOBAL_CATALOG_GENERATED_AT } from '@/lib/attendance/portal-global-catalog-seed';

export function getGlobalPortalCatalogSeed(): PortalDefinitionRecord[] {
  return PORTAL_GLOBAL_CATALOG_SEED.map((d) => ({ ...d, scope: 'global' as const }));
}

export function getGlobalCatalogStats() {
  return { ...PORTAL_GLOBAL_CATALOG_STATS, generated_at: PORTAL_GLOBAL_CATALOG_GENERATED_AT };
}

export interface GlobalCatalogFilter {
  owner_key?: string | null;
  journey?: string | null;
  audience?: string | null;
  status?: string | null;
  confidence?: string | null;
}

/** Filtra o catálogo global por owner/journey/audience/status/confidence. */
export function filterGlobalCatalog(filter: GlobalCatalogFilter = {}): PortalDefinitionRecord[] {
  return getGlobalPortalCatalogSeed().filter((d) => {
    if (filter.owner_key && d.owner_key !== filter.owner_key) return false;
    if (filter.journey && !(d.supported_journeys || []).includes(filter.journey)) return false;
    if (filter.audience && String(d.metadata?.audience ?? '') !== filter.audience) return false;
    if (filter.status && d.status !== filter.status) return false;
    if (filter.confidence && String(d.metadata?.confidence ?? '') !== filter.confidence) return false;
    return true;
  });
}

/** Versão pública/sanitizada do catálogo (garante ausência de campos sensíveis). */
export function sanitizeGlobalCatalogEntry(d: PortalDefinitionRecord): Record<string, unknown> {
  return {
    portal_id: d.portal_id,
    label: d.label,
    owner_kind: d.owner_kind,
    owner_key: d.owner_key,
    base_url: d.base_url,
    login_url: d.login_url ?? null,
    supported_journeys: d.supported_journeys,
    auth_methods: d.auth_methods,
    challenge_profile: d.challenge_profile,
    browser_strategy: d.browser_strategy,
    status: d.status,
    scope: 'global',
    metadata: {
      audience: d.metadata?.audience ?? null,
      line_of_business: d.metadata?.line_of_business ?? null,
      journey_type: d.metadata?.journey_type ?? null,
      confidence: d.metadata?.confidence ?? null,
      official_sources: d.metadata?.official_sources ?? null,
      checked_at: d.metadata?.checked_at ?? null,
      source_document: d.metadata?.source_document ?? null,
      source_type: d.metadata?.source_type ?? null,
    },
    real_action_allowed: false,
  };
}
