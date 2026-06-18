#!/usr/bin/env node
/**
 * 43P1.1 — Portal Browser canonical store (offline, sem DB/browser/segredo).
 *
 *   node scripts/attendance-portal-canonical-store.test.mjs
 *
 * Garante: connector slug próprio portal_browser (nunca whatsapp_zapi); catálogo
 * global vazio não quebra; resolve canônico (global/tenant_draft/tenant account/
 * none); browser_strategy normalizado (string|objeto); challenge override; sem
 * segredo cru; real_action_allowed=false e connector_template portal_browser.
 */
import {
  PORTAL_BROWSER_CONNECTOR_SLUG,
  getGlobalPortalCatalog,
  resolvePortalCanonical,
  normalizeBrowserStrategy,
  buildPortalDefinitionRecord,
  buildPortalAccountRecord,
  buildCredentialRefRecord,
  buildSessionRefRecord,
  deriveAccountStatus,
  findRequestSecrets,
} from '../lib/attendance/portal-admin-sanitizers.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== 43P1.1 — Portal Browser Canonical Store ==');

// [1] Connector slug próprio.
console.log('\n[1] connector slug');
{
  assert('slug portal_browser', PORTAL_BROWSER_CONNECTOR_SLUG === 'portal_browser');
  assert('slug NÃO é whatsapp_zapi', PORTAL_BROWSER_CONNECTOR_SLUG !== 'whatsapp_zapi');
}

// [2] browser_strategy normalização.
console.log('\n[2] browser_strategy');
{
  const fromStr = normalizeBrowserStrategy('browserbase');
  assert('string → {primary,fallback}', fromStr.primary === 'browserbase' && fromStr.fallback === null);
  const fromObj = normalizeBrowserStrategy({ primary: 'browserbase_playwright_stagehand', fallback: 'skyvern_lab' });
  assert('objeto preservado', fromObj.primary === 'browserbase_playwright_stagehand' && fromObj.fallback === 'skyvern_lab');
  const fromBad = normalizeBrowserStrategy({ primary: 'telegram' });
  assert('valor inválido → unknown', fromBad.primary === 'unknown');
  const def = buildPortalDefinitionRecord({ label: 'X', owner_key: 'allianz', base_url: 'https://x.com', browser_strategy: { primary: 'browserbase_playwright_stagehand', fallback: 'skyvern_lab' } });
  assert('record canoniza browser_strategy', def.browser_strategy.primary === 'browserbase_playwright_stagehand');
}

// [3] challenge_profile override explícito.
console.log('\n[3] challenge override');
{
  const def = buildPortalDefinitionRecord({ label: 'X', owner_key: 'allianz', base_url: 'https://x.com', auth_methods: [], challenge_profile: { captcha: true } });
  assert('override captcha respeitado', def.challenge_profile.captcha === true);
  assert('override força requires_hitl', def.challenge_profile.requires_hitl === true);
}

// [4] catálogo global vazio não quebra.
console.log('\n[4] catálogo global');
{
  const cat = getGlobalPortalCatalog();
  assert('catálogo é array', Array.isArray(cat));
  assert('catálogo vazio no MVP', cat.length === 0);
}

// [5] resolve canônico.
console.log('\n[5] resolve canônico');
{
  const tenantDef = buildPortalDefinitionRecord({ portal_id: 'allianz_portal', label: 'Allianz', owner_key: 'allianz', base_url: 'https://portal.allianz.com.br', auth_methods: ['password', 'mfa'], supported_journeys: ['residential_assistance'], scope: 'tenant_draft' });

  // sem conta → create_portal_account, portal_source tenant_draft
  const noAcct = resolvePortalCanonical([], [tenantDef], [], { company_id: 'co', owner_key: 'allianz', journey: 'residential_assistance' });
  assert('tenant_draft sem conta → create_portal_account', noAcct.next_step === 'create_portal_account');
  assert('portal_source tenant_draft', noAcct.portal_source === 'tenant_draft', noAcct.portal_source);
  assert('connector_template portal_browser', noAcct.connector_template === 'portal_browser');
  assert('real_action_allowed false', noAcct.real_action_allowed === false);

  // com conta saudável → ready_for_dry_run
  const acct = buildPortalAccountRecord({ company_id: 'co', portal_id: 'allianz_portal', label: 'conta', challenge_profile: tenantDef.challenge_profile });
  acct.credential_ref = buildCredentialRefRecord({ company_id: 'co', portal_id: 'allianz_portal', vault_ref: 'vault://aaa111bbb222' });
  acct.session_ref = buildSessionRefRecord({ company_id: 'co', portal_id: 'allianz_portal', storage_ref: 'store://ccc333', status: 'healthy', expires_at: new Date(Date.now() + 3600_000).toISOString() });
  acct.status = deriveAccountStatus(acct);
  const ready = resolvePortalCanonical([], [tenantDef], [acct], { company_id: 'co', owner_key: 'allianz', journey: 'residential_assistance' });
  assert('conta saudável → ready_for_dry_run', ready.next_step === 'ready_for_dry_run_43p3');
  assert('account_source tenant', ready.account_source === 'tenant');

  // só global (sem tenant) → portal_source global
  const globalDef = { ...tenantDef, scope: 'global' };
  const onlyGlobal = resolvePortalCanonical([globalDef], [], [], { company_id: 'co', owner_key: 'allianz' });
  assert('só global → portal_source global', onlyGlobal.portal_source === 'global', onlyGlobal.portal_source);

  // nada → none
  const none = resolvePortalCanonical([], [], [], { company_id: 'co', owner_key: 'porto' });
  assert('nada → none', none.portal_source === 'none' && none.portal_available === false);
}

// [6] sem segredo cru.
console.log('\n[6] segurança');
{
  assert('findRequestSecrets detecta storageState', findRequestSecrets({ storage_state: 'x' }).length > 0);
  let threw = false;
  try { buildSessionRefRecord({ company_id: 'co', portal_id: 'p', storage_ref: 's', storageState: { cookies: [] } }); } catch { threw = true; }
  assert('session com storageState → lança', threw);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
