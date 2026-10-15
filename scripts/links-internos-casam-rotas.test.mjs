// modelo: claude-opus-5-5
//
// SPEC-139 L5 (EXTRA-001.9) — todo link interno casa com uma rota que EXISTE.
//
// O `rotas-montam` prova que a tabela de rotas MONTA. Ele não sabe se alguém
// aponta para um endereço que não está nela: um `href` para uma pasta que mudou
// de lugar compila, passa no `tsc`, passa no `next build` — e o corretor clica
// num 404. Este guarda lê os links literais do código e casa cada um com a
// tabela de rotas lida do disco, pela MESMA regra pasta → URL do App Router.
//
// O que ele lê (em app/, components/, lib/ — fora `*.test.*`):
//   href="/x" · href={'/x'} · href={`/x/${y}`} · href: '/x'           (JSX e objetos de menu)
//   router.push('/x') · router.replace('/x')
//   redirect('/x') · permanentRedirect('/x')
//
// AS EXCEÇÕES — o que ele NÃO cobra, e por quê:
//   externos   http:, https:, mailto:, tel:, //host   não são rotas deste app
//   âncoras    "#secao"                               ficam na mesma página
//   relativos  "x/y", "./x", "../x"                   dependem de onde a página está; o código não os usa para navegar
//   dinâmicos  `${base}/x`                            o começo vem de uma variável: não há texto para casar.
//              Quando o começo é texto (`/dashboard/auxiliares/${slug}`), o guarda casa o
//              texto e trata cada `${…}` como "qualquer segmento" — cobra o que dá para cobrar.
//   arquivos   "/widget.js"                          servidos de public/, conferidos no disco
//   query/hash "/x?aba=y#z"                          só o caminho é casado
//
// E a segunda pergunta (SPEC-139 §6, mutação 5): os endereços ANTIGOS da
// EXTRA-001.9 continuam respondendo — cada um é uma `page.tsx` com `redirect()`
// (307) para o endereço novo, e o novo existe. Sem isso, o favorito do corretor
// vira 404 no dia do deploy. ⛔ Nunca pasta dinâmica nova na mesma posição
// (CLAUDE.md §9.1): o guarda também confere que nenhum `[param]` mora como
// irmão das pastas que a 001.9 tocou.
//
// Rodar:  node --test scripts/links-internos-casam-rotas.test.mjs

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const APP = path.join(RAIZ, 'app');
const PUBLIC = path.join(RAIZ, 'public');
const PASTAS_LIDAS = ['app', 'components', 'lib'];
const EXTENSOES = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs']);
const ARQUIVOS_DE_ROTA = ['page.tsx', 'page.ts', 'page.jsx', 'page.js', 'route.ts', 'route.tsx', 'route.js'];

// ─────────────────────────────────────────────────────────────────────────────
// A tabela de rotas — a mesma regra pasta → URL do `scripts/rotas-montam.test.mjs`
// ─────────────────────────────────────────────────────────────────────────────

/** @returns {string[][]} cada rota como lista de segmentos ([] = "/") */
export function rotasDoDisco(app = APP) {
  const rotas = [];
  const temArquivoDeRota = (dir) => {
    const arquivos = fs.readdirSync(dir);
    return ARQUIVOS_DE_ROTA.some((a) => arquivos.includes(a));
  };
  if (temArquivoDeRota(app)) rotas.push([]);
  (function anda(dir, segs) {
    for (const entrada of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entrada.isDirectory()) continue;
      const nome = entrada.name;
      const sub = path.join(dir, nome);
      if (nome.startsWith('_')) continue;                                       // pasta privada
      if ((nome.startsWith('(') && nome.endsWith(')')) || nome.startsWith('@')) { // grupo / slot
        if (temArquivoDeRota(sub)) rotas.push(segs);
        anda(sub, segs);
        continue;
      }
      const novos = [...segs, nome];
      if (temArquivoDeRota(sub)) rotas.push(novos);
      anda(sub, novos);
    }
  })(app, []);
  return rotas;
}

// ─────────────────────────────────────────────────────────────────────────────
// O casamento link × rota
// ─────────────────────────────────────────────────────────────────────────────

const CORINGA = '\u0000'; // o lugar de um `${…}` dentro do link

const ehDinamico = (s) => s.startsWith('[') && s.endsWith(']');
const ehCatchAll = (s) => s.startsWith('[...') || s.startsWith('[[...');
const ehCatchAllOpcional = (s) => s.startsWith('[[...');

function segmentoCasa(segLink, segRota) {
  if (ehDinamico(segRota)) return true;
  if (!segLink.includes(CORINGA)) return segLink === segRota;
  const re = new RegExp('^' + segLink.split(CORINGA).map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*') + '$');
  return re.test(segRota);
}

/** casa os segmentos do link com os de UMA rota */
function casaRota(link, rota) {
  const anda = (i, j) => {
    if (j < rota.length && ehCatchAll(rota[j])) {
      if (ehCatchAllOpcional(rota[j]) && j === rota.length - 1 && i === link.length) return true;
      // [...x] consome 1+ segmentos do link
      for (let k = i + 1; k <= link.length; k++) if (anda(k, j + 1)) return true;
      return false;
    }
    if (i === link.length) return j === rota.length;
    // `${…}` como segmento inteiro, no FIM do link: pode ser um caminho de 0+ segmentos
    if (link[i] === CORINGA && i === link.length - 1) return true;
    if (j === rota.length) return false;
    return segmentoCasa(link[i], rota[j]) && anda(i + 1, j + 1);
  };
  return anda(0, 0);
}

/**
 * Classifica um link. `texto` é o conteúdo da string (template: com `${…}` cru).
 * @returns {{tipo:'interno', caminho:string, segs:string[]} | {tipo:'excecao', porque:string}}
 */
export function classificar(texto, ehTemplate) {
  let t = texto.trim();
  if (/^(https?:|mailto:|tel:|sms:|whatsapp:|data:|blob:|javascript:)/i.test(t) || t.startsWith('//')) {
    return { tipo: 'excecao', porque: 'externo' };
  }
  if (t.startsWith('#')) return { tipo: 'excecao', porque: 'ancora' };
  if (ehTemplate) t = t.replace(/\$\{[^}]*\}/g, CORINGA);
  if (t.startsWith(CORINGA)) return { tipo: 'excecao', porque: 'dinamico (o comeco vem de variavel)' };
  if (!t.startsWith('/')) return { tipo: 'excecao', porque: 'relativo' };
  const corte = t.search(/[?#]/);
  const caminho = corte >= 0 ? t.slice(0, corte) : t;
  const segs = caminho.split('/').filter(Boolean);
  return { tipo: 'interno', caminho: caminho || '/', segs };
}

export function linkExiste(segs, rotas, publicDir = PUBLIC) {
  if (rotas.some((r) => casaRota(segs, r))) return true;
  // arquivo estático de public/ (só quando o link é texto puro)
  if (segs.length && !segs.some((s) => s.includes(CORINGA))) {
    const arq = path.join(publicDir, ...segs);
    if (fs.existsSync(arq) && fs.statSync(arq).isFile()) return true;
  }
  return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// A leitura dos links no código
// ─────────────────────────────────────────────────────────────────────────────

const PADROES = [
  // href="/x"  href='/x'
  { nome: 'href', re: /\bhref\s*=\s*(["'])((?:(?!\1).)*)\1/g, grupo: 2, tpl: false },
  // href={'/x'}  href={"/x"}
  { nome: 'href', re: /\bhref\s*=\s*\{\s*(["'])((?:(?!\1).)*)\1\s*\}/g, grupo: 2, tpl: false },
  // href={`/x/${y}`}
  { nome: 'href', re: /\bhref\s*=\s*\{\s*`([^`]*)`\s*\}/g, grupo: 1, tpl: true },
  // href: '/x'  (objetos de menu, catálogos)
  { nome: 'href', re: /\bhref\s*:\s*(["'])((?:(?!\1).)*)\1/g, grupo: 2, tpl: false },
  { nome: 'href', re: /\bhref\s*:\s*`([^`]*)`/g, grupo: 1, tpl: true },
  // router.push / router.replace
  { nome: 'router', re: /\brouter\.(?:push|replace)\(\s*(["'])((?:(?!\1).)*)\1/g, grupo: 2, tpl: false },
  { nome: 'router', re: /\brouter\.(?:push|replace)\(\s*`([^`]*)`/g, grupo: 1, tpl: true },
  // redirect / permanentRedirect
  { nome: 'redirect', re: /\b(?:permanentRedirect|redirect)\(\s*(["'])((?:(?!\1).)*)\1/g, grupo: 2, tpl: false },
  { nome: 'redirect', re: /\b(?:permanentRedirect|redirect)\(\s*`([^`]*)`/g, grupo: 1, tpl: true },
];

function arquivosDoCodigo() {
  const lista = [];
  for (const pasta of PASTAS_LIDAS) {
    const raiz = path.join(RAIZ, pasta);
    if (!fs.existsSync(raiz)) continue;
    (function anda(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
        const p = path.join(dir, e.name);
        if (e.isDirectory()) { anda(p); continue; }
        if (!EXTENSOES.has(path.extname(e.name))) continue;
        if (/\.test\.[a-z]+$/.test(e.name)) continue; // teste mente de propósito (mutação, controle)
        lista.push(p);
      }
    })(raiz);
  }
  return lista;
}

/** @returns {{arquivo:string, linha:number, tipo:string, texto:string, tpl:boolean}[]} */
export function linksDoTexto(fonte, arquivo = '<texto>') {
  const achados = [];
  const visto = new Set();
  for (const p of PADROES) {
    p.re.lastIndex = 0;
    let m;
    while ((m = p.re.exec(fonte))) {
      const texto = m[p.grupo];
      const linha = fonte.slice(0, m.index).split('\n').length;
      const chave = `${linha}|${texto}`;
      if (visto.has(chave)) continue; // href={'/x'} casa em dois padrões
      visto.add(chave);
      achados.push({ arquivo, linha, tipo: p.nome, texto, tpl: p.tpl });
    }
  }
  return achados;
}

function todosOsLinks() {
  const todos = [];
  for (const arq of arquivosDoCodigo()) {
    const rel = path.relative(RAIZ, arq).split(path.sep).join('/');
    todos.push(...linksDoTexto(fs.readFileSync(arq, 'utf8'), rel));
  }
  return todos;
}

/** @returns {{quebrados: object[], excecoes: Record<string, number>, conferidos: number}} */
export function auditar(links, rotas) {
  const quebrados = [];
  const excecoes = {};
  let conferidos = 0;
  for (const l of links) {
    const c = classificar(l.texto, l.tpl);
    if (c.tipo === 'excecao') { excecoes[c.porque] = (excecoes[c.porque] ?? 0) + 1; continue; }
    conferidos++;
    if (!linkExiste(c.segs, rotas)) quebrados.push({ ...l, caminho: c.caminho });
  }
  return { quebrados, excecoes, conferidos };
}

// ─────────────────────────────────────────────────────────────────────────────
// Os endereços da EXTRA-001.9 (SPEC-139 §4.5) — antigo → novo
// ─────────────────────────────────────────────────────────────────────────────

const P = '/dashboard/personalizacao';
export const MUDANCAS_DA_001_9 = [
  { antigo: `${P}/agentes/even`, novo: `${P}/corretora/agente-de-atendimento` },
  { antigo: `${P}/equipe`,       novo: `${P}/corretora/equipe` },
  { antigo: `${P}/conhecimento`, novo: `${P}/corretora/conhecimento` },
  { antigo: `${P}/custos`,       novo: `${P}/corretora/custos` },
];

const pastaDe = (url) => path.join(APP, ...url.split('/').filter(Boolean));

// ─────────────────────────────────────────────────────────────────────────────
// Os testes
// ─────────────────────────────────────────────────────────────────────────────

const ROTAS = rotasDoDisco();

test('a tabela de rotas foi lida do disco (raiz, dinâmicas e grupos)', () => {
  assert.ok(ROTAS.length > 100, `só ${ROTAS.length} rotas — a leitura do disco quebrou`);
  assert.ok(ROTAS.some((r) => r.join('/') === 'dashboard/auxiliares/[slug]'), 'a rota dinâmica [slug] entra na tabela');
});

test('CONTROLE: o casamento consegue ficar VERMELHO (um link inventado não casa)', () => {
  // §9.3 — um guarda que não tem como falhar não guarda nada. As duas linhas abaixo
  // provam que "existe" e "não existe" dão respostas DIFERENTES na mesma régua.
  const bom = linksDoTexto(`<Link href="/dashboard/personalizacao/corretora">x</Link>`);
  const ruim = linksDoTexto(`<Link href="/dashboard/personalizacao/nao-existe-139">x</Link>`);
  assert.equal(auditar(bom, ROTAS).quebrados.length, 0, 'o link para rota que existe passa');
  assert.equal(auditar(ruim, ROTAS).quebrados.length, 1, 'o link para rota inexistente fica VERMELHO');
  // dinâmicos: o texto conta, a variável vira "qualquer segmento"
  const dinOk = linksDoTexto('router.push(`/dashboard/auxiliares/${slug}?aba=inicio`)');
  const dinRuim = linksDoTexto('router.push(`/dashboard/nao-existe-139/${slug}`)');
  assert.equal(auditar(dinOk, ROTAS).quebrados.length, 0, 'template que cai em [slug] passa');
  assert.equal(auditar(dinRuim, ROTAS).quebrados.length, 1, 'template com texto inexistente fica VERMELHO');
  // as exceções são exceções, não silêncio
  const exc = auditar(linksDoTexto(`href="https://x.com" href="#topo" href={\`\${base}/x\`} redirect('/widget.js')`), ROTAS);
  assert.equal(exc.quebrados.length, 0);
  assert.deepEqual(exc.excecoes, { externo: 1, ancora: 1, 'dinamico (o comeco vem de variavel)': 1 });
});

// Os quebrados que o guarda ACHOU no dia em que nasceu (15/10/2026), em arquivos fora
// da fatia L5 — a fatia não conserta arquivo alheio, e um guarda vermelho para sempre
// ensina a ignorá-lo. Cada linha é uma PENDÊNCIA com dono, não uma licença: o guarda
// fica vermelho se a lista mentir (o link foi consertado e a linha continua aqui).
// Chave: `arquivo caminho` (sem número de linha — a linha anda quando o arquivo muda).
export const QUEBRADOS_CONHECIDOS = new Map([
  ['app/api/admin/control-plane/me/route.ts /admin/connectors',
    'menu do Admin (SPEC-061 §10): a tela de conexões mora em /admin/integrations — pendência para a costura/gerente'],
  ['app/api/admin/control-plane/me/route.ts /admin/finops',
    'menu do Admin (SPEC-061 §10): o financeiro mora em /admin/financeiro — pendência para a costura/gerente'],
]);

test('todo link interno literal em app/, components/ e lib/ casa com uma rota que existe', () => {
  const links = todosOsLinks();
  const { quebrados, excecoes, conferidos } = auditar(links, ROTAS);
  console.log(`  links lidos: ${links.length} · conferidos: ${conferidos} · exceções: ${JSON.stringify(excecoes)}`);
  for (const q of quebrados) {
    const conhecido = QUEBRADOS_CONHECIDOS.get(`${q.arquivo} ${q.caminho}`);
    console.log(`  ${conhecido ? 'CONHECIDO' : 'QUEBRADO '}  ${q.arquivo}:${q.linha}  ${q.tipo}  ${q.caminho}${conhecido ? `  — ${conhecido}` : ''}`);
  }
  assert.ok(conferidos > 200, `só ${conferidos} links conferidos — a leitura do código quebrou`);
  const novos = quebrados.filter((q) => !QUEBRADOS_CONHECIDOS.has(`${q.arquivo} ${q.caminho}`));
  assert.deepEqual(novos.map((q) => `${q.arquivo}:${q.linha} ${q.caminho}`), [],
    'link interno sem rota: o corretor clica e cai num 404');
  const achados = new Set(quebrados.map((q) => `${q.arquivo} ${q.caminho}`));
  const vencidos = [...QUEBRADOS_CONHECIDOS.keys()].filter((k) => !achados.has(k));
  assert.deepEqual(vencidos, [], 'a lista de conhecidos mente: estes já foram consertados — tire-os da lista (§9.3)');
});

test('EXTRA-001.9: cada endereço antigo é uma page.tsx com redirect() para o novo, e o novo existe', () => {
  for (const { antigo, novo } of MUDANCAS_DA_001_9) {
    const paginaAntiga = path.join(pastaDe(antigo), 'page.tsx');
    assert.ok(fs.existsSync(paginaAntiga), `${antigo} sem page.tsx — o favorito do corretor vira 404`);
    const fonte = fs.readFileSync(paginaAntiga, 'utf8');
    assert.ok(fonte.includes(`redirect('${novo}')`), `${antigo} não redireciona para ${novo}`);
    assert.ok(fs.existsSync(path.join(pastaDe(novo), 'page.tsx')), `${novo} não existe`);
    assert.ok(linkExiste(novo.split('/').filter(Boolean), ROTAS), `${novo} não está na tabela de rotas`);
  }
});

test('EXTRA-001.9: o endereço antigo só redireciona — o conteúdo MUDOU de casa, não ficou duplicado', () => {
  for (const { antigo } of MUDANCAS_DA_001_9) {
    const pasta = pastaDe(antigo);
    const sobras = fs.readdirSync(pasta, { withFileTypes: true })
      .filter((e) => e.isFile() && e.name !== 'page.tsx')
      .map((e) => e.name);
    assert.deepEqual(sobras, [], `${antigo} ainda guarda ${sobras.join(', ')} — o conteúdo é do endereço novo`);
  }
});

test('CLAUDE.md §9.1: nenhuma pasta dinâmica mora ao lado das pastas que a 001.9 tocou', () => {
  const posicoes = new Set();
  for (const { antigo, novo } of MUDANCAS_DA_001_9) {
    posicoes.add(path.dirname(pastaDe(antigo)));
    posicoes.add(path.dirname(pastaDe(novo)));
  }
  for (const dir of posicoes) {
    const dinamicas = fs.readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isDirectory() && e.name.startsWith('['))
      .map((e) => e.name);
    assert.deepEqual(dinamicas, [], `${path.relative(RAIZ, dir)} tem pasta dinâmica: ${dinamicas.join(', ')}`);
  }
});

test('o menu da corretora aponta para os endereços NOVOS, nunca para os antigos', () => {
  const hub = fs.readFileSync(path.join(APP, 'dashboard', 'personalizacao', 'corretora', 'page.tsx'), 'utf8');
  for (const { antigo, novo } of MUDANCAS_DA_001_9) {
    assert.ok(hub.includes(`href="${novo}"`), `o hub Corretora não leva a ${novo}`);
    assert.ok(!hub.includes(`href="${antigo}"`), `o hub Corretora ainda leva ao endereço antigo ${antigo}`);
  }
});

test('a Prontidão não mostra "Even" — o nome é AutoBrokers / Agente de Atendimento (CLAUDE.md §1)', async () => {
  const { buildReadiness } = await import('../lib/admin/tenant-readiness.ts');
  const textos = buildReadiness({}).items.flatMap((i) => [i.label, i.reason, i.action]).join(' | ');
  const textosCheios = buildReadiness({
    company_name: 'X', core_provisioned: true, even_provisioned: true, core_personalized: true,
    even_personalized: true, even_active: true, team_count: 1, handoff_defined: true,
    active_corridors: 1, installed_auxiliaries: 1, whatsapp_connected: true,
    knowledge_configured: true, approvers_defined: true,
  }).items.flatMap((i) => [i.label, i.reason, i.action]).join(' | ');
  assert.doesNotMatch(textos, /\bEven\b/, 'a Prontidão vazia ainda diz "Even"');
  assert.doesNotMatch(textosCheios, /\bEven\b/, 'a Prontidão cheia ainda diz "Even"');
  const hrefs = buildReadiness({}).items.map((i) => i.href).filter(Boolean);
  for (const { antigo } of MUDANCAS_DA_001_9) {
    assert.ok(!hrefs.includes(antigo), `a Prontidão ainda leva ao endereço antigo ${antigo}`);
  }
  for (const h of hrefs) assert.ok(linkExiste(classificar(h, false).segs, ROTAS), `a Prontidão leva a ${h}, que não existe`);
});
