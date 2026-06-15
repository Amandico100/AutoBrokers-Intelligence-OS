#!/usr/bin/env node
/**
 * 42B7 — Attendance E2E Golden Tests
 *
 * Suíte de regressão do fluxo Allianz Residencial / Eletricista contra o runtime
 * determinístico do Web (rotas /api/attendance/cases/.../runtime/*).
 *
 * Como rodar (requer Web no ar + sessão autenticada):
 *   BASE_URL=http://localhost:3000 \
 *   SESSION_COOKIE="<cole o Cookie do navegador autenticado>" \
 *   node scripts/attendance-golden-tests.mjs
 *
 * Variáveis:
 *   BASE_URL                         default http://localhost:3000
 *   SESSION_COOKIE                   cookie iron-session (obrigatório p/ testes live)
 *   BACKEND_URL                      opcional, health do backend
 *   ATTENDANCE_TEST_SUBCORRIDOR      default 'electrician'
 *   ATTENDANCE_LLM_FALLBACK_ENABLED  awareness do flag (só p/ asserts do off-topic)
 *
 * NUNCA usa CPF real — usa o fictício 123.456.789-09.
 * NUNCA depende de WhatsApp/InfoCap real.
 * NUNCA imprime CPF nos resultados (mascarado).
 *
 * IMPORTANTE (endpoint correto): o backend de fallback é POST /attendance/agent-reply
 * (SEM o prefixo /api). O Web NÃO expõe /api/attendance/agent-reply.
 */

const BASE_URL = (process.env.BASE_URL || 'http://localhost:3000').replace(/\/$/, '');
const SESSION_COOKIE = process.env.SESSION_COOKIE || '';
const BACKEND_URL = process.env.BACKEND_URL || '';
const SUBCORRIDOR = process.env.ATTENDANCE_TEST_SUBCORRIDOR || 'electrician';
const LLM_FLAG = process.env.ATTENDANCE_LLM_FALLBACK_ENABLED === 'true';

const FAKE_CPF = '123.456.789-09';
const FAKE_CPF_DIGITS = '12345678909';

let pass = 0;
let fail = 0;
const failures = [];

function ok(name) {
  pass += 1;
  console.log(`  ✓ ${name}`);
}
function ko(name, detail) {
  fail += 1;
  failures.push({ name, detail });
  console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`);
}
function assert(name, cond, detail) {
  if (cond) ok(name);
  else ko(name, detail);
}
function mask(s) {
  return String(s == null ? '' : s).replace(/\d[\d.\-/\s]{6,}\d/g, '[masked]');
}

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(SESSION_COOKIE ? { Cookie: SESSION_COOKIE } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let json = null;
  try {
    json = await res.json();
  } catch {
    json = null;
  }
  return { status: res.status, json };
}

function containsCpf(raw) {
  return raw.includes(FAKE_CPF_DIGITS) || raw.includes(FAKE_CPF);
}
function noCpfExposed(label, resp) {
  const raw = JSON.stringify(resp ?? {});
  const caseHasDoc = resp?.case && Object.prototype.hasOwnProperty.call(resp.case, 'insured_document_ref');
  assert(`${label}: resposta não contém insured_document_ref`, !caseHasDoc, 'campo presente no case');
  assert(`${label}: resposta não vaza CPF`, !containsCpf(raw), 'CPF cru no JSON');
}

async function createCase(label) {
  const { status, json } = await api('/api/attendance/cases', {
    method: 'POST',
    body: {
      customer_name: 'Teste Golden',
      channel: 'dashboard',
      selected_subcorridor_key: SUBCORRIDOR,
      create_conversation: true,
    },
  });
  if (status !== 201 || !json?.case?.id) {
    ko(`${label}: criar caso`, `status=${status}`);
    return null;
  }
  ok(`${label}: criar caso`);
  return json.case.id;
}

const getDetail = (id) => api(`/api/attendance/cases/${id}`);
const reply = (id, message) =>
  api(`/api/attendance/cases/${id}/runtime/reply`, { method: 'POST', body: { message, source: 'dashboard' } });
const step = (id) => api(`/api/attendance/cases/${id}/runtime/step`, { method: 'POST', body: { source: 'dashboard' } });
const policyLookup = (id) =>
  api(`/api/attendance/cases/${id}/runtime/policy-lookup`, {
    method: 'POST',
    body: { source: 'mock', mode: 'mock', fixture: 'allianz_residential_electrician_covered' },
  });
const policyLookupInfocap = (id) =>
  api(`/api/attendance/cases/${id}/runtime/policy-lookup`, {
    method: 'POST',
    body: { source: 'infocap', mode: 'connector' },
  });

function runtimeDiag(resp) {
  return resp?.corridor_run?.diagnostics?.runtime || {};
}

// Avança um caso novo até o gate de CPF (identity_document). Retorna caseId.
async function caseAtCpfGate(label) {
  const id = await createCase(label);
  if (!id) return null;
  await reply(id, 'Estou sem luz só na cozinha'); // → pergunta risco
  const r = await reply(id, 'Não, sem cheiro de queimado nem faísca.'); // → gate de CPF
  const sel = r.json?.next_step?.selected_slot;
  assert(`${label}: chegou ao gate de CPF`, sel === 'identity_document', `selected_slot=${sel}`);
  return id;
}

// ---------------------------------------------------------------------------
async function main() {
  console.log('== 42B7 — Attendance E2E Golden Tests ==');
  console.log(`BASE_URL=${BASE_URL} · LLM_FALLBACK_FLAG=${LLM_FLAG ? 'on' : 'off'}`);

  if (BACKEND_URL) {
    try {
      const h = await fetch(`${BACKEND_URL.replace(/\/$/, '')}/`);
      console.log(`backend / → ${h.status}`);
    } catch {
      console.log('backend health: indisponível (ok, opcional)');
    }
  }

  if (!SESSION_COOKIE) {
    console.log('\n[SKIP] SESSION_COOKIE ausente — testes live ignorados.');
    console.log('Defina SESSION_COOKIE com o cookie de uma sessão autenticada e rode novamente.');
    console.log('\nResumo: 0 testes live executados (skip).');
    process.exit(0);
  }

  // === Cenário 2: fluxo normal completo ===
  console.log('\n[2] Fluxo normal completo (sem luz na cozinha → CPF → policy → resume → slots)');
  {
    const id = await createCase('fluxo');
    if (id) {
      const r1 = await reply(id, 'Estou sem luz só na cozinha');
      assert('fluxo: reconhece problema e pergunta risco', r1.json?.next_step?.selected_slot === 'risk_indicators', `sel=${r1.json?.next_step?.selected_slot}`);
      noCpfExposed('fluxo r1', r1.json);

      const r2 = await reply(id, 'Não, sem cheiro de queimado nem faísca.');
      assert('fluxo: risco baixo → pede CPF', r2.json?.next_step?.selected_slot === 'identity_document', `sel=${r2.json?.next_step?.selected_slot}`);

      const r3 = await reply(id, FAKE_CPF);
      assert('fluxo: CPF capturado → policy_lookup_required', r3.json?.next_step?.status === 'policy_lookup_required' || r3.json?.intake?.status === 'policy_lookup_required', JSON.stringify(r3.json?.next_step));
      assert('fluxo: status do caso = policy_check', r3.json?.case?.status === 'policy_check', `status=${r3.json?.case?.status}`);
      noCpfExposed('fluxo r3 (pós-CPF)', r3.json);

      // 42B7.1: GET detail sanitizado (PII)
      const det = await getDetail(id);
      const detRaw = JSON.stringify(det.json ?? {});
      assert('detail: case sem insured_document_ref', det.json?.case && !Object.prototype.hasOwnProperty.call(det.json.case, 'insured_document_ref'), 'campo presente');
      assert('detail: has_insured_document_ref === true', det.json?.case?.has_insured_document_ref === true, `val=${det.json?.case?.has_insured_document_ref}`);
      assert('detail: não vaza CPF (formatado ou dígitos)', !containsCpf(detRaw), 'CPF cru no detail');
      assert('detail: messages não expõem CPF cru', !(det.json?.messages || []).some((m) => containsCpf(String(m?.content || ''))), 'CPF em messages');

      const pl = await policyLookup(id);
      assert('fluxo: policy lookup mock ok', pl.status === 200 && pl.json?.ok === true, `status=${pl.status}`);
      assert('fluxo: verification_status confiável', String(pl.json?.case?.verification_status || '').startsWith('verified'), `vs=${pl.json?.case?.verification_status}`);
      assert('fluxo: macro = policy_evidence_ready', pl.json?.case?.metadata?.attendance_macro_state === 'policy_evidence_ready', `macro=${pl.json?.case?.metadata?.attendance_macro_state}`);
      noCpfExposed('fluxo policy-lookup', pl.json);

      const st = await step(id);
      assert('fluxo: runtime/step retoma (collecting_slots)', st.json?.case?.status === 'collecting_slots', `status=${st.json?.case?.status}`);
      assert('fluxo: retomada seleciona próximo slot', !!st.json?.step?.selected_slot, `sel=${st.json?.step?.selected_slot}`);

      // coletar slots restantes
      await reply(id, 'É na cozinha.');
      await reply(id, 'Fico totalmente sem energia, o disjuntor cai.');
      const rEnd = await reply(id, 'Sim, é o mesmo endereço da apólice.');
      const ns = String(rEnd.json?.next_step?.question || rEnd.json?.case?.next_step || '');
      assert('fluxo: conclusão reconhece apólice/evidência', /evid[êe]ncia|registrada/i.test(ns) || rEnd.json?.next_step?.status === 'no_missing_slots', mask(ns));
      noCpfExposed('fluxo final', rEnd.json);
    }
  }

  // === Cenário 3: off-topic no gate de CPF (LLM fallback) ===
  console.log('\n[3] Off-topic no gate de CPF');
  {
    const id = await caseAtCpfGate('offtopic');
    if (id) {
      const r = await reply(id, 'O que significa van nos nomes holandeses?');
      const diag = runtimeDiag(r.json);
      assert('offtopic: não avança (continua no CPF)', r.json?.next_step?.selected_slot === 'identity_document', `sel=${r.json?.next_step?.selected_slot}`);
      assert('offtopic: status conversation_recovery', r.json?.next_step?.status === 'conversation_recovery', `st=${r.json?.next_step?.status}`);
      assert('offtopic: diagnostics.llm_fallback registrado', !!diag.llm_fallback, 'ausente');
      if (LLM_FLAG) {
        assert('offtopic(LLM on): used=true (se backend ok)', diag.llm_fallback?.used === true || diag.llm_fallback?.attempted === true, JSON.stringify(diag.llm_fallback));
        const q = String(r.json?.next_step?.question || '');
        if (diag.llm_fallback?.used) {
          assert('offtopic(LLM): resposta menciona van/de/do/origem', /van|de\b|do\b|origem/i.test(q), mask(q));
        }
      } else {
        assert('offtopic(LLM off): used=false', diag.llm_fallback?.used !== true, JSON.stringify(diag.llm_fallback));
      }
      noCpfExposed('offtopic', r.json);
    }
  }

  // === Cenário 4: clarificação ===
  console.log('\n[4] Clarificação no gate de CPF');
  {
    const id = await caseAtCpfGate('clarif');
    if (id) {
      const r = await reply(id, 'Por que você precisa do meu CPF?');
      assert('clarif: mantém identity_document', r.json?.next_step?.selected_slot === 'identity_document', `sel=${r.json?.next_step?.selected_slot}`);
      assert('clarif: não avança p/ policy lookup', r.json?.case?.metadata?.attendance_macro_state !== 'policy_lookup_required' || r.json?.case?.status === 'policy_check', 'avançou indevidamente');
      assert('clarif: gerou resposta', !!r.json?.next_step?.question, 'sem resposta');
      noCpfExposed('clarif', r.json);
    }
  }

  // === Cenário 5: CPF indisponível ===
  console.log('\n[5] CPF indisponível');
  {
    const id = await caseAtCpfGate('cpf-indisp');
    if (id) {
      const r = await reply(id, 'Não estou com o CPF agora, mando depois.');
      assert('cpf-indisp: mantém identity_document', r.json?.next_step?.selected_slot === 'identity_document', `sel=${r.json?.next_step?.selected_slot}`);
      assert('cpf-indisp: kind = unavailable_data', r.json?.intake?.kind === 'unavailable_data', `kind=${r.json?.intake?.kind}`);
      noCpfExposed('cpf-indisp', r.json);
    }
  }

  // === Cenário 6: frustração ===
  console.log('\n[6] Frustração (após pergunta de risco)');
  {
    const id = await createCase('frustra');
    if (id) {
      await reply(id, 'Estou sem luz'); // → pergunta risco
      const r = await reply(id, 'JÁ DISSE. ESTOU SEM LUZ SÓ NA COZINHA. QUERO ELETRICISTA.');
      assert('frustra: tratado como conversation_recovery', r.json?.next_step?.status === 'conversation_recovery', `st=${r.json?.next_step?.status}`);
      const filled = r.json?.corridor_run?.slots?.filled || {};
      assert('frustra: inferiu affected_area=cozinha', String(filled.affected_area || '').toLowerCase().includes('cozinha'), `area=${filled.affected_area}`);
      assert('frustra: inferiu electrical_issue_type', !!filled.electrical_issue_type, 'não inferido');
      noCpfExposed('frustra', r.json);
    }
  }

  // === Cenário 7: high risk ===
  console.log('\n[7] High risk');
  {
    const id = await createCase('risco');
    if (id) {
      await reply(id, 'Estou com um problema elétrico'); // → pergunta risco
      const r = await reply(id, 'Tem cheiro de queimado e saiu uma faísca.');
      assert('risco: status handoff', r.json?.case?.status === 'handoff', `status=${r.json?.case?.status}`);
      assert('risco: priority high', r.json?.case?.priority === 'high', `pri=${r.json?.case?.priority}`);
      assert('risco: risk_level high', r.json?.case?.risk_level === 'high', `risk=${r.json?.case?.risk_level}`);
      assert('risco: handoff_required true', r.json?.case?.handoff_required === true, `hr=${r.json?.case?.handoff_required}`);
      assert('risco: não pediu CPF', r.json?.next_step?.selected_slot !== 'identity_document', `sel=${r.json?.next_step?.selected_slot}`);
      assert('risco: NÃO usou LLM fallback', runtimeDiag(r.json).llm_fallback?.used !== true, 'usou LLM em risco');
      // step depois do handoff → 409
      const st = await step(id);
      assert('risco: step pós-handoff retorna 409', st.status === 409, `status=${st.status}`);
      noCpfExposed('risco', r.json);
    }
  }

  // === Cenário 8: InfoCap connector sem configuração (42I2) ===
  console.log('\n[8] InfoCap connector (read-only) — sem conexão configurada não confirma cobertura');
  {
    const id = await caseAtCpfGate('infocap');
    if (id) {
      await reply(id, FAKE_CPF); // → policy_lookup_required
      const r = await policyLookupInfocap(id);
      const st = r.json?.policy_lookup_result?.status;
      assert('infocap: não quebra a rota', r.status === 200, `status=${r.status}`);
      const SAFE_INFOCAP = ['blocked_not_configured', 'blocked_missing_credentials', 'unsupported', 'not_found', 'provider_error', 'auth_error', 'multiple_matches', 'found'];
      assert('infocap: status conhecido', SAFE_INFOCAP.includes(st), `plr.status=${st}`);
      // CPF fictício → não deve confirmar cobertura sem evidência real
      const det = await getDetail(id);
      if (st !== 'found') {
        assert('infocap: verification_status não vira verified sem found', !String(det.json?.case?.verification_status || '').startsWith('verified'), `vs=${det.json?.case?.verification_status}`);
        assert('infocap: next_step não usa texto obsoleto', !/será implementado no próximo batch/i.test(String(det.json?.case?.next_step || '')), `next=${det.json?.case?.next_step}`);
      }
      noCpfExposed('infocap', r.json);
    }
  }

  // === Resumo ===
  console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
  if (fail > 0) {
    console.log('Falhas:');
    for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`);
    process.exit(1);
  }
  process.exit(0);
}

main().catch((e) => {
  console.error('Erro inesperado na suíte:', e?.message || e);
  process.exit(2);
});
