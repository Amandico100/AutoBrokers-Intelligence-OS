// TA2-A — store da configuração de agente por tenant (Core/Even). Server-only.
// Reusa a tabela `agents` (Smith). NÃO cria estrutura paralela. A config editável
// é mesclada em context_package + colunas reais (name/avatar/temperature) + o
// agent_system_prompt é RE-RENDERIZADO (o runtime passa a usar a config).
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  getBlueprintByRole, computeAgentConfigUpdate, resetAgentConfigUpdate, sanitizeAgentConfigForDashboard,
  type AgentRole, type TenantAgentConfigInput,
} from '@/lib/admin/agent-blueprints-canonical';

export type AgentKey = 'autobrokers' | 'even';
export function roleForKey(key: string): AgentRole | null {
  if (key === 'autobrokers') return 'core';
  if (key === 'even') return 'attendance';
  return null;
}

const AGENT_SELECT = 'id, name, slug, is_active, avatar_url, llm_temperature, llm_model, agent_role, agent_audience, blueprint_version, context_package';

async function companyName(supabase: SupabaseClient, companyId: string): Promise<string> {
  const { data } = await supabase.from('companies').select('company_name').eq('id', companyId).maybeSingle();
  return data?.company_name ?? 'Corretora';
}

export async function getTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select(AGENT_SELECT).eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent) {
    return { ok: true as const, provisioned: false, blueprint_key: bp.blueprint_key, config: sanitizeAgentConfigForDashboard(bp, name, null), agent: null };
  }
  return {
    ok: true as const, provisioned: true, blueprint_key: bp.blueprint_key,
    agent: { id: agent.id, name: agent.name, is_active: agent.is_active, avatar_url: agent.avatar_url ?? null, llm_temperature: agent.llm_temperature ?? null, blueprint_version: agent.blueprint_version ?? null, audience: agent.agent_audience ?? null },
    config: sanitizeAgentConfigForDashboard(bp, name, agent.context_package),
  };
}

export async function patchTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole, input: TenantAgentConfigInput) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  const upd = computeAgentConfigUpdate(bp, name, agent.context_package, input);
  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };
  return { ok: true as const, rejected: upd.rejected, config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package) };
}

export async function resetTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  const upd = resetAgentConfigUpdate(bp, name, agent.context_package);
  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };
  return { ok: true as const, config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package) };
}
