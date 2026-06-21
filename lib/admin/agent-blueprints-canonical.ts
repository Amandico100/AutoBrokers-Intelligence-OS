// Tenant Activation 1 — Blueprints CANÔNICOS role-aware + Effective Configuration.
// SELF-CONTAINED (puro, testável). Não cria estrutura paralela: alimenta a criação
// de agents (tabela `agents`) e a composição da config efetiva do runtime.
//
// Composição (SPEC-012 §6):
//   Blueprint global vN + Guardrails imutáveis + Variáveis da empresa
//   + Overrides seguros do tenant = Effective Configuration.
// A corretora altera SÓ variáveis/overrides seguros; NUNCA o prompt protegido,
// role, audience, guardrails ou a marca "AutoBrokers".

export type AgentRole = 'core' | 'attendance' | 'subagent';
export type AgentAudience = 'broker_internal' | 'insured_external' | 'internal';

export interface BlueprintVariable {
  key: string;
  label: string;
  default: string;
  editable_by_tenant: boolean; // false = preenchido pelo sistema (ex.: company_name)
}

export interface CanonicalBlueprint {
  blueprint_key: string;
  blueprint_version: string;
  role: AgentRole;
  audience: AgentAudience;
  brand_locked_name: string | null; // ex.: 'AutoBrokers' (não renomeável)
  default_display_name: string;      // ex.: 'AutoBrokers' | 'Even'
  display_name_template: string;     // ex.: 'AutoBrokers da {{company_name}}'
  allow_direct_chat: boolean;
  is_subagent: boolean;
  default_llm_provider: string;
  default_llm_model: string;
  // Template do system prompt com {{variáveis}}. PROTEGIDO (tenant não edita o texto).
  system_prompt_template: string;
  variables: BlueprintVariable[];
  immutable_guardrails: string[];     // regras que nunca mudam
  safe_override_fields: string[];     // campos que o tenant pode ajustar
  default_active: boolean;            // estado inicial do agente
}

const CORE_GUARDRAILS = [
  'isolamento_multi_tenant', 'nunca_cross_tenant', 'sem_acesso_a_segredos',
  'sem_promessa_de_cobertura_sem_evidencia', 'respeita_approval_e_gates', 'marca_autobrokers_bloqueada',
];
const ATTENDANCE_GUARDRAILS = [
  'isolamento_multi_tenant', 'nunca_promete_cobertura_sem_evidencia', 'nunca_inventa_protocolo',
  'respeita_approval_gates_consent', 'risco_grave_vai_para_humano', 'sem_acesso_a_segredos', 'usa_apenas_corredores_ativados',
];

export const AUTOBROKERS_CORE_BLUEPRINT: CanonicalBlueprint = {
  blueprint_key: 'autobrokers-core-v1',
  blueprint_version: 'v1',
  role: 'core',
  audience: 'broker_internal',
  brand_locked_name: 'AutoBrokers',
  default_display_name: 'AutoBrokers',
  display_name_template: 'AutoBrokers da {{company_name}}',
  allow_direct_chat: true,
  is_subagent: false,
  default_llm_provider: 'openai',
  default_llm_model: 'gpt-4o-mini',
  system_prompt_template: [
    'Voce e o AutoBrokers da {{company_name}} — o braco direito interno e inteligentissimo da corretora.',
    'Apresente-se como "AutoBrokers da {{company_name}}". A marca AutoBrokers nunca muda.',
    'Voce ajuda o corretor/gestor/equipe em estrategia, vendas, marketing, operacao, gestao, seguros, financeiro e juridico,',
    'usando o conhecimento global curado do AutoBrokers + o conhecimento privado autorizado da propria corretora.',
    'Regras: nunca acesse dados de outra corretora; nunca exponha segredos; nunca prometa cobertura sem evidencia;',
    'respeite approval e gates; quando faltar dado, diga que vai verificar. Seja claro, util e direto.',
    'Tom: {{tone}}.',
  ].join(' '),
  variables: [
    { key: 'company_name', label: 'Nome da corretora', default: '', editable_by_tenant: false },
    { key: 'tone', label: 'Tom de comunicacao', default: 'profissional e acolhedor', editable_by_tenant: true },
  ],
  immutable_guardrails: CORE_GUARDRAILS,
  safe_override_fields: ['avatar_url', 'tone', 'idioma', 'llm_temperature'],
  default_active: true,
};

export const EVEN_ATTENDANCE_BLUEPRINT: CanonicalBlueprint = {
  blueprint_key: 'even-attendance-v1',
  blueprint_version: 'v1',
  role: 'attendance',
  audience: 'insured_external',
  brand_locked_name: null,
  default_display_name: 'Even',
  display_name_template: '{{attendant_name}}',
  allow_direct_chat: false,
  is_subagent: false,
  default_llm_provider: 'openai',
  default_llm_model: 'gpt-4o-mini',
  system_prompt_template: [
    'Voce e {{attendant_name}} ({{attendant_gender}}), atendente de assistencia e sinistro da {{company_name}} no WhatsApp.',
    'Atenda o segurado com clareza, empatia e seguranca. Use {{attendant_pronoun}} ao se referir a si.',
    'Regras: nunca prometa cobertura sem evidencia; nunca diga que acionou a seguradora sem acao real; nunca invente protocolo;',
    'colete uma informacao por vez; em risco grave (fumaca, faisca, incendio, risco a vida) oriente seguranca e encaminhe a humano;',
    'use apenas os corredores e subcorredores habilitados pela corretora; quando faltar evidencia de apolice, informe que vai verificar;',
    'mascare dados sensiveis; em duvida, encaminhe a {{handoff_target}}. Horario de atendimento: {{business_hours}}. Tom: {{tone}}.',
    'Abertura sugerida: "{{opening_message}}". Encerramento sugerido: "{{closing_message}}".',
  ].join(' '),
  variables: [
    { key: 'company_name', label: 'Nome da corretora', default: '', editable_by_tenant: false },
    { key: 'attendant_name', label: 'Nome do atendente', default: 'Even', editable_by_tenant: true },
    { key: 'attendant_gender', label: 'Genero', default: 'feminino', editable_by_tenant: true },
    { key: 'attendant_pronoun', label: 'Pronome', default: 'ela', editable_by_tenant: true },
    { key: 'tone', label: 'Tom', default: 'acolhedor e objetivo', editable_by_tenant: true },
    { key: 'business_hours', label: 'Horario de atendimento', default: '24h', editable_by_tenant: true },
    { key: 'handoff_target', label: 'Destino de handoff humano', default: 'um atendente humano da corretora', editable_by_tenant: true },
    { key: 'opening_message', label: 'Mensagem de abertura', default: 'Ola! Sou a Even, atendente da sua corretora. Como posso ajudar?', editable_by_tenant: true },
    { key: 'closing_message', label: 'Mensagem de encerramento', default: 'Posso ajudar em algo mais?', editable_by_tenant: true },
  ],
  immutable_guardrails: ATTENDANCE_GUARDRAILS,
  safe_override_fields: ['avatar_url', 'attendant_name', 'attendant_gender', 'attendant_pronoun', 'tone', 'business_hours', 'handoff_target', 'opening_message', 'closing_message', 'voice', 'llm_temperature'],
  default_active: false, // Even nasce provisionada e INATIVA
};

export const CANONICAL_BLUEPRINTS: CanonicalBlueprint[] = [AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT];

export function getCanonicalBlueprint(key: string): CanonicalBlueprint | null {
  return CANONICAL_BLUEPRINTS.find((b) => b.blueprint_key === key) ?? null;
}
export function getBlueprintByRole(role: AgentRole): CanonicalBlueprint | null {
  return CANONICAL_BLUEPRINTS.find((b) => b.role === role) ?? null;
}

/** Renderiza um template substituindo {{var}} pelos valores (faltantes viram default/''). */
export function renderTemplate(template: string, values: Record<string, string>): string {
  return template.replace(/\{\{\s*([a-z0-9_]+)\s*\}\}/gi, (_m, k) => (values[k] != null ? String(values[k]) : ''));
}

export interface EffectiveConfigInput {
  blueprint: CanonicalBlueprint;
  company_name: string;
  tenant_variables?: Record<string, string>; // valores escolhidos pela corretora
  tenant_overrides?: Record<string, unknown>; // ex.: { avatar_url, llm_temperature }
}
export interface EffectiveConfig {
  blueprint_key: string;
  blueprint_version: string;
  role: AgentRole;
  audience: AgentAudience;
  display_name: string;
  is_subagent: boolean;
  allow_direct_chat: boolean;
  system_prompt: string;
  llm_provider: string;
  llm_model: string;
  llm_temperature: number | null; // materializado (override seguro) ou null = default
  avatar_url: string | null;      // materializado
  voice: string | null;           // materializado
  applied_overrides: string[];
  overrides_applied: Record<string, unknown>; // valores REALMENTE aplicados (whitelist)
  rejected_overrides: string[]; // tentativas fora da whitelist (bloqueadas)
  variables_used: Record<string, string>;
  immutable_guardrails: string[];
}

/**
 * Compõe a Effective Configuration. Variáveis não-editáveis (ex.: company_name) e
 * a marca são impostas pelo sistema; overrides fora da whitelist são REJEITADOS.
 */
export function resolveEffectiveConfig(input: EffectiveConfigInput): EffectiveConfig {
  const bp = input.blueprint;
  // 1) valores das variáveis: default → tenant (só as editáveis) → system (company_name, brand).
  const values: Record<string, string> = {};
  for (const v of bp.variables) values[v.key] = v.default;
  if (input.tenant_variables) {
    for (const v of bp.variables) {
      if (v.editable_by_tenant && typeof input.tenant_variables[v.key] === 'string' && input.tenant_variables[v.key].trim()) {
        values[v.key] = input.tenant_variables[v.key].trim();
      }
    }
  }
  values.company_name = input.company_name; // sistema impõe
  values.broker_brand = bp.brand_locked_name ?? values.attendant_name ?? '';

  // 2) overrides seguros (whitelist) — MATERIALIZADOS (valores realmente aplicados).
  const applied: string[] = [];
  const rejected: string[] = [];
  const overrides_applied: Record<string, unknown> = {};
  const llm_provider = bp.default_llm_provider;
  const llm_model = bp.default_llm_model; // modelo NUNCA é override do tenant (anti custo premium)
  let llm_temperature: number | null = null;
  if (input.tenant_overrides) {
    for (const [k, v] of Object.entries(input.tenant_overrides)) {
      if (bp.safe_override_fields.includes(k)) {
        applied.push(k);
        overrides_applied[k] = v;
        if (k === 'llm_temperature' && typeof v === 'number') llm_temperature = v;
        // overrides que também são variáveis (ex.: tone) refletem no prompt:
        if (typeof v === 'string' && bp.variables.some((bv) => bv.key === k && bv.editable_by_tenant)) values[k] = v;
      } else {
        rejected.push(k); // nunca aplica fora da whitelist (agent_system_prompt, role, audience, llm_model premium...)
      }
    }
  }
  const avatar_url = typeof overrides_applied.avatar_url === 'string' ? (overrides_applied.avatar_url as string) : null;
  const voice = typeof overrides_applied.voice === 'string' ? (overrides_applied.voice as string) : null;

  // 3) nome de exibição: marca travada para core.
  const display_name = bp.brand_locked_name
    ? renderTemplate(bp.display_name_template, values) // "AutoBrokers da {company}"
    : renderTemplate(bp.display_name_template, values); // "{attendant_name}"

  return {
    blueprint_key: bp.blueprint_key,
    blueprint_version: bp.blueprint_version,
    role: bp.role,
    audience: bp.audience,
    display_name,
    is_subagent: bp.is_subagent,
    allow_direct_chat: bp.allow_direct_chat,
    system_prompt: renderTemplate(bp.system_prompt_template, values),
    llm_provider,
    llm_model,
    llm_temperature,
    avatar_url,
    voice,
    applied_overrides: applied,
    overrides_applied,
    rejected_overrides: rejected,
    variables_used: values,
    immutable_guardrails: bp.immutable_guardrails,
  };
}

// --- TA2-A: persistência canônica da configuração do agente por tenant ---------
// A config editável vive em agents.context_package.tenant_agent_config (preserva
// o resto do context_package). O prompt efetivo é RE-RENDERIZADO e gravado em
// agents.agent_system_prompt → o runtime (que lê agent_system_prompt + colunas)
// passa a usar a configuração SEM precisar mudar o runtime. NUNCA expõe prompt
// protegido como editável; modelo/role/audience/guardrails nunca mudam.

export const TENANT_AGENT_CONFIG_NS = 'tenant_agent_config';

export interface TenantAgentConfigInput {
  variables?: Record<string, string>;
  overrides?: Record<string, unknown>;
}
export interface AgentConfigUpdate {
  columns: Record<string, unknown>;        // colunas de `agents` a atualizar
  context_package: Record<string, unknown>; // context_package mesclado (preserva existente)
  effective: EffectiveConfig;
  rejected: string[];
}

/** Campos que o tenant pode editar para um blueprint (variáveis + overrides seguros). */
export function editableForBlueprint(bp: CanonicalBlueprint): { variables: BlueprintVariable[]; override_fields: string[] } {
  return { variables: bp.variables.filter((v) => v.editable_by_tenant), override_fields: bp.safe_override_fields };
}

/** Calcula a atualização canônica (colunas + context_package) a partir da edição do tenant. */
export function computeAgentConfigUpdate(
  bp: CanonicalBlueprint,
  companyName: string,
  currentContextPackage: unknown,
  input: TenantAgentConfigInput,
): AgentConfigUpdate {
  const eff = resolveEffectiveConfig({ blueprint: bp, company_name: companyName, tenant_variables: input.variables, tenant_overrides: input.overrides });

  const columns: Record<string, unknown> = { agent_system_prompt: eff.system_prompt };
  // Marca travada: Core mantém name 'AutoBrokers'. Even usa o nome escolhido.
  if (!bp.brand_locked_name) columns.name = eff.display_name;
  if (eff.avatar_url !== null) columns.avatar_url = eff.avatar_url;
  if (eff.llm_temperature !== null) columns.llm_temperature = eff.llm_temperature;

  const cp: Record<string, unknown> = (currentContextPackage && typeof currentContextPackage === 'object' && !Array.isArray(currentContextPackage))
    ? { ...(currentContextPackage as Record<string, unknown>) } : {};
  const editableVarKeys = bp.variables.filter((v) => v.editable_by_tenant).map((v) => v.key);
  const savedVars: Record<string, string> = {};
  for (const k of editableVarKeys) savedVars[k] = eff.variables_used[k];
  cp[TENANT_AGENT_CONFIG_NS] = {
    blueprint_key: bp.blueprint_key,
    blueprint_version: bp.blueprint_version,
    variables: savedVars,
    overrides: eff.overrides_applied,
    updated_at: new Date().toISOString(),
  };

  return { columns, context_package: cp, effective: eff, rejected: eff.rejected_overrides };
}

/** Reset: limpa os overrides do tenant e volta ao padrão do blueprint. */
export function resetAgentConfigUpdate(bp: CanonicalBlueprint, companyName: string, currentContextPackage: unknown): AgentConfigUpdate {
  const update = computeAgentConfigUpdate(bp, companyName, currentContextPackage, {});
  // remove o namespace (volta 100% ao padrão), preservando o resto do context_package.
  const cp = { ...(update.context_package as Record<string, unknown>) };
  delete cp[TENANT_AGENT_CONFIG_NS];
  return { ...update, context_package: cp };
}

/** Visão sanitizada para o Dashboard/Portal Admin: valores editáveis atuais, SEM prompt protegido. */
export function sanitizeAgentConfigForDashboard(
  bp: CanonicalBlueprint,
  companyName: string,
  currentContextPackage: unknown,
): {
  blueprint_key: string; blueprint_version: string; role: AgentRole; audience: AgentAudience;
  brand_locked_name: string | null; display_name: string;
  editable_variables: Array<{ key: string; label: string; value: string }>;
  editable_override_fields: string[];
  current_overrides: Record<string, unknown>;
} {
  const saved = (currentContextPackage && typeof currentContextPackage === 'object' && !Array.isArray(currentContextPackage))
    ? ((currentContextPackage as Record<string, unknown>)[TENANT_AGENT_CONFIG_NS] as any) : null;
  const savedVars: Record<string, string> = (saved && typeof saved.variables === 'object') ? saved.variables : {};
  const eff = resolveEffectiveConfig({ blueprint: bp, company_name: companyName, tenant_variables: savedVars, tenant_overrides: (saved && typeof saved.overrides === 'object') ? saved.overrides : {} });
  return {
    blueprint_key: bp.blueprint_key, blueprint_version: bp.blueprint_version, role: bp.role, audience: bp.audience,
    brand_locked_name: bp.brand_locked_name, display_name: eff.display_name,
    editable_variables: bp.variables.filter((v) => v.editable_by_tenant).map((v) => ({ key: v.key, label: v.label, value: eff.variables_used[v.key] ?? v.default })),
    editable_override_fields: bp.safe_override_fields,
    current_overrides: (saved && typeof saved.overrides === 'object') ? saved.overrides : {},
  };
}
