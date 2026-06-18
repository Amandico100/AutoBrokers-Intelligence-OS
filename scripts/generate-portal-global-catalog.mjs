#!/usr/bin/env node
/**
 * 43P1.2 — Gera o seed do Global Portal Catalog a partir do registry oficial.
 *   node scripts/generate-portal-global-catalog.mjs
 * Lê docs/intake/portal-registry/portal_registry_unificado_linha_a_linha.csv,
 * roda o importer puro e escreve lib/attendance/portal-global-catalog-seed.ts.
 * NÃO acessa portal/URL real; só metadados.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parsePortalRegistryCsv, buildGlobalPortalCatalogFromRows } from '../lib/attendance/portal-intake-importer.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const csvPath = path.join(root, 'docs/intake/portal-registry/portal_registry_unificado_linha_a_linha.csv');
const outPath = path.join(root, 'lib/attendance/portal-global-catalog-seed.ts');

if (!fs.existsSync(csvPath)) {
  console.error('intake_files_missing:', csvPath);
  process.exit(2);
}

const content = fs.readFileSync(csvPath, 'utf8');
const rows = parsePortalRegistryCsv(content);
const { definitions, stats } = buildGlobalPortalCatalogFromRows(rows, '2026-06-18T00:00:00.000Z');

const header = `// AUTO-GERADO por scripts/generate-portal-global-catalog.mjs (43P1.2). NÃO editar à mão.
// Fonte: docs/intake/portal-registry/portal_registry_unificado_linha_a_linha.csv (official_research).
// Sem credencial/PII. Catálogo GLOBAL (scope:'global'). real_action_allowed sempre false.
import type { PortalDefinitionRecord } from '@/lib/attendance/portal-admin-sanitizers';

export const PORTAL_GLOBAL_CATALOG_GENERATED_AT = '2026-06-18T00:00:00.000Z';
export const PORTAL_GLOBAL_CATALOG_STATS = ${JSON.stringify(stats, null, 2)} as const;

export const PORTAL_GLOBAL_CATALOG_SEED: PortalDefinitionRecord[] = ${JSON.stringify(definitions, null, 2)};
`;

fs.writeFileSync(outPath, header, 'utf8');
console.log('seed written:', outPath);
console.log('stats:', JSON.stringify(stats, null, 2));
