// Corridor Runtime Step Engine (determinístico, server-side, channel-agnostic).
//
// Não envia WhatsApp, não cria dispatch_packet, não cria approval_request,
// não aciona seguradora, não chama portal/InfoCap, não confirma cobertura.
// É um motor de PASSO: dado o estado de slots de um corredor, escolhe o próximo
// dado necessário e gera UMA pergunta humana. Futuramente o Attendance Agent/Smith
// poderá chamá-lo como ferramenta. Sem LLM solto, sem motor paralelo.
import { normalizeSlots } from './handoff-dossier';

export const RUNTIME_ENGINE = 'corridor_runtime_step_v1';

// Prioridade segura para Allianz Residencial / Eletricista MVP:
// risco físico antes de dados administrativos; apólice/evidência antes de acionamento.
export const ELECTRICIAN_SLOT_PRIORITY = [
  'risk_indicators',
  'affected_area',
  'electrical_issue_type',
  'property_address_confirmed',
  'policy_evidence_status',
] as const;

export type RuntimeStepStatus = 'question_generated' | 'no_missing_slots' | 'case_not_runtime_editable';

export interface RuntimeStepResult {
  selectedSlot: string | null;
  question: string | null;
  stepStatus: RuntimeStepStatus;
  externalActionAllowed: false;
  nextStep: string;
  /** Novo status para attendance_cases, ou null para manter o atual. */
  caseStatusUpdate: string | null;
  /** Nova fase para corridor_runs, ou null para manter a atual. */
  runPhaseUpdate: string | null;
  safetyNotes: string[];
}

// Mensagem de conclusão quando não há mais slot a coletar.
const COMPLETE_NEXT_STEP =
  'Dados mínimos coletados. Próximo passo: validar apólice/evidência antes de preparar acionamento.';

/** Considera um valor de slot como "preenchido". `false` é válido; vazio/objeto vazio não. */
export function isSlotFilled(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (typeof value === 'boolean') return true;
  if (typeof value === 'number') return true;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0;
  return true;
}

/** Próximo slot prioritário ainda não preenchido (ou null se todos preenchidos). */
export function selectNextSlot(
  filled: Record<string, unknown>,
  priority: readonly string[] = ELECTRICIAN_SLOT_PRIORITY,
): string | null {
  for (const key of priority) {
    if (!isSlotFilled(filled[key])) return key;
  }
  return null;
}

const ELECTRICAL_HINT_RE = /(luz|energia|disjuntor|tomada|curto|fios?|fia[çc][aã]o|el[eé]tric|chuveiro|apag[ãa]|sem força)/i;

/** Pergunta humanizada por slot, com leve contextualização a partir de problem_description. */
export function questionForSlot(slot: string, filled: Record<string, unknown>): string {
  switch (slot) {
    case 'risk_indicators': {
      // Contexto elétrico reforça a abertura, mas a pergunta de segurança é a mesma.
      const desc = typeof filled.problem_description === 'string' ? filled.problem_description : '';
      const electrical = ELECTRICAL_HINT_RE.test(desc);
      const opener = electrical ? 'Entendi' : 'Obrigada por explicar';
      return `${opener}. Antes de seguir, preciso só confirmar uma coisa para sua segurança: tem cheiro de queimado, faísca, fumaça ou algum risco imediato aí?`;
    }
    case 'affected_area':
      return 'Perfeito. Em qual área da casa isso está acontecendo? Por exemplo: cozinha, sala, quarto, área externa ou a casa toda.';
    case 'electrical_issue_type':
      return 'Certo. O que exatamente aconteceu: ficou sem energia, o disjuntor está desarmando, alguma tomada parou ou é outro problema elétrico?';
    case 'property_address_confirmed':
      return 'Para deixar o atendimento encaminhado corretamente, você confirma se o endereço do imóvel segurado é o mesmo cadastrado na apólice?';
    case 'policy_evidence_status':
      return 'Antes de qualquer acionamento, preciso validar a assistência na apólice. Você tem o número da apólice ou algum documento/foto da apólice para conferirmos?';
    default:
      return 'Pode me dar um pouco mais de detalhe sobre o que está acontecendo, por favor?';
  }
}

const HIGH_RISK_RE = /(faísca|faisca|fumaça|fumaca|cheiro de queimado|queimad|choque|fogo|inc[eê]ndio|fa[ií]sc)/i;

/** Heurística leve para sinalizar risco elétrico alto a partir de risk_indicators já preenchido. */
export function detectHighRisk(riskIndicators: unknown): boolean {
  if (!riskIndicators) return false;
  if (typeof riskIndicators === 'string') return HIGH_RISK_RE.test(riskIndicators);
  if (typeof riskIndicators === 'object' && !Array.isArray(riskIndicators)) {
    const o = riskIndicators as Record<string, unknown>;
    const flagKeys = ['has_danger', 'danger', 'fire', 'smoke', 'spark', 'burning', 'shock', 'immediate_danger'];
    if (flagKeys.some((k) => o[k] === true)) return true;
    const level = typeof o.risk_level === 'string' ? o.risk_level.toLowerCase() : '';
    if (level === 'high' || level === 'critical') return true;
    if (typeof o.notes === 'string' && HIGH_RISK_RE.test(o.notes)) return true;
  }
  return false;
}

// Status de caso que ainda estão na fase de coleta (podem virar policy_check ao completar).
const COLLECTING_STATUSES = new Set([
  'new',
  'triage',
  'collecting',
  'corridor_selected',
  'collecting_slots',
]);

// Fases de run anteriores à coleta (podem avançar para collect_slots/readiness_check).
const PRE_COLLECT_PHASES = new Set(['intake', 'identify_insured', 'identify_policy', 'select_subcorridor']);

/**
 * Calcula um passo do corredor (puro, sem I/O).
 * Não decide acionamento externo. external_action_allowed é sempre false neste MVP.
 */
export function computeRuntimeStep(input: { caseRow: any; run: any }): RuntimeStepResult {
  const { caseRow, run } = input;
  const slots = normalizeSlots(run?.slots);
  const filled = slots.filled;

  const safetyNotes: string[] = [];
  if (detectHighRisk(filled.risk_indicators)) {
    safetyNotes.push('Indício de risco elétrico alto — orientar segurança e considerar handoff humano.');
  }
  safetyNotes.push('Ação externa bloqueada neste MVP (dry-run/HITL).');
  safetyNotes.push('Não confirmar cobertura sem evidência de apólice.');

  const currentPhase = typeof run?.phase === 'string' ? run.phase : null;
  const currentStatus = typeof caseRow?.status === 'string' ? caseRow.status : null;

  const selectedSlot = selectNextSlot(filled);

  if (!selectedSlot) {
    // Todos os slots prioritários preenchidos: não gerar nova pergunta de coleta.
    const caseStatusUpdate = currentStatus && COLLECTING_STATUSES.has(currentStatus) ? 'policy_check' : null;
    const runPhaseUpdate =
      currentPhase && (PRE_COLLECT_PHASES.has(currentPhase) || currentPhase === 'collect_slots')
        ? 'readiness_check'
        : null;
    return {
      selectedSlot: null,
      question: null,
      stepStatus: 'no_missing_slots',
      externalActionAllowed: false,
      nextStep: COMPLETE_NEXT_STEP,
      caseStatusUpdate,
      runPhaseUpdate,
      safetyNotes,
    };
  }

  const question = questionForSlot(selectedSlot, filled);
  const caseStatusUpdate = currentStatus && (currentStatus === 'new' || currentStatus === 'triage') ? 'collecting_slots' : null;
  const runPhaseUpdate = currentPhase && PRE_COLLECT_PHASES.has(currentPhase) ? 'collect_slots' : null;

  return {
    selectedSlot,
    question,
    stepStatus: 'question_generated',
    externalActionAllowed: false,
    nextStep: question,
    caseStatusUpdate,
    runPhaseUpdate,
    safetyNotes,
  };
}

// ----------------------------------------------------------------------------
// Extração de slot a partir da resposta do cliente (42B5C).
// Heurística leve, segura e que NÃO inventa: na dúvida marca como ambíguo e
// pede clarificação. Nunca valida apólice, nunca consulta InfoCap.
// ----------------------------------------------------------------------------

export type SlotConfidence = 'low' | 'medium' | 'high';

export interface SlotExtraction {
  /** Conseguiu um valor utilizável para gravar em filled[slot]. */
  filled: boolean;
  /** Resposta ambígua/impossível: manter slot em missing e pedir clarificação. */
  ambiguous: boolean;
  value: unknown;
  confidence: SlotConfidence;
  /** risk_indicators: indica risco elétrico alto detectado. */
  riskHigh?: boolean;
  /** Motivo de conflito (não-ambíguo) a registrar, ex.: address_not_confirmed. */
  conflictReason?: string;
}

// Sinais de risco elétrico imediato.
const RISK_SIGNAL_PATTERNS: Array<{ re: RegExp; signal: string }> = [
  { re: /fuma[çc]a/i, signal: 'smoke' },
  { re: /fa[ií]sca/i, signal: 'spark' },
  { re: /queimad|cheiro de queim/i, signal: 'burning' },
  { re: /choque/i, signal: 'shock' },
  { re: /fogo|inc[eê]ndio/i, signal: 'fire' },
  { re: /derretend|derretid/i, signal: 'melting' },
  { re: /curto(-| )?circuito|curto/i, signal: 'short_circuit' },
];

// Negação/segurança: "não", "sem", "nenhum", "tudo normal", etc.
const RISK_NEGATION_RE = /^\s*n[ãa]o\b|\bsem\b|nenhum|\bnada\b|tranquil|tudo (normal|certo|ok)|sem risco/i;

const TRUNCATE_RAW = 500;

function truncate(s: string, n = TRUNCATE_RAW): string {
  return s.length > n ? s.slice(0, n) : s;
}

function extractRiskIndicators(message: string): SlotExtraction {
  const signals: string[] = [];
  for (const { re, signal } of RISK_SIGNAL_PATTERNS) {
    if (re.test(message) && !signals.includes(signal)) signals.push(signal);
  }
  const negated = RISK_NEGATION_RE.test(message);
  const hasImmediateRisk = signals.length > 0 && !negated;
  return {
    filled: true,
    ambiguous: false,
    confidence: signals.length > 0 ? 'medium' : 'low',
    riskHigh: hasImmediateRisk,
    value: {
      raw: truncate(message),
      has_immediate_risk: hasImmediateRisk,
      risk_level: hasImmediateRisk ? 'high' : 'low',
      signals: hasImmediateRisk ? signals : [],
    },
  };
}

function extractAffectedArea(message: string): SlotExtraction {
  const clean = message.trim();
  if (clean.length < 2) {
    return { filled: false, ambiguous: true, value: null, confidence: 'low' };
  }
  return { filled: true, ambiguous: false, value: truncate(clean), confidence: 'medium' };
}

function extractElectricalIssueType(message: string): SlotExtraction {
  const m = message.toLowerCase();
  let normalized: string;
  if (/disjuntor|desarm|caiu a chave|cai a chave|disjunta/.test(m)) normalized = 'breaker_tripping';
  else if (/sem luz|sem energia|sem for[çc]a|apagou|falta de energia|sem eletricidade/.test(m)) normalized = 'no_power';
  else if (/tomada/.test(m)) normalized = 'outlet_issue';
  else if (/chuveiro/.test(m)) normalized = 'shower_issue';
  else if (/fia[çc][ãa]o|\bfio\b|\bfios\b/.test(m)) normalized = 'wiring_issue';
  else normalized = 'other';
  return {
    filled: true,
    ambiguous: false,
    confidence: normalized === 'other' ? 'low' : 'medium',
    value: { raw: truncate(message), normalized },
  };
}

function extractAddressConfirmed(message: string): SlotExtraction {
  const m = message.toLowerCase();
  // unknown primeiro ("não sei" contém "não").
  if (/n[ãa]o sei|preciso verificar|talvez|acho que|n[ãa]o tenho certeza/.test(m)) {
    return { filled: false, ambiguous: true, value: null, confidence: 'low' };
  }
  if (/n[ãa]o\b|mudou|outro endere|n[ãa]o é|nao e|trocou|mudei|diferente/.test(m)) {
    return {
      filled: true,
      ambiguous: false,
      confidence: 'medium',
      conflictReason: 'address_not_confirmed',
      value: { raw: truncate(message), confirmed: false },
    };
  }
  if (/\bsim\b|isso|confere|certo|exato|é esse|e esse|mesmo|correto|cadastrad|igual/.test(m)) {
    return { filled: true, ambiguous: false, confidence: 'medium', value: { raw: truncate(message), confirmed: true } };
  }
  return { filled: false, ambiguous: true, value: null, confidence: 'low' };
}

function extractPolicyEvidenceStatus(message: string): SlotExtraction {
  const m = message.toLowerCase();
  if (/n[ãa]o tenho|n[ãa]o sei|n[ãa]o acho|perdi|sem ap[óo]lice|n[ãa]o possuo/.test(m)) {
    return { filled: true, ambiguous: false, confidence: 'medium', value: { raw: truncate(message), status: 'not_available' } };
  }
  if (/vou mandar|depois|mais tarde|te mando|te envio|envio depois|procurar|vou achar|vou ver/.test(m)) {
    return { filled: true, ambiguous: false, confidence: 'medium', value: { raw: truncate(message), status: 'pending' } };
  }
  if (/\d{4,}/.test(m) || /tenho|enviei|mandei|segue|foto|documento|ap[óo]lice|n[úu]mero/.test(m)) {
    return { filled: true, ambiguous: false, confidence: 'medium', value: { raw: truncate(message), status: 'provided' } };
  }
  return { filled: false, ambiguous: true, value: null, confidence: 'low' };
}

/** Extrai valor seguro para o slot a partir da resposta do cliente. */
export function extractSlotValue(slot: string, rawMessage: string): SlotExtraction {
  const message = (rawMessage || '').trim();
  if (!message) return { filled: false, ambiguous: true, value: null, confidence: 'low' };
  switch (slot) {
    case 'risk_indicators':
      return extractRiskIndicators(message);
    case 'affected_area':
      return extractAffectedArea(message);
    case 'electrical_issue_type':
      return extractElectricalIssueType(message);
    case 'property_address_confirmed':
      return extractAddressConfirmed(message);
    case 'policy_evidence_status':
      return extractPolicyEvidenceStatus(message);
    default:
      // Slot genérico: grava texto limpo, confiança baixa.
      return { filled: true, ambiguous: false, value: truncate(message), confidence: 'low' };
  }
}

/** Pergunta curta de clarificação quando a resposta foi ambígua. */
export function clarificationForSlot(slot: string): string {
  switch (slot) {
    case 'affected_area':
      return 'Só para confirmar: em qual cômodo ou parte da casa está o problema? Por exemplo cozinha, sala ou área externa.';
    case 'property_address_confirmed':
      return 'Sem problema. Você consegue confirmar se o endereço do imóvel com o problema é o mesmo da apólice? Pode responder só sim ou não.';
    case 'policy_evidence_status':
      return 'Só para eu entender: você tem em mãos o número da apólice ou um documento/foto dela, ou prefere enviar depois?';
    case 'electrical_issue_type':
      return 'Pode me dizer com outras palavras o que está acontecendo com a parte elétrica? Por exemplo: sem energia, disjuntor desarmando ou uma tomada parada.';
    default:
      return 'Pode me explicar um pouco melhor, por favor? Quero registrar certinho para te ajudar.';
  }
}
