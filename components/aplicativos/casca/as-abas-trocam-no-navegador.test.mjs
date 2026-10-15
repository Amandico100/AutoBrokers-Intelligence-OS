// SPEC-131-0-B3 · F3 — as abas de um aplicativo trocam NO NAVEGADOR (§4 "Abas instantâneas", mutação 5 da §6).
//
// Roda com: node components/aplicativos/casca/as-abas-trocam-no-navegador.test.mjs
//
// 📊 A CAUSA (M4 da SPEC): `trocar()` fazia `router.push('?aba=…')` numa página `force-dynamic` que NÃO lê
// `searchParams` (`app/dashboard/auxiliares/[slug]/page.tsx`): cada troca de aba pedia ao servidor a página INTEIRA
// (RSC, com as leituras do backend), à toa — 📊 relato do Founder: 3–4 s por troca. No Next ≥ 14.1 (instalado 15.5.12)
// `window.history.pushState/replaceState` são interceptados pelo App Router (`app-router.js`, ACTION_RESTORE, sem
// fetch) e `useSearchParams` passa a devolver a URL nova SEM requisição.
//
// COMO FUNCIONA — o código REAL, executado (CLAUDE.md §9.4): o trecho de cada função que muda a URL (`trocar` da casca,
// `mudar` das listas de Cotações e Renovações, `agir` do maestro) é RECORTADO do arquivo de verdade, transpilado com o
// TypeScript do projeto e CHAMADO com um `router` e um `window.history` espiões. O guarda afirma o que a função FAZ
// (quem foi chamado, com que URL), não o texto dela. Uma varredura textual complementa: nenhuma mudança SÓ de query
// nos quatro arquivos usa `router.push`/`router.replace`.
//
// LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): cada guarda roda também contra a forma DEFEITUOSA (o `router.push` de antes)
// e tem de ficar VERMELHO nela; e a varredura NÃO acusa uma mudança de ROTA (`router.push('/outra/rota')`).

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const ts = require('typescript');

let falhas = 0;
function checar(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else {
    falhas += 1;
    console.log(`  X   ${nome}${detalhe ? `  — ${detalhe}` : ''}`);
  }
}

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');
const ARQ = {
  casca: 'components/aplicativos/casca/AbasDoAplicativo.tsx',
  maestro: 'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx',
  cotacoes: 'components/aplicativos/cotacao/AbaCotacoes.tsx',
  renovacoes: 'components/aplicativos/renovacao/AbaRenovacoes.tsx',
};

/** Recorta do `inicio` até o fechamento do 1º `abre` depois dele (contando aninhamento). */
function recortar(fonte, inicio, abre = '{') {
  const i = fonte.indexOf(inicio);
  if (i < 0) return null;
  const fecha = abre === '{' ? '}' : ')';
  // função: o corpo começa no `{` depois do `) ` que fecha a assinatura (a assinatura pode ter `{ … }` de tipo)
  let j = abre === '{' ? fonte.indexOf(') {', i) + 2 : fonte.indexOf(abre, i + inicio.length - 1);
  let prof = 0;
  for (; j < fonte.length; j += 1) {
    if (fonte[j] === abre) prof += 1;
    else if (fonte[j] === fecha) {
      prof -= 1;
      if (prof === 0) return fonte.slice(i, j + 1);
    }
  }
  return null;
}

const transpilar = (codigo) =>
  ts.transpileModule(codigo, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
    fileName: 'trecho.tsx',
  }).outputText;

/** Espiões: tudo o que a função pedir ao roteador e ao histórico fica anotado, em ordem. */
function espioes() {
  const chamadas = [];
  const router = {
    push: (url) => chamadas.push(['router.push', url]),
    replace: (url) => chamadas.push(['router.replace', url]),
    refresh: () => chamadas.push(['router.refresh']),
    back: () => chamadas.push(['router.back']),
  };
  const window = {
    history: {
      pushState: (d, _t, url) => chamadas.push(['history.pushState', String(url), d]),
      replaceState: (d, _t, url) => chamadas.push(['history.replaceState', String(url), d]),
    },
  };
  return { chamadas, router, window };
}

/** A casca: carrega o módulo inteiro (para `urlDaAba`, se houver) com um `require` falso, e recorta `trocar`. */
function rodarTrocar(fonte, { pathname, busca, abaAtual, id }) {
  const corpo = recortar(fonte, 'function trocar(');
  if (!corpo) return { erro: 'trocar() não encontrada' };
  const mod = { exports: {} };
  const falso = () => new Proxy({}, { get: () => () => null });
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', transpilar(fonte))(falso, mod, mod.exports);
  const { chamadas, router, window } = espioes();
  const buscaObj = new URLSearchParams(busca);
  // eslint-disable-next-line no-new-func
  const fabrica = new Function('router', 'window', 'pathname', 'busca', 'abaAtual', 'urlDaAba',
    `${transpilar(corpo)}\nreturn trocar;`);
  fabrica(router, window, pathname, buscaObj, abaAtual, mod.exports.urlDaAba)(id);
  return { chamadas };
}

/** As listas: recorta `const mudar = useCallback(...)` e chama o `mudar` de verdade. */
function rodarMudar(fonte, { pathname, busca }, chamadasDoTeste) {
  const corpo = recortar(fonte, 'const mudar = useCallback(', '(');
  if (!corpo) return { erro: 'mudar não encontrado' };
  const { chamadas, router, window } = espioes();
  // eslint-disable-next-line no-new-func
  const fabrica = new Function('router', 'window', 'pathname', 'busca',
    `const useCallback = (f) => f;\n${transpilar(corpo)}\nreturn mudar;`);
  const mudar = fabrica(router, window, pathname, new URLSearchParams(busca));
  for (const [novos, modo] of chamadasDoTeste) mudar(novos, modo);
  return { chamadas };
}

/** O maestro: recorta `async function agir(...)` e roda o INSTALAR com um fetch que responde ok. */
async function rodarInstalar(fonte) {
  const corpo = recortar(fonte, 'async function agir(');
  if (!corpo) return { erro: 'agir() não encontrada' };
  const { chamadas, router, window } = espioes();
  const item = { slug: 'renovacao', template_id: 'tpl-1', sem_rotina: false, conectores_pendentes: [] };
  const botao = { tipo: 'acao', rotulo: 'Instalar' };
  const fetch = async () => ({ ok: true, json: async () => ({ ok: true }) });
  // eslint-disable-next-line no-new-func
  const fabrica = new Function('router', 'window', 'item', 'botao', 'fetch', 'setOcupado', 'setErro', 'NOME_HUMANO_DA_CONEXAO', 'console',
    `${transpilar(corpo)}\nreturn agir;`);
  const agir = fabrica(router, window, item, botao, fetch, () => {}, () => {}, {}, { error: () => {} });
  await agir('install');
  return { chamadas };
}

// ─── a varredura: nenhuma mudança SÓ de query por router.push/replace ─────────────────────────────────────────────
const semComentario = (f) => f.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');

/** O 1º argumento de cada `router.push(`/`router.replace(`, resolvido quando é uma variável `const x = …`. */
function chamadasDoRoteador(fonte) {
  const f = semComentario(fonte);
  const achadas = [];
  for (const m of f.matchAll(/router\.(push|replace)\(\s*/g)) {
    let j = m.index + m[0].length;
    let arg = '';
    let prof = 0;
    let crase = false;
    for (; j < f.length; j += 1) {
      const c = f[j];
      if (c === '`') crase = !crase;
      if (!crase && prof === 0 && (c === ',' || c === ')')) break;
      if (c === '(' || c === '{') prof += 1;
      if (c === ')' || c === '}') prof -= 1;
      arg += c;
    }
    arg = arg.trim();
    if (/^[A-Za-z_$][\w$]*$/.test(arg)) {
      const def = new RegExp(`const\\s+${arg}\\s*=\\s*([^;\\n]+)`).exec(f);
      if (def) arg = def[1].trim();
    }
    achadas.push({ metodo: m[1], arg });
  }
  return achadas;
}

/** Mudança SÓ de query = a parte do caminho é a página atual (`${pathname}` ou a rota própria do arquivo) e há `?`. */
function acusacoes(fonte, rotasProprias) {
  return chamadasDoRoteador(fonte)
    .filter(({ arg }) => {
      if (!arg.includes('?')) return false;
      const caminho = arg.replace(/^[`'"]/, '').split('?')[0];
      return caminho === '${pathname}' || /^pathname\s*\+/.test(arg) || rotasProprias.includes(caminho);
    })
    .concat(chamadasDoRoteador(fonte).filter(({ arg }) => /^urlDaAba\(/.test(arg)))
    .map(({ metodo, arg }) => `router.${metodo}(${arg})`);
}
const ROTAS = {
  casca: ['${pathname}'],
  maestro: ['${pathname}', '/dashboard/auxiliares/${item.slug}'],
  cotacoes: ['${pathname}'],
  renovacoes: ['${pathname}'],
};

const FONTES = Object.fromEntries(Object.entries(ARQ).map(([k, rel]) => [k, ler(rel)]));

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] a casca: trocar de aba é history.pushState (sem servidor), preserva os outros parâmetros e apaga `item`');
const CASO = { pathname: '/dashboard/auxiliares/renovacao', busca: 'aba=renovacoes&item=r-1&escopo=todas', abaAtual: 'renovacoes' };
function guardaDoTrocar(fonte) {
  const erros = [];
  const outra = rodarTrocar(fonte, { ...CASO, id: 'inicio' });
  if (outra.erro) return [outra.erro];
  const ch = outra.chamadas;
  if (ch.some(([q]) => q.startsWith('router.'))) erros.push(`chamou o roteador: ${JSON.stringify(ch)}`);
  const ps = ch.filter(([q]) => q === 'history.pushState');
  if (ps.length !== 1) erros.push(`pushState ${ps.length}× (esperado 1): ${JSON.stringify(ch)}`);
  else {
    const u = new URL(ps[0][1], 'http://x');
    if (u.pathname !== CASO.pathname) erros.push(`o caminho mudou: ${ps[0][1]}`);
    if (u.searchParams.get('aba') !== 'inicio') erros.push(`aba errada: ${ps[0][1]}`);
    if (u.searchParams.has('item')) erros.push(`trocar de aba manteve o item: ${ps[0][1]}`);
    if (u.searchParams.get('escopo') !== 'todas') erros.push(`perdeu os outros parâmetros: ${ps[0][1]}`);
  }
  // clicar na MESMA aba mantém o detalhe aberto (a regra de hoje: `item` é da aba que o abriu)
  const mesma = rodarTrocar(fonte, { ...CASO, id: 'renovacoes' });
  const psm = (mesma.chamadas || []).filter(([q]) => q === 'history.pushState');
  if (psm.length !== 1 || !new URL(psm[0][1], 'http://x').searchParams.has('item')) erros.push(`a mesma aba apagou o item: ${JSON.stringify(mesma.chamadas)}`);
  return erros;
}
const eTrocar = guardaDoTrocar(FONTES.casca);
checar(eTrocar.length === 0, 'trocar() → history.pushState(url com aba nova, sem item, com escopo); nenhuma chamada ao roteador', eTrocar.join(' | '));
// CONTROLE (mutação 5 da SPEC): o `router.push` de antes deixa o guarda VERMELHO
const trocarAntigo = FONTES.casca.replace(/function trocar\(/, 'function trocar_novo(') +
  `\nfunction trocar(id: string) {\n  const p = new URLSearchParams(busca?.toString() ?? '');\n  p.set('aba', id);\n  if (id !== abaAtual) p.delete('item');\n  router.push(\`\${pathname}?\${p.toString()}\`, { scroll: false });\n}\n`;
checar(guardaDoTrocar(trocarAntigo).length > 0, 'CONTROLE: o trocar() de ANTES (router.push) deixa o guarda VERMELHO', guardaDoTrocar(trocarAntigo).join(' | '));

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] as listas (Cotações, Renovações): filtros e detalhe (`item`) mudam a URL no navegador');
function guardaDoMudar(fonte) {
  const erros = [];
  const r = rodarMudar(fonte, { pathname: '/dashboard/auxiliares/renovacao', busca: 'aba=renovacoes&escopo=todas' }, [
    [{ item: 'r-9' }, 'push'],
    [{ estado: 'calculada' }, undefined],
    [{ q: null }, 'replace'],
  ]);
  if (r.erro) return [r.erro];
  const ch = r.chamadas;
  if (ch.some(([q]) => q.startsWith('router.'))) erros.push(`chamou o roteador: ${JSON.stringify(ch)}`);
  const esperado = [
    ['history.pushState', '/dashboard/auxiliares/renovacao?aba=renovacoes&escopo=todas&item=r-9'],
    ['history.replaceState', '/dashboard/auxiliares/renovacao?aba=renovacoes&escopo=todas&estado=calculada'],
    ['history.replaceState', '/dashboard/auxiliares/renovacao?aba=renovacoes&escopo=todas'],
  ];
  const obtido = ch.map(([q, u]) => [q, u]);
  if (JSON.stringify(obtido) !== JSON.stringify(esperado)) erros.push(`obtido ${JSON.stringify(obtido)}`);
  return erros;
}
for (const k of ['cotacoes', 'renovacoes']) {
  const e = guardaDoMudar(FONTES[k]);
  checar(e.length === 0, `${k}: mudar(push) → pushState · mudar() → replaceState · a aba e os outros parâmetros ficam`, e.join(' | '));
  const antigo = FONTES[k]
    .replace(/window\.history\.pushState\(null, '', url\)/, 'router.push(url, { scroll: false })')
    .replace(/window\.history\.replaceState\(null, '', url\)/, 'router.replace(url, { scroll: false })');
  checar(guardaDoMudar(antigo).length > 0, `CONTROLE ${k}: o mudar() de ANTES (router.push/replace) deixa o guarda VERMELHO`);
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] o maestro: Instalar leva ao Configurar pelo histórico, e o refresh (o estado mudou no servidor) continua');
async function guardaDoInstalar(fonte) {
  const r = await rodarInstalar(fonte);
  if (r.erro) return [r.erro];
  const obtido = r.chamadas.map(([q, u]) => (u ? [q, u] : [q]));
  const esperado = [['history.pushState', '/dashboard/auxiliares/renovacao?aba=configurar'], ['router.refresh']];
  return JSON.stringify(obtido) === JSON.stringify(esperado) ? [] : [`obtido ${JSON.stringify(obtido)}`];
}
const eInst = await guardaDoInstalar(FONTES.maestro);
checar(eInst.length === 0, 'agir("install") → pushState(?aba=configurar) e DEPOIS router.refresh(); nenhum router.push', eInst.join(' | '));
const maestroAntigo = FONTES.maestro.replace(
  /window\.history\.pushState\(null, '', `\/dashboard\/auxiliares\/\$\{item\.slug\}\?aba=configurar`\)/,
  'router.push(`/dashboard/auxiliares/${item.slug}?aba=configurar`, { scroll: false })');
checar((await guardaDoInstalar(maestroAntigo)).length > 0, 'CONTROLE: o Instalar de ANTES (router.push + refresh = 2 idas ao servidor) deixa o guarda VERMELHO');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[4] varredura: nos quatro arquivos, nenhum router.push/replace que mude SÓ a query');
for (const [k, fonte] of Object.entries(FONTES)) {
  const a = acusacoes(fonte, ROTAS[k]);
  checar(a.length === 0, `${ARQ[k]}: zero mudanças só-de-query pelo roteador`, a.join(' | '));
}
// CONTROLE (vermelho): a forma de antes é acusada — por variável `url` e por literal da rota própria
checar(acusacoes("const url = `${pathname}?${p.toString()}`;\nrouter.push(url, { scroll: false });", ['${pathname}']).length === 1 &&
  acusacoes('router.push(`/dashboard/auxiliares/${item.slug}?aba=configurar`, { scroll: false });', ROTAS.maestro).length === 1 &&
  acusacoes("router.replace(`${pathname}?${p}`);", ['${pathname}']).length === 1 &&
  acusacoes("router.push(urlDaAba(pathname, busca?.toString() ?? '', id, abaAtual), { scroll: false });", ['${pathname}']).length === 1,
  'CONTROLE: router.push(url de ${pathname}?…) · router.push(rota própria ?aba=) · router.replace(${pathname}?…) · router.push(urlDaAba(…)) são ACUSADOS');
// CONTROLE (verde): mudança de ROTA não é acusada — nem sem query, nem com query para OUTRA rota
checar(acusacoes("router.push('/dashboard/auxiliares');\nrouter.push(`/dashboard/auxiliares/${slug}`);\nrouter.push(`/dashboard/cotacao?origem=loja`);\nrouter.back();",
  ROTAS.maestro).length === 0,
  'CONTROLE: router.push de MUDANÇA DE ROTA (/dashboard/auxiliares, /${slug}, outra rota com ?) NÃO é acusado');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[5] o Next instalado intercepta history.pushState (sem isto a troca não re-renderizaria)');
const NEXT_VER = JSON.parse(ler('node_modules/next/package.json')).version;
const APP_ROUTER = ler('node_modules/next/dist/client/components/app-router.js');
const RESTORE = ler('node_modules/next/dist/client/components/router-reducer/reducers/restore-reducer.js');
const [maj, min] = NEXT_VER.split('.').map(Number);
checar(maj > 14 || (maj === 14 && min >= 1), `next ${NEXT_VER} ≥ 14.1`);
checar(/window\.history\.pushState = function pushState\(/.test(APP_ROUTER) && /window\.history\.replaceState = function replaceState\(/.test(APP_ROUTER) &&
  /applyUrlFromHistoryPushReplace\(url\)/.test(APP_ROUTER) && /type: _routerreducertypes\.ACTION_RESTORE/.test(APP_ROUTER),
  'app-router.js troca pushState/replaceState por versões que despacham ACTION_RESTORE (usePathname/useSearchParams)');
checar(!/fetchServerResponse|fetch\(/.test(RESTORE) && /canonicalUrl: href/.test(RESTORE),
  'restore-reducer.js não busca nada no servidor — só troca a URL canônica');

console.log(falhas === 0 ? '\nTODOS OS GUARDAS VERDES' : `\n${falhas} GUARDA(S) VERMELHO(S)`);
process.exit(falhas === 0 ? 0 : 1);
