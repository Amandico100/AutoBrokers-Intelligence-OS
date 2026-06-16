// Policy Evidence Pack + Interpretation Context (42I3A).
//
// Helpers PUROS (sem I/O) que:
//  1. constroem um Policy Evidence Pack a partir de um documento de apólice
//     (shape /documento da InfoCap) — espelha a lógica do backend p/ testes;
//  2. normalizam/sanitizam um pack vindo do backend;
//  3. mapeiam o pack para o contrato CoverageEvidence (persistência);
//  4. montam um policy_interpretation_context seguro para o Smith/LLM.
//
// REGRAS DE OURO:
//  - NUNCA afirmar cobertura específica sem itens/coberturas no documento.
//  - Diferenciar "apólice localizada" de "cobertura confirmada".
//  - Sem PII crua: nome/numero mascarados; nenhum CPF/segredo.
//  - Não decide cobertura via LLM; só estrutura evidência factual.

import type { CoverageEvidence } from './policy-lookup';

export interface AssistanceSignals {
  residential: boolean | null;
  electrician: boolean | null;
  emergency_assistance: boolean | null;
}

export interface CoverageSection {
  label: string;
  amount: string | null;
}

export interface PolicyEvidencePack {
  source: 'infocap';
  verified_by: 'connector';
  policy_found: boolean;
  policy_selected: boolean;
  policy_ref: string | null;
  masked_policy_number: string | null;
  insurer_detected: string | null;
  product_detected: string | null;
  line_kind_detected: string | null;
  policy_status: string | null;
  active_now: boolean | null;
  expired: boolean | null;
  valid_from: string | null;
  valid_to: string | null;
  holder_name_masked: string | null;
  risk_address_summary_masked: string | null;
  object_summary: string | null;
  coverage_sections: CoverageSection[];
  coverages_count: number | null;
  cancelled: boolean;
  assistance_signals: AssistanceSignals;
  confidence: 'low' | 'medium' | 'high';
  human_required: boolean;
  limitations: string[];
}

// --- helpers internos (puros) -------------------------------------------------

const SIG_RESIDENTIAL = /residenc|resid[êe]ncia|im[oó]vel|casa|home|habita/i;
const SIG_ELECTRICIAN = /eletric|el[eé]tric|electr|eletricista/i;
const SIG_EMERGENCY = /assist|emerg[êe]nc|24h|24\s*horas|socorro|chaveiro|encanador/i;

const CANCEL_TRUTHY = new Set(['1', 't', 'true', 's', 'sim']);

function s(v: unknown): string | null {
  if (typeof v === 'string' && v.trim()) return v.trim();
  if (typeof v === 'number') return String(v);
  return null;
}

function firstStr(o: Record<string, unknown>, keys: string[]): string | null {
  for (const k of keys) {
    const v = s(o[k]);
    if (v) return v;
  }
  return null;
}

function maskTail(value: string | null, keep = 2): string | null {
  const d = (value || '').replace(/\D/g, '');
  if (d.length < keep) return null;
  return `****${d.slice(-keep)}`;
}

function maskName(name: string | null): string | null {
  const v = (name || '').trim();
  if (!v) return null;
  return (
    v
      .split(/\s+/)
      .map((p) => (p ? `${p[0].toUpperCase()}***` : ''))
      .join(' ')
      .trim() || null
  );
}

function parseDate(value: string | null): Date | null {
  if (!value) return null;
  const raw = value.trim().slice(0, 10);
  let m = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/); // dd/mm/yyyy
  if (m) return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
  m = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/); // yyyy-mm-dd
  if (m) return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  m = raw.match(/^(\d{2})-(\d{2})-(\d{4})$/); // dd-mm-yyyy
  if (m) return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
  return null;
}

function activeExpired(
  validFrom: string | null,
  validTo: string | null,
  cancelled: boolean,
  now = new Date(),
): { active_now: boolean | null; expired: boolean | null } {
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const from = parseDate(validFrom);
  const to = parseDate(validTo);
  let expired: boolean | null = null;
  if (to) expired = today > to.getTime();
  let active: boolean | null = null;
  if (cancelled) active = false;
  else if (to) {
    const started = !from || today >= from.getTime();
    active = started && today <= to.getTime();
  }
  return { active_now: active, expired };
}

function collectTexts(doc: Record<string, unknown>): string[] {
  const parts: string[] = [];
  for (const k of ['ramo', 'ramo_abrev', 'produto', 'descricao', 'tipo_seguro']) {
    const v = s(doc[k]);
    if (v) parts.push(v);
  }
  for (const lk of ['itens', 'coberturas']) {
    const items = doc[lk];
    if (Array.isArray(items)) {
      for (const it of items.slice(0, 40)) {
        if (it && typeof it === 'object') {
          for (const dk of ['descricao', 'cobertura', 'nome', 'item', 'ramo', 'tipo']) {
            const v = s((it as Record<string, unknown>)[dk]);
            if (v) parts.push(v);
          }
        }
      }
    }
  }
  return parts;
}

function collectSections(doc: Record<string, unknown>): CoverageSection[] {
  const out: CoverageSection[] = [];
  for (const lk of ['itens', 'coberturas']) {
    const items = doc[lk];
    if (Array.isArray(items)) {
      for (const it of items.slice(0, 40)) {
        if (!it || typeof it !== 'object') continue;
        const o = it as Record<string, unknown>;
        const label = firstStr(o, ['descricao', 'cobertura', 'nome', 'item', 'ramo', 'tipo']);
        const amount = firstStr(o, ['valor', 'is', 'importancia_segurada', 'limite', 'capital']);
        if (label) out.push({ label, amount });
      }
    }
  }
  return out.slice(0, 40);
}

function signal(joined: string, hasText: boolean, re: RegExp): boolean | null {
  if (!hasText) return null;
  return re.test(joined);
}

/**
 * Builder PURO do Policy Evidence Pack a partir de um documento bruto
 * (shape /documento). Espelha o backend; usado por fixtures/testes.
 */
export function buildPolicyEvidencePackFromDocument(
  rawDoc: Record<string, unknown>,
  now = new Date(),
): PolicyEvidencePack {
  const doc = rawDoc && typeof rawDoc === 'object' ? rawDoc : {};
  const cancelled = CANCEL_TRUTHY.has(String(doc.cancelado).toLowerCase()) || doc.cancelado === true || doc.cancelado === 1;
  const status = cancelled
    ? 'cancelado'
    : firstStr(doc, ['sit_acompanhamento_txt', 'sit_renovacao_txt', 'tipdoc_txt', 'situacao', 'status']) || 'ativo';
  const validFrom = firstStr(doc, ['inivig', 'datini', 'inicio_vigencia']);
  const validTo = firstStr(doc, ['fimvig', 'datfim', 'fim_vigencia']);
  const ae = activeExpired(validFrom, validTo, cancelled, now);

  const texts = collectTexts(doc);
  const joined = texts.join(' ');
  const hasText = texts.length > 0;
  const sections = collectSections(doc);
  const coveragesCount = Array.isArray(doc.itens)
    ? (doc.itens as unknown[]).length
    : Array.isArray(doc.coberturas)
      ? (doc.coberturas as unknown[]).length
      : 0;

  const signals: AssistanceSignals = {
    residential: signal(joined, hasText, SIG_RESIDENTIAL),
    electrician: signal(joined, hasText, SIG_ELECTRICIAN),
    emergency_assistance: signal(joined, hasText, SIG_EMERGENCY),
  };
  const anySignal = Object.values(signals).some((v) => v === true);
  const hasCoverage = sections.length > 0 || coveragesCount > 0;

  let confidence: 'low' | 'medium' | 'high';
  if (cancelled || ae.active_now === false) confidence = 'low';
  else if (anySignal && hasCoverage) confidence = 'high';
  else if (hasCoverage) confidence = 'medium';
  else confidence = 'low';

  const limitations: string[] = [];
  if (!hasCoverage) {
    limitations.push(
      'Documento não trouxe itens/coberturas detalhados; existência da apólice confirmada, cobertura específica não.',
    );
  }
  if (cancelled) limitations.push('Apólice consta como cancelada.');
  if (ae.active_now === false && !cancelled) limitations.push('Apólice fora do período de vigência atual.');

  return {
    source: 'infocap',
    verified_by: 'connector',
    policy_found: true,
    policy_selected: true,
    policy_ref: firstStr(doc, ['nosnum', 'codigo', 'codcli']) || 'infocap-doc',
    masked_policy_number: maskTail(firstStr(doc, ['numapo', 'apolice', 'nosnum', 'numero', 'num_apolice'])),
    insurer_detected: firstStr(doc, ['seguradora_abrev', 'seguradora', 'cia', 'codcia']),
    product_detected: firstStr(doc, ['ramo_abrev', 'ramo', 'codram', 'produto', 'descricao']),
    line_kind_detected: null,
    policy_status: status,
    active_now: ae.active_now,
    expired: ae.expired,
    valid_from: validFrom,
    valid_to: validTo,
    holder_name_masked: maskName(firstStr(doc, ['cliente', 'nome', 'name', 'razao_social'])),
    risk_address_summary_masked: firstStr(doc, ['cidade', 'municipio', 'estado', 'uf']),
    object_summary: firstStr(doc, ['objeto', 'bem', 'descricao_objeto', 'local_risco']),
    coverage_sections: sections,
    coverages_count: coveragesCount,
    cancelled,
    assistance_signals: signals,
    confidence,
    human_required: cancelled || confidence === 'low',
    limitations,
  };
}

/** Normaliza/sanitiza um pack vindo do backend, garantindo formato seguro. */
export function normalizeEvidencePack(input: unknown): PolicyEvidencePack | null {
  if (!input || typeof input !== 'object') return null;
  const o = input as Record<string, unknown>;
  const conf = o.confidence;
  const confidence: 'low' | 'medium' | 'high' =
    conf === 'high' || conf === 'medium' || conf === 'low' ? conf : 'low';
  const sigIn = (o.assistance_signals && typeof o.assistance_signals === 'object'
    ? o.assistance_signals
    : {}) as Record<string, unknown>;
  const triBool = (v: unknown): boolean | null => (v === true ? true : v === false ? false : null);
  const sections = Array.isArray(o.coverage_sections)
    ? (o.coverage_sections as unknown[])
        .filter((x) => x && typeof x === 'object')
        .map((x) => {
          const xs = x as Record<string, unknown>;
          return { label: s(xs.label) || '', amount: s(xs.amount) };
        })
        .filter((x) => x.label)
        .slice(0, 40)
    : [];
  return {
    source: 'infocap',
    verified_by: 'connector',
    policy_found: o.policy_found === true,
    policy_selected: o.policy_selected === true,
    policy_ref: s(o.policy_ref),
    masked_policy_number: s(o.masked_policy_number),
    insurer_detected: s(o.insurer_detected),
    product_detected: s(o.product_detected),
    line_kind_detected: s(o.line_kind_detected),
    policy_status: s(o.policy_status),
    active_now: triBool(o.active_now),
    expired: triBool(o.expired),
    valid_from: s(o.valid_from),
    valid_to: s(o.valid_to),
    holder_name_masked: s(o.holder_name_masked),
    risk_address_summary_masked: s(o.risk_address_summary_masked),
    object_summary: s(o.object_summary),
    coverage_sections: sections,
    coverages_count: typeof o.coverages_count === 'number' ? o.coverages_count : sections.length || null,
    cancelled: o.cancelled === true,
    assistance_signals: {
      residential: triBool(sigIn.residential),
      electrician: triBool(sigIn.electrician),
      emergency_assistance: triBool(sigIn.emergency_assistance),
    },
    confidence,
    human_required: o.human_required === true,
    limitations: Array.isArray(o.limitations)
      ? (o.limitations as unknown[]).filter((x): x is string => typeof x === 'string').slice(0, 10)
      : [],
  };
}

/** Resumo humano que separa "apólice localizada" de "cobertura confirmada". */
export function coverageSummaryFromPack(pack: PolicyEvidencePack): string {
  const ins = pack.insurer_detected ? ` ${pack.insurer_detected}` : '';
  const prod = pack.product_detected ? ` ${pack.product_detected}` : '';
  const head = `Apólice${ins}${prod} localizada na InfoCap${pack.active_now === true ? ' e vigente' : ''}.`;
  const hasCoverage = pack.coverage_sections.length > 0 || (pack.coverages_count || 0) > 0;
  if (pack.cancelled) {
    return `${head} ATENÇÃO: a apólice consta como cancelada — não confirmar cobertura.`;
  }
  if (!hasCoverage) {
    return `${head} O documento não trouxe coberturas detalhadas; cobertura específica NÃO confirmada (requer validação).`;
  }
  const sigs: string[] = [];
  if (pack.assistance_signals.residential) sigs.push('assistência residencial');
  if (pack.assistance_signals.electrician) sigs.push('eletricista');
  if (pack.assistance_signals.emergency_assistance) sigs.push('assistência/emergência');
  const sigTxt = sigs.length ? ` Sinais de cobertura: ${sigs.join(', ')}.` : '';
  return `${head} Coberturas detalhadas disponíveis no documento.${sigTxt} Cobertura específica sujeita às condições da apólice.`;
}

/** Mapeia o pack para o contrato CoverageEvidence (persistência em attendance_cases). */
export function evidencePackToCoverageEvidence(
  pack: PolicyEvidencePack,
  sourceRef = 'infocap:documento',
  verifiedAt = new Date().toISOString(),
): CoverageEvidence {
  return {
    source: 'connector',
    source_ref: sourceRef,
    verified_at: verifiedAt,
    verified_by: 'connector',
    confidence: pack.confidence,
    coverage_summary: coverageSummaryFromPack(pack),
    limitations: pack.limitations,
    human_required: pack.human_required,
  };
}

export interface PolicyInterpretationContext {
  provider: 'infocap';
  policy_located: boolean;
  coverage_confirmed: boolean;
  policy_summary: {
    insurer: string | null;
    product: string | null;
    policy_status: string | null;
    masked_policy_number: string | null;
    active_now: boolean | null;
    valid_from: string | null;
    valid_to: string | null;
  };
  evidence_found: {
    coverage_sections_count: number;
    assistance_signals: AssistanceSignals;
    confidence: 'low' | 'medium' | 'high';
  };
  gaps: string[];
  insured_question: string | null;
  rules: string[];
}

/**
 * Contexto seguro para o Smith/LLM INTERPRETAR a apólice — sem motor paralelo,
 * sem inventar cobertura. Apenas estrutura fatos + regras de resposta.
 */
export function buildPolicyInterpretationContext(input: {
  pack: PolicyEvidencePack;
  insuredQuestion?: string | null;
}): PolicyInterpretationContext {
  const { pack } = input;
  const hasCoverage = pack.coverage_sections.length > 0 || (pack.coverages_count || 0) > 0;
  const coverageConfirmed = hasCoverage && !pack.cancelled && pack.active_now !== false;

  const gaps: string[] = [...pack.limitations];
  if (pack.active_now == null) gaps.push('Vigência não pôde ser confirmada pelas datas do documento.');
  if (!hasCoverage) gaps.push('Sem itens/coberturas detalhados para confirmar cobertura específica.');

  return {
    provider: 'infocap',
    policy_located: pack.policy_found,
    coverage_confirmed: coverageConfirmed,
    policy_summary: {
      insurer: pack.insurer_detected,
      product: pack.product_detected,
      policy_status: pack.policy_status,
      masked_policy_number: pack.masked_policy_number,
      active_now: pack.active_now,
      valid_from: pack.valid_from,
      valid_to: pack.valid_to,
    },
    evidence_found: {
      coverage_sections_count: pack.coverage_sections.length,
      assistance_signals: pack.assistance_signals,
      confidence: pack.confidence,
    },
    gaps: Array.from(new Set(gaps)).slice(0, 10),
    insured_question: input.insuredQuestion ? String(input.insuredQuestion).slice(0, 500) : null,
    rules: [
      'Responda de forma humana e clara.',
      'Diferencie "apólice localizada" de "cobertura confirmada".',
      'NÃO invente cobertura: só afirme o que está nas evidências/coberturas.',
      'Se a apólice estiver cancelada ou fora de vigência, não confirme acionamento.',
      'Se a evidência for ambígua ou confidence baixa, peça validação humana.',
    ],
  };
}

// ---------------------------------------------------------------------------
// Coverage Readiness Gate (42I3B) — decide se o atendimento pode seguir para
// acionamento/dispatch ou se exige validação humana. PURO, sem I/O, sem LLM.
// ---------------------------------------------------------------------------

export type CoverageReadinessState =
  | 'policy_located_only' // apólice localizada, cobertura específica não confirmada
  | 'coverage_confirmed' // cobertura específica encontrada com confiança suficiente
  | 'human_validation_required' // confiança baixa / sem itens / múltiplas / ambígua
  | 'blocked'; // cancelada/vencida/sem evidência → não seguir p/ acionamento

export interface CoverageReadiness {
  state: CoverageReadinessState;
  coverage_confirmed: boolean;
  human_required: boolean;
  /** Pode liberar preparação de dispatch (ainda HITL no MVP)? Só se coverage_confirmed. */
  dispatch_allowed: boolean;
  reasons: string[];
  message: string;
}

export interface CoverageReadinessInput {
  coverage_confirmed?: boolean | null;
  human_required?: boolean | null;
  confidence?: string | null;
  cancelled?: boolean | null;
  expired?: boolean | null;
  active_now?: boolean | null;
  coverages_count?: number | null;
  multiple_matches?: boolean | null;
  insurer?: string | null;
  product?: string | null;
}

// Rótulos amigáveis (abreviações comuns da InfoCap → nome humano).
const INSURER_LABELS: Record<string, string> = {
  ALLI: 'Allianz',
  PORTO: 'Porto Seguro',
  AZUL: 'Azul Seguros',
  HDI: 'HDI',
  TOKIO: 'Tokio Marine',
  BRAD: 'Bradesco Seguros',
  SUHAI: 'Suhai',
  MAPFRE: 'Mapfre',
};
const PRODUCT_LABELS: Record<string, string> = {
  RESI: 'Residencial',
  AUTO: 'Automóvel',
  VIDA: 'Vida',
  EMPR: 'Empresarial',
  COND: 'Condomínio',
};

function titleCase(v: string): string {
  return v
    .toLowerCase()
    .split(/\s+/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');
}

export function humanizeInsurer(key?: string | null): string | null {
  const k = (key || '').trim();
  if (!k) return null;
  return INSURER_LABELS[k.toUpperCase()] || titleCase(k);
}

export function humanizeProduct(key?: string | null): string | null {
  const k = (key || '').trim();
  if (!k) return null;
  return PRODUCT_LABELS[k.toUpperCase()] || titleCase(k);
}

/** Frase "Allianz Residencial" / "apólice" defensiva. */
function policyLabel(insurer?: string | null, product?: string | null): string {
  const ins = humanizeInsurer(insurer);
  const prod = humanizeProduct(product);
  const parts = [ins, prod].filter(Boolean);
  return parts.length ? `apólice ${parts.join(' ')}` : 'apólice';
}

/** Mensagem humana que diferencia apólice localizada de cobertura confirmada. */
export function buildCoverageReasoningMessage(
  readiness: Pick<CoverageReadiness, 'state' | 'human_required'>,
  ctx: { insurer?: string | null; product?: string | null; active_now?: boolean | null },
): string {
  const label = policyLabel(ctx.insurer, ctx.product);
  const vig = ctx.active_now === true ? ' vigente' : '';
  switch (readiness.state) {
    case 'coverage_confirmed':
      return `Localizei uma ${label}${vig} e encontrei evidência de assistência elétrica/residencial nos detalhes. Vou seguir com os dados do atendimento para preparar o acionamento.`;
    case 'blocked':
      return `Localizei uma ${label}, mas ela não está apta para acionamento automático (cancelada ou fora de vigência). Vou registrar e encaminhar para validação humana antes de qualquer providência.`;
    case 'human_validation_required':
    case 'policy_located_only':
    default:
      return `Localizei uma ${label}${vig} na InfoCap. O documento confirma a existência da apólice, mas não trouxe os itens de cobertura detalhados para eu afirmar automaticamente a assistência elétrica. Vou continuar coletando os dados do atendimento, mas antes de acionar será necessária validação humana da cobertura.`;
  }
}

/** Avalia a prontidão de cobertura (gate de acionamento). PURO. */
export function evaluateCoverageReadiness(input: CoverageReadinessInput): CoverageReadiness {
  const reasons: string[] = [];
  const cancelled = input.cancelled === true;
  const expired = input.expired === true;
  const humanRequiredFlag = input.human_required === true;
  const confidence = (input.confidence || '').toLowerCase();
  const coveragesCount = typeof input.coverages_count === 'number' ? input.coverages_count : 0;
  const multiple = input.multiple_matches === true;
  const coverageConfirmed = input.coverage_confirmed === true;

  let state: CoverageReadinessState;
  if (cancelled || expired) {
    if (cancelled) reasons.push('policy_cancelled');
    if (expired) reasons.push('policy_expired');
    state = 'blocked';
  } else if (coverageConfirmed && !humanRequiredFlag && (confidence === 'high' || confidence === 'medium')) {
    reasons.push('coverage_confirmed');
    state = 'coverage_confirmed';
  } else if (humanRequiredFlag || confidence === 'low' || coveragesCount === 0 || multiple || !coverageConfirmed) {
    if (humanRequiredFlag) reasons.push('human_required_flag');
    if (confidence === 'low') reasons.push('low_confidence');
    if (coveragesCount === 0) reasons.push('no_coverage_items');
    if (multiple) reasons.push('multiple_policies');
    if (!coverageConfirmed) reasons.push('coverage_not_confirmed');
    state = 'human_validation_required';
  } else {
    reasons.push('policy_located');
    state = 'policy_located_only';
  }

  const dispatch_allowed = state === 'coverage_confirmed';
  const human_required = humanRequiredFlag || state === 'human_validation_required' || state === 'blocked';
  const message = buildCoverageReasoningMessage(
    { state, human_required },
    { insurer: input.insurer, product: input.product, active_now: input.active_now },
  );
  return { state, coverage_confirmed: coverageConfirmed, human_required, dispatch_allowed, reasons, message };
}

/** Conveniência: readiness diretamente a partir de um evidence pack. */
export function coverageReadinessFromPack(
  pack: PolicyEvidencePack,
  opts: { multiple_matches?: boolean } = {},
): CoverageReadiness {
  const ctx = buildPolicyInterpretationContext({ pack });
  return evaluateCoverageReadiness({
    coverage_confirmed: ctx.coverage_confirmed,
    human_required: pack.human_required,
    confidence: pack.confidence,
    cancelled: pack.cancelled,
    expired: pack.expired,
    active_now: pack.active_now,
    coverages_count: pack.coverages_count,
    multiple_matches: opts.multiple_matches,
    insurer: pack.insurer_detected,
    product: pack.product_detected,
  });
}

/** Resumo seguro do pack para metadata/diagnostics (sem PII crua). */
export function safeEvidencePackSummary(pack: PolicyEvidencePack): Record<string, unknown> {
  return {
    provider: 'infocap',
    policy_ref: pack.policy_ref,
    masked_policy_number: pack.masked_policy_number,
    insurer_detected: pack.insurer_detected,
    product_detected: pack.product_detected,
    policy_status: pack.policy_status,
    active_now: pack.active_now,
    expired: pack.expired,
    coverages_count: pack.coverages_count,
    cancelled: pack.cancelled,
    assistance_signals: pack.assistance_signals,
    confidence: pack.confidence,
    human_required: pack.human_required,
  };
}
