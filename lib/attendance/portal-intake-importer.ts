// 43P1.2 — Official Portal Intake Importer. PURO, self-contained (sem imports
// cross-module em runtime). Lê o registry oficial pesquisado (CSV/markdown) e
// produz PortalDefinitionRecord GLOBAIS (scope:'global'), sem credencial/PII,
// preservando fonte/confidence/checked_at. NUNCA acessa portal/URL real.

import type { PortalDefinitionRecord, PortalAuthMethod, ChallengeProfile } from '@/lib/attendance/portal-catalog-types';

// --- CSV / Markdown parsing -------------------------------------------------

/** Parser CSV robusto (aspas, vírgulas internas, CRLF). PURO. */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let i = 0, field = '', row: string[] = [], inQ = false;
  while (i < text.length) {
    const c = text[i];
    if (inQ) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; }
      else field += c;
    } else {
      if (c === '"') inQ = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && text[i + 1] === '\n') i++;
        if (field.length || row.length) { row.push(field); rows.push(row); row = []; field = ''; }
      } else field += c;
    }
    i++;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

export interface RegistryRow { [k: string]: string; }

/** CSV → array de objetos keyed pelo header. */
export function parsePortalRegistryCsv(content: string): RegistryRow[] {
  const rows = parseCsv(content);
  if (rows.length < 2) return [];
  const head = rows[0].map((h) => h.trim());
  return rows.slice(1)
    .filter((r) => r.length >= head.length - 2 && r.some((c) => c && c.trim()))
    .map((r) => { const o: RegistryRow = {}; head.forEach((h, idx) => { o[h] = (r[idx] ?? '').trim(); }); return o; });
}

/** Markdown pipe-table → linhas (fallback p/ PORTAL REGISTRY *.md). PURO. */
export function parsePortalRegistryMarkdown(content: string, _sourceName?: string): RegistryRow[] {
  const out: RegistryRow[] = [];
  const lines = content.split(/\r?\n/);
  let header: string[] | null = null;
  for (const line of lines) {
    const t = line.trim();
    if (!t.startsWith('|')) { header = null; continue; }
    const cells = t.split('|').slice(1, -1).map((c) => c.trim());
    if (/^[-:\s|]+$/.test(t.replace(/\|/g, ''))) continue; // separador ---
    if (!header) { header = cells; continue; }
    if (cells.length === header.length) {
      const o: RegistryRow = {}; header.forEach((h, idx) => { o[h] = cells[idx] ?? ''; }); out.push(o);
    }
  }
  return out;
}

// --- helpers ----------------------------------------------------------------

function slugify(s: string): string {
  return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 48) || 'surface';
}
function isHttps(url: string | null | undefined): boolean {
  return typeof url === 'string' && /^https:\/\//i.test(url.trim());
}

const JOURNEY_MAP: Record<string, string> = {
  login_base: 'login', cobrança: 'billing_query', cobranca: 'billing_query', suporte: 'support',
  sinistro: 'claim', assistência: 'assistance', assistencia: 'assistance', mobile_app: 'mobile_app',
  cotação: 'quote', cotacao: 'quote', multicálculo: 'quote', multicalculo: 'quote', segunda_via: 'document_query',
  status: 'status_query', 'apólice/documentos': 'policy_query', 'apolice/documentos': 'policy_query',
  developer_portal: 'developer_portal', api_catalog: 'api_catalog', emissão: 'issue', emissao: 'issue', other: 'other',
};
export function mapJourneyType(jt: string | null | undefined): string {
  const k = (jt || '').trim().toLowerCase();
  return JOURNEY_MAP[k] ?? (k || 'other');
}

export function mapAuthMethods(authType: string | null | undefined): PortalAuthMethod[] {
  const a = (authType || '').trim().toLowerCase();
  if (a === 'login_password') return ['password'];
  if (a === 'login_password_mfa') return ['password', 'mfa'];
  if (a === 'login_password_captcha') return ['password', 'captcha'];
  if (a === 'oauth2') return ['sso'];
  return [];
}

function challengeFromRegistry(authMethods: PortalAuthMethod[], challengeRaw: string | null | undefined): ChallengeProfile {
  const raw = (challengeRaw || '').toLowerCase();
  const captcha = authMethods.includes('captcha') || /captcha|recaptcha/.test(raw);
  const mfa = authMethods.includes('mfa') || /\bmfa\b|2fa|authenticator/.test(raw);
  const certificate = authMethods.includes('certificate') || /certificad|e-?cnpj|e-?cpf/.test(raw);
  const otp = /\botp\b|one-?time|token sms/.test(raw);
  return { captcha, mfa, certificate, otp, requires_hitl: captcha || mfa || certificate || otp };
}

const OWNER_KINDS = ['insurer', 'provider', 'regulator', 'broker', 'other'];
function ownerKindFor(row: RegistryRow): 'insurer' | 'provider' | 'regulator' | 'broker' | 'other' {
  const et = (row.entity_type || '').toLowerCase();
  const ik = (row.insurer_key || '').toLowerCase();
  if (et && OWNER_KINDS.includes(et)) return et as any;
  if (ik === 'susep' || ik === 'open_insurance') return 'regulator';
  return 'insurer';
}

export type IntakeConfidenceAction = 'seed_active' | 'needs_review' | 'ignored';

/** Regras de confiança: confirmed+https+audiência operacional → seed_active; strong/partial → needs_review; resto → ignored. */
export function classifyPortalSourceConfidence(row: RegistryRow): IntakeConfidenceAction {
  const conf = (row.confidence || '').toLowerCase();
  if (!isHttps(row.canonical_url)) return 'ignored';
  if (conf === 'confirmed') {
    const aud = (row.audience || '').toLowerCase();
    return ['corretor', 'segurado', 'parceiro'].includes(aud) ? 'seed_active' : 'needs_review';
  }
  if (conf === 'strong_evidence' || conf === 'partial_evidence') return 'needs_review';
  return 'ignored';
}

/** Mapeia uma linha de registry → PortalDefinitionRecord global. null se ignorada. */
export function mapRegistryRowToPortalDefinition(row: RegistryRow, now: string): PortalDefinitionRecord | null {
  const action = classifyPortalSourceConfidence(row);
  if (action === 'ignored') return null;
  if (!row.insurer_key || !row.surface_name || !isHttps(row.canonical_url)) return null;

  const authMethods = mapAuthMethods(row.auth_type);
  const challenge = challengeFromRegistry(authMethods, row.challenge_profile);
  const portal_id = `${slugify(row.insurer_key)}__${slugify(row.surface_name)}`;
  const status = action === 'seed_active' ? 'sandbox_ready' : 'needs_review';

  return {
    portal_id,
    label: row.surface_name,
    owner_kind: ownerKindFor(row),
    owner_key: row.insurer_key,
    base_url: row.canonical_url,
    login_url: isHttps(row.launch_url) ? row.launch_url : null,
    supported_journeys: [mapJourneyType(row.journey_type)],
    auth_methods: authMethods,
    challenge_profile: challenge,
    browser_strategy: { primary: 'browserbase_playwright_stagehand', fallback: 'skyvern_lab' },
    status,
    scope: 'global',
    notes: (row.notes || '').slice(0, 400) || null,
    metadata: {
      audience: row.audience || null,
      line_of_business: row.line_of_business || null,
      journey_type: row.journey_type || null,
      url_kind: row.url_kind || null,
      session_profile: row.session_profile || null,
      integration_type: row.integration_type || null,
      public_api_evidence: row.public_api_evidence || null,
      broker_standardization_likelihood: row.broker_standardization_likelihood || null,
      same_for_all_brokers: row.same_for_all_brokers || null,
      confidence: row.confidence || null,
      official_sources: row.official_sources || null,
      checked_at: row.checked_at || null,
      registry_block: row.registry_block || null,
      source_document: row.source_document || null,
      source_type: 'official_research',
    },
    created_at: now,
    updated_at: now,
  };
}

/** Dedupe por portal_id: une jornadas/auth, mantém maior confiança/status, une fontes. PURO. */
export function dedupePortalDefinitions(defs: PortalDefinitionRecord[]): PortalDefinitionRecord[] {
  const rank: Record<string, number> = { sandbox_ready: 2, needs_review: 1, draft: 0, inactive: 0 };
  const byId = new Map<string, PortalDefinitionRecord>();
  for (const d of defs) {
    const prev = byId.get(d.portal_id);
    if (!prev) { byId.set(d.portal_id, { ...d }); continue; }
    const merged: PortalDefinitionRecord = { ...prev };
    merged.supported_journeys = Array.from(new Set([...(prev.supported_journeys || []), ...(d.supported_journeys || [])]));
    merged.auth_methods = Array.from(new Set([...(prev.auth_methods || []), ...(d.auth_methods || [])])) as PortalAuthMethod[];
    merged.challenge_profile = {
      captcha: prev.challenge_profile.captcha || d.challenge_profile.captcha,
      mfa: prev.challenge_profile.mfa || d.challenge_profile.mfa,
      certificate: prev.challenge_profile.certificate || d.challenge_profile.certificate,
      otp: prev.challenge_profile.otp || d.challenge_profile.otp,
      requires_hitl: prev.challenge_profile.requires_hitl || d.challenge_profile.requires_hitl,
    };
    if ((rank[d.status] ?? 0) > (rank[prev.status] ?? 0)) merged.status = d.status;
    // une official_sources nos metadados
    const ps = String(prev.metadata?.official_sources ?? '');
    const ds = String(d.metadata?.official_sources ?? '');
    merged.metadata = { ...prev.metadata, official_sources: Array.from(new Set([...ps.split(/[;\n]/), ...ds.split(/[;\n]/)].map((s) => s.trim()).filter(Boolean))).join(' ; ') };
    byId.set(d.portal_id, merged);
  }
  return Array.from(byId.values());
}

export interface CatalogBuildStats {
  source_rows: number;
  mapped: number;
  seed_active: number;
  needs_review: number;
  ignored: number;
  insurers: string[];
  deduped: number;
}

export interface CatalogBuildResult {
  definitions: PortalDefinitionRecord[];
  stats: CatalogBuildStats;
}

/** Pipeline completo: linhas → definições globais dedupadas + estatísticas. PURO. */
export function buildGlobalPortalCatalogFromRows(rows: RegistryRow[], now = new Date().toISOString()): CatalogBuildResult {
  let seed_active = 0, needs_review = 0, ignored = 0;
  const defs: PortalDefinitionRecord[] = [];
  for (const row of rows) {
    const action = classifyPortalSourceConfidence(row);
    if (action === 'ignored') { ignored++; continue; }
    if (action === 'seed_active') seed_active++; else needs_review++;
    const def = mapRegistryRowToPortalDefinition(row, now);
    if (def) defs.push(def); else ignored++;
  }
  const deduped = dedupePortalDefinitions(defs);
  const insurers = Array.from(new Set(deduped.map((d) => d.owner_key))).sort();
  return {
    definitions: deduped,
    stats: { source_rows: rows.length, mapped: defs.length, seed_active, needs_review, ignored, insurers, deduped: deduped.length },
  };
}
