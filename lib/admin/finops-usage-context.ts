// Tenant Activation 2 (Parte 0.5) — contrato canônico de atribuição de custo (FinOps).
// SELF-CONTAINED (puro, testável). NÃO cria billing paralelo: define o objeto de
// atribuição que TODA chamada de LLM/tool deve carregar para o usage logging
// existente (credit_transactions/token_usage_logs/billing_service), permitindo
// somar custo por empresa, agente, caso, corredor e auxiliar.

export interface UsageAttribution {
  company_id: string;
  agent_id: string | null;
  attendance_case_id: string | null;
  corridor_run_id: string | null;
  auxiliary_run_id: string | null;
  conversation_id: string | null;
  tool_name: string | null;
  model: string | null;
}

export interface BuildUsageAttributionInput {
  company_id: string;
  agent_id?: string | null;
  attendance_case_id?: string | null;
  corridor_run_id?: string | null;
  auxiliary_run_id?: string | null;
  conversation_id?: string | null;
  tool_name?: string | null;
  model?: string | null;
}

/** Monta a atribuição canônica (campos ausentes viram null). */
export function buildUsageAttribution(input: BuildUsageAttributionInput): UsageAttribution {
  const s = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v.trim() : null);
  return {
    company_id: input.company_id,
    agent_id: s(input.agent_id),
    attendance_case_id: s(input.attendance_case_id),
    corridor_run_id: s(input.corridor_run_id),
    auxiliary_run_id: s(input.auxiliary_run_id),
    conversation_id: s(input.conversation_id),
    tool_name: s(input.tool_name),
    model: s(input.model),
  };
}

/** Atribuição mínima válida exige company_id (custo SEMPRE por empresa). */
export function isAttributable(a: UsageAttribution): boolean {
  return Boolean(a.company_id);
}

/** Dimensão de agrupamento para relatórios (Portal Admin/FinOps). */
export type CostDimension = 'company' | 'agent' | 'case' | 'corridor' | 'auxiliary';
export function attributionDimensions(a: UsageAttribution): CostDimension[] {
  const dims: CostDimension[] = ['company'];
  if (a.agent_id) dims.push('agent');
  if (a.attendance_case_id) dims.push('case');
  if (a.corridor_run_id) dims.push('corridor');
  if (a.auxiliary_run_id) dims.push('auxiliary');
  return dims;
}
