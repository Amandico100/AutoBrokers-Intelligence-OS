// SPEC-014 C1 — Capability Registry (módulo único, PURO e testável).
// Catálogo canônico + matriz de autorização + resolver. Fonte única de verdade para o
// Admin de Capabilities e para o seed do banco (SPEC-014-01-capability-registry.sql).
// O runtime Smith (Python) consome as TABELAS; este módulo NÃO duplica execução — só governa.

export type CapabilityCategory =
  | 'knowledge' | 'productivity' | 'research' | 'sales' | 'insurance_ops' | 'communication' | 'internal';
export type CapabilityOwner = 'platform' | 'tenant' | 'operational';
export type CapabilityRisk = 'low' | 'medium' | 'high';
export type AgentRole = 'core' | 'attendance' | 'auxiliary' | 'subagent';

export interface Capability {
  key: string;
  name: string;
  category: CapabilityCategory;
  owner: CapabilityOwner;
  risk: CapabilityRisk;
  requires_connection: boolean; // exige tenant_connection (Vault/OAuth)
  requires_approval: boolean;   // ação que escreve/abre exige aprovação humana
  provider?: string;
  note?: string;
}

// §5 da SPEC-014 — catálogo inicial congelado.
export const CAPABILITY_CATALOG: Capability[] = [
  { key: 'knowledge.global.search', name: 'Conhecimento global AutoBrokers', category: 'knowledge', owner: 'platform', risk: 'low', requires_connection: false, requires_approval: false, provider: 'rag' },
  { key: 'knowledge.tenant.search', name: 'Conhecimento privado da corretora', category: 'knowledge', owner: 'tenant', risk: 'low', requires_connection: false, requires_approval: false, provider: 'rag' },
  { key: 'memory.company.read_write', name: 'Memória da corretora', category: 'internal', owner: 'tenant', risk: 'low', requires_connection: false, requires_approval: false, provider: 'memory' },
  { key: 'memory.user.read_write', name: 'Memória do usuário', category: 'internal', owner: 'tenant', risk: 'low', requires_connection: false, requires_approval: false, provider: 'memory' },
  { key: 'control_plane.read', name: 'Estado operacional da corretora', category: 'internal', owner: 'platform', risk: 'low', requires_connection: false, requires_approval: false, note: 'read-only, sem cross-tenant' },
  { key: 'platform.web.search', name: 'Busca na web', category: 'research', owner: 'platform', risk: 'low', requires_connection: false, requires_approval: false, provider: 'tavily', note: 'chave AutoBrokers; custo atribuído à corretora' },
  { key: 'platform.document.extract', name: 'Leitura/OCR de documentos', category: 'productivity', owner: 'platform', risk: 'low', requires_connection: false, requires_approval: false, provider: 'docling' },
  { key: 'operational.infocap.policy_lookup.read', name: 'Consulta de apólice (InfoCap)', category: 'insurance_ops', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: false, provider: 'infocap', note: 'Vault + auditoria; read-only' },
  { key: 'operational.policy_evidence.read', name: 'Evidência de cobertura', category: 'insurance_ops', owner: 'operational', risk: 'medium', requires_connection: true, requires_approval: false, provider: 'infocap' },
  { key: 'tenant.google_drive.read', name: 'Google Drive (leitura)', category: 'productivity', owner: 'tenant', risk: 'medium', requires_connection: true, requires_approval: false, provider: 'mcp:google-drive' },
  { key: 'tenant.google_calendar.read_write', name: 'Google Calendar', category: 'productivity', owner: 'tenant', risk: 'medium', requires_connection: true, requires_approval: true, provider: 'mcp:google-calendar' },
  { key: 'tenant.slack.read_write', name: 'Slack', category: 'communication', owner: 'tenant', risk: 'medium', requires_connection: true, requires_approval: true, provider: 'mcp:slack' },
  { key: 'tenant.notion.read_write', name: 'Notion', category: 'productivity', owner: 'tenant', risk: 'medium', requires_connection: true, requires_approval: true, provider: 'notion' },
  { key: 'operational.whatsapp.send', name: 'Enviar WhatsApp', category: 'communication', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: true, provider: 'zapi', note: 'consentimento + aprovação' },
  { key: 'operational.portal.policy.read', name: 'Portal — apólice (leitura)', category: 'insurance_ops', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: false, provider: 'portal_worker', note: 'HITL' },
  { key: 'operational.portal.billing.read', name: 'Portal — cobrança (leitura)', category: 'insurance_ops', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: false, provider: 'portal_worker', note: 'HITL' },
  { key: 'operational.portal.assistance.read', name: 'Portal — assistência (leitura)', category: 'insurance_ops', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: false, provider: 'portal_worker', note: 'HITL' },
  { key: 'operational.portal.assistance.prepare', name: 'Portal — preparar abertura', category: 'insurance_ops', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: false, provider: 'portal_worker', note: 'prepara, não abre' },
  { key: 'operational.portal.assistance.request', name: 'Portal — abrir assistência', category: 'insurance_ops', owner: 'operational', risk: 'high', requires_connection: true, requires_approval: true, provider: 'portal_worker', note: 'abre com aprovação' },
];

// §6 da SPEC-014 — matriz rígida: o conjunto MÁXIMO permitido por papel.
// (Auxiliar declara o subconjunto mínimo no contrato; aqui é o teto permitido.)
export const AUTHORIZATION_MATRIX: Record<AgentRole, string[]> = {
  core: [
    'knowledge.global.search', 'knowledge.tenant.search', 'memory.company.read_write', 'memory.user.read_write',
    'control_plane.read', 'platform.web.search', 'platform.document.extract',
    'operational.infocap.policy_lookup.read', 'operational.policy_evidence.read',
    'tenant.google_drive.read', 'tenant.google_calendar.read_write', 'tenant.slack.read_write', 'tenant.notion.read_write',
  ],
  attendance: [
    'knowledge.tenant.search', 'memory.company.read_write', 'memory.user.read_write',
    'platform.document.extract', 'operational.infocap.policy_lookup.read', 'operational.policy_evidence.read',
    'operational.whatsapp.send',
    'operational.portal.policy.read', 'operational.portal.billing.read', 'operational.portal.assistance.read',
    'operational.portal.assistance.prepare', 'operational.portal.assistance.request',
  ],
  auxiliary: [
    'knowledge.tenant.search', 'memory.company.read_write', 'platform.web.search', 'platform.document.extract',
    'operational.whatsapp.send', 'tenant.google_drive.read', 'tenant.notion.read_write', 'tenant.slack.read_write',
  ],
  subagent: [
    'knowledge.tenant.search', 'platform.web.search', 'platform.document.extract',
  ],
};

const BY_KEY = new Map(CAPABILITY_CATALOG.map((c) => [c.key, c]));

export function getCapability(key: string): Capability | undefined { return BY_KEY.get(key); }
export function allCapabilityKeys(): string[] { return CAPABILITY_CATALOG.map((c) => c.key); }
export function capabilitiesForRole(role: AgentRole): Capability[] {
  const allowed = new Set(AUTHORIZATION_MATRIX[role] ?? []);
  return CAPABILITY_CATALOG.filter((c) => allowed.has(c.key));
}
export function isAllowedForRole(role: AgentRole, key: string): boolean {
  return (AUTHORIZATION_MATRIX[role] ?? []).includes(key);
}
export function categories(): CapabilityCategory[] {
  return Array.from(new Set(CAPABILITY_CATALOG.map((c) => c.category)));
}
/** Sanidade do catálogo: matriz só referencia keys existentes; sem duplicata. */
export function validateCatalog(): string[] {
  const errors: string[] = [];
  const keys = new Set(allCapabilityKeys());
  for (const [role, list] of Object.entries(AUTHORIZATION_MATRIX)) {
    for (const k of list) if (!keys.has(k)) errors.push(`matriz[${role}] referencia capability inexistente: ${k}`);
  }
  if (keys.size !== CAPABILITY_CATALOG.length) errors.push('capability_key duplicada no catálogo');
  return errors;
}

// ---------------------------------------------------------------------------
// Resolver: papel + entitlements/conexões do tenant → status de cada capability.
// É a "verdade" que o Admin mostra e que o runtime usa para anexar/bloquear tools.
// ---------------------------------------------------------------------------

export type CapabilityStatus =
  | 'active'              // permitido e pronto para uso em produção
  | 'needs_connection'   // permitido, mas falta a corretora conectar (Vault/OAuth)
  | 'needs_entitlement'  // permitido, mas a corretora ainda não habilitou
  | 'disabled'           // habilitação existe mas está desligada
  | 'not_allowed_for_role'; // o papel do agente não pode usar esta capability

export interface TenantEntitlement {
  capability_key: string;
  enabled: boolean;
  connection_present?: boolean; // existe tenant_connection saudável p/ esta capability
}

export interface ResolvedCapability {
  key: string;
  status: CapabilityStatus;
  reason: string;
  capability: Capability;
}

/**
 * Para auxiliares, `declaredKeys` é o subconjunto que o contrato exige; só ele é considerado
 * (mínimo necessário). Para core/attendance/subagent, considera-se toda a matriz do papel.
 */
export function resolveAgentCapabilities(
  role: AgentRole,
  entitlements: TenantEntitlement[] = [],
  declaredKeys?: string[],
): ResolvedCapability[] {
  const allowed = new Set(AUTHORIZATION_MATRIX[role] ?? []);
  const ent = new Map(entitlements.map((e) => [e.capability_key, e]));
  const declared = declaredKeys ? new Set(declaredKeys) : null;

  const out: ResolvedCapability[] = [];
  for (const cap of CAPABILITY_CATALOG) {
    if (declared && !declared.has(cap.key)) continue; // auxiliar: só o que declarou
    if (!allowed.has(cap.key)) {
      out.push({ key: cap.key, status: 'not_allowed_for_role', reason: `papel "${role}" não pode usar`, capability: cap });
      continue;
    }
    const e = ent.get(cap.key);
    if (e && e.enabled === false) {
      out.push({ key: cap.key, status: 'disabled', reason: 'desligado pela corretora', capability: cap });
      continue;
    }
    if (cap.requires_connection && !(e?.connection_present)) {
      out.push({ key: cap.key, status: 'needs_connection', reason: 'aguardando conexão da corretora', capability: cap });
      continue;
    }
    // Capabilities internas/plataforma (sem conexão) nascem LIGADAS em produção.
    // O gate real de externos/operacionais é a conexão (acima); o status 'needs_entitlement'
    // fica reservado para opt-in explícito futuro (ainda não auto-gera).
    out.push({ key: cap.key, status: 'active', reason: 'pronto', capability: cap });
  }
  return out;
}

export function activeKeys(resolved: ResolvedCapability[]): string[] {
  return resolved.filter((r) => r.status === 'active').map((r) => r.key);
}

/** Resumo p/ a UI: contagem por status. */
export function summarize(resolved: ResolvedCapability[]): Record<CapabilityStatus, number> {
  const base: Record<CapabilityStatus, number> = {
    active: 0, needs_connection: 0, needs_entitlement: 0, disabled: 0, not_allowed_for_role: 0,
  };
  for (const r of resolved) base[r.status] += 1;
  return base;
}

/** Uma capability exige aprovação humana para executar a ação? (gate de produção). */
export function requiresApproval(key: string): boolean {
  return Boolean(getCapability(key)?.requires_approval);
}
