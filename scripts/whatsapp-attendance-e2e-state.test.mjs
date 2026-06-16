#!/usr/bin/env node
/**
 * 42W1.2 — WhatsApp Attendance E2E state (LIVE, requer servidor + sessão).
 *
 *   BASE_URL=http://localhost:3000 SESSION_COOKIE="<cookie>" node scripts/whatsapp-attendance-e2e-state.test.mjs
 *
 * Sem SESSION_COOKIE → SKIP (não falha). Usa o CPF de teste do Founder.
 * Valida: seleção não se repete após resolvida; subcorridor electrician;
 * sinistro vira triage; outbound dry-run.
 */
const BASE_URL = (process.env.BASE_URL || 'http://localhost:3000').replace(/\/$/, '');
const COOKIE = process.env.SESSION_COOKIE || '';
const CPF = process.env.E2E_CPF || '04760897941';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

async function sim(from, text) {
  const r = await fetch(`${BASE_URL}/api/attendance/whatsapp/simulate-inbound`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(COOKIE ? { Cookie: COOKIE } : {}) },
    body: JSON.stringify({ from_phone: from, from_name: 'Cliente Teste', text }),
  });
  return r.json().catch(() => ({}));
}

async function main() {
  console.log('== 42W1.2 — WhatsApp E2E state ==');
  if (!COOKIE) {
    console.log('[SKIP] SESSION_COOKIE ausente — defina para rodar o teste live.');
    process.exit(0);
  }

  // Fluxo residencial — telefone único por execução.
  const PHONE = `5544${Math.floor(100000 + Math.random() * 899999)}`;
  await sim(PHONE, 'Oi');
  await sim(PHONE, 'estou sem luz');
  await sim(PHONE, 'só na cozinha');
  await sim(PHONE, 'não tem cheiro de queimado nem faísca');
  const cpf = await sim(PHONE, CPF);
  assert('CPF → lista de apólices (multiple_matches)', /ap[óo]lice/i.test(String(cpf.auto_reply || '')) || cpf.action === 'policy_selection_pending' || cpf.diagnostics?.events?.includes('policy_lookup_multiple_matches'), JSON.stringify(cpf.diagnostics?.events));

  const pick = await sim(PHONE, 'a primeira');
  assert('seleção resolvida', pick.action === 'policy_selected' && pick.selected_policy_ref, JSON.stringify({ a: pick.action, r: pick.selected_policy_ref }));
  assert('outbound dry-run', pick.outbound?.dry_run === true && pick.outbound?.sent === false);

  // Slots após seleção — NÃO pode voltar a pedir apólice (P0).
  const s1 = await sim(PHONE, 'é na cozinha');
  assert('pós-seleção não repete lista de apólices', !/encontrei mais de uma ap[óo]lice/i.test(String(s1.auto_reply || '')), String(s1.auto_reply));
  assert('pós-seleção não volta a policy_selection_pending', s1.action !== 'policy_selection_pending', s1.action);
  await sim(PHONE, 'fico totalmente sem energia na cozinha');
  const end = await sim(PHONE, 'sim, é o mesmo endereço da apólice');
  assert('final não fica em policy_selection_pending', end.action !== 'policy_selection_pending', end.action);

  if (end.case_id) {
    const det = await (await fetch(`${BASE_URL}/api/attendance/cases/${end.case_id}`, { headers: COOKIE ? { Cookie: COOKIE } : {} })).json();
    assert('selected_subcorridor_key = electrician', det.case?.selected_subcorridor_key === 'electrician', String(det.case?.selected_subcorridor_key));
    assert('verification verified_by_connector', String(det.case?.verification_status || '').startsWith('verified'), det.case?.verification_status);
    assert('dispatch_readiness não é policy_selection_pending', det.case?.metadata?.dispatch_readiness?.packet_state !== 'policy_selection_pending');
  }

  // Sinistro → triage.
  const claimPhone = `5544${Math.floor(100000 + Math.random() * 899999)}`;
  const claim = await sim(claimPhone, 'bati o carro e preciso de ajuda');
  assert('sinistro → triage', claim.action === 'triage' && (claim.intent === 'claim' || claim.diagnostics?.events?.some((e) => /intent:claim/.test(e))), JSON.stringify({ a: claim.action, i: claim.intent }));

  console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
  if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
  process.exit(0);
}
main().catch((e) => { console.error('erro:', e?.message || e); process.exit(2); });
