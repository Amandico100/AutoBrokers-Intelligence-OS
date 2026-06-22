#!/usr/bin/env node
/** SPEC-013 — releases imutáveis + secret scan + seed (puro, offline). */
import { CANONICAL_BLUEPRINTS, AUTOBROKERS_CORE_BLUEPRINT } from '../lib/admin/agent-blueprints-canonical.ts';
import {
  buildArtifactFromCanonical, scanForSecrets, assertReleasePublishable, hashArtifact,
  canEditRelease, canTransitionRelease, seedReleasesFromCanonical, ARTIFACT_SCHEMA_VERSION,
} from '../lib/admin/blueprint-release.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 — blueprint releases ==\n');

// artefato a partir do canônico
const art = buildArtifactFromCanonical(AUTOBROKERS_CORE_BLUEPRINT);
assert('artefato com schema_version', art.schema_version === ARTIFACT_SCHEMA_VERSION);
assert('artefato traz prompt-base e guardrails', typeof art.system_prompt_template === 'string' && Array.isArray(art.immutable_guardrails) && art.immutable_guardrails.length > 0);
assert('artefato nasce sem capability_keys', Array.isArray(art.declared_capability_keys) && art.declared_capability_keys.length === 0);

// secret scan
assert('scan limpo no artefato', scanForSecrets(art).length === 0);
assert('scan detecta campo token', scanForSecrets({ x: { access_token: 'abc' } }).some((s) => s.includes('forbidden_secret_field')));
assert('scan detecta sk- key', scanForSecrets({ k: 'sk-ABCDEFGH1234567890' }).some((s) => s.includes('openai_like_key')));
assert('scan detecta bearer', scanForSecrets({ h: 'Bearer abcdef123456' }).some((s) => s.includes('bearer_token')));
assert('scan detecta jwt', scanForSecrets({ t: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c' }).some((s) => s.includes('jwt')));
assert('scan detecta url com segredo', scanForSecrets({ u: 'https://api.x.com/cb?access_token=zzz' }).some((s) => s.includes('url_with_secret')));

// publicabilidade
assert('artefato canônico é publicável', assertReleasePublishable(art).ok === true);
const withSecret = { ...art, leaked: { token: 'xyz' } };
assert('artefato com segredo é bloqueado', assertReleasePublishable(withSecret).ok === false);
const withRawTool = { ...art, mcp_connections: [{ url: 'https://x/mcp' }] };
assert('tool/MCP livre é bloqueado', assertReleasePublishable(withRawTool).errors.some((e) => e.startsWith('tool_mcp_livre_proibido')));
const badCaps = { ...art, declared_capability_keys: [123] };
assert('capability_keys inválidas bloqueiam', assertReleasePublishable(badCaps).ok === false);

// hash criptográfico (SHA-256) determinístico + imutabilidade
assert('hash determinístico', hashArtifact(art) === hashArtifact(buildArtifactFromCanonical(AUTOBROKERS_CORE_BLUEPRINT)));
assert('hash muda com o conteúdo', hashArtifact(art) !== hashArtifact({ ...art, role: 'mudou' }));
assert('hash é sha256 (64 hex)', /^sha256_[0-9a-f]{64}$/.test(hashArtifact(art)));
assert('só draft é editável', canEditRelease('draft') === true && canEditRelease('published') === false && canEditRelease('retired') === false);
assert('transições válidas', canTransitionRelease('draft', 'published') && canTransitionRelease('published', 'retired'));
assert('transições inválidas bloqueadas', !canTransitionRelease('published', 'draft') && !canTransitionRelease('retired', 'published'));

// seed
const seeds = seedReleasesFromCanonical(CANONICAL_BLUEPRINTS);
assert('seed gera 2 releases', seeds.length === 2);
assert('seed v1.0.0 published', seeds.every((s) => s.semantic_version === '1.0.0' && s.status === 'published'));
assert('seed com hash sha256 e sem segredo', seeds.every((s) => /^sha256_[0-9a-f]{64}$/.test(s.artifact_hash) && assertReleasePublishable(s.artifact).ok));
assert('seed cobre core e even', seeds.some((s) => s.blueprint_key === 'autobrokers-core-v1') && seeds.some((s) => s.blueprint_key === 'even-attendance-v1'));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
