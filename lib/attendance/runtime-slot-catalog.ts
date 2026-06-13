// Runtime Slot Catalog (42B5D).
//
// Catálogo declarativo de comportamento por tipo de slot: pergunta, clarificação,
// extração segura e flags de segurança. Extraído do corridor-runtime para que
// novos corredores/subcorredores possam reusar/estender slots sem espalhar
// if/else pelo runtime. Não envia nada, não valida apólice, não consulta InfoCap.
//
// IMPORTANTE: as perguntas/clarificações/extratores aqui são idênticos ao
// comportamento do 42B5B/42B5C (refatoração estrutural, sem mudança funcional).

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

export interface SlotDefinition {
  key: string;
  label: string;
  /** Prioridade default (menor = perguntado antes). */
  priority_default: number;
  /** Pergunta humanizada (recebe os slots já preenchidos para contexto). */
  question: (filled: Record<string, unknown>) => string;
  /** Pergunta curta de clarificação quando a resposta foi ambígua. */
  clarification: () => string;
  /** Extração segura a partir da resposta do cliente. */
  extractor: (message: string) => SlotExtraction;
  /** Metadados de segurança (ex.: slot que sinaliza risco físico). */
  safety?: { raisesRisk?: boolean };
}

// ---------------------------------------------------------------------------
// Helpers compartilhados (idênticos ao 42B5C)
// ---------------------------------------------------------------------------

const TRUNCATE_RAW = 500;
function truncate(s: string, n = TRUNCATE_RAW): string {
  return s.length > n ? s.slice(0, n) : s;
}

const ELECTRICAL_HINT_RE =
  /(luz|energia|disjuntor|tomada|curto|fios?|fia[çc][aã]o|el[eé]tric|chuveiro|apag[ãa]|sem força)/i;

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

// ---------------------------------------------------------------------------
// Extratores por slot (idênticos ao 42B5C)
// ---------------------------------------------------------------------------

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

/** Extrator genérico (slot sem definição dedicada): grava texto limpo, confiança baixa. */
export function genericExtractor(message: string): SlotExtraction {
  const clean = (message || '').trim();
  if (!clean) return { filled: false, ambiguous: true, value: null, confidence: 'low' };
  return { filled: true, ambiguous: false, value: truncate(clean), confidence: 'low' };
}

/** Pergunta genérica (slot sem definição dedicada). */
export const GENERIC_QUESTION = 'Pode me dar um pouco mais de detalhe sobre o que está acontecendo, por favor?';
/** Clarificação genérica. */
export const GENERIC_CLARIFICATION =
  'Pode me explicar um pouco melhor, por favor? Quero registrar certinho para te ajudar.';

// ---------------------------------------------------------------------------
// Catálogo
// ---------------------------------------------------------------------------

export const SLOT_CATALOG: Record<string, SlotDefinition> = {
  risk_indicators: {
    key: 'risk_indicators',
    label: 'Indicadores de risco',
    priority_default: 1,
    safety: { raisesRisk: true },
    question: (filled) => {
      const desc = typeof filled.problem_description === 'string' ? filled.problem_description : '';
      const electrical = ELECTRICAL_HINT_RE.test(desc);
      const opener = electrical ? 'Entendi' : 'Obrigada por explicar';
      return `${opener}. Antes de seguir, preciso só confirmar uma coisa para sua segurança: tem cheiro de queimado, faísca, fumaça ou algum risco imediato aí?`;
    },
    clarification: () => GENERIC_CLARIFICATION,
    extractor: extractRiskIndicators,
  },
  affected_area: {
    key: 'affected_area',
    label: 'Área afetada',
    priority_default: 2,
    question: () =>
      'Perfeito. Em qual área da casa isso está acontecendo? Por exemplo: cozinha, sala, quarto, área externa ou a casa toda.',
    clarification: () =>
      'Só para confirmar: em qual cômodo ou parte da casa está o problema? Por exemplo cozinha, sala ou área externa.',
    extractor: extractAffectedArea,
  },
  electrical_issue_type: {
    key: 'electrical_issue_type',
    label: 'Tipo de problema elétrico',
    priority_default: 3,
    question: () =>
      'Certo. O que exatamente aconteceu: ficou sem energia, o disjuntor está desarmando, alguma tomada parou ou é outro problema elétrico?',
    clarification: () =>
      'Pode me dizer com outras palavras o que está acontecendo com a parte elétrica? Por exemplo: sem energia, disjuntor desarmando ou uma tomada parada.',
    extractor: extractElectricalIssueType,
  },
  property_address_confirmed: {
    key: 'property_address_confirmed',
    label: 'Endereço confirmado',
    priority_default: 4,
    question: () =>
      'Para deixar o atendimento encaminhado corretamente, você confirma se o endereço do imóvel segurado é o mesmo cadastrado na apólice?',
    clarification: () =>
      'Sem problema. Você consegue confirmar se o endereço do imóvel com o problema é o mesmo da apólice? Pode responder só sim ou não.',
    extractor: extractAddressConfirmed,
  },
  policy_evidence_status: {
    key: 'policy_evidence_status',
    label: 'Status da evidência de apólice',
    priority_default: 5,
    question: () =>
      'Antes de qualquer acionamento, preciso validar a assistência na apólice. Você tem o número da apólice ou algum documento/foto da apólice para conferirmos?',
    clarification: () =>
      'Só para eu entender: você tem em mãos o número da apólice ou um documento/foto dela, ou prefere enviar depois?',
    extractor: extractPolicyEvidenceStatus,
  },
};

/** Prioridade canônica do MVP Allianz/Eletricista (derivada do priority_default). */
export const ELECTRICIAN_SLOT_PRIORITY: readonly string[] = Object.values(SLOT_CATALOG)
  .slice()
  .sort((a, b) => a.priority_default - b.priority_default)
  .map((s) => s.key);

export function getSlotDefinition(key: string): SlotDefinition | undefined {
  return SLOT_CATALOG[key];
}
