#!/usr/bin/env node
/**
 * 43P1.2 — Official Portal Intake Importer (offline; lê o CSV real do intake).
 *
 *   node scripts/attendance-portal-intake-importer.test.mjs
 *
 * Garante: parse CSV/markdown; mapeamento Allianz/SulAmérica; regras de confiança;
 * dedupe; https obrigatório; official_sources preservado; sem segredo/PII; catálogo
 * global cobre as 8+ seguradoras; tenant continua separado.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  parseCsv,
  parsePortalRegistryCsv,
  parsePortalRegistryMarkdown,
  classifyPortalSourceConfidence,
  mapRegistryRowToPortalDefinition,
  mapJourneyType,
  mapAuthMethods,
  dedupePortalDefinitions,
  buildGlobalPortalCatalogFromRows,
} from '../lib/attendance/portal-intake-importer.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const csvPath = path.join(root, 'docs/intake/portal-registry/portal_registry_unificado_linha_a_linha.csv');

console.log('== 43P1.2 — Portal Intake Importer ==');

// [1] CSV/markdown parsing.
console.log('\n[1] parsing');
{
  const rows = parseCsv('a,b,c\n1,"2,2",3\n');
  assert('csv lida aspas com vírgula', rows[1][1] === '2,2');
  const md = parsePortalRegistryMarkdown('| insurer_key | surface_name |\n| --- | --- |\n| allianz | AllianzNet |\n');
  assert('markdown table parse', md.length === 1 && md[0].insurer_key === 'allianz');
}

// [2] mapeamentos.
console.log('\n[2] mapeamentos');
{
  assert('journey login_base→login', mapJourneyType('login_base') === 'login');
  assert('journey sinistro→claim', mapJourneyType('sinistro') === 'claim');
  assert('auth login_password→[password]', JSON.stringify(mapAuthMethods('login_password')) === '["password"]');
  assert('auth mfa', mapAuthMethods('login_password_mfa').includes('mfa'));
  assert('auth captcha', mapAuthMethods('login_password_captcha').includes('captcha'));
}

// [3] regras de confiança.
console.log('\n[3] confiança');
{
  const confirmedCorretor = { confidence: 'confirmed', audience: 'corretor', canonical_url: 'https://x.com' };
  assert('confirmed+corretor → seed_active', classifyPortalSourceConfidence(confirmedCorretor) === 'seed_active');
  const confirmedDev = { confidence: 'confirmed', audience: 'desenvolvedor', canonical_url: 'https://x.com' };
  assert('confirmed+dev → needs_review', classifyPortalSourceConfidence(confirmedDev) === 'needs_review');
  const strong = { confidence: 'strong_evidence', audience: 'corretor', canonical_url: 'https://x.com' };
  assert('strong_evidence → needs_review', classifyPortalSourceConfidence(strong) === 'needs_review');
  const noHttps = { confidence: 'confirmed', audience: 'corretor', canonical_url: 'http://x.com' };
  assert('sem https → ignored', classifyPortalSourceConfidence(noHttps) === 'ignored');
  const unconf = { confidence: 'unconfirmed', audience: 'corretor', canonical_url: 'https://x.com' };
  assert('unconfirmed → ignored', classifyPortalSourceConfidence(unconf) === 'ignored');
}

// [4] mapeamento de linha → definition.
console.log('\n[4] row → definition');
{
  const allianz = { insurer_key: 'allianz', surface_name: 'AllianzNet Corretor', audience: 'corretor', journey_type: 'login_base', canonical_url: 'https://www.allianznet.com.br/x', launch_url: 'https://www.allianznet.com.br/x', auth_type: 'login_password', challenge_profile: 'unknown', confidence: 'confirmed', official_sources: 'https://www.allianznet.com.br/x', checked_at: '2026-04-06' };
  const def = mapRegistryRowToPortalDefinition(allianz, '2026-06-18T00:00:00.000Z');
  assert('allianz def criada', def && def.owner_key === 'allianz');
  assert('allianz scope global', def.scope === 'global');
  assert('allianz status sandbox_ready', def.status === 'sandbox_ready', def.status);
  assert('allianz journey login', def.supported_journeys.includes('login'));
  assert('allianz browser_strategy objeto', def.browser_strategy.primary === 'browserbase_playwright_stagehand');
  assert('allianz official_sources preservado', String(def.metadata.official_sources).includes('allianznet'));
  assert('allianz source_type official_research', def.metadata.source_type === 'official_research');

  const sula = { insurer_key: 'sulamerica', surface_name: 'Portal do Corretor', audience: 'corretor', journey_type: 'sinistro', canonical_url: 'https://portal.sulamerica.com.br/x', auth_type: 'login_password_mfa', challenge_profile: 'unknown', confidence: 'strong_evidence', official_sources: 'https://portal.sulamerica.com.br', checked_at: '2026-04-06' };
  const sdef = mapRegistryRowToPortalDefinition(sula, '2026-06-18T00:00:00.000Z');
  assert('sulamerica needs_review', sdef.status === 'needs_review');
  assert('sulamerica mfa → requires_hitl', sdef.challenge_profile.requires_hitl === true);
}

// [5] dedupe.
console.log('\n[5] dedupe');
{
  const now = '2026-06-18T00:00:00.000Z';
  const a = mapRegistryRowToPortalDefinition({ insurer_key: 'allianz', surface_name: 'AllianzNet Corretor', audience: 'corretor', journey_type: 'login_base', canonical_url: 'https://x.com', auth_type: 'login_password', confidence: 'confirmed' }, now);
  const b = mapRegistryRowToPortalDefinition({ insurer_key: 'allianz', surface_name: 'AllianzNet Corretor', audience: 'corretor', journey_type: 'sinistro', canonical_url: 'https://x.com', auth_type: 'login_password', confidence: 'confirmed' }, now);
  const deduped = dedupePortalDefinitions([a, b]);
  assert('dedupe une mesma surface', deduped.length === 1);
  assert('dedupe une jornadas', deduped[0].supported_journeys.includes('login') && deduped[0].supported_journeys.includes('claim'));
}

// [6] build a partir do CSV REAL do intake.
console.log('\n[6] CSV real');
{
  if (!fs.existsSync(csvPath)) {
    assert('intake CSV presente', false, 'intake_files_missing: ' + csvPath);
  } else {
    const rows = parsePortalRegistryCsv(fs.readFileSync(csvPath, 'utf8'));
    assert('CSV real parseado (>150 linhas)', rows.length > 150, String(rows.length));
    const { definitions, stats } = buildGlobalPortalCatalogFromRows(rows, '2026-06-18T00:00:00.000Z');
    assert('catálogo não vazio', definitions.length > 0);
    assert('ignored=0 (todas https/confidence)', stats.ignored === 0, String(stats.ignored));
    for (const ik of ['allianz', 'porto', 'hdi', 'tokio_marine', 'sulamerica', 'azul', 'alfa', 'chubb']) {
      assert(`cobre ${ik}`, stats.insurers.includes(ik));
    }
    // sem segredo cru nas saídas (chaves que carregariam valor sensível).
    // Nota: 'password' é enum de auth_methods e 'otp' é flag booleano de challenge — NÃO são segredos.
    const raw = JSON.stringify(definitions).toLowerCase();
    for (const bad of ['"senha"', '"cookie"', '"storage_state"', '"storagestate"', '"client_token"', '"vault_ref"', '"private_key"', '"bearer"']) {
      assert(`sem chave de segredo ${bad}`, !raw.includes(bad), bad);
    }
    const ALLOWED_AUTH = ['password', 'mfa', 'captcha', 'sso', 'certificate', 'otp'];
    assert('auth_methods só com enum permitido', definitions.every((d) => (d.auth_methods || []).every((m) => ALLOWED_AUTH.includes(m))));
    assert('challenge_profile.otp é boolean', definitions.every((d) => typeof d.challenge_profile.otp === 'boolean'));
    assert('todas base_url https', definitions.every((d) => /^https:\/\//i.test(d.base_url)));
  }
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
