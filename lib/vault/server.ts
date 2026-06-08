// Server-only helpers do Vault (auth + company + sanitização + auditoria).
// NÃO importar em componentes client. Reusa o padrão de sessão dos Auxiliares.
import type { SupabaseClient } from '@supabase/supabase-js';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

// Reexporta para as rotas do Vault usarem um único ponto.
export { resolveSessionCompany, getSupabaseAdmin };

// --- Valores permitidos (espelham os comentários do DDL 39A1) ---
export const CONNECTION_STATUSES = [
  'draft', 'configuring', 'connected', 'disconnected', 'error', 'revoked', 'blocked',
] as const;
export const HEALTH_STATUSES = ['unknown', 'healthy', 'degraded', 'failed'] as const;
export const PERMISSION_STATUSES = ['active', 'paused', 'revoked', 'expired'] as const;
export const RISK_LEVELS = ['low', 'medium', 'high', 'critical'] as const;

// --- Bloqueio de segredos no payload ---
export const SENSITIVE_KEYS = [
  'token', 'access_token', 'refresh_token', 'client_token',
  'password', 'secret', 'api_key', 'key', 'credential', 'credentials',
];

export const SECRET_REJECTION_MESSAGE =
  'Credenciais devem ser configuradas por fluxo seguro de conexão, não por esta rota.';

/** Varre profundamente o payload por nomes de campo sensíveis (match exato, case-insensitive). */
export function payloadHasSecret(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some((v) => payloadHasSecret(v));
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (SENSITIVE_KEYS.includes(k.toLowerCase())) return true;
    if (v && typeof v === 'object' && payloadHasSecret(v)) return true;
  }
  return false;
}

export function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

export interface VaultAuditEntry {
  company_id: string;
  event_type: string;
  action?: string | null;
  status?: string | null;
  risk_level?: string | null;
  tenant_connection_id?: string | null;
  approval_request_id?: string | null;
  actor_user_id?: string | null;
  metadata?: Record<string, unknown>;
}

/** Grava um evento de auditoria (best-effort; nunca derruba a operação principal). */
export async function writeAudit(supabase: SupabaseClient, entry: VaultAuditEntry): Promise<void> {
  try {
    await supabase.from('vault_audit_log').insert({
      company_id: entry.company_id,
      event_type: entry.event_type,
      action: entry.action ?? null,
      status: entry.status ?? null,
      risk_level: entry.risk_level ?? null,
      tenant_connection_id: entry.tenant_connection_id ?? null,
      approval_request_id: entry.approval_request_id ?? null,
      actor_user_id: entry.actor_user_id ?? null,
      metadata: entry.metadata ?? {},
    });
  } catch (e) {
    console.error('[VAULT audit] failed to write event', e);
  }
}
