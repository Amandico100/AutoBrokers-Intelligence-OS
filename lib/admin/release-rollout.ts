// SPEC-013 Fase B P4 — rollout de release para instâncias tenant (PURO, testável).
// Aplica o artefato de uma release global na instância da corretora PRESERVANDO a
// personalização local (tenant_agent_config). Reusa computeAgentConfigUpdate (TA2-A)
// via composição no store. Aqui ficam só funções puras (sem I/O, sem import runtime).
import type { CanonicalBlueprint, AgentRole, AgentAudience, TenantAgentConfigInput } from '@/lib/admin/agent-blueprints-canonical';
import type { BlueprintArtifact } from '@/lib/admin/blueprint-release';

export type RolloutStatus = 'pending' | 'canary' | 'active' | 'paused' | 'failed' | 'rolled_back';
export const ROLLOUT_STATES: RolloutStatus[] = ['pending', 'canary', 'active', 'paused', 'failed', 'rolled_back'];

const ALLOWED: Record<RolloutStatus, RolloutStatus[]> = {
  pending: ['canary', 'active', 'failed'],
  canary: ['active', 'paused', 'rolled_back', 'failed'],
  active: ['paused', 'rolled_back'],
  paused: ['active', 'rolled_back'],
  failed: ['pending'],
  rolled_back: [],
};
export function canRolloutTransition(from: RolloutStatus, to: RolloutStatus): boolean {
  return (ALLOWED[from] ?? []).includes(to);
}

/** Converte o artefato de release num CanonicalBlueprint para reusar a materialização. */
export function artifactToBlueprint(artifact: BlueprintArtifact, blueprintVersion: string): CanonicalBlueprint {
  return {
    blueprint_key: artifact.blueprint_key,
    blueprint_version: blueprintVersion,
    role: artifact.role as AgentRole,
    audience: artifact.audience as AgentAudience,
    brand_locked_name: artifact.brand_locked_name,
    default_display_name: artifact.default_display_name,
    display_name_template: artifact.display_name_template,
    allow_direct_chat: artifact.allow_direct_chat,
    is_subagent: artifact.is_subagent,
    default_llm_provider: artifact.llm_provider,
    default_llm_model: artifact.llm_model,
    system_prompt_template: artifact.system_prompt_template,
    variables: artifact.variables as CanonicalBlueprint['variables'],
    immutable_guardrails: artifact.immutable_guardrails,
    safe_override_fields: artifact.safe_override_fields,
    default_active: artifact.default_active,
  };
}

// SPEC-013 P4-hardening — snapshot do estado do agente ANTES do rollout, para um
// rollback seguro inclusive no PRIMEIRO rollout (volta ao estado original).
export interface AgentSnapshot {
  name: string | null;
  avatar_url: string | null;
  llm_temperature: number | null;
  agent_system_prompt: string | null;
  context_package: unknown;
  blueprint_version: string | null;
}
export function captureAgentSnapshot(agent: Record<string, unknown>): AgentSnapshot {
  return {
    name: (agent.name as string) ?? null,
    avatar_url: (agent.avatar_url as string) ?? null,
    llm_temperature: agent.llm_temperature != null ? Number(agent.llm_temperature) : null,
    agent_system_prompt: (agent.agent_system_prompt as string) ?? null,
    context_package: agent.context_package ?? null,
    blueprint_version: (agent.blueprint_version as string) ?? null,
  };
}

/** Extrai a personalização local salva (para reaplicar sobre a nova release). */
export function extractSavedTenantInput(currentContextPackage: unknown): TenantAgentConfigInput {
  const cp = (currentContextPackage && typeof currentContextPackage === 'object' && !Array.isArray(currentContextPackage))
    ? (currentContextPackage as Record<string, unknown>) : {};
  const saved = cp['tenant_agent_config'] as any;
  return {
    variables: (saved && typeof saved.variables === 'object') ? saved.variables : {},
    overrides: (saved && typeof saved.overrides === 'object') ? saved.overrides : {},
  };
}
