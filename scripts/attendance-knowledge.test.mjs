#!/usr/bin/env node
/**
 * 42R0 — Attendance Knowledge/RAG safe context (offline, sem rede).
 *
 *   node scripts/attendance-knowledge.test.mjs
 *
 * Garante: conhecimento geral explica conceitos; NUNCA confirma cobertura sem
 * evidência; sem PII na query; provenance presente; fallback sem RAG funciona.
 */
import {
  buildAttendanceKnowledgeQuery,
  retrieveAttendanceKnowledge,
  knowledgeLeadForCategory,
  knowledgeForLlm,
  safeKnowledgeSummary,
} from '../lib/attendance/attendance-knowledge.ts';
import { buildPolicyQAContext, answerPolicyQuestionDeterministic } from '../lib/attendance/policy-qa.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

const RES_CTX = { corridor: 'allianz_residential_assistance', subcorridor: 'electrician', insurer: 'allianz', product: 'Residencial', macro_service: 'residential_assistance' };

console.log('== 42R0 — Attendance Knowledge/RAG ==');

// [1] Query sanitizada (sem PII).
console.log('\n[1] query sanitizada');
{
  const q = buildAttendanceKnowledgeQuery(RES_CTX, 'assistance_question');
  const raw = JSON.stringify(q);
  assert('categoria presente', q.category === 'assistance_question');
  assert('terms inclui subcorridor/product/macro', q.terms.includes('electrician'));
  assert('sem CPF/telefone na query', !/\d{8,}/.test(raw));
}

// [2] Recuperação por categoria.
console.log('\n[2] recuperação');
{
  const assist = retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'assistance_question'));
  assert('assistência → snippets', assist.snippets.length > 0);
  assert('assistência → inclui elétrica (residencial)', assist.snippets.some((s) => /el[ée]tric/i.test(s.title) || /el[ée]tric/i.test(s.summary)));
  const proc = retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'process_status_question'));
  assert('processo → snippet de processo', proc.snippets.some((s) => /atendimento/i.test(s.title)));
  const status = retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'policy_status_question'));
  assert('status → sem snippet (usa evidence)', status.snippets.length === 0 && status.unavailable_reason === 'no_relevant_knowledge');
  assert('warning rag_not_configured (builtin)', assist.warnings.includes('rag_not_configured_using_builtin'));
  assert('provenance presente', assist.snippets.every((s) => typeof s.provenance === 'string' && s.provenance.length > 0));
}

// [3] Lead só em categorias conceituais.
console.log('\n[3] knowledge lead');
{
  const snip = retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'assistance_question')).snippets;
  assert('assistência → lead', typeof knowledgeLeadForCategory(snip, 'assistance_question') === 'string');
  assert('coverage → lead', typeof knowledgeLeadForCategory(retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'policy_coverage_question')).snippets, 'policy_coverage_question') === 'string');
  assert('status → sem lead', knowledgeLeadForCategory(snip, 'policy_status_question') === null);
  assert('dispatch → sem lead', knowledgeLeadForCategory(snip, 'dispatch_status_question') === null);
}

// [4] CRÍTICO: cobertura NÃO é confirmada mesmo com knowledge.
console.log('\n[4] knowledge NÃO confirma cobertura');
{
  const caseLow = {
    policy_source: 'connector', verification_status: 'verified_by_connector',
    policy_snapshot: { insurer_key: 'Allianz', product: 'Residencial', active_now: true, valid_to: '31/10/2026', cancelled: false, policy_ref: '97652' },
    coverage_evidence: { confidence: 'low', human_required: true, source: 'connector' },
    metadata: { coverage_readiness: { human_required: true }, policy_interpretation_context: { coverage_confirmed: false } },
  };
  const kn = retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'policy_coverage_question'));
  const ctx = buildPolicyQAContext(caseLow, { knowledge: kn.snippets.map((s) => ({ title: s.title, summary: s.summary, provenance: s.provenance, scope: s.scope })) });
  const lead = knowledgeLeadForCategory(kn.snippets, 'policy_coverage_question');
  const det = answerPolicyQuestionDeterministic('policy_coverage_question', ctx);
  const full = `${lead} ${det.answer}`;
  assert('inclui conceito geral (Em geral)', /em geral/i.test(full), full);
  assert('mantém limite (não trouxe itens / validar)', /(não trouxe os itens|valida)/i.test(full), full);
  assert('NÃO afirma cobertura específica', !/sim,? (voc[êe]|tem cobertura|cobre eletricista)/i.test(full), full);
  assert('ctx tem knowledge', Array.isArray(ctx.knowledge) && ctx.knowledge.length > 0);
}

// [5] Fallback sem RAG: status segue evidence (sem knowledge).
console.log('\n[5] fallback determinístico');
{
  const caseConfirmed = {
    policy_source: 'connector', verification_status: 'verified_by_connector',
    policy_snapshot: { insurer_key: 'Allianz', product: 'Residencial', active_now: true, valid_to: '31/10/2026', cancelled: false },
    metadata: { policy_interpretation_context: { coverage_confirmed: true } },
  };
  const ctx = buildPolicyQAContext(caseConfirmed, {});
  const a = answerPolicyQuestionDeterministic('policy_status_question', ctx);
  assert('status vigente sem depender de knowledge', /vigente/i.test(a.answer));
  assert('ctx.knowledge vazio sem snippets', Array.isArray(ctx.knowledge) && ctx.knowledge.length === 0);
}

// [6] knowledgeForLlm + summary seguros.
console.log('\n[6] llm strings + summary');
{
  const kn = retrieveAttendanceKnowledge(buildAttendanceKnowledgeQuery(RES_CTX, 'assistance_question'));
  const forLlm = knowledgeForLlm(kn.snippets);
  assert('strings curtas p/ LLM', forLlm.length > 0 && forLlm.every((s) => typeof s === 'string'));
  const sum = safeKnowledgeSummary(kn);
  assert('summary tem ids', Array.isArray(sum.ids) && sum.ids.length > 0);
  assert('summary não despeja conteúdo grande', !JSON.stringify(sum).includes('emergenciais como eletricista'));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
