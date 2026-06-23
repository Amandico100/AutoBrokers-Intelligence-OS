#!/usr/bin/env node
/** SPEC-014 C1 — Capability Registry: catálogo, matriz e resolver (puro, offline). */
import {
  CAPABILITY_CATALOG, AUTHORIZATION_MATRIX, validateCatalog, capabilitiesForRole, isAllowedForRole, categories,
  resolveAgentCapabilities, activeKeys, summarize, requiresApproval,
} from '../lib/capabilities/registry.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-014 C1 — capability registry ==\n');

// Catálogo íntegro
assert('catálogo sem erros (matriz só referencia keys existentes)', validateCatalog().length === 0);
assert('categorias incluem insurance_ops e productivity', categories().includes('insurance_ops') && categories().includes('productivity'));

// Matriz
assert('core pode busca web', isAllowedForRole('core', 'platform.web.search'));
assert('attendance NÃO tem busca web aberta', !isAllowedForRole('attendance', 'platform.web.search'));
assert('core pode InfoCap', isAllowedForRole('core', 'operational.infocap.policy_lookup.read'));
assert('attendance pode abrir assistência', isAllowedForRole('attendance', 'operational.portal.assistance.request'));
assert('core NÃO abre assistência (não é ferramenta livre)', !isAllowedForRole('core', 'operational.portal.assistance.request'));

// Resolver — Core
const core = resolveAgentCapabilities('core', []);
const coreMap = Object.fromEntries(core.map((r) => [r.key, r.status]));
assert('Core: busca web ATIVA por padrão (plataforma, sem conexão)', coreMap['platform.web.search'] === 'active');
assert('Core: conhecimento global ATIVO', coreMap['knowledge.global.search'] === 'active');
assert('Core: InfoCap precisa de conexão sem entitlement', coreMap['operational.infocap.policy_lookup.read'] === 'needs_connection');
assert('Core: Google Drive precisa de conexão', coreMap['tenant.google_drive.read'] === 'needs_connection');

// Resolver — Core COM InfoCap conectado
const coreInfo = resolveAgentCapabilities('core', [{ capability_key: 'operational.infocap.policy_lookup.read', enabled: true, connection_present: true }]);
const ci = Object.fromEntries(coreInfo.map((r) => [r.key, r.status]));
assert('Core: InfoCap ATIVO quando conectado+habilitado', ci['operational.infocap.policy_lookup.read'] === 'active');

// Resolver — desligado
const off = resolveAgentCapabilities('core', [{ capability_key: 'platform.web.search', enabled: false }]);
assert('Core: busca web DESLIGADA quando corretora desliga', Object.fromEntries(off.map((r) => [r.key, r.status]))['platform.web.search'] === 'disabled');

// Resolver — Auxiliar declara só o mínimo
const aux = resolveAgentCapabilities('auxiliary', [], ['platform.web.search']);
assert('Auxiliar de pesquisa: só a capability declarada aparece', aux.length === 1 && aux[0].key === 'platform.web.search');
assert('Auxiliar de pesquisa: busca web ativa', aux[0].status === 'active');
const auxBad = resolveAgentCapabilities('auxiliary', [], ['operational.portal.assistance.request']);
assert('Auxiliar não pode portal assistance (fora da matriz)', auxBad[0].status === 'not_allowed_for_role');

// Aprovação
assert('abrir assistência exige aprovação', requiresApproval('operational.portal.assistance.request'));
assert('busca web NÃO exige aprovação', !requiresApproval('platform.web.search'));

// Helpers
assert('capabilitiesForRole(core) > capabilitiesForRole(subagent)', capabilitiesForRole('core').length > capabilitiesForRole('subagent').length);
assert('summarize soma = total resolvido', (() => { const s = summarize(core); return Object.values(s).reduce((a, b) => a + b, 0) === core.length; })());
assert('activeKeys do Core inclui memória do usuário', activeKeys(core).includes('memory.user.read_write'));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
