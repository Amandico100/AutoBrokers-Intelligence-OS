// 43P0 — Portal Browser Registry contracts. PURO, self-contained, SEM execução
// real (nenhum browser, login, credencial ou portal real). Contratos + validação
// + sanitização para a futura infraestrutura global de portais (SPEC-011).
//
// Regra de ouro: dry_run=true e real_action_allowed=false por padrão; nenhum
// segredo/cookie/storageState/OTP/CAPTCHA token nesta camada.

export type PortalOwnerKind = 'insurer' | 'provider' | 'regulator' | 'broker_tool' | 'other';
export type PortalAuthMethod = 'password' | 'mfa' | 'captcha' | 'sso' | 'certificate';
export type PortalRisk = 'low' | 'medium' | 'high';
export type PortalStatus = 'draft' | 'mapped' | 'sandbox_ready' | 'homologating' | 'approved_future' | 'blocked';

export interface PortalDefinition {
  portal_id: string;
  label: string;
  owner_kind: PortalOwnerKind;
  insurer_key?: string | null;
  provider_key?: string | null;
  base_url: string;
  login_url?: string | null;
  supported_channels: Array<'browser' | 'api' | 'email' | 'phone'>;
  auth_methods: PortalAuthMethod[];
  risk_level: PortalRisk;
  status: PortalStatus;
  notes?: string | null;
}

export interface PortalPage {
  page_id: string;
  label: string;
  url_pattern: string; // padrão, nunca query com segredo
  kind: 'login' | 'dashboard' | 'form' | 'list' | 'detail' | 'download' | 'challenge' | 'other';
}

export interface PortalJourney {
  journey_id: string;
  label: string;
  steps: string[]; // descrição de passos, sem segredo
  expected_outputs: string[];
}

export interface PortalChallengeRule {
  kind: 'captcha' | 'otp' | 'mfa_app' | 'certificate' | 'token' | 'account_locked';
  detect_hint: string;
  requires_human: true; // SEMPRE humano — nunca bypass
  bypass_allowed: false;
}

export interface PortalMap {
  portal_id: string;
  version: string;
  journeys: PortalJourney[];
  known_pages: PortalPage[];
  challenges: PortalChallengeRule[];
  drift_signals: string[];
  evidence_outputs: string[];
}

export type PortalActionKind =
  | 'open_assistance'
  | 'open_claim'
  | 'check_payment'
  | 'download_policy'
  | 'consult_status'
  | 'upload_document'
  | 'other';

export type PortalSkillPromotion = 'draft' | 'sandbox' | 'validated' | 'approved_future';

export interface PortalSkill {
  skill_id: string;
  portal_id: string;
  objective: string;
  corridor_key?: string | null;
  subcorridor_key?: string | null;
  action_kind: PortalActionKind;
  required_inputs: string[];
  output_schema: Record<string, unknown>;
  allowed_actions: string[];
  forbidden_actions: string[];
  promotion_status: PortalSkillPromotion;
}

export interface PortalActionCandidate {
  case_id: string | null;
  action_goal: string;
  portal_id: string;
  portal_skill_id: string | null;
  required_inputs: string[];
  available_inputs: Record<string, unknown>;
  missing_inputs: string[];
  credential_ref_required: boolean;
  session_ref_required: boolean;
  approval_required: boolean;
  dry_run: true; // SEMPRE
  real_send_allowed: false; // SEMPRE
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// Chaves que NUNCA podem aparecer em contratos desta camada.
export const PORTAL_FORBIDDEN_KEYS = [
  'password', 'senha', 'token', 'client_token', 'cookie', 'cookies',
  'storage_state', 'storagestate', 'otp', 'mfa_code', 'captcha_token',
  'authorization', 'secret', 'certificate_pem', 'private_key',
];

/** Verifica recursivamente se algum campo proibido (segredo/PII) vazou. PURO. */
export function findForbiddenKeys(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (PORTAL_FORBIDDEN_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findForbiddenKeys(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

function isHttpsLike(url: string | null | undefined): boolean {
  return typeof url === 'string' && /^https:\/\//i.test(url.trim());
}

export function validatePortalDefinition(def: Partial<PortalDefinition> | null | undefined): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!def || typeof def !== 'object') return { valid: false, errors: ['missing_definition'], warnings };
  if (!def.portal_id) errors.push('missing_portal_id');
  if (!def.label) errors.push('missing_label');
  if (!def.owner_kind) errors.push('missing_owner_kind');
  if (!isHttpsLike(def.base_url)) errors.push('base_url_must_be_https');
  if (def.login_url && !isHttpsLike(def.login_url)) errors.push('login_url_must_be_https');
  if (!Array.isArray(def.auth_methods) || def.auth_methods.length === 0) warnings.push('no_auth_methods_declared');
  if ((def.auth_methods || []).includes('captcha') || (def.auth_methods || []).includes('mfa')) {
    warnings.push('challenge_capable_portal_requires_hitl');
  }
  if (findForbiddenKeys(def).length > 0) errors.push('forbidden_secret_field_present');
  return { valid: errors.length === 0, errors, warnings };
}

export function validatePortalMap(map: Partial<PortalMap> | null | undefined): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!map || typeof map !== 'object') return { valid: false, errors: ['missing_map'], warnings };
  if (!map.portal_id) errors.push('missing_portal_id');
  if (!map.version) errors.push('missing_version');
  if (!Array.isArray(map.journeys) || map.journeys.length === 0) warnings.push('no_journeys');
  if (!Array.isArray(map.challenges)) warnings.push('no_challenge_rules');
  // Toda regra de challenge precisa ser HITL (nunca bypass). Valida input não-confiável.
  for (const chRaw of map.challenges || []) {
    const ch = chRaw as unknown as Record<string, unknown>;
    if (ch.bypass_allowed === true || ch.requires_human === false) {
      errors.push('challenge_rule_must_be_hitl');
    }
  }
  if (findForbiddenKeys(map).length > 0) errors.push('forbidden_secret_field_present');
  return { valid: errors.length === 0, errors, warnings };
}

export function validatePortalSkill(skill: Partial<PortalSkill> | null | undefined): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!skill || typeof skill !== 'object') return { valid: false, errors: ['missing_skill'], warnings };
  if (!skill.skill_id) errors.push('missing_skill_id');
  if (!skill.portal_id) errors.push('missing_portal_id');
  if (!skill.objective) errors.push('missing_objective');
  if (!skill.action_kind) errors.push('missing_action_kind');
  if (skill.promotion_status === 'approved_future') warnings.push('approved_future_still_blocked_in_43p0');
  // Forbidden actions devem conter as proibições de segurança mínimas.
  const forb = (skill.forbidden_actions || []).join(' ').toLowerCase();
  if (!forb.includes('captcha') && !forb.includes('2fa') && !forb.includes('otp')) {
    warnings.push('skill_should_forbid_captcha_2fa_bypass');
  }
  if (findForbiddenKeys(skill).length > 0) errors.push('forbidden_secret_field_present');
  return { valid: errors.length === 0, errors, warnings };
}

/** Sanitiza uma PortalDefinition para resposta pública (remove qualquer campo proibido). */
export function sanitizePortalDefinition(def: PortalDefinition): Record<string, unknown> {
  const clone: Record<string, unknown> = { ...def };
  for (const k of Object.keys(clone)) {
    if (PORTAL_FORBIDDEN_KEYS.includes(k.toLowerCase())) delete clone[k];
  }
  return clone;
}

export interface BuildActionCandidateInput {
  case_id?: string | null;
  action_goal: string;
  portal: PortalDefinition;
  skill?: PortalSkill | null;
  available_inputs?: Record<string, unknown>;
}

/** Monta um PortalActionCandidate. NUNCA executa. dry_run/real_send sempre travados. */
export function buildPortalActionCandidate(input: BuildActionCandidateInput): PortalActionCandidate {
  const required = input.skill?.required_inputs ?? [];
  const available = input.available_inputs ?? {};
  const missing = required.filter((k) => available[k] === undefined || available[k] === null || available[k] === '');
  const authMethods = input.portal.auth_methods || [];
  return {
    case_id: input.case_id ?? null,
    action_goal: input.action_goal,
    portal_id: input.portal.portal_id,
    portal_skill_id: input.skill?.skill_id ?? null,
    required_inputs: required,
    available_inputs: available,
    missing_inputs: missing,
    credential_ref_required: authMethods.includes('password') || authMethods.includes('certificate') || authMethods.includes('sso'),
    session_ref_required: authMethods.includes('mfa') || authMethods.includes('captcha') || authMethods.includes('password'),
    approval_required: true,
    dry_run: true,
    real_send_allowed: false,
  };
}
