#!/usr/bin/env node
/** SPEC-013 B1 — publish guard + lifecycle de Auxiliar (puro, offline). */
import {
  canPublishAgentAsGlobalAuxiliary, publishBlockReason,
  nextTenantAuxStatus, tenantAuxStatusLabel, TENANT_AUX_STATES,
} from '../lib/admin/auxiliary-publish.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 B1 — auxiliary publish/lifecycle ==\n');

// publish guard
assert('global_auxiliary do Studio publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_auxiliary' }) === true);
assert('Core (global_core) NÃO publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_core' }) === false);
assert('Even (global_attendance) NÃO publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_attendance' }) === false);
assert('subagent NÃO publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'source_subagent' }) === false);
assert('empresa cliente NÃO publica como global', canPublishAgentAsGlobalAuxiliary({ companyKind: 'client', studioSourceKind: 'global_auxiliary' }) === false);

assert('motivo: fora do Studio', publishBlockReason({ companyKind: 'client', studioSourceKind: 'global_auxiliary' }) === 'fonte_precisa_ser_studio');
assert('motivo: core/even', publishBlockReason({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_core' }) === 'core_ou_even_nao_publicavel');
assert('motivo: subagent', publishBlockReason({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'source_subagent' }) === 'subagent_nao_publicavel');
assert('motivo: ok = null', publishBlockReason({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_auxiliary' }) === null);

// lifecycle
assert('5 estados', TENANT_AUX_STATES.length === 5);
assert('active→pause', nextTenantAuxStatus('active', 'pause') === 'paused');
assert('paused→resume', nextTenantAuxStatus('paused', 'resume') === 'active');
assert('active→uninstall', nextTenantAuxStatus('active', 'uninstall') === 'uninstalled');
assert('paused→uninstall', nextTenantAuxStatus('paused', 'uninstall') === 'uninstalled');
assert('resume só de paused', nextTenantAuxStatus('active', 'resume') === null);
assert('pause de uninstalled inválido', nextTenantAuxStatus('uninstalled', 'pause') === null);
assert('uninstall de uninstalled inválido', nextTenantAuxStatus('uninstalled', 'uninstall') === null);
assert('awaiting_runtime pode pausar', nextTenantAuxStatus('awaiting_runtime', 'pause') === 'paused');
assert('label honesto', tenantAuxStatusLabel('awaiting_runtime') === 'Aguardando configuração' && tenantAuxStatusLabel('active') === 'Pronto');

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
