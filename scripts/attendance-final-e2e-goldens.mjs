#!/usr/bin/env node
/**
 * 42B7.2 — Final E2E Golden Tests (Attendance + InfoCap + WhatsApp simulated + Dispatch).
 *
 * Congela o comportamento do MVP para evitar regressão. LIVE: requer servidor + sessão.
 *
 *   BASE_URL=http://localhost:3000 \
 *   SESSION_COOKIE="<cookie iron-session autenticado>" \
 *   E2E_CPF="<cpf real de teste com apólice na InfoCap>" \   # opcional; sem ele, cenários InfoCap são SKIP
 *   node scripts/attendance-final-e2e-goldens.mjs
 *
 * Sem SESSION_COOKIE → SKIP geral (não falha). Sem E2E_CPF → SKIP dos cenários InfoCap.
 * NUNCA hardcoda CPF. NUNCA habilita envio externo. Tudo dry-run.
 */
import {
  WA_TRIAGE_MESSAGES,
  FORBIDDEN_PATTERNS,
  EXPECTED,
} from './fixtures/attendance-e2e.fixtures.mjs';

const BASE_URL = (process.env.BASE_URL || 'http://localhost:3000').replace(/\/$/, '');
const COOKIE = process.env.SESSION_COOKIE || '';
const CPF = process.env.E2E_CPF || '';
const CPF_DIGITS = CPF.replace(/\D/g, '');
const SUBCORRIDOR = process.env.ATTENDANCE_TEST_SUBCORRIDOR || 'electrician';

let pass = 0, fail = 0, skipped = 0;
const failures = [];
const createdCaseIds = [];

function ok(name) { pass++; console.log(`  ✓ ${name}`); }
function ko(name, detail) { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
function assert(name, cond, detail) { cond ? ok(name) : ko(name, detail); }
function skip(name) { skipped++; console.log(`  ⊘ SKIP ${name}`); }

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(COOKIE ? { Cookie: COOKIE } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  let json = null;
  try { json = await res.json(); } catch { json = null; }
  return { status: res.status, json };
}
function uniquePhone() { return `5544${Math.floor(100000 + Math.random() * 899999)}`; }
async function sim(phone, text, extra = {}) {
  const { json } = await api('/api/attendance/whatsapp/simulate-inbound', {
    method: 'POST',
    body: { from_phone: phone, from_name: 'Cliente Teste', text, ...extra },
  });
  return json || {};
}

/** Asserções de segurança/PII aplicadas a QUALQUER resposta pública. */
function secScan(label, resp, phone) {
  const raw = JSON.stringify(resp ?? {});
  if (CPF_DIGITS) assert(`${label}: sem CPF cru`, !raw.includes(CPF_DIGITS) && (!CPF || !raw.includes(CPF)), 'CPF no output');
  if (phone) assert(`${label}: sem telefone cru`, !raw.includes(phone), 'telefone cru no output');
  for (const p of FORBIDDEN_PATTERNS) assert(`${label}: sem ${p.name}`, !p.re.test(raw), `${p.name} no output`);
  // outbound/external nunca enviado
  if (resp?.outbound) assert(`${label}: outbound.sent=false`, resp.outbound.sent === false);
  if (resp?.external_action) assert(`${label}: external_action.sent=false`, resp.external_action.sent === false);
}

// ---------------------------------------------------------------------------
async function scenarioA_dashboard() {
  console.log('\n[A] Dashboard E2E — Allianz Residencial / Eletricista (InfoCap)');
  if (!CPF) { skip('A: requer E2E_CPF'); return; }
  const created = await api('/api/attendance/cases', { method: 'POST', body: { customer_name: 'Teste Golden', channel: 'dashboard', selected_subcorridor_key: SUBCORRIDOR, create_conversation: true } });
  if (created.status !== 201 || !created.json?.case?.id) { ko('A: criar caso', `status=${created.status}`); return; }
  const id = created.json.case.id; createdCaseIds.push(id);
  ok('A: caso criado');
  const reply = (m) => api(`/api/attendance/cases/${id}/runtime/reply`, { method: 'POST', body: { message: m, source: 'dashboard' } });
  await reply('estou sem luz só na cozinha');
  await reply('não, sem cheiro de queimado nem faísca');
  const r3 = await reply(CPF);
  assert('A: CPF → policy_lookup_required', r3.json?.next_step?.status === 'policy_lookup_required' || r3.json?.case?.status === 'policy_check', JSON.stringify(r3.json?.next_step));
  secScan('A r3', r3.json);
  const lk = await api(`/api/attendance/cases/${id}/runtime/policy-lookup`, { method: 'POST', body: { source: 'infocap', mode: 'connector' } });
  const plr = lk.json?.policy_lookup_result; const st = plr?.status;
  assert('A: lookup status conhecido', ['multiple_matches', 'found', 'client_found', 'not_found', 'provider_error', 'auth_error'].includes(st), `st=${st}`);
  secScan('A lookup', lk.json);
  if (st !== 'multiple_matches' && st !== 'found') { skip(`A: InfoCap retornou ${st} (sem apólice selecionável neste ambiente)`); return; }
  const ref = st === 'multiple_matches' ? plr.matches?.[0]?.policy_ref : plr.selected?.policy_ref;
  const selr = await api(`/api/attendance/cases/${id}/runtime/policy-select`, { method: 'POST', body: { source: 'infocap', policy_ref: ref } });
  assert('A: policy-select ok', selr.status === 200 && selr.json?.ok === true, `status=${selr.status}`);
  assert('A: verified_by_connector antes do HITL', String(selr.json?.case?.verification_status || '').startsWith('verified'), selr.json?.case?.verification_status);
  secScan('A select', selr.json);
  await reply('é na cozinha');
  await reply('fico totalmente sem energia na cozinha');
  await reply('sim, é o mesmo endereço da apólice');
  const d1 = await api(`/api/attendance/cases/${id}/runtime/dispatch-dry-run`, { method: 'POST' });
  assert('A: dispatch antes HITL = hitl_required', d1.json?.dispatch_readiness?.packet_state === 'hitl_required', d1.json?.dispatch_readiness?.packet_state);
  assert('A: external_action.sent=false', d1.json?.external_action?.sent === false);
  secScan('A dispatch1', d1.json);
  const cv = await api(`/api/attendance/cases/${id}/runtime/coverage-validation`, { method: 'POST', body: { decision: 'approved', source: 'human' } });
  assert('A: coverage approved', cv.json?.ok === true && cv.json?.coverage_validation?.dispatch_allowed === true, JSON.stringify(cv.json?.coverage_validation));
  const det = await api(`/api/attendance/cases/${id}`);
  assert('A: verified_by_human após HITL', det.json?.case?.verification_status === 'verified_by_human', det.json?.case?.verification_status);
  const d2 = await api(`/api/attendance/cases/${id}/runtime/dispatch-dry-run`, { method: 'POST' });
  assert('A: dispatch após HITL = ready_for_human_approval', d2.json?.dispatch_readiness?.packet_state === 'ready_for_human_approval', d2.json?.dispatch_readiness?.packet_state);
  assert('A: dispatch após HITL não envia', d2.json?.external_action?.sent === false);
  secScan('A dispatch2', d2.json);
}

async function scenarioB_whatsappResidential() {
  console.log('\n[B] WhatsApp simulado — residencial/eletricista');
  if (!CPF) { skip('B: requer E2E_CPF'); return; }
  const P = uniquePhone();
  await sim(P, 'Oi'); await sim(P, 'estou sem luz'); await sim(P, 'só na cozinha'); await sim(P, 'não tem cheiro de queimado nem faísca');
  const cpf = await sim(P, CPF); secScan('B cpf', cpf, P);
  const pick = await sim(P, 'a primeira'); secScan('B pick', pick, P);
  assert('B: policy_selected', pick.action === 'policy_selected' && Boolean(pick.selected_policy_ref), JSON.stringify({ a: pick.action }));
  const s1 = await sim(P, 'é na cozinha'); secScan('B s1', s1, P);
  assert('B: pós-seleção NÃO repete lista de apólices', !/encontrei mais de uma ap[óo]lice/i.test(String(s1.auto_reply || '')) && s1.action !== 'policy_selection_pending', s1.action);
  await sim(P, 'fico totalmente sem energia na cozinha');
  const end = await sim(P, 'sim, é o mesmo endereço da apólice'); secScan('B end', end, P);
  if (end.case_id) {
    createdCaseIds.push(end.case_id);
    const det = await api(`/api/attendance/cases/${end.case_id}`);
    assert('B: upgrade para corredor residencial', det.json?.case?.selected_corridor_key === EXPECTED.residential.upgrade_corridor, det.json?.case?.selected_corridor_key);
    assert('B: subcorridor electrician', det.json?.case?.selected_subcorridor_key === 'electrician', det.json?.case?.selected_subcorridor_key);
    assert('B: dispatch hitl_required', det.json?.case?.metadata?.dispatch_readiness?.packet_state === 'hitl_required', det.json?.case?.metadata?.dispatch_readiness?.packet_state);
    secScan('B detail', det.json, P);
  }
  assert('B: outbound dry-run', end.outbound?.dry_run === true && end.outbound?.sent === false, JSON.stringify(end.outbound));
}

async function scenarioC_claimTriage() {
  console.log('\n[C] WhatsApp triage global — sinistro');
  const P = uniquePhone();
  const r = await sim(P, WA_TRIAGE_MESSAGES.claim); secScan('C', r, P);
  assert('C: action triage', r.action === 'triage', r.action);
  const ev = r.diagnostics?.events || [];
  assert('C: intent claim', r.intent === 'claim' || ev.some((e) => /intent:claim/.test(e)), JSON.stringify(ev));
  assert('C: não vira residencial/allianz', !ev.some((e) => /corridor:allianz/.test(e)), JSON.stringify(ev));
  if (r.case_id) { createdCaseIds.push(r.case_id); const det = await api(`/api/attendance/cases/${r.case_id}`); assert('C: corridor null', det.json?.case?.selected_corridor_key == null && det.json?.case?.selected_subcorridor_key == null, `${det.json?.case?.selected_corridor_key}/${det.json?.case?.selected_subcorridor_key}`); }
  assert('C: outbound dry-run', r.outbound?.dry_run === true && r.outbound?.sent === false);
}

async function scenarioD_policyQuestion() {
  console.log('\n[D] WhatsApp policy question / consulta apólice');
  const P = uniquePhone();
  const r = await sim(P, WA_TRIAGE_MESSAGES.policy_question); secScan('D', r, P);
  const ev = r.diagnostics?.events || [];
  assert('D: intent policy_question/consultation', ev.some((e) => /intent:policy_/.test(e)) || ['triage', 'triage_pending'].includes(r.action), JSON.stringify(ev));
  assert('D: não aciona/inventa cobertura (triage)', r.action === 'triage' || r.action === 'triage_pending', r.action);
  assert('D: não vira residencial automaticamente', !ev.some((e) => /corridor:allianz/.test(e)), JSON.stringify(ev));
}

async function scenarioE_outOfOrder() {
  console.log('\n[E] WhatsApp ordem fora do padrão');
  if (!CPF) { skip('E: requer E2E_CPF'); return; }
  const P = uniquePhone();
  await sim(P, 'estou sem luz'); await sim(P, 'só na cozinha');
  const late = await sim(P, 'não tem cheiro de queimado'); secScan('E late', late, P);
  assert('E: risco tardio não vira "CPF inválido"', !/cpf.*inv[áa]lido|n[úu]mero v[áa]lido de cpf/i.test(String(late.auto_reply || '')), String(late.auto_reply));
  const cpf = await sim(P, CPF); secScan('E cpf', cpf, P);
  assert('E: fluxo segue após CPF', cpf.ok !== false, JSON.stringify(cpf.action));
}

async function scenarioF_ambiguousSelection() {
  console.log('\n[F] WhatsApp seleção ambígua');
  if (!CPF) { skip('F: requer E2E_CPF'); return; }
  const P = uniquePhone();
  await sim(P, 'Oi'); await sim(P, 'estou sem luz'); await sim(P, 'só na cozinha'); await sim(P, 'não tem cheiro de queimado nem faísca');
  const cpf = await sim(P, CPF);
  // só faz sentido se vieram múltiplas apólices
  const hasMatches = /encontrei mais de uma ap[óo]lice/i.test(String(cpf.auto_reply || ''));
  if (!hasMatches) { skip('F: ambiente não retornou múltiplas apólices'); return; }
  const amb = await sim(P, 'essa'); secScan('F amb', amb, P);
  assert('F: ambíguo não seleciona sozinho', amb.action !== 'policy_selected', amb.action);
  assert('F: pede esclarecimento com lista', /qual delas|encontrei mais de uma/i.test(String(amb.auto_reply || '')), String(amb.auto_reply));
}

async function scenarioG_handoffBlocks() {
  console.log('\n[G] Handoff bloqueia auto-resposta');
  const P = uniquePhone();
  const first = await sim(P, 'preciso de ajuda urgente');
  const caseId = first.case_id;
  if (!caseId) { skip('G: case não criado'); return; }
  createdCaseIds.push(caseId);
  const patched = await api(`/api/attendance/cases/${caseId}`, { method: 'PATCH', body: { status: 'handoff', handoff_required: true, handoff_reason: 'manual_review' } });
  if (patched.status !== 200) { skip(`G: não conseguiu marcar handoff (status=${patched.status})`); return; }
  const r = await sim(P, 'tem novidade?'); secScan('G', r, P);
  assert('G: handoff_block', r.action === 'handoff_block', r.action);
  assert('G: auto_reply nulo', r.auto_reply == null);
  assert('G: outbound não enviado', r.outbound?.sent === false);
}

async function scenarioH_media() {
  console.log('\n[H] Mídia básica não trava');
  const P = uniquePhone();
  for (const kind of ['audio', 'image', 'document', 'location']) {
    const r = await sim(P, '', { media_kind: kind });
    secScan(`H ${kind}`, r, P);
    assert(`H ${kind}: responde ack sem travar`, r.ok === true && typeof r.auto_reply === 'string' && r.auto_reply.length > 0, JSON.stringify({ ok: r.ok }));
    assert(`H ${kind}: não vaza URL/payload`, !/http(s)?:\/\//i.test(String(r.auto_reply || '')), String(r.auto_reply));
  }
}

async function main() {
  console.log('== 42B7.2 — Final E2E Golden Tests ==');
  console.log(`BASE_URL=${BASE_URL} · CPF=${CPF ? 'set' : 'unset'} · cookie=${COOKIE ? 'set' : 'unset'}`);
  if (!COOKIE) {
    console.log('\n[SKIP] SESSION_COOKIE ausente — testes live ignorados (não é falha).');
    console.log('Defina SESSION_COOKIE (e E2E_CPF para cenários InfoCap) e rode novamente.');
    process.exit(0);
  }
  await scenarioA_dashboard();
  await scenarioB_whatsappResidential();
  await scenarioC_claimTriage();
  await scenarioD_policyQuestion();
  await scenarioE_outOfOrder();
  await scenarioF_ambiguousSelection();
  await scenarioG_handoffBlocks();
  await scenarioH_media();

  console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam, ${skipped} pulados ==`);
  console.log(`cases criados: ${createdCaseIds.length}`);
  if (fail > 0) { console.log('Falhas:'); for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
  process.exit(0);
}
main().catch((e) => { console.error('Erro inesperado:', e?.message || e); process.exit(2); });
