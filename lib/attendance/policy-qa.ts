// Policy Q&A & Reasoning Layer (42Q0) — PURO, sem I/O.
//
// Permite o segurado fazer perguntas livres (cobertura, status da apólice,
// assistência, andamento) e receber uma resposta INTELIGENTE com LIMITES. O
// runtime determinístico continua a autoridade de estado; aqui só classificamos
// a pergunta e produzimos uma resposta segura a partir do Evidence Pack /
// Coverage Readiness (fonte de verdade operacional). NUNCA inventa cobertura,
// NUNCA muda estado, NUNCA aciona side effects.

export type AttendanceQuestionCategory =
  | 'policy_coverage_question'
  | 'policy_status_question'
  | 'assistance_question'
  | 'process_status_question'
  | 'dispatch_status_question'
  | 'clarification_question'
  | 'media_offer_question'
  | 'off_topic_but_answerable'
  | 'customer_frustration'
  | 'new_issue_or_intent_shift'
  | 'slot_answer'
  | 'unknown';

const INTERROGATIVE_RE = /^\s*(o que|que\b|qual|quais|quem|onde|quando|por que|por qu[eê]|porque|como|pra que|para que|tem como|posso|d[áa] pra|consigo|vai|v[ãa]o|ser[áa])/i;
const COVERAGE_RE = /\b(cobertura|cobre|coberto|tenho cobertura|tenho direito|tem direito|d[áa] direito|est[áa] coberto|inclui|atende|paga(r)?)\b/i;
const STATUS_RE = /\b(ap[óo]lice.*(ativa|vigente|v[áa]lida|valendo|cancelad|vencid)|est[áa] (ativa|vigente|valendo)|minha ap[óo]lice|vig[êe]ncia|t[áa] valendo)\b/i;
const DISPATCH_RE = /\b(previs[aã]o|prazo|quando.*(vem|chega|atende|v[ãa]o)|j[áa] chamaram|prestador|protocolo|t[ée]cnico|quando.*(t[ée]cnico|profissional)|j[áa] foi acionad)\b/i;
const PROCESS_RE = /\b(e agora|pr[óo]ximo passo|o que falta|o que (preciso|falta|vem|fa[çc]o)|como (funciona|fica) (agora|daqui)|o que acontece)\b/i;
const WHY_RE = /\b(por que|por qu[eê]|porque|pra que|para que|por qual motivo|como assim)\b/i;
const ASSISTANCE_RE = /\b(assist[êe]ncia|voc[êe]s mandam|enviam algu[ée]m|mandam (eletricista|t[ée]cnico|profissional)|como funciona a assist)\b/i;
const HUMAN_REQ_RE = /\b(falar com (um |uma )?(humano|atendente|pessoa|algu[ée]m)|atendente humano|pessoa de verdade|quero (um )?humano|me transfere|transferir para)\b/i;
const MEDIA_OFFER_RE = /\b(posso (te )?(mandar|enviar)|pode (mandar|enviar)|quero (mandar|enviar)|vou (mandar|enviar))\b.*\b(foto|imagem|[áa]udio|v[íi]deo|documento|pdf|print|comprovante|localiza[çc][ãa]o)\b/i;
const FRUSTRATION_RE = /(j[aá] (disse|falei|informei|expliquei)|de novo|outra vez|quantas vezes|que saco|\baff+\b|pelo amor|t[oô] cansad|cansei|absurdo|ridiculo|rid[íi]culo)/i;
const NEW_ISSUE_RE = /\b(na verdade.*(outro|tamb[ée]m)|tamb[ée]m tem|outro problema|al[ée]m disso|esqueci de (falar|dizer))\b/i;
const DOMAIN_RE = /(luz|energia|el[eé]tric|tomada|disjuntor|chuveiro|fia[çc]|vazament|encan|cano|ap[oó]lice|cobertura|seguro|assist|prestador|seguradora|eletricista|sinistro)/i;

function isQuestionish(m: string): boolean {
  return m.includes('?') || INTERROGATIVE_RE.test(m.trim());
}

/**
 * Classifica a pergunta livre do segurado. Conservador: só retorna categoria de
 * Q&A quando há sinal forte; senão `slot_answer` (preserva o fluxo já testado).
 */
export function classifyAttendanceQuestion(
  message: string,
  _caseContext?: unknown,
): { category: AttendanceQuestionCategory; signals: string[] } {
  const m = (message || '').trim();
  if (!m) return { category: 'unknown', signals: ['empty'] };
  const lower = m.toLowerCase();

  if (HUMAN_REQ_RE.test(lower)) return { category: 'customer_frustration', signals: ['human_request'] };
  if (MEDIA_OFFER_RE.test(lower)) return { category: 'media_offer_question', signals: ['media_offer'] };
  if (FRUSTRATION_RE.test(lower)) return { category: 'customer_frustration', signals: ['frustration'] };
  if (NEW_ISSUE_RE.test(lower)) return { category: 'new_issue_or_intent_shift', signals: ['new_issue'] };

  const q = isQuestionish(lower);
  // "por que ..." é clarificação mesmo quando menciona cobertura/apólice.
  if (WHY_RE.test(lower) && q && DOMAIN_RE.test(lower)) return { category: 'clarification_question', signals: ['why'] };
  if (COVERAGE_RE.test(lower) && (q || /^(cobre|cobertura)/i.test(lower))) return { category: 'policy_coverage_question', signals: ['coverage'] };
  if (STATUS_RE.test(lower)) return { category: 'policy_status_question', signals: ['status'] };
  if (DISPATCH_RE.test(lower) && q) return { category: 'dispatch_status_question', signals: ['dispatch'] };
  if (ASSISTANCE_RE.test(lower) && q) return { category: 'assistance_question', signals: ['assistance'] };
  if (PROCESS_RE.test(lower)) return { category: 'process_status_question', signals: ['process'] };
  if (q && !DOMAIN_RE.test(lower)) return { category: 'off_topic_but_answerable', signals: ['off_topic'] };
  return { category: 'slot_answer', signals: ['default'] };
}

/** É uma pergunta livre que o Q&A deve responder (vs. resposta de slot)? */
export function isAnswerableQuestion(category: AttendanceQuestionCategory): boolean {
  return (
    category === 'policy_coverage_question' ||
    category === 'policy_status_question' ||
    category === 'assistance_question' ||
    category === 'process_status_question' ||
    category === 'dispatch_status_question' ||
    category === 'clarification_question' ||
    category === 'media_offer_question'
  );
}

export interface PolicyQAContext {
  intent: string | null;
  corridor: string | null;
  subcorridor: string | null;
  insurer: string | null;
  product: string | null;
  policy_status: string | null;
  active_now: boolean | null;
  valid_to: string | null;
  coverage_confirmed: boolean;
  coverage_summary: string | null;
  confidence: string | null;
  human_required: boolean;
  cancelled: boolean;
  coverage_readiness_state: string | null;
  dispatch_state: string | null;
  assistance_signals: Record<string, unknown> | null;
  gaps: string[];
  pending_question: string | null;
  has_policy: boolean;
  /** Conhecimento geral sanitizado (42R0) — explica conceitos, NUNCA confirma cobertura. */
  knowledge: Array<{ title: string; summary: string; provenance: string; scope: string }>;
  allowed: string[];
  forbidden: string[];
}

function safeStr(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v.trim() : null;
}
function triBool(v: unknown): boolean | null {
  return v === true ? true : v === false ? false : null;
}

/** Contexto SANITIZADO para Q&A (sem CPF/telefone/nome/endereço/token/payload). */
export function buildPolicyQAContext(
  caseRow: any,
  opts: { pendingQuestion?: string | null; knowledge?: Array<{ title: string; summary: string; provenance: string; scope: string }> } = {},
): PolicyQAContext {
  const md = caseRow?.metadata && typeof caseRow.metadata === 'object' ? caseRow.metadata : {};
  const snap = caseRow?.policy_snapshot && typeof caseRow.policy_snapshot === 'object' ? caseRow.policy_snapshot : {};
  const ce = caseRow?.coverage_evidence && typeof caseRow.coverage_evidence === 'object' ? caseRow.coverage_evidence : {};
  const cr = md.coverage_readiness && typeof md.coverage_readiness === 'object' ? md.coverage_readiness : {};
  const pic = md.policy_interpretation_context && typeof md.policy_interpretation_context === 'object' ? md.policy_interpretation_context : {};
  const dr = md.dispatch_readiness && typeof md.dispatch_readiness === 'object' ? md.dispatch_readiness : {};
  const pack = md.policy_evidence_pack && typeof md.policy_evidence_pack === 'object' ? md.policy_evidence_pack : {};

  const hasPolicy = Boolean(
    caseRow?.policy_source === 'connector' ||
      (typeof caseRow?.verification_status === 'string' && caseRow.verification_status.startsWith('verified')) ||
      snap.policy_ref || snap.masked_policy_number,
  );

  const gaps: string[] = Array.isArray(pic.gaps)
    ? pic.gaps.filter((g: unknown): g is string => typeof g === 'string').slice(0, 6)
    : Array.isArray(ce.limitations)
      ? ce.limitations.filter((g: unknown): g is string => typeof g === 'string').slice(0, 6)
      : [];

  return {
    intent: safeStr(caseRow?.intent),
    corridor: safeStr(caseRow?.selected_corridor_key),
    subcorridor: safeStr(caseRow?.selected_subcorridor_key),
    insurer: safeStr(snap.insurer_key) || safeStr(pack.insurer_detected) || safeStr(caseRow?.insurer_key),
    product: safeStr(snap.product) || safeStr(pack.product_detected),
    policy_status: safeStr(snap.policy_status) || safeStr(pack.policy_status),
    active_now: triBool(snap.active_now ?? pack.active_now),
    valid_to: safeStr(snap.valid_to ?? pack.valid_to),
    coverage_confirmed: pic.coverage_confirmed === true,
    coverage_summary: safeStr(ce.coverage_summary),
    confidence: safeStr(ce.confidence) || safeStr(pack.confidence),
    human_required: cr.human_required === true || ce.human_required === true,
    cancelled: snap.cancelled === true || pack.cancelled === true,
    coverage_readiness_state: safeStr(cr.state),
    dispatch_state: safeStr(dr.packet_state),
    assistance_signals: pack.assistance_signals && typeof pack.assistance_signals === 'object' ? pack.assistance_signals : null,
    gaps,
    pending_question: safeStr(opts.pendingQuestion),
    has_policy: hasPolicy,
    knowledge: Array.isArray(opts.knowledge) ? opts.knowledge.slice(0, 3) : [],
    allowed: [
      'explicar e resumir o que já consta nas evidências',
      'diferenciar apólice localizada de cobertura confirmada',
      'orientar o próximo passo seguro',
      'responder de forma humana e curta',
    ],
    forbidden: [
      'confirmar cobertura específica sem evidência',
      'prometer prestador/protocolo/prazo sem acionamento real',
      'mudar o estado do atendimento',
      'pedir dado já coletado',
      'expor CPF/telefone/endereço completo/token',
    ],
  };
}

function insurerProductLabel(ctx: PolicyQAContext): string {
  const parts = [ctx.insurer, ctx.product].filter(Boolean);
  return parts.length ? `apólice ${parts.join(' ')}` : 'apólice';
}

/**
 * Resposta DETERMINÍSTICA e segura por categoria. É a base (autoridade); o LLM,
 * quando habilitado, só reescreve/enriquece em cima disto, sem inventar.
 */
export function answerPolicyQuestionDeterministic(
  category: AttendanceQuestionCategory,
  ctx: PolicyQAContext,
): { answer: string; requires_handoff: boolean } {
  const label = insurerProductLabel(ctx);

  if (category === 'customer_frustration') {
    return {
      answer:
        'Entendo, e peço desculpa pela demora. Estou aqui para resolver com você. Se preferir, posso encaminhar para um atendente humano; senão, sigo cuidando do seu atendimento agora mesmo.',
      requires_handoff: true,
    };
  }

  if (category === 'policy_status_question') {
    if (!ctx.has_policy) return { answer: 'Ainda estou localizando e validando a sua apólice. Assim que eu confirmar, te aviso.', requires_handoff: false };
    if (ctx.cancelled) return { answer: `Encontrei a ${label}, mas ela consta como cancelada. Por isso não consigo seguir com acionamento; vou deixar isso para a equipe verificar.`, requires_handoff: true };
    if (ctx.active_now === true) return { answer: `Sim, localizei uma ${label} vigente na InfoCap${ctx.valid_to ? `, com validade até ${ctx.valid_to}` : ''}.`, requires_handoff: false };
    if (ctx.active_now === false) return { answer: `Localizei a ${label}, mas ela parece estar fora do período de vigência. Vou deixar a equipe confirmar isso antes de seguir.`, requires_handoff: true };
    return { answer: `Localizei a ${label}, mas ainda preciso confirmar a vigência antes de te dar certeza.`, requires_handoff: false };
  }

  if (category === 'policy_coverage_question') {
    if (!ctx.has_policy) return { answer: 'Antes de falar de cobertura, preciso localizar a sua apólice. Assim que localizar, verifico isso com cuidado.', requires_handoff: false };
    if (ctx.cancelled || ctx.active_now === false) return { answer: `Encontrei a ${label}, mas ela não está apta (cancelada ou fora de vigência), então não posso confirmar cobertura. Vou encaminhar para validação humana.`, requires_handoff: true };
    if (ctx.coverage_confirmed) return { answer: `Sim — encontrei evidência de cobertura na ${label}${ctx.valid_to ? ` (vigente até ${ctx.valid_to})` : ''}. Posso seguir com os dados para preparar o acionamento.`, requires_handoff: false };
    return {
      answer: `Localizei uma ${label}${ctx.active_now === true ? ' vigente' : ''} na InfoCap, mas o documento não trouxe os itens de cobertura detalhados para eu afirmar isso automaticamente. Para não te passar informação errada, vou deixar essa cobertura validada pela equipe antes de qualquer acionamento.`,
      requires_handoff: false,
    };
  }

  if (category === 'clarification_question') {
    return {
      answer:
        'Porque eu localizei a apólice, mas os detalhes de cobertura específica não vieram claros no documento. Para não te passar uma informação errada, a cobertura precisa ser validada antes do acionamento.',
      requires_handoff: false,
    };
  }

  if (category === 'media_offer_question') {
    return {
      answer:
        'Pode sim! Você pode me mandar foto, áudio, documento ou a localização — eles ajudam como evidência do atendimento. Só lembrando que a cobertura ainda depende da apólice e da validação.',
      requires_handoff: false,
    };
  }

  if (category === 'dispatch_status_question') {
    return {
      answer:
        'Ainda não tenho protocolo nem prestador confirmado. Primeiro preciso concluir a validação da cobertura e preparar o acionamento; assim que avançar, te passo o status.',
      requires_handoff: false,
    };
  }

  if (category === 'assistance_question') {
    return {
      answer:
        'A assistência funciona assim: eu confirmo a apólice e a cobertura, reúno os dados do atendimento e preparo o acionamento para a equipe. Não aciono prestador por conta própria sem essa validação.',
      requires_handoff: false,
    };
  }

  if (category === 'process_status_question') {
    if (ctx.dispatch_state === 'ready_for_human_approval') return { answer: 'O pacote do seu atendimento já está montado e aguardando a aprovação da equipe para o acionamento.', requires_handoff: false };
    if (ctx.dispatch_state === 'hitl_required') return { answer: 'Já organizei o seu atendimento; agora a equipe precisa validar a cobertura antes de acionar, para evitar qualquer erro.', requires_handoff: false };
    if (!ctx.has_policy) return { answer: 'O próximo passo é localizar e validar a sua apólice. Em seguida coleto os dados e preparo o acionamento.', requires_handoff: false };
    return { answer: 'Estou reunindo os dados do seu atendimento. Assim que tiver tudo, preparo o acionamento para a equipe revisar.', requires_handoff: false };
  }

  // off_topic_but_answerable / fallback
  return {
    answer: 'Posso te ajudar com isso. Sobre o seu atendimento, sigo cuidando da sua apólice e dos próximos passos.',
    requires_handoff: false,
  };
}

/** Resumo seguro para diagnostics (sem PII). */
export function safePolicyQaSummary(category: AttendanceQuestionCategory, ctx: PolicyQAContext, llmUsed: boolean): Record<string, unknown> {
  return {
    category,
    coverage_confirmed: ctx.coverage_confirmed,
    has_policy: ctx.has_policy,
    coverage_readiness_state: ctx.coverage_readiness_state,
    dispatch_state: ctx.dispatch_state,
    llm_used: llmUsed,
    at: new Date().toISOString(),
  };
}
