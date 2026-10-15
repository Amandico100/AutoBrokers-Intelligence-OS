// SPEC-139 · L1 — a PRANCHA das capas: as três direções (A · Placa, B · Traço, C · Cena) lado a lado, para o Founder
// escolher. E o gerador do desenho dos ícones que as capas usam.
//
//   node scripts/prancha-das-capas.mjs <saida.html>      grava a prancha (uma página, tudo SVG inline, zero requisição)
//   node scripts/prancha-das-capas.mjs --icones          regrava components/aplicativos/casca/capas/icones-svg.ts
//
// O desenho vem da MESMA fonte que o produto vai usar: `components/aplicativos/casca/capas/composicoes.ts` (TypeScript
// puro, sem React), carregado direto pelo Node 24 (type stripping). Os imports sem extensão do arquivo .ts são
// resolvidos por um gancho curto abaixo — o mesmo arquivo compila no Next sem mudança.
//
// --icones: o lucide-react 0.446 NÃO exporta o desenho do ícone (`iconNode`): o desenho só existe como argumento de
// `createLucideIcon(...)` dentro de dist/esm/icons/<nome>.js. Este modo lê esses arquivos (pacote instalado, por
// require.resolve — ou NODE_PATH quando a árvore não tem node_modules) e grava o mapa nome → elementos SVG.
//
// A página segue o contrato de página publicada: sem <!doctype>/<html>/<head>/<body>; cores só por tokens; claro e
// escuro da PÁGINA por seletor; as capas mostram SEMPRE as duas variantes, dentro de painéis com as cores do produto.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire, registerHooks } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RAIZ = 'C:/Users/amand/Projetos/AUTOBROKERS RESULTA/AutoBrokers-FIX-139D';
const PASTA_DAS_CAPAS = path.join(RAIZ, 'components', 'aplicativos', 'casca', 'capas');

/** Os ícones que as capas desenham: os de APLICATIVO_VISUAL (catalog.ts) + o padrão. */
const ICONES = [
  'BadgePercent', 'BookOpenCheck', 'CalendarClock', 'Calculator', 'ChartNoAxesCombined', 'FolderCheck', 'HandCoins',
  'LayoutGrid', 'MessageSquareReply', 'Radar', 'ReceiptText', 'RefreshCcwDot', 'ScanText', 'ScrollText', 'ShieldCheck',
  'Sunrise', 'Umbrella', 'UserRoundCheck', 'UserSearch',
];

const kebab = (nome) => nome.replace(/([a-z0-9])([A-Z])/g, '$1-$2').replace(/([A-Z])([A-Z][a-z])/g, '$1-$2').toLowerCase();

function gerarIcones() {
  const require = createRequire(path.join(RAIZ, 'package.json'));
  let pacote;
  try {
    pacote = path.dirname(require.resolve('lucide-react/package.json'));
  } catch {
    const extra = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean);
    const achado = extra.map((p) => path.join(p, 'lucide-react')).find((p) => fs.existsSync(path.join(p, 'package.json')));
    if (!achado) throw new Error('lucide-react não encontrado (defina NODE_PATH para um node_modules que o tenha)');
    pacote = achado;
  }
  const versao = JSON.parse(fs.readFileSync(path.join(pacote, 'package.json'), 'utf8')).version;
  const linhas = [];
  for (const nome of ICONES) {
    const arquivo = path.join(pacote, 'dist', 'esm', 'icons', `${kebab(nome)}.js`);
    const fonte = fs.readFileSync(arquivo, 'utf8');
    const m = fonte.match(/createLucideIcon\(\s*"([^"]+)",\s*(\[[\s\S]*?\])\s*\);/);
    if (!m) throw new Error(`não achei o desenho de ${nome} em ${arquivo}`);
    // o argumento é um literal de array JS (chaves sem aspas): avaliado isolado, sem acesso a nada
    const nos = Function(`"use strict"; return (${m[2]});`)();
    const svg = nos
      .map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).filter(([k]) => k !== 'key').map(([k, v]) => `${k}="${v}"`).join(' ')}/>`)
      .join('');
    linhas.push(`  ${nome}: '${svg}',`);
  }
  const saida = [
    '// GERADO — não edite à mão. SPEC-139 · L1: o desenho dos ícones lucide que entram DENTRO do SVG das capas.',
    `// Fonte: lucide-react ${versao} (dist/esm/icons/*.js), licença ISC. Regerar: node scripts/prancha-das-capas.mjs --icones`,
    '// Cada valor são os elementos de um ícone na grade 24×24 (sem o <svg> em volta; o traço é de quem desenha).',
    '',
    'export const ICONES_SVG: Readonly<Record<string, string>> = {',
    ...linhas,
    '};',
    '',
  ].join('\n');
  const destino = path.join(PASTA_DAS_CAPAS, 'icones-svg.ts');
  fs.writeFileSync(destino, saida);
  console.log(`gravado ${path.relative(RAIZ, destino)} — ${ICONES.length} ícones, lucide-react ${versao}`);
}

let ganchoRegistrado = false;
/** Resolve `./paleta` → `./paleta.ts` (o Next resolve sozinho; o Node puro pede a extensão). */
export function registrarImportsSemExtensao() {
  if (ganchoRegistrado) return;
  ganchoRegistrado = true;
  registerHooks({
    resolve(especificador, contexto, proximo) {
      if (/^\.\.?\//.test(especificador) && !path.extname(especificador)) {
        try { return proximo(`${especificador}.ts`, contexto); } catch { /* cai no padrão */ }
      }
      return proximo(especificador, contexto);
    },
  });
}

/** Os três módulos das capas, pelo caminho (o teste passa um caminho de cópia mutada). */
export async function carregarCapas(pasta = PASTA_DAS_CAPAS) {
  registrarImportsSemExtensao();
  const url = (arquivo) => pathToFileURL(path.join(pasta, arquivo)).href;
  const [composicoes, paleta, icones] = await Promise.all([
    import(url('composicoes.ts')), import(url('paleta.ts')), import(url('icones-svg.ts')),
  ]);
  return { ...composicoes, ...paleta, ...icones };
}

// ── a página ────────────────────────────────────────────────────────────────────────────────────────────────────────

/** Nomes de exibição (os mesmos do catálogo) — só para a legenda da grade e os cards da prancha. */
const NOMES = {
  'caca-comissao': 'Caça-Comissão', 'carteira-blindada': 'Carteira Blindada', 'checklist-6h': 'Checklist das 6h',
  'clientes-perdidos': 'Clientes Perdidos', 'cobranca-feita': 'Cobrança', 'contabilidade-pronta': 'Contabilidade Pronta',
  cotacao: 'Cotação Rápida', 'digitacao-zero': 'Digitação Zero', 'follow-up-whatsapp': 'Follow-up do WhatsApp',
  'organizacao-completa': 'Organização Completa', 'protecao-completa': 'Proteção Completa',
  'quem-cobra-menos': 'Quem Cobra Menos', 'radar-mercado-regulacao': 'Radar de Mercado', renovacao: 'Renovação',
  'resgatar-cliente': 'Resgatar Cliente', 'resumo-atendimentos': 'Resumo de Atendimentos',
  'sinistralidade-avancada': 'Sinistralidade Avançada', 'tarefas-agendadas': 'Tarefas Agendadas',
};

/** Os quatro da amostra: o estado e a prova seguem o card real (sem número inventado — D-131-26). */
const AMOSTRA = [
  { slug: 'renovacao', frase: 'As renovações do mês calculadas de madrugada, prontas para você conferir de manhã.', selo: null, prova: 'Pronto para ligar' },
  { slug: 'cobranca-feita', frase: 'Lembra o segurado da parcela em aberto pelo WhatsApp, no tom da sua corretora.', selo: ['Falta conectar', 'aviso'], prova: 'Falta conectar InfoCap' },
  { slug: 'checklist-6h', frase: 'Às 6 da manhã, a lista do que precisa da sua atenção hoje.', selo: ['Desligado', 'neutro'], prova: 'Pronto para ligar' },
  { slug: 'sinistralidade-avancada', frase: 'Você entra na negociação sabendo qual seguradora vai apertar.', selo: ['Em breve', 'neutro'], prova: 'Em breve' },
];

const DIRECOES = [
  { letra: 'A', nome: 'Placa', frase: 'O ícone vira uma peça de esmalte, com brilho e sombra, sobre a cor do aplicativo. Calma e reconhecível de longe — a cara de loja de aplicativos.' },
  { letra: 'B', nome: 'Traço', frase: 'O ícone em tamanho grande, só em linha de luz, saindo pela borda, sobre a grade em que ele foi desenhado. Técnica e elegante.' },
  { letra: 'C', nome: 'Cena', frase: 'Três peças do trabalho que o aplicativo faz — documento, mensagem, calendário, gráfico — flutuando em perspectiva, e o ícone num selo. Conta o que ele faz.' },
];

function paginaDaPrancha(c) {
  const capa = (slug, direcao, tema) => c.capaSvg({ slug, direcao, tema });
  const tileIcone = (slug, tema, lado) => {
    const v = c.visualDaCapa(slug);
    const t = c.tokensDaCapa(v.h, tema);
    return `<svg viewBox="0 0 24 24" width="${lado}" height="${lado}" fill="none" stroke="${t.tinta}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${c.ICONES_SVG[v.icone]}</svg>`;
  };
  const selo = (s) => (s ? `<span class="selo selo-${s[1]}">${s[0]}</span>` : '');

  const card = (a, d, tema) => `
      <article class="card">
        <div class="card-capa">${capa(a.slug, d, tema)}<span class="esmaece"></span>${a.selo ? `<span class="selo-sobre">${selo(a.selo)}</span>` : ''}</div>
        ${d === 'C' ? '' : `<span class="tile">${tileIcone(a.slug, tema, 24)}</span>`}
        <div class="card-texto"><h4>${NOMES[a.slug]}</h4><p>${a.frase}</p></div>
        <div class="card-rodape"><span>${a.prova}</span><span class="abrir">Abrir</span></div>
      </article>`;

  const cabecalho = (a, d, tema) => `
      <div class="cab produto-${tema}">
        <div class="cab-capa">${c.capaSvg({ slug: a.slug, direcao: d, tema, enquadramento: 'cabecalho' })}</div>
        <div class="cab-linha"><span class="tile tile-72">${tileIcone(a.slug, tema, 34)}</span><div><strong>${NOMES[a.slug]}</strong>${selo(a.selo)}</div></div>
      </div>`;

  const grade = (d, tema) => `
      <div class="painel produto-${tema}">
        <p class="painel-nome">${tema === 'claro' ? 'Tema claro' : 'Tema escuro'}</p>
        <ul class="grade18">${c.SLUGS_DA_LOJA.map((s) => `<li><div class="mini">${capa(s, d, tema)}</div><span>${NOMES[s] ?? s}</span></li>`).join('')}</ul>
      </div>`;

  const secao = (dir) => `
  <section class="direcao" id="direcao-${dir.letra}" aria-labelledby="titulo-${dir.letra}">
    <div class="direcao-cab">
      <span class="letra" aria-hidden="true">${dir.letra}</span>
      <div><h2 id="titulo-${dir.letra}"><span class="sr">Direção ${dir.letra}: </span>${dir.nome}</h2><p>${dir.frase}</p></div>
    </div>

    <h3>No card da loja</h3>
    <div class="painel produto-claro"><p class="painel-nome">Tema claro</p><div class="cards">${AMOSTRA.map((a) => card(a, dir.letra, 'claro')).join('')}</div></div>
    <div class="painel produto-escuro"><p class="painel-nome">Tema escuro</p><div class="cards">${AMOSTRA.map((a) => card(a, dir.letra, 'escuro')).join('')}</div></div>

    <h3>No topo da página do aplicativo</h3>
    <div class="cabs">${AMOSTRA.map((a) => cabecalho(a, dir.letra, 'claro') + cabecalho(a, dir.letra, 'escuro')).join('')}</div>

    <h3>Os 18 aplicativos juntos</h3>
    ${grade(dir.letra, 'claro')}${grade(dir.letra, 'escuro')}
  </section>`;

  const trio = DIRECOES.map((dir) => `
      <a class="trio-item" href="#direcao-${dir.letra}">
        <span class="trio-capas"><span class="trio-capa">${capa('renovacao', dir.letra, 'claro')}</span><span class="trio-capa">${capa('renovacao', dir.letra, 'escuro')}</span></span>
        <span class="trio-legenda"><span class="trio-letra">${dir.letra}</span><span>${dir.nome}${dir.letra === 'C' ? ' — a escolhida' : ''}</span></span>
      </a>`).join('');

  // a escolhida (D-139-03: sem resposta do Founder, a de maior nota), grande: três aplicativos, claro e escuro
  const destaque = ['renovacao', 'cobranca-feita', 'checklist-6h'].map((s) => `<li><span class="dest-capa">${capa(s, 'C', 'claro')}</span><span class="dest-capa">${capa(s, 'C', 'escuro')}</span><span class="dest-nome">${NOMES[s]}</span></li>`).join('');

  return `<title>Capas da loja</title>
<meta name="description" content="A capa escolhida pelo Founder (C · Cena) e as outras duas direções, para comparar.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Geist:wght@400..600&display=swap">
<style>${ESTILO}</style>
<main class="pagina">
  <header class="topo">
    <p class="marca">Loja de aplicativos do AutoBrokers</p>
    <h1>Escolhida pelo Founder: C · Cena</h1>
    <p class="lead">Você escolheu a C em 15/10. Ela agora se monta para cada lugar: no card, duas peças grandes; no topo da página, a cena inteira na faixa; na vitrine, a cena à direita e o texto à esquerda. A capa de cada aplicativo é feita em código, sem foto e sem texto, com a cor dele, e muda sozinha para o tema escuro. Abaixo, as três direções aparecem no card da loja, no topo da página do aplicativo e com os 18 aplicativos juntos, sempre no claro e no escuro.</p>
    <div class="tema" role="group" aria-label="Tema desta página">
      <button type="button" data-tema="auto" aria-pressed="true">Automático</button>
      <button type="button" data-tema="light" aria-pressed="false">Claro</button>
      <button type="button" data-tema="dark" aria-pressed="false">Escuro</button>
    </div>
  </header>
  <section class="destaque" aria-label="A direção escolhida pelo Founder, C · Cena"><ul>${destaque}</ul></section>
  <h2 class="tres">As três direções</h2>
  <nav class="trio" aria-label="As três direções, com a capa da Renovação">${trio}
  </nav>
  ${DIRECOES.map(secao).join('\n')}
  <footer class="fim">
    <p class="fim-pergunta">Escolhida: C · Cena.</p>
    <p>Se nenhuma servir, as capas podem ser imagens suas: 1600 × 900, sem texto. Elas entram no lugar da capa desenhada, aplicativo por aplicativo.</p>
  </footer>
</main>
<script>
(function () {
  var raiz = document.documentElement, botoes = document.querySelectorAll('[data-tema]');
  function aplicar(v) {
    if (v === 'light' || v === 'dark') raiz.setAttribute('data-theme', v); else { raiz.removeAttribute('data-theme'); v = 'auto'; }
    botoes.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-tema') === v)); });
    try { localStorage.setItem('prancha-capas-tema', v); } catch (e) {}
  }
  var salvo = 'auto';
  try { salvo = localStorage.getItem('prancha-capas-tema') || 'auto'; } catch (e) {}
  aplicar(salvo);
  botoes.forEach(function (b) { b.addEventListener('click', function () { aplicar(b.getAttribute('data-tema')); }); });
})();
</script>
`;
}

const ESTILO = `
:root {
  --bg: #eceef2; --ink: #15171c; --ink-2: #4b525d; --linha: #d6dae1; --cartao: #ffffff; --realce: #2b6a8f;
  --botao: #ffffff; --botao-ativo: #15171c; --botao-ativo-ink: #ffffff;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0b0c0f; --ink: #eef0f3; --ink-2: #a2aab5; --linha: #24272e; --cartao: #14161a; --realce: #7fb3d4;
    --botao: #17191e; --botao-ativo: #eef0f3; --botao-ativo-ink: #0b0c0f;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0b0c0f; --ink: #eef0f3; --ink-2: #a2aab5; --linha: #24272e; --cartao: #14161a; --realce: #7fb3d4;
  --botao: #17191e; --botao-ativo: #eef0f3; --botao-ativo-ink: #0b0c0f;
  color-scheme: dark;
}
/* as cores do PRODUTO (globals.css), fixas: o painel claro é o app no claro, o escuro é o app no escuro */
.produto-claro {
  --p-bg: #ffffff; --p-surface: #f6f7f9; --p-surface-2: #eef0f3; --p-border: #dcdfe5; --p-border-soft: #e8eaee;
  --p-fg: #1b1e24; --p-fg-2: #434a55; --p-muted: #636a73; --p-primary: #1b1e24;
}
.produto-escuro {
  --p-bg: #0a0b0d; --p-surface: #14161a; --p-surface-2: #1c1f24; --p-border: #272b31; --p-border-soft: #1a1d23;
  --p-fg: #f1f3f5; --p-fg-2: #c4cad2; --p-muted: #828a93; --p-primary: #6fa6c9;
}
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: Geist, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; -webkit-font-smoothing: antialiased; }
svg { display: block; }
.pagina { max-width: 1280px; margin: 0 auto; padding: 56px 24px 96px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.topo { max-width: 820px; }
.marca { margin: 0 0 18px; font-size: 15px; color: var(--ink-2); }
h1 { margin: 0; font-family: "Bricolage Grotesque", Geist, sans-serif; font-weight: 750; font-size: clamp(40px, 7vw, 84px); line-height: .98; letter-spacing: -0.035em; font-variation-settings: "opsz" 96; }
.lead { margin: 22px 0 0; font-size: 18px; line-height: 1.55; color: var(--ink-2); max-width: 66ch; }
.tema { display: inline-flex; gap: 4px; margin-top: 28px; padding: 4px; border: 1px solid var(--linha); border-radius: 12px; background: var(--botao); }
.tema button { font: inherit; font-size: 14px; color: var(--ink-2); background: transparent; border: 0; border-radius: 9px; padding: 8px 14px; min-height: 40px; cursor: pointer; }
.tema button[aria-pressed="true"] { background: var(--botao-ativo); color: var(--botao-ativo-ink); }
.tema button:focus-visible, .trio-item:focus-visible { outline: 2px solid var(--realce); outline-offset: 3px; }

.destaque ul { list-style: none; margin: 48px 0 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
.destaque li { display: grid; gap: 10px; }
.dest-capa { position: relative; display: block; overflow: hidden; border-radius: 18px; aspect-ratio: 16 / 9; box-shadow: 0 30px 60px -32px rgba(10, 20, 40, .5); }
.dest-capa svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.dest-nome { font-size: 15px; color: var(--ink-2); }
.tres { margin: 88px 0 0; font-family: "Bricolage Grotesque", sans-serif; font-weight: 700; font-size: 32px; letter-spacing: -0.02em; }
.trio { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; margin: 24px 0 24px; }
.trio-item { display: block; color: inherit; text-decoration: none; border-radius: 22px; }
.trio-capas { display: grid; border-radius: 20px; overflow: hidden; box-shadow: 0 1px 0 rgba(255,255,255,.4) inset, 0 30px 60px -30px rgba(10, 20, 40, .45); }
.trio-capa svg { width: 100%; height: auto; aspect-ratio: 16 / 9; }
.trio-legenda { display: flex; align-items: baseline; gap: 12px; margin-top: 14px; font-size: 18px; color: var(--ink-2); }
.trio-letra { font-family: "Bricolage Grotesque", sans-serif; font-weight: 750; font-size: 34px; line-height: 1; color: var(--ink); }

.direcao { margin-top: 96px; padding-top: 48px; border-top: 1px solid var(--linha); }
.direcao-cab { display: grid; grid-template-columns: auto 1fr; gap: 28px; align-items: end; max-width: 980px; }
.letra { font-family: "Bricolage Grotesque", sans-serif; font-weight: 800; font-size: clamp(120px, 18vw, 220px); line-height: .74; letter-spacing: -0.06em; font-variation-settings: "opsz" 96; }
.direcao-cab h2 { margin: 0; font-family: "Bricolage Grotesque", sans-serif; font-weight: 700; font-size: 40px; letter-spacing: -0.02em; }
.direcao-cab p { margin: 10px 0 0; font-size: 18px; line-height: 1.5; color: var(--ink-2); max-width: 60ch; }
h3 { margin: 56px 0 16px; font-size: 20px; font-weight: 600; letter-spacing: -0.01em; }

.painel { background: var(--p-bg); border: 1px solid var(--p-border); border-radius: 22px; padding: 18px; color: var(--p-fg); }
.painel + .painel { margin-top: 14px; }
.painel-nome { margin: 2px 4px 14px; font-size: 13px; color: var(--p-muted); }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(232px, 1fr)); gap: 16px; }

/* o card real (laudo §2.3) */
.card { display: flex; flex-direction: column; overflow: hidden; border-radius: 16px; border: 1px solid var(--p-border); background: var(--p-surface); transition: transform .2s ease, box-shadow .2s ease; }
.card:hover { transform: translateY(-2px); box-shadow: 0 18px 40px -22px rgba(0,0,0,.35); }
.card-capa { position: relative; overflow: hidden; aspect-ratio: 16 / 9; }
.card-capa svg { position: absolute; inset: 0; width: 100%; height: 100%; transition: transform .3s ease; }
.card:hover .card-capa svg { transform: scale(1.03); }
.esmaece { position: absolute; inset: auto 0 0 0; height: 33%; background: linear-gradient(to bottom, transparent, var(--p-surface)); }
.selo-sobre { position: absolute; left: 12px; top: 12px; border-radius: 999px; background: color-mix(in srgb, var(--p-bg) 72%, transparent); backdrop-filter: blur(6px); }
.tile { position: relative; display: flex; align-items: center; justify-content: center; width: 48px; height: 48px; margin: -24px 0 0 16px; border-radius: 12px; border: 1px solid var(--p-border); background: var(--p-surface-2); box-shadow: 0 0 0 4px var(--p-surface); }
.card-texto { padding: 12px 16px 16px; flex: 1; }
.card-texto h4 { margin: 0; font-size: 16px; font-weight: 600; letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-texto p { margin: 4px 0 0; font-size: 14px; line-height: 1.43; color: var(--p-muted); min-height: 2.86em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-rodape { display: flex; justify-content: space-between; gap: 12px; padding: 12px 16px; border-top: 1px solid var(--p-border-soft); font-size: 12px; color: var(--p-fg-2); }
.abrir { font-weight: 500; color: var(--p-primary); white-space: nowrap; }
.abrir::after { content: ""; display: inline-block; width: 6px; height: 6px; margin-left: 6px; border-top: 1.5px solid currentColor; border-right: 1.5px solid currentColor; transform: translateY(-1px) rotate(45deg); }
.selo { display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 999px; font-size: 12px; font-weight: 500; border: 1px solid transparent; white-space: nowrap; }
.produto-claro .selo-neutro { background: #eef0f3; color: #434a55; border-color: #dcdfe5; }
.produto-claro .selo-aviso { background: #fbf1dc; color: #7a4d06; border-color: #f0dcae; }
.produto-escuro .selo-neutro { background: #1c1f24; color: #c4cad2; border-color: #2c3037; }
.produto-escuro .selo-aviso { background: #2d230f; color: #f0c97a; border-color: #4a3a17; }

/* o cabeçalho da página do aplicativo: 4:1 no computador, 5:2 no celular (como o produto) */
.cabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.cab { background: var(--p-bg); border: 1px solid var(--p-border); border-radius: 22px; padding: 14px 14px 16px; color: var(--p-fg); }
.cab-capa { position: relative; overflow: hidden; aspect-ratio: 4 / 1; border-radius: 14px; border: 1px solid var(--p-border); }
.cab-capa svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.cab-linha { display: flex; align-items: flex-end; gap: 12px; padding: 0 4px; }
.cab-linha strong { display: block; font-size: 18px; font-weight: 600; letter-spacing: -0.01em; margin-bottom: 4px; }
.cab-linha .selo { margin-bottom: 4px; }
.cab-linha > div { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding-bottom: 2px; }
/* o tile do cabeçalho real: 72 px, sobe 40 px sobre a capa (56 no celular) — CabecalhoDoAplicativo.tsx */
.tile-72 { width: 72px; height: 72px; margin: -40px 0 0 12px; border-radius: 16px; box-shadow: 0 0 0 4px var(--p-bg); z-index: 1; flex-shrink: 0; }

.grade18 { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 14px 12px; }
.grade18 li { min-width: 0; }
.mini { position: relative; overflow: hidden; aspect-ratio: 16 / 9; border-radius: 10px; border: 1px solid var(--p-border-soft); }
.mini svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.grade18 span { display: block; margin-top: 6px; font-size: 12px; color: var(--p-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.fim { margin-top: 96px; padding-top: 40px; border-top: 1px solid var(--linha); max-width: 720px; color: var(--ink-2); font-size: 16px; line-height: 1.55; }
.fim-pergunta { margin: 0 0 8px; font-family: "Bricolage Grotesque", sans-serif; font-size: 32px; font-weight: 700; letter-spacing: -0.02em; color: var(--ink); }

@media (max-width: 960px) {
  .trio, .destaque ul { grid-template-columns: 1fr; }
  .cabs { grid-template-columns: 1fr; }
  .grade18 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .pagina { padding: 32px 16px 72px; }
  .cab-capa { aspect-ratio: 5 / 2; }
  .tile-72 { margin: -56px 0 0 8px; }
  .cab { padding: 10px 10px 12px; }
  .painel { padding: 12px; border-radius: 18px; }
  .direcao-cab { grid-template-columns: 1fr; gap: 8px; }
  .letra { font-size: 120px; }
  .grade18 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) {
  .card, .card-capa svg { transition: none; }
  .card:hover, .card:hover .card-capa svg { transform: none; }
}
`;

const ehPrincipal = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (ehPrincipal) {
  if (process.argv.includes('--icones')) {
    gerarIcones();
  } else {
    const saida = process.argv[2];
    if (!saida) {
      console.error('uso: node scripts/prancha-das-capas.mjs <saida.html>  |  --icones');
      process.exit(2);
    }
    const capas = await carregarCapas();
    const html = paginaDaPrancha(capas);
    fs.mkdirSync(path.dirname(path.resolve(saida)), { recursive: true });
    fs.writeFileSync(saida, html);
    const tamanhos = [];
    for (const slug of capas.SLUGS_DA_LOJA) for (const d of ['A', 'B', 'C']) for (const t of ['claro', 'escuro']) {
      tamanhos.push([`${d} ${slug} ${t}`, Buffer.byteLength(capas.capaSvg({ slug, direcao: d, tema: t }))]);
    }
    for (const d of ['A', 'B', 'C']) {
      const so = tamanhos.filter(([k]) => k.startsWith(d)).map(([, b]) => b);
      console.log(`direção ${d}: ${Math.min(...so)}–${Math.max(...so)} bytes por capa`);
    }
    console.log(`prancha gravada: ${saida} (${(Buffer.byteLength(html) / 1024).toFixed(0)} KB)`);
  }
}
