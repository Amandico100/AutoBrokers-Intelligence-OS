#!/usr/bin/env node
/**
 * SPEC-116 U10 (F4) — NENHUM AGENTE NASCE COM MODELO GRAVADO.
 *
 * O que se afirma é o comportamento do MOTOR REAL (CLAUDE.md §9.4), não o texto
 * dos arquivos:
 *   · `provisionTenant` (lib/admin/provision-tenant.ts) é EXECUTADO para DUAS
 *     corretoras sobre um dublê do Supabase (a única borda). Todo agente que
 *     nasce tem `llm_provider`/`llm_model` NULOS e nenhum `vision_model`; toda
 *     linha de memória nasce sem modelo; nada é compartilhado entre os tenants.
 *   · a rota de SANDBOX (`app/api/admin/sandbox/bootstrap-tenant/route.ts`) é
 *     EXECUTADA com o mesmo dublê: o agente sandbox nasce sem modelo.
 *   · o AUXILIAR instalado (`buildAgentCreatePayload`, o que a rota de install
 *     chama) nasce sem modelo, mesmo com um modelo velho no blueprint.
 *   · as RELEASES (`blueprint-release.ts`) não carregam modelo.
 *   · `papelDoAgente` (TS) = `model_policy.papel_do_agente` (py): a mesma tabela
 *     de casos está em `backend/tests/test_spec116_f4_nascimento_e_catalogo.py`.
 *
 * LINHA DE CONTROLE: o dublê GRAVA o que recebe — um agente inserido com modelo
 * aparece como modelo (provado no início, antes das afirmações).
 *
 * Rodar: node scripts/spec116-f4-nascimento.test.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, existsSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve as resolvePath } from 'node:path';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

// ---------------------------------------------------------------------------
// Carregador de TS com o alias `@/` — o código do produto, transpilado e
// executado de verdade. `mocks` substitui SÓ a borda (Next, Supabase, auth).
// ---------------------------------------------------------------------------
function criarCarregador(mocks = {}) {
  const cache = new Map();
  function localizar(base) {
    for (const c of [base, `${base}.ts`, `${base}.tsx`, join(base, 'index.ts')]) {
      if (existsSync(c) && statSync(c).isFile()) return c;
    }
    return null;
  }
  function carregar(abs) {
    if (cache.has(abs)) return cache.get(abs).exports;
    if (abs.endsWith('.json')) {
      const obj = JSON.parse(readFileSync(abs, 'utf8'));
      cache.set(abs, { exports: obj });
      return obj;
    }
    const js = ts.transpileModule(readFileSync(abs, 'utf8'), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
        esModuleInterop: true, jsx: ts.JsxEmit.React,
      },
    }).outputText;
    const mod = { exports: {} };
    cache.set(abs, mod);
    const req = (id) => {
      if (id in mocks) return mocks[id];
      let base = null;
      if (id.startsWith('@/')) base = join(RAIZ, id.slice(2));
      else if (id.startsWith('.')) base = resolvePath(dirname(abs), id);
      if (base === null) return require(id);
      const achado = localizar(base);
      if (!achado) throw new Error(`não achei ${id} (de ${abs})`);
      return carregar(achado);
    };
    new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
    return mod.exports;
  }
  return (rel) => carregar(join(RAIZ, rel));
}

// ---------------------------------------------------------------------------
// Dublê do Supabase: tabelas em memória, query builder encadeável e "thenable".
// ---------------------------------------------------------------------------
function criarBanco(inicial = {}) {
  const tabelas = {};
  for (const [t, linhas] of Object.entries(inicial)) tabelas[t] = linhas.map((l) => ({ ...l }));
  let seq = 0;
  const novoId = () => `00000000-0000-4000-8000-${String(++seq).padStart(12, '0')}`;
  const tab = (t) => (tabelas[t] ??= []);

  function query(t) {
    const filtros = [];
    let op = 'select'; let dados = null; let unico = null; let head = false; let contar = false;
    const casa = (l) => filtros.every((f) => f(l));
    const q = {
      select(_cols, opts) { if (opts?.head) head = true; if (opts?.count) contar = true; return q; },
      eq(c, v) { filtros.push((l) => l[c] === v); return q; },
      neq(c, v) { filtros.push((l) => l[c] !== v); return q; },
      is(c, v) { filtros.push((l) => (l[c] ?? null) === v); return q; },
      in(c, vs) { filtros.push((l) => vs.includes(l[c])); return q; },
      limit() { return q; }, order() { return q; },
      insert(d) { op = 'insert'; dados = d; return q; },
      update(d) { op = 'update'; dados = d; return q; },
      upsert(d) { op = 'upsert'; dados = d; return q; },
      maybeSingle() { unico = 'maybe'; return q; },
      single() { unico = 'single'; return q; },
      then(ok, err) { return Promise.resolve(executar()).then(ok, err); },
    };
    function executar() {
      let saida;
      if (op === 'insert' || op === 'upsert') {
        const linhas = (Array.isArray(dados) ? dados : [dados]).map((d) => ({ id: novoId(), ...d }));
        tab(t).push(...linhas);
        saida = linhas.map((l) => ({ ...l }));
      } else if (op === 'update') {
        saida = [];
        for (const l of tab(t)) if (casa(l)) { Object.assign(l, dados); saida.push({ ...l }); }
      } else {
        saida = tab(t).filter(casa).map((l) => ({ ...l }));
      }
      if (head) return { data: null, count: saida.length, error: null };
      if (unico === 'maybe') return { data: saida[0] ?? null, error: null, count: contar ? saida.length : null };
      if (unico === 'single') {
        return saida.length ? { data: saida[0], error: null } : { data: null, error: { message: 'no rows', code: 'PGRST116' } };
      }
      return { data: saida, error: null, count: contar ? saida.length : null };
    }
    return q;
  }
  return { from: (t) => query(t), tabelas };
}

// ---------------------------------------------------------------------------
let pass = 0; let fail = 0; const failures = [];
function assert(nome, cond) {
  if (cond) { pass++; console.log(`  ok   ${nome}`); } else { fail++; failures.push(nome); console.log(`  X    ${nome}`); }
}

const CO_ALFA = '11111111-1111-4111-8111-111111111111';
const CO_BETA = '22222222-2222-4222-8222-222222222222';
const empresas = () => ([
  { id: CO_ALFA, company_name: 'Corretora Alfa', company_kind: 'client', status: 'active' },
  { id: CO_BETA, company_name: 'Corretora Beta', company_kind: 'client', status: 'active' },
]);

console.log('== SPEC-116 U10 — nascimento sem modelo gravado ==\n');

// LINHA DE CONTROLE — o dublê não "some" com um modelo gravado.
{
  const b = criarBanco();
  await b.from('agents').insert({ company_id: CO_ALFA, llm_model: 'controle-x' });
  const { data } = await b.from('agents').select('*').eq('company_id', CO_ALFA);
  assert('controle: o dublê grava o modelo que recebe', data[0].llm_model === 'controle-x');
}

// 1. provisionTenant — DUAS corretoras, o motor real
console.log('\n[1] provisionamento de duas corretoras (motor real, Supabase dublado)');
{
  const carregar = criarCarregador();
  const { provisionTenant } = carregar('lib/admin/provision-tenant.ts');
  const banco = criarBanco({
    companies: empresas(),
    auxiliary_templates: [{ id: 'tpl-1', is_active: true }],
  });
  const rA = await provisionTenant(banco, CO_ALFA);
  const rB = await provisionTenant(banco, CO_BETA);
  assert('Alfa provisionada (core + atendimento criados)', rA.ok && rA.core.action === 'created' && rA.attendance.action === 'created');
  assert('Beta provisionada (core + atendimento criados)', rB.ok && rB.core.action === 'created' && rB.attendance.action === 'created');

  const agentes = banco.tabelas.agents ?? [];
  assert('4 agentes (2 por corretora)', agentes.length === 4);
  assert('NENHUM agente nasce com llm_model gravado', agentes.every((a) => (a.llm_model ?? null) === null));
  assert('NENHUM agente nasce com llm_provider gravado', agentes.every((a) => (a.llm_provider ?? null) === null));
  assert('NENHUM agente nasce com vision_model', agentes.every((a) => !('vision_model' in a) || a.vision_model == null));
  const memoria = banco.tabelas.memory_settings ?? [];
  assert('memória nasce para os 4 agentes', memoria.length === 4);
  assert('memória nasce SEM modelo (o DEFAULT da coluna é legado ignorado — D-116-15)',
    memoria.every((m) => !('memory_llm_model' in m)));

  // isolamento: dois tenants, nenhuma linha compartilhada
  const idsA = new Set(agentes.filter((a) => a.company_id === CO_ALFA).map((a) => a.id));
  const idsB = new Set(agentes.filter((a) => a.company_id === CO_BETA).map((a) => a.id));
  assert('cada corretora com os SEUS 2 agentes', idsA.size === 2 && idsB.size === 2);
  assert('nenhum agente em duas corretoras', [...idsA].every((id) => !idsB.has(id)));
  assert('ids devolvidos pertencem à própria corretora',
    idsA.has(rA.core.id) && idsA.has(rA.attendance.id) && idsB.has(rB.core.id) && idsB.has(rB.attendance.id));
  assert('memória de cada agente é da corretora do agente',
    memoria.every((m) => agentes.find((a) => a.id === m.agent_id)?.company_id === m.company_id));
  const promptA = agentes.find((a) => a.id === rA.core.id).agent_system_prompt;
  assert('prompt da Alfa não cita a Beta', promptA.includes('Corretora Alfa') && !promptA.includes('Corretora Beta'));
}

// 2. sandbox — a rota EXECUTADA
console.log('\n[2] sandbox de corretora (rota executada)');
{
  const banco = criarBanco({ companies: empresas() });
  const carregar = criarCarregador({
    'next/server': { NextResponse: { json: (body, init) => ({ body, status: init?.status ?? 200 }) } },
    'next/headers': { cookies: () => ({ get: () => undefined }) },
    '@supabase/supabase-js': { createClient: () => banco },
    '@/lib/admin/admin-auth': {
      requireMasterAdmin: async () => ({ ok: true }),
      assertSameOrigin: () => null,
    },
  });
  const rota = carregar('app/api/admin/sandbox/bootstrap-tenant/route.ts');
  const resp = await rota.POST({ json: async () => ({ companyId: CO_BETA }) });
  const sandbox = (banco.tabelas.agents ?? []).filter((a) => a.company_id === CO_BETA);
  assert('rota respondeu 200 e criou o agente sandbox', resp.status === 200 && sandbox.length === 1);
  assert('sandbox nasce SEM modelo gravado', sandbox.length === 1 && sandbox[0].llm_model === null && sandbox[0].llm_provider === null);
  assert('sandbox não tocou a outra corretora', !(banco.tabelas.agents ?? []).some((a) => a.company_id === CO_ALFA));
}

// 3. auxiliar instalado + releases + blueprint extraído
console.log('\n[3] auxiliar, releases e blueprint');
{
  const carregar = criarCarregador();
  const { buildAgentCreatePayload, extractBlueprintFromAgent } = carregar('lib/admin/agent-blueprints.ts');
  const prompt = 'Voce e o auxiliar de pesquisa da corretora. Pesquise empresas e devolva um resumo claro, com a fonte de cada dado.';
  const p = buildAgentCreatePayload(CO_ALFA, { name: 'Pesquisa', llm_provider: 'openai', llm_model: 'gpt-4o-mini', agent_system_prompt: prompt });
  assert('auxiliar nasce SEM modelo mesmo com modelo velho no blueprint', p.llm_model === null && p.llm_provider === null);
  const bp = extractBlueprintFromAgent({ name: 'X', llm_provider: 'anthropic', llm_model: 'claude-sonnet-5', agent_system_prompt: prompt });
  assert('blueprint extraído de um agente não carrega modelo', !('llm_model' in bp) && !('llm_provider' in bp));

  const R = carregar('lib/admin/blueprint-release.ts');
  const C = carregar('lib/admin/agent-blueprints-canonical.ts');
  assert('blueprints canônicos: default de modelo NULO', C.CANONICAL_BLUEPRINTS.every((b) => b.default_llm_model === null && b.default_llm_provider === null));
  assert('release canônica sem modelo', C.CANONICAL_BLUEPRINTS.every((b) => R.buildArtifactFromCanonical(b).llm_model === null));
  assert('release do Studio ignora o modelo do Source Agent',
    R.buildArtifactFromSourceAgent(C.AUTOBROKERS_CORE_BLUEPRINT, { agent_system_prompt: 'x', llm_provider: 'openai', llm_model: 'gpt-4o-mini' }).llm_model === null);
  assert('release de auxiliar sem modelo (era o fallback do mini)',
    R.buildAuxiliaryArtifact({ name: 'A', slug: 'a', agent_system_prompt: 'x' }).llm_model === null);
  const eff = C.resolveEffectiveConfig({ blueprint: C.EVEN_ATTENDANCE_BLUEPRINT, company_name: 'Corretora Alfa', tenant_overrides: { llm_model: 'modelo-caro' } });
  assert('override de modelo pelo tenant continua recusado', eff.rejected_overrides.includes('llm_model') && eff.llm_model === null);
}

// 4. papelDoAgente = model_policy.papel_do_agente (mesma tabela no teste py)
console.log('\n[4] função do agente → papel da rota');
{
  const { papelDoAgente } = criarCarregador()('lib/admin/agent-health.ts');
  const CASOS = [
    ['core', 'chat_principal'], ['', 'chat_principal'], [null, 'chat_principal'],
    ['attendance', 'atendimento'], ['insured_external', 'atendimento'],
    ['subagent', 'subagente'], ['qualquer_outra', 'subagente'], [' CORE ', 'chat_principal'],
  ];
  for (const [funcao, papel] of CASOS) assert(`${JSON.stringify(funcao)} → ${papel}`, papelDoAgente(funcao) === papel);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
