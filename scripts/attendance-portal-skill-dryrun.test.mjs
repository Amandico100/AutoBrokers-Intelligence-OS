#!/usr/bin/env node
/**
 * 43P3 — First Portal Skill dry-run + Portal Map v1 (offline; nenhum portal/browser real).
 *
 *   node scripts/attendance-portal-skill-dryrun.test.mjs
 *
 * Garante: map v1; skill v1; gates (account/credential/session); dry-run passa;
 * outputs esperados; challenge → waiting_human; forbidden bloqueado; eval/promote;
 * trace/replay sem PII; real_action_allowed=false; providers stagehand/skyvern_lab mock.
 */
import { getPortalMaps, getPortalMapForPortal, validatePortalMap } from '../lib/attendance/portal-maps.ts';
import { getPortalSkill, getPortalSkills, validatePortalSkill } from '../lib/attendance/portal-skills.ts';
import {
  runPortalSkillDryRun,
  applyPortalSkillStep,
  buildPortalSkillEval,
  sanitizePortalSkillRun,
  findSkillRunSecrets,
} from '../lib/attendance/portal-skill-runner.ts';
import { getBrowserRelayAdapter } from '../lib/attendance/browser-relay-adapters.ts';
import { startBrowserRelaySandbox, applyBrowserRelaySandboxStep, buildRelayTrace, buildRelayReplay } from '../lib/attendance/browser-relay-runtime.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const PORTAL = 'allianz__allianznet_corretor_portal_do_corretor';
const skill = getPortalSkill(PORTAL, 'login_check');
const map = getPortalMapForPortal(PORTAL, 'login');
function deps(provider = 'browserbase') { return { adapter: getBrowserRelayAdapter(provider), startRelay: startBrowserRelaySandbox, applyStep: applyBrowserRelaySandboxStep }; }
function runWith(over = {}) {
  return runPortalSkillDryRun({
    skill, map, portal_id: PORTAL, portal_account_id: 'pacct-1',
    account_present: true, credential_present: true, session_status: 'healthy', provider: 'browserbase', ...over,
  }, deps(over.provider || 'browserbase'));
}

console.log('== 43P3 — Portal Skill Dry-run ==');

// [1] map/skill v1.
console.log('\n[1] map/skill');
{
  assert('map v1 existe', Boolean(map) && map.portal_map_id === 'allianznet_corretor_login_map_v1');
  assert('map válido', validatePortalMap(map).valid === true);
  assert('skill v1 existe', Boolean(skill) && skill.portal_skill_id === 'allianznet_corretor_login_check_v1');
  assert('skill válida', validatePortalSkill(skill).valid === true);
  assert('skill promotion draft', skill.promotion_status === 'draft');
  assert('getPortalSkills lista', getPortalSkills().length >= 1);
  assert('getPortalMaps lista', getPortalMaps().length >= 1);
}

// [2] gates.
console.log('\n[2] gates');
{
  const noMap = runPortalSkillDryRun({ skill, map: null, portal_id: PORTAL, account_present: true, credential_present: true, session_status: 'healthy', provider: 'mock' }, deps('mock'));
  assert('sem map → sandbox_failed/no_map', noMap.status === 'sandbox_failed' && noMap.next_step === 'no_map');
  const noAcct = runWith({ account_present: false });
  assert('sem conta → planned/create_portal_account', noAcct.status === 'planned' && noAcct.next_step === 'create_portal_account');
  const noCred = runWith({ credential_present: false });
  assert('sem credencial → credential_required', noCred.next_step === 'credential_required');
  const expired = runWith({ session_status: 'expired' });
  assert('sessão expirada → waiting_human', expired.status === 'waiting_human' && expired.challenge_detected === true);
}

// [3] dry-run passa.
console.log('\n[3] dry-run passa');
{
  const run = runWith();
  assert('status sandbox_passed', run.status === 'sandbox_passed', run.status);
  assert('output login_form_detected', run.outputs.includes('login_form_detected'));
  assert('output auth_required', run.outputs.includes('auth_required'));
  assert('output post_login_home_detected', run.outputs.includes('post_login_home_detected'));
  assert('relay_session presente', Boolean(run.relay_session));
  assert('real_action_allowed false', run.real_action_allowed === false);
}

// [4] eval / promote.
console.log('\n[4] eval');
{
  const run = runWith();
  const ev = buildPortalSkillEval(run, skill);
  assert('eval passed', ev.passed === true);
  assert('eval score 1', ev.score === 1, String(ev.score));
  assert('eval required outputs found', ev.required_outputs_found.length === skill.expected_outputs.length);
  assert('eval forbidden vazio', ev.forbidden_actions_detected.length === 0);
  assert('eval trace+replay', ev.trace_available && ev.replay_available);
  assert('eval safe_to_promote', ev.safe_to_promote_to_sandbox_validated === true);
  assert('eval real_action_allowed false', ev.real_action_allowed === false);
}

// [5] challenge inesperado → waiting_human.
console.log('\n[5] challenge');
{
  const run = runWith({ inject_challenge: 'apareceu recaptcha na tela' });
  assert('challenge → waiting_human', run.status === 'waiting_human' && run.challenge_detected === true);
  assert('challenge output', run.outputs.includes('challenge_required'));
  const ev = buildPortalSkillEval(run, skill);
  assert('challenge não passa', ev.passed === false);
  assert('challenge não promove', ev.safe_to_promote_to_sandbox_validated === false);
  // OTP mascarado
  const otpRun = runWith({ inject_challenge: 'informe o codigo 123456' });
  assert('OTP mascarado no run', !JSON.stringify(otpRun).includes('123456'));
}

// [6] forbidden bloqueado.
console.log('\n[6] forbidden');
{
  let run = runWith();
  const blocked = applyPortalSkillStep(run, { action: 'submit_login_real' }, skill, deps());
  assert('forbidden bloqueado (next_step)', blocked.next_step === 'forbidden_action_blocked');
  assert('forbidden não vira detected/performed', blocked.forbidden_actions_detected.length === 0);
  assert('forbidden registra evento no relay', blocked.relay_session.events.some((e) => e.type === 'forbidden_action_blocked'));
}

// [7] trace/replay sem PII.
console.log('\n[7] trace/replay');
{
  const run = runWith({ inject_challenge: 'codigo 999888' });
  const trace = buildRelayTrace(run.relay_session);
  const replay = buildRelayReplay(run.relay_session);
  assert('trace has_pii false', trace.has_pii === false);
  assert('replay has_pii false', replay.has_pii === false);
  assert('trace sem OTP cru', !JSON.stringify(trace).includes('999888'));
  assert('sanitize run sem segredo', findSkillRunSecrets(sanitizePortalSkillRun(run)).length === 0);
}

// [8] providers stagehand / skyvern_lab mock.
console.log('\n[8] providers');
{
  const sh = runWith({ provider: 'stagehand' });
  assert('stagehand sandbox_passed', sh.status === 'sandbox_passed' && sh.provider === 'stagehand');
  const sky = runWith({ provider: 'skyvern_lab' });
  assert('skyvern_lab sandbox_passed', sky.status === 'sandbox_passed' && sky.provider === 'skyvern_lab');
  assert('adapters não abrem real', getBrowserRelayAdapter('stagehand').canOpenRealBrowser === false && getBrowserRelayAdapter('skyvern_lab').canAccessRealUrl === false);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
