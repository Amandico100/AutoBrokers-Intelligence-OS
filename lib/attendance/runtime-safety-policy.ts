// Runtime Safety & Handoff Decision Layer (42B5E).
//
// Política PURA e testável: quando risco elétrico alto é detectado, o runtime
// NÃO continua a coleta normal. Em vez disso responde com orientação curta de
// segurança, marca prioridade/risco alto e prepara o caso para dossiê/handoff
// humano. Não envia WhatsApp, não cria dispatch, não cria approval_request,
// não consulta InfoCap, não confirma cobertura. Sem I/O.
import { detectHighRisk } from './runtime-slot-catalog';

// Mensagem curta, calma e humana — sem termos internos, sem prometer cobertura/acionamento.
export const SAFETY_HANDOFF_MESSAGE =
  'Entendi. Como você mencionou cheiro de queimado/faísca, por segurança não toque em tomadas, fios ou quadro. Afaste as pessoas do local e, se for seguro fazer isso, desligue o disjuntor geral. Vou tratar como prioridade e encaminhar com as informações necessárias.';

const SAFETY_NEXT_STEP =
  'Risco elétrico alto detectado. Preparar dossiê e transferir para suporte humano configurado.';

const SAFETY_NOTE =
  'Risco elétrico alto: orientar segurança e transferir para suporte humano. Não acionar nada automaticamente.';

export const HIGH_RISK_REASON = 'high_risk_electrical';
export const SAFETY_LAST_AGENT_ACTION = 'safety_handoff:risk_indicators';

export interface SafetyDecisionTriggered {
  triggered: true;
  reason: typeof HIGH_RISK_REASON;
  risk_level: 'high';
  priority: 'high';
  handoff_required: true;
  handoff_reason: typeof HIGH_RISK_REASON;
  stop_normal_collection: true;
  assistant_message: string;
  next_step: string;
  last_agent_action: string;
  safety_note: string;
}

export interface SafetyDecisionNone {
  triggered: false;
}

export type SafetyDecision = SafetyDecisionTriggered | SafetyDecisionNone;

/**
 * Avalia se a interação atual exige a camada de segurança/handoff de risco alto.
 *
 * Dispara quando:
 *  - a extração do slot `risk_indicators` retornou `riskHigh === true` (resposta atual), OU
 *  - os slots já preenchidos contêm `risk_indicators` com indício de risco alto.
 *
 * Quando dispara, o runtime deve PARAR a coleta normal e seguir a decisão.
 */
export function evaluateRuntimeSafetyDecision(input: {
  caseRow?: any;
  targetSlot?: string | null;
  extraction?: { riskHigh?: boolean } | null;
  filledSlots?: Record<string, unknown>;
}): SafetyDecision {
  const fromExtraction = input.extraction?.riskHigh === true && input.targetSlot === 'risk_indicators';
  const fromFilled = detectHighRisk(input.filledSlots?.risk_indicators);
  if (!fromExtraction && !fromFilled) return { triggered: false };

  return {
    triggered: true,
    reason: HIGH_RISK_REASON,
    risk_level: 'high',
    priority: 'high',
    handoff_required: true,
    handoff_reason: HIGH_RISK_REASON,
    stop_normal_collection: true,
    assistant_message: SAFETY_HANDOFF_MESSAGE,
    next_step: SAFETY_NEXT_STEP,
    last_agent_action: SAFETY_LAST_AGENT_ACTION,
    safety_note: SAFETY_NOTE,
  };
}
