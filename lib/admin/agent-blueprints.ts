// Cria Agents/Subagents Smith a partir de um blueprint (caminho canônico: backend /api/agents/).
// NUNCA copia segredos (blueprint é sanitizado antes). Server-only.
import { sanitizeBlueprint } from './auxiliary-runtime';

export interface AgentCreatePayload {
  company_id: string;
  name: string;
  slug: string;
  is_subagent: boolean;
  allow_direct_chat: boolean;
  llm_provider: string;
  llm_model: string;
  agent_system_prompt?: string;
  is_active: boolean;
}

function slugify(input: string): string {
  const base = input.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return base || 'auxiliar';
}

/** Monta o payload de AgentCreate a partir do blueprint (já sanitizado). Slug único por sufixo. */
export function buildAgentCreatePayload(
  companyId: string,
  blueprint: Record<string, unknown>,
): AgentCreatePayload {
  const bp = sanitizeBlueprint(blueprint) as Record<string, unknown>;
  const s = (k: string) => (typeof bp[k] === 'string' ? (bp[k] as string) : undefined);
  const b = (k: string, d: boolean) => (typeof bp[k] === 'boolean' ? (bp[k] as boolean) : d);
  const base = slugify(s('slug') || s('name') || 'auxiliar');
  const suffix = Date.now().toString(36).slice(-4);
  return {
    company_id: companyId,
    name: s('name') || 'Auxiliar',
    slug: `${base}-${suffix}`,
    is_subagent: b('is_subagent', true),
    allow_direct_chat: b('allow_direct_chat', false),
    llm_provider: s('llm_provider') || 'openai',
    llm_model: s('llm_model') || 'gpt-4o-mini',
    agent_system_prompt: s('agent_system_prompt') || undefined,
    is_active: true,
  };
}

/**
 * Cria o agent via backend canônico (require_master_admin = X-Admin-API-Key).
 * Retorna { agentId } ou { error } — nunca lança (binding é best-effort).
 */
export async function createAgentViaBackend(
  backendUrl: string,
  adminApiKey: string,
  payload: AgentCreatePayload,
): Promise<{ agentId?: string; error?: string }> {
  try {
    const res = await fetch(`${backendUrl}/api/agents/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-API-Key': adminApiKey },
      body: JSON.stringify(payload),
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }
    if (!res.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : undefined;
      return { error: detail || `backend ${res.status}` };
    }
    const id = data.id;
    return typeof id === 'string' ? { agentId: id } : { error: 'agent sem id' };
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'erro de conexão' };
  }
}

/** Busca um agent por id via backend canônico (sanitizado pelo backend: has_api_key, sem chaves cruas). */
export async function fetchAgentViaBackend(
  backendUrl: string,
  adminApiKey: string,
  agentId: string,
): Promise<{ agent?: Record<string, unknown>; error?: string }> {
  try {
    const res = await fetch(`${backendUrl}/api/agents/${agentId}`, {
      headers: { 'X-Admin-API-Key': adminApiKey },
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    try {
      data = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    } catch {
      data = {};
    }
    if (!res.ok) return { error: typeof data.detail === 'string' ? data.detail : `backend ${res.status}` };
    return { agent: data };
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'erro de conexão' };
  }
}

// Campos NÃO sensíveis que podem viajar no blueprint (a inteligência global do Auxiliar).
const BLUEPRINT_ALLOWED_KEYS = [
  'name',
  'slug',
  'is_subagent',
  'allow_direct_chat',
  'llm_provider',
  'llm_model',
  'agent_system_prompt',
  'llm_temperature',
  'llm_max_tokens',
  'allow_web_search',
  'allow_vision',
  'is_hyde_enabled',
  'tools_config',
  'security_settings',
  'widget_config',
  'retrieval_mode',
  'personality',
  'reasoning_effort',
  'verbosity',
];

/** Extrai um blueprint SEGURO de um agent existente (whitelist + sanitização profunda). */
export function extractBlueprintFromAgent(agent: Record<string, unknown>): Record<string, unknown> {
  const picked: Record<string, unknown> = {};
  for (const k of BLUEPRINT_ALLOWED_KEYS) {
    if (agent[k] !== undefined && agent[k] !== null) picked[k] = agent[k];
  }
  return sanitizeBlueprint(picked) as Record<string, unknown>;
}
