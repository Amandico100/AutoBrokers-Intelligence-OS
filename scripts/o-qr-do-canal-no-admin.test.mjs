#!/usr/bin/env node
/**
 * SPEC-133-A F4 (D-133A-10) — o QR do Quem Cobra Menos no portal admin.
 *
 * O que se afirma é o COMPORTAMENTO das peças reais, transpiladas com a API do
 * TypeScript e executadas (o padrão de `scripts/agent-health.test.mjs`):
 *
 *   1. a prop `endpoint`: sem ela → a URL das corretoras e a chave antiga da
 *      tentativa; com ela → a do admin e outra chave.
 *   2. a empresa do canal vem do banco PELO TIPO, e é fail-closed (0 → 404, 2 → 409).
 *   3. O FIO: a rota admin REAL (com o `requireMasterAdmin` REAL, a ponte REAL e o
 *      `writeAudit` REAL) até o `fetch` do backend. Dublês só na borda: cookie da
 *      sessão, cliente do banco e a rede.
 *   4. não-regressão: a rota do hub das corretoras continua mandando a empresa da
 *      SESSÃO ao backend depois que a ponte saiu dela.
 *   5. os componentes não guardam mais a URL das corretoras escrita à mão.
 *
 * Rode: node scripts/o-qr-do-canal-no-admin.test.mjs
 */
import { createRequire } from 'node:module';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const ts = require('typescript');

let pass = 0, fail = 0; const failures = [];
function assert(n, c, extra = '') {
  if (c) { pass++; console.log(`  ok   ${n}`); }
  else { fail++; failures.push(n); console.log(`  X    ${n}${extra ? `  (${extra})` : ''}`); }
}

// ---------------------------------------------------------------- o carregador
// Transpila .ts do repositório e resolve `@/…` e caminhos relativos. Um módulo
// em STUBS é substituído pelo dublê (só a borda: sessão, banco, rede).
let STUBS = {};
let CACHE = {};
function resolverArquivo(base, spec) {
  let alvo;
  if (spec.startsWith('@/')) alvo = join(RAIZ, spec.slice(2));
  else if (spec.startsWith('.')) alvo = join(dirname(base), spec);
  else return null;
  for (const ext of ['.ts', '.tsx', '/index.ts', '']) {
    if (existsSync(alvo + ext) && statSync(alvo + ext).isFile()) return alvo + ext;
  }
  return null;
}
function carregar(arquivo) {
  if (CACHE[arquivo]) return CACHE[arquivo].exports;
  const fonte = readFileSync(arquivo, 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const mod = { exports: {} };
  CACHE[arquivo] = mod;
  const req = (spec) => {
    if (spec in STUBS) return STUBS[spec];
    const local = resolverArquivo(arquivo, spec);
    if (local) return carregar(local);
    return require(spec);
  };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, req);
  return mod.exports;
}
const rel = (p) => join(RAIZ, p);

// ---------------------------------------------------------------- 1. a prop
console.log('\n-- 1. a prop `endpoint` --');
CACHE = {}; STUBS = {};
const EP = carregar(rel('components/vault/whatsapp-channel-endpoint.ts'));
assert('sem endpoint → a URL das corretoras', EP.endpointDoCartao() === '/api/dashboard/whatsapp-channel');
assert('endpoint vazio → a URL das corretoras', EP.endpointDoCartao('  ') === '/api/dashboard/whatsapp-channel');
assert('com endpoint → a do admin', EP.endpointDoCartao('/api/admin/canais/whatsapp') === '/api/admin/canais/whatsapp');
assert('sem endpoint → a MESMA chave de tentativa de sempre (sessão em curso não se perde)',
  EP.chaveDaTentativa() === 'autobrokers-whatsapp-observer-attempt');
assert('com endpoint → outra chave (o admin não retoma a tentativa da corretora)',
  EP.chaveDaTentativa('/api/admin/canais/whatsapp') !== EP.chaveDaTentativa());
assert('a query das corretoras sai igual à de antes',
  EP.comQuery(EP.endpointDoCartao(), 'action=status') === '/api/dashboard/whatsapp-channel?action=status');

// ---------------------------------------------------------------- dublês da borda
const CANAL = 'canal-0000-aaaa';
const OUTRA = 'corretora-1111-bbbb';
const EMPRESAS_BASE = [
  { id: OUTRA, company_name: 'Corretora X', company_kind: 'client' },
  { id: CANAL, company_name: 'Canal', company_kind: 'platform_canal' },
];
let estado;
function novoEstado() {
  return { sessao: {}, admins: new Set(['adm-1']), empresas: EMPRESAS_BASE.map((e) => ({ ...e })), filtrosCompanies: [], auditoria: [], fetches: [] };
}
function fakeSupabase() {
  return {
    from(tabela) {
      const filtros = [];
      let lim = null;
      const exec = () => {
        if (tabela === 'admin_users') {
          const id = filtros.find((f) => f[0] === 'id')?.[1];
          return { data: estado.admins.has(id) ? [{ id }] : [], error: null };
        }
        if (tabela === 'companies') {
          estado.filtrosCompanies.push(filtros.slice());
          let linhas = estado.empresas.filter((e) => filtros.every(([c, v]) => e[c] === v));
          if (lim) linhas = linhas.slice(0, lim);
          return { data: linhas.map(({ id, company_name }) => ({ id, company_name })), error: null };
        }
        return { data: [], error: null };
      };
      const b = {
        select() { return b; },
        eq(c, v) { filtros.push([c, v]); return b; },
        order() { return b; },
        limit(n) { lim = n; return b; },
        async maybeSingle() { const r = exec(); return { data: r.data[0] ?? null, error: r.error }; },
        then(ok, ko) { return Promise.resolve(exec()).then(ok, ko); },
        async insert(linha) { if (tabela === 'vault_audit_log') estado.auditoria.push(linha); return { error: null }; },
        update() { return b; },
      };
      return b;
    },
  };
}
function stubsDaBorda() {
  return {
    'next/headers': { cookies: async () => ({}) },
    'iron-session': { getIronSession: async (_c, opts) => (opts?.cookieName === 'admin' ? estado.sessao : {}) },
    '@supabase/supabase-js': { createClient: () => fakeSupabase() },
    '@/lib/iron-session': { adminSessionOptions: { cookieName: 'admin' }, sessionOptions: { cookieName: 'user' } },
    '@/lib/auxiliaries/server': {
      resolveSessionCompany: async () => ({ userId: 'u-1', companyId: OUTRA }),
      getSupabaseAdmin: () => fakeSupabase(),
    },
  };
}
globalThis.fetch = async (url, init = {}) => {
  estado.fetches.push({ url: String(url), body: init.body ? JSON.parse(init.body) : null, headers: init.headers || {} });
  return new Response(JSON.stringify({ ok: true, state: 'connecting' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
};
process.env.BACKEND_INTERNAL_API_KEY = 'chave-de-teste';
process.env.NEXT_PUBLIC_API_URL = 'https://backend.teste';
const { NextRequest } = require('next/server');
const pedidoGET = (q) => new NextRequest(`https://app.teste/api/admin/canais/whatsapp${q}`);
const pedidoPOST = (corpo, origem = 'https://app.teste') => new NextRequest('https://app.teste/api/admin/canais/whatsapp', {
  method: 'POST', body: JSON.stringify(corpo), headers: { 'content-type': 'application/json', origin: origem, host: 'app.teste' },
});
const MASTER = { adminId: 'adm-1', role: 'master_admin' };

// ---------------------------------------------------------------- 2. a empresa do canal
console.log('\n-- 2. a empresa do canal vem do banco pelo TIPO --');
CACHE = {}; STUBS = stubsDaBorda();
const CDP = carregar(rel('lib/admin/canal-da-plataforma.ts'));
assert('0 linhas → 404 canal_nao_cadastrado', CDP.escolherEmpresaDoCanal([]).detail === 'canal_nao_cadastrado');
assert('2 linhas → 409 canal_ambiguo (nunca "a primeira")', CDP.escolherEmpresaDoCanal([{ id: 'a' }, { id: 'b' }]).status === 409);
assert('1 linha → ela', CDP.escolherEmpresaDoCanal([{ id: 'a' }]).companyId === 'a');
estado = novoEstado();
const r2 = await CDP.resolverEmpresaDoCanal(fakeSupabase());
assert('resolver acha o canal entre empresas de outro tipo', r2.ok && r2.companyId === CANAL, JSON.stringify(r2));
assert('o filtro é company_kind = platform_canal (nenhum id no código)',
  JSON.stringify(estado.filtrosCompanies[0]) === JSON.stringify([['company_kind', 'platform_canal']]));

// ---------------------------------------------------------------- 3. O FIO
console.log('\n-- 3. O FIO: rota admin real → guarda real → ponte real → backend --');
CACHE = {}; STUBS = stubsDaBorda();
const ROTA = carregar(rel('app/api/admin/canais/whatsapp/route.ts'));

estado = novoEstado(); estado.sessao = MASTER;
let res = await ROTA.GET(pedidoGET(`?action=qr&company_id=${OUTRA}`));
assert('master + canal → 200', res.status === 200, `status ${res.status}`);
assert('o backend recebe o QR DA EMPRESA DO CANAL, com a query do intruso ignorada',
  estado.fetches.length === 1 && estado.fetches[0].url === `https://backend.teste/api/whatsapp-channel/qr?company_id=${CANAL}&purpose=observer`,
  estado.fetches[0]?.url);
assert('a chave interna vai no cabeçalho', estado.fetches[0]?.headers['X-AutoBrokers-Internal-Key'] === 'chave-de-teste');

estado = novoEstado(); estado.sessao = MASTER;
res = await ROTA.GET(pedidoGET(''));
assert('sem action → status do canal', estado.fetches[0]?.url.includes(`/api/whatsapp-channel/status?company_id=${CANAL}`));

estado = novoEstado(); estado.sessao = MASTER;
res = await ROTA.POST(pedidoPOST({ action: 'pairing', method: 'qr', company_id: OUTRA }));
assert('POST pairing → 200', res.status === 200, `status ${res.status}`);
assert('o pareamento vai para a empresa do CANAL (company_id do corpo ignorado)',
  estado.fetches[0]?.url === 'https://backend.teste/api/whatsapp-channel/pairing' && estado.fetches[0]?.body?.company_id === CANAL
  && estado.fetches[0]?.body?.purpose === 'observer');
assert('a auditoria registra a ação no canal, sem número e sem QR',
  estado.auditoria.length === 1 && estado.auditoria[0].company_id === CANAL && estado.auditoria[0].action === 'pairing'
  && !JSON.stringify(estado.auditoria[0]).match(/\d{10,}/));

estado = novoEstado(); estado.sessao = MASTER;
res = await ROTA.POST(pedidoPOST({ action: 'disconnect' }));
assert('desconectar → o canal', estado.fetches[0]?.url.endsWith('/api/whatsapp-channel/disconnect') && estado.fetches[0]?.body?.company_id === CANAL);

console.log('\n-- 3b. as portas fechadas (ZERO chamada ao backend) --');
const fechadas = [
  ['sem sessão de admin → 401', {}, () => ROTA.GET(pedidoGET('?action=qr')), 401],
  ['admin de CORRETORA → 403', { adminId: 'adm-1', role: 'company_admin', companyId: OUTRA }, () => ROTA.GET(pedidoGET('?action=qr')), 403],
  ['master com companyId na sessão (não é de plataforma) → 403', { adminId: 'adm-1', role: 'master_admin', companyId: OUTRA }, () => ROTA.GET(pedidoGET('?action=qr')), 403],
  ['master REVOGADO (sem linha em admin_users) → 403', { adminId: 'adm-fantasma', role: 'master_admin' }, () => ROTA.GET(pedidoGET('?action=qr')), 403],
  ['POST de outra origem → 403', MASTER, () => ROTA.POST(pedidoPOST({ action: 'pairing' }, 'https://malicioso.teste')), 403],
  ['POST sem sessão → 401', {}, () => ROTA.POST(pedidoPOST({ action: 'pairing' })), 401],
  ['autorização de Auxiliar no canal → 400', MASTER, () => ROTA.POST(pedidoPOST({ action: 'set-auxiliary-authorization', permitir: true })), 400],
  ['ação desconhecida → 400', MASTER, () => ROTA.POST(pedidoPOST({ action: 'apagar-tudo' })), 400],
];
for (const [nome, sessao, chamar, esperado] of fechadas) {
  estado = novoEstado(); estado.sessao = sessao;
  const r = await chamar();
  assert(nome, r.status === esperado && estado.fetches.length === 0, `status ${r.status}, fetches ${estado.fetches.length}`);
}
estado = novoEstado(); estado.sessao = MASTER; estado.empresas = EMPRESAS_BASE.filter((e) => e.company_kind !== 'platform_canal');
res = await ROTA.GET(pedidoGET('?action=qr'));
assert('nenhuma empresa platform_canal → 404 e nada ao backend', res.status === 404 && estado.fetches.length === 0);
estado = novoEstado(); estado.sessao = MASTER; estado.empresas.push({ id: 'canal-2', company_name: 'Outro', company_kind: 'platform_canal' });
res = await ROTA.GET(pedidoGET('?action=qr'));
assert('duas empresas platform_canal → 409 e nada ao backend', res.status === 409 && estado.fetches.length === 0);

// ---------------------------------------------------------------- 4. não-regressão
console.log('\n-- 4. o hub das corretoras depois que a ponte saiu dele --');
CACHE = {}; STUBS = stubsDaBorda();
const HUB = carregar(rel('app/api/dashboard/whatsapp-channel/route.ts'));
estado = novoEstado();
res = await HUB.GET(new NextRequest('https://app.teste/api/dashboard/whatsapp-channel?action=qr'));
assert('o hub continua mandando a empresa da SESSÃO ao backend',
  res.status === 200 && estado.fetches[0]?.url === `https://backend.teste/api/whatsapp-channel/qr?company_id=${OUTRA}&purpose=observer`,
  estado.fetches[0]?.url);

// ---------------------------------------------------------------- 5. os componentes
console.log('\n-- 5. os componentes e a página --');
for (const arq of ['components/vault/WhatsAppChannelCard.tsx', 'components/vault/WhatsAppPairingFlow.tsx']) {
  const src = readFileSync(rel(arq), 'utf8');
  const literais = (src.match(/['`]\/api\/dashboard\/whatsapp-channel/g) || []).length;
  assert(`${arq}: nenhuma URL das corretoras escrita à mão`, literais === 0, `${literais} literal(is)`);
  const fetches = [...src.matchAll(/fetch\(\s*([^,)\n]+)/g)].map((m) => m[1].trim());
  assert(`${arq}: todo fetch sai do endpoint resolvido (${fetches.length})`,
    fetches.length > 0 && fetches.every((f) => /^(ENDPOINT|comQuery\(ENDPOINT)/.test(f)), fetches.join(' | '));
}
const card = readFileSync(rel('components/vault/WhatsAppChannelCard.tsx'), 'utf8');
assert('o cartão repassa o endpoint ao pareamento', /<WhatsAppPairingFlow[\s\S]{0,80}endpoint=\{endpoint\}/.test(card));
const pagina = readFileSync(rel('app/admin/canais/quem-cobra-menos/whatsapp/page.tsx'), 'utf8');
const epPagina = pagina.match(/ENDPOINT_DO_CANAL = '([^']+)'/)?.[1];
assert('a página aponta para a rota admin que existe',
  epPagina === '/api/admin/canais/whatsapp' && existsSync(rel(`app${epPagina}/route.ts`)));
assert('a página diz como ler o QR e avisa dos convidados',
  pagina.includes('Aparelhos conectados') && pagina.includes('só responde a números convidados'));
const layout = readFileSync(rel('app/admin/layout.tsx'), 'utf8');
assert('o menu do admin leva à página', layout.includes("href: '/admin/canais/quem-cobra-menos/whatsapp'")
  && existsSync(rel('app/admin/canais/quem-cobra-menos/whatsapp/page.tsx')));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
