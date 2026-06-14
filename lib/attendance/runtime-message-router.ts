// Runtime Message Router (42B5K).
//
// Classificador LEVE e PURO (sem I/O) que decide como uma mensagem do segurado
// deve ser tratada ANTES de assumir que ela é a resposta do slot ativo. Evita
// que o atendimento fique rígido demais (ex.: pergunta fora do fluxo derruba o
// corredor). Conservador por padrão: na dúvida, retorna `slot_answer` para
// preservar o comportamento já testado (42B5C/D/E/F/G/H).
//
// NÃO chama LLM, NÃO confirma cobertura, NÃO altera estado — só classifica.

export type MessageRouteKind =
  | 'slot_answer'
  | 'off_topic_general_question'
  | 'frustration_or_repetition'
  | 'unavailable_data'
  | 'correction'
  | 'clarification_question'
  | 'delay_request'
  | 'unsafe_or_high_risk'
  | 'unknown';

export interface MessageRouteInput {
  message: string;
  activeSlot: string | null;
  lastAgentAction?: string | null;
  macroState?: string | null;
  filled?: Record<string, unknown>;
  missing?: string[];
}

export interface MessageRoute {
  kind: MessageRouteKind;
  signals: string[];
}

const INTERROGATIVE_RE = /^\s*(o que|que\b|qual|quais|quem|onde|quando|por que|por qu[eê]|porque|como|pra que|para que|significa|existe|tem como|vc sabe|voc[eê] sabe)/i;

const DOMAIN_RE =
  /(luz|energia|el[eé]tric|tomada|disjuntor|chuveiro|\bfio\b|\bfios\b|curto|fia[çc][ãa]o|apag|sem for[çc]a|vazament|encan|\bcano\b|chave|fechadura|guincho|eletrodom|geladeira|m[aá]quina|ar[- ]condicionado|ap[oó]lice|cobertura|atendimento|seguro|\bcpf\b|\bcnpj\b|endere[çc]o|cozinha|sala|quarto|banheiro|garagem|varanda|quintal|casa|[aá]rea|risco|cheiro|queimad|fa[ií]sca|fuma[çc]a|eletricista|encanador|prestador|seguradora|allianz|sinistro)/i;

const FRUSTRATION_RE =
  /(j[aá] (disse|falei|informei|respondi|expliquei)|de novo|outra vez|quantas vezes|voc[eê]s? n[aã]o (entend|escut|ouv)|t[oô] falando|estou falando|que saco|\baff+\b|n[aã]o tô conseguindo|n[aã]o estou conseguindo|pelo amor)/i;

const UNAVAILABLE_RE =
  /(n[aã]o (tenho|estou com|t[oô] com|sei onde)|t[aá] com|est[aá] com|mando depois|envio depois|te mando|depois eu|mais tarde|agora n[aã]o (tenho|estou|posso|consigo)|n[aã]o tenho aqui|n[aã]o tô com|n[aã]o estou com)/i;

const DELAY_RE =
  /(um momento|s[oó] um (instante|minuto|segundo)|espera a[ií]|aguarda|j[aá] volto|depois eu respondo|me d[aá] um tempo|j[aá] te respondo|peraí|pera a[ií])/i;

const CORRECTION_RE =
  /(na verdade|corrigindo|me enganei|\berrei\b|quis dizer|n[aã]o [eé] (isso|bem)|me confundi|deixa eu corrigir)/i;

const WHY_RE = /(por que|por qu[eê]|porque|pra que|para que|por qual motivo|como assim)/i;

function isQuestion(m: string): boolean {
  return m.includes('?') || INTERROGATIVE_RE.test(m.trim());
}

function isDomainRelated(m: string): boolean {
  return DOMAIN_RE.test(m);
}

function looksLikeShortAnswer(m: string): boolean {
  return /^\s*(sim|n[aã]o|isso|correto|exato|confere|[eé] isso|claro|ok|certo|pode ser|talvez|acho que)\b/i.test(m);
}

function uppercaseRatio(m: string): number {
  const letters = m.replace(/[^A-Za-zÀ-ÿ]/g, '');
  if (letters.length < 8) return 0;
  const upper = (letters.match(/[A-ZÀ-Þ]/g) || []).length;
  return upper / letters.length;
}

/**
 * Classifica a mensagem do cliente. Ordem das regras pensada para ser segura:
 * frustração → indisponibilidade (gates de doc) → adiamento → correção →
 * clarificação (pergunta sobre o atendimento) → off-topic (pergunta geral) →
 * slot_answer (default).
 */
export function classifyMessageRoute(input: MessageRouteInput): MessageRoute {
  const message = (input.message || '').trim();
  const signals: string[] = [];
  if (!message) return { kind: 'unknown', signals: ['empty'] };

  const activeSlot = input.activeSlot || null;
  const docGate = activeSlot === 'identity_document' || activeSlot === 'policy_evidence_status';

  // 1. Frustração / repetição
  if (FRUSTRATION_RE.test(message) || uppercaseRatio(message) > 0.85) {
    signals.push('frustration');
    return { kind: 'frustration_or_repetition', signals };
  }

  // 2. Dado indisponível — só relevante em gate de documento/apólice
  if (docGate && UNAVAILABLE_RE.test(message)) {
    signals.push('unavailable_doc');
    return { kind: 'unavailable_data', signals };
  }

  // 3. Pedido de adiamento
  if (DELAY_RE.test(message)) {
    signals.push('delay');
    return { kind: 'delay_request', signals };
  }

  // 4. Correção explícita
  if (CORRECTION_RE.test(message)) {
    signals.push('correction');
    return { kind: 'correction', signals };
  }

  // 5. Clarificação sobre o próprio atendimento (pergunta + motivo + domínio)
  if (isQuestion(message) && WHY_RE.test(message) && (isDomainRelated(message) || docGate)) {
    signals.push('why_question');
    return { kind: 'clarification_question', signals };
  }

  // 6. Pergunta geral fora do fluxo (pergunta, sem relação com o atendimento)
  if (isQuestion(message) && !isDomainRelated(message) && !looksLikeShortAnswer(message)) {
    signals.push('off_topic_question');
    return { kind: 'off_topic_general_question', signals };
  }

  // 7. Default seguro
  return { kind: 'slot_answer', signals: ['default'] };
}
