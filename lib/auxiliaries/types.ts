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
  error_message?: string | null;
  cost_usd?: number | null;
  created_at?: string | null;
  finished_at?: string | null;
  // demais colunas do banco ficam acessíveis sem quebrar tipagem
  [key: string]: unknown;
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
}
