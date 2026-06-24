// R1A.1 - selecao segura de tenant_connections para o Contract Capture Gate.
// Helper puro: nao acessa Supabase, Vault, backend ou provider.

export type InfocapContractProbeResponseStatus =
  | 'probe_ready'
  | 'blocked_missing_credentials'
  | 'ambiguous_connection';

export type InfocapContractProbeSelectionStatus =
  | 'connection_usable'
  | 'reconnect_required'
  | 'manual_connection_cleanup_required';

export interface InfocapConnectionCandidate {
  id?: string | null;
  company_id?: string | null;
  connector_template_id?: string | null;
  status?: string | null;
  health_status?: string | null;
  encrypted_secret_ref?: string | null;
  connection_config?: unknown;
  metadata?: unknown;
  created_at?: string | null;
}

export interface InfocapConnectionResolutionSummary {
  total_infocap_connections: number;
  inactive_connection_count: number;
  operational_status_count: number;
  vault_secret_present_count: number;
  base_url_configured_count: number;
  eligible_connection_count: number;
  vault_configured: boolean;
  selection_status: InfocapContractProbeSelectionStatus;
  selection_strategy: 'scope_status_vault_base_url_single';
}

export interface InfocapConnectionResolutionDecision {
  selectedConnectionId: string | null;
  responseStatus: InfocapContractProbeResponseStatus;
  selectionStatus: InfocapContractProbeSelectionStatus;
  summary: InfocapConnectionResolutionSummary;
}

const OPERATIONAL_STATUSES = new Set(['connected', 'active', 'healthy']);
const INACTIVE_STATUSES = new Set(['archived', 'inactive', 'revoked', 'disconnected', 'blocked']);

function norm(value: unknown): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasSecretRef(conn: InfocapConnectionCandidate): boolean {
  return typeof conn.encrypted_secret_ref === 'string' && conn.encrypted_secret_ref.trim().length > 0;
}

function hasEffectiveBaseUrl(conn: InfocapConnectionCandidate, providerDefaultBaseUrl?: string): boolean {
  const config = isPlainObject(conn.connection_config) ? conn.connection_config : {};
  const configured = typeof config.base_url === 'string' && config.base_url.trim().length > 0;
  const providerDefault = typeof providerDefaultBaseUrl === 'string' && providerDefaultBaseUrl.trim().length > 0;
  return configured || providerDefault;
}

function isInactive(conn: InfocapConnectionCandidate): boolean {
  return INACTIVE_STATUSES.has(norm(conn.status));
}

function hasOperationalStatus(conn: InfocapConnectionCandidate): boolean {
  const status = norm(conn.status);
  const health = norm(conn.health_status);
  if (health === 'failed') return false;
  return OPERATIONAL_STATUSES.has(status) || health === 'healthy';
}

function inScope(
  conn: InfocapConnectionCandidate,
  companyId?: string,
  connectorTemplateId?: string,
): boolean {
  if (companyId && conn.company_id && conn.company_id !== companyId) return false;
  if (connectorTemplateId && conn.connector_template_id && conn.connector_template_id !== connectorTemplateId) return false;
  return true;
}

export function resolveInfocapContractProbeConnection(
  candidates: InfocapConnectionCandidate[],
  options: {
    companyId?: string;
    connectorTemplateId?: string;
    providerDefaultBaseUrl?: string;
  } = {},
): InfocapConnectionResolutionDecision {
  const scoped = candidates.filter((conn) => inScope(conn, options.companyId, options.connectorTemplateId));
  const inactive = scoped.filter(isInactive);
  const operational = scoped.filter((conn) => !isInactive(conn) && hasOperationalStatus(conn));
  const withSecret = scoped.filter((conn) => !isInactive(conn) && hasSecretRef(conn));
  const withBaseUrl = scoped.filter((conn) => !isInactive(conn) && hasEffectiveBaseUrl(conn, options.providerDefaultBaseUrl));
  const eligible = scoped.filter((conn) => (
    !isInactive(conn)
    && hasOperationalStatus(conn)
    && hasSecretRef(conn)
    && hasEffectiveBaseUrl(conn, options.providerDefaultBaseUrl)
  ));

  let selectedConnectionId: string | null = null;
  let responseStatus: InfocapContractProbeResponseStatus = 'blocked_missing_credentials';
  let selectionStatus: InfocapContractProbeSelectionStatus = 'reconnect_required';

  if (eligible.length === 1) {
    selectedConnectionId = eligible[0].id ?? null;
    responseStatus = 'probe_ready';
    selectionStatus = 'connection_usable';
  } else if (eligible.length > 1) {
    responseStatus = 'ambiguous_connection';
    selectionStatus = 'manual_connection_cleanup_required';
  }

  return {
    selectedConnectionId,
    responseStatus,
    selectionStatus,
    summary: {
      total_infocap_connections: scoped.length,
      inactive_connection_count: inactive.length,
      operational_status_count: operational.length,
      vault_secret_present_count: withSecret.length,
      base_url_configured_count: withBaseUrl.length,
      eligible_connection_count: eligible.length,
      vault_configured: withSecret.length > 0,
      selection_status: selectionStatus,
      selection_strategy: 'scope_status_vault_base_url_single',
    },
  };
}

export function sanitizeConnectionResolutionForOutput(
  decision: InfocapConnectionResolutionDecision,
): InfocapConnectionResolutionSummary {
  return { ...decision.summary };
}
