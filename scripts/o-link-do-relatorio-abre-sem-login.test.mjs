// O link público do relatório (`/r/<token>`) abre SEM login.
//
// 📊 Em 03/10/2026 um GET em produção com token falso em `/r/<token>` caiu em
// `/login`. A rota `app/r/[token]/route.ts` (SPEC-057) foi feita para o CLIENTE
// do corretor — quem não tem conta — e se protege sozinha pelo token (formato
// base64url ≥ 32, busca no backend com X-Internal-Key, 404 "Link indisponível").
// O agente manda o corretor enviar esse link ao segurado
// (`backend/app/agents/tools/report_tool.py`, "válido por 30 dias"). Mas o
// `middleware.ts` não listava `/r/` como público: TODO cliente que abriu o link
// caiu na tela de login da corretora.
//
// Este teste roda a função `middleware` REAL (TypeScript transpilado do disco,
// `next/server` e `iron-session` reais, `@/lib/iron-session` real) com um
// `NextRequest` SEM cookie — não um regex sobre o texto (CLAUDE.md §9.4).
//
// 🔴 Linhas de controle (CLAUDE.md §9.3):
//   · `/dashboard` sem sessão CONTINUA indo para `/login` — prova que o
//     middleware carregado de fato redireciona, e que o verde de `/r/` não vem
//     de um middleware que libera tudo;
//   · o MESMO middleware sem `'/r/'` (reconstruído do fonte, um fator só)
//     redireciona `/r/<token>` para `/login` — prova que o guarda CONSEGUE
//     ficar vermelho.
//
// 🔴 E os headers (red team 04/10/2026, laudo Q1): no Next 15 o header que o
// middleware grava em `NextResponse.next()` VENCE o da rota. Gravando
// `Content-Security-Policy: frame-ancestors 'none';` e `Referrer-Policy:
// strict-origin-when-cross-origin` em `/r/`, o middleware APAGAVA a CSP restrita
// da rota (`default-src 'none'; …`) e o `no-referrer`. O guarda ⑤ exige que o
// middleware NÃO escreva esses dois em `/r/`, que a ROTA real (GET com o backend
// dublado) declare `default-src 'none'` e `frame-ancestors 'none'`, e que a
// mutação para o comportamento antigo fique VERMELHA.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// iron-session exige senha de 32+ caracteres; sem ela a leitura lança e o
// middleware trata como "sem sessão" pelo catch — queremos o caminho real.
process.env.SESSION_SECRET = process.env.SESSION_SECRET
  || 'teste-local-somente-0123456789abcdef0123456789';

let pass = 0, fail = 0;
function assert(nome, cond, extra = '') {
  if (cond) { pass++; console.log(`  ✓ ${nome}`); }
  else { fail++; console.log(`  ✗ ${nome}${extra ? ' — ' + extra : ''}`); }
}

function transpilar(fonte, nome) {
  return ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: nome,
  }).outputText;
}

function executar(js, resolverImport) {
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const libIronSession = executar(
  transpilar(fs.readFileSync(path.join(RAIZ, 'lib/iron-session.ts'), 'utf8'), 'lib/iron-session.ts'),
  (id) => (id === 'iron-session' ? require('iron-session') : undefined));

function resolverDoMiddleware(id) {
  if (id === 'next/server') return require('next/server');
  if (id === 'iron-session') return require('iron-session');
  if (id === '@/lib/iron-session') return libIronSession;
  return undefined;
}

const FONTE = fs.readFileSync(path.join(RAIZ, 'middleware.ts'), 'utf8');
const atual = executar(transpilar(FONTE, 'middleware.ts'), resolverDoMiddleware);

// O middleware de ANTES do conserto: o fonte atual sem a linha do `'/r/'`.
const FONTE_SEM_R = FONTE.replace(/^[ \t]*'\/r\/',.*\r?\n/m, '');
const semR = executar(transpilar(FONTE_SEM_R, 'middleware.SEM_R.ts'), resolverDoMiddleware);

// O middleware de ANTES do conserto dos headers: grava CSP/Referrer-Policy em /r/.
const LINHA_DA_POLITICA = "const rotaDeclaraPropriaPolitica = pathname.startsWith('/r/');";
const FONTE_HEADERS_ANTIGOS = FONTE.replace(LINHA_DA_POLITICA, 'const rotaDeclaraPropriaPolitica = false;');
const headersAntigos = executar(transpilar(FONTE_HEADERS_ANTIGOS, 'middleware.HEADERS_ANTIGOS.ts'), resolverDoMiddleware);

const { NextRequest } = require('next/server');
const BASE = 'http://localhost:3000';
// 43 caracteres base64url — o formato de `secrets.token_urlsafe(32)`.
const TOKEN = 'tOkEnFaLsO_de-teste_0123456789abcdefghijklm';

async function rodar(mw, caminho) {
  const res = await mw.middleware(new NextRequest(BASE + caminho));
  const loc = res.headers.get('location') || '';
  return {
    status: res.status,
    loc,
    paraLogin: res.status >= 300 && res.status < 400 && new URL(loc, BASE).pathname === '/login',
    segue: res.headers.get('x-middleware-next') === '1',
    csp: res.headers.get('content-security-policy'),
    referrer: res.headers.get('referrer-policy'),
    xfo: res.headers.get('x-frame-options'),
  };
}

console.log('== o link público do relatório /r/ abre sem login ==\n');

assert('o token de teste tem 43 caracteres base64url', TOKEN.length === 43 && /^[A-Za-z0-9_-]+$/.test(TOKEN));
assert('🔴 o middleware SEM /r/ foi mesmo reconstruído (um fator só mudou)',
  FONTE_SEM_R !== FONTE && FONTE_SEM_R.length < FONTE.length);

// ① o conserto
{
  const r = await rodar(atual, `/r/${TOKEN}`);
  assert('/r/<token> sem sessão NÃO redireciona para /login', !r.paraLogin, `status ${r.status} location ${r.loc}`);
  assert('/r/<token> sem sessão segue para a rota (x-middleware-next)', r.segue, `status ${r.status}`);
}

// ② linha de controle: o middleware carregado redireciona quem precisa de sessão
{
  const r = await rodar(atual, '/dashboard');
  assert('CONTROLE: /dashboard sem sessão continua indo para /login', r.paraLogin, `status ${r.status} location ${r.loc}`);
}
{
  // o prefixo tem barra: não abre `/relatorios`, `/r` nem nada que só comece com "r"
  const r1 = await rodar(atual, '/relatorios');
  assert('CONTROLE: /relatorios sem sessão continua indo para /login', r1.paraLogin, `status ${r1.status}`);
  const r2 = await rodar(atual, '/r');
  assert('CONTROLE: /r (sem barra) sem sessão continua indo para /login', r2.paraLogin, `status ${r2.status}`);
  const r3 = await rodar(atual, '/register');
  assert('/register continua público (rota exata, não afetada)', !r3.paraLogin && r3.segue, `status ${r3.status}`);
}

// ③ linha de controle: sem o '/r/' o guarda fica VERMELHO
{
  const r = await rodar(semR, `/r/${TOKEN}`);
  assert('CONTROLE: o middleware SEM /r/ manda /r/<token> para /login (o defeito de 03/10)', r.paraLogin, `status ${r.status} location ${r.loc}`);
}

// ④ a pasta não pode abrir outra coisa: sob app/r/ só existem os arquivos CONHECIDOS.
// 🔴 §9.3: era "só [token]/route.ts" até a SPEC-130-A pôr a imagem da prévia da proposta
// (`[token]/previa.png/route.ts`, que se protege pelo token como a página). A lição
// migra: a lista é fechada e escrita à mão — qualquer arquivo novo deixa o guarda vermelho.
const ARQUIVOS_DE_R = ['[token]/previa.png/route.ts', '[token]/route.ts'];
{
  const arquivos = [];
  (function anda(dir) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) anda(p); else arquivos.push(path.relative(path.join(RAIZ, 'app', 'r'), p).replace(/\\/g, '/'));
    }
  })(path.join(RAIZ, 'app', 'r'));
  assert('sob app/r/ só existem os arquivos conhecidos',
    JSON.stringify(arquivos.sort()) === JSON.stringify(ARQUIVOS_DE_R), JSON.stringify(arquivos));
}

// ⑤ os headers: em /r/ vale a política da ROTA, não a do middleware
{
  const r = await rodar(atual, `/r/${TOKEN}`);
  assert('/r/<token>: o middleware NÃO grava Content-Security-Policy (vale a da rota)', r.csp === null, `csp=${r.csp}`);
  assert('/r/<token>: o middleware NÃO grava Referrer-Policy (vale o no-referrer da rota)', r.referrer === null, `referrer=${r.referrer}`);
  assert('/r/<token>: anti-clickjacking do middleware continua (X-Frame-Options DENY)', r.xfo === 'DENY', `xfo=${r.xfo}`);

  const d = await rodar(atual, '/dashboard');
  assert('CONTROLE: /dashboard sem sessão segue indo para /login (o conserto não abriu nada)', d.paraLogin, `status ${d.status}`);
  const login = await rodar(atual, '/login');
  assert("CONTROLE: /login (público) continua com CSP frame-ancestors 'none'", login.csp === "frame-ancestors 'none';", `csp=${login.csp}`);
  assert('CONTROLE: /login continua com Referrer-Policy strict-origin-when-cross-origin', login.referrer === 'strict-origin-when-cross-origin', `referrer=${login.referrer}`);
  const reg = await rodar(atual, '/register');
  assert("CONTROLE: /register (começa com 'r', sem a barra) NÃO perde a CSP do middleware",
    reg.segue && reg.csp === "frame-ancestors 'none';", `csp=${reg.csp}`);
  const e = await rodar(atual, '/embed/x');
  assert('CONTROLE: /embed/ continua com frame-ancestors *', e.csp === 'frame-ancestors *;', `csp=${e.csp}`);

  // mutação: o comportamento antigo (middleware grava CSP/Referrer em /r/) fica VERMELHO
  assert('🔴 a mutação para os headers antigos foi mesmo aplicada (um fator só)',
    FONTE.includes(LINHA_DA_POLITICA) && FONTE_HEADERS_ANTIGOS !== FONTE);
  const m = await rodar(headersAntigos, `/r/${TOKEN}`);
  assert("CONTROLE: o middleware ANTIGO grava frame-ancestors 'none'; em /r/ (o defeito do laudo Q1)",
    m.csp === "frame-ancestors 'none';" && m.referrer === 'strict-origin-when-cross-origin', `csp=${m.csp} referrer=${m.referrer}`);
}

// ⑥ a ROTA real declara a CSP restrita com frame-ancestors (GET real, backend dublado em fetch)
{
  const fonteRota = fs.readFileSync(path.join(RAIZ, 'app/r/[token]/route.ts'), 'utf8');
  const rota = executar(transpilar(fonteRota, 'route.ts'),
    (id) => (id === 'next/server' ? require('next/server') : undefined));
  const fetchOriginal = globalThis.fetch;
  const envOriginal = { u: process.env.NEXT_PUBLIC_API_URL, k: process.env.BACKEND_INTERNAL_API_KEY };
  process.env.NEXT_PUBLIC_API_URL = 'http://backend-falso.invalid';
  process.env.BACKEND_INTERNAL_API_KEY = 'chave-falsa-de-teste';
  let urlPedida = '';
  globalThis.fetch = async (u) => {
    urlPedida = String(u);
    return new Response(JSON.stringify({ ok: true, html: '<!doctype html><p>RELATORIO_OK</p>' }),
      { status: 200, headers: { 'content-type': 'application/json' } });
  };
  try {
    const res = await rota.GET(new NextRequest(`${BASE}/r/${TOKEN}`), { params: Promise.resolve({ token: TOKEN }) });
    const diretivas = (res.headers.get('content-security-policy') || '').split(/;\s*/);
    assert('a rota foi ao backend dublado (o GET real rodou)',
      res.status === 200 && urlPedida.endsWith(`/api/artifacts/shared/${TOKEN}`), `status ${res.status} url ${urlPedida}`);
    assert("a ROTA declara default-src 'none'", diretivas.includes("default-src 'none'"), diretivas.join('; '));
    assert("a ROTA declara frame-ancestors 'none' (anti-clickjacking sem o middleware)",
      diretivas.includes("frame-ancestors 'none'"), diretivas.join('; '));
    assert('a ROTA declara Referrer-Policy no-referrer', res.headers.get('referrer-policy') === 'no-referrer');
  } finally {
    globalThis.fetch = fetchOriginal;
    if (envOriginal.u === undefined) delete process.env.NEXT_PUBLIC_API_URL; else process.env.NEXT_PUBLIC_API_URL = envOriginal.u;
    if (envOriginal.k === undefined) delete process.env.BACKEND_INTERNAL_API_KEY; else process.env.BACKEND_INTERNAL_API_KEY = envOriginal.k;
  }
}

console.log(`\n${pass} ok, ${fail} falha(s)`);
process.exit(fail ? 1 : 0);
