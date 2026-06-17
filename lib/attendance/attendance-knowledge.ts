// Attendance Knowledge / RAG Safe Context Layer (42R0) — sem I/O obrigatório.
//
// Fornece CONHECIMENTO GERAL e seguro para o Policy Q&A explicar conceitos
// (assistência, cobertura elétrica, assistência x sinistro, processo). O
// conhecimento NUNCA confirma cobertura específica — isso é sempre do Evidence
// Pack. Hoje a base é uma curadoria interna (sem ingestão); a interface de
// recuperação fica future-ready para um RAG real do Smith (Qdrant) via 42R1.
//
// Decisão: NÃO criar motor RAG paralelo. Quando o Smith expuser um endpoint de
// knowledge para atendimento, `retrieveAttendanceKnowledge` passa a mesclá-lo.

import type { AttendanceQuestionCategory } from './policy-qa';

export type KnowledgeScope = 'global' | 'tenant' | 'corridor' | 'insurer';

export interface KnowledgeSnippet {
  id: string;
  title: string;
  summary: string;
  scope: KnowledgeScope;
  source_type: string; // ex.: 'curated_builtin' | 'rag_chunk'
  provenance: string; // origem rastreável, sem PII
  confidence: 'low' | 'medium' | 'high';
  /** Frase curta de conceito GERAL p/ liderar a resposta (nunca confirma cobertura). */
  lead?: string;
}

export interface KnowledgeQuery {
  category: AttendanceQuestionCategory;
  corridor: string | null;
  subcorridor: string | null;
  insurer: string | null;
  product: string | null;
  macro_service: string | null;
  terms: string[];
}

export interface KnowledgeResult {
  snippets: KnowledgeSnippet[];
  warnings: string[];
  unavailable_reason?: string;
}

// --- Curadoria interna (conceitos gerais, seguros, sem confirmar cobertura) ---
const BUILTIN: KnowledgeSnippet[] = [
  {
    id: 'kb-residential-assistance',
    title: 'O que é assistência residencial',
    summary:
      'Assistência residencial é um serviço emergencial que pode incluir eletricista, encanador, chaveiro e outros, conforme o produto/plano contratado.',
    scope: 'global',
    source_type: 'curated_builtin',
    provenance: 'curadoria interna AutoBrokers (conceito geral)',
    confidence: 'medium',
    lead: 'Em geral, a assistência residencial pode incluir serviços emergenciais como eletricista, dependendo do produto contratado.',
  },
  {
    id: 'kb-electrical-assistance',
    title: 'Assistência elétrica (geral)',
    summary:
      'A assistência elétrica costuma cobrir reparos emergenciais de problemas elétricos na residência, dentro dos limites e condições da apólice.',
    scope: 'global',
    source_type: 'curated_builtin',
    provenance: 'curadoria interna AutoBrokers (conceito geral)',
    confidence: 'medium',
    lead: 'Em geral, a assistência elétrica cobre reparos emergenciais, dentro dos limites e condições da apólice.',
  },
  {
    id: 'kb-assistance-vs-claim',
    title: 'Assistência x sinistro',
    summary:
      'Assistência é um serviço emergencial (ex.: enviar um profissional). Sinistro é um pedido de indenização por um dano coberto (ex.: incêndio, roubo). São processos diferentes.',
    scope: 'global',
    source_type: 'curated_builtin',
    provenance: 'curadoria interna AutoBrokers (conceito geral)',
    confidence: 'high',
    lead: 'Assistência é um serviço emergencial; sinistro é um pedido de indenização por um dano coberto — são processos diferentes.',
  },
  {
    id: 'kb-process',
    title: 'Como funciona o atendimento',
    summary:
      'O atendimento normalmente segue: localizar a apólice, validar a cobertura, reunir os dados do problema e preparar o acionamento para a equipe revisar.',
    scope: 'global',
    source_type: 'curated_builtin',
    provenance: 'curadoria interna AutoBrokers (procedimento)',
    confidence: 'high',
    lead: 'O atendimento segue por etapas: localizar a apólice, validar a cobertura, reunir os dados e preparar o acionamento.',
  },
];

const RESIDENTIAL_RE = /resid|el[ée]tric|eletric|luz|energia|disjuntor|encanad|chaveiro/i;

/** Monta uma query de knowledge SANITIZADA (sem CPF/telefone/nome/endereço). */
export function buildAttendanceKnowledgeQuery(
  ctx: {
    corridor?: string | null;
    subcorridor?: string | null;
    insurer?: string | null;
    product?: string | null;
    macro_service?: string | null;
  },
  category: AttendanceQuestionCategory,
): KnowledgeQuery {
  const terms: string[] = [];
  for (const v of [ctx.subcorridor, ctx.product, ctx.macro_service]) {
    if (typeof v === 'string' && v.trim()) terms.push(v.trim().toLowerCase());
  }
  return {
    category,
    corridor: ctx.corridor ?? null,
    subcorridor: ctx.subcorridor ?? null,
    insurer: ctx.insurer ?? null,
    product: ctx.product ?? null,
    macro_service: ctx.macro_service ?? null,
    terms,
  };
}

/**
 * Recupera conhecimento seguro para a pergunta. Hoje: curadoria interna por
 * categoria/termos. Future-ready: quando `ATTENDANCE_KNOWLEDGE_URL` existir, este
 * helper mesclará snippets do RAG do Smith (sanitizados). NUNCA confirma cobertura.
 */
export function retrieveAttendanceKnowledge(query: KnowledgeQuery): KnowledgeResult {
  const warnings: string[] = [];
  const ragConfigured = Boolean(process.env.ATTENDANCE_KNOWLEDGE_URL);
  if (!ragConfigured) warnings.push('rag_not_configured_using_builtin');

  const snippets: KnowledgeSnippet[] = [];
  const isResidential = (query.corridor || '').includes('residential') || RESIDENTIAL_RE.test(query.terms.join(' '));

  switch (query.category) {
    case 'assistance_question':
    case 'policy_coverage_question':
      if (isResidential) snippets.push(BUILTIN[1]); // assistência elétrica
      snippets.push(BUILTIN[0]); // assistência residencial
      break;
    case 'process_status_question':
      snippets.push(BUILTIN[3]); // processo
      break;
    case 'clarification_question':
      snippets.push(BUILTIN[3], BUILTIN[0]);
      break;
    case 'new_issue_or_intent_shift':
      snippets.push(BUILTIN[2]); // assistência x sinistro
      break;
    default:
      break;
  }

  return { snippets: snippets.slice(0, 3), warnings, unavailable_reason: snippets.length === 0 ? 'no_relevant_knowledge' : undefined };
}

/** Frase de conceito geral para liderar a resposta (nunca confirma cobertura). */
export function knowledgeLeadForCategory(snippets: KnowledgeSnippet[], category: AttendanceQuestionCategory): string | null {
  // Só lideramos a resposta com conceito geral em perguntas conceituais/cobertura.
  const eligible =
    category === 'policy_coverage_question' ||
    category === 'assistance_question' ||
    category === 'clarification_question' ||
    category === 'process_status_question';
  if (!eligible) return null;
  const withLead = snippets.find((s) => typeof s.lead === 'string' && s.lead.trim());
  return withLead?.lead?.trim() || null;
}

/** Strings curtas e seguras p/ alimentar o LLM (conceitos gerais). */
export function knowledgeForLlm(snippets: KnowledgeSnippet[]): string[] {
  return snippets.slice(0, 3).map((s) => `${s.title}: ${s.summary}`);
}

/** Resumo p/ diagnostics (títulos/provenance/escopo; sem dump de conteúdo). */
export function safeKnowledgeSummary(result: KnowledgeResult): Record<string, unknown> {
  return {
    count: result.snippets.length,
    ids: result.snippets.map((s) => s.id),
    scopes: result.snippets.map((s) => s.scope),
    source_types: Array.from(new Set(result.snippets.map((s) => s.source_type))),
    unavailable_reason: result.unavailable_reason ?? null,
    warnings: result.warnings,
  };
}
