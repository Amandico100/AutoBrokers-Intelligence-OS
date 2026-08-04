// Cria Agents/Subagents Smith a partir de um blueprint (caminho canônico: backend /api/agents/).
// NUNCA copia segredos (blueprint é sanitizado antes). Server-only.
//
// P-38 — ESTE ARQUIVO NASCIA COM O AGENTE MUDO E LIGADO.
//
// `agent_system_prompt: s('agent_system_prompt') || undefined` e, na linha
// seguinte, `is_active: true`. Em JSON, `undefined` não vira `null`: a CHAVE
// SOME. O backend recebia um insert sem prompt nenhum e com o agente ativo, e
// nada em todo o caminho tinha como perceber — nem o portão do TypeScript
// (que vive em provision-tenant.ts, outro fluxo), nem o backend, que até
// 04/08/2026 não tinha portão.
//
// A regra é a de `createSourceAuxiliary`: aqui o mínimo é "não vazio", e não
// os 120 caracteres do agente canônico. Auxiliar sem descrição nasce com um
// esboço de uma frase de propósito — isso é o produto. O que não pode existir
// é a linha com prompt em branco E ativa.
import { sanitizeBlueprint } from './auxiliary-runtime';
import { problemasDoPromptDeAutoria } from './provision-tenant';

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
  /** Por que o agente nasceu desligado. Ausente = nasceu com voz. */
  prompt_problemas?: string[];
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

  // O PORTÃO, antes de montar o payload. `problemas` vazio = o prompt serve.
  const prompt = s('agent_system_prompt');
  const problemas = problemasDoPromptDeAutoria(prompt ?? '', 1);

  return {
    company_id: companyId,
    name: s('name') || 'Auxiliar',
    slug: `${base}-${suffix}`,
    is_subagent: b('is_subagent', true),
    allow_direct_chat: b('allow_direct_chat', false),
    llm_provider: s('llm_provider') || 'openai',
    llm_model: s('llm_model') || 'gpt-4o-mini',
    agent_system_prompt: problemas.length ? undefined : prompt,
    // O agente mudo NASCE DESLIGADO. Era `true` fixo, uma linha abaixo de um
    // prompt que podia ter sumido do JSON — as duas decisões estavam lado a
    // lado e nenhuma olhava para a outra.
    is_active: problemas.length === 0,
    ...(problemas.length ? { prompt_problemas: problemas } : {}),
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
    // `prompt_problemas` é diagnóstico local: explica por que `is_active` veio
    // false. Não atravessa o fio — o backend tem o seu próprio portão e não
    // deve confiar num campo que o cliente mandou.
    const { prompt_problemas: _local, ...corpo } = payload;
    const res = await fetch(`${backendUrl}/api/agents/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-API-Key': adminApiKey },
      body: JSON.stringify(corpo),
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
