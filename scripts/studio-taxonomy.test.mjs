#!/usr/bin/env node
/** SPEC-013 — taxonomia Studio/Tenant (puro, offline). */
import {
  STUDIO_SOURCE_KINDS, studioSourceKindForRole, tenantInstanceKind, canPublishAsAuxiliary, isGlobalChatOrAttendance,
} from '../lib/admin/studio-taxonomy.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 — studio taxonomy ==\n');

assert('4 source kinds', STUDIO_SOURCE_KINDS.length === 4);
assert('core → global_core', studioSourceKindForRole('core') === 'global_core');
assert('attendance → global_attendance', studioSourceKindForRole('attendance') === 'global_attendance');
assert('outro role → null (marcação explícita)', studioSourceKindForRole('subagent') === null);

assert('tenant core', tenantInstanceKind('core') === 'core');
assert('tenant attendance', tenantInstanceKind('attendance') === 'attendance');
assert('tenant auxiliary runtime', tenantInstanceKind('core', true) === 'auxiliary_runtime');
assert('tenant custom', tenantInstanceKind('weird') === 'tenant_custom');

assert('só global_auxiliary publica como Auxiliar', canPublishAsAuxiliary('global_auxiliary') === true);
assert('global_core NÃO publica como Auxiliar', canPublishAsAuxiliary('global_core') === false);
assert('Core/Even são chat/attendance globais', isGlobalChatOrAttendance('global_core') && isGlobalChatOrAttendance('global_attendance') && !isGlobalChatOrAttendance('global_auxiliary'));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
