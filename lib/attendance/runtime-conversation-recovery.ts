// Runtime Conversation Recovery (42B5K).
//
// Dado o tipo de rota da mensagem (runtime-message-router), produz uma resposta
// humana e segura SEM derrubar o corredor, sem confirmar cobertura, sem ação
// externa. PURO (sem I/O). Não usa LLM neste batch: respostas determinísticas e
// honestas. A resposta inteligente/aberta (ex.: responder trivia) fica para o
// fallback via Attendance Agent/Smith em batch futuro (registrado no relatório).
import { questionForSlot } from './corridor-runtime';
import { IDENTITY_QUESTION } from './runtime-identity-policy';
import type { MessageRoute } from './runtime-message-router';

export interface RecoveryContext {
  activeSlot: string | null;
  filled: Record<string, unknown>;
  missing: string[];
  message: string;
  caseRow: any;
}

export interface RecoveryDecision {
  /** true = a rota produz a resposta aqui (pula a extração de slot). */
  handled: boolean;
  assistant_message: string;
  /** Slots a preencher por inferência segura (apenas em frustração/repetição). */
  fill: Record<string, unknown>;
  /** Após preencher, computar o próximo slot e anexar a pergunta. */
  advance: boolean;
  /** Preservar o last_agent_action atual (não virar conversation_recovery). */
  keep_last_agent_action: boolean;
}

const ROOM_PATTERNS: Array<{ re: RegExp; area: string }> = [
  { re: /cozinha/i, area: 'cozinha' },
  { re: /\bsala\b/i, area: 'sala' },
  { re: /quarto/i, area: 'quarto' },
  { re: /banheiro/i, area: 'banheiro' },
  { re: /garagem/i, area: 'garagem' },
  { re: /varanda/i, area: 'varanda' },
  { re: /quintal/i, area: 'quintal' },
  { re: /[aá]rea externa|parte externa|do lado de fora/i, area: 'área externa' },
  { re: /casa toda|toda a casa|a casa inteira|tudo/i, area: 'casa toda' },
];

const ELECTRICAL_NORMALIZE: Array<{ re: RegExp; normalized: string }> = [
  { re: /disjuntor|desarm|caiu a chave|cai a chave/i, normalized: 'breaker_tripping' },
  { re: /sem luz|sem energia|sem for[çc]a|apagou|falta de energia|sem eletricidade/i, normalized: 'no_power' },
  { re: /tomada/i, normalized: 'outlet_issue' },
  { re: /chuveiro/i, normalized: 'shower_issue' },
  { re: /fia[çc][ãa]o|\bfio\b|\bfios\b/i, normalized: 'wiring_issue' },
];

/** Inferência segura de slots a partir de uma mensagem (frustração/repetição). */
export function inferSlotsFromMessage(
  message: string,
  missing: string[],
  filled: Record<string, unknown>,
): Record<string, unknown> {
  const fill: Record<string, unknown> = {};
  const msg = message || '';
  const isMissing = (k: string) => missing.includes(k) && !(k in filled);

  if (isMissing('affected_area')) {
    const room = ROOM_PATTERNS.find((r) => r.re.test(msg));
    if (room) fill.affected_area = room.area;
  }
  if (isMissing('electrical_issue_type')) {
    const issue = ELECTRICAL_NORMALIZE.find((r) => r.re.test(msg));
    if (issue) fill.electrical_issue_type = { raw: msg.slice(0, 200), normalized: issue.normalized };
  }
  return fill;
}

function currentQuestion(ctx: RecoveryContext): string {
  if (ctx.activeSlot === 'identity_document') return IDENTITY_QUESTION;
  if (ctx.activeSlot) return questionForSlot(ctx.activeSlot, ctx.filled);
  return 'Podemos continuar de onde paramos?';
}

/**
 * Constrói a decisão de recuperação. Para slot_answer/correction/unsafe/unknown
 * retorna handled=false (deixa o fluxo normal de slot rodar).
 */
export function buildRecoveryResponse(route: MessageRoute, ctx: RecoveryContext): RecoveryDecision {
  const q = currentQuestion(ctx);

  switch (route.kind) {
    case 'off_topic_general_question':
      return {
        handled: true,
        // Sem LLM: não arriscar resposta imprecisa; reconhecer e voltar ao atendimento.
        assistant_message: `Boa pergunta! Essa é uma questão geral, então prefiro não me alongar para não atrasar o seu atendimento. Voltando: ${q}`,
        fill: {},
        advance: false,
        keep_last_agent_action: true,
      };

    case 'frustration_or_repetition': {
      const fill = inferSlotsFromMessage(ctx.message, ctx.missing, ctx.filled);
      return {
        handled: true,
        assistant_message: 'Entendi, você tem razão. Já registrei o que você informou. Vou seguir com os próximos dados necessários para o acionamento.',
        fill,
        advance: true,
        keep_last_agent_action: false,
      };
    }

    case 'unavailable_data':
      return {
        handled: true,
        assistant_message:
          'Sem problema. Pode me enviar quando conseguir. Para confirmar a cobertura eu preciso dessa validação, mas posso manter o atendimento aberto e adiantar as demais informações do caso.',
        fill: {},
        advance: false,
        keep_last_agent_action: true,
      };

    case 'clarification_question':
      return {
        handled: true,
        assistant_message:
          ctx.activeSlot === 'identity_document'
            ? `Preciso do CPF apenas para localizar sua apólice com segurança, antes de confirmar qualquer cobertura. ${q}`
            : `Preciso dessa informação para encaminhar seu atendimento corretamente. ${q}`,
        fill: {},
        advance: false,
        keep_last_agent_action: true,
      };

    case 'delay_request':
      return {
        handled: true,
        assistant_message: `Sem pressa, fico no aguardo. Quando puder, é só me responder: ${q}`,
        fill: {},
        advance: false,
        keep_last_agent_action: true,
      };

    default:
      // slot_answer, correction, unsafe_or_high_risk, unknown → fluxo normal.
      return { handled: false, assistant_message: '', fill: {}, advance: false, keep_last_agent_action: true };
  }
}
