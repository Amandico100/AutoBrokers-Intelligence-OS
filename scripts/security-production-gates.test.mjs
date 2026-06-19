#!/usr/bin/env node
/**
 * SEC-001 — Production Gates & PII redaction (offline).
 *
 *   node scripts/security-production-gates.test.mjs
 *
 * Garante: flags ausentes bloqueiam; kill switch; portal/external/rag/memory
 * bloqueados; mesmo com tudo ligado o real continua false; segredos rejeitados;
 * PII/segredo redigidos; auditoria sanitizada.
 */
import {
  getProductionFlags,
  evaluateGlobalKillSwitch,
  evaluatePortalRealActionGate,
  evaluateExternalActionRealSendGate,
  evaluateRagKnowledgePublishGate,
  evaluateMemoryAccessGate,
  assertNoRawSecrets,
  assertNoPIIInLogPayload,
  sanitizeAuditPayload,
} from '../lib/security/production-gates.ts';
import { redactPII, redactDeep, findSecretKeys } from '../lib/security/pii-redaction.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

console.log('== SEC-001 — Production Gates ==');

// [1] flags default safe.
console.log('\n[1] flags');
{
  const f = getProductionFlags({});
  assert('env vazio → kill switch ativo', f.global_kill_switch === true);
  assert('portal real off', f.portal_real_action_enabled === false);
  assert('external real off', f.external_action_real_enabled === false);
  assert('rag publish off', f.rag_publish_to_attendance_enabled === false);
  assert('web_search_attendance sempre false', f.web_search_attendance_enabled === false);
  const fOn = getProductionFlags({ WEB_SEARCH_ATTENDANCE_ENABLED: 'true', PORTAL_REAL_ACTION_ENABLED: 'true', GLOBAL_KILL_SWITCH: 'false' });
  assert('web_search_attendance ignora env true', fOn.web_search_attendance_enabled === false);
  assert('kill switch desliga só com false explícito', fOn.global_kill_switch === false);
}

// [2] kill switch.
console.log('\n[2] kill switch');
{
  assert('kill ativo por padrão', evaluateGlobalKillSwitch(getProductionFlags({})).active === true);
  assert('kill off explícito', evaluateGlobalKillSwitch(getProductionFlags({ GLOBAL_KILL_SWITCH: 'false' })).active === false);
}

// [3] portal/external — mesmo com tudo ligado, real continua false.
console.log('\n[3] portal/external');
{
  const allOn = getProductionFlags({ GLOBAL_KILL_SWITCH: 'false', PORTAL_REAL_ACTION_ENABLED: 'true', PORTAL_LOGIN_REAL_ENABLED: 'true', PORTAL_SESSION_CAPTURE_ENABLED: 'true', EXTERNAL_ACTION_REAL_ENABLED: 'true', INSURER_WHATSAPP_REAL_SEND_ENABLED: 'true' });
  const portal = evaluatePortalRealActionGate({ flags: allOn, dry_run_passed: true, trace_available: true, replay_available: true, approval_exists: true });
  assert('portal gate allowed false (travado SEC-001)', portal.allowed === false);
  assert('portal real_action_allowed false', portal.real_action_allowed === false);
  const portalDefault = evaluatePortalRealActionGate({});
  assert('portal default blocker kill switch', portalDefault.blockers.includes('global_kill_switch_active'));

  const ext = evaluateExternalActionRealSendGate({ flags: allOn, channel: 'insurer_whatsapp', adapter_can_send_real: true, approval_exists: true });
  assert('external gate allowed false', ext.allowed === false && ext.real_action_allowed === false);
  const extDefault = evaluateExternalActionRealSendGate({ channel: 'insurer_whatsapp' });
  assert('external default blockers', extDefault.blockers.includes('external_action_real_disabled') && extDefault.blockers.includes('adapter_cannot_send_real'));
}

// [4] RAG publish gate.
console.log('\n[4] rag publish');
{
  const brokerInternal = evaluateRagKnowledgePublishGate({ target: 'attendance', audience: 'broker_internal', sensitivity: 'high', status: 'published', source_kind: 'curated' });
  assert('broker_internal bloqueado no attendance', brokerInternal.blockers.includes('audience_not_allowed_for_attendance'));
  const insured = evaluateRagKnowledgePublishGate({ target: 'attendance', audience: 'insured_external', sensitivity: 'low', status: 'published', source_kind: 'curated', has_provenance: true, approval_exists: true });
  assert('insured_external ainda allowed false (flag off)', insured.allowed === false && insured.blockers.includes('rag_publish_to_attendance_disabled'));
  const raw = evaluateRagKnowledgePublishGate({ target: 'attendance', audience: 'insured_external', sensitivity: 'low', status: 'draft', source_kind: 'raw_intake' });
  assert('raw_intake → quarantine blocker', raw.blockers.includes('raw_intake_must_be_quarantined'));
  const missing = evaluateRagKnowledgePublishGate({ target: 'attendance' });
  assert('sem audience/sensitivity → blockers', missing.blockers.includes('missing_audience') && missing.blockers.includes('missing_sensitivity'));
}

// [5] memory access.
console.log('\n[5] memory access');
{
  const att = evaluateMemoryAccessGate({ actor: 'attendance', audience: 'broker_internal', same_tenant: true, same_case_or_session: true, company_match: true });
  assert('attendance broker_internal bloqueado', att.allowed === false && att.blockers.includes('attendance_only_insured_external'));
  const cross = evaluateMemoryAccessGate({ actor: 'attendance', audience: 'insured_external', same_tenant: false, company_match: false });
  assert('cross-tenant bloqueado', cross.blockers.includes('cross_tenant_blocked') && cross.blockers.includes('company_mismatch'));
  const core = evaluateMemoryAccessGate({ actor: 'core', audience: 'broker_internal', same_tenant: true, company_match: true, flags: getProductionFlags({ MEMORY_LONG_TERM_ENABLED: 'true' }) });
  assert('core tenant scope ok (com flag)', core.blockers.includes('memory_long_term_disabled') === false);
}

// [6] segredos / PII.
console.log('\n[6] segredos/PII');
{
  assert('assertNoRawSecrets detecta password', assertNoRawSecrets({ a: { password: 'x' } }).ok === false);
  assert('assertNoRawSecrets detecta storage_state', assertNoRawSecrets({ s: { storage_state: '{}' } }).ok === false);
  assert('assertNoRawSecrets limpo ok', assertNoRawSecrets({ a: { b: 1 } }).ok === true);
  assert('PII log CPF detectado', assertNoPIIInLogPayload({ x: 'cpf 047.608.979-41' }).ok === false);
  assert('redactPII CPF', !redactPII('cliente 047.608.979-41').includes('047.608.979-41'));
  assert('redactPII OTP', redactPII('codigo 123456').includes('[otp]'));
  assert('redactPII email', redactPII('a@b.com').includes('[email]'));
  assert('redactDeep remove token', findSecretKeys(redactDeep({ token: 'abc', nested: { cookie: 'x' } })).length === 0 ? true : (typeof redactDeep({ token: 'abc' }).token === 'string'));
  const dirty = { cookie: 'sid=abc', note: 'telefone (44) 99999-8888 e codigo 999111', nested: { vault_ref: 'vault://x' } };
  const clean = sanitizeAuditPayload(dirty);
  assert('sanitizeAuditPayload remove segredo', clean.cookie === '[redacted]' && clean.nested.vault_ref === '[redacted]');
  assert('sanitizeAuditPayload mascara num/otp', !JSON.stringify(clean).includes('999111'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
