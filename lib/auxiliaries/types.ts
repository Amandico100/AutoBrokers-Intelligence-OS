// Tipos compartilhados dos Auxiliares (consumidos pelo client em 38A3).

export type AuxiliaryRunStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'awaiting_approval'
  | 'cancelled';

export interface AuxiliaryRunOutput {
  summary: string;
  topics: string[];
  decisions: string[];
  pending_items: string[];
  next_steps: string[];
  confidence?: 'low' | 'medium' | 'high';
}

export interface AuxiliaryRun {
  id: string;
  status: AuxiliaryRunStatus | string;
  output?: AuxiliaryRunOutput | null;
  run_type?: string | null;
  template_id?: string | null;
  tenant_auxiliary_id?: string | null;
  conversation_id?: string | null;
  user_id?: string | null;
  error_message?: string | null;
  cost_usd?: number | null;
  token_usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number } | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  // demais colunas do banco ficam acessíveis sem quebrar tipagem
  [key: string]: unknown;
}

export interface ResumoConversation {
  id: string;
  title: string;
  last_message_preview?: string;
  session_id?: string;
  created_at?: string;
  updated_at?: string;
  message_count?: number;
}

export interface AuxiliaryTemplate {
  id: string;
  slug: string;
  name: string;
  [key: string]: unknown;
}

export interface TenantAuxiliary {
  id: string;
  slug: string;
  status: string;
  [key: string]: unknown;
}

export interface RunResumoResponse {
  success: boolean;
  run?: { id: string; status: string; output: AuxiliaryRunOutput };
  error?: string;
  message?: string;
}

export interface FollowUpDraftResponse {
  success: boolean;
  draft?: { message: string };
  run_id?: string | null;
  model?: string;
  error?: string;
  message?: string;
}

// =============================================================================
// Auxiliary Blueprint Contract (42A5) — contrato declarativo dos Auxiliares.
// Todos os tipos abaixo são ADITIVOS e backward-compatible. O contrato vive em
// auxiliary_templates.default_config.contract e tenant_auxiliaries.config.contract.
// =============================================================================

export type AuxiliaryType =
  | 'read_only'
  | 'draft_only'
  | 'approval_required'
  | 'external_action'
  | 'workflow'
  | 'agent_based';

export type AuxiliaryAudience = 'broker_internal' | 'operator_internal' | 'system_internal';

export type AuxiliarySideEffects = 'none' | 'draft_only' | 'approval_required' | 'external_action';

export type AuxiliaryRiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface AuxiliaryKnowledgeReq {
  scope: 'agent' | 'tenant' | 'global' | 'carrier' | 'none';
  namespace?: string;
  required: boolean;
}

export interface AuxiliaryMemoryReq {
  type: 'session' | 'user' | 'brokerage' | 'case' | 'operational' | 'none';
  required: boolean;
}

export interface AuxiliaryToolReq {
  type: 'internal' | 'connector' | 'whatsapp' | 'email' | 'portal' | 'mcp' | 'http';
  slug?: string;
  required: boolean;
  approval_required: boolean;
}

export interface AuxiliaryContract {
  kind: 'auxiliary_contract_v1';
  auxiliary_type: AuxiliaryType;
  audience: AuxiliaryAudience;
  goal: string;
  non_goals: string[];
  when_to_use: string[];
  when_not_to_use: string[];
  inputs: { required: string[]; optional: string[] };
  outputs: { format: string; fields: string[] };
  requires_knowledge: AuxiliaryKnowledgeReq[];
  requires_memory: AuxiliaryMemoryReq[];
  requires_tools: AuxiliaryToolReq[];
  side_effects: AuxiliarySideEffects;
  risk_level: AuxiliaryRiskLevel;
  approval_policy: { required: boolean; reason: string };
  billing_policy: { billable: boolean; cost_source: 'token_usage_logs' | 'external_provider' | 'none' };
  observability: { log_run: boolean; log_cost: boolean; log_approval: boolean };
}
