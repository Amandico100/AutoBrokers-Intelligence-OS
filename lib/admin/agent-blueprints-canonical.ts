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
  safe_override_fields: ['avatar_url', 'attendant_name', 'attendant_gender', 'attendant_pronoun', 'tone', 'business_hours', 'handoff_target', 'opening_message', 'closing_message', 'voice'],
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
  applied_overrides: string[];
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

  // 2) overrides seguros (whitelist).
  const applied: string[] = [];
  const rejected: string[] = [];
  let llm_provider = bp.default_llm_provider;
  let llm_model = bp.default_llm_model;
  if (input.tenant_overrides) {
    for (const [k] of Object.entries(input.tenant_overrides)) {
      if (bp.safe_override_fields.includes(k)) applied.push(k);
      else rejected.push(k); // nunca aplica fora da whitelist (ex.: agent_system_prompt, role, audience, llm_model premium)
    }
  }

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
    applied_overrides: applied,
    rejected_overrides: rejected,
    variables_used: values,
    immutable_guardrails: bp.immutable_guardrails,
  };
}
