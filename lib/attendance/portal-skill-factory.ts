// 43P3.1 — Portal Skill Factory, Evidence Gates & Repeatable Templates. PURO,
// self-contained. Garante que toda Portal Skill nasça de EVIDÊNCIA (catálogo
// oficial + map + trace/replay + revisão), nunca de prompt solto. NÃO acessa
// portal real; nenhuma skill é promovida a real aqui.

import type { PortalDefinitionRecord } from '@/lib/attendance/portal-admin-sanitizers';
import type { PortalMapRecord } from '@/lib/attendance/portal-maps';
import type { PortalSkillRecord } from '@/lib/attendance/portal-skills';

// --- Blueprints (genéricos, não específicos de seguradora) ------------------
export interface PortalSkillBlueprint {
  blueprint_key: string;
  journey: string;
  objective_template: string;
  required_evidence: string[];
  required_inputs: string[];
  allowed_actions: string[];
  forbidden_actions: string[];
  expected_outputs: string[];
  recommended_map_pages: string[];
  challenge_policy: 'hitl_required';
  min_quality_score: number;
  promotion_rules: string[];
}

const COMMON_FORBIDDEN = [
  'insert_credential_real', 'submit_real', 'bypass_captcha_2fa', 'access_real_url',
  'download_upload_real', 'store_raw_storage_state_cookie', 'expose_credential',
];
const COMMON_EVIDENCE = ['global_catalog_entry', 'official_sources', 'confidence', 'journey_type', 'audience'];
const COMMON_PROMOTION = ['dry_run_passed', 'trace_replay_present', 'no_forbidden_actions', 'no_pii_secrets', 'human_review_for_promotion'];

function blueprint(over: Partial<PortalSkillBlueprint> & { blueprint_key: string; journey: string; objective_template: string }): PortalSkillBlueprint {
  return {
    required_evidence: [...COMMON_EVIDENCE, 'portal_map_or_draft'],
    required_inputs: ['portal_id', 'portal_account_id', 'credential_ref', 'session_ref_or_pending', 'provider'],
    allowed_actions: ['observe_mock', 'extract_mock', 'detect_challenge_mock', 'build_trace_replay'],
    forbidden_actions: COMMON_FORBIDDEN,
    expected_outputs: [],
    recommended_map_pages: [],
    challenge_policy: 'hitl_required',
    min_quality_score: 80,
    promotion_rules: COMMON_PROMOTION,
    ...over,
  };
}

const BLUEPRINTS: PortalSkillBlueprint[] = [
  blueprint({ blueprint_key: 'login_check', journey: 'login', objective_template: 'Validar em dry-run que o portal {owner_key} possui jornada de login mapeável, sem login real.', expected_outputs: ['login_form_detected', 'auth_required', 'post_login_home_detected'], recommended_map_pages: ['landing_or_login', 'login_form', 'post_login_home_mock'] }),
  blueprint({ blueprint_key: 'policy_query', journey: 'policy_query', objective_template: 'Validar em dry-run a consulta de apólice/documentos em {owner_key}, sem acessar dados reais.', expected_outputs: ['policy_search_detected', 'policy_result_detected'], recommended_map_pages: ['post_login_home_mock', 'policy_search_mock', 'policy_detail_mock'] }),
  blueprint({ blueprint_key: 'billing_query', journey: 'billing_query', objective_template: 'Validar em dry-run a consulta de cobrança/2ª via em {owner_key}, sem acessar dados reais.', expected_outputs: ['billing_section_detected', 'invoice_list_detected'], recommended_map_pages: ['post_login_home_mock', 'billing_mock'] }),
  blueprint({ blueprint_key: 'status_query', journey: 'status_query', objective_template: 'Validar em dry-run a consulta de status (sinistro/assistência) em {owner_key}, sem acessar dados reais.', expected_outputs: ['status_section_detected', 'status_result_detected'], recommended_map_pages: ['post_login_home_mock', 'status_mock'] }),
  blueprint({ blueprint_key: 'document_download_dryrun', journey: 'document_query', objective_template: 'Validar em dry-run a localização de documentos/apólice em {owner_key}, SEM baixar arquivo real.', expected_outputs: ['document_section_detected', 'document_link_detected'], recommended_map_pages: ['post_login_home_mock', 'documents_mock'], forbidden_actions: [...COMMON_FORBIDDEN, 'download_file_real'] }),
  blueprint({ blueprint_key: 'assistance_opening_dryrun', journey: 'assistance', objective_template: 'Validar em dry-run o fluxo de abertura de assistência em {owner_key}, SEM abrir chamado real.', expected_outputs: ['assistance_form_detected', 'assistance_fields_detected'], recommended_map_pages: ['post_login_home_mock', 'assistance_form_mock'], forbidden_actions: [...COMMON_FORBIDDEN, 'open_assistance_real'] }),
  blueprint({ blueprint_key: 'claim_notice_dryrun', journey: 'claim', objective_template: 'Validar em dry-run o fluxo de aviso de sinistro em {owner_key}, SEM registrar sinistro real.', expected_outputs: ['claim_form_detected', 'claim_fields_detected'], recommended_map_pages: ['post_login_home_mock', 'claim_form_mock'], forbidden_actions: [...COMMON_FORBIDDEN, 'submit_claim_real'] }),
];

export function getPortalSkillBlueprints(): PortalSkillBlueprint[] {
  return BLUEPRINTS.map((b) => ({ ...b }));
}
export function getPortalSkillBlueprint(key: string | null | undefined): PortalSkillBlueprint | null {
  const b = BLUEPRINTS.find((x) => x.blueprint_key === key);
  return b ? { ...b } : null;
}

const JOURNEY_TO_BLUEPRINT: Record<string, string> = {
  login: 'login_check', policy_query: 'policy_query', billing_query: 'billing_query', status_query: 'status_query',
  document_query: 'document_download_dryrun', assistance: 'assistance_opening_dryrun', claim: 'claim_notice_dryrun',
};
export function blueprintKeyForJourney(journey: string | null | undefined): string | null {
  return (journey && JOURNEY_TO_BLUEPRINT[journey]) || null;
}

// --- Evidence Pack ----------------------------------------------------------
export interface PortalSkillEvidencePack {
  portal_id: string;
  owner_key: string;
  source_documents: string[];
  official_sources: string[];
  confidence: string | null;
  audience: string | null;
  journey: string | null;
  portal_status: string | null;
  portal_map_id: string | null;
  trace_id: string | null;
  replay_id: string | null;
  human_review_status: 'none' | 'pending' | 'approved';
  missing_evidence: string[];
  evidence_score: number; // 0..100
}

function splitSources(s: unknown): string[] {
  if (!s) return [];
  return String(s).split(/[;\n]/).map((x) => x.trim()).filter(Boolean);
}

export interface BuildEvidenceInput {
  portalEntry: PortalDefinitionRecord;
  journey?: string | null;
  map?: PortalMapRecord | null;
  trace_id?: string | null;
  replay_id?: string | null;
  human_review_status?: 'none' | 'pending' | 'approved';
}

export function buildPortalSkillEvidencePack(input: BuildEvidenceInput): PortalSkillEvidencePack {
  const e = input.portalEntry;
  const md = (e.metadata ?? {}) as Record<string, unknown>;
  const official = splitSources(md.official_sources);
  const journey = input.journey ?? (e.supported_journeys?.[0] ?? null);
  const missing: string[] = [];
  if (official.length === 0) missing.push('official_sources');
  if (!md.confidence) missing.push('confidence');
  if (!md.audience) missing.push('audience');
  if (!journey) missing.push('journey');
  if (!e.status) missing.push('portal_status');
  if (!input.map?.portal_map_id) missing.push('portal_map');
  if (!input.trace_id) missing.push('trace');
  if (!input.replay_id) missing.push('replay');
  if ((input.human_review_status ?? 'none') !== 'approved') missing.push('human_review');

  let score = 0;
  if (official.length > 0) score += 25;
  const conf = String(md.confidence ?? '');
  if (conf === 'confirmed') score += 20; else if (conf === 'strong_evidence') score += 12; else if (conf === 'partial_evidence') score += 6;
  if (md.audience) score += 10;
  if (journey) score += 10;
  if (e.status) score += 5;
  if (input.map?.portal_map_id) score += 15;
  if (input.trace_id) score += 8;
  if (input.replay_id) score += 7;

  return {
    portal_id: e.portal_id,
    owner_key: e.owner_key,
    source_documents: splitSources(md.source_document),
    official_sources: official,
    confidence: (md.confidence as string) ?? null,
    audience: (md.audience as string) ?? null,
    journey,
    portal_status: e.status ?? null,
    portal_map_id: input.map?.portal_map_id ?? null,
    trace_id: input.trace_id ?? null,
    replay_id: input.replay_id ?? null,
    human_review_status: input.human_review_status ?? 'none',
    missing_evidence: missing,
    evidence_score: Math.min(100, score),
  };
}

export function validateSkillEvidencePack(pack: PortalSkillEvidencePack): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!pack.portal_id) errors.push('missing_portal_id');
  if (pack.official_sources.length === 0) errors.push('missing_official_sources');
  if (!pack.confidence) errors.push('missing_confidence');
  if (!pack.journey) errors.push('missing_journey');
  return { valid: errors.length === 0, errors };
}

export function explainMissingEvidence(pack: PortalSkillEvidencePack): string[] {
  const human: Record<string, string> = {
    official_sources: 'Faltam fontes oficiais (official_sources) do portal.',
    confidence: 'Falta o nível de confiança (confidence) da pesquisa.',
    audience: 'Falta a audiência (corretor/segurado/...).',
    journey: 'Falta a jornada (journey).',
    portal_status: 'Falta o status do portal.',
    portal_map: 'Falta um Portal Map (ou draft) para esta jornada.',
    trace: 'Falta um trace de dry-run (rode a skill no sandbox).',
    replay: 'Falta um replay de dry-run.',
    human_review: 'Falta revisão humana para promoção.',
  };
  return pack.missing_evidence.map((m) => human[m] ?? m);
}

// --- Skill Quality Score ----------------------------------------------------
export type SkillQualityTier = 'draft_needs_evidence' | 'draft_ready_for_dryrun' | 'sandbox_validated_candidate' | 'production_candidate_future';

export interface SkillQualityResult {
  score: number; // 0..100
  tier: SkillQualityTier;
  reasons: string[];
  blockers: string[];
  safe_to_promote_to_sandbox_validated: boolean;
  real_action_allowed: false;
}

export interface LastRunLite {
  passed?: boolean;
  trace_available?: boolean;
  replay_available?: boolean;
  status?: string;
  forbidden_actions_detected?: string[];
  challenge_detected?: boolean;
}

export function evaluatePortalSkillQuality(
  skill: PortalSkillRecord | null,
  evidencePack: PortalSkillEvidencePack,
  lastRun?: LastRunLite | null,
): SkillQualityResult {
  const reasons: string[] = [];
  const blockers: string[] = [];
  let score = 0;

  // Evidência (até 50)
  if (evidencePack.official_sources.length > 0) { score += 18; reasons.push('official_sources_present'); } else blockers.push('no_official_sources');
  if (evidencePack.confidence === 'confirmed') { score += 12; reasons.push('confidence_confirmed'); }
  else if (evidencePack.confidence === 'strong_evidence') { score += 7; reasons.push('confidence_strong'); }
  else if (evidencePack.confidence === 'partial_evidence') { score += 3; reasons.push('confidence_partial'); }
  if (evidencePack.audience) { score += 5; }
  if (evidencePack.journey) { score += 5; }
  if (evidencePack.portal_map_id) { score += 10; reasons.push('map_versioned'); } else blockers.push('no_portal_map');

  // Skill/forbidden (até 15)
  if (skill) {
    const forb = (skill.forbidden_actions || []).join(' ').toLowerCase();
    if (forb.includes('captcha') && forb.includes('real')) { score += 10; reasons.push('forbidden_actions_present'); } else blockers.push('weak_forbidden_actions');
    if ((skill.guardrails || []).length > 0) score += 5;
  } else blockers.push('no_skill');

  // Execução (até 30)
  if (lastRun?.passed) { score += 12; reasons.push('dry_run_passed'); } else blockers.push('no_dry_run_passed');
  if (lastRun?.trace_available) { score += 9; reasons.push('trace_available'); } else blockers.push('no_trace');
  if (lastRun?.replay_available) { score += 9; reasons.push('replay_available'); } else blockers.push('no_replay');
  if (lastRun?.challenge_detected) blockers.push('unresolved_challenge');
  if ((lastRun?.forbidden_actions_detected?.length ?? 0) > 0) blockers.push('forbidden_action_detected');

  // Revisão humana (até 5)
  if (evidencePack.human_review_status === 'approved') { score += 5; reasons.push('human_reviewed'); }

  score = Math.min(100, score);

  // Tier — não pode passar de draft sem trace/replay (dry-run real do sandbox).
  const hasRunEvidence = Boolean(lastRun?.trace_available && lastRun?.replay_available && lastRun?.passed);
  let tier: SkillQualityTier;
  if (score < 60 || !evidencePack.portal_map_id) tier = 'draft_needs_evidence';
  else if (!hasRunEvidence || score < 80) tier = 'draft_ready_for_dryrun';
  else if (score < 95) tier = 'sandbox_validated_candidate';
  else tier = 'production_candidate_future';

  const safe = tier === 'sandbox_validated_candidate' || tier === 'production_candidate_future';
  return { score, tier, reasons, blockers, safe_to_promote_to_sandbox_validated: safe, real_action_allowed: false };
}

// --- Candidate Generator ----------------------------------------------------
export interface SkillCandidate {
  owner_key: string;
  portal_id: string;
  journey: string;
  blueprint_key: string | null;
  reason: string;
  risk_level: 'low' | 'medium' | 'high';
  evidence_score: number;
  suggested_next_step: string;
}

export interface CandidateFilters {
  audience?: string | null;
  status?: string | null;
  confidence?: string | null;
  exclude_mfa_captcha?: boolean;
  journeys?: string[];
}

const DEFAULT_USEFUL_JOURNEYS = ['login', 'policy_query', 'billing_query', 'status_query', 'support', 'claim', 'assistance', 'document_query'];

function riskForEntry(e: PortalDefinitionRecord): 'low' | 'medium' | 'high' {
  const cp = e.challenge_profile;
  if (cp.certificate) return 'high';
  if (cp.mfa || cp.captcha || cp.otp) return 'medium';
  return 'low';
}

export function generatePortalSkillCandidatesFromCatalog(
  catalog: PortalDefinitionRecord[],
  filters: CandidateFilters = {},
): SkillCandidate[] {
  const journeys = filters.journeys && filters.journeys.length > 0 ? filters.journeys : DEFAULT_USEFUL_JOURNEYS;
  const out: SkillCandidate[] = [];
  for (const e of catalog) {
    const md = (e.metadata ?? {}) as Record<string, unknown>;
    if (filters.audience && String(md.audience ?? '') !== filters.audience) continue;
    if (filters.status && e.status !== filters.status) continue;
    if (filters.confidence && String(md.confidence ?? '') !== filters.confidence) continue;
    if (filters.exclude_mfa_captcha && (e.challenge_profile.mfa || e.challenge_profile.captcha)) continue;
    for (const journey of e.supported_journeys || []) {
      if (!journeys.includes(journey)) continue;
      const bp = blueprintKeyForJourney(journey);
      if (!bp) continue;
      const pack = buildPortalSkillEvidencePack({ portalEntry: e, journey });
      const risk = riskForEntry(e);
      out.push({
        owner_key: e.owner_key,
        portal_id: e.portal_id,
        journey,
        blueprint_key: bp,
        reason: `Catálogo: ${md.confidence ?? '?'} / audiência ${md.audience ?? '?'} / status ${e.status}`,
        risk_level: risk,
        evidence_score: pack.evidence_score,
        suggested_next_step: risk === 'low' ? 'instantiate_skill_and_dry_run' : 'review_challenge_before_dry_run',
      });
    }
  }
  // Ordena: menor risco + maior evidência primeiro.
  const riskRank = { low: 0, medium: 1, high: 2 };
  return out.sort((a, b) => riskRank[a.risk_level] - riskRank[b.risk_level] || b.evidence_score - a.evidence_score);
}
