// Resolver GLOBAL de intenção/corredor (42W1.1) — PURO, sem I/O, sem LLM.
//
// Tira o hardcoding de Allianz/Residencial/Eletricista do canal WhatsApp. O canal
// é GLOBAL: classifica a intenção do texto e mapeia para um corredor disponível
// (corridor_templates ativos). Se não houver corredor para a intenção, devolve
// triagem (sem inventar execução). O runtime/corredor decide o atendimento; o
// canal só roteia.

export type AttendanceIntentBucket =
  | 'residential_assistance'
  | 'auto_assistance'
  | 'claim'
  | 'policy_question'
  | 'policy_consultation'
  | 'followup_existing_case'
  | 'billing_document'
  | 'unknown';

export interface AvailableCorridor {
  corridor_key: string;
  subcorridor_key: string | null;
  insurer_key?: string | null;
  line_kind?: string | null;
  macro_service?: string | null;
  service_type?: string | null;
  display_name?: string | null;
  scope?: string | null; // 'global' | 'tenant'
}

export interface ResolvedIntent {
  confidence: 'high' | 'medium' | 'low';
  intent: AttendanceIntentBucket;
  insurer_key: string | null;
  line_kind: string | null;
  macro_service: string | null;
  selected_corridor_key: string | null;
  selected_subcorridor_key: string | null;
  reason: string;
  needs_clarification: boolean;
  clarification_question: string | null;
  candidate_corridors: Array<{ corridor_key: string; subcorridor_key: string | null }>;
}

function norm(s?: string | null): string {
  return (s || '').toString().toLowerCase();
}

// --- classificação de intenção (palavra-chave, prioridade explícita) ---
const RE = {
  followup: /\b(previs[aã]o|protocolo|prestador|andamento|status|j[áa]\s+chamaram|qual.*atendimento|meu atendimento|acompanhar|atualiza[çc][aã]o)\b/i,
  claim: /\b(bati|batida|colis[aã]o|acidente|roubo|furto|sinistro|colidi|capot|incend(io|iei)|alagou|enchente|raio|granizo)\b/i,
  auto: /\b(carro|ve[íi]culo|autom[óo]vel|moto|pneu|furou|furado|bateria|guincho|pane seca|chave tranca|n[aã]o liga|n[aã]o d[áa] partida)\b/i,
  residential: /\b(luz|energia|el[ée]tric|eletric|disjuntor|tomada|l[âa]mpada|sem luz|curto|fia[çc][aã]o|encanad|vazamento|cano|torneira|chuveiro|fechadura|porta|telhado|goteira|infiltra)\b/i,
  policy_question: /\b(cobertura|cobre|coberto|tenho direito|tenho cobertura|est[áa] coberto|inclui)\b/i,
  policy_consultation: /\b(consultar\s+(minha\s+)?ap[óo]lice|minha ap[óo]lice|dados da ap[óo]lice|segunda via|n[úu]mero da ap[óo]lice|vig[êe]ncia)\b/i,
  billing: /\b(boleto|fatura|pagamento|segunda via.*boleto|cobran[çc]a|declara[çc][aã]o|comprovante|documento)\b/i,
};

/** Classifica a intenção do texto (bucket). Prioridade: followup > claim > policy > billing > auto > residential. */
export function classifyAttendanceIntent(text: string): { bucket: AttendanceIntentBucket; reason: string } {
  const t = norm(text);
  if (!t.trim()) return { bucket: 'unknown', reason: 'empty' };
  if (RE.followup.test(t)) return { bucket: 'followup_existing_case', reason: 'followup_keyword' };
  if (RE.claim.test(t)) return { bucket: 'claim', reason: 'claim_keyword' };
  if (RE.policy_consultation.test(t)) return { bucket: 'policy_consultation', reason: 'policy_consultation_keyword' };
  if (RE.policy_question.test(t)) return { bucket: 'policy_question', reason: 'policy_question_keyword' };
  if (RE.billing.test(t)) return { bucket: 'billing_document', reason: 'billing_keyword' };
  if (RE.auto.test(t)) return { bucket: 'auto_assistance', reason: 'auto_keyword' };
  if (RE.residential.test(t)) return { bucket: 'residential_assistance', reason: 'residential_keyword' };
  return { bucket: 'unknown', reason: 'no_keyword' };
}

const CLARIFICATION: Record<AttendanceIntentBucket, string> = {
  residential_assistance: 'Entendi que é uma assistência na sua residência. Pode me dizer rapidamente o que está acontecendo?',
  auto_assistance: 'Entendi que é sobre seu veículo. É uma assistência (pneu, bateria, guincho) ou um sinistro (batida, roubo)?',
  claim: 'Entendi que pode ser um sinistro. Pode me contar rapidamente o que aconteceu?',
  policy_question: 'Posso te ajudar com a dúvida sobre cobertura. Sobre qual apólice ou tipo de cobertura você quer saber?',
  policy_consultation: 'Posso ajudar com sua apólice. O que você gostaria de consultar?',
  followup_existing_case: 'Vou verificar o seu atendimento. Pode confirmar de qual atendimento você está falando?',
  billing_document: 'Posso ajudar com boleto/documento. Pode me dizer exatamente o que você precisa?',
  unknown: 'Pode me explicar rapidamente o que você precisa? É uma assistência (ex.: eletricista, encanador), um sinistro, ou uma dúvida sobre a apólice?',
};

/** Encontra um corredor disponível para o bucket (prioriza tenant sobre global). */
function matchCorridor(bucket: AttendanceIntentBucket, corridors: AvailableCorridor[]): AvailableCorridor | null {
  const byPref = [...corridors].sort((a, b) => (a.scope === 'tenant' ? -1 : 0) - (b.scope === 'tenant' ? -1 : 0));
  const macro = (c: AvailableCorridor) => norm(c.macro_service);
  const line = (c: AvailableCorridor) => norm(c.line_kind);
  const test = (pred: (c: AvailableCorridor) => boolean) => byPref.find(pred) || null;

  switch (bucket) {
    case 'residential_assistance':
      return test((c) => line(c) === 'residential' && /assist/.test(macro(c)))
        || test((c) => line(c) === 'residential');
    case 'auto_assistance':
      return test((c) => line(c) === 'auto' && /assist/.test(macro(c)))
        || test((c) => line(c) === 'auto' && !/claim|sinistro/.test(macro(c)));
    case 'claim':
      return test((c) => /claim|sinistro/.test(macro(c)));
    case 'policy_question':
    case 'policy_consultation':
      return test((c) => /policy|ap[óo]lice|consult/.test(macro(c)));
    case 'billing_document':
      return test((c) => /billing|document|cobran/.test(macro(c)));
    default:
      return null;
  }
}

export interface ResolveInput {
  text: string;
  availableCorridors?: AvailableCorridor[];
  defaultCorridorKey?: string | null;
  defaultSubcorridorKey?: string | null;
}

/**
 * Resolve intenção + corredor. PURO. Sem corredor disponível → triagem.
 * Default por env só é usado se configurado E o corredor existir entre os disponíveis.
 */
export function resolveAttendanceIntentAndCorridor(input: ResolveInput): ResolvedIntent {
  const corridors = Array.isArray(input.availableCorridors) ? input.availableCorridors : [];
  const { bucket, reason } = classifyAttendanceIntent(input.text);
  const candidates = corridors.map((c) => ({ corridor_key: c.corridor_key, subcorridor_key: c.subcorridor_key ?? null }));

  // followup não cria corredor — o bridge tenta achar um case existente antes.
  if (bucket === 'followup_existing_case') {
    return {
      confidence: 'medium', intent: bucket, insurer_key: null, line_kind: null, macro_service: 'followup',
      selected_corridor_key: null, selected_subcorridor_key: null, reason,
      needs_clarification: false, clarification_question: null, candidate_corridors: candidates,
    };
  }

  let matched = matchCorridor(bucket, corridors);

  // Fallback por env: só se configurado E presente entre os disponíveis.
  if (!matched && input.defaultCorridorKey) {
    matched =
      corridors.find(
        (c) => c.corridor_key === input.defaultCorridorKey && (c.subcorridor_key ?? null) === (input.defaultSubcorridorKey ?? c.subcorridor_key ?? null),
      ) || corridors.find((c) => c.corridor_key === input.defaultCorridorKey) || null;
  }

  if (matched) {
    const clear = bucket !== 'unknown';
    return {
      confidence: clear ? 'high' : 'medium',
      intent: bucket === 'unknown' ? 'residential_assistance' : bucket,
      insurer_key: matched.insurer_key ?? null,
      line_kind: matched.line_kind ?? null,
      macro_service: matched.macro_service ?? null,
      selected_corridor_key: matched.corridor_key,
      selected_subcorridor_key: matched.subcorridor_key ?? null,
      reason: matched.scope === 'tenant' ? `${reason}+tenant_corridor` : `${reason}+corridor`,
      needs_clarification: false,
      clarification_question: null,
      candidate_corridors: candidates,
    };
  }

  // Sem corredor → triagem (não inventa execução).
  return {
    confidence: 'low',
    intent: bucket,
    insurer_key: null,
    line_kind: null,
    macro_service: null,
    selected_corridor_key: null,
    selected_subcorridor_key: null,
    reason: `${reason}+no_corridor`,
    needs_clarification: true,
    clarification_question: CLARIFICATION[bucket],
    candidate_corridors: candidates,
  };
}

export interface ResolvedCaseFields {
  status: string;
  intent: string;
  insurer_key: string | null;
  line_kind: string | null;
  macro_service: string | null;
  selected_corridor_key: string | null;
  selected_subcorridor_key: string | null;
  summary: string;
  next_step: string;
}

/** Monta os campos do attendance_case a partir da intenção resolvida. PURO/genérico. */
export function buildAttendanceCaseFieldsFromResolvedIntent(
  resolved: ResolvedIntent,
  ctx: { channel?: string } = {},
): ResolvedCaseFields {
  const channel = ctx.channel || 'whatsapp';
  if (resolved.selected_corridor_key) {
    return {
      status: 'collecting_slots',
      intent: resolved.intent,
      insurer_key: resolved.insurer_key,
      line_kind: resolved.line_kind,
      macro_service: resolved.macro_service,
      selected_corridor_key: resolved.selected_corridor_key,
      selected_subcorridor_key: resolved.selected_subcorridor_key,
      summary: `Atendimento via ${channel} — ${resolved.macro_service || resolved.intent}.`,
      next_step: 'Coletar dados mínimos e validar apólice antes de qualquer acionamento externo.',
    };
  }
  return {
    status: 'triage',
    intent: resolved.intent === 'unknown' ? 'triage' : resolved.intent,
    insurer_key: null,
    line_kind: null,
    macro_service: null,
    selected_corridor_key: null,
    selected_subcorridor_key: null,
    summary: `Triagem de atendimento via ${channel}.`,
    next_step: resolved.clarification_question || CLARIFICATION.unknown,
  };
}
