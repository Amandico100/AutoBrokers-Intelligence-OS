#!/usr/bin/env node
/** SPEC-013 — classificação de empresa (puro, offline). */
import {
  normalizeCompanyKind, isPlatformCompany, isClientCompany, isBlueprintStudio, isGlobalKnowledge,
  visibleInClientListing, canUseTenantDashboard, shouldAutoProvisionOnCreate, allowsClientOperations, requiresMasterOnly,
} from '../lib/admin/company-kind.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 — company kind ==\n');

assert('default seguro = client', normalizeCompanyKind(undefined) === 'client' && normalizeCompanyKind('lixo') === 'client');
assert('studio reconhecido', isBlueprintStudio('platform_blueprint_studio') && isPlatformCompany('platform_blueprint_studio'));
assert('knowledge reconhecido', isGlobalKnowledge('platform_knowledge') && isPlatformCompany('platform_knowledge'));
assert('client não é plataforma', isClientCompany('client') && !isPlatformCompany('client'));

// fluxos: só cliente
assert('só cliente na listagem', visibleInClientListing('client') && !visibleInClientListing('platform_blueprint_studio'));
assert('só cliente no dashboard tenant', canUseTenantDashboard('client') && !canUseTenantDashboard('platform_knowledge'));
assert('só cliente auto-provisiona', shouldAutoProvisionOnCreate('client') && !shouldAutoProvisionOnCreate('platform_blueprint_studio'));
assert('só cliente opera (WhatsApp/portal/corridor)', allowsClientOperations('client') && !allowsClientOperations('platform_blueprint_studio'));
assert('plataforma exige master', requiresMasterOnly('platform_blueprint_studio') && requiresMasterOnly('platform_knowledge') && !requiresMasterOnly('client'));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
