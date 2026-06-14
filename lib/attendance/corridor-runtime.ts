// Corridor Runtime Step Engine (determinístico, server-side, channel-agnostic).
//
// Não envia WhatsApp, não cria dispatch_packet, não cria approval_request,
// não aciona seguradora, não chama portal/InfoCap, não confirma cobertura.
// É um motor de PASSO: dado o estado de slots de um corredor, escolhe o próximo
// dado necessário e gera UMA pergunta humana. Futuramente o Attendance Agent/Smith
// poderá chamá-lo como ferramenta. Sem LLM solto, sem motor paralelo.
//
// 42B5D: o comportamento por slot (pergunta/clarificação/extração/segurança) vive
// no Slot Catalog (runtime-slot-catalog.ts). Este módulo cuida do FLUXO genérico
// (seleção, status, fases, diagnostics) e delega o resto ao catálogo.
import { normalizeSlots } from './handoff-dossier';
import {
  ELECTRICIAN_SLOT_PRIORITY,
  GENERIC_CLARIFICATION,
  GENERIC_QUESTION,
  detectHighRisk,
  genericExtractor,
  getSlotDefinition,
  type SlotConfidence,
  type SlotExtraction,
} from './runtime-slot-catalog';

export const RUNTIME_ENGINE = 'corridor_runtime_step_v1';

// Re-exports para compatibilidade com importadores existentes (step/reply routes etc.).
export { ELECTRICIAN_SLOT_PRIORITY, detectHighRisk };
export type { SlotConfidence, SlotExtraction };

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

// Mensagens de conclusão quando não há mais slot a coletar.
const COMPLETE_NEXT_STEP_NO_EVIDENCE =
  'Dados mínimos coletados. Próximo passo: validar apólice/evidência antes de preparar acionamento.';
const COMPLETE_NEXT_STEP_WITH_EVIDENCE =
  'Dados mínimos coletados e apólice/evidência já registrada. Próximo passo: preparar validação final/readiness e pacote de acionamento em modo dry-run/HITL.';

// verification_status considerados confiáveis para a evidência de apólice (42B5K.1).
const TRUSTED_VERIFICATION = ['verified_by_human', 'verified_by_connector', 'verified_by_document'];

/** Valor estruturado seguro que satisfaz policy_evidence_status a partir da evidência. */
export const POLICY_EVIDENCE_SATISFIED = { status: 'provided', source: 'coverage_evidence' } as const;

/** Evidência de cobertura pronta + verificação confiável (não pedir apólice de novo). */
export function isCoverageEvidenceReady(caseRow: any): boolean {
  const ev = caseRow?.coverage_evidence;
  return Boolean(
    ev &&
      typeof ev === 'object' &&
      !Array.isArray(ev) &&
      Object.keys(ev).length > 0 &&
      typeof caseRow?.verification_status === 'string' &&
      TRUSTED_VERIFICATION.includes(caseRow.verification_status),
  );
}

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

/** Pergunta humanizada por slot (delegada ao Slot Catalog). */
export function questionForSlot(slot: string, filled: Record<string, unknown>): string {
  const def = getSlotDefinition(slot);
  return def ? def.question(filled) : GENERIC_QUESTION;
}

/** Pergunta curta de clarificação quando a resposta foi ambígua (delegada ao catálogo). */
export function clarificationForSlot(slot: string): string {
  const def = getSlotDefinition(slot);
  return def ? def.clarification() : GENERIC_CLARIFICATION;
}

/** Extrai valor seguro para o slot a partir da resposta do cliente (delegado ao catálogo). */
export function extractSlotValue(slot: string, rawMessage: string): SlotExtraction {
  const message = (rawMessage || '').trim();
  if (!message) return { filled: false, ambiguous: true, value: null, confidence: 'low' };
  const def = getSlotDefinition(slot);
  return def ? def.extractor(message) : genericExtractor(message);
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
 *
 * @param slotPriority ordem de slots resolvida (Runtime Config Resolver). Default:
 *   ELECTRICIAN_SLOT_PRIORITY — preserva o comportamento do MVP Allianz/Eletricista.
 */
export function computeRuntimeStep(input: {
  caseRow: any;
  run: any;
  slotPriority?: readonly string[];
}): RuntimeStepResult {
  const { caseRow, run } = input;
  const slotPriority = input.slotPriority && input.slotPriority.length > 0 ? input.slotPriority : ELECTRICIAN_SLOT_PRIORITY;
  const slots = normalizeSlots(run?.slots);
  const filled = { ...slots.filled };

  // 42B5K/42B5K.1: se a evidência de apólice já está pronta, o slot
  // policy_evidence_status é considerado satisfeito — não perguntar de novo.
  const evidenceReady = isCoverageEvidenceReady(caseRow);
  if (evidenceReady && !isSlotFilled(filled.policy_evidence_status)) {
    filled.policy_evidence_status = { ...POLICY_EVIDENCE_SATISFIED };
  }

  const safetyNotes: string[] = [];
  if (detectHighRisk(filled.risk_indicators)) {
    safetyNotes.push('Indício de risco elétrico alto — orientar segurança e considerar handoff humano.');
  }
  safetyNotes.push('Ação externa bloqueada neste MVP (dry-run/HITL).');
  safetyNotes.push('Não confirmar cobertura sem evidência de apólice.');

  const currentPhase = typeof run?.phase === 'string' ? run.phase : null;
  const currentStatus = typeof caseRow?.status === 'string' ? caseRow.status : null;

  const selectedSlot = selectNextSlot(filled, slotPriority);

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
      nextStep: evidenceReady ? COMPLETE_NEXT_STEP_WITH_EVIDENCE : COMPLETE_NEXT_STEP_NO_EVIDENCE,
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
