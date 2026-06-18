// 43P3 — Portal Skills v1. PURO, self-contained. Skill = DEFINIÇÃO de tarefa
// (não agente solto): objetivo, inputs, ações permitidas/proibidas, passos,
// outputs esperados e guardrails. NÃO acessa URL real. promotion_status máximo
// 'sandbox_validated' neste estágio; real_action_allowed sempre false.

export type PortalSkillPromotion = 'draft' | 'sandbox_validated' | 'approved_future';

export interface PortalSkillRecord {
  portal_skill_id: string;
  portal_id: string;
  portal_map_id: string;
  skill_key: string;
  journey: string;
  objective: string;
  required_inputs: string[];
  allowed_actions: string[];
  forbidden_actions: string[];
  steps: string[];
  expected_outputs: string[];
  guardrails: string[];
  promotion_status: PortalSkillPromotion;
  real_action_allowed: false;
}

const ALLIANZNET_LOGIN_CHECK_V1: PortalSkillRecord = {
  portal_skill_id: 'allianznet_corretor_login_check_v1',
  portal_id: 'allianz__allianznet_corretor_portal_do_corretor',
  portal_map_id: 'allianznet_corretor_login_map_v1',
  skill_key: 'login_check',
  journey: 'login',
  objective: 'Validar, em dry-run, que o portal do corretor possui jornada de login mapeável, sem executar login real.',
  required_inputs: ['portal_id', 'portal_account_id', 'credential_ref', 'session_ref_or_pending', 'provider'],
  allowed_actions: [
    'observe_login_screen_mock',
    'detect_login_form_mock',
    'extract_field_labels_mock',
    'detect_challenge_mock',
    'build_trace_replay',
  ],
  forbidden_actions: [
    'insert_username_password_real',
    'submit_login_real',
    'bypass_captcha_2fa',
    'access_real_url',
    'download_upload_real',
    'store_raw_storage_state_cookie',
    'expose_credential',
  ],
  steps: [
    'start_relay_sandbox',
    'observe_landing_login_page',
    'extract_visible_auth_fields',
    'classify_challenges',
    'simulate_post_login_ready_mock',
    'build_trace_replay',
    'evaluate_skill',
  ],
  expected_outputs: ['login_form_detected', 'auth_required', 'post_login_home_detected'],
  guardrails: [
    'nunca inserir credencial real',
    'nunca submeter login real',
    'CAPTCHA/2FA = HITL, nunca bypass',
    'nenhuma URL real acessada',
    'sem PII/segredo no trace/replay',
  ],
  promotion_status: 'draft',
  real_action_allowed: false,
};

const SKILLS: PortalSkillRecord[] = [ALLIANZNET_LOGIN_CHECK_V1];

export function getPortalSkills(): PortalSkillRecord[] {
  return SKILLS.map((s) => ({ ...s }));
}

export function getPortalSkill(portalId: string | null | undefined, skillKey: string | null | undefined): PortalSkillRecord | null {
  const s = SKILLS.find((x) => x.portal_id === portalId && x.skill_key === skillKey);
  return s ? { ...s } : null;
}

export function getPortalSkillById(skillId: string | null | undefined): PortalSkillRecord | null {
  const s = SKILLS.find((x) => x.portal_skill_id === skillId);
  return s ? { ...s } : null;
}

export interface SkillValidationResult { valid: boolean; errors: string[]; warnings: string[]; }

export function validatePortalSkill(skill: Partial<PortalSkillRecord> | null | undefined): SkillValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!skill || typeof skill !== 'object') return { valid: false, errors: ['missing_skill'], warnings };
  if (!skill.portal_skill_id) errors.push('missing_portal_skill_id');
  if (!skill.portal_id) errors.push('missing_portal_id');
  if (!skill.portal_map_id) errors.push('missing_portal_map_id');
  if (!skill.skill_key) errors.push('missing_skill_key');
  if (!skill.objective) errors.push('missing_objective');
  const forb = (skill.forbidden_actions || []).join(' ').toLowerCase();
  if (!forb.includes('captcha') && !forb.includes('2fa')) warnings.push('skill_should_forbid_captcha_2fa');
  if (!forb.includes('real')) warnings.push('skill_should_forbid_real_actions');
  if (skill.promotion_status === 'approved_future') warnings.push('approved_future_blocked_in_43p3');
  return { valid: errors.length === 0, errors, warnings };
}
