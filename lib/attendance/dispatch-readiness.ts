// Dispatch Readiness + Packet Builder (42B6) — PURO, sem I/O.
//
// Prepara um "pacote de acionamento" em modo dry-run/HITL: avalia se o caso
// está pronto, aplica o COVERAGE GATE (do 42I3B) e monta um packet sanitizado.
// NUNCA envia nada (WhatsApp/seguradora/prestador), NUNCA decide autorização por
// LLM, NUNCA expõe CPF/nome completo/telefone/endereço completos/payload bruto.
//
// `external_action_allowed`/`external_action_sent` são SEMPRE false neste batch.

// Primitivos locais (espelham corridor-runtime.isSlotFilled / handoff-dossier
// .normalizeSlots/.maskPhone) — mantidos aqui para o módulo ser puro/autocontido
// (testável no Node sem resolução de imports extensionless). Comportamento idêntico.
function isSlotFilled(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (typeof value === 'boolean') return true;
  if (typeof value === 'number') return true;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0;
  return true;
}

function normalizeSlots(slots: unknown): { filled: Record<string, unknown>; missing: string[]; conflicts: unknown[] } {
  const s = slots && typeof slots === 'object' && !Array.isArray(slots) ? (slots as Record<string, any>) : {};
  const filled = s.filled && typeof s.filled === 'object' && !Array.isArray(s.filled) ? (s.filled as Record<string, unknown>) : {};
  const missing = Array.isArray(s.missing) ? s.missing.filter((x: unknown): x is string => typeof x === 'string') : [];
  const conflicts = Array.isArray(s.conflicts) ? s.conflicts : [];
  return { filled, missing, conflicts };
}

function maskPhone(value?: string | null): string {
  const r = (value || '').trim();
  if (!r) return '';
  const digits = r.replace(/\D/g, '');
  if (digits.length < 6) return r;
  return `${r.slice(0, 4)}****${r.slice(-4)}`;
}

// Estado humano-legível do packet (mapeado depois p/ status do banco).
export type DispatchPacketState =
  | 'incomplete' // faltam slots operacionais
  | 'blocked' // risco alto / apólice cancelada-vencida / cobertura reprovada
  | 'hitl_required' // cobertura não confirmada → precisa validação humana
  | 'ready_for_human_approval'; // tudo pronto → aguardando aprovação humana p/ envio

export interface DispatchReadiness {
  identity_ready: boolean;
  policy_selected: boolean;
  policy_verified: boolean;
  coverage_confirmed: boolean;
  human_validation_required: boolean;
  risk_ok: boolean;
  required_slots_ready: boolean;
  address_ready: boolean;
  contact_ready: boolean;
  dispatch_allowed: boolean; // pode ser aprovado p/ envio (ainda dry-run/HITL no MVP)
  hitl_required: boolean;
  packet_state: DispatchPacketState;
  missing_slots: string[];
  blockers: string[];
  warnings: string[];
}

// Slots operacionais exigidos para acionar (policy_evidence_status é satisfeito
// pela evidência; risk_indicators é gate de segurança, não operacional).
const DEFAULT_REQUIRED_SLOTS = ['affected_area', 'electrical_issue_type', 'property_address_confirmed'];

function identityDigits(caseRow: any): number {
  const d = typeof caseRow?.insured_document_ref === 'string' ? caseRow.insured_document_ref.replace(/\D/g, '') : '';
  return d.length;
}

export interface DispatchReadinessInput {
  caseRow: any;
  run: any;
  coverageReadiness: any; // metadata.coverage_readiness (42I3B)
  evidencePack?: any; // metadata.policy_evidence_pack (summary)
  requiredSlots?: readonly string[];
}

/** Avalia a prontidão operacional + gate de cobertura para acionamento. PURO. */
export function evaluateDispatchReadiness(input: DispatchReadinessInput): DispatchReadiness {
  const { caseRow, run, coverageReadiness: cr } = input;
  const filled = normalizeSlots(run?.slots).filled;
  const requiredSlots =
    input.requiredSlots && input.requiredSlots.length > 0
      ? input.requiredSlots.filter((k) => k !== 'policy_evidence_status' && k !== 'risk_indicators')
      : DEFAULT_REQUIRED_SLOTS;

  const dlen = identityDigits(caseRow);
  const identity_ready = dlen === 11 || dlen === 14;
  const policy_selected = Boolean(
    caseRow?.metadata?.policy_select?.selected_policy_ref || input.evidencePack?.policy_ref,
  );
  const verification = typeof caseRow?.verification_status === 'string' ? caseRow.verification_status : '';
  const policy_verified = verification.startsWith('verified');

  const crState = typeof cr?.state === 'string' ? cr.state : null;
  const coverage_confirmed =
    cr?.coverage_confirmed === true || crState === 'coverage_confirmed' || crState === 'human_approved';
  const coverageBlocked = crState === 'blocked' || crState === 'human_rejected';
  const human_validation_required =
    cr?.human_required === true || crState === 'human_validation_required' || crState === 'needs_more_info';

  const risk_ok = caseRow?.risk_level !== 'high' && caseRow?.status !== 'handoff';

  const missing_slots = requiredSlots.filter((k) => !isSlotFilled(filled[k]));
  const required_slots_ready = missing_slots.length === 0;
  const address_ready = isSlotFilled(filled.property_address_confirmed) || Boolean(caseRow?.insured_address);
  const contact_ready = Boolean(caseRow?.customer_phone);

  const blockers: string[] = [];
  const warnings: string[] = [];

  if (!risk_ok) blockers.push('high_risk_or_handoff');
  if (!identity_ready) blockers.push('identity_missing');
  if (!policy_selected) blockers.push('policy_not_selected');
  if (!policy_verified) blockers.push('policy_not_verified');
  if (crState === 'blocked') blockers.push('policy_cancelled_or_expired');
  if (crState === 'human_rejected') blockers.push('coverage_rejected_by_human');

  if (!coverage_confirmed && !coverageBlocked) warnings.push('coverage_not_confirmed');
  if (human_validation_required) warnings.push('human_validation_required');
  if (missing_slots.length > 0) warnings.push('missing_required_slots');
  if (!address_ready) warnings.push('address_not_confirmed');
  if (!contact_ready) warnings.push('contact_missing');

  // Precedência: blocked > incomplete > hitl_required > ready_for_human_approval
  let packet_state: DispatchPacketState;
  if (!risk_ok || coverageBlocked || !identity_ready || !policy_selected || !policy_verified) {
    packet_state = 'blocked';
  } else if (!required_slots_ready) {
    packet_state = 'incomplete';
  } else if (!coverage_confirmed || human_validation_required) {
    packet_state = 'hitl_required';
  } else {
    packet_state = 'ready_for_human_approval';
  }

  const dispatch_allowed = packet_state === 'ready_for_human_approval';
  const hitl_required = packet_state === 'hitl_required' || packet_state === 'ready_for_human_approval' || packet_state === 'blocked';

  return {
    identity_ready,
    policy_selected,
    policy_verified,
    coverage_confirmed,
    human_validation_required,
    risk_ok,
    required_slots_ready,
    address_ready,
    contact_ready,
    dispatch_allowed,
    hitl_required,
    packet_state,
    missing_slots,
    blockers,
    warnings,
  };
}

// Status permitidos pela tabela dispatch_packets (CHECK do 42B3).
export type DispatchPacketDbStatus =
  | 'draft'
  | 'missing_data'
  | 'ready_for_approval'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'sent_dry_run'
  | 'sent_real'
  | 'failed'
  | 'cancelled';

/** Mapeia o estado humano-legível do packet para o status permitido no banco. */
export function dbStatusForPacketState(state: DispatchPacketState): DispatchPacketDbStatus {
  switch (state) {
    case 'incomplete':
      return 'missing_data';
    case 'blocked':
      return 'awaiting_approval'; // bloqueado → precisa decisão humana (sem enviar)
    case 'hitl_required':
      return 'awaiting_approval';
    case 'ready_for_human_approval':
      return 'ready_for_approval';
    default:
      return 'draft';
  }
}

function recommendedAction(state: DispatchPacketState): string {
  switch (state) {
    case 'incomplete':
      return 'collect_remaining_slots';
    case 'blocked':
      return 'human_review_required';
    case 'hitl_required':
      return 'human_coverage_validation';
    case 'ready_for_human_approval':
      return 'await_human_approval_to_dispatch';
    default:
      return 'review';
  }
}

/** Resumo de endereço PARCIAL/mascarado (cidade/estado/bairro; nunca rua+número). */
export function maskAddressSummary(caseRow: any, filled: Record<string, unknown>): string | null {
  const addr =
    caseRow?.insured_address && typeof caseRow.insured_address === 'object' && !Array.isArray(caseRow.insured_address)
      ? (caseRow.insured_address as Record<string, unknown>)
      : {};
  const city = typeof addr.city === 'string' ? addr.city : typeof addr.cidade === 'string' ? addr.cidade : null;
  const state = typeof addr.state === 'string' ? addr.state : typeof addr.uf === 'string' ? addr.uf : null;
  const district =
    typeof addr.district === 'string' ? addr.district : typeof addr.bairro === 'string' ? addr.bairro : null;
  const parts = [district, city, state].filter(Boolean);
  if (parts.length) return parts.join(' / ');
  // fallback: apenas se o slot confirma o endereço da apólice (sem expor texto cru)
  if (isSlotFilled(filled.property_address_confirmed)) return 'endereço da apólice (confirmado, detalhe omitido)';
  return null;
}

export interface DispatchPacketInput {
  caseRow: any;
  run: any;
  template?: any;
  evidencePack?: any;
  coverageReadiness?: any;
  readiness: DispatchReadiness;
  generatedAt: string;
}

/** Monta o Dispatch Packet sanitizado (sem CPF/nome completo/telefone/endereço crus). */
export function buildDispatchPacket(input: DispatchPacketInput): Record<string, unknown> {
  const { caseRow: c, run, template: tpl, evidencePack: ep, coverageReadiness: cr, readiness, generatedAt } = input;
  const slots = normalizeSlots(run?.slots);
  const coverage = c?.coverage_evidence && typeof c.coverage_evidence === 'object' ? c.coverage_evidence : null;

  return {
    case_id: c?.id ?? null,
    case_number: c?.case_number ?? null,
    company_id: c?.company_id ?? null,
    corridor: c?.selected_corridor_key || tpl?.corridor_key || null,
    subcorridor: c?.selected_subcorridor_key || tpl?.subcorridor_key || null,
    service_type: 'electrician',
    insurer: ep?.insurer_detected || c?.insurer_key || null,
    product: ep?.product_detected || null,
    selected_policy_ref: c?.metadata?.policy_select?.selected_policy_ref || ep?.policy_ref || null,
    masked_policy_number: ep?.masked_policy_number || null,
    policy_status: ep?.policy_status || null,
    coverage_summary: typeof coverage?.coverage_summary === 'string' ? coverage.coverage_summary : null,
    coverage_readiness: cr ? { state: cr.state ?? null, dispatch_allowed: cr.dispatch_allowed === true } : null,
    required_slots: readiness.required_slots_ready
      ? Object.keys(slots.filled).filter((k) => k !== 'policy_evidence_status')
      : undefined,
    collected_slots: Object.keys(slots.filled),
    missing_slots: readiness.missing_slots,
    risk_summary: { risk_level: c?.risk_level ?? null, risk_ok: readiness.risk_ok },
    customer_contact_ref: c?.customer_phone ? maskPhone(c.customer_phone) : null,
    address_summary: maskAddressSummary(c, slots.filled),
    human_validation_required: readiness.human_validation_required || readiness.hitl_required,
    recommended_action: recommendedAction(readiness.packet_state),
    status: readiness.packet_state,
    external_action_allowed: false,
    external_action_sent: false,
    audit_notes: [
      'Dispatch preparado em modo dry-run/HITL. Nenhuma ação externa foi executada.',
      'Cobertura específica só é afirmada com evidência; caso contrário exige validação humana.',
    ],
    generated_at: generatedAt,
  };
}
