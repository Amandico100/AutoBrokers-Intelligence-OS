// SPEC-123 F4 — O DIÁRIO É DE QUEM DECIDIU. O guarda das rotas do diário de decisões.
//
// Executa as rotas REAIS (`app/api/dashboard/decisoes/route.ts` e
// `app/api/admin/decisoes/route.ts`, transpiladas com o `typescript` do projeto) sobre
// um dublê do Supabase que APLICA os filtros — a borda é o banco, o resto é o produto.
// `assertSameOrigin` e a política de same-origin são os módulos REAIS de `lib/admin/`.
//
// Dois modos:
//   node scripts/o-diario-e-de-quem-decidiu.test.mjs
//        o guarda sozinho, com duas corretoras (ids por argumento/ambiente, ou fictícios).
//   node scripts/o-diario-e-de-quem-decidiu.test.mjs --fio <entrada.json> <saida.json>
//        o ELO do teste do fio (`backend/tests/test_spec123_diario_fio.py`): recebe as
//        linhas que o SERVIÇO Python gravou, roda GET/POST como cada corretora, devolve as
//        linhas depois do POST e o que cada uma viu — o Python segue o fio a partir daí.
//
// 🔴 CLAUDE.md §7: a corretora A vê só as dela; a B não vê as da A; a B não avalia as da A.
// 🔴 §9.3: cada guarda tem a sua linha de CONTROLE (ela prova que o guarda consegue ficar
//    vermelho) — ex.: o dublê SEM filtro mostraria a linha da A para a B.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

const ROTA = 'app/api/dashboard/decisoes/route.ts';
const ROTA_ADMIN = 'app/api/admin/decisoes/route.ts';

const fonte = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');

function carregarTS(rel, resolver) {
  const js = ts.transpileModule(fonte(rel), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolver(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

// ─────────────────────────────────────────────────────────────────────────────
// O dublê do Supabase — filtros APLICADOS, e toda consulta REGISTRADA
// ─────────────────────────────────────────────────────────────────────────────
function dubleSupabase(mundo, registro) {
  function tabela(nome) {
    const c = { tabela: nome, op: 'select', payload: null, pred: [], ordem: [], limite: null, retorno: false };
    registro.push(c);
    const k = {};
    k.select = () => { if (c.op !== 'select') c.retorno = true; return k; };
    k.insert = (p) => { c.op = 'insert'; c.payload = p; return k; };
    k.update = (p) => { c.op = 'update'; c.payload = p; return k; };
    for (const op of ['eq', 'is', 'gte', 'lte', 'lt', 'gt', 'in']) {
      k[op] = (col, val) => { c.pred.push({ op, col, val }); return k; };
    }
    k.order = (col, o) => { c.ordem.push({ col, asc: o?.ascending !== false }); return k; };
    k.limit = (n) => { c.limite = n; return k; };
    const casa = (l, p) => {
      const v = l[p.col];
      switch (p.op) {
        case 'eq': return String(v) === String(p.val);
        case 'is': return p.val === null ? v == null : v === p.val;
        case 'gte': return v != null && v >= p.val;
        case 'lte': return v != null && v <= p.val;
        case 'lt': return v != null && v < p.val;
        case 'gt': return v != null && v > p.val;
        case 'in': return (p.val || []).map(String).includes(String(v));
        default: return true;
      }
    };
    const resolver = () => {
      const linhas = (mundo[nome] = mundo[nome] || []);
      const alvo = linhas.filter((l) => c.pred.every((p) => casa(l, p)));
      if (c.op === 'update') { for (const l of alvo) Object.assign(l, c.payload); return alvo.map((l) => ({ ...l })); }
      if (c.op === 'insert') { const l = { ...c.payload }; linhas.push(l); return [l]; }
      let saida = [...alvo];
      for (const o of [...c.ordem].reverse()) {
        saida.sort((a, b) => (a[o.col] === b[o.col] ? 0 : (a[o.col] < b[o.col] ? -1 : 1) * (o.asc ? 1 : -1)));
      }
      if (c.limite != null) saida = saida.slice(0, c.limite);
      return saida.map((l) => ({ ...l }));
    };
    const corpo = () => ({ data: resolver(), error: null });
    k.maybeSingle = () => { const r = corpo(); return Promise.resolve({ data: r.data[0] ?? null, error: null }); };
    k.then = (ok, err) => Promise.resolve(corpo()).then(ok, err);
    return k;
  }
  return { from: tabela };
}

class NextResponseFalsa {
  static json(body, init) { return { body, status: init?.status ?? 200 }; }
  constructor(body, init) { this.body = body; this.status = init?.status ?? 200; }
}

function resolvedor({ supabase, sessao, master, proxy }) {
  const r = (id) => {
    if (id === 'next/server') return { NextResponse: NextResponseFalsa, NextRequest: class {} };
    if (id === 'next/headers') return { cookies: async () => ({ get: () => undefined, set: () => {} }) };
    if (id === 'iron-session') return { getIronSession: async () => ({}) };
    if (id === '@supabase/supabase-js') return { createClient: () => supabase };
    if (id === '@/lib/iron-session') return { sessionOptions: {}, adminSessionOptions: {} };
    if (id === '@/lib/vault/server') {
      return { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => supabase };
    }
    if (id === '@/lib/diario/placar') return carregarTS('lib/diario/placar.ts', r);   // SPEC-125 S6: o placar REAL
    if (id === '@/lib/logger') return { logSystemAction: async () => {} };
    if (id === '@/lib/admin-proxy') return { authenticatedProxy: proxy || (async () => NextResponseFalsa.json({ proxy: true })) };
    if (id === '@/lib/admin/admin-auth' && master !== undefined) {
      // o módulo REAL, com só `requireMasterAdmin` trocado pela sessão do teste
      const real = carregarTS('lib/admin/admin-auth.ts', r);
      return { ...real, requireMasterAdmin: async () => master };
    }
    if (id.startsWith('@/lib/admin/')) return carregarTS(`lib/admin/${id.slice('@/lib/admin/'.length)}.ts`, r);
    return undefined;
  };
  return r;
}

async function executar(rota, { metodo = 'GET', url = 'http://t.local/api/x', corpo = null, mundo, sessao = null,
  master, proxy, origem = 'http://t.local' } = {}) {
  const registro = [];
  const supabase = dubleSupabase(mundo, registro);
  const mod = carregarTS(rota, resolvedor({ supabase, sessao, master, proxy }));
  const req = {
    method: metodo, url, nextUrl: new URL(url),
    headers: { get: (n) => ({ origin: origem, host: 't.local' })[String(n).toLowerCase()] ?? null },
    json: async () => corpo ?? {},
    text: async () => JSON.stringify(corpo ?? {}),
  };
  const orig = console.error; console.error = () => {};
  try {
    const res = await mod[metodo](req);
    return { status: res.status, body: res.body, registro };
  } finally { console.error = orig; }
}

// ─────────────────────────────────────────────────────────────────────────────
// O placar
// ─────────────────────────────────────────────────────────────────────────────
const falhas = [];
function ok(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else { falhas.push(nome); console.log(`  X   ${nome}${detalhe ? `\n        ${detalhe}` : ''}`); }
}

function linha(company_id, id, extra = {}) {
  return {
    id, company_id, created_at: extra.created_at || '2026-09-30T12:00:00.000Z', origem: 'acionamento',
    seguradora: 'porto', ramo: 'auto', servico: 'guincho', classe: 'deduzir', acao: 'respondeu_ura',
    nota: 88, limiar: 70, modo: 'on', chave_idempotencia: `chave-${id}`,
    explicacao_para_gente: 'A Porto Seguro perguntou "Qual o problema?". O agente respondeu "2".',
    tela_mascarada: 'Qual o problema?\n1 - Pane\n2 - Bateria', valor_mascarado: '2',
    segunda_opiniao: { concordou: true }, resultado: 'pendente', resultado_em: null,
    veredito: null, o_certo_era: null, sugere_regra: false, veredito_por: null, veredito_em: null,
    virou_caso_em: null, caso_chave: null, carta_rascunho_id: null, ...extra,
  };
}

async function guardas(A, B, mundo, idA, idB) {
  const sA = { userId: 'u-a', companyId: A };
  const sB = { userId: 'u-b', companyId: B };

  const semSessao = await executar(ROTA, { mundo, sessao: null });
  ok(semSessao.status === 401, 'sem sessão → 401', `status=${semSessao.status}`);

  const gA = await executar(ROTA, { mundo, sessao: sA });
  const idsA = (gA.body.items || []).map((i) => i.id);
  ok(gA.status === 200 && idsA.includes(idA), 'a corretora A vê a decisão dela', JSON.stringify(gA.body).slice(0, 200));
  ok(!idsA.includes(idB), '🔴 a corretora A NÃO vê a decisão da B', `viu ${idsA}`);
  const gB = await executar(ROTA, { mundo, sessao: sB });
  const idsB = (gB.body.items || []).map((i) => i.id);
  ok(idsB.includes(idB) && !idsB.includes(idA), '🔴 a corretora B vê só a dela', `viu ${idsB}`);
  const filtro = gB.registro.find((c) => c.tabela === 'diario_de_decisoes');
  ok(filtro && filtro.pred.some((p) => p.op === 'eq' && p.col === 'company_id' && p.val === B),
    'a leitura carrega `.eq(company_id)` da SESSÃO');
  // CONTROLE (§9.3): o dublê SEM o filtro mostraria a linha da A para a B — o guarda consegue falhar.
  const semFiltro = (mundo.diario_de_decisoes || []).filter((l) => l.veredito == null).map((l) => l.id);
  ok(semFiltro.includes(idA) && semFiltro.includes(idB), 'CONTROLE: sem filtro, as duas linhas apareceriam juntas');

  // POST — só a dona avalia
  const alheio = await executar(ROTA, { metodo: 'POST', mundo, sessao: sB,
    corpo: { id: idA, veredito: 'errado', o_certo_era: 'era a opção 1' } });
  ok(alheio.status === 404, '🔴 a B NÃO avalia a decisão da A (404, sem oráculo)', `status=${alheio.status}`);
  ok((mundo.diario_de_decisoes.find((l) => l.id === idA) || {}).veredito == null, '… e a linha da A continua sem veredito');
  const cruzado = await executar(ROTA, { metodo: 'POST', mundo, sessao: sA, origem: 'http://mal.local',
    corpo: { id: idA, veredito: 'certo' } });
  ok(cruzado.status === 403, 'POST de outra origem → 403', `status=${cruzado.status}`);
  const semCerto = await executar(ROTA, { metodo: 'POST', mundo, sessao: sA, corpo: { id: idA, veredito: 'errado', o_certo_era: ' x ' } });
  ok(semCerto.status === 400, '"errado" sem o que era o certo → 400', `status=${semCerto.status}`);
  const certo = await executar(ROTA, { metodo: 'POST', mundo, sessao: sA,
    corpo: { id: idA, veredito: 'errado', o_certo_era: 'responder a opção 1, o carro não liga', sugere_regra: true } });
  ok(certo.status === 200, 'a dona marca "errado" com o certo → 200', JSON.stringify(certo.body));
  const l = mundo.diario_de_decisoes.find((x) => x.id === idA) || {};
  ok(l.veredito === 'errado' && l.o_certo_era && l.sugere_regra === true && l.veredito_por === 'u-a' && l.veredito_em,
    'o veredito, o certo, a regra, quem e quando ficaram gravados', JSON.stringify(l).slice(0, 300));
  const deNovo = await executar(ROTA, { metodo: 'POST', mundo, sessao: sA, corpo: { id: idA, veredito: 'certo' } });
  ok(deNovo.status === 409, 'avaliar de novo (outra pessoa ao mesmo tempo) → 409', `status=${deNovo.status}`);
  ok(l.veredito === 'errado', '… e o primeiro veredito fica');
  const upd = certo.registro.find((c) => c.tabela === 'diario_de_decisoes' && c.op === 'update');
  ok(upd && upd.pred.some((p) => p.col === 'company_id' && p.val === A) && upd.pred.some((p) => p.op === 'is' && p.col === 'veredito'),
    'a escrita é atômica e por corretora (`.eq(company_id)` + `.is(veredito, null)`)');

  // Admin — só o master, e ele vê todas
  const naoMaster = await executar(ROTA_ADMIN, { mundo, master: { ok: false, status: 403, error: 'master_required' } });
  ok(naoMaster.status === 403, 'admin: quem não é master → 403', `status=${naoMaster.status}`);
  const master = { ok: true, ctx: { adminId: 'm' }, supabase: dubleSupabase(mundo, []) };
  const gM = await executar(ROTA_ADMIN, { mundo, master, url: 'http://t.local/api/admin/decisoes?veredito=todas' });
  const idsM = (gM.body.items || []).map((i) => i.id);
  ok(idsM.includes(idA) && idsM.includes(idB), 'admin: o master vê as duas corretoras', `viu ${idsM}`);
  let chamou = null;
  const pM = await executar(ROTA_ADMIN, { metodo: 'POST', mundo, master, url: `http://t.local/api/admin/decisoes?id=${idA}`,
    proxy: async (_req, caminho) => { chamou = caminho; return NextResponseFalsa.json({ ok: true }); } });
  ok(pM.status === 200 && chamou === `/api/admin/atlas/diario/${idA}/carta`, 'admin: "virar carta" vai ao backend pelo proxy de plataforma', String(chamou));
  const pNaoMaster = await executar(ROTA_ADMIN, { metodo: 'POST', mundo, master: { ok: false, status: 401, error: 'x' },
    url: `http://t.local/api/admin/decisoes?id=${idA}`, proxy: async () => { chamou = 'NAO_DEVIA'; return NextResponseFalsa.json({}); } });
  ok(pNaoMaster.status === 401 && chamou !== 'NAO_DEVIA', 'admin: sem master, "virar carta" nem chega ao backend');
  return { gA: idsA, gB: idsB };
}

async function main() {
  const args = process.argv.slice(2);
  if (args[0] === '--fio') {
    // O ELO do teste do fio: as linhas vêm do SERVIÇO Python.
    const entrada = JSON.parse(fs.readFileSync(args[1], 'utf8'));
    const mundo = { diario_de_decisoes: entrada.linhas, companies: entrada.companies || [] };
    const vistos = await guardas(entrada.A, entrada.B, mundo, entrada.idA, entrada.idB);
    fs.writeFileSync(args[2], JSON.stringify({ linhas: mundo.diario_de_decisoes, vistos, falhas }, null, 1));
  } else {
    const A = process.env.DIARIO_CORRETORA_A || '00000000-0000-4000-8000-0000000000a1';
    const B = process.env.DIARIO_CORRETORA_B || '00000000-0000-4000-8000-0000000000b2';
    const idA = '11111111-1111-4111-8111-111111111111';
    const idB = '22222222-2222-4222-8222-222222222222';
    const mundo = { diario_de_decisoes: [linha(A, idA), linha(B, idB, { created_at: '2026-09-30T13:00:00.000Z' })], companies: [] };
    console.log('\n[1] o diário é de quem decidiu');
    await guardas(A, B, mundo, idA, idB);
  }
  console.log(falhas.length ? `\n${falhas.length} FALHA(S)` : '\nTODOS OS GUARDAS VERDES');
  process.exit(falhas.length ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
