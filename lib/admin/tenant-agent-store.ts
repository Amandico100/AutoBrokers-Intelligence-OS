// TA2-A — store da configuração de agente por tenant (Core/Even). Server-only.
// Reusa a tabela `agents` (Smith). NÃO cria estrutura paralela. A config editável
// é mesclada em context_package + colunas reais (name/avatar/temperature) + o
// agent_system_prompt é RE-RENDERIZADO (o runtime passa a usar a config).
//
// P-36 — este era o caminho MAIS quente dos três que gravavam
// `agent_system_prompt` sem o portão de prompt vazio: é o que roda quando
// alguém salva a tela de Personalização. Ele reescreve o prompt inteiro a cada
// save, e nada conferia o que saiu nem o que o banco guardou.
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  getBlueprintByRole, computeAgentConfigUpdate, resetAgentConfigUpdate, sanitizeAgentConfigForDashboard,
  validateTenantAgentInput,
  type AgentRole, type TenantAgentConfigInput,
} from '@/lib/admin/agent-blueprints-canonical';
import { problemasDoUpdate, conferirPromptGravado } from '@/lib/admin/provision-tenant';

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

  // TA2-B — valida/sanitiza server-side ANTES de materializar (rejeita perigoso).
  const v = validateTenantAgentInput(bp, input);
  if (!v.ok) return { ok: false as const, error: 'validation_failed', errors: v.errors };

  const upd = computeAgentConfigUpdate(bp, name, agent.context_package, v.clean);

  // O PORTÃO, antes da escrita. Uma personalização que se resolve para nada
  // (variável faltando, template quebrado) produziria a casca de guardrails —
  // ~560 caracteres sem uma instrução sobre o que o agente é. Recusar o save é
  // melhor que emudecer um agente que já falava.
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) return { ok: false as const, error: 'prompt_invalido', errors: problemas };

  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };

  const conferido = await conferirPromptGravado(supabase, companyId, agent.id, 'patch_tenant_agent_config');
  if (!conferido.ok) return { ok: false as const, error: conferido.reason ?? 'prompt_vazio_apos_escrita' };

  return { ok: true as const, rejected: upd.rejected, config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package) };
}

/**
 * SPEC-045 — botão LIGAR/DESLIGAR do Agente de Atendimento (agents.is_active).
 * SÓ o papel attendance é alternável (o Core/AutoBrokers fica sempre ativo).
 * DESLIGADO = modo observação: o número segue pareado, a equipe humana atende
 * e o sistema captura (Espelho). O OBSERVADOR NUNCA DESLIGA — o botão governa
 * apenas se o agente RESPONDE. O gate correspondente vive no webhook (backend).
 */
export async function setTenantAgentActive(
  supabase: SupabaseClient, companyId: string, role: AgentRole, isActive: boolean,
) {
  if (role !== 'attendance') return { ok: false as const, error: 'toggle_only_attendance' };
  const { data: agent } = await supabase.from('agents').select('id, is_active')
    .eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };
  const { error } = await supabase.from('agents')
    .update({ is_active: isActive, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };
  return { ok: true as const, is_active: isActive };
}

export async function resetTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  const upd = resetAgentConfigUpdate(bp, name, agent.context_package);

  // Voltar ao padrão também reescreve o prompt inteiro. Se o blueprint global
  // estiver quebrado, "resetar" seria o botão que apaga a voz do agente.
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) return { ok: false as const, error: 'prompt_invalido', errors: problemas };

  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };

  const conferido = await conferirPromptGravado(supabase, companyId, agent.id, 'reset_tenant_agent_config');
  if (!conferido.ok) return { ok: false as const, error: conferido.reason ?? 'prompt_vazio_apos_escrita' };

  return { ok: true as const, config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package) };
}
