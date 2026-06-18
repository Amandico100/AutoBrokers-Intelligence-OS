#!/usr/bin/env node
/**
 * 43P3.1 — Portal Skill Factory, Evidence Gates & Quality Score (offline).
 *
 *   node scripts/attendance-portal-skill-factory.test.mjs
 *
 * Garante: blueprints; evidence pack; missing evidence; quality score/tier;
 * candidatos do catálogo; risco por MFA/captcha; skill não vira sandbox_validated
 * sem trace/replay; sem PII/segredo; real_action_allowed=false.
 */
import {
  getPortalSkillBlueprints,
  getPortalSkillBlueprint,
  blueprintKeyForJourney,
  buildPortalSkillEvidencePack,
  validateSkillEvidencePack,
  explainMissingEvidence,
  evaluatePortalSkillQuality,
  generatePortalSkillCandidatesFromCatalog,
} from '../lib/attendance/portal-skill-factory.ts';
import { getPortalSkill } from '../lib/attendance/portal-skills.ts';
import { getPortalMapForPortal } from '../lib/attendance/portal-maps.ts';
import { PORTAL_GLOBAL_CATALOG_SEED } from '../lib/attendance/portal-global-catalog-seed.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const PORTAL_ID = 'allianz__allianznet_corretor_portal_do_corretor';
const allianzEntry = PORTAL_GLOBAL_CATALOG_SEED.find((e) => e.portal_id === PORTAL_ID);
const allianzSkill = getPortalSkill(PORTAL_ID, 'login_check');
const allianzMap = getPortalMapForPortal(PORTAL_ID, 'login');

console.log('== 43P3.1 — Portal Skill Factory ==');

// [1] blueprints.
console.log('\n[1] blueprints');
{
  const keys = getPortalSkillBlueprints().map((b) => b.blueprint_key);
  for (const k of ['login_check', 'policy_query', 'billing_query', 'status_query', 'document_download_dryrun', 'assistance_opening_dryrun', 'claim_notice_dryrun']) {
    assert(`blueprint ${k}`, keys.includes(k));
  }
  assert('blueprint login_check journey login', getPortalSkillBlueprint('login_check').journey === 'login');
  assert('blueprint forbidden inclui bypass', getPortalSkillBlueprint('login_check').forbidden_actions.includes('bypass_captcha_2fa'));
  assert('blueprint challenge_policy hitl', getPortalSkillBlueprint('policy_query').challenge_policy === 'hitl_required');
  assert('journey→blueprint billing_query', blueprintKeyForJourney('billing_query') === 'billing_query');
  assert('journey→blueprint login', blueprintKeyForJourney('login') === 'login_check');
  assert('journey desconhecido → null', blueprintKeyForJourney('xpto') === null);
}

// [2] evidence pack.
console.log('\n[2] evidence pack');
{
  assert('entry allianz no seed', Boolean(allianzEntry));
  const pack = buildPortalSkillEvidencePack({ portalEntry: allianzEntry, journey: 'login', map: allianzMap });
  assert('pack official_sources presente', pack.official_sources.length > 0);
  assert('pack confidence confirmed', pack.confidence === 'confirmed');
  assert('pack portal_map_id', pack.portal_map_id === 'allianznet_corretor_login_map_v1');
  assert('pack score >= 80 (com map, sem run)', pack.evidence_score >= 80, String(pack.evidence_score));
  assert('pack missing trace/replay/human', pack.missing_evidence.includes('trace') && pack.missing_evidence.includes('human_review'));
  assert('validate pack valid', validateSkillEvidencePack(pack).valid === true);
  assert('explain missing legível', explainMissingEvidence(pack).length === pack.missing_evidence.length);
}

// [3] missing evidence (sem official_sources).
console.log('\n[3] missing evidence');
{
  const weak = { portal_id: 'x__y', owner_key: 'x', status: 'needs_review', supported_journeys: ['login'], challenge_profile: { captcha: false, mfa: false, certificate: false, otp: false, requires_hitl: false }, metadata: { confidence: 'partial_evidence', audience: 'corretor' } };
  const pack = buildPortalSkillEvidencePack({ portalEntry: weak, journey: 'login', map: null });
  assert('sem official → missing', pack.missing_evidence.includes('official_sources'));
  assert('sem map → missing portal_map', pack.missing_evidence.includes('portal_map'));
  assert('validate inválido', validateSkillEvidencePack(pack).valid === false);
  assert('score baixo', pack.evidence_score < 60, String(pack.evidence_score));
}

// [4] quality score / tiers.
console.log('\n[4] quality');
{
  const pack = buildPortalSkillEvidencePack({ portalEntry: allianzEntry, journey: 'login', map: allianzMap });
  // sem run → não pode sandbox_validated
  const noRun = evaluatePortalSkillQuality(allianzSkill, pack, null);
  assert('sem run → não promove', noRun.safe_to_promote_to_sandbox_validated === false);
  assert('sem run → tier draft_ready_for_dryrun', noRun.tier === 'draft_ready_for_dryrun', noRun.tier);
  assert('sem run blocker no_trace', noRun.blockers.includes('no_trace'));
  // com run completo → promovível
  const fullRun = { passed: true, trace_available: true, replay_available: true, status: 'sandbox_passed', forbidden_actions_detected: [], challenge_detected: false };
  const withRun = evaluatePortalSkillQuality(allianzSkill, pack, fullRun);
  assert('com run → score alto', withRun.score >= 80, String(withRun.score));
  assert('com run → promovível', withRun.safe_to_promote_to_sandbox_validated === true);
  assert('com run → tier candidate', ['sandbox_validated_candidate', 'production_candidate_future'].includes(withRun.tier), withRun.tier);
  assert('quality real_action_allowed false', withRun.real_action_allowed === false);
  // run com challenge → blocker
  const chRun = { passed: false, trace_available: true, replay_available: true, challenge_detected: true };
  assert('challenge → não promove', evaluatePortalSkillQuality(allianzSkill, pack, chRun).safe_to_promote_to_sandbox_validated === false);
}

// [5] candidatos do catálogo.
console.log('\n[5] candidatos');
{
  const cands = generatePortalSkillCandidatesFromCatalog(PORTAL_GLOBAL_CATALOG_SEED, { audience: 'corretor', status: 'sandbox_ready', confidence: 'confirmed', exclude_mfa_captcha: true });
  assert('candidatos gerados', cands.length > 0);
  const allianzLogin = cands.find((c) => c.portal_id === PORTAL_ID && c.journey === 'login');
  assert('candidato Allianz login aparece', Boolean(allianzLogin), 'não achou');
  assert('candidato Allianz blueprint login_check', allianzLogin?.blueprint_key === 'login_check');
  assert('candidato Allianz risco low', allianzLogin?.risk_level === 'low');
  assert('candidatos ordenados por risco', cands[0].risk_level === 'low');

  // risco maior com MFA/captcha
  const all = generatePortalSkillCandidatesFromCatalog(PORTAL_GLOBAL_CATALOG_SEED, {});
  const risky = all.find((c) => c.risk_level === 'medium' || c.risk_level === 'high');
  assert('há candidatos com risco elevado (MFA/captcha/cert)', Boolean(risky));
}

// [6] sem segredo/PII.
console.log('\n[6] segurança');
{
  const cands = generatePortalSkillCandidatesFromCatalog(PORTAL_GLOBAL_CATALOG_SEED, {});
  const raw = JSON.stringify(cands).toLowerCase();
  for (const bad of ['"password"', '"senha"', '"cookie"', '"storage_state"', '"client_token"', '"vault_ref"']) {
    assert(`candidatos sem ${bad}`, !raw.includes(bad));
  }
  const pack = buildPortalSkillEvidencePack({ portalEntry: allianzEntry, journey: 'login', map: allianzMap });
  assert('pack sem chave de segredo', !JSON.stringify(pack).toLowerCase().includes('"password"'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
