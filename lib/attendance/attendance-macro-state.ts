// Attendance Macro State Machine & Identity/Policy Gate (42B5G).
//
// Camada GLOBAL e reutilizável (sem I/O) que governa a espinha dorsal do
// atendimento: Entrada → Identidade → Apólice/InfoCap Gate → Levantamento →
// Decisão Operacional → Corredor/Subcorredor. NÃO é um script de chatbot e NÃO
// substitui o Smith: é um trilho de segurança/estado que será chamado pelo
// Attendance Agent do Smith como ferramenta determinística.
//
// NÃO consulta InfoCap, NÃO confirma cobertura, NÃO aciona seguradora,
// NÃO cria dispatch/approval. Apenas decide estado e próximo gate.
import { isSlotFilled } from './corridor-runtime';
import { detectHighRisk } from './runtime-slot-catalog';
import {
  IDENTITY_QUESTION,
  IDENTITY_NEXT_STEP,
  POLICY_LOOKUP_MESSAGE,
  POLICY_NEXT_STEP,
} from './runtime-identity-policy';

export const MACRO_STATES = {
  ENTRY: 'entry',
  NEEDS_INTENT: 'needs_intent',
  IDENTITY_REQUIRED: 'identity_required',
  IDENTITY_COLLECTING: 'identity_collecting',
  POLICY_LOOKUP_REQUIRED: 'policy_lookup_required',
  POLICY_LOOKUP_BLOCKED: 'policy_lookup_blocked',
  POLICY_LOOKUP_PENDING: 'policy_lookup_pending',
  POLICY_SELECTED: 'policy_selected',
  OPERATIONAL_DECISION: 'operational_decision',
  CORRIDOR_SELECTED: 'corridor_selected',
  CORRIDOR_COLLECTING_SLOTS: 'corridor_collecting_slots',
  HANDOFF: 'handoff',
  CLOSED: 'closed',
} as const;

export type MacroState = (typeof MACRO_STATES)[keyof typeof MACRO_STATES];

export interface MacroStateDecision {
  macro_state: MacroState;
  should_ask_identity: boolean;
  should_require_policy_lookup: boolean;
  should_block_corridor_slot_collection: boolean;
  should_continue_corridor_runtime: boolean;
}

/**
 * Este atendimento depende de apólice/cobertura? No MVP, praticamente todo
 * atendimento de assistência/sinistro depende. Pode ser desligado por caso via
 * metadata.skip_policy_gate=true (ex.: dúvida genérica que não toca apólice).
 */
export function caseNeedsPolicy(caseRow: any): boolean {
  if (caseRow?.metadata?.skip_policy_gate === true) return false;
  return true;
}

/** Identidade válida = insured_document_ref com 11 (CPF) ou 14 (CNPJ) dígitos. */
export function hasValidIdentity(caseRow: any): boolean {
  const digits = typeof caseRow?.insured_document_ref === 'string' ? caseRow.insured_document_ref.replace(/\D/g, '') : '';
  return digits.length === 11 || digits.length === 14;
}

// verification_status considerados confiáveis para destravar o corredor.
const TRUSTED_VERIFICATION = new Set(['verified_by_human', 'verified_by_connector', 'verified_by_document']);

/**
 * Evidência de apólice pronta para retomar o corredor (42B5H): macro state em
 * `policy_evidence_ready`, `coverage_evidence` preenchido e `verification_status`
 * confiável. NÃO afirma cobertura por conta própria — só reconhece a evidência.
 */
export function isPolicyEvidenceReady(caseRow: any): boolean {
  const macro = caseRow?.metadata?.attendance_macro_state;
  const ev = caseRow?.coverage_evidence;
  const hasEvidence = ev && typeof ev === 'object' && !Array.isArray(ev) && Object.keys(ev).length > 0;
  const verified = typeof caseRow?.verification_status === 'string' && TRUSTED_VERIFICATION.has(caseRow.verification_status);
  return macro === 'policy_evidence_ready' && Boolean(hasEvidence) && verified;
}

/** Abertura curta e humana ao retomar o atendimento após a apólice/evidência. */
export const RESUME_AFTER_POLICY_PREFIX =
  'Apólice localizada e evidência registrada. Agora vou seguir com os dados do atendimento. ';

function blocked(macro_state: MacroState): MacroStateDecision {
  return {
    macro_state,
    should_ask_identity: false,
    should_require_policy_lookup: false,
    should_block_corridor_slot_collection: true,
    should_continue_corridor_runtime: false,
  };
}

/**
 * Avalia o macro estado atual e o próximo gate obrigatório. Puro, sem I/O.
 * Precedência: handoff/closed > risco alto > coleta de risco > identidade >
 * apólice/InfoCap > corredor.
 */
export function evaluateAttendanceMacroState(input: {
  caseRow: any;
  filledSlots?: Record<string, unknown>;
  riskHigh?: boolean;
}): MacroStateDecision {
  const { caseRow } = input;
  const filledSlots = input.filledSlots || {};
  const status = caseRow?.status;

  if (status === 'handoff') return blocked(MACRO_STATES.HANDOFF);
  if (status === 'closed' || status === 'cancelled') return blocked(MACRO_STATES.CLOSED);

  // Risco alto tem precedência sobre identidade/apólice.
  if (input.riskHigh === true || detectHighRisk(filledSlots.risk_indicators)) {
    return blocked(MACRO_STATES.HANDOFF);
  }

  // Ainda coletando o gate de segurança (risco) → corredor continua (pergunta risco).
  const riskResolved = isSlotFilled(filledSlots.risk_indicators);
  if (!riskResolved) {
    return {
      macro_state: MACRO_STATES.CORRIDOR_COLLECTING_SLOTS,
      should_ask_identity: false,
      should_require_policy_lookup: false,
      should_block_corridor_slot_collection: false,
      should_continue_corridor_runtime: true,
    };
  }

  const needsPolicy = caseNeedsPolicy(caseRow);
  const identity = hasValidIdentity(caseRow);
  const verified =
    typeof caseRow?.verification_status === 'string' && caseRow.verification_status.startsWith('verified');

  // Gate de identidade: precisa apólice e ainda não tem documento.
  if (needsPolicy && !identity) {
    return {
      macro_state: MACRO_STATES.IDENTITY_REQUIRED,
      should_ask_identity: true,
      should_require_policy_lookup: false,
      should_block_corridor_slot_collection: true,
      should_continue_corridor_runtime: false,
    };
  }

  // Gate de apólice: tem documento, mas apólice ainda não verificada (InfoCap futuro).
  if (needsPolicy && identity && !verified) {
    return {
      macro_state: MACRO_STATES.POLICY_LOOKUP_REQUIRED,
      should_ask_identity: false,
      should_require_policy_lookup: true,
      should_block_corridor_slot_collection: true,
      should_continue_corridor_runtime: false,
    };
  }

  // Gates resolvidos / não aplicáveis → corredor pode continuar.
  return {
    macro_state: MACRO_STATES.CORRIDOR_COLLECTING_SLOTS,
    should_ask_identity: false,
    should_require_policy_lookup: false,
    should_block_corridor_slot_collection: false,
    should_continue_corridor_runtime: true,
  };
}

export interface MacroGateOverride {
  selected_slot: string;
  question: string;
  status: string;
  next_step: string;
  last_agent_action: string;
  macro_state: MacroState;
  /** Novo attendance_cases.status sugerido (ex.: policy_check), se aplicável. */
  case_status?: string;
}

/**
 * Retorna um override de próxima resposta quando um gate (identidade/apólice)
 * deve interromper a coleta normal do corredor; null se o corredor pode seguir.
 */
export function macroGateOverride(input: {
  caseRow: any;
  filledSlots?: Record<string, unknown>;
}): MacroGateOverride | null {
  const macro = evaluateAttendanceMacroState(input);
  if (macro.should_ask_identity) {
    return {
      selected_slot: 'identity_document',
      question: IDENTITY_QUESTION,
      status: 'identity_required',
      next_step: IDENTITY_NEXT_STEP,
      last_agent_action: 'ask:identity_document',
      macro_state: MACRO_STATES.IDENTITY_REQUIRED,
    };
  }
  if (macro.should_require_policy_lookup) {
    return {
      selected_slot: 'policy_lookup',
      question: POLICY_LOOKUP_MESSAGE,
      status: 'policy_lookup_required',
      next_step: POLICY_NEXT_STEP,
      last_agent_action: 'policy_lookup:pending',
      macro_state: MACRO_STATES.POLICY_LOOKUP_REQUIRED,
      case_status: 'policy_check',
    };
  }
  return null;
}
