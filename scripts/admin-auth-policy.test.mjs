#!/usr/bin/env node
/** TA2-B — políticas de autorização puras (offline). */
import { canWriteTenantConfig, isPlatformMaster, canAdminReadCompany, canProvisionTenant, sameOriginOk, tenantCompanyConsistent } from '../lib/admin/admin-auth-policy.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-B — admin auth policy ==\n');

// master de plataforma = master_admin SEM company
assert('master sem company é master', isPlatformMaster({ role: 'master_admin', companyId: null }) === true);
assert('master COM company NÃO é master de plataforma', isPlatformMaster({ role: 'master_admin', companyId: 'c1' }) === false);
assert('company_admin não é master', isPlatformMaster({ role: 'company_admin', companyId: 'c1' }) === false);

// escrita tenant
assert('owner escreve', canWriteTenantConfig({ role: null, isOwner: true }) === true);
assert('admin_company escreve', canWriteTenantConfig({ role: 'admin_company', isOwner: false }) === true);
assert('role comum NÃO escreve', canWriteTenantConfig({ role: 'member', isOwner: false }) === false);
assert('sem role/sem owner NÃO escreve', canWriteTenantConfig({ role: null, isOwner: false }) === false);

// leitura admin de empresa
assert('master lê qualquer empresa', canAdminReadCompany({ role: 'master_admin', sessionCompanyId: null, targetCompanyId: 'c9' }) === true);
assert('company_admin lê a PRÓPRIA', canAdminReadCompany({ role: 'company_admin', sessionCompanyId: 'c1', targetCompanyId: 'c1' }) === true);
assert('company_admin NÃO lê outra empresa', canAdminReadCompany({ role: 'company_admin', sessionCompanyId: 'c1', targetCompanyId: 'c2' }) === false);
assert('sessão sem papel NÃO lê', canAdminReadCompany({ role: null, sessionCompanyId: null, targetCompanyId: 'c1' }) === false);

// provisionamento só master
assert('só master provisiona', canProvisionTenant({ role: 'master_admin', companyId: null }) === true);
assert('company_admin NÃO provisiona', canProvisionTenant({ role: 'company_admin', companyId: 'c1' }) === false);

// [TA2-C] same-origin + consistência sessão×banco
console.log('\n[TA2-C] same-origin + consistência');
assert('sameOrigin: sem origin permite (defesa em profundidade)', sameOriginOk({ origin: null, host: 'app.com' }) === true);
assert('sameOrigin: host igual permite', sameOriginOk({ origin: 'https://app.com', host: 'app.com' }) === true);
assert('sameOrigin: host diferente bloqueia', sameOriginOk({ origin: 'https://evil.com', host: 'app.com' }) === false);
assert('sameOrigin: origin inválido bloqueia', sameOriginOk({ origin: 'not-a-url', host: 'app.com' }) === false);
assert('consistência: banco sem empresa bloqueia', tenantCompanyConsistent({ sessionCompanyId: 'c1', dbCompanyId: null }) === false);
assert('consistência: sessão sem empresa usa o banco', tenantCompanyConsistent({ sessionCompanyId: null, dbCompanyId: 'c1' }) === true);
assert('consistência: divergência bloqueia', tenantCompanyConsistent({ sessionCompanyId: 'c2', dbCompanyId: 'c1' }) === false);
assert('consistência: iguais ok', tenantCompanyConsistent({ sessionCompanyId: 'c1', dbCompanyId: 'c1' }) === true);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
