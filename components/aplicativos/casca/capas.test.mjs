// SPEC-139 · L1 — as capas geradas em código: o que TODA capa precisa cumprir, medido no SVG que o motor devolve
// (`capaSvg` de capas/composicoes.ts, o mesmo que o produto e a prancha usam — nunca uma reimplementação aqui).
//
// Roda com: node components/aplicativos/casca/capas.test.mjs
//
//   1. determinística: o mesmo pedido devolve os mesmos bytes;
//   2. sem texto, sem emoji, sem imagem, sem endereço externo (a mutação 2 da SPEC §6);
//   3. tamanho: ≤ 8 KB por capa (alvo 4 KB; decisão do gerente: até 8 se o efeito pedir) — mínimo e máximo impressos;
//   4. a cor vem SÓ da paleta; o claro e o escuro são a MESMA arte (mesma geometria, outra tabela);
//   5. a paleta cobre todo aplicativo da loja com o MESMO ícone do catálogo; vizinhos na galeria com matizes distintas;
//   6. o ícone sobrevive ao recorte 4:1 do cabeçalho (y 250..650) e fica na área segura;
//   7. vários na mesma página: nenhum id repetido entre capas;
//   8. o PRODUTO: CapaGerada.tsx (renderizado) desenha a composição da direção A; cover_url vence; sem texto.
//
// Numa árvore sem node_modules: NODE_PATH=<node_modules da árvore principal> (typescript, react, react-dom).
//
// LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): cada guarda roda também contra uma entrada que ele DEVE reprovar — e a
// mutação 2 roda de verdade: uma CÓPIA de composicoes.ts com um <text> injetado (o original nunca é tocado).

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, '..', '..', '..');
const PASTA = path.join(AQUI, 'capas');
const { carregarCapas } = await import(pathToFileURL(path.join(RAIZ, 'scripts', 'prancha-das-capas.mjs')).href);

let falhas = 0;
function checar(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else {
    falhas += 1;
    console.log(`  X   ${nome}${detalhe ? `  — ${detalhe}` : ''}`);
  }
}

const DIRECOES = ['A', 'B', 'C'];
const TEMAS = ['claro', 'escuro'];
const LIMITE = 8 * 1024;

// ── os guardas (funções puras sobre o SVG) ─────────────────────────────────────────────────────────────────────────

/** O que não pode existir numa capa. Devolve a lista do que achou (vazia = limpa). */
function proibidos(svg) {
  const achados = [];
  if (/<text[\s>]/i.test(svg)) achados.push('<text>');
  if (/<tspan[\s>]/i.test(svg)) achados.push('<tspan>');
  if (/<image[\s>]/i.test(svg) || /<img[\s>]/i.test(svg)) achados.push('<image>');
  if (/<foreignObject/i.test(svg)) achados.push('<foreignObject>');
  if (/<script/i.test(svg)) achados.push('<script>');
  if (/\shref=|xlink:href/i.test(svg)) achados.push('href');
  if (/url\(\s*['"]?(https?:|data:|\/\/)/i.test(svg)) achados.push('url externa');
  if (/@import/i.test(svg)) achados.push('@import');
  if (/\p{Extended_Pictographic}/u.test(svg)) achados.push('emoji');
  return achados;
}

/** A caixa do DESENHO do ícone principal (o grupo `id="<prefixo>i"`): a grade 24 tem margem 2, o traço soma metade. */
function caixaDoIcone(svg) {
  const m = svg.match(/<g id="c[0-9a-z]+i" transform="translate\((-?[\d.]+) (-?[\d.]+)\) scale\(([\d.]+)\)"[^>]*stroke-width="([\d.]+)"/);
  if (!m) return null;
  const [x, y, s, w] = m.slice(1).map(Number);
  const meio = (w * s) / 2;
  return { x0: x + 2 * s - meio, y0: y + 2 * s - meio, x1: x + 22 * s + meio, y1: y + 22 * s + meio };
}

/** Quanto do desenho fica visível num recorte (0–1, o produto das frações horizontal e vertical). */
function fracaoVisivel(c, { x0, y0, x1, y1 }) {
  const fx = Math.max(0, Math.min(c.x1, x1) - Math.max(c.x0, x0)) / (c.x1 - c.x0);
  const fy = Math.max(0, Math.min(c.y1, y1) - Math.max(c.y0, y0)) / (c.y1 - c.y0);
  return fx * fy;
}

/**
 * O ícone sobrevive? A e C: inteiro no miolo 4:1 e na área segura. B (o ícone cortado pela borda É a direção): no miolo
 * 4:1, ≥ 85 % do desenho na altura E ≥ 85 % na largura (cada eixo medido sozinho, com o traço).
 */
function iconeSobrevive(svg, direcao) {
  const c = caixaDoIcone(svg);
  if (!c) return { ok: false, motivo: 'grupo do ícone não encontrado' };
  const miolo = { x0: 0, y0: 250, x1: 1600, y1: 650 };
  const seguro = { x0: 80, y0: 80, x1: 1520, y1: 820 };
  if (direcao === 'B') {
    const fy = fracaoVisivel(c, { ...miolo, x0: -1e6, x1: 1e6 });
    const fx = fracaoVisivel(c, { ...miolo, y0: -1e6, y1: 1e6 });
    return { ok: fy >= 0.85 && fx >= 0.85, motivo: `${(Math.min(fx, fy) * 100).toFixed(0)} % visível no 4:1 (altura ${(fy * 100).toFixed(0)} %, largura ${(fx * 100).toFixed(0)} %)` };
  }
  const f4 = fracaoVisivel(c, miolo);
  const fs = fracaoVisivel(c, seguro);
  return { ok: f4 === 1 && fs === 1, motivo: `4:1 ${(f4 * 100).toFixed(0)} % · área segura ${(fs * 100).toFixed(0)} %` };
}

/** A geometria sem as cores e as opacidades: o claro e o escuro de uma capa têm de dar a MESMA. */
function geometria(svg) {
  return [...svg.matchAll(/\s(d|transform|cx|cy|r|rx|ry|x|y|width|height|x1|y1|x2|y2|points)="([^"]*)"/g)]
    .map((m) => `${m[1]}=${m[2]}`).join('|');
}

const distanciaDeMatiz = (a, b) => { const d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); };

/** Vizinhos na ordem dada com matizes a ≥ `minimo` graus. Devolve o par mais próximo. */
function vizinhosDistintos(ordem, h, minimo) {
  let pior = { d: 999, par: '' };
  for (let i = 1; i < ordem.length; i += 1) {
    const d = distanciaDeMatiz(h(ordem[i - 1]), h(ordem[i]));
    if (d < pior.d) pior = { d, par: `${ordem[i - 1]} → ${ordem[i]}` };
  }
  return { ok: pior.d >= minimo, ...pior };
}

// ── as medições ────────────────────────────────────────────────────────────────────────────────────────────────────

const capas = await carregarCapas(PASTA);
const { capaSvg, SLUGS_DA_LOJA, PALETA, visualDaCapa, tokensDaCapa } = capas;

console.log('\n1. determinística');
{
  let iguais = 0;
  let total = 0;
  for (const slug of SLUGS_DA_LOJA) for (const direcao of DIRECOES) for (const tema of TEMAS) {
    total += 1;
    if (capaSvg({ slug, direcao, tema }) === capaSvg({ slug, direcao, tema })) iguais += 1;
  }
  checar(iguais === total, `mesmo pedido → mesmos bytes (${iguais}/${total})`);
  // controle: o guarda consegue ver diferença — dois slugs dão bytes diferentes
  checar(capaSvg({ slug: 'renovacao', direcao: 'A', tema: 'claro' }) !== capaSvg({ slug: 'cobranca-feita', direcao: 'A', tema: 'claro' }),
    'controle: capas de aplicativos diferentes têm bytes diferentes');
  // um módulo carregado de novo (outra instância) devolve os mesmos bytes: nada depende de estado do processo
  const copia = fs.mkdtempSync(path.join(os.tmpdir(), 'capas-de-novo-'));
  for (const f of ['composicoes.ts', 'paleta.ts', 'icones-svg.ts']) fs.copyFileSync(path.join(PASTA, f), path.join(copia, f));
  const outra = await carregarCapas(copia);
  const pedido = { slug: 'checklist-6h', direcao: 'C', tema: 'escuro' };
  checar(outra.capaSvg(pedido) === capaSvg(pedido), 'outra instância do módulo → os mesmos bytes');
  fs.rmSync(copia, { recursive: true, force: true });
}

console.log('\n2. sem texto, sem emoji, sem imagem, sem endereço externo');
{
  const sujas = [];
  for (const slug of SLUGS_DA_LOJA) for (const direcao of DIRECOES) for (const tema of TEMAS) {
    const p = proibidos(capaSvg({ slug, direcao, tema }));
    if (p.length) sujas.push(`${direcao} ${slug} ${tema}: ${p.join(', ')}`);
  }
  checar(sujas.length === 0, `as ${SLUGS_DA_LOJA.length * 6} capas estão limpas`, sujas.slice(0, 3).join(' · '));
  // controles: o guarda reprova cada coisa proibida
  for (const [rotulo, lixo] of [
    ['<text>', '<text x="0" y="0">Renovação</text>'], ['emoji', '<path d="M0 0"/>🚗'], ['<image>', '<image href="x.png"/>'],
    ['url externa', '<rect fill="url(https://x.y/z)"/>'], ['xlink:href', '<use xlink:href="#a"/>'],
  ]) {
    checar(proibidos(`<svg>${lixo}</svg>`).length > 0, `controle: o guarda reprova ${rotulo}`);
  }
}

console.log('\n2b. a MUTAÇÃO 2 da SPEC, de verdade: uma cópia do motor com um <text> injetado');
{
  const pasta = fs.mkdtempSync(path.join(os.tmpdir(), 'capas-mutacao-'));
  for (const f of ['paleta.ts', 'icones-svg.ts']) fs.copyFileSync(path.join(PASTA, f), path.join(pasta, f));
  // CRLF → LF: numa cópia do Windows (core.autocrlf) a âncora com '\n' não casava e a mutação nem rodava (costura L6)
  const fonte = fs.readFileSync(path.join(PASTA, 'composicoes.ts'), 'utf8').replace(/\r\n/g, '\n');
  const alvo = 'camadaDeGrao(p, tema)\n  );\n}\n\n// ── B';
  checar(fonte.includes(alvo), 'o ponto da mutação existe no motor (o fim da direção A)');
  fs.writeFileSync(path.join(pasta, 'composicoes.ts'), fonte.replace(alvo, 'camadaDeGrao(p, tema) + \'<text x="80" y="120">Renovação</text>\'\n  );\n}\n\n// ── B'));
  const mutante = await carregarCapas(pasta);
  const p = proibidos(mutante.capaSvg({ slug: 'renovacao', direcao: 'A', tema: 'claro' }));
  checar(p.includes('<text>'), 'a capa mutada fica VERMELHA no guarda', p.join(', ') || 'o guarda não viu');
  checar(proibidos(capaSvg({ slug: 'renovacao', direcao: 'A', tema: 'claro' })).length === 0, 'o motor original segue limpo');
  fs.rmSync(pasta, { recursive: true, force: true });
}

console.log('\n3. tamanho');
{
  for (const direcao of DIRECOES) {
    const bytes = SLUGS_DA_LOJA.flatMap((slug) => TEMAS.map((tema) => Buffer.byteLength(capaSvg({ slug, direcao, tema }))));
    const max = Math.max(...bytes);
    checar(max <= LIMITE, `direção ${direcao}: ${Math.min(...bytes)}–${max} bytes por capa (teto ${LIMITE})`);
  }
}

console.log('\n4. a cor vem só da paleta; claro e escuro são a mesma arte');
{
  const fora = [];
  const diferentes = [];
  for (const slug of SLUGS_DA_LOJA) for (const direcao of DIRECOES) {
    for (const tema of TEMAS) {
      const svg = capaSvg({ slug, direcao, tema });
      const permitidas = new Set([...Object.values(tokensDaCapa(visualDaCapa(slug).h, tema)), '#fff', '#000']);
      for (const cor of svg.match(/#[0-9a-f]{3,6}\b/gi) ?? []) if (!permitidas.has(cor.toLowerCase())) fora.push(`${direcao} ${slug} ${tema} ${cor}`);
    }
    if (geometria(capaSvg({ slug, direcao, tema: 'claro' })) !== geometria(capaSvg({ slug, direcao, tema: 'escuro' }))) diferentes.push(`${direcao} ${slug}`);
  }
  checar(fora.length === 0, 'nenhuma cor fora da paleta do aplicativo', fora.slice(0, 3).join(' · '));
  checar(diferentes.length === 0, 'claro e escuro com a MESMA geometria (108 pares)', diferentes.slice(0, 3).join(' · '));
  // controle: o guarda de geometria vê uma diferença real
  const a = capaSvg({ slug: 'renovacao', direcao: 'B', tema: 'claro' });
  checar(geometria(a) !== geometria(a.replace(/r="2\.4"/, 'r="3"')), 'controle: um raio mudado muda a geometria');
  // mesma luminosidade para todos: o papel `cor` de dois aplicativos de matizes distantes tem L igual por construção —
  // aqui se confere a tabela única (mesmo número de papéis e o mesmo conjunto de chaves para todos)
  const chaves = new Set(SLUGS_DA_LOJA.map((s) => Object.keys(tokensDaCapa(visualDaCapa(s).h, 'claro')).join(',')));
  checar(chaves.size === 1, 'uma receita só de papéis para todos os aplicativos');
}

console.log('\n5. a paleta e o catálogo; vizinhos distintos');
{
  const catalogo = fs.readFileSync(path.join(RAIZ, 'lib', 'auxiliaries', 'catalog.ts'), 'utf8');
  const bloco = catalogo.match(/export const APLICATIVO_VISUAL[^{]*\{([\s\S]*?)\n\};/);
  checar(Boolean(bloco), 'APLICATIVO_VISUAL encontrado no catálogo');
  const doCatalogo = Object.fromEntries([...(bloco?.[1] ?? '').matchAll(/'?([a-z0-9-]+)'?\s*:\s*\{\s*icone:\s*'([A-Za-z]+)',\s*matiz:\s*(\d+)/g)]
    .map((m) => [m[1], { icone: m[2], matiz: Number(m[3]) }]));
  const semCapa = Object.keys(doCatalogo).filter((s) => visualDaCapa(s).icone !== doCatalogo[s].icone || visualDaCapa(s).matiz !== doCatalogo[s].matiz);
  checar(Object.keys(doCatalogo).length >= 18 && semCapa.length === 0,
    `os ${Object.keys(doCatalogo).length} do catálogo têm a mesma figura e a mesma matiz do laudo na paleta`, semCapa.join(', '));
  checar(SLUGS_DA_LOJA.every((s) => s in doCatalogo), `os ${SLUGS_DA_LOJA.length} da grade existem no catálogo`);
  for (const nome of new Set(Object.values(PALETA).map((v) => v.icone))) {
    checar(typeof capas.ICONES_SVG[nome] === 'string' && capas.ICONES_SVG[nome].length > 20, `o desenho de ${nome} está no mapa gerado`);
  }
  // a ordem da galeria dentro de um estado é alfabética (catalog.ts) — a ordem dos slugs é a mesma dos nomes
  const h = (s) => visualDaCapa(s).h;
  const v = vizinhosDistintos(SLUGS_DA_LOJA, h, 18);
  checar(v.ok, `vizinhos em ordem alfabética a ≥ 18° (o par mais próximo: ${v.par}, ${v.d}°)`);
  let minimo = 999;
  for (let i = 0; i < SLUGS_DA_LOJA.length; i += 1) for (let j = i + 1; j < SLUGS_DA_LOJA.length; j += 1) {
    minimo = Math.min(minimo, distanciaDeMatiz(h(SLUGS_DA_LOJA[i]), h(SLUGS_DA_LOJA[j])));
  }
  checar(minimo >= 8, `quaisquer dois aplicativos a ≥ 8° (o menor: ${minimo}°)`);
  // controle: em ordem de matiz (o pior caso) o guarda reprova
  const porMatiz = [...SLUGS_DA_LOJA].sort((a, b) => h(a) - h(b));
  checar(!vizinhosDistintos(porMatiz, h, 18).ok, 'controle: em ordem de matiz, vizinhos a < 18° são reprovados');
  // a ordem do laudo é preservada (o verde segue verde, o violeta segue violeta)
  const frios = SLUGS_DA_LOJA.filter((s) => PALETA[s].matiz > 120);
  const ordemDoLaudo = [...frios].sort((a, b) => PALETA[a].matiz - PALETA[b].matiz || a.localeCompare(b));
  const ordemDaCapa = [...frios].sort((a, b) => PALETA[a].h - PALETA[b].h || a.localeCompare(b));
  checar(ordemDoLaudo.join() === ordemDaCapa.join(), 'a ordem das matizes do laudo é a mesma na capa');
}

console.log('\n6. o ícone sobrevive ao recorte 4:1 e fica na área segura');
{
  const ruins = [];
  let piorB = 1;
  for (const slug of SLUGS_DA_LOJA) for (const direcao of DIRECOES) {
    const r = iconeSobrevive(capaSvg({ slug, direcao, tema: 'claro' }), direcao);
    if (!r.ok) ruins.push(`${direcao} ${slug}: ${r.motivo}`);
    if (direcao === 'B') piorB = Math.min(piorB, Number.parseFloat(r.motivo) / 100);
  }
  checar(ruins.length === 0, `A e C: o ícone inteiro no 4:1 e na área segura; B: ≥ 85 % em cada eixo (pior B: ${(piorB * 100).toFixed(0)} %)`, ruins.slice(0, 3).join(' · '));
  // controle: o mesmo ícone empurrado para cima sai do miolo e o guarda reprova
  const a = capaSvg({ slug: 'renovacao', direcao: 'A', tema: 'claro' });
  const empurrada = a.replace(/(<g id="c[0-9a-z]+i" transform="translate\([\d.]+ )([\d.]+)/, (_, ini, y) => `${ini}${Number(y) - 160}`);
  checar(!iconeSobrevive(empurrada, 'A').ok, 'controle: o ícone 160 acima sai do 4:1 e fica VERMELHO');
}

console.log('\n7. várias capas na mesma página: nenhum id repetido');
{
  const vistos = new Map();
  let repetidos = 0;
  for (const slug of SLUGS_DA_LOJA) for (const direcao of DIRECOES) for (const tema of TEMAS) {
    for (const m of capaSvg({ slug, direcao, tema }).matchAll(/\sid="([^"]+)"/g)) {
      const dono = `${direcao} ${slug} ${tema}`;
      if (vistos.has(m[1]) && vistos.get(m[1]) !== dono) repetidos += 1;
      vistos.set(m[1], dono);
    }
  }
  checar(repetidos === 0, `${vistos.size} ids, nenhum de duas capas`);
}

console.log('\n8. o PRODUTO: CapaGerada desenha a composição (renderizado de verdade, React no servidor)');
{
  // o componente real (CapaGerada.tsx) transpilado com o TypeScript do projeto e carregado com um `require` que entrega o
  // React instalado, o `cn` e o MESMO módulo de composições que o teste mediu acima
  const require = createRequire(path.join(RAIZ, 'package.json'));
  const ts = require('typescript');
  const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const carregarCapa = (composicoes) => {
    const fonte = fs.readFileSync(path.join(AQUI, 'CapaGerada.tsx'), 'utf8');
    const js = ts.transpileModule(fonte, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
      fileName: 'CapaGerada.tsx',
    }).outputText;
    const mod = { exports: {} };
    const req = (id) => {
      if (id === './capas/composicoes') return composicoes;
      if (id === '@/lib/utils') return { cn: (...c) => c.filter(Boolean).join(' ') };
      return require(id);
    };
    new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
    return mod.exports;
  };
  const { CapaGerada, svgsDaCapa } = carregarCapa(capas);
  const html = (props) => renderToStaticMarkup(React.createElement(CapaGerada, props));

  const gerada = html({ slug: 'renovacao', icone: 'RefreshCcwDot', matiz: 203, className: 'aspect-[16/9]' });
  const esperado = svgsDaCapa({ slug: 'renovacao', icone: 'RefreshCcwDot', matiz: 203 });
  checar(gerada.includes(esperado.claro) && gerada.includes(esperado.escuro),
    'a capa sem cover_url é o SVG da composição — claro E escuro, os mesmos bytes do motor');
  checar(esperado.claro === capaSvg({ slug: 'renovacao', direcao: capas.DIRECAO_DO_PRODUTO, tema: 'claro' }) && capas.DIRECAO_DO_PRODUTO === 'A',
    'a direção do produto é a A · Placa (D-139-03), e é a mesma do motor');
  checar(/dark:hidden/.test(gerada) && /hidden dark:block/.test(gerada), 'o tema escolhe qual aparece (dark:hidden / hidden dark:block)');
  checar(proibidos(gerada.replace(/<\/?div[^>]*>/g, '')).length === 0, 'a capa renderizada não tem texto, imagem nem endereço externo');
  checar(/motion-reduce:transform-none/.test(html({ slug: 'renovacao', icone: 'RefreshCcwDot', matiz: 203, crescerNoHover: true })),
    'o crescer no hover respeita prefers-reduced-motion');

  const comFoto = html({ slug: 'renovacao', icone: 'RefreshCcwDot', matiz: 203, coverUrl: 'https://exemplo.invalid/capa.webp' });
  checar(comFoto.includes('<img') && comFoto.includes('https://exemplo.invalid/capa.webp') && !comFoto.includes('<svg'),
    'cover_url VENCE: a imagem do Founder, e nenhuma capa gerada junto');

  // sem slug (quem só passa ícone + matiz): a MESMA capa da linha da tabela com esse par
  const semSlug = svgsDaCapa({ icone: 'ReceiptText', matiz: 158 });
  const comSlug = svgsDaCapa({ slug: 'cobranca-feita', icone: 'ReceiptText', matiz: 158 });
  checar(geometria(semSlug.claro) === geometria(comSlug.claro) && semSlug.claro.match(/#[0-9a-f]{6}/g).join() === comSlug.claro.match(/#[0-9a-f]{6}/g).join(),
    'sem slug, o par ícone + matiz dá a mesma cor e a mesma figura da linha da tabela');
  checar(svgsDaCapa({ icone: 'Plug', matiz: 999 }).claro === svgsDaCapa({ icone: 'Plug', matiz: 999 }).claro
    && proibidos(svgsDaCapa({ icone: '<text>x</text>', matiz: Number.NaN }).claro).length === 0,
    'um par desconhecido (ou lixo) cai numa capa determinística e limpa — o nome do ícone nunca é escrito no SVG');

  // a MUTAÇÃO 2 da SPEC no produto: o componente renderizando um motor que injeta <text> fica VERMELHO
  const mutante = carregarCapa({ ...capas, capaSvg: (p) => capas.capaSvg(p).replace('</svg>', '<text x="80" y="120">Renovação</text></svg>') });
  const sujo = renderToStaticMarkup(React.createElement(mutante.CapaGerada, { slug: 'renovacao', icone: 'RefreshCcwDot', matiz: 203 }));
  checar(proibidos(sujo).includes('<text>'), 'controle: o produto com um motor que escreve <text> fica VERMELHO');
}

console.log(falhas === 0 ? '\nTUDO VERDE' : `\n${falhas} FALHA(S)`);
process.exit(falhas === 0 ? 0 : 1);
