// InfoCap Policy Lookup Connector — read-only foundation (42I2).
//
// Resolve a configuração da corretora via Vault `tenant_connections` (template
// global `infocap`) e expõe um contrato normalizado de lookup de apólice.
//
// IMPORTANTE:
// - Credenciais são POR CORRETORA e ficam SEMPRE no Vault/tenant_connections
//   (referência em `encrypted_secret_ref`). NUNCA em código/env/prompt/RAG/log.
// - Este batch é a FUNDAÇÃO: não há especificação verificada do endpoint/payload
//   /response da API InfoCap no repositório, então NÃO inventamos chamada HTTP.
//   Conexão ausente → `blocked_not_configured`; conexão presente → `unsupported`
//   (a chamada real read-only será implementada no próximo batch, a partir da
//   documentação oficial). NUNCA fabrica evidência de cobertura.
import { getAdminClient } from '@/lib/attendance/support-destinations';

export type InfocapLookupStatus =
  | 'found'
  | 'client_found'
  | 'policy_lookup_pending'
  | 'not_found'
  | 'multiple_matches'
  | 'blocked_missing_credentials'
  | 'blocked_not_configured'
  | 'provider_error'
  | 'auth_error'
  | 'unsupported';

export interface InfocapPolicyMatch {
  policy_ref: string;
  insurer_key: string | null;
  product: string | null;
  line_kind: string | null;
  policy_status: string | null;
  masked_policy_number: string | null;
  holder_name_masked: string | null;
}

export interface InfocapCoverageEvidence {
  source: 'infocap';
  source_ref: string;
  verified_at: string;
  verified_by: 'connector';
  confidence: 'low' | 'medium' | 'high';
  coverage_summary: string;
  limitations: string[];
  human_required: boolean;
}

export interface InfocapPolicyLookupResult {
  ok: boolean;
  status: InfocapLookupStatus;
  source: 'infocap';
  source_ref?: string;
  matches?: InfocapPolicyMatch[];
  selected?: InfocapPolicyMatch | null;
  coverage_evidence?: InfocapCoverageEvidence | null;
  verification_status?: 'verified_by_connector' | 'unverified';
  blockers?: string[];
  requires_human?: boolean;
  notes?: string[];
  // Diagnóstico seguro (sem PII/segredo) — 42I2.1A
  provider?: 'infocap';
  query_strategy?: 'document_cpf' | 'customer_name' | 'fallback';
  search_path?: string;
  search_param?: string;
  http_status?: number;
  result_count?: number;
  // Cliente localizado sem apólice — 42I2.1C (refs sanitizadas, sem PII crua)
  infocap_client_found?: boolean;
  client_ref_available?: boolean;
  client_ref_fields?: string[];
  client_ref?: Record<string, unknown>;
  next_possible_endpoints?: string[];
}

export interface InfocapPolicyLookupInput {
  companyId: string;
  caseId: string;
  documentRef?: string;
  customerPhone?: string;
  customerName?: string;
  policyNumber?: string;
}

const INFOCAP_SLUG = 'infocap';
const CONNECTED_STATUSES = new Set(['connected']);

function backendUrl(): string {
  return (
    process.env.ATTENDANCE_BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.BACKEND_URL ||
    'http://localhost:8000'
  );
}

/** Resolve a conexão InfoCap da corretora (sem expor segredo). */
async function resolveInfocapConnection(companyId: string): Promise<{
  connected: boolean;
  status: string | null;
  baseUrlConfigured: boolean;
  hasSecretRef: boolean;
  connectionId: string | null;
}> {
  const supabaseAdmin = getAdminClient();

  // 1. Template global do conector InfoCap
  const { data: tpl } = await supabaseAdmin
    .from('connector_templates')
    .select('id')
    .eq('slug', INFOCAP_SLUG)
    .eq('is_active', true)
    .maybeSingle();
  if (!tpl?.id) {
    return { connected: false, status: null, baseUrlConfigured: false, hasSecretRef: false, connectionId: null };
  }

  // 2. Conexão da corretora para esse template
  const { data: conn } = await supabaseAdmin
    .from('tenant_connections')
    .select('id, status, connection_config, encrypted_secret_ref')
    .eq('company_id', companyId)
    .eq('connector_template_id', tpl.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!conn) {
    return { connected: false, status: null, baseUrlConfigured: false, hasSecretRef: false, connectionId: null };
  }

  const config = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
  const baseUrlConfigured =
    typeof (config as any).base_url === 'string' && (config as any).base_url.length > 0;
  const hasSecretRef = typeof conn.encrypted_secret_ref === 'string' && conn.encrypted_secret_ref.length > 0;

  return {
    connected: CONNECTED_STATUSES.has(conn.status),
    status: conn.status ?? null,
    baseUrlConfigured,
    hasSecretRef,
    connectionId: conn.id ?? null,
  };
}

export interface InfocapDiagnostics {
  provider: 'infocap';
  template_found: boolean;
  tenant_connection_found: boolean;
  status: string | null;
  base_url_configured: boolean;
  secret_ref_present: boolean;
  ready_for_real_lookup: boolean;
  blockers: string[];
}

/**
 * Diagnóstico SEGURO da conexão InfoCap da corretora (sem expor segredo/login/token).
 * Apenas booleanos/status para confirmar se o cadastro no Vault está pronto.
 */
export async function diagnoseInfocapConnection(companyId: string): Promise<InfocapDiagnostics> {
  const blockers: string[] = [];
  const supabaseAdmin = getAdminClient();

  // 1. Template global
  const { data: tpl } = await supabaseAdmin
    .from('connector_templates')
    .select('id')
    .eq('slug', INFOCAP_SLUG)
    .eq('is_active', true)
    .maybeSingle();
  const templateFound = Boolean(tpl?.id);
  if (!templateFound) blockers.push('infocap_template_not_found');

  // 2. Conexão da corretora
  let connectionFound = false;
  let status: string | null = null;
  let baseUrlConfigured = false;
  let secretRefPresent = false;

  if (templateFound) {
    const { data: conn } = await supabaseAdmin
      .from('tenant_connections')
      .select('status, connection_config, encrypted_secret_ref')
      .eq('company_id', companyId)
      .eq('connector_template_id', tpl!.id)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (conn) {
      connectionFound = true;
      status = conn.status ?? null;
      const config = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
      baseUrlConfigured = typeof (config as any).base_url === 'string' && (config as any).base_url.length > 0;
      secretRefPresent = typeof conn.encrypted_secret_ref === 'string' && conn.encrypted_secret_ref.length > 0;
    } else {
      blockers.push('tenant_connection_not_found');
    }
  }

  if (connectionFound && status !== 'connected') blockers.push('connection_not_connected');
  if (connectionFound && !secretRefPresent) blockers.push('missing_credentials');
  if (connectionFound && !baseUrlConfigured) blockers.push('missing_base_url');

  const readyForRealLookup =
    templateFound && connectionFound && status === 'connected' && secretRefPresent && baseUrlConfigured;

  return {
    provider: 'infocap',
    template_found: templateFound,
    tenant_connection_found: connectionFound,
    status,
    base_url_configured: baseUrlConfigured,
    secret_ref_present: secretRefPresent,
    ready_for_real_lookup: readyForRealLookup,
    blockers,
  };
}

/**
 * Lookup read-only de apólice via InfoCap. Não faz chamada HTTP real ainda
 * (sem spec verificada do endpoint). Nunca fabrica evidência de cobertura.
 */
export async function lookupInfocapPolicy(input: InfocapPolicyLookupInput): Promise<InfocapPolicyLookupResult> {
  try {
    const conn = await resolveInfocapConnection(input.companyId);

    if (!conn.connected) {
      return {
        ok: false,
        status: 'blocked_not_configured',
        source: 'infocap',
        verification_status: 'unverified',
        blockers: ['infocap_connection_not_configured'],
        requires_human: false,
        notes: [
          'Conexão InfoCap não configurada/ativa para esta corretora. Configure em Vault/tenant_connections (credenciais por corretora).',
        ],
      };
    }

    if (!conn.hasSecretRef) {
      return {
        ok: false,
        status: 'blocked_missing_credentials',
        source: 'infocap',
        verification_status: 'unverified',
        blockers: ['infocap_missing_credentials'],
        requires_human: false,
        notes: ['Conexão InfoCap presente, mas sem credenciais (encrypted_secret_ref) no Vault.'],
      };
    }
    if (!conn.baseUrlConfigured || !conn.connectionId) {
      return {
        ok: false,
        status: 'blocked_not_configured',
        source: 'infocap',
        verification_status: 'unverified',
        blockers: ['infocap_missing_base_url'],
        requires_human: false,
        notes: ['Conexão InfoCap sem base_url configurada.'],
      };
    }

    // Chamada read-only REAL: delega ao backend (que decifra as credenciais e
    // chama a InfoCap/CorpAPI). O segredo nunca trafega pelo Web.
    const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
    if (!internalKey) {
      return {
        ok: false,
        status: 'provider_error',
        source: 'infocap',
        verification_status: 'unverified',
        blockers: ['internal_key_missing'],
        requires_human: false,
        notes: ['Chave interna Next↔Backend não configurada.'],
      };
    }

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15_000);
      const res = await fetch(`${backendUrl()}/attendance/connectors/infocap/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
        body: JSON.stringify({
          company_id: input.companyId,
          tenant_connection_id: conn.connectionId,
          document: input.documentRef || undefined,
          name: input.customerName || undefined,
        }),
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (!res.ok) {
        return {
          ok: false,
          status: 'provider_error',
          source: 'infocap',
          verification_status: 'unverified',
          blockers: [`backend_http_${res.status}`],
          requires_human: false,
        };
      }
      const data = (await res.json()) as InfocapPolicyLookupResult;
      // Confia no shape sanitizado retornado pelo backend (sem segredo/CPF).
      return { ...data, source: 'infocap' };
    } catch (e: any) {
      return {
        ok: false,
        status: 'provider_error',
        source: 'infocap',
        verification_status: 'unverified',
        blockers: [e?.name === 'AbortError' ? 'backend_timeout' : 'backend_fetch_error'],
        requires_human: false,
      };
    }
  } catch {
    return {
      ok: false,
      status: 'provider_error',
      source: 'infocap',
      verification_status: 'unverified',
      blockers: ['infocap_resolve_error'],
      requires_human: false,
      notes: ['Falha ao resolver a conexão InfoCap.'],
    };
  }
}
