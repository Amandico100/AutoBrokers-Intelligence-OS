// SPEC-125 S6 — O PLACAR DO DIÁRIO CONTA CERTO, E A PAUSA É SÓ DA CORRETORA DONA.
//
// [1] `lib/diario/placar.ts` (a função REAL, transpilada) sobre um mundo contado À MÃO.
// [2] A ROTA REAL `app/api/dashboard/decisoes/route.ts` sobre um dublê do Supabase que APLICA os
//     filtros: o placar da A não conta as linhas da B; a A vê a fala COMPLETA só das dela.
// [3] "Pausar esta seguradora": só admin (403 para membro), exige confirmação (400), escreve
//     `cerebro_modos.modo='off'` SÓ na corretora dona (a B, com a mesma seguradora, continua `on`),
//     cria a linha `todos` se faltar, e registra quem/quando.
// Linha de CONTROLE (§9.3): o dublê sem o filtro pausaria a B também — o guarda consegue falhar.
//
//   node scripts/o-placar-do-diario.test.mjs

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');
const ROTA = 'app/api/dashboard/decisoes/route.ts';

function carregarTS(rel, resolver) {
  const js = ts.transpileModule(fs.readFileSync(path.join(RAIZ, rel), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)((id) => {
    const r = resolver(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  }, mod, mod.exports);
  return mod.exports;
}

function dubleSupabase(mundo, registro) {
  return {
    from(nome) {
      const c = { tabela: nome, op: 'select', payload: null, pred: [], limite: null };
      registro.push(c);
      const k = {};
      k.select = () => k;
      k.insert = (p) => { c.op = 'insert'; c.payload = p; return k; };
      k.update = (p) => { c.op = 'update'; c.payload = p; return k; };
      for (const op of ['eq', 'is', 'gte', 'lte', 'lt', 'in']) k[op] = (col, val) => { c.pred.push({ op, col, val }); return k; };
      k.order = () => k;
      k.limit = (n) => { c.limite = n; return k; };
      const casa = (l, p) => {
        const v = l[p.col];
        if (p.op === 'eq') return String(v) === String(p.val);
        if (p.op === 'is') return p.val === null ? v == null : v === p.val;
        if (p.op === 'gte') return v != null && v >= p.val;
        if (p.op === 'lte') return v != null && v <= p.val;
        if (p.op === 'lt') return v != null && v < p.val;
        return true;
      };
      const run = () => {
        const linhas = (mundo[nome] = mundo[nome] || []);
        const alvo = linhas.filter((l) => c.pred.every((p) => casa(l, p)));
        if (c.op === 'insert') { linhas.push({ ...c.payload }); return [c.payload]; }
        if (c.op === 'update') { for (const l of alvo) Object.assign(l, c.payload); return alvo; }
        return c.limite != null ? alvo.slice(0, c.limite) : alvo;
      };
      k.maybeSingle = () => Promise.resolve({ data: run()[0] ?? null, error: null });
      k.then = (ok, err) => Promise.resolve({ data: run().map((l) => ({ ...l })), error: null }).then(ok, err);
      return k;
    },
  };
}

class NextResponseFalsa { static json(body, init) { return { body, status: init?.status ?? 200 }; } }

async function executar({ metodo = 'GET', corpo = null, mundo, sessao, membro, registro = [], url = 'http://t.local/api/dashboard/decisoes' }) {
  const supabase = dubleSupabase(mundo, registro);
  const logs = [];
  const r = (id) => {
    if (id === 'next/server') return { NextResponse: NextResponseFalsa, NextRequest: class {} };
    if (id === 'next/headers') return { cookies: async () => ({ get: () => undefined }) };
    if (id === 'iron-session') return { getIronSession: async () => ({}) };
    if (id === '@supabase/supabase-js') return { createClient: () => supabase };
    if (id === '@/lib/iron-session') return { sessionOptions: {}, adminSessionOptions: {} };
    if (id === '@/lib/vault/server') return { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => supabase };
    if (id === '@/lib/logger') return { logSystemAction: async (e) => { logs.push(e); } };
    if (id === '@/lib/diario/placar') return carregarTS('lib/diario/placar.ts', r);
    if (id === '@/lib/admin/admin-auth') {
      const real = carregarTS('lib/admin/admin-auth.ts', r);
      return { ...real, requireCompanyMember: async () => (membro ? { ...membro, supabase } : { ok: false, status: 401, error: 'no_session' }) };
    }
    if (id.startsWith('@/lib/admin/')) return carregarTS(`lib/admin/${id.slice('@/lib/admin/'.length)}.ts`, r);
    return undefined;
  };
  const mod = carregarTS(ROTA, r);
  const req = {
    method: metodo, url, nextUrl: new URL(url),
    headers: { get: (n) => ({ origin: 'http://t.local', host: 't.local' })[String(n).toLowerCase()] ?? null },
    json: async () => corpo ?? {},
  };
  const orig = console.error; console.error = () => {};
  try { const res = await mod[metodo](req); return { ...res, registro, logs }; } finally { console.error = orig; }
}

const falhas = [];
const ok = (cond, nome, det = '') => {
  if (cond) console.log(`  OK  ${nome}`);
  else { falhas.push(nome); console.log(`  X   ${nome}${det ? `\n        ${det}` : ''}`); }
};

const A = process.env.DIARIO_CORRETORA_A || '00000000-0000-4000-8000-0000000000a1';
const B = process.env.DIARIO_CORRETORA_B || '00000000-0000-4000-8000-0000000000b2';
const AGORA = Date.now();
const dias = (n) => new Date(AGORA - n * 86_400_000).toISOString();
let seq = 0;
const L = (company_id, d, extra) => ({
  id: `l-${++seq}`, company_id, created_at: dias(d), seguradora: 'porto', classe: 'deduzir', acao: 'respondeu_ura',
  modo: 'on', resultado: 'pendente', veredito: null, work_run_id: null, conversation_id: null, origem: 'acionamento',
  explicacao_para_gente: 'frase', tela_mascarada: 'tela [placa]', tela_completa: 'tela ABC1D23', ...extra,
});

/** O mundo da A, contado À MÃO (os números esperados estão ao lado de cada linha). */
function mundoContado() {
  seq = 0;
  return {
    diario_de_decisoes: [
      // conversa 1 (A): deduziu + depois chamou pessoa → NÃO resolvida sem atendente
      L(A, 1, { conversation_id: 'c1', origem: 'atendimento', acao: 'respondeu_segurado', veredito: 'certo' }),
      L(A, 1, { conversation_id: 'c1', origem: 'atendimento', classe: 'nunca_sozinho', acao: 'chamou_pessoa' }),
      // conversa 2 (A): respondeu regra, o segurado corrigiu (erro leve) → resolvida sem atendente
      L(A, 2, { conversation_id: 'c2', origem: 'atendimento', classe: 'responder_com_dado', acao: 'respondeu_segurado', resultado: 'segurado_corrigiu', veredito: 'errado' }),
      // acionamento r1 (A): perguntou ao segurado → resolvido sem atendente; seguradora hdi
      L(A, 3, { work_run_id: 'r1', classe: 'perguntar_ao_segurado', acao: 'perguntou_segurado', seguradora: 'hdi' }),
      // acionamento r2 (A): DEDUZIU, agiu, marcado errado → ERRO GRAVE; semana anterior (9 dias)
      L(A, 9, { work_run_id: 'r2', veredito: 'errado' }),
      // acionamento r3 (A): sombra (não agiu) → não entra no % de pergunta; semana anterior
      L(A, 10, { work_run_id: 'r3', modo: 'sombra', acao: 'nao_agiu', veredito: 'certo' }),
      // fora da janela de 30 dias → não conta
      L(A, 40, { work_run_id: 'r4', veredito: 'errado' }),
      // a corretora B: nunca pode entrar no placar da A
      L(B, 1, { work_run_id: 'rb1', classe: 'nunca_sozinho', acao: 'respondeu_ura', veredito: 'errado' }),
      L(B, 1, { work_run_id: 'rb2', acao: 'chamou_pessoa' }),
    ],
    cerebro_modos: [
      { company_id: A, insurer_key: 'porto', ramo: 'todos', modo: 'on', limiar: 70, motivo: 'x', ligado_por: 'm' },
      { company_id: A, insurer_key: 'porto', ramo: 'auto', modo: 'on', limiar: 70, motivo: 'x', ligado_por: 'm' },
      { company_id: A, insurer_key: 'hdi', ramo: 'auto', modo: 'on', limiar: 70, motivo: 'x', ligado_por: 'm' },
      { company_id: B, insurer_key: 'porto', ramo: 'todos', modo: 'on', limiar: 70, motivo: 'x', ligado_por: 'm' },
    ],
  };
}

async function main() {
  console.log('\n[1] o placar conta certo (função pura, contado à mão)');
  const P = carregarTS('lib/diario/placar.ts', () => undefined);
  const m = mundoContado();
  const p = P.calcularPlacar(m.diario_de_decisoes.filter((l) => l.company_id === A), new Date(AGORA), 30);
  // à mão: 6 decisões na janela; atendimentos c1,c2,r1,r2,r3 = 5; sem atendente = c2,r1,r2,r3 = 4 → 80%
  ok(p.decisoes === 6 && p.atendimentos === 5, '6 decisões em 5 atendimentos (a de 40 dias fica fora)', JSON.stringify([p.decisoes, p.atendimentos]));
  ok(p.pct_sem_atendente === 80, 'resolvidos sem atendente = 4 de 5 = 80%', String(p.pct_sem_atendente));
  // agiram (modo on, acao != nao_agiu) = 5; perguntou = 1 → 20%
  ok(p.pct_pergunta_ao_segurado === 20, 'viraram pergunta ao segurado = 1 de 5 = 20%', String(p.pct_pergunta_ao_segurado));
  ok(p.avaliadas.certo === 2 && p.avaliadas.errado === 2 && p.avaliadas.sem === 2, 'avaliadas: 2 certas · 2 erradas · 2 sem', JSON.stringify(p.avaliadas));
  ok(p.por_seguradora.hdi?.total === 1 && p.por_seguradora.porto?.errado === 2, 'por seguradora: hdi 1 · porto com 2 erradas', JSON.stringify(p.por_seguradora));
  ok(p.por_classe.deduzir?.total === 3 && p.por_classe.nunca_sozinho?.total === 1, 'por classe: deduzir 3 · chamou uma pessoa 1', JSON.stringify(p.por_classe));
  ok(p.erros_graves === 1, 'erros graves = 1 (a dedução errada que AGIU; sombra e chamar pessoa não contam)', String(p.erros_graves));
  ok(p.erros_leves === 1, 'erros leves = 1 (o segurado corrigiu)', String(p.erros_leves));
  ok(p.semana.decisoes === 4 && p.semana_anterior.decisoes === 2, 'tendência: 4 esta semana × 2 na anterior', JSON.stringify([p.semana, p.semana_anterior]));
  ok(p.semana.pct_certo === 50 && p.semana_anterior.pct_certo === 50, 'acerto: 1/2 esta semana · 1/2 na anterior', JSON.stringify([p.semana.pct_certo, p.semana_anterior.pct_certo]));
  // CONTROLE: o placar SEM o filtro (A+B) seria outro — o teste da rota abaixo consegue ver a diferença
  const pAB = P.calcularPlacar(m.diario_de_decisoes, new Date(AGORA), 30);
  ok(pAB.erros_graves !== p.erros_graves, 'CONTROLE: com as linhas da B o placar mudaria (o guarda da rota consegue falhar)');

  console.log('\n[2] a rota: o placar e a fala completa são só da dona');
  const sA = { userId: 'u-a', companyId: A };
  const g = await executar({ mundo: mundoContado(), sessao: sA, url: 'http://t.local/api/dashboard/decisoes?veredito=todas' });
  ok(g.status === 200 && g.body.placar?.erros_graves === 1 && g.body.placar?.decisoes === 6, 'o placar da A não conta as linhas da B', JSON.stringify(g.body.placar && [g.body.placar.decisoes, g.body.placar.erros_graves]));
  ok(g.body.modos?.porto === 'ligado' && g.body.modos?.hdi === 'ligado', 'o modo por seguradora vem da corretora', JSON.stringify(g.body.modos));
  const comp = (g.body.items || []).map((i) => i.tela_completa);
  ok(comp.length === 7 && comp.every((t) => t === 'tela ABC1D23') && !(g.body.items || []).some((i) => /^l-(8|9)$/.test(i.id)), 'a A recebe a fala COMPLETA das 7 linhas dela (e nenhuma da B)', JSON.stringify(comp));
  const semSessao = await executar({ mundo: mundoContado(), sessao: null });
  ok(semSessao.status === 401, 'sem sessão → 401');

  console.log('\n[3] pausar esta seguradora — só a dona, só admin, com confirmação e registro');
  const admA = { ok: true, ctx: { userId: 'u-a', companyId: A, role: 'admin_company', isOwner: false } };
  const naoAdmin = await executar({ metodo: 'POST', mundo: mundoContado(), sessao: sA,
    membro: { ok: false, status: 403, error: 'admin_required' }, corpo: { acao: 'pausar_seguradora', seguradora: 'porto', confirmar: true } });
  ok(naoAdmin.status === 403 && /administra/.test(naoAdmin.body.error), 'quem não administra → 403 em português', JSON.stringify(naoAdmin.body));
  const semConfirmar = await executar({ metodo: 'POST', mundo: mundoContado(), sessao: sA, membro: admA,
    corpo: { acao: 'pausar_seguradora', seguradora: 'porto' } });
  ok(semConfirmar.status === 400, 'sem confirmação → 400 (nada muda)');
  const mundo = mundoContado();
  const pausa = await executar({ metodo: 'POST', mundo, sessao: sA, membro: admA,
    corpo: { acao: 'pausar_seguradora', seguradora: 'porto', confirmar: true, motivo: 'muitos erros' } });
  const porto = (c) => mundo.cerebro_modos.filter((l) => l.company_id === c && l.insurer_key === 'porto');
  ok(pausa.status === 200, 'a admin da A pausa a Porto → 200', JSON.stringify(pausa.body));
  ok(porto(A).length === 2 && porto(A).every((l) => l.modo === 'off' && l.ligado_por === 'corretora:u-a' && /muitos erros/.test(l.motivo)),
    'as DUAS linhas da Porto da A (todos + auto) ficaram off, com quem e por quê', JSON.stringify(porto(A)));
  ok(porto(B).every((l) => l.modo === 'on'), '🔴 a Porto da B CONTINUA ligada', JSON.stringify(porto(B)));
  ok(mundo.cerebro_modos.filter((l) => l.company_id === A && l.insurer_key === 'hdi').every((l) => l.modo === 'on'), 'a HDI da A não mudou');
  ok(pausa.logs.length === 1 && pausa.logs[0].companyId === A && pausa.logs[0].details?.acao === 'pausar_seguradora', 'a pausa ficou registrada (system_logs)');
  const mundo2 = mundoContado();
  await executar({ metodo: 'POST', mundo: mundo2, sessao: sA, membro: admA, corpo: { acao: 'pausar_seguradora', seguradora: 'hdi', confirmar: true } });
  const hdi = mundo2.cerebro_modos.filter((l) => l.company_id === A && l.insurer_key === 'hdi');
  ok(hdi.length === 2 && hdi.every((l) => l.modo === 'off') && hdi.some((l) => l.ramo === 'todos'), 'sem linha `todos`, a pausa a CRIA (off)', JSON.stringify(hdi));
  const ups = pausa.registro.filter((c) => c.tabela === 'cerebro_modos' && c.op !== 'select');
  ok(ups.length > 0 && ups.every((c) => c.op === 'insert' ? c.payload.company_id === A : c.pred.some((p) => p.col === 'company_id' && p.val === A)),
    'toda escrita em cerebro_modos é da corretora da SESSÃO');
  // CONTROLE (§9.3): sem o filtro, o mesmo update teria pegado a B
  const semFiltro = mundoContado().cerebro_modos.filter((l) => l.insurer_key === 'porto').map((l) => l.company_id);
  ok(semFiltro.includes(B), 'CONTROLE: sem o filtro, a Porto da B estaria no alvo');

  console.log(falhas.length ? `\n${falhas.length} FALHA(S)` : '\nTODOS OS GUARDAS VERDES');
  process.exit(falhas.length ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
