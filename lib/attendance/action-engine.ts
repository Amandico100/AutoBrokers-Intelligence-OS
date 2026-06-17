// Global External Action Engine (42X0) — PURO, channel-agnostic, dry-run.
//
// Lê dispatch_packet/coverage_readiness/dispatch_readiness e monta um
// ExternalActionPlan: avalia canais, escolhe o recomendado, lista dados
// faltantes, gera draft (mascarado) e interpreta respostas SIMULADAS da
// seguradora. NUNCA envia nada: `external_action_sent` é sempre false; todo
// side effect real exigirá adapter + permissão + HITL + flag (42X1+).

// --- Playbooks (inline; self-contained p/ testes Node sem resolução de import) ---
export type ActionChannel =
  | 'insurer_whatsapp'
  | 'insurer_portal'
  | 'insurer_phone_0800'
  | 'insurer_email'
  | 'insurer_api'
  | 'human_broker_manual';

export interface ActionPlaybook {
  playbook_id: string;
  scope: 'global' | 'insurer' | 'corridor' | 'tenant';
  channel: ActionChannel;
  insurer_key?: string | null;
  corridor_key?: string | null;
  subcorridor_key?: string | null;
  objective: string;
  opening_message_template: string;
  required_payload_fields: string[];
  expected_questions: string[];
  response_interpretation_rules: string[];
  fallback_rules: string[];
  escalation_rules: string[];
  forbidden_actions: string[];
}

const COMMON_FORBIDDEN = [
  'enviar mensagem real sem adapter + permissão + HITL',
  'confirmar cobertura sem evidência oficial',
  'expor CPF/telefone/endereço completos',
  'prometer prazo/protocolo sem retorno real',
];

const ALLIANZ_ELECTRICIAN_WHATSAPP: ActionPlaybook = {
  playbook_id: 'allianz_residential_electrician_whatsapp_v1',
  scope: 'corridor',
  channel: 'insurer_whatsapp',
  insurer_key: 'allianz',
  corridor_key: 'allianz_residential_assistance',
  subcorridor_key: 'electrician',
  objective: 'Abrir acionamento de assistência elétrica residencial junto à seguradora.',
  opening_message_template:
    'Olá, sou da corretora. Preciso abrir um atendimento de assistência residencial para a {insurer} (apólice final {masked_policy}). O segurado relata {problem} em {area}, sem sinais de fumaça, faísca ou cheiro de queimado. Pode me orientar o procedimento para acionamento de eletricista?',
  required_payload_fields: ['insurer', 'masked_policy_number', 'affected_area', 'electrical_issue_type', 'risk_ok'],
  expected_questions: ['número da apólice', 'CPF do segurado', 'endereço do imóvel', 'telefone de contato', 'há risco/fumaça?'],
  response_interpretation_rules: [
    'se pedirem dado faltante → coletar do segurado/humano (mascarado quando sensível)',
    'se redirecionarem ao portal → trocar canal recomendado',
    'se pedirem documento → encaminhar evidência de documento',
    'se perguntarem cobertura → não afirmar; manter validação',
  ],
  fallback_rules: ['se canal indisponível → human_broker_manual', 'se ambíguo → needs_human_review'],
  escalation_rules: ['risco alto → handoff humano imediato', 'conflito documento×InfoCap → validação humana'],
  forbidden_actions: COMMON_FORBIDDEN,
};

function genericManualPlaybook(insurerKey: string | null, corridorKey: string | null, subcorridorKey: string | null): ActionPlaybook {
  return {
    playbook_id: 'generic_manual_v1',
    scope: 'global',
    channel: 'human_broker_manual',
    insurer_key: insurerKey,
    corridor_key: corridorKey,
    subcorridor_key: subcorridorKey,
    objective: 'Preparar dossiê de acionamento para tratativa humana (canal específico ainda não homologado).',
    opening_message_template:
      'Dossiê de acionamento preparado para a equipe: {insurer} (apólice final {masked_policy}), {problem} em {area}. Acionamento externo aguardando homologação de canal.',
    required_payload_fields: ['insurer', 'masked_policy_number', 'affected_area'],
    expected_questions: [],
    response_interpretation_rules: ['tratativa conduzida por humano'],
    fallback_rules: ['sempre disponível como último recurso'],
    escalation_rules: ['risco alto → handoff humano imediato'],
    forbidden_actions: COMMON_FORBIDDEN,
  };
}

/** Seleciona o playbook mais específico disponível (corredor>seguradora>global). PURO. */
export function getPlaybook(input: {
  insurerKey?: string | null;
  corridorKey?: string | null;
  subcorridorKey?: string | null;
  channel?: ActionChannel | null;
}): ActionPlaybook {
  const ins = (input.insurerKey || '').toLowerCase();
  const sub = (input.subcorridorKey || '').toLowerCase();
  const corr = (input.corridorKey || '').toLowerCase();
  if (
    (input.channel == null || input.channel === 'insurer_whatsapp') &&
    ins === 'allianz' &&
    corr === 'allianz_residential_assistance' &&
    sub === 'electrician'
  ) {
    return ALLIANZ_ELECTRICIAN_WHATSAPP;
  }
  return genericManualPlaybook(input.insurerKey ?? null, input.corridorKey ?? null, input.subcorridorKey ?? null);
}

function humanInsurer(k?: string | null): string {
  const v = (k || '').toLowerCase();
  const map: Record<string, string> = { allianz: 'Allianz', porto: 'Porto Seguro', azul: 'Azul', hdi: 'HDI', tokio: 'Tokio Marine', bradesco: 'Bradesco', mapfre: 'Mapfre' };
  return map[v] || (k ? k.charAt(0).toUpperCase() + k.slice(1) : 'a seguradora');
}

/** Monta a mensagem-draft para a seguradora (mascarada). PURO. Nunca CPF/telefone/endereço cru. */
export function buildInsurerMessageDraft(
  playbook: ActionPlaybook,
  data: { insurer?: string | null; masked_policy_number?: string | null; affected_area?: string | null; problem?: string | null },
): string {
  const insurer = humanInsurer(data.insurer);
  const masked = (data.masked_policy_number || '****').replace(/[^\d*]/g, '') || '****';
  // Normaliza a área (slot pode vir com filler: "é na cozinha" → "cozinha").
  const rawArea = (data.affected_area || '').toString().trim();
  const cleanArea = rawArea.replace(/^(é\s+|s[óo]\s+|na\s+|no\s+|em\s+|aqui\s+(na|no)\s+)+/i, '').trim();
  const area = cleanArea || 'no imóvel';
  const problem = (data.problem && data.problem.trim()) || 'um problema na residência';
  return playbook.opening_message_template
    .replace('{insurer}', insurer)
    .replace('{masked_policy}', masked)
    .replace('{area}', area)
    .replace('{problem}', problem);
}

export type ActionPlanStatus = 'incomplete' | 'blocked' | 'hitl_required' | 'ready_for_human_approval';

export interface ChannelCandidate {
  channel: ActionChannel;
  priority: number;
  available_now: boolean;
  reason: string;
  requires: string;
  risk: 'low' | 'medium' | 'high';
  current_mode: 'dry_run' | 'not_configured' | 'future';
  // 42X3.1 — enriquecido quando há config de canal resolvida no registry:
  provider_key?: string | null;
  config_id?: string | null;
  destination_ref_masked?: string | null;
  homologation_status?: string | null;
}

/**
 * Config de canal resolvida (forma "lite", sem acoplar o engine ao registry —
 * a rota a constrói a partir do InsurerActionChannelConfig). 42X3.1.
 */
export interface PlanChannelConfig {
  config_id: string;
  provider_key: string;
  provider_label?: string | null;
  channel: 'insurer_whatsapp' | 'manual';
  destination_ref_masked: string | null;
  homologation_status: string;
  provider_payload?: Record<string, unknown> | null;
}

export interface ExternalActionPlan {
  case_id: string | null;
  dispatch_packet_id: string | null;
  corridor_key: string | null;
  subcorridor_key: string | null;
  insurer_key: string | null;
  channel_candidates: ChannelCandidate[];
  selected_channel: ActionChannel | null;
  action_goal: string;
  required_data: string[];
  available_data: string[];
  missing_data: string[];
  readiness: { packet_state: string | null; dispatch_allowed: boolean };
  coverage_gate: { state: string | null; human_required: boolean };
  hitl_gate: { required: boolean; reason: string | null };
  planned_steps: string[];
  message_drafts: Array<{ channel: ActionChannel; text: string }>;
  fallback_steps: string[];
  human_review_required: boolean;
  risk_flags: string[];
  allowed_to_prepare: boolean;
  status: ActionPlanStatus;
  playbook_id: string;
  dry_run: true;
  external_action_sent: false;
  // 42X3.1 — config de canal/provider resolvida (alinha plan→execution→outbox):
  selected_config_id: string | null;
  selected_provider_key: string | null;
  selected_provider_label: string | null;
  selected_destination_ref_masked: string | null;
  selected_homologation_status: string | null;
  selected_provider_payload: Record<string, unknown> | null;
  channel_config_source: 'registry' | 'fallback_manual' | 'none';
}

export interface ChannelAvailability {
  insurer_whatsapp?: boolean;
  insurer_portal?: boolean;
  insurer_phone_0800?: boolean;
  insurer_email?: boolean;
  insurer_api?: boolean;
  human_destination?: boolean;
}

/** Avalia canais candidatos (PURO). No MVP, canais da seguradora ficam dry_run/future. */
export function evaluateChannelCandidates(avail: ChannelAvailability): ChannelCandidate[] {
  const c: ChannelCandidate[] = [
    {
      channel: 'insurer_whatsapp',
      priority: 1,
      available_now: false, // nunca "agora" no 42X0 (sem envio real)
      reason: avail.insurer_whatsapp ? 'conexão WhatsApp da seguradora configurada (dry-run)' : 'WhatsApp da seguradora não configurado',
      requires: 'tenant_connection (whatsapp seguradora)',
      risk: 'medium',
      current_mode: avail.insurer_whatsapp ? 'dry_run' : 'not_configured',
    },
    {
      channel: 'insurer_portal',
      priority: 2,
      available_now: false,
      reason: avail.insurer_portal ? 'portal configurado (dry-run; sem acesso real)' : 'portal não configurado',
      requires: 'connector portal + automação homologada',
      risk: 'high',
      current_mode: avail.insurer_portal ? 'dry_run' : 'future',
    },
    {
      channel: 'insurer_phone_0800',
      priority: 3,
      available_now: false,
      reason: 'discagem 0800 não disponível neste estágio',
      requires: 'integração de voz futura',
      risk: 'high',
      current_mode: 'future',
    },
    {
      channel: 'insurer_email',
      priority: 4,
      available_now: false,
      reason: avail.insurer_email ? 'e-mail configurado (dry-run)' : 'e-mail não configurado',
      requires: 'remetente/endereço homologado',
      risk: 'medium',
      current_mode: avail.insurer_email ? 'dry_run' : 'future',
    },
    {
      channel: 'insurer_api',
      priority: 5,
      available_now: false,
      reason: avail.insurer_api ? 'API da seguradora configurada (dry-run)' : 'API não disponível',
      requires: 'connector API homologado',
      risk: 'medium',
      current_mode: avail.insurer_api ? 'dry_run' : 'future',
    },
    {
      channel: 'human_broker_manual',
      priority: 9,
      available_now: avail.human_destination !== false, // fallback sempre disponível
      reason: 'tratativa humana (fallback sempre disponível)',
      requires: 'operador/destino humano',
      risk: 'low',
      current_mode: 'dry_run',
    },
  ];
  return c.sort((a, b) => a.priority - b.priority);
}

function slotFilled(filled: Record<string, unknown>, key: string): boolean {
  const v = filled[key];
  if (v === null || v === undefined) return false;
  if (typeof v === 'string') return v.trim().length > 0;
  if (typeof v === 'object') return Object.keys(v as Record<string, unknown>).length > 0;
  return true;
}

export interface BuildPlanInput {
  caseRow: any;
  dispatchPacket: any; // payload/metadata do dispatch_packet
  filledSlots?: Record<string, unknown>;
  channels: ChannelCandidate[];
  activeChannelConfig?: PlanChannelConfig | null; // 42X3.1 — config resolvida do registry
}

/** Mapeia o canal do registry ('manual') para o ActionChannel do engine. */
function mapConfigChannel(ch: 'insurer_whatsapp' | 'manual'): ActionChannel {
  return ch === 'insurer_whatsapp' ? 'insurer_whatsapp' : 'human_broker_manual';
}

/** Monta o ExternalActionPlan a partir do dispatch_packet + gates. PURO. dry-run sempre. */
export function buildExternalActionPlan(input: BuildPlanInput): ExternalActionPlan {
  const { caseRow: c, dispatchPacket: dp, channels } = input;
  const filled = input.filledSlots || {};
  const md = c?.metadata && typeof c.metadata === 'object' ? c.metadata : {};
  const cr = md.coverage_readiness && typeof md.coverage_readiness === 'object' ? md.coverage_readiness : {};
  const dr = md.dispatch_readiness && typeof md.dispatch_readiness === 'object' ? md.dispatch_readiness : {};
  const snap = c?.policy_snapshot && typeof c.policy_snapshot === 'object' ? c.policy_snapshot : {};
  const packetState: string | null = dr.packet_state ?? (dp?.metadata?.packet_state ?? null);

  const playbook: ActionPlaybook = getPlaybook({
    insurerKey: c?.insurer_key ?? snap.insurer_key ?? null,
    corridorKey: c?.selected_corridor_key ?? null,
    subcorridorKey: c?.selected_subcorridor_key ?? null,
    channel: 'insurer_whatsapp',
  });

  // Dados disponíveis vs exigidos pelo playbook.
  const available: string[] = [];
  const missing: string[] = [];
  for (const field of playbook.required_payload_fields) {
    let has = false;
    if (field === 'insurer') has = Boolean(c?.insurer_key || snap.insurer_key);
    else if (field === 'masked_policy_number') has = Boolean(snap.masked_policy_number);
    else if (field === 'risk_ok') has = c?.risk_level !== 'high';
    else has = slotFilled(filled, field);
    (has ? available : missing).push(field);
  }

  // Gates → status.
  const coverageHuman = cr.human_required === true;
  const coverageState: string | null = cr.state ?? null;
  let status: ActionPlanStatus;
  let allowed = false;
  let humanReview = false;
  const riskFlags: string[] = [];
  if (c?.risk_level === 'high') riskFlags.push('high_risk');
  if (md.document_infocap_conflict) riskFlags.push('document_infocap_conflict');

  if (packetState === 'blocked' || c?.risk_level === 'high') {
    status = 'blocked';
    humanReview = true;
  } else if (packetState === 'incomplete' || missing.length > 0) {
    status = 'incomplete';
  } else if (packetState === 'ready_for_human_approval' && !coverageHuman) {
    status = 'ready_for_human_approval';
    allowed = true;
  } else {
    // hitl_required ou cobertura ainda não validada
    status = 'hitl_required';
    humanReview = true;
  }

  // 42X3.1 — config de canal/provider resolvida (registry). Quando presente,
  // ela dita o canal selecionado e enriquece o candidate correspondente.
  const cfg = input.activeChannelConfig ?? null;
  const cfgChannel: ActionChannel | null = cfg ? mapConfigChannel(cfg.channel) : null;
  const enrichedChannels: ChannelCandidate[] = channels.map((ch) =>
    cfg && ch.channel === cfgChannel
      ? {
          ...ch,
          current_mode: 'dry_run',
          provider_key: cfg.provider_key,
          config_id: cfg.config_id,
          destination_ref_masked: cfg.destination_ref_masked,
          homologation_status: cfg.homologation_status,
          reason: `config ${cfg.provider_key} (${cfg.homologation_status}) — sandbox/dry-run`,
        }
      : ch,
  );

  // Canal recomendado: config resolvida vence; senão maior prioridade dry_run; senão manual.
  let selected: ActionChannel | null;
  if (cfg && cfgChannel) {
    selected = cfgChannel;
  } else {
    const preferred = enrichedChannels.find((ch) => ch.current_mode === 'dry_run' && ch.channel !== 'human_broker_manual')
      || enrichedChannels.find((ch) => ch.channel === 'human_broker_manual')
      || null;
    selected = preferred ? preferred.channel : null;
  }

  // Drafts só quando pronto p/ aprovação humana (dry-run).
  const drafts: Array<{ channel: ActionChannel; text: string }> = [];
  if (allowed && selected) {
    const draftPlaybook = getPlaybook({ insurerKey: c?.insurer_key ?? snap.insurer_key, corridorKey: c?.selected_corridor_key, subcorridorKey: c?.selected_subcorridor_key, channel: selected });
    drafts.push({
      channel: selected,
      text: buildInsurerMessageDraft(draftPlaybook, {
        insurer: c?.insurer_key ?? snap.insurer_key,
        masked_policy_number: snap.masked_policy_number,
        affected_area: typeof filled.affected_area === 'string' ? filled.affected_area : null,
        problem: typeof filled.electrical_issue_type === 'string' ? filled.electrical_issue_type : 'um problema na residência',
      }),
    });
  }

  const plannedSteps: string[] = [];
  if (status === 'incomplete') plannedSteps.push(`coletar dados faltantes: ${missing.join(', ')}`);
  else if (status === 'blocked') plannedSteps.push('revisão humana (risco/apólice/conflito) antes de qualquer acionamento');
  else if (status === 'hitl_required') plannedSteps.push('aguardar validação humana de cobertura', 'após validação, preparar acionamento dry-run');
  else if (status === 'ready_for_human_approval') plannedSteps.push(`preparar mensagem para ${selected}`, 'aguardar aprovação humana de envio (dry-run)');

  return {
    case_id: c?.id ?? null,
    dispatch_packet_id: dp?.id ?? null,
    corridor_key: c?.selected_corridor_key ?? null,
    subcorridor_key: c?.selected_subcorridor_key ?? null,
    insurer_key: c?.insurer_key ?? snap.insurer_key ?? null,
    channel_candidates: enrichedChannels,
    selected_channel: selected,
    action_goal: playbook.objective,
    required_data: playbook.required_payload_fields,
    available_data: available,
    missing_data: missing,
    readiness: { packet_state: packetState, dispatch_allowed: dr.dispatch_allowed === true },
    coverage_gate: { state: coverageState, human_required: coverageHuman },
    hitl_gate: { required: humanReview || coverageHuman, reason: humanReview ? (status === 'blocked' ? 'blocked' : 'coverage_validation') : null },
    planned_steps: plannedSteps,
    message_drafts: drafts,
    fallback_steps: ['human_broker_manual (dossiê + tratativa humana)'],
    human_review_required: humanReview,
    risk_flags: riskFlags,
    allowed_to_prepare: allowed,
    status,
    playbook_id: playbook.playbook_id,
    dry_run: true,
    external_action_sent: false,
    selected_config_id: cfg?.config_id ?? null,
    selected_provider_key: cfg && selected === cfgChannel ? cfg.provider_key : null,
    selected_provider_label: cfg && selected === cfgChannel ? (cfg.provider_label ?? cfg.provider_key) : null,
    selected_destination_ref_masked: cfg && selected === cfgChannel ? cfg.destination_ref_masked : null,
    selected_homologation_status: cfg && selected === cfgChannel ? cfg.homologation_status : null,
    selected_provider_payload: cfg?.provider_payload ?? null,
    channel_config_source: cfg ? 'registry' : selected === 'human_broker_manual' ? 'fallback_manual' : 'none',
  };
}

export type InsurerReplyClassification =
  | 'accepted'
  | 'asks_for_missing_data'
  | 'coverage_question'
  | 'requests_document'
  | 'redirects_channel'
  | 'unavailable'
  | 'human_required'
  | 'unknown';

export type ActionNextStep =
  | 'ask_insured'
  | 'ask_human'
  | 'update_action_plan'
  | 'retry_message'
  | 'wait'
  | 'manual_handoff';

export interface InsurerReplyInterpretation {
  classification: InsurerReplyClassification;
  next_step: ActionNextStep;
  missing_data_request: string | null;
  suggested_channel: ActionChannel | null;
  customer_message: string | null;
  reasoning: string;
}

const RE = {
  policy: /\b(n[úu]mero da ap[óo]lice|qual.*ap[óo]lice|informe a ap[óo]lice)\b/i,
  cpf: /\bcpf\b/i,
  address: /\b(endere[çc]o|cep|onde fica|local do im[óo]vel)\b/i,
  phone: /\b(telefone|contato|n[úu]mero do segurado|whats do segurado)\b/i,
  portal: /\b(portal|pelo site|acesse o site|sistema online|abra um chamado no portal)\b/i,
  unavailable: /\b(n[ãa]o (fazemos|atendemos|realizamos)|fora de cobertura deste canal|n[ãa]o é por aqui|canal incorreto)\b/i,
  document: /\b(envie (a|o) (ap[óo]lice|documento|comprovante)|precisamos do documento|anexe)\b/i,
  coverage: /\b(cobertura|est[áa] coberto|tem direito|cobre\b)\b/i,
  accepted: /\b(recebido|protocolo|abrimos|encaminhad|vamos providenciar|registrado|acionamento aberto|chamado aberto)\b/i,
};

/** Interpreta a resposta SIMULADA da seguradora (PURO; sem side effect). */
export function interpretInsurerReply(reply: string, ctx: { hasPolicyNumber?: boolean } = {}): InsurerReplyInterpretation {
  const r = (reply || '').trim();
  if (!r) return { classification: 'unknown', next_step: 'ask_human', missing_data_request: null, suggested_channel: null, customer_message: null, reasoning: 'empty_reply' };
  const m = r.toLowerCase();

  if (RE.unavailable.test(m)) {
    return { classification: 'unavailable', next_step: 'manual_handoff', missing_data_request: null, suggested_channel: 'human_broker_manual', customer_message: 'A seguradora indicou que esse canal não trata esse tipo de atendimento. Vou encaminhar para nossa equipe seguir pelo caminho correto.', reasoning: 'channel_unavailable' };
  }
  if (RE.portal.test(m)) {
    return { classification: 'redirects_channel', next_step: 'update_action_plan', missing_data_request: null, suggested_channel: 'insurer_portal', customer_message: 'A seguradora pediu para seguir pelo portal. Vou preparar esse caminho com a nossa equipe.', reasoning: 'redirect_portal' };
  }
  if (RE.document.test(m)) {
    return { classification: 'requests_document', next_step: 'ask_insured', missing_data_request: 'documento/apólice', suggested_channel: null, customer_message: 'A seguradora pediu um documento. Você pode me enviar a apólice ou o comprovante?', reasoning: 'requests_document' };
  }
  if (RE.cpf.test(m)) {
    return { classification: 'asks_for_missing_data', next_step: 'ask_human', missing_data_request: 'cpf', suggested_channel: null, customer_message: 'A seguradora pediu um dado adicional do segurado. Vou confirmar isso com segurança pela nossa equipe.', reasoning: 'asks_cpf_sensitive' };
  }
  if (RE.policy.test(m)) {
    return { classification: 'asks_for_missing_data', next_step: ctx.hasPolicyNumber ? 'update_action_plan' : 'ask_human', missing_data_request: 'policy_number', suggested_channel: null, customer_message: 'A seguradora pediu o número da apólice. Vou providenciar com a nossa equipe.', reasoning: 'asks_policy_number' };
  }
  if (RE.address.test(m)) {
    return { classification: 'asks_for_missing_data', next_step: 'ask_insured', missing_data_request: 'endereço', suggested_channel: null, customer_message: 'A seguradora precisa confirmar o endereço do imóvel. Pode me confirmar o endereço, por favor?', reasoning: 'asks_address' };
  }
  if (RE.phone.test(m)) {
    return { classification: 'asks_for_missing_data', next_step: 'ask_insured', missing_data_request: 'contact_phone', suggested_channel: null, customer_message: 'A seguradora pediu um telefone de contato. Qual o melhor número para contato?', reasoning: 'asks_phone' };
  }
  if (RE.coverage.test(m)) {
    return { classification: 'coverage_question', next_step: 'ask_human', missing_data_request: null, suggested_channel: null, customer_message: 'A seguradora levantou um ponto de cobertura. Nossa equipe vai validar isso antes de seguir, para evitar erro.', reasoning: 'coverage_question' };
  }
  if (RE.accepted.test(m)) {
    return { classification: 'accepted', next_step: 'wait', missing_data_request: null, suggested_channel: null, customer_message: 'A seguradora sinalizou que recebeu as informações. Vou acompanhar os próximos passos.', reasoning: 'accepted' };
  }
  return { classification: 'unknown', next_step: 'ask_human', missing_data_request: null, suggested_channel: null, customer_message: 'Recebi uma resposta da seguradora que preciso revisar com a nossa equipe antes de seguir.', reasoning: 'ambiguous' };
}

// ===========================================================================
// External Action EXECUTION (42X1) — máquina de estado sandbox/dry-run.
// NUNCA envia real: canSendReal=false; external_action_sent=false sempre.
// ===========================================================================

export type ExecutionStatus =
  | 'draft'
  | 'approved_for_sandbox'
  | 'running_sandbox'
  | 'waiting_insurer'
  | 'waiting_insured'
  | 'waiting_human'
  | 'completed_sandbox'
  | 'failed_sandbox'
  | 'cancelled';

export type ExecutionMode = 'sandbox' | 'dry_run' | 'real_future';

export interface ExecutionEvent {
  at: string;
  type: string;
  classification?: string | null;
  next_step?: string | null;
  note?: string | null;
  excerpt?: string | null; // mascarado/truncado
}

export interface ExternalActionExecutionSession {
  execution_id: string;
  case_id: string | null;
  dispatch_packet_id: string | null;
  status: ExecutionStatus;
  mode: ExecutionMode;
  channel: ActionChannel | null;
  adapter: string;
  current_step: string;
  last_event_at: string;
  events: ExecutionEvent[];
  insurer_thread_ref: string | null;
  next_required_input: string | null;
  customer_update: string | null;
  human_review_required: boolean;
  suggested_channel: ActionChannel | null;
  prepared_message: string | null; // mascarado
  external_action_sent: false;
}

export interface ChannelAdapter {
  channel: ActionChannel;
  adapter_id: string;
  mode: ExecutionMode;
  canSendReal: false;
}

/** Adapters por canal (sandbox/future). NENHUM envia real neste estágio. */
export function getChannelAdapter(channel: ActionChannel | null): ChannelAdapter {
  switch (channel) {
    case 'insurer_whatsapp':
      return { channel, adapter_id: 'insurer_whatsapp_sandbox', mode: 'sandbox', canSendReal: false };
    case 'human_broker_manual':
      return { channel, adapter_id: 'human_manual_sandbox', mode: 'sandbox', canSendReal: false };
    case 'insurer_portal':
      return { channel, adapter_id: 'portal_future', mode: 'real_future', canSendReal: false };
    case 'insurer_phone_0800':
      return { channel, adapter_id: 'phone_0800_future', mode: 'real_future', canSendReal: false };
    case 'insurer_email':
      return { channel, adapter_id: 'email_future', mode: 'real_future', canSendReal: false };
    case 'insurer_api':
      return { channel, adapter_id: 'api_future', mode: 'real_future', canSendReal: false };
    default:
      return { channel: 'human_broker_manual', adapter_id: 'human_manual_sandbox', mode: 'sandbox', canSendReal: false };
  }
}

function execId(): string {
  return `exec-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** 42X3.1 — adapter sandbox por provider (alinha execução ao provider do plano). */
function providerSandboxAdapterId(providerKey: string | null, channel: ActionChannel | null): string {
  switch (providerKey) {
    case 'zapi': return 'zapi_sandbox';
    case 'evolution_go': return 'evolution_go_sandbox';
    case 'meta_cloud': return 'meta_cloud_sandbox';
    case 'manual': return 'human_manual_sandbox';
    default: return getChannelAdapter(channel).adapter_id;
  }
}

/** Inicia uma sessão de execução sandbox a partir de um ExternalActionPlan pronto. */
export function startExecutionSession(plan: ExternalActionPlan): ExternalActionExecutionSession | { error: string } {
  if (plan.status !== 'ready_for_human_approval') {
    return { error: `plan_not_ready:${plan.status}` };
  }
  const adapterId = providerSandboxAdapterId(plan.selected_provider_key ?? null, plan.selected_channel);
  const now = new Date().toISOString();
  const prepared = plan.message_drafts[0]?.text ?? null;
  return {
    execution_id: execId(),
    case_id: plan.case_id,
    dispatch_packet_id: plan.dispatch_packet_id,
    status: 'waiting_insurer',
    mode: 'sandbox',
    channel: plan.selected_channel,
    adapter: adapterId,
    current_step: 'sent_initial_message_sandbox',
    last_event_at: now,
    events: [
      { at: now, type: 'session_started', note: 'sandbox' },
      { at: now, type: 'message_prepared', note: adapterId },
      { at: now, type: 'simulated_send', note: 'dry-run — nada foi enviado (canSendReal=false)' },
    ],
    insurer_thread_ref: null,
    next_required_input: 'simulated_insurer_reply',
    customer_update: 'Preparei o acionamento em modo simulado e estou aguardando o retorno da seguradora.',
    human_review_required: false,
    suggested_channel: null,
    prepared_message: prepared,
    external_action_sent: false,
  };
}

const SENSITIVE_REQUESTS = new Set(['cpf']);

/** Recuperação inteligente: dado interpretação da resposta, decide o próximo estado. PURO. */
export function recoverExternalExecutionStep(
  interp: InsurerReplyInterpretation,
  ctx: { hasPolicyNumber?: boolean } = {},
): { next_status: ExecutionStatus; next_required_input: string | null; human_review_required: boolean; suggested_channel: ActionChannel | null; customer_update: string | null } {
  const cm = interp.customer_message;
  switch (interp.classification) {
    case 'accepted':
      return { next_status: 'completed_sandbox', next_required_input: null, human_review_required: false, suggested_channel: null, customer_update: cm };
    case 'asks_for_missing_data': {
      const req = interp.missing_data_request || '';
      if (SENSITIVE_REQUESTS.has(req)) {
        return { next_status: 'waiting_human', next_required_input: 'human_provides_sensitive_data', human_review_required: true, suggested_channel: null, customer_update: cm };
      }
      if (req === 'policy_number') {
        if (ctx.hasPolicyNumber) {
          // Dado disponível e não-sensível: prepara follow-up sandbox e volta a aguardar a seguradora.
          return { next_status: 'waiting_insurer', next_required_input: 'simulated_insurer_reply', human_review_required: false, suggested_channel: null, customer_update: 'A seguradora pediu o número da apólice; já tenho essa informação e segui o atendimento.' };
        }
        // Não temos a apólice localizada → humano providencia (não é dado que o segurado digita).
        return { next_status: 'waiting_human', next_required_input: 'human_provides_policy', human_review_required: true, suggested_channel: null, customer_update: cm };
      }
      // endereço/telefone → pedir ao segurado.
      return { next_status: 'waiting_insured', next_required_input: req || 'insured_answer', human_review_required: false, suggested_channel: null, customer_update: cm };
    }
    case 'requests_document':
      return { next_status: 'waiting_insured', next_required_input: 'documento', human_review_required: false, suggested_channel: null, customer_update: cm };
    case 'redirects_channel':
      return { next_status: 'waiting_human', next_required_input: 'human_setup_channel', human_review_required: true, suggested_channel: interp.suggested_channel, customer_update: cm };
    case 'coverage_question':
      return { next_status: 'waiting_human', next_required_input: 'human_validates_coverage', human_review_required: true, suggested_channel: null, customer_update: cm };
    case 'unavailable':
      return { next_status: 'waiting_human', next_required_input: 'human_manual_handoff', human_review_required: true, suggested_channel: 'human_broker_manual', customer_update: cm };
    default:
      return { next_status: 'waiting_human', next_required_input: 'human_review', human_review_required: true, suggested_channel: null, customer_update: cm };
  }
}

const _EXEC_LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
function maskExec(s: string): string {
  return (s || '').replace(_EXEC_LONG_DIGITS, '[omitido]').slice(0, 240);
}

export interface ExecutionEventInput {
  event_type: 'simulated_insurer_reply' | 'simulated_send_ack' | 'cancel' | 'human_note' | 'insured_answer';
  text?: string;
}

/** Aplica um evento à sessão (PURO). NUNCA envia real. */
export function applyExecutionEvent(
  session: ExternalActionExecutionSession,
  event: ExecutionEventInput,
  ctx: { hasPolicyNumber?: boolean } = {},
): ExternalActionExecutionSession {
  const now = new Date().toISOString();
  const s: ExternalActionExecutionSession = { ...session, events: [...session.events], last_event_at: now, external_action_sent: false };
  if (s.status === 'completed_sandbox' || s.status === 'cancelled' || s.status === 'failed_sandbox') {
    s.events.push({ at: now, type: 'event_ignored_terminal', note: event.event_type });
    return s;
  }

  if (event.event_type === 'cancel') {
    s.status = 'cancelled';
    s.current_step = 'cancelled';
    s.next_required_input = null;
    s.customer_update = 'O acionamento simulado foi cancelado.';
    s.events.push({ at: now, type: 'cancelled' });
    return s;
  }
  if (event.event_type === 'human_note') {
    s.events.push({ at: now, type: 'human_note', excerpt: maskExec(event.text || '') });
    return s;
  }
  if (event.event_type === 'simulated_send_ack') {
    s.events.push({ at: now, type: 'simulated_send_ack', note: 'dry-run' });
    return s;
  }
  if (event.event_type === 'insured_answer') {
    // Segurado respondeu → prepara follow-up sandbox e volta a aguardar a seguradora.
    s.status = 'waiting_insurer';
    s.current_step = 'insured_answer_received';
    s.next_required_input = 'simulated_insurer_reply';
    s.customer_update = 'Obrigado! Já segui com a informação no atendimento.';
    s.events.push({ at: now, type: 'insured_answer', excerpt: maskExec(event.text || '') });
    return s;
  }

  // simulated_insurer_reply
  const interp = interpretInsurerReply(event.text || '', { hasPolicyNumber: ctx.hasPolicyNumber });
  const rec = recoverExternalExecutionStep(interp, ctx);
  s.status = rec.next_status;
  s.current_step = `insurer_${interp.classification}`;
  s.next_required_input = rec.next_required_input;
  s.human_review_required = rec.human_review_required;
  s.suggested_channel = rec.suggested_channel;
  s.customer_update = rec.customer_update;
  s.events.push({ at: now, type: 'insurer_reply', classification: interp.classification, next_step: interp.next_step, excerpt: maskExec(event.text || '') });
  return s;
}

/** Resumo seguro da sessão (sem PII). */
export function safeExecutionSessionSummary(s: ExternalActionExecutionSession): Record<string, unknown> {
  return {
    execution_id: s.execution_id,
    status: s.status,
    channel: s.channel,
    adapter: s.adapter,
    current_step: s.current_step,
    human_review_required: s.human_review_required,
    suggested_channel: s.suggested_channel,
    next_required_input: s.next_required_input,
    event_count: s.events.length,
    external_action_sent: false,
    mode: s.mode,
    last_event_at: s.last_event_at,
  };
}

// =============================================================================
// 42X2 — External Action Outbox, Permission Gates & Real Adapter Skeleton
// PURO. NENHUM envio real. send_allowed é SEMPRE false neste estágio porque
// nenhum adapter tem canSendReal=true e as flags vêm desligadas por padrão.
// =============================================================================

export type OutboxStatus =
  | 'draft'
  | 'awaiting_approval'
  | 'approved_not_sent'
  | 'blocked'
  | 'cancelled'
  | 'sent_future';

export interface ExternalActionOutboxEntry {
  outbox_id: string;
  case_id: string | null;
  dispatch_packet_id: string | null;
  execution_id: string | null;
  channel: ActionChannel | null;
  provider: string | null;
  destination_ref_masked: string | null; // NUNCA o destino cru
  message_text: string | null; // mascarado
  payload_sanitized: Record<string, unknown>;
  status: OutboxStatus;
  approval_required: boolean;
  approved_by: string | null;
  approved_at: string | null;
  send_allowed: false; // SEMPRE false no 42X2
  sent: false; // SEMPRE false no 42X2
  blockers: string[];
  created_at: string;
  updated_at: string;
}

function maskDestination(ref: string | null | undefined): string | null {
  if (!ref) return null;
  const s = String(ref);
  if (s.length <= 4) return '****';
  return `****${s.slice(-4)}`;
}

export interface BuildOutboxInput {
  case_id: string | null;
  dispatch_packet_id: string | null;
  execution?: ExternalActionExecutionSession | null;
  plan?: ExternalActionPlan | null;
  destination_ref?: string | null;
  provider?: string | null;
  // 42X3 — vindos da config de canal resolvida (provider-agnostic):
  channel?: ActionChannel | null;
  destination_ref_masked?: string | null;
  provider_payload?: Record<string, unknown> | null;
  config_id?: string | null;
  // 42X4 — resumo do harness de homologação do provider (sanitizado):
  provider_validation?: Record<string, unknown> | null;
}

/**
 * Cria uma entrada de outbox a partir do plano/sessão. Exige que a execução
 * esteja "pronta" (plano ready_for_human_approval). Caso contrário → blocked.
 */
export function buildOutboxEntry(input: BuildOutboxInput): ExternalActionOutboxEntry {
  const now = new Date().toISOString();
  const channel = input.channel ?? input.execution?.channel ?? input.plan?.selected_channel ?? null;
  const adapter = getChannelAdapter(channel);
  const planReady = input.plan?.status === 'ready_for_human_approval';
  const execOk =
    !input.execution ||
    ['waiting_insurer', 'waiting_insured', 'waiting_human', 'running_sandbox', 'approved_for_sandbox', 'completed_sandbox'].includes(
      input.execution.status,
    );
  const blockers: string[] = [];
  if (!planReady) blockers.push('plan_not_ready');
  if (!execOk) blockers.push('execution_not_ready');
  // Mesmo "pronto", nunca pode enviar: registra o motivo real.
  blockers.push('real_send_disabled_42x2');

  const status: OutboxStatus = planReady && execOk ? 'awaiting_approval' : 'blocked';
  const messageText = input.execution?.prepared_message ?? input.plan?.message_drafts?.[0]?.text ?? null;

  return {
    outbox_id: `obx-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    case_id: input.case_id,
    dispatch_packet_id: input.dispatch_packet_id,
    execution_id: input.execution?.execution_id ?? null,
    channel,
    provider: input.provider ?? (channel === 'insurer_whatsapp' ? 'zapi' : null),
    destination_ref_masked: input.destination_ref_masked ?? maskDestination(input.destination_ref),
    message_text: messageText ? maskExec(messageText) : null,
    payload_sanitized: {
      channel,
      adapter_id: adapter.adapter_id,
      can_send_real: adapter.canSendReal, // false
      playbook_id: input.plan?.playbook_id ?? null,
      config_id: input.config_id ?? null,
      provider_payload: input.provider_payload ?? null,
      provider_validation: input.provider_validation ?? null,
    },
    status,
    approval_required: true,
    approved_by: null,
    approved_at: null,
    send_allowed: false,
    sent: false,
    blockers,
    created_at: now,
    updated_at: now,
  };
}

/** Aprova (HITL) a entrada → approved_not_sent. NUNCA habilita envio real. */
export function approveOutboxEntry(entry: ExternalActionOutboxEntry, approver: string): ExternalActionOutboxEntry {
  const now = new Date().toISOString();
  if (entry.status === 'cancelled' || entry.status === 'sent_future') return entry;
  if (entry.status === 'blocked') {
    // Aprovação não desbloqueia um item bloqueado por gate de segurança.
    return { ...entry, updated_at: now };
  }
  return {
    ...entry,
    status: 'approved_not_sent',
    approved_by: approver,
    approved_at: now,
    send_allowed: false, // continua false: aprovação ≠ envio
    sent: false,
    updated_at: now,
  };
}

/** Cancela a entrada. */
export function cancelOutboxEntry(entry: ExternalActionOutboxEntry): ExternalActionOutboxEntry {
  const now = new Date().toISOString();
  return { ...entry, status: 'cancelled', send_allowed: false, sent: false, updated_at: now };
}

// --- Permission gates -------------------------------------------------------

export interface ExternalSendPermissionContext {
  realEnabled: boolean; // EXTERNAL_ACTION_REAL_ENABLED
  insurerWhatsappRealSend: boolean; // INSURER_WHATSAPP_REAL_SEND_ENABLED
  killSwitchActive: boolean; // EXTERNAL_ACTION_KILL_SWITCH (true = bloqueia)
  adapterCanSendReal: boolean; // adapter.canSendReal
  tenantConnectionStatus: string | null; // 'connected' libera
  credentialRefPresent: boolean; // encrypted_secret_ref presente
  actionPlanStatus: ActionPlanStatus | string | null;
  executionStatus: ExecutionStatus | string | null;
  coverageState: string | null; // 'human_approved'
  packetState: string | null; // 'ready_for_human_approval'
  approvalStatus: string | null; // 'approved'
  rateLimit: { used: number; limit: number };
  channelHomologated: boolean;
  piiViolation: boolean;
}

export interface ExternalSendPermissionResult {
  send_allowed: false; // SEMPRE false no 42X2
  gates: Record<string, boolean>;
  blockers: string[];
  reason: string;
}

/**
 * Avalia TODOS os gates de envio externo. No 42X2 o resultado é sempre
 * send_allowed=false (adapter.canSendReal=false e/ou flags off), mas a função
 * já modela cada gate para o futuro (42X3+).
 */
export function evaluateExternalSendPermission(ctx: ExternalSendPermissionContext): ExternalSendPermissionResult {
  const gates: Record<string, boolean> = {
    real_flag_enabled: ctx.realEnabled === true,
    insurer_whatsapp_real_send_enabled: ctx.insurerWhatsappRealSend === true,
    kill_switch_off: ctx.killSwitchActive !== true,
    adapter_can_send_real: ctx.adapterCanSendReal === true,
    tenant_connection_active: ctx.tenantConnectionStatus === 'connected',
    credential_present: ctx.credentialRefPresent === true,
    action_plan_ready: ctx.actionPlanStatus === 'ready_for_human_approval',
    execution_ready: ['waiting_insurer', 'waiting_insured', 'waiting_human', 'running_sandbox', 'approved_for_sandbox'].includes(
      String(ctx.executionStatus),
    ),
    coverage_human_approved: ctx.coverageState === 'human_approved',
    dispatch_ready: ctx.packetState === 'ready_for_human_approval',
    approval_exists: ctx.approvalStatus === 'approved',
    rate_limit_ok: ctx.rateLimit.used < ctx.rateLimit.limit,
    channel_homologated: ctx.channelHomologated === true,
    no_pii_violation: ctx.piiViolation !== true,
  };
  const blockers = Object.entries(gates)
    .filter(([, ok]) => !ok)
    .map(([k]) => k);
  // SEGURANÇA: no 42X2 nunca liberamos envio real, mesmo que algum dia todos os
  // gates passem — o tipo força send_allowed=false e a constante trava aqui.
  const send_allowed = false as const;
  const reason = blockers.length > 0 ? `blocked_by:${blockers.join(',')}` : 'real_send_disabled_42x2';
  return { send_allowed, gates, blockers, reason };
}

// --- Insurer WhatsApp Real Adapter Skeleton ---------------------------------

export interface RealSendInput {
  destination_ref: string | null;
  provider: string | null;
  message_text: string | null;
  tenant_connection: { status?: string; encrypted_secret_ref?: string | null } | null;
}

export interface RealSendResult {
  sent: false; // SEMPRE false
  status: 'blocked_real_send_disabled' | 'invalid_destination' | 'invalid_provider' | 'no_tenant_connection';
  reason: string;
  prepared_payload?: Record<string, unknown> | null;
}

export interface RealAdapterSkeleton {
  channel: ActionChannel;
  adapter_id: string;
  provider: string;
  canSendReal: false;
  validateDestination: (ref: string | null) => boolean;
  validateProvider: (provider: string | null) => boolean;
  buildPayload: (input: RealSendInput) => Record<string, unknown>;
  send: (input: RealSendInput) => RealSendResult;
}

/**
 * Skeleton do adapter real de WhatsApp da seguradora. Monta payload e valida
 * pré-condições, mas canSendReal=false: send() SEMPRE retorna bloqueado e
 * NUNCA chama provider (Z-API/Meta) real.
 */
export function getInsurerWhatsAppRealAdapterSkeleton(): RealAdapterSkeleton {
  const validateDestination = (ref: string | null) => typeof ref === 'string' && /^\d{8,15}$/.test(ref.replace(/\D/g, ''));
  const validateProvider = (provider: string | null) => provider === 'zapi' || provider === 'meta_cloud' || provider === 'evolution';
  return {
    channel: 'insurer_whatsapp',
    adapter_id: 'insurer_whatsapp_real_skeleton',
    provider: 'zapi',
    canSendReal: false,
    validateDestination,
    validateProvider,
    buildPayload: (input) => ({
      provider: input.provider,
      to_masked: maskDestination(input.destination_ref),
      body: input.message_text ? maskExec(input.message_text) : null,
      dry_run: true,
    }),
    send: (input) => {
      // Ordem de validação só para diagnóstico — nada é enviado em nenhuma hipótese.
      if (!input.tenant_connection || input.tenant_connection.status !== 'connected') {
        return { sent: false, status: 'no_tenant_connection', reason: 'tenant_connection ausente/inativa' };
      }
      if (!validateProvider(input.provider)) {
        return { sent: false, status: 'invalid_provider', reason: 'provider não homologado' };
      }
      if (!validateDestination(input.destination_ref)) {
        return { sent: false, status: 'invalid_destination', reason: 'destino inválido' };
      }
      return {
        sent: false,
        status: 'blocked_real_send_disabled',
        reason: 'canSendReal=false — envio real desabilitado no 42X2',
        prepared_payload: {
          provider: input.provider,
          to_masked: maskDestination(input.destination_ref),
          body: input.message_text ? maskExec(input.message_text) : null,
        },
      };
    },
  };
}

// --- Audit trail (sanitizado) ----------------------------------------------

export type OutboxAuditType =
  | 'outbox_prepared'
  | 'approval_requested'
  | 'approved_not_sent'
  | 'send_blocked_by_gate'
  | 'cancelled'
  | 'permission_evaluated'
  | 'adapter_not_real_enabled';

export interface OutboxAuditEvent {
  at: string;
  type: OutboxAuditType;
  outbox_id: string | null;
  note?: string | null;
  blockers?: string[];
}

export function buildAuditEvent(type: OutboxAuditType, outbox_id: string | null, extra: { note?: string; blockers?: string[] } = {}): OutboxAuditEvent {
  return {
    at: new Date().toISOString(),
    type,
    outbox_id,
    note: extra.note ? maskExec(extra.note) : null,
    blockers: extra.blockers,
  };
}

/** Resumo seguro do outbox (sem PII/destino cru). */
export function safeOutboxSummary(entries: ExternalActionOutboxEntry[]): Record<string, unknown> {
  const last = entries[entries.length - 1] ?? null;
  return {
    count: entries.length,
    last_status: last?.status ?? null,
    last_channel: last?.channel ?? null,
    last_outbox_id: last?.outbox_id ?? null,
    any_send_allowed: false,
    any_sent: false,
    updated_at: last?.updated_at ?? null,
  };
}

/** Resumo seguro do plano para diagnostics/persistência (sem PII/draft sensível). */
export function safeActionPlanSummary(plan: ExternalActionPlan): Record<string, unknown> {
  return {
    status: plan.status,
    selected_channel: plan.selected_channel,
    allowed_to_prepare: plan.allowed_to_prepare,
    human_review_required: plan.human_review_required,
    missing_data: plan.missing_data,
    risk_flags: plan.risk_flags,
    playbook_id: plan.playbook_id,
    coverage_state: plan.coverage_gate.state,
    packet_state: plan.readiness.packet_state,
    external_action_sent: false,
    dry_run: true,
    selected_config_id: plan.selected_config_id ?? null,
    selected_provider_key: plan.selected_provider_key ?? null,
    selected_destination_ref_masked: plan.selected_destination_ref_masked ?? null,
    selected_homologation_status: plan.selected_homologation_status ?? null,
    channel_config_source: plan.channel_config_source ?? 'none',
  };
}
