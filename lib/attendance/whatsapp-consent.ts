// 42X5B — consentimento/opt-in de WhatsApp. SELF-CONTAINED (puro, testável).
// Sem tabela nova: o ConsentRecord é persistido em estrutura existente
// (attendance_cases.metadata.consent OU tenant_connections.connection_config.
// whatsapp_consents[] por hash de telefone). Aqui só a LÓGICA pura de decisão.
//
// Regras:
//  - opt_out bloqueia QUALQUER envio imediatamente.
//  - resposta a inbound dentro da janela de sessão é permitida (consentimento
//    implícito de atendimento iniciado pelo segurado).
//  - envio PROATIVO/campanha exige opt-in explícito.

export type ConsentStatus = 'opted_in' | 'opted_out' | 'session' | 'unknown';

export interface ConsentRecord {
  status: ConsentStatus;
  source?: string | null; // inbound | form | import | operator
  at?: string | null;
  scope?: string | null; // attendance | campaign | all
}

export interface ConsentContext {
  record: ConsentRecord | null;
  is_proactive: boolean;
  last_inbound_at?: string | null; // ISO da última msg do segurado
  now?: number;
  session_window_ms?: number; // janela de atendimento (default 24h)
}

export interface ConsentDecision {
  consent_ok: boolean;
  reason: string;
}

const DEFAULT_WINDOW = 24 * 60 * 60 * 1000;

export function isWithinSessionWindow(ctx: ConsentContext): boolean {
  if (!ctx.last_inbound_at) return false;
  const now = ctx.now ?? Date.now();
  const win = ctx.session_window_ms ?? DEFAULT_WINDOW;
  const t = Date.parse(ctx.last_inbound_at);
  return Number.isFinite(t) && now - t <= win;
}

export function evaluateConsent(ctx: ConsentContext): ConsentDecision {
  const r = ctx.record;
  if (r?.status === 'opted_out') return { consent_ok: false, reason: 'opted_out' };

  if (!ctx.is_proactive) {
    // Resposta a atendimento iniciado pelo segurado: permitida dentro da janela.
    if (isWithinSessionWindow(ctx)) return { consent_ok: true, reason: 'session_reply' };
    if (r?.status === 'opted_in') return { consent_ok: true, reason: 'opted_in' };
    return { consent_ok: false, reason: 'no_session_no_opt_in' };
  }

  // Proativo/campanha: exige opt-in explícito.
  if (r?.status === 'opted_in') return { consent_ok: true, reason: 'opted_in' };
  return { consent_ok: false, reason: 'proactive_requires_opt_in' };
}
