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
  const area = data.affected_area || 'no imóvel';
  const problem = data.problem || 'um problema na residência';
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

  // Canal recomendado: o de maior prioridade com modo dry_run; senão fallback manual.
  const preferred = channels.find((ch) => ch.current_mode === 'dry_run' && ch.channel !== 'human_broker_manual')
    || channels.find((ch) => ch.channel === 'human_broker_manual')
    || null;
  const selected = preferred ? preferred.channel : null;

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
    channel_candidates: channels,
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
  };
}
