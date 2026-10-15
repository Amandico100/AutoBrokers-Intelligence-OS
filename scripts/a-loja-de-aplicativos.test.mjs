#!/usr/bin/env node
// modelo: claude-opus-5-5
/**
 * O FIO da SPEC-139 (§2) — a loja de aplicativos, do clique na galeria até o banco, com o CÓDIGO REAL.
 *
 * Rode: node scripts/a-loja-de-aplicativos.test.mjs
 *
 *   /dashboard/auxiliares → AuxiliaresClient → CardDoAplicativo → CapaGerada(slug → paleta + composição C; cover_url vence)
 *   /dashboard/auxiliares/cobranca-feita?aba=configurar → ABAS_DO_APLICATIVO → o arquivo que a casca carrega → o MESMO
 *     formulário do modal (o dourado da L2: os 7 cenários, o MESMO sha256) → a MESMA rota de gravação (company_id da sessão)
 *   ?aba=cobrancas → o arquivo da aba → a rota que ele lê, EXECUTADA com duas corretoras (só a da sessão volta)
 *   os endereços antigos (L3, L5 e os que já redirecionavam para eles) → redirect() → o novo existe, num salto só
 *   "Em breve": sem Ligar, sem capa, só Início e Dúvidas
 *
 * COMO: os .ts/.tsx do produto são transpilados com o TypeScript do projeto e carregados com um `require` que entrega o
 * React, o lucide e o Radix instalados; só a BORDA é dublê (`next/link`, `next/navigation`, a sessão e o Supabase). Os
 * componentes são RENDERIZADOS (react-dom/server) — o que se confere é o HTML que o corretor recebe, não o regex da fonte.
 * O endereço → arquivo segue a regra do App Router (estático vence dinâmico; grupo `(x)` não conta; volta atrás quando
 * a pasta estática não tem a página). Cada guarda tem LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3).
 *
 * O que NÃO prova: o import dinâmico do webpack (prova o contrato dele — a forma e o `webpackInclude` lidos da casca),
 * o 307 do servidor (prova o `redirect()` da página; o `next start` + 1 requisição é do gerente) e o desenho (é do juiz
 * de design, pelo harness `/embed/loja`).
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const RAIZ = process.env.LOJA_SOB_TESTE_RAIZ
  ? path.resolve(process.env.LOJA_SOB_TESTE_RAIZ)
  : path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(RAIZ, 'app');
const requireReal = createRequire(path.join(RAIZ, 'package.json'));
function exigir(id) {
  try { return requireReal(id); } catch (e) {
    for (const p of (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)) {
      try { return createRequire(path.join(p, 'x.js'))(id); } catch { /* tenta o próximo */ }
    }
    throw e;
  }
}
const ts = exigir('typescript');
const React = exigir('react');
const { renderToStaticMarkup } = exigir('react-dom/server');

let falhas = 0;
const checar = (cond, nome, detalhe = '') => {
  if (cond) console.log(`  OK  ${nome}`);
  else { falhas += 1; console.log(`  X   ${nome}${detalhe ? `\n        — ${detalhe}` : ''}`); }
  return Boolean(cond);
};
const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');
const existe = (rel) => fs.existsSync(path.join(RAIZ, rel));
const semComentarios = (src) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/\{\/\*[\s\S]*?\*\/\}/g, '');
const sha = (obj) => crypto.createHash('sha256').update(JSON.stringify(obj)).digest('hex');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O carregador: .ts/.tsx do produto → CommonJS; `@/` e `./` resolvidos no disco; o resto do node_modules; a borda é dublê
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
const semProps = (r) => Object.fromEntries(Object.entries(r).filter(([k]) => !['prefetch', 'scroll', 'replace', 'shallow'].includes(k)));
const BORDA = {
  'next/link': { __esModule: true, default: ({ href, children, ...r }) => React.createElement('a', { href: String(href), ...semProps(r) }, children) },
  'next/navigation': {
    useRouter: () => ({ push() {}, replace() {}, refresh() {}, back() {} }),
    usePathname: () => '/dashboard/auxiliares',
    useSearchParams: () => new URLSearchParams(),
    redirect: (u) => { throw Object.assign(new Error('NEXT_REDIRECT'), { destino: u }); },
    notFound: () => { throw new Error('NEXT_NOT_FOUND'); },
  },
  '@supabase/supabase-js': {},
};
const cache = new Map();
function resolverArquivo(base) {
  for (const ext of ['', '.ts', '.tsx', '.js', '/index.ts', '/index.tsx']) {
    const f = base + ext;
    if (fs.existsSync(f) && fs.statSync(f).isFile()) return f;
  }
  throw new Error(`não achei o módulo ${path.relative(RAIZ, base)}`);
}
function resolverImport(de, id) {
  if (id.startsWith('@/')) return resolverArquivo(path.join(RAIZ, id.slice(2)));
  if (id.startsWith('.')) return resolverArquivo(path.resolve(path.dirname(de), id));
  return null;
}
function carregar(abs, extras = {}, semCache = false) {
  if (!semCache && cache.has(abs)) return cache.get(abs).exports;
  const fonte = extras.__fonte ?? fs.readFileSync(abs, 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    fileName: path.basename(abs),
  }).outputText;
  const mod = { exports: {} };
  if (!semCache) cache.set(abs, mod);
  const req = (id) => {
    if (id in extras) return extras[id];
    if (id in BORDA) return BORDA[id];
    if (/\.css$/.test(id)) return {};
    const arq = resolverImport(abs, id);
    if (arq) return /\.(tsx?)$/.test(arq) ? carregar(arq) : exigir(arq);
    return exigir(id);
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}
const modulo = (rel, extras) => carregar(path.join(RAIZ, rel), extras);

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O endereço → o arquivo que o App Router serve (estático vence dinâmico; grupo não conta; volta atrás)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
const ehGrupo = (n) => n.startsWith('(') && n.endsWith(')');
const ehDinamico = (n) => n.startsWith('[') && n.endsWith(']') && !n.startsWith('[...') && !n.startsWith('[[...');
export function arquivoDoEndereco(url, app = APP) {
  const segs = url.split(/[?#]/)[0].split('/').filter(Boolean);
  const pastas = (dir) => fs.readdirSync(dir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name);
  const anda = (dir, i) => {
    if (i === segs.length) {
      for (const f of ['page.tsx', 'page.ts', 'route.ts', 'route.tsx']) if (fs.existsSync(path.join(dir, f))) return path.join(dir, f);
      for (const g of pastas(dir).filter(ehGrupo)) { const r = anda(path.join(dir, g), i); if (r) return r; }
      return null;
    }
    const nomes = pastas(dir);
    if (nomes.includes(segs[i])) { const r = anda(path.join(dir, segs[i]), i + 1); if (r) return r; }
    for (const g of nomes.filter(ehGrupo)) { const r = anda(path.join(dir, g), i); if (r) return r; }
    for (const d of nomes.filter(ehDinamico)) { const r = anda(path.join(dir, d), i + 1); if (r) return r; }
    return null;
  };
  return anda(app, 0);
}
const rel = (abs) => (abs ? path.relative(RAIZ, abs).split(path.sep).join('/') : null);
/** página que SÓ redireciona: o corpo do default export começa no redirect() */
const soRedireciona = (fonte) => /export default (?:async )?function \w*\([^)]*\)\s*\{\s*redirect\(\s*'([^']+)'\s*\)/.exec(semComentarios(fonte))?.[1] ?? null;

console.log('\n[0] O carregador e o endereço → arquivo têm controle');
checar(rel(arquivoDoEndereco('/dashboard/auxiliares/cobranca-feita')) === 'app/dashboard/auxiliares/[slug]/page.tsx',
  '/dashboard/auxiliares/cobranca-feita → [slug]/page.tsx (dinâmico)');
checar(rel(arquivoDoEndereco('/dashboard/auxiliares/checklist-6h')) === 'app/dashboard/auxiliares/[slug]/page.tsx',
  '/dashboard/auxiliares/checklist-6h → [slug] (a pasta estática checklist-6h não tem page: volta atrás)');
checar(rel(arquivoDoEndereco('/dashboard/auxiliares/galeria/follow-up-whatsapp')) === 'app/dashboard/auxiliares/galeria/follow-up-whatsapp/page.tsx',
  'CONTROLE: o estático vence o dinâmico (galeria/follow-up-whatsapp ≠ galeria/[slug])');
checar(arquivoDoEndereco('/dashboard/nao-existe-139/x/y') === null, 'CONTROLE: um endereço inventado não tem arquivo');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// [1] A galeria → o card → a capa (paleta + composição C; cover_url vence) e o tile com a cor da MESMA paleta
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] /dashboard/auxiliares → AuxiliaresClient → CardDoAplicativo → CapaGerada(slug → paleta + C)');
const C = modulo('lib/auxiliaries/catalog.ts');
const COMPOSICOES = modulo('components/aplicativos/casca/capas/composicoes.ts');
const PALETA = modulo('components/aplicativos/casca/capas/paleta.ts');
const CARD = modulo('components/aplicativos/casca/CardDoAplicativo.tsx');
const CAB = modulo('components/aplicativos/casca/CabecalhoDoAplicativo.tsx');

const galeria = arquivoDoEndereco('/dashboard/auxiliares');
checar(rel(galeria) === 'app/dashboard/auxiliares/page.tsx' && /<AuxiliaresClient\s*\/>/.test(fs.readFileSync(galeria, 'utf8')),
  'a galeria é a page.tsx que monta o AuxiliaresClient');
const cliente = semComentarios(ler('app/dashboard/auxiliares/AuxiliaresClient.tsx'));
checar(/from '@\/components\/aplicativos\/casca\/CardDoAplicativo'/.test(cliente) && /<CardDoAplicativo key=\{i\.slug\} item=\{i\}/.test(cliente)
  && /<LinhaEmBreve key=\{i\.slug\} item=\{i\}/.test(cliente), 'o AuxiliaresClient desenha cada item com o CardDoAplicativo (e o "Em breve" com a LinhaEmBreve)');

const VISUAL = C.APLICATIVO_VISUAL;
function itemDe(slug, x = {}) {
  const v = VISUAL[slug] ?? C.VISUAL_PADRAO;
  return {
    template_id: `t-${slug}`, slug, nome: `App ${slug}`, headline: 'Uma frase de exemplo.', categorias: [], estado_catalogo: 'available',
    estado: 'disponivel', o_que_faz: [], promessa: null, fontes: [], falta_para_existir: null, descricao: null, resumo: null,
    conectores_pendentes: [], conectores_prontos: [], instalado: false, install_id: null, ultima_execucao: null, rotinas: 0,
    tela_de_execucao: null, icone: v.icone, matiz: v.matiz, cover_url: null, faq: [], destaque: null, conexoes: [],
    prova: { execucoes: 0, ultima_execucao: null, renovacoes_no_mes: null }, sem_rotina: false, ...x,
  };
}
const html = (Comp, props) => renderToStaticMarkup(React.createElement(Comp, props));
const tintaDe = (slug, tema) => PALETA.tokensDaCapa(PALETA.visualDaCapa(slug).h, tema).tinta;
const varDoTile = (h, nome) => new RegExp(`--tile-${nome}:\\s*(#[0-9a-f]{6})`, 'i').exec(h)?.[1]?.toLowerCase() ?? null;
/** o primeiro tile do ícone (o span com a classe `icone-aplicativo`) e o estilo dele */
const tileDo = (h) => /<span style="([^"]*)" class="[^"]*icone-aplicativo[^"]*"/.exec(h)?.[1] ?? '';

const LOJA = PALETA.SLUGS_DA_LOJA;
checar(LOJA.length === 18, `a paleta tem os ${LOJA.length} aplicativos da loja`);
const capaErrada = [];
const tileErrado = [];
for (const slug of LOJA) {
  const h = html(CARD.CardDoAplicativo, { item: itemDe(slug) });
  for (const tema of ['claro', 'escuro']) {
    if (!h.includes(COMPOSICOES.capaSvg({ slug, direcao: COMPOSICOES.DIRECAO_DO_PRODUTO, tema }))) capaErrada.push(`${slug} ${tema}`);
  }
  // D-139-CB-03 (conserto B): o tile do card só existe com a capa do Founder — a cor dele se mede num card com cover_url
  if (tileDo(h) !== '') tileErrado.push(`${slug} (tile ao lado da capa gerada)`);
  const estilo = tileDo(html(CARD.CardDoAplicativo, { item: itemDe(slug, { cover_url: 'https://exemplo.invalid/c.webp' }) }));
  if (varDoTile(estilo, 'claro') !== tintaDe(slug, 'claro') || varDoTile(estilo, 'escuro') !== tintaDe(slug, 'escuro')) {
    tileErrado.push(`${slug} (${estilo || 'sem tile'})`);
  }
}
checar(COMPOSICOES.DIRECAO_DO_PRODUTO === 'C', 'a direção do produto é a C · Cena (a escolha do Founder, 15/10)');
checar(capaErrada.length === 0, `os ${LOJA.length} cards desenham a capa da composição C pela linha do slug (claro E escuro)`, capaErrada.slice(0, 3).join(' · '));
checar(tileErrado.length === 0, `capa gerada: nenhum card repete o ícone num tile; com cover_url, o tile dos ${LOJA.length} tem a TINTA da paleta do slug (claro e escuro)`, tileErrado.slice(0, 2).join(' · '));
// o caso que separa "a matiz do laudo" de "a matiz da capa": o Radar (262° no laudo → 214° na capa, conserto B)
const radar = tileDo(html(CARD.CardDoAplicativo, { item: itemDe('radar-mercado-regulacao', { cover_url: 'https://exemplo.invalid/r.webp' }) }));
checar(PALETA.visualDaCapa('radar-mercado-regulacao').h === 214 && varDoTile(radar, 'claro') === tintaDe('radar-mercado-regulacao', 'claro'),
  'o Radar: o tile bate com a capa (h 214), não com a matiz 262 do laudo');
checar(tintaDe('radar-mercado-regulacao', 'claro') !== PALETA.tokensDaCapa(262, 'claro').tinta,
  'CONTROLE: a tinta de 262° é OUTRA cor (o guarda consegue ver a diferença)');

// a cor do estilo chega à TINTA pintada: a classe lê as variáveis nos dois temas
const CSS = ler('app/globals.css');
const regraClara = /\.icone-aplicativo\s*\{([^}]*)\}/.exec(CSS)?.[1] ?? '';
const regraEscura = /\.dark \.icone-aplicativo\s*\{([^}]*)\}/.exec(CSS)?.[1] ?? '';
checar(/color:\s*var\(--tile-claro\b/.test(regraClara) && /color:\s*var\(--tile-escuro\b/.test(regraEscura),
  'globals.css: `.icone-aplicativo` pinta com --tile-claro, e no escuro com --tile-escuro', `${regraClara.trim()} | ${regraEscura.trim()}`);

// contraste do ícone sobre o fundo do tile (bg-surface-2) ≥ 3:1 nos dois temas
function hslParaRgb(h, s, l) {
  s /= 100; l /= 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  return [0, 8, 4].map((n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1))));
}
const lum = (rgb) => { const [r, g, b] = rgb.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const hexRgb = (hx) => [1, 3, 5].map((i) => parseInt(hx.slice(i, i + 2), 16) / 255);
const contraste = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
const surface2 = [...CSS.matchAll(/--surface-2:\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%/g)].map((m) => hslParaRgb(+m[1], +m[2], +m[3]));
checar(surface2.length >= 2, 'o fundo do tile (--surface-2) lido do :root e do .dark');
let piorContraste = { v: 99, onde: '' };
for (const slug of [...LOJA, '__desconhecido__']) {
  for (const [i, tema] of [[0, 'claro'], [1, 'escuro']]) {
    const v = contraste(hexRgb(tintaDe(slug, tema)), surface2[i]);
    if (v < piorContraste.v) piorContraste = { v, onde: `${slug} ${tema}` };
  }
}
checar(piorContraste.v >= 3, `o ícone no tile tem contraste ≥ 3:1 nos dois temas (o pior: ${piorContraste.v.toFixed(2)}:1, ${piorContraste.onde})`);
checar(contraste(hexRgb(PALETA.tokensDaCapa(300, 'escuro').fundo), surface2[1]) < 3,
  'CONTROLE: o fundo da capa escura sobre o surface-2 escuro fica abaixo de 3:1 (o medidor consegue reprovar)');

// cover_url vence — no card E no cabeçalho
const comFoto = html(CARD.CardDoAplicativo, { item: itemDe('renovacao', { cover_url: 'https://exemplo.invalid/capa.webp' }) });
checar(comFoto.includes('src="https://exemplo.invalid/capa.webp"') && !/data-capa="gerada"/.test(comFoto), 'cover_url vence no card: a imagem, nenhuma capa gerada');
const botaoDisp = C.botaoPrincipal(itemDe('renovacao', { cover_url: 'https://exemplo.invalid/capa.webp' }));
const cabFoto = html(CAB.CabecalhoDoAplicativo, { item: itemDe('renovacao', { cover_url: 'https://exemplo.invalid/capa.webp' }), botao: botaoDisp,
  conexoes: [], resumoDosPassos: '0 de 1 prontos', ocupado: false, erro: '', onAcao() {} });
checar(cabFoto.includes('src="https://exemplo.invalid/capa.webp"') && !/data-capa="gerada"/.test(cabFoto), 'cover_url vence no cabeçalho também');

// o cabeçalho lê a MESMA linha da paleta (capa e tile) — completo e compacto
const itemRadar = itemDe('radar-mercado-regulacao');
const propsCab = { item: itemRadar, botao: C.botaoPrincipal(itemRadar), conexoes: [], resumoDosPassos: '0 de 1 prontos', ocupado: false, erro: '', onAcao() {} };
const cab = html(CAB.CabecalhoDoAplicativo, propsCab);
const cabCompacto = html(CAB.CabecalhoDoAplicativo, { ...propsCab, compacto: true });
checar(cab.includes(COMPOSICOES.capaSvg({ slug: 'radar-mercado-regulacao', direcao: COMPOSICOES.DIRECAO_DO_PRODUTO, tema: 'escuro', enquadramento: 'cabecalho' })),
  'o cabeçalho desenha a capa da linha do slug, no quadro do cabeçalho (a cena inteira no 4:1)');
// D-139-L6-01: com a capa GERADA o cabeçalho completo não repete o ícone num tile (a placa da capa É o ícone); com a
// capa do Founder (cover_url) o tile volta; o compacto (sem capa) sempre tem o tile — e todo tile tem a tinta do slug
const cabRadarFoto = html(CAB.CabecalhoDoAplicativo, { ...propsCab, item: { ...itemRadar, cover_url: 'https://exemplo.invalid/r.webp' } });
checar(tileDo(cab) === '', 'capa gerada: o cabeçalho completo NÃO repete o ícone num tile ao lado da placa (D-139-L6-01)');
const tilesCab = [cabRadarFoto, cabCompacto].map((h) => varDoTile(tileDo(h), 'escuro'));
checar(tilesCab.every((t) => t === tintaDe('radar-mercado-regulacao', 'escuro')),
  'o tile do cabeçalho (com cover_url, e no compacto) existe e tem a tinta do slug', tilesCab.join(' · '));

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// [2] A Cobrança: ?aba=configurar → o arquivo que a casca carrega → o MESMO corpo do modal → a rota → a corretora
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] /dashboard/auxiliares/cobranca-feita?aba=configurar → ABAS_DO_APLICATIVO → o formulário do modal → a gravação');
const paginaApp = arquivoDoEndereco('/dashboard/auxiliares/cobranca-feita?aba=configurar');
const fontePagina = paginaApp ? semComentarios(fs.readFileSync(paginaApp, 'utf8')) : '';
checar(/import AuxiliarDetalheClient from '\.\/AuxiliarDetalheClient'/.test(fontePagina) && /<AuxiliarDetalheClient\b/.test(fontePagina)
  && /resolveSessionCompany\(\)/.test(fontePagina) && /auxiliarPorSlug\(supabase, sessao\.companyId, slug\)/.test(fontePagina),
  'a página do aplicativo monta a casca com o item DESTA corretora (company_id da sessão)');
const detalhe = semComentarios(ler('app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx'));
checar(/abasDoAplicativo\(item\)/.test(detalhe) && /abaValida\(abas, busca\?\.get\('aba'\)\)/.test(detalhe) && /<AbasDoAplicativo\b/.test(detalhe),
  'a casca lê ?aba= e as abas do catálogo (abasDoAplicativo → abaValida → AbasDoAplicativo)');

const CASCA_ABAS = ler('components/aplicativos/casca/AbasDoAplicativo.tsx');
const FORMA = new RegExp(/const FORMA_DO_COMPONENTE = \/(.+?)\/;/.exec(CASCA_ABAS)[1]);
const INCLUIR = new RegExp(/webpackInclude:\s*\/(.+?)\/\s*\*\//.exec(CASCA_ABAS)[1]);
checar(/`@\/components\/aplicativos\/\$\{pasta\}\/Aba\$\{nome\}`/.test(CASCA_ABAS), 'o import dinâmico da casca é components/aplicativos/<pasta>/Aba<Nome>');
/** o arquivo que a casca carrega para uma aba (ou null se a forma/contexto a recusam) */
function arquivoDaAba(componente) {
  const m = FORMA.exec(componente ?? '');
  if (!m) return null;
  const relArq = `components/aplicativos/${m[1]}/Aba${m[2]}.tsx`;
  if (!INCLUIR.test(`./${m[1]}/Aba${m[2]}.tsx`)) return null;
  return existe(relArq) ? relArq : null;
}
const cobInstalada = itemDe('cobranca-feita', { estado: 'pausado', instalado: true, install_id: 'i-1', faq: [{ pergunta: 'p?', resposta: 'r' }] });
const abasCob = C.abasDoAplicativo(cobInstalada);
checar(C.abaValida(abasCob, 'configurar') === 'configurar' && C.abaValida(abasCob, 'cobrancas') === 'cobrancas',
  'instalada: ?aba=configurar e ?aba=cobrancas abrem direto', abasCob.map((a) => a.id).join(','));
const arqConfigurar = arquivoDaAba(abasCob.find((a) => a.id === 'configurar')?.componente);
const arqCobrancas = arquivoDaAba(abasCob.find((a) => a.id === 'cobrancas')?.componente);
checar(Boolean(arqConfigurar), `o Configurar da Cobrança é um arquivo que a casca carrega (${abasCob.find((a) => a.id === 'configurar')?.componente} → ${arqConfigurar})`);
checar(Boolean(arqCobrancas), `"Cobranças" é um arquivo que a casca carrega (${abasCob.find((a) => a.id === 'cobrancas')?.componente} → ${arqCobrancas})`);
checar(!arquivoDaAba('cobranca/AbaInexistente139') && !arquivoDaAba('../casca/AbaInicio'),
  'CONTROLE: um componente que não está no disco (ou com "..") não vira arquivo');
const naoInstalada = C.abasDoAplicativo(itemDe('cobranca-feita', { faq: [{ pergunta: 'p?', resposta: 'r' }] }));
checar(!naoInstalada.some((a) => a.id === 'configurar') && C.abaValida(naoInstalada, 'configurar') === 'inicio',
  'não instalada: o Configurar não aparece e ?aba=configurar cai no Início (o "Instale para configurar" da aba nunca é o caminho)');

// o arquivo da aba → o hook e o formulário que ELE importa → o mesmo arquivo que o modal importa
const importsDe = (relArq) => [...semComentarios(ler(relArq)).matchAll(/from '([^']+)'/g)].map((m) => m[1]);
const absDe = (relArq, id) => { try { return resolverImport(path.join(RAIZ, relArq), id); } catch { return null; } };
let formularioDaAba = null;
let hookDaAba = null;
if (arqConfigurar) {
  const imps = importsDe(arqConfigurar);
  hookDaAba = imps.map((i) => absDe(arqConfigurar, i)).find((a) => a && /useFormularioDaRotina\.ts$/.test(a)) ?? null;
  checar(Boolean(hookDaAba) && /useFormularioDaRotina\(/.test(ler(arqConfigurar)) && /\.salvar\(\)/.test(semComentarios(ler(arqConfigurar))),
    'a aba Configurar grava pelo `salvar()` do hook useFormularioDaRotina');
  if (hookDaAba) {
    const hook = semComentarios(fs.readFileSync(hookDaAba, 'utf8'));
    formularioDaAba = [...hook.matchAll(/from '([^']+)'/g)].map((m) => absDe(rel(hookDaAba), m[1])).find((a) => a && /formulario\.ts$/.test(a)) ?? null;
    checar(/fetch\(ROTA_DAS_ROTINAS,/.test(hook) && /body:\s*JSON\.stringify\(corpoDaGravacao\(form, editing, auxiliarSlug, portais\)\)/.test(hook),
      'o hook faz UM POST a ROTA_DAS_ROTINAS com o corpo de corpoDaGravacao');
  }
}
const modalImporta = importsDe('components/auxiliares/PainelDeRotinas.tsx').map((i) => absDe('components/auxiliares/PainelDeRotinas.tsx', i)).filter(Boolean);
checar(Boolean(formularioDaAba) && modalImporta.includes(hookDaAba),
  'o modal (PainelDeRotinas) usa o MESMO hook — logo o MESMO formulário — que a aba', `${rel(formularioDaAba)} · ${rel(hookDaAba)}`);

// O DOURADO da L2, reusado: os mesmos cenários e os mesmos hashes, lidos do teste dela (uma fonte só)
const L2 = ler('scripts/a-cobranca-na-casca.test.mjs');
function literal(nome) {
  const ini = L2.indexOf(`const ${nome} = `);
  if (ini < 0) throw new Error(`o teste da L2 não tem ${nome}`);
  let i = ini + `const ${nome} = `.length;
  const abre = L2[i];
  const fecha = abre === '[' ? ']' : '}';
  let fundo = 0; let aspas = null;
  for (let j = i; j < L2.length; j += 1) {
    const c = L2[j];
    if (aspas) { if (c === '\\') { j += 1; continue; } if (c === aspas) aspas = null; continue; }
    if (c === "'" || c === '"' || c === '`') { aspas = c; continue; }
    if (c === abre) fundo += 1;
    else if (c === fecha) { fundo -= 1; if (fundo === 0) return L2.slice(i, j + 1); }
  }
  throw new Error(`literal ${nome} sem fim`);
}
const NOMES = ['PORTAIS', 'MODELO', 'MODELO_SEM_PORTAIS', 'ROTINA_LEGADA', 'ROTINA_TESTE', 'ROTINA_GENERICA', 'CENARIOS', 'DOURADO'];
// eslint-disable-next-line no-new-func
const FIX = new Function(`${NOMES.map((n) => `const ${n} = ${literal(n)};`).join('\n')}\nreturn { ${NOMES.join(', ')} };`)();
function rodar(F, c) {
  let form; let editing;
  if (c.abrir.rotina) { form = F.formDaRotinaSalva(c.abrir.rotina); editing = c.abrir.rotina; }
  else { form = c.abrir.novo ? F.formDoModelo(c.abrir.novo, 'Cobrança Feita') : F.formEmBranco('Cobrança Feita'); editing = 'new'; }
  for (const k of c.cliques) {
    if (k.dia !== undefined) form = F.alternarDia(form, k.dia);
    else if (k.cobranca) form = F.comCobranca(form, k.cobranca);
    else if (k.campo) form = F.comCampo(form, k.campo);
    else if (k.portal) form = F.alternarPortal(form, FIX.PORTAIS, k.portal[0], k.portal[1]);
  }
  return F.corpoDaGravacao(form, editing, c.slug, FIX.PORTAIS);
}
if (formularioDaAba) {
  const F = carregar(formularioDaAba);
  const diferentes = FIX.CENARIOS.filter((c) => sha(rodar(F, c)) !== FIX.DOURADO[c.nome]);
  checar(FIX.CENARIOS.length === 7 && diferentes.length === 0,
    `os ${FIX.CENARIOS.length} cenários do dourado da L2: o formulário que a aba Configurar carrega grava o MESMO corpo (sha256) que o modal de 5f9bdac`,
    diferentes.map((c) => c.nome).join(' · '));
  const fonteF = fs.readFileSync(formularioDaAba, 'utf8');
  const M = carregar(formularioDaAba, { __fonte: fonteF.replace("auxiliar: auxiliarSlug,", "auxiliar: auxiliarSlug, origem: 'aba',") }, true);
  checar(FIX.CENARIOS.some((c) => sha(rodar(M, c)) !== FIX.DOURADO[c.nome]), 'CONTROLE: um campo a mais no corpo muda o hash (mutação 1 da SPEC, em memória)');
  checar(/ROTA_DAS_ROTINAS = '\/api\/dashboard\/rotinas'/.test(fonteF), 'a rota de gravação é /api/dashboard/rotinas');
}
const rotaRotinas = arquivoDoEndereco('/api/dashboard/rotinas');
const fonteRotinas = rotaRotinas ? semComentarios(fs.readFileSync(rotaRotinas, 'utf8')) : '';
const postRotinas = fonteRotinas.split('export async function POST')[1] ?? '';
checar(rel(rotaRotinas) === 'app/api/dashboard/rotinas/route.ts' && /const ctx = await resolveSessionCompany\(\)/.test(postRotinas)
  && /company_id: ctx\.companyId/.test(postRotinas) && /\.update\(patch\)\.eq\('id', id\)\.eq\('company_id', ctx\.companyId\)/.test(postRotinas),
  'a rota grava a rotina na corretora da SESSÃO (criar com company_id da sessão; atualizar só com o filtro dela)');

// ?aba=cobrancas → a rota que a aba lê, EXECUTADA com duas corretoras
console.log('\n[3] ?aba=cobrancas → a rota de leitura, executada com DUAS corretoras');
const fonteCob = arqCobrancas ? semComentarios(ler(arqCobrancas)) : '';
const urlLida = /fetch\(`(\/api\/[^`?$]+)/.exec(fonteCob)?.[1] ?? null;
const rotaLida = urlLida ? arquivoDoEndereco(urlLida) : null;
checar(Boolean(rotaLida) && !/method:\s*'POST'/.test(fonteCob), `a aba lê ${urlLida} → ${rel(rotaLida)} (só GET)`);
const diasAtras = (n) => new Date(Date.now() - n * 86_400_000).toISOString();
const LINHAS = [
  { id: 'a1', company_id: 'corretora-a', status: 'aceito_pelo_canal', send_mode: 'real', modalidade: 'cliente', portal_key: 'allianz_corretor', recibo: '1', cliente_nome: 'Fulana Exemplo', to_last4: '0001', sent_at: diasAtras(1), created_at: diasAtras(1), encaminhado_ao_cliente_em: null },
  { id: 'b1', company_id: 'corretora-b', status: 'aceito_pelo_canal', send_mode: 'real', modalidade: 'cliente', portal_key: 'hdi_corretor', recibo: '2', cliente_nome: 'Cicrano Exemplo', to_last4: '0002', sent_at: diasAtras(1), created_at: diasAtras(1), encaminhado_ao_cliente_em: null },
];
function bancoDublê() {
  const pedidos = [];
  return {
    pedidos,
    from(tabela) {
      const q = { tabela, filtros: [], cols: '', lim: null };
      pedidos.push(q);
      const api = {
        select(c) { q.cols = c; return api; }, eq(c, v) { q.filtros.push(['eq', c, v]); return api; },
        gte(c, v) { q.filtros.push(['gte', c, v]); return api; }, order() { return api; }, limit(n) { q.lim = n; return api; },
        then(ok, erro) {
          const r = LINHAS.filter((l) => q.filtros.every(([op, c, v]) => (op === 'eq' ? l[c] === v : String(l[c]) >= String(v))));
          return Promise.resolve({ data: r, error: null }).then(ok, erro);
        },
      };
      return api;
    },
  };
}
async function chamar(sessao, fonteRota) {
  const banco = bancoDublê();
  const R = carregar(rotaLida, {
    __fonte: fonteRota,
    'next/server': { NextResponse: { json: (corpo, init) => ({ corpo, status: init?.status ?? 200 }) } },
    '@/lib/vault/server': { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => banco },
  }, true);
  return R.GET({ nextUrl: new URL(`http://x${urlLida}?periodo=30`) });
}
if (rotaLida) {
  const fonteRota = fs.readFileSync(rotaLida, 'utf8');
  const ra = await chamar({ companyId: 'corretora-a', userId: 'u-a' }, fonteRota);
  const rb = await chamar({ companyId: 'corretora-b', userId: 'u-b' }, fonteRota);
  const ids = (r) => (r.corpo?.itens || []).map((x) => x.id).join(',');
  checar(ids(ra) === 'a1' && ids(rb) === 'b1', 'a corretora A vê só a dela; a B, só a dela', `A=${ids(ra)} B=${ids(rb)}`);
  const semFiltro = await chamar({ companyId: 'corretora-a', userId: 'u-a' }, fonteRota.split(".eq('company_id', ctx.companyId)").join(''));
  checar(ids(semFiltro).includes('b1'), 'CONTROLE: sem o filtro company_id a linha da B aparece para a A (mutação 3 da SPEC)');
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// [4] Os endereços antigos → redirect() → o novo existe, num salto só
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[4] Os endereços antigos redirecionam DIRETO para o novo, e o novo abre');
const AUX = '/dashboard/auxiliares';
const P = '/dashboard/personalizacao';
const ANTIGOS = [
  // L3 (P-16) e quem já levava a eles
  [`${AUX}/checklist-6h/hoje`, `${AUX}/checklist-6h?aba=hoje`],
  [`${AUX}/galeria/follow-up-whatsapp`, `${AUX}/follow-up-whatsapp?aba=follow-ups`],
  [`${AUX}/galeria/resumo-atendimentos`, `${AUX}/resumo-atendimentos?aba=resumos`],
  ['/dashboard/briefing', `${AUX}/checklist-6h?aba=hoje`],
  // L5 (EXTRA-001.9) e quem já levava a eles
  [`${P}/agentes/even`, `${P}/corretora/agente-de-atendimento`],
  [`${P}/equipe`, `${P}/corretora/equipe`],
  [`${P}/conhecimento`, `${P}/corretora/conhecimento`],
  [`${P}/custos`, `${P}/corretora/custos`],
  ['/dashboard/equipe', `${P}/corretora/equipe`],
  ['/admin/team', `${P}/corretora/equipe`],
  ['/dashboard/documentos', `${P}/corretora/conhecimento`],
  ['/admin/documents', `${P}/corretora/conhecimento`],
  ['/dashboard/plano', `${P}/corretora/custos`],
  ['/admin/billing', `${P}/corretora/custos`],
];
for (const [antigo, novo] of ANTIGOS) {
  const arq = arquivoDoEndereco(antigo);
  const destino = arq ? soRedireciona(fs.readFileSync(arq, 'utf8')) : null;
  const arqNovo = destino ? arquivoDoEndereco(destino) : null;
  const doisSaltos = arqNovo ? soRedireciona(fs.readFileSync(arqNovo, 'utf8')) : null;
  let abaOk = true;
  const m = /^\/dashboard\/auxiliares\/([a-z0-9-]+)\?aba=([a-z0-9-]+)$/.exec(destino ?? '');
  if (m) {
    const it = itemDe(m[1], { estado: 'ligado', instalado: true, faq: [{ pergunta: 'p?', resposta: 'r' }] });
    abaOk = C.abaValida(C.abasDoAplicativo(it), m[2]) === m[2];
  }
  checar(destino === novo && Boolean(arqNovo) && !doisSaltos && abaOk,
    `${antigo} → ${destino ?? '(sem redirect)'}${m ? ' (a aba existe)' : ''}`,
    `esperado ${novo} · arquivo novo ${rel(arqNovo)}${doisSaltos ? ` · DOIS saltos: o novo redireciona para ${doisSaltos}` : ''}${abaOk ? '' : ' · a aba não existe'}`);
}
checar(soRedireciona("export default function X() {\n  redirect('/a');\n}") === '/a' && soRedireciona("export default function X() { return <div/>; }") === null,
  'CONTROLE: o leitor de redirect() acha o destino e reconhece a página que não redireciona');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// [5] O "Em breve" é honesto: sem Ligar, sem capa, só Início e Dúvidas
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[5] "Em breve": sem Ligar, sem capa na linha, só Início e Dúvidas');
const breve = itemDe('caca-comissao', { estado: 'em_breve', estado_catalogo: 'coming_soon', falta_para_existir: 'Falta conectar o portal.', faq: [{ pergunta: 'p?', resposta: 'r' }] });
const linhaBreve = html(CARD.LinhaEmBreve, { item: breve });
checar(!/data-capa=|<svg[^>]*viewBox="0 0 1600 900"/.test(linhaBreve) && !/Ligar|Instalar/.test(linhaBreve) && /Em breve/.test(linhaBreve),
  'a linha do "Em breve" na galeria: sem capa, sem Ligar/Instalar, com o selo');
const cabBreve = html(CAB.CabecalhoDoAplicativo, { item: breve, botao: C.botaoPrincipal(breve), conexoes: [], resumoDosPassos: '0 de 0 prontos', ocupado: false, erro: '', onAcao() {} });
const botoes = [...cabBreve.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g)].map((x) => x[1].replace(/<[^>]+>/g, '').trim());
checar(botoes.length === 1 && botoes[0] === 'Em breve' && /<button[^>]*disabled/.test(cabBreve) && !/Ligar|Instalar/.test(cabBreve),
  'o cabeçalho do "Em breve": um botão só, "Em breve", desabilitado — nunca Ligar', botoes.join(' | '));
checar(C.abasDoAplicativo(breve).map((a) => a.id).join(',') === 'inicio,duvidas', 'as abas do "Em breve": Início e Dúvidas');
const cabLigavel = html(CAB.CabecalhoDoAplicativo, { item: itemDe('renovacao'), botao: C.botaoPrincipal(itemDe('renovacao')), conexoes: [], resumoDosPassos: '0 de 1 prontos', ocupado: false, erro: '', onAcao() {} });
checar(/Ligar/.test(cabLigavel), 'CONTROLE: fora do "Em breve" o cabeçalho mostra o Ligar (o guarda consegue ver um)');

console.log(falhas === 0 ? '\nO FIO DA LOJA: TODOS OS ELOS VERDES\n' : `\n${falhas} ELO(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
