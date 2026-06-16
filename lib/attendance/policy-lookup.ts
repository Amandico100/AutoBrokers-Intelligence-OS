// Policy Lookup — Manual/Mock Resolver (42I1).
//
// Helpers PUROS (sem I/O) que produzem um `policy_lookup_result` estruturado a
// partir de uma fixture (mock) ou de entrada manual segura, e o mapeiam para os
// campos JÁ existentes de attendance_cases. NÃO chama InfoCap real, NÃO usa
// credenciais, NÃO cria SQL/tabela, NÃO confirma cobertura via LLM. A cobertura
// só é afirmada porque vem de evidência estruturada (coverage_evidence).
//
// Contrato definido em 42I0P. Ver docs/canon/design/2026-06-claude-design/42I0P-...md

export type PolicyLookupStatus =
  | 'policy_selected'
  | 'policy_evidence_ready'
  | 'policy_multiple_matches'
  | 'policy_not_found'
  | 'policy_lookup_pending'
  | 'policy_lookup_blocked';

export type PolicyLookupSource = 'manual' | 'mock' | 'infocap' | 'connector' | 'upload' | 'human' | 'unknown';

export type VerificationStatus =
  | 'unverified'
  | 'pending_human'
  | 'verified_by_document'
  | 'verified_by_connector'
  | 'verified_by_human'
  | 'not_applicable';

export interface CoverageEvidence {
  source: PolicyLookupSource;
  source_ref: string;
  verified_at: string;
  verified_by: 'agent' | 'human' | 'connector';
  confidence: 'low' | 'medium' | 'high';
  coverage_summary: string;
  limitations: string[];
  human_required: boolean;
}

export interface PolicyMatch {
  policy_ref: string;
  insurer_key: string;
  product: string | null;
  line_kind: string;
  policy_status: string;
  masked_policy_number: string;
  holder_name_masked: string | null;
  valid_from: string | null;
  valid_to: string | null;
}

export interface PolicyLookupResult {
  status: PolicyLookupStatus;
  source: PolicyLookupSource;
  source_ref: string | null;
  queried_document_type: 'cpf' | 'cnpj' | null;
  matches: PolicyMatch[];
  selected: PolicyMatch | null;
  coverage_evidence: CoverageEvidence | null;
  verification_status: VerificationStatus;
  next_macro_state: string;
  blockers: string[];
  requires_human: boolean;
  notes: string | null;
}

export interface PolicyLookupCaseData {
  customer_name?: string | null;
  insured_name?: string | null;
  document_type?: 'cpf' | 'cnpj' | null;
}

// Valores aceitos por attendance_cases.policy_source (CHECK da migração 20260612).
// 'mock' NÃO existe no schema → mock é persistido como 'snapshot' (snapshot canned).
const VALID_POLICY_SOURCES = new Set(['manual', 'upload', 'snapshot', 'infocap', 'connector', 'human', 'unknown']);

const MOCK_LIMITATION = 'Validação mock/manual para MVP; não representa consulta real à seguradora.';

function str(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v.trim() : null;
}

/** Máscara de número de apólice: mantém só os últimos 4. */
export function maskPolicyNumber(value?: string | null): string {
  const v = (value || '').trim();
  if (v.length <= 4) return '****';
  return `****${v.slice(-4)}`;
}

/** Máscara de nome: iniciais + ***. "Maria Silva" → "M*** S***". */
export function maskName(name?: string | null): string | null {
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

// Nota do snapshot por origem: connector/infocap é consulta real (sem payload bruto).
const CONNECTOR_SNAPSHOT_NOTE =
  'Snapshot sanitizado de apólice localizada via InfoCap/connector. Não contém payload bruto.';
const MOCK_SNAPSHOT_NOTE = 'Snapshot mínimo (mock/manual). Não é consulta real à seguradora.';

/** Snapshot mínimo e sanitizado (sem segredo, sem excesso de PII). */
export function sanitizePolicySnapshot(input: unknown): Record<string, unknown> {
  const o = input && typeof input === 'object' && !Array.isArray(input) ? (input as Record<string, unknown>) : {};
  const source = str(o.source);
  const isConnector = source === 'connector' || source === 'infocap';
  return {
    insurer_key: str(o.insurer_key),
    product: str(o.product),
    line_kind: str(o.line_kind),
    policy_status: str(o.policy_status),
    masked_policy_number: str(o.masked_policy_number),
    valid_from: str(o.valid_from),
    valid_to: str(o.valid_to),
    source,
    captured_at: new Date().toISOString(),
    note: isConnector ? CONNECTOR_SNAPSHOT_NOTE : MOCK_SNAPSHOT_NOTE,
  };
}

// Campos sensíveis que NUNCA podem vir no body (segredo/credencial).
const FORBIDDEN_INPUT_KEYS = ['token', 'password', 'senha', 'api_key', 'apikey', 'secret', 'credential', 'credentials'];

export interface PolicyLookupInput {
  source?: string;
  mode?: string;
  fixture?: string;
  policy_number?: string;
  insurer_key?: string;
  product?: string;
  line_kind?: string;
  policy_status?: string;
  coverage_summary?: string;
  limitations?: unknown;
  confidence?: string;
  human_required?: boolean;
  force?: boolean;
  [k: string]: unknown;
}

export function validatePolicyLookupInput(input: PolicyLookupInput): { valid: boolean; error?: string } {
  if (!input || typeof input !== 'object') return { valid: false, error: 'Body inválido' };

  for (const key of Object.keys(input)) {
    if (FORBIDDEN_INPUT_KEYS.includes(key.toLowerCase())) {
      return { valid: false, error: 'Campo sensível não permitido no body' };
    }
  }

  const mode = str(input.mode) || str(input.source);
  if (!mode) return { valid: false, error: 'Informe source/mode (mock ou manual)' };
  const m = mode.toLowerCase();
  if (m === 'mock') {
    if (!str(input.fixture)) return { valid: false, error: 'fixture é obrigatória no modo mock' };
    return { valid: true };
  }
  if (m === 'manual') {
    if (!str(input.coverage_summary) && !str(input.policy_number)) {
      return { valid: false, error: 'No modo manual informe pelo menos coverage_summary ou policy_number' };
    }
    return { valid: true };
  }
  return { valid: false, error: 'source/mode deve ser mock ou manual neste batch' };
}

// ---------------------------------------------------------------------------
// Fixtures de mock
// ---------------------------------------------------------------------------

export const POLICY_LOOKUP_FIXTURES = ['allianz_residential_electrician_covered'] as const;
export type PolicyLookupFixture = (typeof POLICY_LOOKUP_FIXTURES)[number];

export function isKnownFixture(name: string): name is PolicyLookupFixture {
  return (POLICY_LOOKUP_FIXTURES as readonly string[]).includes(name);
}

/** Resultado simulado (mock) para uma fixture conhecida. Lança se desconhecida. */
export function buildMockPolicyLookupResult(fixture: string, caseData: PolicyLookupCaseData): PolicyLookupResult {
  if (!isKnownFixture(fixture)) {
    throw new Error(`unknown_fixture:${fixture}`);
  }
  const now = new Date().toISOString();
  const docType = caseData.document_type ?? null;

  if (fixture === 'allianz_residential_electrician_covered') {
    const rawNumber = 'MOCK-ALLIANZ-RES-0001';
    const match: PolicyMatch = {
      policy_ref: 'mock-allianz-res-0001',
      insurer_key: 'allianz',
      product: 'Residencial',
      line_kind: 'residential',
      policy_status: 'active',
      masked_policy_number: maskPolicyNumber(rawNumber),
      holder_name_masked: maskName(caseData.customer_name || caseData.insured_name),
      valid_from: null,
      valid_to: null,
    };
    return {
      status: 'policy_evidence_ready',
      source: 'mock',
      source_ref: `mock:${fixture}`,
      queried_document_type: docType,
      matches: [match],
      selected: match,
      coverage_evidence: {
        source: 'mock',
        source_ref: `mock:${fixture}`,
        verified_at: now,
        verified_by: 'human',
        confidence: 'medium',
        coverage_summary:
          'Assistência residencial Allianz inclui suporte para eletricista emergencial (evidência mock/manual).',
        limitations: [MOCK_LIMITATION],
        human_required: false,
      },
      verification_status: 'verified_by_human',
      next_macro_state: 'policy_evidence_ready',
      blockers: [],
      requires_human: false,
      notes: 'Resultado simulado (mock) para destravar o fluxo E2E antes da API real da InfoCap.',
    };
  }

  // Inalcançável (isKnownFixture garante), mas mantém o tipo total.
  throw new Error(`unknown_fixture:${fixture}`);
}

/** Resultado a partir de entrada manual segura do operador. */
export function buildPolicyLookupResult(input: PolicyLookupInput, caseData: PolicyLookupCaseData): PolicyLookupResult {
  const now = new Date().toISOString();
  const docType = caseData.document_type ?? null;
  const rawNumber = str(input.policy_number);
  const coverageSummary = str(input.coverage_summary);
  const confidence = (['low', 'medium', 'high'] as const).includes(str(input.confidence) as any)
    ? (str(input.confidence) as 'low' | 'medium' | 'high')
    : 'medium';
  const limitations = Array.isArray(input.limitations)
    ? (input.limitations.filter((x): x is string => typeof x === 'string' && x.trim().length > 0).slice(0, 10))
    : [];
  if (!limitations.includes(MOCK_LIMITATION)) limitations.push(MOCK_LIMITATION);
  const humanRequired = input.human_required === true;

  const match: PolicyMatch = {
    policy_ref: `manual-${(rawNumber || 'sem-numero').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40)}`,
    insurer_key: str(input.insurer_key) || 'unknown',
    product: str(input.product),
    line_kind: str(input.line_kind) || 'unknown',
    policy_status: str(input.policy_status) || 'unknown',
    masked_policy_number: maskPolicyNumber(rawNumber),
    holder_name_masked: maskName(caseData.customer_name || caseData.insured_name),
    valid_from: null,
    valid_to: null,
  };

  if (!coverageSummary) {
    // Sem evidência de cobertura → não destrava; fica pendente.
    return {
      status: 'policy_lookup_pending',
      source: 'manual',
      source_ref: 'manual:operator',
      queried_document_type: docType,
      matches: [match],
      selected: match,
      coverage_evidence: null,
      verification_status: 'pending_human',
      next_macro_state: 'policy_lookup_required',
      blockers: ['no_coverage_summary'],
      requires_human: true,
      notes: 'Apólice informada manualmente, mas sem resumo de cobertura para gerar evidência.',
    };
  }

  return {
    status: 'policy_evidence_ready',
    source: 'manual',
    source_ref: 'manual:operator',
    queried_document_type: docType,
    matches: [match],
    selected: match,
    coverage_evidence: {
      source: 'manual',
      source_ref: 'manual:operator',
      verified_at: now,
      verified_by: 'human',
      confidence,
      coverage_summary: coverageSummary,
      limitations,
      human_required: humanRequired,
    },
    verification_status: 'verified_by_human',
    next_macro_state: 'policy_evidence_ready',
    blockers: [],
    requires_human: humanRequired,
    notes: 'Evidência registrada manualmente pelo operador (MVP).',
  };
}

/** Resumo seguro do resultado para diagnostics/metadata (sem PII crua). */
export function safePolicyLookupSummary(result: PolicyLookupResult): Record<string, unknown> {
  return {
    status: result.status,
    source: result.source,
    verification_status: result.verification_status,
    requires_human: result.requires_human,
    matches_count: result.matches.length,
    selected: result.selected
      ? {
          insurer_key: result.selected.insurer_key,
          product: result.selected.product,
          line_kind: result.selected.line_kind,
          policy_status: result.selected.policy_status,
          masked_policy_number: result.selected.masked_policy_number,
        }
      : null,
  };
}

function policySourceForColumn(source: PolicyLookupSource): string {
  if (source === 'mock') return 'snapshot'; // CHECK não aceita 'mock'
  if (VALID_POLICY_SOURCES.has(source)) return source;
  return 'unknown';
}

export interface PolicyLookupCasePayload {
  caseFields: {
    policy_source: string;
    policy_number: string | null;
    policy_snapshot: Record<string, unknown>;
    coverage_evidence: CoverageEvidence | null;
    verification_status: VerificationStatus;
    next_step: string;
  };
  metadataPatch: { attendance_macro_state: string; policy_lookup: Record<string, unknown> };
  runtimePatch: Record<string, unknown>;
  lastAgentAction: string;
}

/** Mapeia o resultado para os campos existentes de attendance_cases + corridor_runs. */
export function applyPolicyLookupResultToCasePayload(
  result: PolicyLookupResult,
  rawPolicyNumber: string | null,
): PolicyLookupCasePayload {
  const summary = safePolicyLookupSummary(result);
  const evidenceReady = result.coverage_evidence != null && result.status === 'policy_evidence_ready';
  const lastAgentAction =
    result.source === 'manual' ? 'policy_lookup:manual_verified' : 'policy_lookup:mock_verified';

  const nextStep = evidenceReady
    ? 'Apólice/evidência registrada. Próximo passo: retomar o corredor de atendimento.'
    : 'Apólice informada, mas sem evidência de cobertura suficiente. Aguardando verificação.';

  return {
    caseFields: {
      policy_source: policySourceForColumn(result.source),
      policy_number: rawPolicyNumber,
      policy_snapshot: sanitizePolicySnapshot({
        insurer_key: result.selected?.insurer_key,
        product: result.selected?.product,
        line_kind: result.selected?.line_kind,
        policy_status: result.selected?.policy_status,
        masked_policy_number: result.selected?.masked_policy_number,
        valid_from: result.selected?.valid_from,
        valid_to: result.selected?.valid_to,
        source: result.source,
      }),
      coverage_evidence: result.coverage_evidence,
      verification_status: result.verification_status,
      next_step: nextStep,
    },
    metadataPatch: { attendance_macro_state: result.next_macro_state, policy_lookup: summary },
    runtimePatch: {
      macro_state: result.next_macro_state,
      external_action_allowed: false,
      coverage_evidence_ready: evidenceReady,
      policy_lookup: summary,
    },
    lastAgentAction,
  };
}
