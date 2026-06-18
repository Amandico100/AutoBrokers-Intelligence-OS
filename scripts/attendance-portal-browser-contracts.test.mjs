#!/usr/bin/env node
/**
 * 43P0 — Portal Browser Relay contracts (offline, sem browser, sem segredo).
 *
 *   node scripts/attendance-portal-browser-contracts.test.mjs
 *
 * Garante: PortalDefinition/Map/Skill validam; CredentialRef/SessionRef nunca
 * carregam segredo e sanitizam; challenge (CAPTCHA/2FA) sempre HITL, nunca bypass;
 * PortalActionCandidate nunca real; BrowserRelaySession nunca envia; promotion gate
 * sempre real_action_allowed=false; sem PII/segredo.
 */
import {
  validatePortalDefinition,
  validatePortalMap,
  validatePortalSkill,
  sanitizePortalDefinition,
  buildPortalActionCandidate,
  findForbiddenKeys,
} from '../lib/attendance/portal-browser-registry.ts';
import {
  buildCredentialRef,
  buildSessionRef,
  sanitizeCredentialRef,
  sanitizeSessionRef,
  evaluateSessionHealth,
  findSessionForbiddenKeys,
} from '../lib/attendance/portal-session-contracts.ts';
import {
  createBrowserRelaySession,
  applyRelayEvent,
  classifyChallenge,
  buildTraceSummary,
  evaluatePortalPromotionGate,
} from '../lib/attendance/browser-relay-contracts.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const portal = {
  portal_id: 'allianz_portal', label: 'Allianz Portal', owner_kind: 'insurer', insurer_key: 'allianz',
  base_url: 'https://portal.allianz.com.br', login_url: 'https://portal.allianz.com.br/login',
  supported_channels: ['browser'], auth_methods: ['password', 'mfa', 'captcha'], risk_level: 'high', status: 'draft',
};

console.log('== 43P0 — Portal Browser Relay contracts ==');

// [1] PortalDefinition.
console.log('\n[1] PortalDefinition');
{
  assert('definição válida', validatePortalDefinition(portal).valid === true);
  assert('http (não https) → erro', validatePortalDefinition({ ...portal, base_url: 'http://x.com' }).errors.includes('base_url_must_be_https'));
  assert('sem portal_id → erro', validatePortalDefinition({ ...portal, portal_id: '' }).errors.includes('missing_portal_id'));
  assert('captcha/mfa → warning HITL', validatePortalDefinition(portal).warnings.includes('challenge_capable_portal_requires_hitl'));
  assert('campo segredo → erro', validatePortalDefinition({ ...portal, password: 'x' }).errors.includes('forbidden_secret_field_present'));
}

// [2] PortalMap.
console.log('\n[2] PortalMap');
{
  const map = { portal_id: 'allianz_portal', version: 'v1', journeys: [{ journey_id: 'j1', label: 'assist', steps: ['login', 'abrir'], expected_outputs: ['protocolo'] }], known_pages: [], challenges: [{ kind: 'captcha', detect_hint: 'recaptcha', requires_human: true, bypass_allowed: false }], drift_signals: [], evidence_outputs: [] };
  assert('map válido', validatePortalMap(map).valid === true);
  const badChallenge = { ...map, challenges: [{ kind: 'captcha', detect_hint: 'x', requires_human: false, bypass_allowed: true }] };
  assert('challenge bypass → erro', validatePortalMap(badChallenge).errors.includes('challenge_rule_must_be_hitl'));
}

// [3] PortalSkill.
console.log('\n[3] PortalSkill');
{
  const skill = { skill_id: 's1', portal_id: 'allianz_portal', objective: 'abrir assistência', action_kind: 'open_assistance', required_inputs: ['policy', 'area'], output_schema: {}, allowed_actions: ['navigate', 'fill', 'submit_dry_run'], forbidden_actions: ['resolver captcha', 'resolver 2fa', 'inserir otp'], promotion_status: 'draft' };
  assert('skill válida', validatePortalSkill(skill).valid === true);
  assert('skill sem forbidden captcha → warning', validatePortalSkill({ ...skill, forbidden_actions: [] }).warnings.includes('skill_should_forbid_captcha_2fa_bypass'));
}

// [4] PortalActionCandidate — nunca real.
console.log('\n[4] PortalActionCandidate');
{
  const skill = { skill_id: 's1', portal_id: 'allianz_portal', objective: 'x', action_kind: 'open_assistance', required_inputs: ['policy', 'area'], output_schema: {}, allowed_actions: [], forbidden_actions: [], promotion_status: 'draft' };
  const cand = buildPortalActionCandidate({ action_goal: 'abrir assistência', portal, skill, available_inputs: { policy: '****99' } });
  assert('dry_run true', cand.dry_run === true);
  assert('real_send_allowed false', cand.real_send_allowed === false);
  assert('approval_required true', cand.approval_required === true);
  assert('missing_inputs area', cand.missing_inputs.includes('area'));
  assert('credential_ref_required (password)', cand.credential_ref_required === true);
  assert('session_ref_required (mfa/captcha)', cand.session_ref_required === true);
}

// [5] CredentialRef / SessionRef — sem segredo.
console.log('\n[5] Credential/Session refs');
{
  const cred = buildCredentialRef({ company_id: 'co', portal_id: 'allianz_portal', account_label: 'conta principal', vault_ref: 'vault://abc123def456' });
  assert('cred criada', typeof cred.credential_ref_id === 'string');
  const credSan = sanitizeCredentialRef(cred);
  assert('cred sanitizada mascara vault_ref', credSan.vault_ref_masked && !String(credSan.vault_ref_masked).includes('abc123def456'));
  assert('cred sanitizada sem campo vault_ref cru', !('vault_ref' in credSan));

  let threw = false;
  try { buildCredentialRef({ company_id: 'co', portal_id: 'p', account_label: 'x', vault_ref: 'v', password: 'segredo123' }); } catch { threw = true; }
  assert('cred com password cru → lança', threw);

  const sess = buildSessionRef({ company_id: 'co', portal_id: 'allianz_portal', storage_ref: 'store://xyz789abc', browser_provider: 'browserbase', status: 'healthy', expires_at: new Date(Date.now() + 3600_000).toISOString() });
  const sessSan = sanitizeSessionRef(sess);
  assert('session sanitizada mascara storage_ref', sessSan.storage_ref_masked && !String(sessSan.storage_ref_masked).includes('xyz789abc'));
  assert('session sanitizada sem storage_ref cru', !('storage_ref' in sessSan));

  let threw2 = false;
  try { buildSessionRef({ company_id: 'co', portal_id: 'p', storage_ref: 's', browser_provider: 'browserbase', cookies: [{ name: 'sid', value: 'x' }] }); } catch { threw2 = true; }
  assert('session com cookies cru → lança', threw2);
}

// [6] Session health.
console.log('\n[6] session health');
{
  const healthy = buildSessionRef({ company_id: 'co', portal_id: 'p', storage_ref: 's', browser_provider: 'browserbase', status: 'healthy', expires_at: new Date(Date.now() + 3600_000).toISOString() });
  assert('healthy usable', evaluateSessionHealth(healthy).usable === true);
  const expired = buildSessionRef({ company_id: 'co', portal_id: 'p', storage_ref: 's', browser_provider: 'browserbase', status: 'healthy', expires_at: new Date(Date.now() - 1000).toISOString() });
  assert('expirada → requires_human', evaluateSessionHealth(expired).requires_human === true && evaluateSessionHealth(expired).status === 'expired');
  const challenge = buildSessionRef({ company_id: 'co', portal_id: 'p', storage_ref: 's', browser_provider: 'browserbase', status: 'challenge_required' });
  assert('challenge → não usável', evaluateSessionHealth(challenge).usable === false);
}

// [7] Challenge policy — CAPTCHA/2FA sempre HITL, nunca bypass.
console.log('\n[7] challenge policy');
{
  for (const [signal, kind] of [['recaptcha v2', 'captcha'], ['informe o codigo OTP', 'otp'], ['app authenticator 2fa', 'mfa_app'], ['certificado e-CNPJ', 'certificate'], ['conta bloqueada', 'account_locked']]) {
    const ch = classifyChallenge(signal);
    assert(`challenge ${kind}`, ch.kind === kind, ch.kind);
    assert(`challenge ${kind} requires_human`, ch.requires_human === true);
    assert(`challenge ${kind} no bypass`, ch.bypass_allowed === false);
  }
  const otp = classifyChallenge('seu código é 482913 use agora');
  assert('OTP mascarado no hint', !otp.detected_hint.includes('482913'), otp.detected_hint);
}

// [8] BrowserRelaySession — nunca envia, nunca real.
console.log('\n[8] relay session');
{
  const s = createBrowserRelaySession({ portal_id: 'allianz_portal', browser_provider: 'browserbase', mode: 'real_future' });
  assert('real_future rebaixado p/ sandbox', s.mode === 'sandbox', s.mode);
  assert('external_action_sent false', s.external_action_sent === false);
  const s2 = applyRelayEvent(s, { type: 'session_loaded', note: 'ok' });
  const s3 = applyRelayEvent(s2, { type: 'challenge_detected', challenge_signal: 'recaptcha apareceu, código 123456' });
  assert('challenge → status challenge_required', s3.status === 'challenge_required');
  assert('challenge OTP/num mascarado nos eventos', !JSON.stringify(s3).includes('123456'));
  const done = applyRelayEvent(s3, { type: 'completed' });
  assert('completed → completed_dry_run', done.status === 'completed_dry_run');
  const after = applyRelayEvent(done, { type: 'navigated', note: 'x' });
  assert('evento após terminal ignorado', after.events.some((e) => e.type === 'event_ignored_terminal'));
  const cancelled = applyRelayEvent(createBrowserRelaySession({ portal_id: 'p' }), { type: 'cancel' });
  assert('cancel → cancelled', cancelled.status === 'cancelled');
  const trace = buildTraceSummary(s3);
  assert('trace has_pii false', trace.has_pii === false);
  assert('trace challenge_kind captcha', trace.challenge_kind === 'captcha');
}

// [9] Promotion gate — sempre real_action_allowed=false.
console.log('\n[9] promotion gate');
{
  const ideal = { portal_status: 'approved_future', skill_promotion: 'approved_future', has_credential_ref: true, has_session_ref: true, session_healthy: true, dry_run_passed: true, trace_available: true, replay_available: true, eval_passed: true, approval_exists: true, kill_switch_off: true, real_flag_enabled: true };
  assert('ctx ideal → real_action_allowed false', evaluatePortalPromotionGate(ideal).real_action_allowed === false);
  const noFlag = evaluatePortalPromotionGate({ ...ideal, real_flag_enabled: false });
  assert('flag off → blocker', noFlag.blockers.includes('real_flag_enabled'));
  const noApproval = evaluatePortalPromotionGate({ ...ideal, approval_exists: false });
  assert('sem approval → blocker', noApproval.blockers.includes('approval_exists'));
}

// [10] Sem segredo/PII em saídas.
console.log('\n[10] no leak');
{
  assert('findForbiddenKeys detecta password', findForbiddenKeys({ a: { password: 'x' } }).length > 0);
  assert('findSessionForbiddenKeys detecta cookie', findSessionForbiddenKeys({ s: { cookie: 'x' } }).length > 0);
  const def = sanitizePortalDefinition({ ...portal });
  assert('sanitizePortalDefinition limpa', findForbiddenKeys(def).length === 0);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
