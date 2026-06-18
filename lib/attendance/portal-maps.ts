// 43P3 — Portal Maps v1. PURO, self-contained. Mapa VERSIONADO da superfície de
// um portal (páginas/jornadas/challenges/outputs). NÃO contém segredo/credencial
// e NÃO acessa URL real. real_action_allowed sempre false.

export type PortalMapStatus = 'draft' | 'sandbox_validated' | 'approved_future';

export interface PortalMapPage {
  page_id: string;
  label: string;
  kind: 'landing' | 'login' | 'home' | 'challenge' | 'session_expired' | 'other';
  field_label_candidates?: string[];
  button_candidates?: string[];
}

export interface PortalMapJourney {
  journey: string;
  label: string;
  page_sequence: string[];
}

export interface PortalMapRecord {
  portal_map_id: string;
  portal_id: string;
  version: string;
  owner_key: string;
  label: string;
  status: PortalMapStatus;
  pages: PortalMapPage[];
  journeys: PortalMapJourney[];
  challenge_signals: string[];
  outputs: string[];
  drift_signals: string[];
  metadata: Record<string, unknown>;
  real_action_allowed: false;
}

const ALLIANZNET_CORRETOR_LOGIN_MAP_V1: PortalMapRecord = {
  portal_map_id: 'allianznet_corretor_login_map_v1',
  portal_id: 'allianz__allianznet_corretor_portal_do_corretor',
  version: 'v1',
  owner_key: 'allianz',
  label: 'AllianzNet Corretor — mapa de login (v1)',
  status: 'draft',
  pages: [
    { page_id: 'landing_or_login', label: 'Landing / login', kind: 'landing', button_candidates: ['entrar', 'acessar', 'login'] },
    {
      page_id: 'login_form',
      label: 'Formulário de login do corretor',
      kind: 'login',
      field_label_candidates: ['usuário', 'user', 'login', 'cpf', 'susep', 'codigo'],
      button_candidates: ['entrar', 'acessar'],
    },
    { page_id: 'post_login_home_mock', label: 'Home pós-login (mock)', kind: 'home' },
    { page_id: 'session_expired_mock', label: 'Sessão expirada (mock)', kind: 'session_expired' },
    { page_id: 'challenge_detected_mock', label: 'Challenge detectado (mock)', kind: 'challenge' },
  ],
  journeys: [
    { journey: 'login', label: 'Login do corretor', page_sequence: ['landing_or_login', 'login_form', 'post_login_home_mock'] },
  ],
  challenge_signals: ['captcha', 'recaptcha', 'otp', 'codigo', '2fa', 'mfa', 'certificado', 'sessao expirada', 'session expired', 'bloqueado', 'credenciais invalidas', 'invalid'],
  outputs: ['login_form_detected', 'auth_required', 'post_login_home_detected', 'session_expired_detected', 'challenge_required'],
  drift_signals: ['novo_seletor_login', 'mudanca_layout', 'campo_inesperado'],
  metadata: { source: 'global_catalog', audience: 'corretor', auth: 'password', captcha_possible: false, note: 'Mapa v1 sandbox; sem acesso real.' },
  real_action_allowed: false,
};

const MAPS: PortalMapRecord[] = [ALLIANZNET_CORRETOR_LOGIN_MAP_V1];

export function getPortalMaps(): PortalMapRecord[] {
  return MAPS.map((m) => ({ ...m }));
}

export function getPortalMapForPortal(portalId: string | null | undefined, journey?: string | null): PortalMapRecord | null {
  if (!portalId) return null;
  const candidates = MAPS.filter((m) => m.portal_id === portalId);
  if (candidates.length === 0) return null;
  if (journey) {
    const withJourney = candidates.find((m) => m.journeys.some((j) => j.journey === journey));
    if (withJourney) return { ...withJourney };
  }
  return { ...candidates[0] };
}

export function getPortalMapById(mapId: string | null | undefined): PortalMapRecord | null {
  const m = MAPS.find((x) => x.portal_map_id === mapId);
  return m ? { ...m } : null;
}

export interface MapValidationResult { valid: boolean; errors: string[]; warnings: string[]; }

export function validatePortalMap(map: Partial<PortalMapRecord> | null | undefined): MapValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!map || typeof map !== 'object') return { valid: false, errors: ['missing_map'], warnings };
  if (!map.portal_map_id) errors.push('missing_portal_map_id');
  if (!map.portal_id) errors.push('missing_portal_id');
  if (!map.version) errors.push('missing_version');
  if (!Array.isArray(map.pages) || map.pages.length === 0) warnings.push('no_pages');
  if (!Array.isArray(map.journeys) || map.journeys.length === 0) warnings.push('no_journeys');
  if (map.status === 'approved_future') warnings.push('approved_future_blocked_in_43p3');
  return { valid: errors.length === 0, errors, warnings };
}
