// Runtime First-Response & Low-Friction Intake Policy (42B5F).
//
// Política PURA e reutilizável (sem I/O) para a PRIMEIRA resposta do cliente,
// quando ainda não há pergunta ativa do agente. Decide se a mensagem é saudação,
// pedido vago, problema já descrito ou risco alto — e qual resposta curta dar,
// sem virar formulário, sem pedir CPF/apólice cedo, sem repetir "Em que posso
// te ajudar?" quando o cliente já explicou. Não envia nada, não consulta InfoCap,
// não cria dispatch, não confirma cobertura.
import { RISK_SAFETY_QUESTION_CORE } from './runtime-slot-catalog';
import { extractSlotValue } from './corridor-runtime';

export type IntakeKind =
  | 'greeting_only'
  | 'needs_help_unclear'
  | 'problem_already_described'
  | 'high_risk_described';

export interface IntakeDecisionNone {
  applies: false;
}

export interface IntakeDecisionApplies {
  applies: true;
  kind: IntakeKind;
  /** true apenas para high_risk_described (a rota aplica a política 42B5E). */
  high_risk: boolean;
  /** Mensagem curta ao cliente (para kinds que não são high risk; high risk usa a msg de segurança). */
  assistant_message: string;
  /** Valor para corridor_runs.last_agent_action. */
  last_agent_action: string;
  /** Próximo passo do caso (operator-facing curto). */
  next_step: string;
  /** Slot a "armar" como pergunta ativa (problem → 'risk_indicators'); null caso contrário. */
  prime_slot: string | null;
  /** Atualizar problem_description nos slots, se ainda vazio/genérico. */
  should_update_problem_description: boolean;
  problem_description: string | null;
}

export type IntakeDecision = IntakeDecisionNone | IntakeDecisionApplies;

// Saudação pura (mensagem inteira é cumprimento / "tem alguém?" / "pode ajudar?").
const GREETING_RE =
  /^\s*(oi+|ol[áa]+|opa|al[ôo]+|al[óo]+|e a[íi]|eai|bom dia|boa tarde|boa noite|boa madrugada|tudo bem\??|tudo certo\??|tem algu[eé]m( a[íi])?\??|pode (me )?ajudar\??|tem como (me )?ajudar\??|consegue (me )?ajudar\??)\s*[!?.…]*\s*$/i;

// Pedido de ajuda vago, sem descrever o problema.
const UNCLEAR_RE =
  /(preciso de ajuda|preciso de uma ajuda|quero ajuda|me ajuda|preciso falar|quero falar|me chama|me liga|tenho um problema|estou com um problema|preciso de atendimento|preciso de voc[êe]s)/i;

// Sinais de que o cliente JÁ descreveu um problema (elétrico + assistências gerais).
const PROBLEM_RE =
  /(luz|energia|el[ée]tric|tomada|disjuntor|chuveiro|\bfio\b|\bfios\b|curto|fia[çc][ãa]o|apag|sem for[çc]a|sem eletricidade|vazamento|vaz(ando|ou)|encana|\bcano\b|chave|fechadura|tranc|guincho|\bcarro\b|ve[íi]culo|desentup|entupi|\bralo\b|esgoto|geladeira|eletrodom|m[áa]quina de lavar|ar[- ]condicionado|assist[êe]ncia|sinistro|bateu|colis|goteira|infiltra|quebr|parou de funcionar|n[ãa]o funciona|estragou)/i;

// problem_description considerado "genérico" (criado automaticamente, não é o relato real).
const GENERIC_PROBLEM_RE =
  /^(\s*)$|atendimento iniciado|iniciado pelo dashboard|^dashboard$|^teste$|sandbox|^cliente$|^atendimento$/i;

const GREETING_MESSAGE = 'Olá! Em que posso te ajudar?';
const UNCLEAR_MESSAGE = 'Claro. Me conta rapidamente o que aconteceu para eu te ajudar.';
const PROBLEM_ACK_MESSAGE = `Entendi. Vou te ajudar com isso. ${RISK_SAFETY_QUESTION_CORE}`;

const GREETING_NEXT_STEP = 'Aguardar o cliente informar o motivo do atendimento.';
const UNCLEAR_NEXT_STEP = 'Aguardar o cliente detalhar o que aconteceu.';

function isGenericProblem(value: unknown): boolean {
  if (typeof value !== 'string') return true;
  const v = value.trim();
  if (!v) return true;
  return GENERIC_PROBLEM_RE.test(v);
}

/**
 * Avalia a primeira resposta de intake. A rota só deve chamar quando NÃO há
 * pergunta ativa do agente e o caso ainda é editável.
 */
export function evaluateFirstResponseIntake(input: {
  message: string;
  filledSlots?: Record<string, unknown>;
}): IntakeDecision {
  const message = (input.message || '').trim();
  if (!message) return { applies: false };

  const filled = input.filledSlots || {};
  const currentProblem = filled.problem_description;
  const problemIsGeneric = isGenericProblem(currentProblem);

  // 1. Risco alto descrito já na primeira mensagem → política de segurança (42B5E).
  const riskExtraction = extractSlotValue('risk_indicators', message);
  if (riskExtraction.riskHigh === true) {
    return {
      applies: true,
      kind: 'high_risk_described',
      high_risk: true,
      assistant_message: '', // a rota usa a mensagem de segurança da política 42B5E
      last_agent_action: 'safety_handoff:first_response',
      next_step: 'Risco elétrico alto detectado. Preparar dossiê e transferir para suporte humano configurado.',
      prime_slot: null,
      should_update_problem_description: problemIsGeneric,
      problem_description: problemIsGeneric ? message : null,
    };
  }

  // 2. Problema já descrito → reconhecer e perguntar risco (sem repetir "em que posso ajudar?").
  if (PROBLEM_RE.test(message)) {
    return {
      applies: true,
      kind: 'problem_already_described',
      high_risk: false,
      assistant_message: PROBLEM_ACK_MESSAGE,
      last_agent_action: 'ask:risk_indicators',
      next_step: PROBLEM_ACK_MESSAGE,
      prime_slot: 'risk_indicators',
      should_update_problem_description: problemIsGeneric,
      problem_description: problemIsGeneric ? message : null,
    };
  }

  // 3. Saudação pura → "Olá! Em que posso te ajudar?".
  if (GREETING_RE.test(message)) {
    return {
      applies: true,
      kind: 'greeting_only',
      high_risk: false,
      assistant_message: GREETING_MESSAGE,
      last_agent_action: 'intake:greeting',
      next_step: GREETING_NEXT_STEP,
      prime_slot: null,
      should_update_problem_description: false,
      problem_description: null,
    };
  }

  // 4. Pedido de ajuda vago ou qualquer outra coisa não classificada → pedir detalhe curto.
  if (UNCLEAR_RE.test(message) || message.split(/\s+/).length <= 3) {
    return {
      applies: true,
      kind: 'needs_help_unclear',
      high_risk: false,
      assistant_message: UNCLEAR_MESSAGE,
      last_agent_action: 'intake:clarify_need',
      next_step: UNCLEAR_NEXT_STEP,
      prime_slot: null,
      should_update_problem_description: false,
      problem_description: null,
    };
  }

  // 5. Fallback: mensagem substantiva sem palavra-chave conhecida → tratar como problema descrito.
  return {
    applies: true,
    kind: 'problem_already_described',
    high_risk: false,
    assistant_message: PROBLEM_ACK_MESSAGE,
    last_agent_action: 'ask:risk_indicators',
    next_step: PROBLEM_ACK_MESSAGE,
    prime_slot: 'risk_indicators',
    should_update_problem_description: problemIsGeneric,
    problem_description: problemIsGeneric ? message : null,
  };
}
