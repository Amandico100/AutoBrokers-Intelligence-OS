// Helpers da decisão canônica (SPEC-002): Auxiliares = produto; runtime = Smith Agents/Subagents.
// Sem segredos. Sem schema novo. O runtime vive em auxiliary_templates.default_config.runtime
// e o binding por corretora em tenant_auxiliaries.config.runtime.

export const FORBIDDEN_SECRET_KEYS = [
  'llm_api_key',
  'vision_api_key',
  'token',
  'client_token',
  'access_token',
  'refresh_token',
  'api_key',
  'password',
  'secret',
  'credential',
];

export type RuntimeKind = 'smith_agent_blueprint' | 'specific_executor' | 'workflow' | 'none';

export interface RuntimeConfig {
  kind: RuntimeKind;
  agent_blueprint?: Record<string, unknown>;
  executor?: string;
  workflow?: string;
}

/** Slugs cujo executor dedicado JÁ está implementado (specific_executor por padrão). */
export const KNOWN_EXECUTORS = ['resumo-atendimentos', 'follow-up-whatsapp'];

function asObject(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

/** Lê o runtime do default_config; infere specific_executor para slugs conhecidos. */
export function parseRuntimeConfig(defaultConfig: unknown, slug?: string): RuntimeConfig {
  const rt = asObject(asObject(defaultConfig).runtime);
  let kind = typeof rt.kind === 'string' ? (rt.kind as RuntimeKind) : undefined;
  if (!kind && slug && KNOWN_EXECUTORS.includes(slug)) kind = 'specific_executor';
  return {
    kind: kind || 'none',
    agent_blueprint: rt.agent_blueprint ? asObject(rt.agent_blueprint) : undefined,
    executor:
      typeof rt.executor === 'string'
        ? rt.executor
        : slug && KNOWN_EXECUTORS.includes(slug)
          ? slug
          : undefined,
    workflow: typeof rt.workflow === 'string' ? rt.workflow : undefined,
  };
}

export function runtimeBadgeLabel(kind: RuntimeKind): string {
  switch (kind) {
    case 'smith_agent_blueprint':
      return 'Agent inteligente';
    case 'specific_executor':
      return 'Executor dedicado';
    case 'workflow':
      return 'Workflow/Corredor';
    default:
      return 'Não configurado';
  }
}

/** Remove QUALQUER chave sensível (em qualquer nível) — sanitização profunda. */
export function sanitizeBlueprint(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sanitizeBlueprint);
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      const lower = k.toLowerCase();
      if (FORBIDDEN_SECRET_KEYS.some((f) => lower.includes(f))) continue;
      out[k] = sanitizeBlueprint(v);
    }
    return out;
  }
  return value;
}
