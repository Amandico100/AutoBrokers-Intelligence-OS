// Tipos do Vault / Conectores / HITL (camada de produto). Consumidos pelo client em 39A3.

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface ConnectorTemplate {
  id: string;
  slug: string;
  name: string;
  description?: string | null;
  category: string;
  provider?: string | null;
  connector_kind: string;
  auth_type: string;
  risk_level: string;
  requires_approval_default?: boolean;
  capabilities?: unknown;
  required_fields?: unknown;
  metadata?: unknown;
  is_active?: boolean;
  [key: string]: unknown;
}

export interface TenantConnection {
  id: string;
  company_id: string;
  connector_template_id: string;
  name: string;
  status: string;
  health_status: string;
  technical_ref_type?: string | null;
  technical_ref_id?: string | null;
  connection_config?: unknown;
  metadata?: unknown;
  owner_user_id?: string | null;
  last_checked_at?: string | null;
  last_used_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  [key: string]: unknown;
}

export interface PermissionGrant {
  id: string;
  company_id: string;
  tenant_connection_id: string;
  subject_type: string;
  subject_id?: string | null;
  allowed_actions?: string[] | unknown;
  requires_approval?: boolean;
  risk_level?: string;
  status?: string;
  expires_at?: string | null;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface ApprovalRequest {
  id: string;
  company_id: string;
  tenant_connection_id?: string | null;
  permission_grant_id?: string | null;
  subject_type: string;
  subject_id?: string | null;
  action_type: string;
  status: string;
  risk_level?: string;
  preview?: unknown;
  request_payload?: unknown;
  approval_result?: unknown;
  error_message?: string | null;
  created_at?: string | null;
  approved_at?: string | null;
  rejected_at?: string | null;
  executed_at?: string | null;
  [key: string]: unknown;
}

export interface VaultAuditLog {
  id: string;
  company_id?: string | null;
  event_type: string;
  action?: string | null;
  status?: string | null;
  risk_level?: string | null;
  tenant_connection_id?: string | null;
  approval_request_id?: string | null;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface CreateTenantConnectionInput {
  connector_template_slug: string;
  name: string;
  status?: string;
  technical_ref_type?: string;
  technical_ref_id?: string;
  connection_config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface CreatePermissionGrantInput {
  subject_type: string;
  subject_id?: string;
  allowed_actions?: string[];
  requires_approval?: boolean;
  risk_level?: string;
}

export interface CreateApprovalRequestInput {
  tenant_connection_id?: string;
  permission_grant_id?: string;
  subject_type: string;
  subject_id?: string;
  action_type: string;
  risk_level?: string;
  preview?: Record<string, unknown>;
  request_payload?: Record<string, unknown>;
}
