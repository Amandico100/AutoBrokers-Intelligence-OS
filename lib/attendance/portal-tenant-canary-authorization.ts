// 43P-FINAL-1 — autorização de canary por TENANT + PORTAL + APPROVAL.
// SELF-CONTAINED (testável offline). Falha fechado. O kill switch SEMPRE vence
// qualquer approval; flag global é freio final; approval expira; approval é por
// company_id + portal_account_id (nunca global/indefinida).

export interface CanaryApprovalRecord {
  company_id: string;
  portal_id: string;
  portal_account_id: string;
  journey: string; // ex.: 'login'
  mode: string; // deve ser 'read_only_canary'
  approved_by: string | null;
  approved_at: string | null; // ISO
  expires_at: string | null; // ISO
  purpose?: string | null;
  revoked?: boolean;
}

export interface CanaryAuthorizationContext {
  // identidade do alvo
  company_id: string | null;
  portal_id: string | null;
  portal_account_id: string | null;
  journey: string | null;
  // quem opera
  is_master: boolean;
  operator_company_id: string | null; // company travada do operador (tenant admin)
  // freios globais
  global_kill_switch: boolean;
  global_flag_enabled: boolean; // ex.: PORTAL_LOGIN_REAL_ENABLED + BROWSERBASE_REAL_BROWSER_ENABLED resolvidos
  // browserbase readiness (env+flags) já avaliado
  readiness_can_open: boolean;
  // approval encontrada para o alvo (ou null)
  approval: CanaryApprovalRecord | null;
  now?: number;
}

export interface CanaryAuthorizationResult {
  authorized: boolean;
  blockers: string[];
  mode: 'read_only_canary';
  real_action_allowed: false;
}

export function evaluateTenantCanaryAuthorization(ctx: CanaryAuthorizationContext): CanaryAuthorizationResult {
  const now = ctx.now ?? Date.now();
  const blockers: string[] = [];

  if (!ctx.company_id) blockers.push('company_scope_missing');
  if (!ctx.portal_id) blockers.push('portal_missing');
  if (!ctx.portal_account_id) blockers.push('portal_account_missing');
  if (!ctx.journey) blockers.push('journey_missing');

  // Isolamento: tenant admin só opera a própria company; master pode escolher.
  if (!ctx.is_master) {
    if (!ctx.operator_company_id) blockers.push('operator_not_scoped');
    else if (ctx.company_id && ctx.operator_company_id !== ctx.company_id) blockers.push('cross_tenant_denied');
  }

  // Freios globais (kill switch SEMPRE vence).
  if (ctx.global_kill_switch) blockers.push('global_kill_switch_active');
  if (!ctx.global_flag_enabled) blockers.push('global_flag_disabled');
  if (!ctx.readiness_can_open) blockers.push('browserbase_not_ready');

  // Approval por tenant + portal account (nunca global).
  const a = ctx.approval;
  if (!a) blockers.push('approval_missing');
  else {
    if (a.revoked) blockers.push('approval_revoked');
    if (a.mode !== 'read_only_canary') blockers.push('approval_mode_invalid');
    if (a.company_id !== ctx.company_id) blockers.push('approval_company_mismatch');
    if (a.portal_account_id !== ctx.portal_account_id) blockers.push('approval_account_mismatch');
    if (ctx.portal_id && a.portal_id !== ctx.portal_id) blockers.push('approval_portal_mismatch');
    if (ctx.journey && a.journey !== ctx.journey) blockers.push('approval_journey_mismatch');
    if (!a.approved_by || !a.approved_at) blockers.push('approval_incomplete');
    if (!a.expires_at) blockers.push('approval_no_expiry'); // approval global/indefinida é proibida
    else if (Date.parse(a.expires_at) <= now) blockers.push('approval_expired');
  }

  return { authorized: blockers.length === 0, blockers, mode: 'read_only_canary', real_action_allowed: false };
}
