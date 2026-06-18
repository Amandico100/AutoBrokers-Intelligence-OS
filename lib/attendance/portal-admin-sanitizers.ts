// 43P1 — Portal admin records, sanitizers & pure logic. PURO, self-contained
// (sem imports cross-module em runtime, p/ testes Node .mjs).
//
// Cria/valida/sanitiza PortalDefinitionRecord, PortalAccountRecord,
// CredentialRefRecord e SessionRefRecord. NUNCA armazena segredo cru: senha/
// token/cookie/storageState/OTP são rejeitados; refs ficam mascaradas.
// Nenhum portal real é acessado.

export type PortalOwnerKind = 'insurer' | 'provider' | 'regulator' | 'broker' | 'other';
export type PortalDefinitionStatus = 'draft' | 'sandbox_ready' | 'needs_review' | 'inactive';
export type PortalAuthMethod = 'password' | 'mfa' | 'captcha' | 'sso' | 'certificate' | 'otp';
export type BrowserStrategyKind = 'browserbase_playwright_stagehand' | 'browserbase' | 'local_playwright' | 'skyvern_lab' | 'unknown';

/** 43P1.1 — estratégia de browser canônica (primary + fallback). */
export interface BrowserStrategySpec {
  primary: BrowserStrategyKind;
  fallback: BrowserStrategyKind | null;
}

/** Connector template canônico do Portal Browser (NUNCA reaproveitar whatsapp_zapi). */
export const PORTAL_BROWSER_CONNECTOR_SLUG = 'portal_browser' as const;

export interface ChallengeProfile {
  captcha: boolean;
  mfa: boolean;
  certificate: boolean;
  otp: boolean;
  requires_hitl: boolean; // SEMPRE true quando há qualquer challenge
}

/** Normaliza browser_strategy: aceita string OU {primary,fallback} → canônico. */
export function normalizeBrowserStrategy(input: unknown): BrowserStrategySpec {
  const valid = (v: unknown): BrowserStrategyKind => {
    const allowed = ['browserbase_playwright_stagehand', 'browserbase', 'local_playwright', 'skyvern_lab', 'unknown'];
    return (typeof v === 'string' && allowed.includes(v)) ? (v as BrowserStrategyKind) : 'unknown';
  };
  if (input && typeof input === 'object') {
    const o = input as Record<string, unknown>;
    return { primary: valid(o.primary ?? 'browserbase'), fallback: o.fallback != null ? valid(o.fallback) : null };
  }
  if (typeof input === 'string') return { primary: valid(input), fallback: null };
  return { primary: 'browserbase', fallback: 'skyvern_lab' };
}

export interface PortalDefinitionRecord {
  portal_id: string;
  label: string;
  owner_kind: PortalOwnerKind;
  owner_key: string;
  base_url: string;
  login_url?: string | null;
  supported_journeys: string[];
  auth_methods: PortalAuthMethod[];
  challenge_profile: ChallengeProfile;
  browser_strategy: BrowserStrategySpec;
  status: PortalDefinitionStatus;
  scope?: 'global' | 'tenant_draft' | 'tenant_override';
  notes?: string | null;
  metadata?: Record<string, unknown>; // 43P1.2 — evidência/fonte/confidence (sem credencial/PII)
  created_at: string;
  updated_at: string;
}

export type PortalAccountStatus =
  | 'not_configured' | 'credential_pending' | 'session_pending'
  | 'healthy' | 'expired' | 'challenge_required' | 'revoked' | 'error';

export type CredentialRefRecordStatus = 'pending' | 'available' | 'revoked' | 'expired' | 'unknown';
export type SessionRefRecordStatus = 'healthy' | 'expired' | 'challenge_required' | 'revoked' | 'unknown';
export type SessionProvider = 'browserbase' | 'local_playwright' | 'skyvern_lab' | 'unknown';

export interface CredentialRefRecord {
  credential_ref_id: string;
  company_id: string;
  portal_id: string;
  vault_ref_masked: string; // NUNCA o segredo nem a ref crua
  status: CredentialRefRecordStatus;
  created_at: string;
  updated_at: string;
}

export interface SessionRefRecord {
  session_ref_id: string;
  company_id: string;
  portal_id: string;
  storage_ref_masked: string; // NUNCA cookie/storageState
  provider: SessionProvider;
  status: SessionRefRecordStatus;
  expires_at?: string | null;
  last_checked_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PortalAccountRecord {
  portal_account_id: string;
  company_id: string;
  portal_id: string;
  label: string;
  credential_ref?: CredentialRefRecord | null;
  session_ref?: SessionRefRecord | null;
  status: PortalAccountStatus;
  last_health_check_at?: string | null;
  challenge_profile: ChallengeProfile;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

// Campos crus que NUNCA podem chegar nesta camada (rejeição 400).
export const REQUEST_FORBIDDEN_KEYS = [
  'password', 'senha', 'pass', 'pwd', 'token', 'client_token', 'cookie', 'cookies',
  'storage_state', 'storagestate', 'otp', 'code', 'mfa_code', 'secret', 'apikey',
  'api_key', 'authorization', 'bearer', 'private_key', 'certificate_pem',
];

/** Procura recursivamente campos proibidos (segredo cru). PURO. */
export function findRequestSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (REQUEST_FORBIDDEN_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findRequestSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

function nowIso(): string { return new Date().toISOString(); }
function genId(p: string): string { return `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`; }
function maskRef(ref: string | null | undefined): string {
  if (!ref) return '***';
  const s = String(ref);
  if (s.length <= 6) return '***';
  return `${s.slice(0, 3)}…${s.slice(-3)}`;
}
function isHttps(url: string | null | undefined): boolean {
  return typeof url === 'string' && /^https:\/\//i.test(url.trim());
}

/** Deriva o challenge_profile a partir dos auth_methods declarados. */
export function buildChallengeProfile(authMethods: PortalAuthMethod[] = []): ChallengeProfile {
  const captcha = authMethods.includes('captcha');
  const mfa = authMethods.includes('mfa');
  const certificate = authMethods.includes('certificate');
  const otp = authMethods.includes('otp');
  return { captcha, mfa, certificate, otp, requires_hitl: captcha || mfa || certificate || otp };
}

export interface ValidationResult { valid: boolean; errors: string[]; warnings: string[]; }

export function validatePortalDefinitionInput(input: Partial<PortalDefinitionRecord> | null | undefined): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!input || typeof input !== 'object') return { valid: false, errors: ['missing_input'], warnings };
  if (!input.label) errors.push('missing_label');
  if (!input.owner_key) errors.push('missing_owner_key');
  if (!isHttps(input.base_url)) errors.push('base_url_must_be_https');
  if (input.login_url && !isHttps(input.login_url)) errors.push('login_url_must_be_https');
  const prof = input.challenge_profile;
  if (prof && (prof.captcha || prof.mfa || prof.certificate || prof.otp) && prof.requires_hitl !== true) {
    errors.push('challenge_profile_must_require_hitl');
  }
  if (findRequestSecrets(input).length > 0) errors.push('forbidden_secret_field_present');
  return { valid: errors.length === 0, errors, warnings };
}

export interface BuildPortalDefinitionInput {
  portal_id?: string;
  label: string;
  owner_kind?: PortalOwnerKind;
  owner_key: string;
  base_url: string;
  login_url?: string | null;
  supported_journeys?: string[];
  auth_methods?: PortalAuthMethod[];
  browser_strategy?: unknown; // string | {primary,fallback} → normalizado
  challenge_profile?: Partial<ChallengeProfile> | null; // override explícito opcional
  status?: PortalDefinitionStatus;
  scope?: 'global' | 'tenant_draft' | 'tenant_override';
  notes?: string | null;
  created_at?: string;
}

export function buildPortalDefinitionRecord(input: BuildPortalDefinitionInput): PortalDefinitionRecord {
  const now = nowIso();
  const authMethods = input.auth_methods ?? [];
  // 43P1.1 — deriva o challenge_profile dos auth_methods, mas aceita override
  // explícito; requires_hitl é sempre forçado quando há qualquer challenge.
  const derived = buildChallengeProfile(authMethods);
  const ov = input.challenge_profile ?? null;
  const challenge_profile: ChallengeProfile = ov
    ? {
        captcha: ov.captcha ?? derived.captcha,
        mfa: ov.mfa ?? derived.mfa,
        certificate: ov.certificate ?? derived.certificate,
        otp: ov.otp ?? derived.otp,
        requires_hitl: true, // recomputado abaixo
      }
    : derived;
  if (ov) challenge_profile.requires_hitl = challenge_profile.captcha || challenge_profile.mfa || challenge_profile.certificate || challenge_profile.otp;
  return {
    portal_id: input.portal_id ?? genId('portal'),
    label: input.label,
    owner_kind: input.owner_kind ?? 'insurer',
    owner_key: input.owner_key,
    base_url: input.base_url,
    login_url: input.login_url ?? null,
    supported_journeys: input.supported_journeys ?? [],
    auth_methods: authMethods,
    challenge_profile,
    browser_strategy: normalizeBrowserStrategy(input.browser_strategy),
    status: input.status ?? 'draft',
    scope: input.scope ?? 'tenant_draft',
    notes: input.notes ?? null,
    created_at: input.created_at ?? now,
    updated_at: now,
  };
}

export interface BuildPortalAccountInput {
  portal_account_id?: string;
  company_id: string;
  portal_id: string;
  label: string;
  challenge_profile?: ChallengeProfile;
  auth_methods?: PortalAuthMethod[];
  notes?: string | null;
  created_at?: string;
}

export function buildPortalAccountRecord(input: BuildPortalAccountInput): PortalAccountRecord {
  const now = nowIso();
  return {
    portal_account_id: input.portal_account_id ?? genId('pacct'),
    company_id: input.company_id,
    portal_id: input.portal_id,
    label: input.label,
    credential_ref: null,
    session_ref: null,
    status: 'not_configured',
    last_health_check_at: null,
    challenge_profile: input.challenge_profile ?? buildChallengeProfile(input.auth_methods ?? []),
    notes: input.notes ?? null,
    created_at: input.created_at ?? now,
    updated_at: now,
  };
}

export interface BuildCredentialRefInput {
  company_id: string;
  portal_id: string;
  vault_ref: string; // ref opaca ao segredo; NUNCA o segredo
  status?: CredentialRefRecordStatus;
}

/** Cria CredentialRefRecord. Lança se receber segredo cru no input. */
export function buildCredentialRefRecord(input: BuildCredentialRefInput): CredentialRefRecord {
  const leak = findRequestSecrets(input);
  if (leak.length > 0) throw new Error(`credential_secret_leak:${leak.join(',')}`);
  if (!input.vault_ref) throw new Error('missing_vault_ref');
  const now = nowIso();
  return {
    credential_ref_id: genId('cred'),
    company_id: input.company_id,
    portal_id: input.portal_id,
    vault_ref_masked: maskRef(input.vault_ref),
    status: input.status ?? 'available',
    created_at: now,
    updated_at: now,
  };
}

export interface BuildSessionRefInput {
  company_id: string;
  portal_id: string;
  storage_ref: string; // ref opaca ao storageState criptografado
  provider?: SessionProvider;
  status?: SessionRefRecordStatus;
  expires_at?: string | null;
}

/** Cria SessionRefRecord. Lança se receber cookie/storageState cru no input. */
export function buildSessionRefRecord(input: BuildSessionRefInput): SessionRefRecord {
  const leak = findRequestSecrets(input);
  if (leak.length > 0) throw new Error(`session_secret_leak:${leak.join(',')}`);
  if (!input.storage_ref) throw new Error('missing_storage_ref');
  const now = nowIso();
  return {
    session_ref_id: genId('sess'),
    company_id: input.company_id,
    portal_id: input.portal_id,
    storage_ref_masked: maskRef(input.storage_ref),
    provider: input.provider ?? 'browserbase',
    status: input.status ?? 'unknown',
    expires_at: input.expires_at ?? null,
    last_checked_at: null,
    created_at: now,
    updated_at: now,
  };
}

/** Deriva o status da conta a partir das refs presentes. */
export function deriveAccountStatus(account: PortalAccountRecord): PortalAccountStatus {
  if (!account.credential_ref) return 'credential_pending';
  if (!account.session_ref) return 'session_pending';
  const s = account.session_ref.status;
  if (s === 'revoked') return 'revoked';
  if (s === 'challenge_required') return 'challenge_required';
  if (s === 'expired') return 'expired';
  if (s === 'healthy') return 'healthy';
  return 'session_pending';
}

export interface MockHealthResult {
  status: PortalAccountStatus;
  session_status: SessionRefRecordStatus;
  usable: boolean;
  requires_human: boolean;
  checked_at: string;
  reason: string;
}

/**
 * Health-check MOCK (não abre browser, não acessa portal). Reavalia a SessionRef
 * só por metadados (status + expiração). 43P1.
 */
export function mockHealthCheck(account: PortalAccountRecord, now: number = Date.now()): MockHealthResult {
  const checked_at = new Date(now).toISOString();
  if (!account.credential_ref) {
    return { status: 'credential_pending', session_status: 'unknown', usable: false, requires_human: true, checked_at, reason: 'no_credential_ref' };
  }
  if (!account.session_ref) {
    return { status: 'session_pending', session_status: 'unknown', usable: false, requires_human: true, checked_at, reason: 'no_session_ref' };
  }
  const sess = account.session_ref;
  if (sess.status === 'revoked') return { status: 'revoked', session_status: 'revoked', usable: false, requires_human: true, checked_at, reason: 'session_revoked' };
  if (sess.status === 'challenge_required') return { status: 'challenge_required', session_status: 'challenge_required', usable: false, requires_human: true, checked_at, reason: 'challenge_required' };
  if (sess.expires_at && new Date(sess.expires_at).getTime() <= now) {
    return { status: 'expired', session_status: 'expired', usable: false, requires_human: true, checked_at, reason: 'session_expired' };
  }
  if (sess.status === 'healthy') return { status: 'healthy', session_status: 'healthy', usable: true, requires_human: false, checked_at, reason: 'session_healthy' };
  return { status: 'session_pending', session_status: 'unknown', usable: false, requires_human: true, checked_at, reason: 'session_unknown_needs_check' };
}

// --- sanitizers para resposta pública ---------------------------------------
export function sanitizePortalAccountRecord(acc: PortalAccountRecord): Record<string, unknown> {
  return {
    portal_account_id: acc.portal_account_id,
    company_id: acc.company_id,
    portal_id: acc.portal_id,
    label: acc.label,
    status: acc.status,
    challenge_profile: acc.challenge_profile,
    credential_ref: acc.credential_ref
      ? { credential_ref_id: acc.credential_ref.credential_ref_id, vault_ref_masked: acc.credential_ref.vault_ref_masked, status: acc.credential_ref.status }
      : null,
    session_ref: acc.session_ref
      ? { session_ref_id: acc.session_ref.session_ref_id, storage_ref_masked: acc.session_ref.storage_ref_masked, provider: acc.session_ref.provider, status: acc.session_ref.status, expires_at: acc.session_ref.expires_at ?? null }
      : null,
    last_health_check_at: acc.last_health_check_at ?? null,
    notes: acc.notes ?? null,
    created_at: acc.created_at,
    updated_at: acc.updated_at,
  };
}

// --- resolve para Action Engine / Portal Action Candidate -------------------
export interface ResolvePortalContext {
  company_id: string;
  owner_key?: string | null;
  portal_id?: string | null;
  journey?: string | null;
}

export interface PortalResolution {
  portal_available: boolean;
  portal_id: string | null;
  portal_account_status: PortalAccountStatus | null;
  credential_status: CredentialRefRecordStatus | null;
  session_status: SessionRefRecordStatus | null;
  challenge_required: boolean;
  next_step: string;
  real_action_allowed: false; // SEMPRE
}

/**
 * Resolve o portal/conta para um objetivo (journey). PURO: recebe os registros
 * já carregados. Escolhe por portal_id explícito ou por owner_key + journey.
 */
export function resolvePortalForJourney(
  definitions: PortalDefinitionRecord[],
  accounts: PortalAccountRecord[],
  ctx: ResolvePortalContext,
): PortalResolution {
  const blocked: Omit<PortalResolution, 'portal_available' | 'portal_id' | 'next_step'> = {
    portal_account_status: null, credential_status: null, session_status: null, challenge_required: false, real_action_allowed: false,
  };
  let def: PortalDefinitionRecord | undefined;
  if (ctx.portal_id) def = definitions.find((d) => d.portal_id === ctx.portal_id);
  else if (ctx.owner_key) {
    def = definitions.find((d) => d.owner_key === ctx.owner_key && (!ctx.journey || d.supported_journeys.includes(ctx.journey)))
      || definitions.find((d) => d.owner_key === ctx.owner_key);
  }
  if (!def) return { ...blocked, portal_available: false, portal_id: null, next_step: 'no_portal_definition' };

  const acct = accounts.find((a) => a.portal_id === def!.portal_id && a.company_id === ctx.company_id);
  if (!acct) {
    return { ...blocked, portal_available: true, portal_id: def.portal_id, challenge_required: def.challenge_profile.requires_hitl, next_step: 'create_portal_account' };
  }
  const health = mockHealthCheck(acct);
  return {
    portal_available: true,
    portal_id: def.portal_id,
    portal_account_status: health.status,
    credential_status: acct.credential_ref?.status ?? null,
    session_status: acct.session_ref?.status ?? null,
    challenge_required: def.challenge_profile.requires_hitl || health.status === 'challenge_required',
    next_step: health.usable ? 'ready_for_dry_run_43p3' : `resolve_${health.reason}`,
    real_action_allowed: false,
  };
}

// --- 43P1.1 — Global Portal Catalog + canonical resolve ---------------------

/**
 * Catálogo GLOBAL de portais (canônico, sem credencial). Vazio até o intake real
 * ser sincronizado (ver 43P1.1 intake sync manifest). NUNCA inventar URL real.
 */
export const GLOBAL_PORTAL_DEFINITIONS: PortalDefinitionRecord[] = [];

export function getGlobalPortalCatalog(): PortalDefinitionRecord[] {
  return GLOBAL_PORTAL_DEFINITIONS.map((d) => ({ ...d, scope: 'global' as const }));
}

export type PortalSource = 'global' | 'tenant_override' | 'tenant_draft' | 'none';

export interface CanonicalPortalResolution extends PortalResolution {
  portal_source: PortalSource;
  account_source: 'tenant' | null;
  connector_template: typeof PORTAL_BROWSER_CONNECTOR_SLUG;
}

/**
 * Resolve canônico (43P1.1): catálogo global → override/draft do tenant → conta
 * tenant saudável. Sempre real_action_allowed=false e connector_template
 * portal_browser (nunca whatsapp_zapi). PURO.
 */
export function resolvePortalCanonical(
  globalDefs: PortalDefinitionRecord[],
  tenantDefs: PortalDefinitionRecord[],
  accounts: PortalAccountRecord[],
  ctx: ResolvePortalContext,
): CanonicalPortalResolution {
  const matches = (d: PortalDefinitionRecord): boolean => {
    if (ctx.portal_id) return d.portal_id === ctx.portal_id;
    if (ctx.owner_key) return d.owner_key === ctx.owner_key && (!ctx.journey || d.supported_journeys.includes(ctx.journey));
    return false;
  };
  // Tenant override/draft tem prioridade sobre o global (corretora pode ajustar).
  const tenantDef = tenantDefs.find(matches) || tenantDefs.find((d) => ctx.owner_key ? d.owner_key === ctx.owner_key : false);
  const globalDef = globalDefs.find(matches) || globalDefs.find((d) => ctx.owner_key ? d.owner_key === ctx.owner_key : false);
  const def = tenantDef ?? globalDef;
  const portal_source: PortalSource = tenantDef
    ? (tenantDef.scope === 'tenant_override' ? 'tenant_override' : 'tenant_draft')
    : (globalDef ? 'global' : 'none');

  const base = {
    portal_account_status: null, credential_status: null, session_status: null,
    challenge_required: false, real_action_allowed: false as const,
    account_source: null, connector_template: PORTAL_BROWSER_CONNECTOR_SLUG,
  };
  if (!def) return { ...base, portal_available: false, portal_id: null, next_step: 'no_portal_definition', portal_source: 'none' };

  const acct = accounts.find((a) => a.portal_id === def.portal_id && a.company_id === ctx.company_id);
  if (!acct) {
    return { ...base, portal_available: true, portal_id: def.portal_id, challenge_required: def.challenge_profile.requires_hitl, next_step: 'create_portal_account', portal_source };
  }
  const health = mockHealthCheck(acct);
  return {
    portal_available: true,
    portal_id: def.portal_id,
    portal_account_status: health.status,
    credential_status: acct.credential_ref?.status ?? null,
    session_status: acct.session_ref?.status ?? null,
    challenge_required: def.challenge_profile.requires_hitl || health.status === 'challenge_required',
    next_step: health.usable ? 'ready_for_dry_run_43p3' : `resolve_${health.reason}`,
    real_action_allowed: false,
    portal_source,
    account_source: 'tenant',
    connector_template: PORTAL_BROWSER_CONNECTOR_SLUG,
  };
}

// --- intake audit -----------------------------------------------------------
export interface IntakeCandidate {
  source: string;
  portal_candidate: string;
  owner_key: string | null;
  base_url_found: string | null;
  journey_candidates: string[];
  challenge_signals: string[];
  confidence: 'low' | 'medium' | 'high';
  action: 'seed_candidate' | 'needs_review' | 'ignored';
}

export interface IntakeScanResult {
  available: boolean;
  reason?: string;
  candidates: IntakeCandidate[];
}

/**
 * Varre fontes de intake já lidas (descritores seguros — sem PII/credencial).
 * Se nenhuma fonte foi fornecida, retorna intake_sources_not_available. PURO.
 */
export function scanPortalIntakeSources(sources: Array<{ source: string; text?: string }> = []): IntakeScanResult {
  if (!sources || sources.length === 0) {
    return { available: false, reason: 'intake_sources_not_available', candidates: [] };
  }
  const candidates: IntakeCandidate[] = [];
  for (const s of sources) {
    const text = (s.text || '').toLowerCase();
    const urlMatch = (s.text || '').match(/https:\/\/[^\s)"']+/i);
    const challenge_signals: string[] = [];
    for (const sig of ['captcha', 'recaptcha', 'mfa', '2fa', 'otp', 'certificado', 'token']) {
      if (text.includes(sig)) challenge_signals.push(sig);
    }
    candidates.push({
      source: s.source,
      portal_candidate: s.source,
      owner_key: null,
      base_url_found: urlMatch ? urlMatch[0] : null,
      journey_candidates: [],
      challenge_signals,
      confidence: urlMatch ? 'medium' : 'low',
      action: urlMatch ? 'needs_review' : 'ignored',
    });
  }
  return { available: true, candidates };
}
