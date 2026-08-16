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
  // SPEC-073: o operador precisa VER por que o retry esta bloqueado. Sem estas
  // chaves a tela so desabilitaria o botao, e um botao cinza sem explicacao faz
  // a pessoa procurar outro caminho para fazer a mesma coisa errada.
  'critical_effect',
  'protocolo',
  'runtime',
  'execution',
  'security_stop',
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

// ---------------------------------------------------------------------------
// SPEC-073 Bloco B — o botao de retentar nao pode reabrir pedido que ja existe.
//
// 🔴 Medido em 16/08/2026: `isRetryableHitlJob` conferia apenas
// `status === 'needs_human'` e a corretora. Só que o caminho adaptativo produz
// `needs_human` CARREGANDO protocolo -- e para isso existe
// `aviso_de_pedido_aberto()`, que prefixa a mensagem com "o atendimento JA FOI
// ABERTO, NAO reexecute". Ou seja: a evidencia gritava, e o botao nao lia.
//
// Clicar retentar num job desses recomeca do passo 1 e cria um SEGUNDO
// atendimento na seguradora. O indice unico parcial do banco nao salva: ele
// impede INSERT novo, nao o requeue da mesma linha.
//
// Esta funcao ESPELHA `guardrails.pode_repetir_com_seguranca()` do worker
// Python. Duas linguagens, uma regra -- e o teste `[dashboard espelha o worker]`
// compara as duas contra os mesmos casos, para a copia nao envelhecer sozinha.
// ---------------------------------------------------------------------------
const FASES_INCERTAS = new Set(['armed', 'submitted', 'unknown']);

export function temProvaDeEfeito(evidence: Record<string, any> | null | undefined): boolean {
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)) return false;
  if (String(evidence.protocolo || '').trim()) return true;
  const ef = evidence.critical_effect;
  if (ef && typeof ef === 'object' && !Array.isArray(ef)) {
    if (String(ef.phase || '').toLowerCase() === 'confirmed') return true;
    if (String(ef.receipt || '').trim()) return true;
  }
  return false;
}

export function podeRepetirComSeguranca(evidence: Record<string, any> | null | undefined): boolean {
  if (temProvaDeEfeito(evidence)) return false;
  const ef = evidence && typeof evidence === 'object' && !Array.isArray(evidence)
    ? evidence.critical_effect
    : null;
  const fase = ef && typeof ef === 'object' ? String(ef.phase || '').toLowerCase() : '';
  if (!fase) return true;                 // nunca armou efeito: repetir e seguro
  return !FASES_INCERTAS.has(fase);
}

export function motivoDeBloqueio(evidence: Record<string, any> | null | undefined): string {
  if (temProvaDeEfeito(evidence)) {
    return 'O atendimento ja foi aberto neste job (protocolo registrado). '
      + 'Retentar criaria um segundo pedido no portal — continue pelo atendimento existente.';
  }
  const ef = evidence && typeof evidence === 'object' && !Array.isArray(evidence)
    ? evidence.critical_effect
    : null;
  const fase = ef && typeof ef === 'object' ? String(ef.phase || '').toLowerCase() : '';
  if (FASES_INCERTAS.has(fase)) {
    return `A operacao pode ter acontecido no portal (fase=${fase}). `
      + 'Consulte o atendimento antes de qualquer nova tentativa — nao reexecute.';
  }
  return '';
}

export function isRetryableHitlJob(row: PortalJobRow | null | undefined, companyId: string): boolean {
  if (!row) return false;
  if (row.status !== 'needs_human' || row.company_id !== companyId) return false;
  return podeRepetirComSeguranca(row.evidence);
}

/** O porque da recusa, para a tela explicar em vez de so desabilitar o botao. */
export function motivoDeRecusaDeRetry(
  row: PortalJobRow | null | undefined,
  companyId: string,
): string {
  if (!row) return 'job inexistente';
  if (row.company_id !== companyId) return 'job de outra corretora';
  if (row.status !== 'needs_human') return 'somente job em needs_human pode ser retentado';
  return motivoDeBloqueio(row.evidence);
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
