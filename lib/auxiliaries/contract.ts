// Auxiliary Blueprint Contract (42A5) — funções puras de contrato.
// Sem schema novo: o contrato vive em default_config.contract (template) e
// config.contract (tenant). Quando ausente, é INFERIDO de campos existentes
// (requires_human_approval, uses_external_actions, execution_mode, trigger_type,
// permissions, runtime). Nunca contém segredo/token/api_key/credential.

import type {
  AuxiliaryContract,
  AuxiliaryType,
  AuxiliaryAudience,
  AuxiliarySideEffects,
  AuxiliaryRiskLevel,
  AuxiliaryKnowledgeReq,
  AuxiliaryMemoryReq,
  AuxiliaryToolReq,
} from './types';

// Chaves sensíveis NUNCA permitidas dentro de um contrato (match por substring).
export const FORBIDDEN_CONTRACT_KEYS = [
  'token',
  'api_key',
  'apikey',
  'secret',
  'password',
  'credential',
  'client_token',
  'access_token',
  'refresh_token',
  'cookie',
  'authorization',
];

const AUX_TYPES: AuxiliaryType[] = [
  'read_only',
  'draft_only',
  'approval_required',
  'external_action',
  'workflow',
  'agent_based',
];
const AUDIENCES: AuxiliaryAudience[] = ['broker_internal', 'operator_internal', 'system_internal'];
const SIDE_EFFECTS: AuxiliarySideEffects[] = ['none', 'draft_only', 'approval_required', 'external_action'];
const RISK_LEVELS: AuxiliaryRiskLevel[] = ['low', 'medium', 'high', 'critical'];
const KNOWLEDGE_SCOPES: AuxiliaryKnowledgeReq['scope'][] = ['agent', 'tenant', 'global', 'carrier', 'none'];
const MEMORY_TYPES: AuxiliaryMemoryReq['type'][] = ['session', 'user', 'brokerage', 'case', 'operational', 'none'];
const TOOL_TYPES: AuxiliaryToolReq['type'][] = ['internal', 'connector', 'whatsapp', 'email', 'portal', 'mcp', 'http'];
const COST_SOURCES: AuxiliaryContract['billing_policy']['cost_source'][] = ['token_usage_logs', 'external_provider', 'none'];

// --------------------------------------------------------------------------
// Helpers básicos
// --------------------------------------------------------------------------
function asObject(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}
function asString(v: unknown, d = ''): string {
  return typeof v === 'string' ? v : d;
}
function asBool(v: unknown, d = false): boolean {
  return typeof v === 'boolean' ? v : d;
}
function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === 'string' && x.trim().length > 0).map((x) => x.trim());
}
function pickEnum<T extends string>(v: unknown, allowed: T[], fallback: T): T {
  return typeof v === 'string' && (allowed as string[]).includes(v) ? (v as T) : fallback;
}

// --------------------------------------------------------------------------
// Sanitização (remove qualquer chave sensível em qualquer nível)
// --------------------------------------------------------------------------
export function sanitizeAuxiliaryContract(value: unknown): { value: unknown; removed: string[] } {
  const removed: string[] = [];
  const walk = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === 'object') {
      const out: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        const lower = k.toLowerCase();
        if (FORBIDDEN_CONTRACT_KEYS.some((f) => lower.includes(f))) {
          removed.push(k);
          continue;
        }
        out[k] = walk(val);
      }
      return out;
    }
    return v;
  };
  return { value: walk(value), removed };
}

// --------------------------------------------------------------------------
// Leitura do contrato explícito (template default_config.contract OU tenant config.contract)
// --------------------------------------------------------------------------
function readContractRaw(source: unknown): Record<string, unknown> | null {
  const s = asObject(source);
  const fromDc = asObject(asObject(s.default_config).contract);
  if (Object.keys(fromDc).length) return fromDc;
  const fromCfg = asObject(asObject(s.config).contract);
  if (Object.keys(fromCfg).length) return fromCfg;
  return null;
}

export function getAuxiliaryContract(source: unknown): Record<string, unknown> | null {
  return readContractRaw(source);
}

function readRuntimeKind(source: unknown): string {
  const s = asObject(source);
  const dcRt = asObject(asObject(s.default_config).runtime);
  const cfgRt = asObject(asObject(s.config).runtime);
  const rt = Object.keys(dcRt).length ? dcRt : cfgRt;
  if (typeof rt.agent_id === 'string' && rt.agent_id) return 'smith_agent';
  return asString(rt.kind);
}

// --------------------------------------------------------------------------
// Inferência (quando não há contrato explícito)
// --------------------------------------------------------------------------
function inferSideEffects(usesExternal: boolean, requiresApproval: boolean): AuxiliarySideEffects {
  if (usesExternal && requiresApproval) return 'approval_required';
  if (usesExternal) return 'external_action';
  if (requiresApproval) return 'draft_only';
  return 'none';
}
function riskFromSideEffects(se: AuxiliarySideEffects): AuxiliaryRiskLevel {
  switch (se) {
    case 'external_action':
      return 'high';
    case 'approval_required':
      return 'medium';
    default:
      return 'low';
  }
}
function typeFromInference(runtimeKind: string, se: AuxiliarySideEffects): AuxiliaryType {
  if (runtimeKind === 'workflow') return 'workflow';
  if (runtimeKind === 'smith_agent_blueprint' || runtimeKind === 'smith_agent') return 'agent_based';
  switch (se) {
    case 'external_action':
      return 'external_action';
    case 'approval_required':
      return 'approval_required';
    case 'draft_only':
      return 'draft_only';
    default:
      return 'read_only';
  }
}

export function inferAuxiliaryContract(source: unknown): AuxiliaryContract {
  const s = asObject(source);
  const slug = asString(s.slug);
  const usesExternal = asBool(s.uses_external_actions, false);
  const runtimeKind = readRuntimeKind(source);

  const rha = s.requires_human_approval;
  const requiresApproval = typeof rha === 'boolean' ? rha : usesExternal;

  const sideEffects = inferSideEffects(usesExternal, requiresApproval);
  const riskLevel = riskFromSideEffects(sideEffects);
  const auxiliaryType = typeFromInference(runtimeKind, sideEffects);
  const approvalRequired = requiresApproval || sideEffects === 'approval_required' || sideEffects === 'external_action';

  const goal =
    asString(s.short_description) || asString(s.description) || asString(s.name) || asString(s.slug);

  const requiresTools: AuxiliaryToolReq[] = [];
  if (slug.includes('whatsapp')) {
    requiresTools.push({ type: 'whatsapp', required: true, approval_required: true });
  } else if (usesExternal) {
    requiresTools.push({ type: 'connector', required: true, approval_required: true });
  }

  return {
    kind: 'auxiliary_contract_v1',
    auxiliary_type: auxiliaryType,
    audience: 'operator_internal',
    goal,
    non_goals: [],
    when_to_use: [],
    when_not_to_use: [],
    inputs: { required: [], optional: [] },
    outputs: { format: 'structured', fields: [] },
    requires_knowledge: [],
    requires_memory: [],
    requires_tools: requiresTools,
    side_effects: sideEffects,
    risk_level: riskLevel,
    approval_policy: {
      required: approvalRequired,
      reason: approvalRequired
        ? 'Ação sensível/externa requer aprovação humana (HITL).'
        : 'Sem efeito externo; execução com log.',
    },
    billing_policy: { billable: true, cost_source: 'token_usage_logs' },
    observability: { log_run: true, log_cost: true, log_approval: approvalRequired },
  };
}

// --------------------------------------------------------------------------
// Normalizadores dos sub-objetos do contrato explícito
// --------------------------------------------------------------------------
function normKnowledge(v: unknown): AuxiliaryKnowledgeReq | null {
  const o = asObject(v);
  const scope = pickEnum(o.scope, KNOWLEDGE_SCOPES, 'none');
  const item: AuxiliaryKnowledgeReq = { scope, required: asBool(o.required, false) };
  const ns = asString(o.namespace);
  if (ns) item.namespace = ns;
  return item;
}
function normMemory(v: unknown): AuxiliaryMemoryReq | null {
  const o = asObject(v);
  const type = pickEnum(o.type, MEMORY_TYPES, 'none');
  return { type, required: asBool(o.required, false) };
}
function normTool(v: unknown): AuxiliaryToolReq | null {
  const o = asObject(v);
  const type = pickEnum(o.type, TOOL_TYPES, 'internal');
  const item: AuxiliaryToolReq = {
    type,
    required: asBool(o.required, false),
    approval_required: asBool(o.approval_required, false),
  };
  const slug = asString(o.slug);
  if (slug) item.slug = slug;
  return item;
}

// --------------------------------------------------------------------------
// Normalização final: contrato explícito (sanitizado) por cima do inferido.
// --------------------------------------------------------------------------
export function normalizeAuxiliaryContract(source: unknown): AuxiliaryContract {
  const inferred = inferAuxiliaryContract(source);
  const explicitRaw = readContractRaw(source);
  if (!explicitRaw) return inferred;

  const { value } = sanitizeAuxiliaryContract(explicitRaw);
  const e = asObject(value);

  const inputs = asObject(e.inputs);
  const outputs = asObject(e.outputs);
  const approval = asObject(e.approval_policy);
  const billing = asObject(e.billing_policy);
  const obs = asObject(e.observability);

  return {
    kind: 'auxiliary_contract_v1',
    auxiliary_type: pickEnum(e.auxiliary_type, AUX_TYPES, inferred.auxiliary_type),
    audience: pickEnum(e.audience, AUDIENCES, inferred.audience),
    goal: asString(e.goal) || inferred.goal,
    non_goals: e.non_goals !== undefined ? asStringArray(e.non_goals) : inferred.non_goals,
    when_to_use: e.when_to_use !== undefined ? asStringArray(e.when_to_use) : inferred.when_to_use,
    when_not_to_use:
      e.when_not_to_use !== undefined ? asStringArray(e.when_not_to_use) : inferred.when_not_to_use,
    inputs:
      e.inputs !== undefined
        ? { required: asStringArray(inputs.required), optional: asStringArray(inputs.optional) }
        : inferred.inputs,
    outputs:
      e.outputs !== undefined
        ? { format: asString(outputs.format, 'structured'), fields: asStringArray(outputs.fields) }
        : inferred.outputs,
    requires_knowledge: Array.isArray(e.requires_knowledge)
      ? (e.requires_knowledge as unknown[]).map(normKnowledge).filter((x): x is AuxiliaryKnowledgeReq => x !== null)
      : inferred.requires_knowledge,
    requires_memory: Array.isArray(e.requires_memory)
      ? (e.requires_memory as unknown[]).map(normMemory).filter((x): x is AuxiliaryMemoryReq => x !== null)
      : inferred.requires_memory,
    requires_tools: Array.isArray(e.requires_tools)
      ? (e.requires_tools as unknown[]).map(normTool).filter((x): x is AuxiliaryToolReq => x !== null)
      : inferred.requires_tools,
    side_effects: pickEnum(e.side_effects, SIDE_EFFECTS, inferred.side_effects),
    risk_level: pickEnum(e.risk_level, RISK_LEVELS, inferred.risk_level),
    approval_policy:
      e.approval_policy !== undefined
        ? { required: asBool(approval.required, inferred.approval_policy.required), reason: asString(approval.reason) || inferred.approval_policy.reason }
        : inferred.approval_policy,
    billing_policy:
      e.billing_policy !== undefined
        ? {
            billable: asBool(billing.billable, true),
            cost_source: pickEnum(billing.cost_source, COST_SOURCES, 'token_usage_logs'),
          }
        : inferred.billing_policy,
    observability:
      e.observability !== undefined
        ? {
            log_run: asBool(obs.log_run, true),
            log_cost: asBool(obs.log_cost, true),
            log_approval: asBool(obs.log_approval, inferred.observability.log_approval),
          }
        : inferred.observability,
  };
}

// --------------------------------------------------------------------------
// Getters de conveniência
// --------------------------------------------------------------------------
export function getAuxiliaryRiskLevel(source: unknown): AuxiliaryRiskLevel {
  return normalizeAuxiliaryContract(source).risk_level;
}
export function getAuxiliarySideEffects(source: unknown): AuxiliarySideEffects {
  return normalizeAuxiliaryContract(source).side_effects;
}
export function requiresHumanApprovalFromContract(source: unknown): boolean {
  return normalizeAuxiliaryContract(source).approval_policy.required;
}

// --------------------------------------------------------------------------
// Badges/microcopy para UI (rótulos PT-BR sem jargão técnico)
// --------------------------------------------------------------------------
const TYPE_LABEL: Record<AuxiliaryType, string> = {
  read_only: 'Somente leitura',
  draft_only: 'Rascunho',
  approval_required: 'Requer aprovação',
  external_action: 'Ação externa',
  workflow: 'Workflow',
  agent_based: 'Agente',
};
const RISK_LABEL: Record<AuxiliaryRiskLevel, string> = {
  low: 'Risco baixo',
  medium: 'Risco médio',
  high: 'Risco alto',
  critical: 'Risco crítico',
};

export function auxiliaryTypeLabel(t: AuxiliaryType): string {
  return TYPE_LABEL[t] ?? t;
}

export function auxiliaryContractBadges(source: unknown): string[] {
  const c = normalizeAuxiliaryContract(source);
  const out: string[] = [TYPE_LABEL[c.auxiliary_type]];
  if (c.approval_policy.required && c.auxiliary_type !== 'approval_required') out.push('Requer aprovação');
  if (c.side_effects === 'external_action' && c.auxiliary_type !== 'external_action') out.push('Ação externa');
  if (c.requires_tools.some((t) => t.type !== 'internal')) out.push('Requer conector');
  if (c.requires_knowledge.some((k) => k.required)) out.push('Requer conhecimento');
  out.push(RISK_LABEL[c.risk_level]);
  return Array.from(new Set(out));
}
