#!/usr/bin/env node
/**
 * 43P1 — Portal admin registry/credential/session (offline, sem DB/browser/segredo).
 *
 *   node scripts/attendance-portal-admin-registry.test.mjs
 *
 * Garante: portal valida (https/HITL); accounts; credential/session refs opacas
 * (rejeitam segredo cru); health-check mock; resolve por owner/journey; sem PII;
 * intake audit sem fontes não quebra.
 */
import {
  buildPortalDefinitionRecord,
  validatePortalDefinitionInput,
  buildPortalAccountRecord,
  buildChallengeProfile,
  buildCredentialRefRecord,
  buildSessionRefRecord,
  deriveAccountStatus,
  mockHealthCheck,
  sanitizePortalAccountRecord,
  resolvePortalForJourney,
  scanPortalIntakeSources,
  findRequestSecrets,
} from '../lib/attendance/portal-admin-sanitizers.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== 43P1 — Portal Admin Registry ==');

// [1] Portal definition.
console.log('\n[1] portal definition');
{
  const v = validatePortalDefinitionInput({ label: 'Allianz', owner_key: 'allianz', base_url: 'https://portal.allianz.com.br' });
  assert('definição válida', v.valid === true);
  assert('http → erro https', validatePortalDefinitionInput({ label: 'x', owner_key: 'y', base_url: 'http://x.com' }).errors.includes('base_url_must_be_https'));
  assert('segredo no input → erro', validatePortalDefinitionInput({ label: 'x', owner_key: 'y', base_url: 'https://x.com', password: 'p' }).errors.includes('forbidden_secret_field_present'));
  const rec = buildPortalDefinitionRecord({ label: 'Allianz', owner_key: 'allianz', base_url: 'https://portal.allianz.com.br', auth_methods: ['password', 'mfa', 'captcha'], supported_journeys: ['residential_assistance'] });
  assert('challenge_profile requires_hitl', rec.challenge_profile.requires_hitl === true);
  assert('browser_strategy normalizado (primary browserbase)', rec.browser_strategy.primary === 'browserbase');
  assert('status default draft', rec.status === 'draft');
}

// [2] challenge profile.
console.log('\n[2] challenge profile');
{
  assert('sem auth → sem hitl', buildChallengeProfile([]).requires_hitl === false);
  assert('captcha → hitl', buildChallengeProfile(['captcha']).requires_hitl === true);
  assert('certificate → hitl', buildChallengeProfile(['certificate']).certificate === true);
}

// [3] account + status derivation.
console.log('\n[3] account');
{
  const acc = buildPortalAccountRecord({ company_id: 'co', portal_id: 'allianz_portal', label: 'conta', auth_methods: ['password', 'mfa'] });
  assert('account status not_configured', acc.status === 'not_configured');
  assert('account challenge hitl (mfa)', acc.challenge_profile.requires_hitl === true);
  acc.credential_ref = buildCredentialRefRecord({ company_id: 'co', portal_id: 'allianz_portal', vault_ref: 'vault://abc123def456' });
  assert('só credencial → session_pending', deriveAccountStatus(acc) === 'session_pending');
  acc.session_ref = buildSessionRefRecord({ company_id: 'co', portal_id: 'allianz_portal', storage_ref: 'store://xyz789abc', status: 'healthy' });
  assert('cred+session healthy → healthy', deriveAccountStatus(acc) === 'healthy');
}

// [4] credential/session refs — sem segredo cru.
console.log('\n[4] refs opacas');
{
  const cred = buildCredentialRefRecord({ company_id: 'co', portal_id: 'p', vault_ref: 'vault://abc123def456' });
  assert('vault_ref mascarado', cred.vault_ref_masked.includes('…') && !cred.vault_ref_masked.includes('abc123def456'));
  let threw = false;
  try { buildCredentialRefRecord({ company_id: 'co', portal_id: 'p', vault_ref: 'v', password: 'segredo' }); } catch { threw = true; }
  assert('credential com password → lança', threw);

  const sess = buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 'store://xyz789abc', provider: 'browserbase' });
  assert('storage_ref mascarado', sess.storage_ref_masked.includes('…') && !sess.storage_ref_masked.includes('xyz789abc'));
  let threw2 = false;
  try { buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 's', cookies: 'sid=abc' }); } catch { threw2 = true; }
  assert('session com cookies → lança', threw2);
  let threw3 = false;
  try { buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 's', storage_state: '{...}' }); } catch { threw3 = true; }
  assert('session com storage_state → lança', threw3);
}

// [5] health-check mock.
console.log('\n[5] health-check mock');
{
  const base = buildPortalAccountRecord({ company_id: 'co', portal_id: 'p', label: 'x' });
  assert('sem credencial → credential_pending', mockHealthCheck(base).status === 'credential_pending');
  base.credential_ref = buildCredentialRefRecord({ company_id: 'co', portal_id: 'p', vault_ref: 'vault://aaa111bbb222' });
  assert('sem sessão → session_pending', mockHealthCheck(base).status === 'session_pending');
  base.session_ref = buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 'store://ccc333ddd444', status: 'healthy', expires_at: new Date(Date.now() + 3600_000).toISOString() });
  assert('healthy → usable', mockHealthCheck(base).usable === true && mockHealthCheck(base).status === 'healthy');
  base.session_ref.expires_at = new Date(Date.now() - 1000).toISOString();
  assert('expirada → expired + requires_human', mockHealthCheck(base).status === 'expired' && mockHealthCheck(base).requires_human === true);
  base.session_ref = buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 'store://e', status: 'challenge_required' });
  assert('challenge → challenge_required', mockHealthCheck(base).status === 'challenge_required');
}

// [6] resolve por owner/journey.
console.log('\n[6] resolve');
{
  const def = buildPortalDefinitionRecord({ portal_id: 'allianz_portal', label: 'Allianz', owner_key: 'allianz', base_url: 'https://portal.allianz.com.br', auth_methods: ['password', 'mfa'], supported_journeys: ['residential_assistance'] });
  const acc = buildPortalAccountRecord({ company_id: 'co', portal_id: 'allianz_portal', label: 'conta', challenge_profile: def.challenge_profile });
  acc.credential_ref = buildCredentialRefRecord({ company_id: 'co', portal_id: 'allianz_portal', vault_ref: 'vault://aaa111bbb222' });
  acc.session_ref = buildSessionRefRecord({ company_id: 'co', portal_id: 'allianz_portal', storage_ref: 'store://ccc333', status: 'healthy', expires_at: new Date(Date.now() + 3600_000).toISOString() });
  acc.status = deriveAccountStatus(acc);

  const r = resolvePortalForJourney([def], [acc], { company_id: 'co', owner_key: 'allianz', journey: 'residential_assistance' });
  assert('resolve portal_available', r.portal_available === true && r.portal_id === 'allianz_portal');
  assert('resolve real_action_allowed false', r.real_action_allowed === false);
  assert('resolve next_step ready_for_dry_run', r.next_step === 'ready_for_dry_run_43p3', r.next_step);

  const noAcct = resolvePortalForJourney([def], [], { company_id: 'co', owner_key: 'allianz' });
  assert('sem conta → create_portal_account', noAcct.next_step === 'create_portal_account');
  const noPortal = resolvePortalForJourney([], [], { company_id: 'co', owner_key: 'porto' });
  assert('sem portal → no_portal_definition', noPortal.portal_available === false && noPortal.next_step === 'no_portal_definition');
}

// [7] sanitização + sem PII.
console.log('\n[7] sanitização');
{
  const acc = buildPortalAccountRecord({ company_id: 'co', portal_id: 'p', label: 'x' });
  acc.credential_ref = buildCredentialRefRecord({ company_id: 'co', portal_id: 'p', vault_ref: 'vault://supersecret123456' });
  acc.session_ref = buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 'store://cookievalue987654' });
  const san = sanitizePortalAccountRecord(acc);
  const raw = JSON.stringify(san);
  assert('sanitize sem vault cru', !raw.includes('supersecret123456'));
  assert('sanitize sem storage cru', !raw.includes('cookievalue987654'));
  assert('findRequestSecrets detecta', findRequestSecrets({ a: { token: 'x' } }).length > 0);
}

// [8] intake audit sem fontes não quebra.
console.log('\n[8] intake audit');
{
  const empty = scanPortalIntakeSources([]);
  assert('sem fontes → not_available', empty.available === false && empty.reason === 'intake_sources_not_available');
  const some = scanPortalIntakeSources([{ source: 'allianz.txt', text: 'portal https://portal.allianz.com.br usa captcha e mfa' }]);
  assert('com fonte → candidato', some.available === true && some.candidates.length === 1);
  assert('candidato detecta url + challenge', some.candidates[0].base_url_found?.includes('allianz') && some.candidates[0].challenge_signals.includes('captcha'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
