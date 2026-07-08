type PortalJobRow = {
  id: string;
  company_id?: string | null;
  portal_key?: string | null;
  journey?: string | null;
  status?: string | null;
  evidence?: Record<string, any> | null;
  screenshots?: string[] | null;
  attempts?: number | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
};

const SAFE_EVIDENCE_KEYS = new Set([
  'message',
  'url',
  'hitl',
  'portal',
  'logged_in',
  'session_reused',
  'session_saved',
  'session_storage_captured',
  'session_storage_restored',
  'login_fields_found',
]);

function pickSafeEvidence(evidence: Record<string, any> | null | undefined): Record<string, any> {
  const out: Record<string, any> = {};
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)) return out;
  for (const [key, value] of Object.entries(evidence)) {
    if (SAFE_EVIDENCE_KEYS.has(key)) out[key] = value;
  }
  return out;
}

export function sanitizePortalJob(row: PortalJobRow, portalNames: Record<string, string> = {}) {
  const portalKey = String(row.portal_key || '');
  const evidence = pickSafeEvidence(row.evidence);
  return {
    id: row.id,
    portal_key: portalKey,
    portal_name: portalNames[portalKey] || portalKey,
    journey: row.journey || '',
    status: row.status || '',
    message: String(evidence.message || row.error || ''),
    evidence,
    screenshot: Array.isArray(row.screenshots) && row.screenshots.length ? row.screenshots[0] : null,
    attempts: Number(row.attempts || 0),
    created_at: row.created_at || null,
    started_at: row.started_at || null,
    finished_at: row.finished_at || null,
    error: row.error || null,
  };
}

export function isRetryableHitlJob(row: PortalJobRow | null | undefined, companyId: string): boolean {
  if (!row) return false;
  return row.status === 'needs_human' && row.company_id === companyId;
}

export function buildPortalJobRetryPatch(nowIso: string, evidence: Record<string, any> | null | undefined = {}) {
  const current = evidence && typeof evidence === 'object' && !Array.isArray(evidence) ? evidence : {};
  const hitl = current.hitl && typeof current.hitl === 'object' && !Array.isArray(current.hitl) ? current.hitl : {};
  return {
    status: 'queued',
    error: null,
    started_at: null,
    finished_at: null,
    evidence: {
      ...current,
      hitl: {
        ...hitl,
        retry_requested_at: nowIso,
        resume_mode: hitl.resume_mode || 'requeue_after_human',
      },
    },
  };
}
