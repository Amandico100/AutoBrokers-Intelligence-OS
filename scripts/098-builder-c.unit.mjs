// ─────────────────────────────────────────────────────────────────────────────
// SPEC-098 · CONSERTO 1 — as asserções do lado Next, uma por conserto
// ─────────────────────────────────────────────────────────────────────────────
//
// Este arquivo é do BUILDER DE CONSERTO, não do desenhista. Ele NÃO substitui
// `scripts/cada-coisa-sabe-de-quem-e.test.mjs` (o guarda da SPEC): guarda os
// CINCO consertos do red team no que eles têm de Next, cada um com o PAR — o
// caso que reprova E o caso que passa. Uma asserção sem par não prova nada:
// uma função que só diz `null` passaria no fail-closed e mataria o produto.
//
// 🔴 Cada asserção EXECUTA a rota (CLAUDE.md §9.4). Nada aqui é regex sobre a
// fonte: o produto é transpilado com o TypeScript do projeto, carregado com um
// `require` falso e rodado sobre dublês de Supabase, sessão e `fetch`.
//
// ⛔ Sem rede, sem banco, sem escrita. Nenhuma mensagem sai: o `fetch` é dublê e
//    REGISTRA o que teria saído — é assim que [C3] e [C4] medem o cabeçalho.
// ⛔ Nenhum nome de pessoa, CPF, telefone, apólice, placa, senha ou token. As
//    corretoras são sentinelas e existem SEMPRE DUAS (CLAUDE.md §7).
//
// Rodar:  node scripts/098-builder-c.unit.mjs
//
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

const CO_ALFA = 'co-alfa-0000-4000-8000-000000000001';
const CO_BETA = 'co-beta-0000-4000-8000-000000000002';
const U_SOCIO = 'u-socio-0000-4000-8000-000000000001';
const AG_ALFA = 'ag-alfa-0000-4000-8000-000000000001';
const AG_BETA = 'ag-beta-0000-4000-8000-000000000002';
const CX_BETA = 'cx-beta-0000-4000-8000-000000000002';
const CHAVE_BOA = 'chave-interna-do-bff-098';

// ─────────────────────────────────────────────────────────────────────────────
// Placar
// ─────────────────────────────────────────────────────────────────────────────
const falhas = [];
function checar(problemas, nome) {
  if (problemas.length === 0) console.log(`  OK  ${nome}`);
  else { falhas.push(nome); console.log(`  X   ${nome}`); for (const p of problemas) console.log(`        ${p}`); }
}
function par(problemas, nome) {
  if (problemas.length > 0) console.log(`  OK  PAR ${nome} — o guarda acusou`);
  else { falhas.push(`PAR ${nome}`); console.log(`  X   PAR ${nome} — NÃO acusou; a asserção irmã não prova nada`); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Ferramentas
// ─────────────────────────────────────────────────────────────────────────────
function existe(rel) { return fs.existsSync(path.join(RAIZ, rel)); }
function fonte(rel) { return fs.readFileSync(path.join(RAIZ, rel), 'utf8'); }
function porQue(rel, erro) {
  if (!existe(rel)) return `MODULO_AUSENTE: \`${rel}\` não existe`;
  return `${erro?.name || 'Erro'}: ${erro?.message || erro}`;
}

function carregarTS(rel, resolverImport) {
  const js = ts.transpileModule(fonte(rel), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import não previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

/** Dublê de Supabase que APLICA os filtros — senão o `.eq('company_id')` do
 *  produto seria decorativo e o guarda leria vazamento como acerto. */
function dubleSupabase(linhasPorTabela, registro) {
  function from(nome) {
    const c = { tabela: nome, op: 'select', predicados: [], payload: null };
    registro.push(c);
    const cadeia = {};
    cadeia.select = () => cadeia;
    cadeia.insert = (p) => { c.op = 'insert'; c.payload = p; return cadeia; };
    cadeia.update = (p) => { c.op = 'update'; c.payload = p; return cadeia; };
    cadeia.delete = () => { c.op = 'delete'; return cadeia; };
    for (const op of ['eq', 'neq', 'in', 'is']) {
      cadeia[op] = (coluna, valor) => { c.predicados.push({ op, coluna, valor }); return cadeia; };
    }
    cadeia.order = () => cadeia; cadeia.limit = () => cadeia;
    const casa = (l, p) => {
      const v = l[p.coluna];
      if (p.op === 'eq') return String(v) === String(p.valor);
      if (p.op === 'neq') return String(v) !== String(p.valor);
      if (p.op === 'in') return (p.valor ?? []).map(String).includes(String(v));
      return true;
    };
    const resolver = () => {
      if (c.op === 'insert') {
        const linha = { id: `${nome.slice(0, 3)}-novo`, ...c.payload };
        (linhasPorTabela[nome] = linhasPorTabela[nome] || []).push(linha);
        return [linha];
      }
      const alvos = (linhasPorTabela[nome] ?? []).filter((l) => c.predicados.every((p) => casa(l, p)));
      if (c.op === 'update') { for (const l of alvos) Object.assign(l, c.payload); }
      return alvos;
    };
    cadeia.maybeSingle = async () => ({ data: resolver()[0] ?? null, error: null });
    cadeia.single = async () => {
      const l = resolver();
      return { data: l[0] ?? null, error: l.length ? null : { message: 'no rows' } };
    };
    cadeia.then = (ok, err) => Promise.resolve({ data: resolver(), error: null }).then(ok, err);
    return cadeia;
  }
  return { from };
}

/** 📊 DUAS corretoras sempre. Beta existe para provar que nada dela atravessa. */
function mundo() {
  return {
    companies: [{ id: CO_ALFA, name: 'Corretora Alfa' }, { id: CO_BETA, name: 'Corretora Beta' }],
    users_v2: [{ id: U_SOCIO, company_id: CO_ALFA, status: 'active' }],
    company_members: [{ user_id: U_SOCIO, company_id: CO_ALFA, status: 'active' }],
    agents: [
      { id: AG_ALFA, company_id: CO_ALFA, is_active: true, allow_direct_chat: true },
      { id: AG_BETA, company_id: CO_BETA, is_active: true, allow_direct_chat: true },
    ],
    agent_mcp_connections: [{ id: CX_BETA, agent_id: AG_BETA }],
    leads: [],
  };
}

class NextResponseFalsa {
  static json(body, init) { return { __json: true, body, status: init?.status ?? 200 }; }
}
const NEXT_SERVER = { NextResponse: NextResponseFalsa, NextRequest: class {} };

async function silenciando(fn) {
  const orig = { log: console.log, error: console.error, warn: console.warn, info: console.info };
  console.log = console.error = console.warn = console.info = () => {};
  try { return await fn(); } finally { Object.assign(console, orig); }
}

function resolvedor({ supabase, sessao, ironSession, extras = {} }) {
  const resolver = (id) => {
    if (id in extras) return extras[id];
    if (id === 'next/server') return NEXT_SERVER;
    if (id === 'next/headers') return { cookies: async () => ({ get: () => undefined, set: () => {} }) };
    if (id === 'iron-session') return { getIronSession: async (_c, o) => ironSession(o) };
    if (id === '@supabase/supabase-js') return { createClient: () => supabase };
    if (id === '@/lib/auxiliaries/server') {
      return { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => supabase };
    }
    if (id === '@/lib/iron-session') {
      return { sessionOptions: { __qual: 'usuario' }, adminSessionOptions: { __qual: 'admin' } };
    }
    if (id.startsWith('@/lib/admin/')) {
      const rel = `lib/admin/${id.slice('@/lib/admin/'.length)}.ts`;
      if (existe(rel)) return carregarTS(rel, resolver);
    }
    if (id.startsWith('@/')) return {};
    return {};
  };
  return resolver;
}

async function executarRota(caminho, {
  metodo = 'GET', url = 'http://t.local/x', corpo = null, cabecalhos = {},
  linhas, sessao = null, ironSession = () => ({}), fetchDublado = null, extras = {}, params = null,
} = {}) {
  const mundoDaVez = linhas || mundo();
  const registro = [];
  const chamadas = [];
  const supabase = dubleSupabase(mundoDaVez, registro);
  const fetchAnterior = globalThis.fetch;
  globalThis.fetch = async (u, init = {}) => {
    chamadas.push({ url: String(u), init, headers: { ...(init.headers || {}) }, body: init.body });
    if (fetchDublado) return fetchDublado(String(u), init);
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  };
  try {
    if (!existe(caminho)) return { erro: porQue(caminho), registro, chamadas, mundo: mundoDaVez };
    const rota = carregarTS(caminho, resolvedor({ supabase, sessao, ironSession, extras }));
    const handler = rota[metodo];
    if (typeof handler !== 'function') return { erro: `\`${caminho}\` não exporta \`${metodo}\``, registro, chamadas, mundo: mundoDaVez };
    const req = {
      method: metodo, url, nextUrl: new URL(url),
      headers: { get: (n) => cabecalhos[n] ?? cabecalhos[String(n).toLowerCase()] ?? null },
      json: async () => (corpo ?? {}),
      cookies: { get: () => undefined },
    };
    const ctx = params ? { params: Promise.resolve(params) } : undefined;
    const r = await silenciando(() => handler(req, ctx));
    return { status: r?.status ?? 200, corpo: r?.body ?? r, registro, chamadas, mundo: mundoDaVez };
  } catch (e) {
    return { erro: porQue(caminho, e), registro, chamadas, mundo: mundoDaVez };
  } finally {
    globalThis.fetch = fetchAnterior;
  }
}

process.env.BACKEND_INTERNAL_API_KEY = CHAVE_BOA;
process.env.NEXT_PUBLIC_API_URL = 'http://backend.local';
process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://supabase.local';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-do-teste';

console.log('SPEC-098 · CONSERTO 1 — as asserções do lado Next\n');

// ══ [C1] B3 · vínculo ativo revogado NUNCA cai na primária ═══════════════════
console.log('[C1] `resolveSessionCompany` — vínculo revogado devolve `null`, não a primária');
async function resolverComSessao(sessaoLocal, mundoLocal) {
  const registro = [];
  const supabase = dubleSupabase(mundoLocal, registro);
  const mod = carregarTS('lib/auxiliaries/server.ts', (id) => {
    if (id === 'next/headers') return { cookies: async () => ({ get: () => undefined }) };
    if (id === 'iron-session') return { getIronSession: async () => sessaoLocal };
    if (id === '@supabase/supabase-js') return { createClient: () => supabase };
    if (id === '@/lib/iron-session') return { sessionOptions: {} };
    return {};
  });
  return silenciando(() => mod.resolveSessionCompany());
}
{
  // 📊 O sócio tem `activeCompanyId = BETA` no cookie (o seletor mostra "Beta"),
  // e o vínculo com a Beta foi REVOGADO. Antes: caía na primária (ALFA) com 200
  // — e `billing/change-plan`, que ESCREVE, agia na corretora errada.
  const m = mundo(); // company_members só tem o vínculo com a ALFA
  const revogado = await resolverComSessao({ userId: U_SOCIO, activeCompanyId: CO_BETA }, m);
  checar(revogado === null ? [] : [
    `com o vínculo da BETA revogado o resolvedor devolveu ${JSON.stringify(revogado)} — `
    + 'tem de ser `null`. Cair na primária devolve dado da corretora ERRADA com 200 '
    + '(`backend/app/core/auth.py:343-348` escreve a mesma regra, e faz 403)',
  ], '[C1] empresa ativa SEM vínculo `active` → `null` (fail-closed, red team B3)');

  // 🔴 O PAR: sem empresa escolhida no seletor, a primária continua valendo.
  // Sem ele, um `return null` no topo passaria em [C1] e mataria o produto.
  const m2 = mundo();
  const semAtiva = await resolverComSessao({ userId: U_SOCIO }, m2);
  checar(semAtiva?.companyId === CO_ALFA ? [] : [
    `sem empresa ativa o resolvedor devolveu ${JSON.stringify(semAtiva)} — tem de ser a primária (ALFA)`,
  ], '[C1b] CONTROLE: sem `activeCompanyId`, vale a empresa primária');
}

// ══ [C2] B2 · o widget público volta a identificar o lead ════════════════════
console.log('\n[C2] `leads/identify` — sem chave, o AGENTE diz a corretora; o corpo não tem voz');
{
  // 📊 O único chamador é `app/embed/[agentId]/page.tsx:363` — o NAVEGADOR do
  // visitante anônimo. Exigir `X-Internal-Key` devolvia 401 e o formulário de
  // lead do widget morria ("Failed to identify lead").
  // O corpo manda o `companyId` da BETA de propósito: ele tem de ser IGNORADO.
  const m = mundo();
  const r = await executarRota('app/api/leads/identify/route.ts', {
    metodo: 'POST',
    corpo: { email: 'visitante@exemplo.invalid', name: 'Visitante', agentId: AG_ALFA, companyId: CO_BETA },
    linhas: m,
  });
  const p = [];
  if (r.erro) p.push(r.erro);
  else {
    if (r.status !== 200) p.push(`sem chave a rota respondeu ${r.status} (corpo: ${JSON.stringify(r.corpo)}) — o widget público tem de conseguir identificar o lead`);
    if (!r.corpo?.leadId) p.push('a resposta não trouxe `leadId`');
    if ('name' in (r.corpo || {}) || 'isNew' in (r.corpo || {})) p.push('a resposta voltou a trazer `name`/`isNew` — o oráculo de PII (E9)');
    const criado = (m.leads || [])[0];
    if (!criado) p.push('nenhum lead foi gravado');
    else if (criado.company_id !== CO_ALFA) p.push(`o lead foi gravado na corretora ${criado.company_id} — o \`companyId\` do CORPO (Beta) decidiu, e ele não pode ter voz`);
  }
  checar(p, '[C2] sem chave, `{email, agentId}` identifica o lead na corretora DO AGENTE (red team B2)');

  // 🔴 O PAR: agente que não existe → 404, e NADA é gravado. Sem isto, uma rota
  // que aceitasse qualquer coisa passaria em [C2].
  const m2 = mundo();
  const r2 = await executarRota('app/api/leads/identify/route.ts', {
    metodo: 'POST',
    corpo: { email: 'visitante@exemplo.invalid', agentId: 'ag-que-nao-existe', companyId: CO_BETA },
    linhas: m2,
  });
  const p2 = [];
  if (r2.status !== 404) p2.push(`agente inexistente respondeu ${r2.status} — tem de ser 404`);
  if ((m2.leads || []).length) p2.push('gravou um lead mesmo sem agente — a corretora veio do corpo');
  checar(p2, '[C2b] PAR: agente inexistente → 404, e o `companyId` do corpo não salva o pedido');
}

// ══ [C3] B2 · `chat/session` tem dois modos, e nenhum deles é 401 no widget ══
console.log('\n[C3] `chat/session` — modo widget (sem chave) e modo painel (com chave)');
{
  const semSessao = await executarRota('app/api/chat/session/route.ts', {
    metodo: 'DELETE', corpo: { sessionId: 'sessao-do-widget', companyId: CO_BETA }, sessao: null,
  });
  const p = [];
  if (semSessao.erro) p.push(semSessao.erro);
  else {
    if (semSessao.status === 401) p.push('o visitante do widget levou 401 — ele não tem sessão de corretor e nunca terá');
    const c = semSessao.chamadas[0];
    if (!c) p.push('não chamou o backend');
    else {
      if (c.headers['X-Internal-Key']) p.push('o modo widget carimbou a chave interna — assim o backend entra em modo `painel` e o modo widget (E5) fica inalcançável');
      const corpo = JSON.parse(c.body || '{}');
      if ('companyId' in corpo) p.push(`o corpo levou \`companyId\` (${corpo.companyId}) — quem diz de quem é a sessão é a LINHA de \`conversations\``);
      if (corpo.sessionId !== 'sessao-do-widget') p.push('o `sessionId` não viajou');
    }
  }
  checar(p, '[C3] sem sessão: repassa SÓ `{sessionId}`, SEM chave — o modo widget do backend fica alcançável');

  // 🔴 O PAR: com sessão de corretor, a chave é carimbada e a corretora é a DA
  // SESSÃO (a do corpo, Beta, continua sem voz).
  const comSessao = await executarRota('app/api/chat/session/route.ts', {
    metodo: 'DELETE', corpo: { sessionId: 'sessao-do-painel', companyId: CO_BETA },
    sessao: { userId: U_SOCIO, companyId: CO_ALFA },
  });
  const p2 = [];
  const c2 = comSessao.chamadas[0];
  if (!c2) p2.push('não chamou o backend');
  else {
    if (c2.headers['X-Internal-Key'] !== CHAVE_BOA) p2.push('o modo painel NÃO carimbou a chave interna');
    const corpo2 = JSON.parse(c2.body || '{}');
    if (corpo2.companyId !== CO_ALFA) p2.push(`o painel mandou \`${corpo2.companyId}\` — tem de ser a corretora da SESSÃO (Alfa), nunca a do corpo (Beta)`);
  }
  checar(p2, '[C3b] PAR: com sessão de corretor, chave carimbada e `companyId` DA SESSÃO');
}

// ══ [C4] B1 · a proxy do MCP fecha a cerca agente ↔ corretora ════════════════
console.log('\n[C4] proxy `/api/mcp/**` — o agente pedido tem de ser DA CORRETORA da sessão');
{
  const CAMINHO = 'app/api/mcp/[...caminho]/route.ts';
  // O corretor logado é legítimo — da ALFA. Ele pede o agente da BETA.
  const alheio = await executarRota(CAMINHO, {
    metodo: 'GET', url: `http://t.local/api/mcp/agent/${AG_BETA}/connections`,
    sessao: { userId: U_SOCIO, companyId: CO_ALFA }, params: { caminho: ['agent', AG_BETA, 'connections'] },
  });
  const p = [];
  if (alheio.erro) p.push(alheio.erro);
  else {
    if (alheio.status !== 403) p.push(`o agente de OUTRA corretora respondeu ${alheio.status} (corpo: ${JSON.stringify(alheio.corpo)}) — tem de ser 403`);
    if (alheio.chamadas.length) p.push('a proxy chegou a chamar o backend COM a chave interna — o pedido alheio não pode receber o crachá da casa');
  }
  checar(p, '[C4] agente de outra corretora → 403, e o backend nem é chamado (red team B1)');

  // 🔴 O PAR: o agente da PRÓPRIA corretora atravessa e a chave é carimbada.
  const proprio = await executarRota(CAMINHO, {
    metodo: 'GET', url: `http://t.local/api/mcp/agent/${AG_ALFA}/connections`,
    sessao: { userId: U_SOCIO, companyId: CO_ALFA }, params: { caminho: ['agent', AG_ALFA, 'connections'] },
  });
  const p2 = [];
  if (proprio.status === 403) p2.push('o agente da PRÓPRIA corretora levou 403 — a cerca fechou a porta de quem podia entrar');
  const c = proprio.chamadas[0];
  if (!c) p2.push('a proxy não chamou o backend com o agente próprio');
  else {
    if (c.headers['X-Internal-Key'] !== CHAVE_BOA) p2.push('a chave interna não foi carimbada');
    if (!new URL(c.url).searchParams.get('company_id')) p2.push('o `company_id` conferido não seguiu na URL — o backend agora o EXIGE nestas rotas');
  }
  checar(p2, '[C4b] PAR: o agente da própria corretora passa, com a chave e o `company_id` conferido');

  // A conexão OAuth não tem `company_id`: quem diz de quem ela é é o agente.
  const conexaoAlheia = await executarRota(CAMINHO, {
    metodo: 'DELETE', url: `http://t.local/api/mcp/connections/${CX_BETA}`,
    cabecalhos: { origin: 'http://t.local', host: 't.local' },
    sessao: { userId: U_SOCIO, companyId: CO_ALFA }, params: { caminho: ['connections', CX_BETA] },
  });
  checar(conexaoAlheia.status === 403 && conexaoAlheia.chamadas.length === 0 ? [] : [
    `o DELETE da conexão da BETA respondeu ${conexaoAlheia.status} com ${conexaoAlheia.chamadas.length} chamada(s) ao backend — `
    + 'era a escrita DESTRUTIVA cross-tenant do B1: a corretora perde a integração e nenhuma tela diz por quê',
  ], '[C4c] `DELETE /connections/<id>` de outra corretora → 403, sem tocar no backend');
}

// ══ [C5] o BFF traduz `erro` → `error` (guarda [3] do desenhista) ════════════
console.log('\n[C5] `brand-identity` — o corpo do backend com `erro` chega à tela com `error`');
{
  const FRASE = 'o Instagram bloqueia a leitura automática — cole a bio ou os posts fixados';
  const extras = {
    '@/lib/admin/admin-auth': {
      requireCompanyMember: async () => ({ ok: true, ctx: { companyId: CO_ALFA, userId: U_SOCIO }, supabase: null }),
      assertSameOrigin: () => null,
    },
  };
  const falha = await executarRota('app/api/dashboard/brand-identity/route.ts', {
    metodo: 'POST', corpo: {}, extras,
    fetchDublado: async () => ({ ok: false, status: 200, json: async () => ({ ok: false, status: 'failed', erro: FRASE, avisos: [] }) }),
  });
  checar(typeof falha.corpo?.error === 'string' && falha.corpo.error.includes('Instagram') ? [] : [
    `a resposta que chega à tela não traz \`error\`: ${JSON.stringify(falha.corpo).slice(0, 200)} — `
    + '📊 §1.1: a tela lê `j?.error`, e sem isso 500, site vazio e "sem fonte" viram a MESMA frase',
  ], '[C5] o corpo com `erro` sai do BFF com `error`, mesma frase humana');

  // 🔴 O PAR: a captura que DEU CERTO não pode ganhar `error`.
  const ok = await executarRota('app/api/dashboard/brand-identity/route.ts', {
    metodo: 'POST', corpo: {}, extras,
    fetchDublado: async () => ({ ok: true, status: 200, json: async () => ({ ok: true, status: 'captured', erro: null, avisos: [] }) }),
  });
  checar(ok.corpo?.error ? [`a captura que deu certo veio com \`error\`: ${JSON.stringify(ok.corpo.error)}`] : [],
    '[C5b] PAR: `erro: null` não vira `error` — o guarda distingue os dois casos');
}

console.log('\n' + '='.repeat(78));
if (falhas.length) {
  console.log(`  ${falhas.length} falha(s):`);
  for (const f of falhas) console.log(`     - ${f}`);
  process.exitCode = 1;
} else {
  console.log('  VERDE — os cinco consertos do red team, no lado Next, com o par de cada um.');
}
console.log('='.repeat(78));
