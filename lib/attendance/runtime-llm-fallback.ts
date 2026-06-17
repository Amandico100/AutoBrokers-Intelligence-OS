// Runtime LLM Fallback (42B5L-FE).
//
// Integração server-side, OPCIONAL e gated por env, com o endpoint backend
// stateless/guardrailado `POST /attendance/agent-reply` (42B5L-BE). Usado apenas
// para mensagens conversacionais seguras (off-topic / clarificação), nunca para
// risco/CPF/cobertura/acionamento/mudança de estado. Em qualquer falha/timeout/
// desabilitado, o runtime usa a resposta determinística do 42B5K.
import type { MessageRoute } from './runtime-message-router';

const FALLBACK_KINDS = new Set<string>(['off_topic_general_question', 'clarification_question']);
const NON_RUNTIME_STATUSES = new Set(['handoff', 'closed', 'cancelled']);
const HIGH_RISK_RE = /(faísca|faisca|fuma[çc]a|cheiro de queim|queimad|choque|fogo|inc[eê]ndio|curto)/i;
const TIMEOUT_MS = 10_000;
const MAX_REPLY = 1200;
const TRUSTED_VERIFICATION = new Set(['verified_by_human', 'verified_by_connector', 'verified_by_document']);

export function isAttendanceFallbackEnabled(): boolean {
  return process.env.ATTENDANCE_LLM_FALLBACK_ENABLED === 'true';
}

export function isFallbackKind(kind: string): boolean {
  return FALLBACK_KINDS.has(kind);
}

function backendUrl(): string {
  return (
    process.env.ATTENDANCE_AGENT_REPLY_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.BACKEND_URL ||
    'http://localhost:8000'
  );
}

/** Mascara dígitos longos (CPF/CNPJ/apólice) e limita tamanho. */
export function sanitizeAttendanceFallbackText(text?: string | null): string {
  const s = (text ?? '').toString();
  const masked = s.replace(/\d[\d.\-/\s]{9,}\d/g, '[omitido]');
  return masked.length > MAX_REPLY ? masked.slice(0, MAX_REPLY) : masked;
}

/** Elegibilidade segura para usar o fallback LLM. Conservador por padrão. */
export function shouldUseLlmFallback(
  route: MessageRoute,
  ctx: { message: string; caseStatus?: string | null; agentId?: string | null },
): boolean {
  if (!isAttendanceFallbackEnabled()) return false;
  if (!FALLBACK_KINDS.has(route.kind)) return false;
  if (!ctx.agentId) return false;
  if (ctx.caseStatus && NON_RUNTIME_STATUSES.has(ctx.caseStatus)) return false;
  const msg = ctx.message || '';
  if (HIGH_RISK_RE.test(msg)) return false; // nunca LLM em risco alto/possível
  if (msg.replace(/\D/g, '').length >= 8) return false; // possível CPF/CNPJ/documento
  return true;
}

export function buildAttendanceFallbackGuardrails() {
  return {
    audience: 'insured_external',
    must: [
      'responder curto e humano, estilo WhatsApp',
      'se responder algo fora do atendimento, voltar ao próximo passo do atendimento',
      'não gerar textão',
    ],
    never: [
      'confirmar cobertura sem evidência',
      'dizer que acionou seguradora/prestador',
      'prometer prazo ou garantia',
      'pedir dado desnecessário',
      'expor CPF, macro_state, slots ou diagnostics',
      'inventar apólice',
      'usar tom de assistente interno da corretora',
    ],
  };
}

/** Contexto SANITIZADO (sem CPF/insured_document_ref/policy_snapshot/diagnostics/slots). */
export function buildAttendanceFallbackContext(
  caseRow: any,
  _corridorRun: any,
  recentMessages: any[],
  currentQuestion: string | null,
  knowledge?: string[],
) {
  const turns = (Array.isArray(recentMessages) ? recentMessages : [])
    .slice(0, 6)
    .reverse()
    .map((m: any) => ({
      role: m?.role === 'assistant' ? 'assistant' : 'user',
      content: sanitizeAttendanceFallbackText(m?.content),
    }))
    .filter((t) => t.content);

  const coverage = caseRow?.coverage_evidence;
  const coverageSummary =
    coverage && typeof coverage === 'object' && typeof coverage.coverage_summary === 'string'
      ? sanitizeAttendanceFallbackText(coverage.coverage_summary)
      : null;

  return {
    case_summary: sanitizeAttendanceFallbackText(caseRow?.summary) || null,
    active_question: currentQuestion ? sanitizeAttendanceFallbackText(currentQuestion) : null,
    next_step: sanitizeAttendanceFallbackText(caseRow?.next_step) || null,
    macro_state: caseRow?.metadata?.attendance_macro_state ?? null,
    status: caseRow?.status ?? null,
    risk_level: caseRow?.risk_level ?? null,
    policy_verified:
      typeof caseRow?.verification_status === 'string' && TRUSTED_VERIFICATION.has(caseRow.verification_status),
    coverage_summary: coverageSummary,
    recent_turns: turns,
    // 42R0: conhecimento geral (conceitos), já sanitizado. NUNCA confirma cobertura.
    knowledge: Array.isArray(knowledge)
      ? knowledge.map((k) => sanitizeAttendanceFallbackText(k)).filter(Boolean).slice(0, 3)
      : undefined,
  };
}

export async function requestAttendanceFallback(payload: {
  company_id: string;
  agent_id: string;
  message: string;
  context: any;
  guardrails: any;
}): Promise<{ ok: boolean; reply?: string; error_code?: string }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${backendUrl()}/attendance/agent-reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!res.ok) {
      let code = `http_${res.status}`;
      try {
        const j = await res.json();
        if (j?.error) code = j.error;
        else if (j?.detail?.error) code = j.detail.error;
      } catch {
        /* ignore */
      }
      return { ok: false, error_code: code };
    }
    const data = await res.json();
    if (data?.ok && typeof data.reply === 'string' && data.reply.trim()) {
      return { ok: true, reply: sanitizeAttendanceFallbackText(data.reply) };
    }
    return { ok: false, error_code: data?.error || 'no_reply' };
  } catch (e: any) {
    clearTimeout(timeout);
    return { ok: false, error_code: e?.name === 'AbortError' ? 'timeout' : 'fetch_error' };
  }
}

export interface LlmFallbackOutcome {
  used: boolean;
  reply?: string;
  diag: Record<string, unknown>;
}

/** Tenta o fallback LLM; sempre retorna um diag seguro (sem PII/prompt/contexto bruto). */
export async function attemptAttendanceLlmFallback(input: {
  route: MessageRoute;
  message: string;
  companyId: string;
  agentId: string | null;
  caseRow: any;
  corridorRun: any;
  recentMessages: any[];
  currentQuestion: string | null;
  knowledge?: string[];
}): Promise<LlmFallbackOutcome> {
  const at = new Date().toISOString();
  if (!shouldUseLlmFallback(input.route, { message: input.message, caseStatus: input.caseRow?.status, agentId: input.agentId })) {
    return {
      used: false,
      diag: { attempted: false, used: false, reason: isAttendanceFallbackEnabled() ? 'ineligible' : 'disabled', safe: true, at },
    };
  }
  const context = buildAttendanceFallbackContext(input.caseRow, input.corridorRun, input.recentMessages, input.currentQuestion, input.knowledge);
  const guardrails = buildAttendanceFallbackGuardrails();
  const result = await requestAttendanceFallback({
    company_id: input.companyId,
    agent_id: input.agentId as string,
    message: sanitizeAttendanceFallbackText(input.message),
    context,
    guardrails,
  });
  if (result.ok && result.reply) {
    return { used: true, reply: result.reply, diag: { attempted: true, used: true, reason: input.route.kind, safe: true, at } };
  }
  return {
    used: false,
    diag: { attempted: true, used: false, reason: input.route.kind, error_code: result.error_code, safe: true, at },
  };
}
