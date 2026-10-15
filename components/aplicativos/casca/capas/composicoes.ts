// SPEC-139 · L1 — as capas geradas em código: `capaSvg({ slug, direcao, tema })` devolve o <svg> inteiro de uma capa.
//
// TypeScript PURO (sem React, sem pacote em tempo de execução): o mesmo arquivo serve o produto (CapaGerada, fase 2) e a
// prancha (scripts/prancha-das-capas.mjs, que o Node 24 carrega direto).
//
// O sistema (SPEC-139 §3), igual nas três direções:
//   · tela 1600×900 (16:9), área segura de 80; o que IMPORTA (o ícone) fica dentro do miolo 4:1 — y 250..650 — que é o
//     recorte do cabeçalho da página do aplicativo (na B, ≥ 85 % do desenho em cada eixo: a direção é o ícone cortado);
//   · a cor vem SÓ da paleta (paleta.ts): mesma luminosidade e croma para todos, o claro e o escuro são a MESMA arte;
//   · o ícone lucide desenhado DENTRO do SVG (icones-svg.ts), traço 1.6 na grade 24;
//   · sem texto, sem emoji, sem imagem, sem requisição; DETERMINÍSTICA: tudo que varia vem do hash do slug.
//
// As direções:
//   A · Placa — o ícone numa placa de esmalte (degradê, brilho especular, borda clara, sombra colorida) com dois vidros atrás,
//               no terço esquerdo (à direita do tile que o cabeçalho sobrepõe); ondas concêntricas saindo da borda direita.
//   B · Traço — o ícone ampliado 3×, só linha, cortado pela borda direita, sobre a grade de construção do lucide e
//               uma malha de pontos acesa por uma luz.
//   C · Cena  — três peças do TRABALHO do aplicativo (documento, cartão, mensagem, calendário, gráfico, recibo, lista) em
//               perspectiva leve, e o ícone num selo. A ESCOLHIDA pelo Founder (15/10/2026) — e a única com
//               enquadramentos (card · cabecalho · destaque, `QUADROS_C` abaixo).

import { PALETA, tokensDaCapa, visualDaCapa, visualDoPedido, type Tema, type TokensDaCapa } from './paleta';
import { ICONES_SVG } from './icones-svg';

export type Direcao = 'A' | 'B' | 'C';

/**
 * A direção que o PRODUTO desenha (CapaGerada). SPEC-139 §3 / D-139-03: a prancha foi ao Founder; em 15/10/2026 ELE ESCOLHEU
 * a C · Cena (conserto B). Trocar de direção é mudar só esta linha.
 */
export const DIRECAO_DO_PRODUTO: Direcao = 'C';
export type { Tema };

export interface PedidoDaCapa {
  /** o aplicativo (a linha da paleta). Sem ele, vale o par icone + matiz do catálogo */
  slug?: string | null;
  icone?: string;
  matiz?: number;
  direcao: Direcao;
  tema: Tema;
  /** onde a capa aparece (só a C muda o quadro): card (padrão) · cabecalho · destaque */
  enquadramento?: Enquadramento;
}

export const LARGURA = 1600;
export const ALTURA = 900;
export const AREA_SEGURA = 80;
/** O miolo que sobra no cabeçalho 4:1 (1600×400, centrado). */
export const RECORTE_4_1 = { y0: 250, y1: 650 } as const;

// ── utilidades ──────────────────────────────────────────────────────────────────────────────────────────────────────

function hash(texto: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < texto.length; i += 1) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** Um gerador pseudoaleatório com semente (mulberry32): a mesma semente, a mesma sequência, sempre. */
function sorteio(semente: number): () => number {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Número curto: no máximo 1 casa, sem zero à esquerda nem à direita. */
const n = (x: number): string => {
  const s = String(Math.round(x * 10) / 10);
  return s.replace(/^(-?)0\./, '$1.');
};

const icone = (nome: string): string => ICONES_SVG[nome] ?? ICONES_SVG.LayoutGrid;

/** O ícone numa caixa quadrada (lado `lado`, canto superior esquerdo em x,y), com o traço na grade 24. */
function glifo(nome: string, x: number, y: number, lado: number, atributos: string, id = ''): string {
  return `<g${id ? ` id="${id}"` : ''} transform="translate(${n(x)} ${n(y)}) scale(${n(lado / 24)})" fill="none" stroke-linecap="round" stroke-linejoin="round" ${atributos}>${icone(nome)}</g>`;
}

const radial = (id: string, cx: number, cy: number, r: number, cor: string, op: number): string =>
  `<radialGradient id="${id}" cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" gradientUnits="userSpaceOnUse"><stop stop-color="${cor}" stop-opacity="${n(op)}"/><stop offset="1" stop-color="${cor}" stop-opacity="0"/></radialGradient>`;

const linear = (id: string, de: string, para: string, attrs = 'x2="0" y2="1"', opDe = 1, opPara = 1): string =>
  `<linearGradient id="${id}" ${attrs}><stop stop-color="${de}"${opDe < 1 ? ` stop-opacity="${n(opDe)}"` : ''}/><stop offset="1" stop-color="${para}"${opPara < 1 ? ` stop-opacity="${n(opPara)}"` : ''}/></linearGradient>`;

const TELA = `width="${LARGURA}" height="${ALTURA}"`;

/**
 * O grão fino (papel/filme): ruído em cinza, em luz suave. ⚠️ A frequência está em unidades do viewBox (1600 de
 * largura), então o grão CRESCE com o quadro: .2 dá ~1 ciclo por px no card (~320 px), mas no destaque e no cabeçalho
 * (~1400 px, retina) virava lixa grossa e manchada (juiz de design 139 R2, Galeria 1a). Por isso a frequência vem do
 * enquadramento (`QUADROS_C.grao`): o grão tem o mesmo tamanho NA TELA em todo lugar.
 */
const grao = (p: string, semente: number, frequencia = 0.2): string =>
  `<filter id="${p}g" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency="${n(frequencia)}" numOctaves="2" seed="${semente % 97}" stitchTiles="stitch"/><feColorMatrix values="0 0 0 9 -4 0 0 0 9 -4 0 0 0 9 -4 0 0 0 0 1"/></filter>`;
// no escuro, .035 (era .07: o overlay sobre fundo escuro pesa o dobro — o juiz viu o grão sujar o destaque)
const camadaDeGrao = (p: string, tema: Tema): string =>
  `<rect ${TELA} filter="url(#${p}g)" opacity="${tema === 'claro' ? '.05' : '.035'}" style="mix-blend-mode:overlay"/>`;

const desfoque = (id: string, d: number): string =>
  `<filter id="${id}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="${d}"/></filter>`;

/** Uma placa de esmalte: sombra colorida, degradê, brilho especular, sombra interna e borda clara de luz. */
function placa(p: string, k: string, x: number, y: number, lado: number, raio: number, t: TokensDaCapa, tema: Tema, circulo = false): { defs: string; corpo: string } {
  const forma = (dx = 0, dy = 0, extra = '', encolhe = 0) => circulo
    ? `<circle cx="${n(x + lado / 2 + dx)}" cy="${n(y + lado / 2 + dy)}" r="${n(lado / 2 - encolhe)}" ${extra}/>`
    : `<rect x="${n(x + dx + encolhe)}" y="${n(y + dy + encolhe)}" width="${n(lado - 2 * encolhe)}" height="${n(lado - 2 * encolhe)}" rx="${n(raio - encolhe)}" ${extra}/>`;
  const defs =
    linear(`${p}${k}t`, t.cor, t.forte, 'x1=".2" y1="0" x2=".7" y2="1"') +
    linear(`${p}${k}s`, '#fff', '#fff', 'x2="0" y2="1"', tema === 'claro' ? 0.5 : 0.48, 0) +
    linear(`${p}${k}e`, '#fff', '#fff', 'x2="0" y2="1"', tema === 'claro' ? 0.9 : 0.7, 0.1) +
    linear(`${p}${k}d`, '#000', '#000', 'x2="0" y2="1"', 0, tema === 'claro' ? 0.16 : 0.3) +
    `<clipPath id="${p}${k}c">${forma()}</clipPath>`;
  const cx = x + lado / 2;
  const corpo =
    forma(0, lado * 0.13, `fill="${t.sombra}" opacity="${tema === 'claro' ? '.42' : '.75'}" filter="url(#${p}b)"`) +
    forma(0, 0, `fill="url(#${p}${k}t)"`) +
    `<g clip-path="url(#${p}${k}c)"><ellipse cx="${n(cx - lado * 0.12)}" cy="${n(y - lado * 0.06)}" rx="${n(lado * 0.95)}" ry="${n(lado * 0.56)}" fill="url(#${p}${k}s)"/>` +
    `<rect x="${n(x)}" y="${n(y + lado * 0.62)}" width="${n(lado)}" height="${n(lado * 0.38)}" fill="url(#${p}${k}d)"/></g>` +
    forma(0, 0, `fill="none" stroke="url(#${p}${k}e)" stroke-width="${n(lado / 100)}"`, lado / 200);
  return { defs, corpo };
}

// ── A · Placa ───────────────────────────────────────────────────────────────────────────────────────────────────────

function direcaoA(p: string, nome: string, t: TokensDaCapa, tema: Tema, r: () => number, semente: number): string {
  const lado = 340;
  // 590: a placa fica à direita do tile do cabeçalho (que sobe 56 px sobre a capa no celular) — nunca um ícone
  // sobre o outro; no card, ela fica acima do tile sobreposto
  const cx = 590;
  const cy = 450;
  const x = cx - lado / 2;
  const y = cy - lado / 2;
  const oy = 450 + Math.round((r() - 0.5) * 120); // o centro das ondas
  const ox = 1660;
  const ax = 1080 + Math.round(r() * 360); // onde nasce a luz do segundo tom
  const ay = 40 + Math.round(r() * 160);
  const giro = 9 + Math.round(r() * 7);
  const raios = [250, 380, 510, 640, 770];
  const pl = placa(p, 'p', x, y, lado, 84, t, tema);
  const claro = tema === 'claro';
  // os vidros atrás da placa: dois planos em leque (profundidade), cada um mais longe e mais transparente
  const vidro = (k: number) =>
    `<rect x="${x}" y="${y}" width="${lado}" height="${lado}" rx="84" transform="rotate(${giro * k} ${cx} ${cy}) translate(${62 * k} ${-34 * k})" fill="${claro ? t.cor : t.vidro}" fill-opacity="${n((claro ? 0.26 : 0.5) / k)}" stroke="#fff" stroke-opacity="${n((claro ? 0.9 : 0.14) / k)}" stroke-width="2.5"/>`;
  return (
    `<defs>${linear(`${p}f`, t.fundo, t.fundo2, 'x1="0" y1="0" x2="1" y2="1"')}` +
    radial(`${p}h`, cx, cy, 620, t.cor, claro ? 0.55 : 0.72) +
    radial(`${p}l`, cx - 40, cy - 60, 260, t.luz, claro ? 0.6 : 0.5) +
    radial(`${p}k`, ax, ay, 760, t.acento, claro ? 0.7 : 0.5) +
    radial(`${p}m`, 1450, 860, 620, t.cor, claro ? 0.5 : 0.38) +
    radial(`${p}s`, ox, oy, raios[4], t.acento, claro ? 0.75 : 0.5) +
    `<linearGradient id="${p}o" x1="820" x2="1600" gradientUnits="userSpaceOnUse"><stop stop-color="${t.tinta}" stop-opacity="0"/><stop offset="1" stop-color="${t.tinta}" stop-opacity="${claro ? '.6' : '.55'}"/></linearGradient>` +
    desfoque(`${p}b`, 30) + pl.defs + grao(p, semente) + '</defs>' +
    `<rect ${TELA} fill="url(#${p}f)"/><rect ${TELA} fill="url(#${p}k)"/><rect ${TELA} fill="url(#${p}m)"/>` +
    // as ondas: um astro de luz nascendo da borda direita, com os anéis que somem para a esquerda
    `<circle cx="${ox}" cy="${oy}" r="${raios[4]}" fill="url(#${p}s)"/>` +
    `<g fill="none" stroke="url(#${p}o)" stroke-width="3.5">${raios.map((ra) => `<circle cx="${ox}" cy="${oy}" r="${ra}"/>`).join('')}</g>` +
    // o halo da cor atrás da placa, com um núcleo de luz
    `<rect ${TELA} fill="url(#${p}h)"/><rect ${TELA} fill="url(#${p}l)"/>` +
    vidro(2) + vidro(1) +
    pl.corpo +
    glifo(nome, cx - 85, cy - 85 + 6, 170, `stroke="${t.sombra}" stroke-opacity="${claro ? '.35' : '.6'}" stroke-width="1.6"`) +
    glifo(nome, cx - 85, cy - 85, 170, `stroke="${t.glifo}" stroke-width="1.6"`, `${p}i`) +
    camadaDeGrao(p, tema)
  );
}

// ── B · Traço ───────────────────────────────────────────────────────────────────────────────────────────────────────

function direcaoB(p: string, nome: string, t: TokensDaCapa, tema: Tema, r: () => number, semente: number): string {
  // 520 (3× o ícone da placa A): o desenho (2..22 da grade 24, com o traço) ocupa y 221..679 — no miolo 4:1 do cabeçalho
  // ficam 87 % da altura dele (a direção É o ícone cortado), no 5:2 do celular, 100 %; a borda direita corta ~11 %
  const lado = 520;
  const cx = 1420;
  const cy = 450;
  const x = cx - lado / 2;
  const y = cy - lado / 2;
  const claro = tema === 'claro';
  const lx = 300 + Math.round(r() * 260); // a segunda luz, do lado vazio
  const ly = 120 + Math.round(r() * 120);
  const passo = 40;
  return (
    `<defs>${linear(`${p}f`, t.fundo, t.fundo2, 'x1="0" y1="0" x2=".8" y2="1"')}` +
    radial(`${p}h`, cx - 60, cy, 760, t.cor, claro ? 0.55 : 0.5) +
    radial(`${p}k`, lx, ly, 640, t.acento, claro ? 0.4 : 0.3) +
    radial(`${p}q`, cx - 120, cy, 820, '#fff', 1) +
    radial(`${p}t`, cx - 30, cy, 400, claro ? t.luz : t.cor, claro ? 0.85 : 0.4) +
    `<mask id="${p}m"><rect ${TELA} fill="url(#${p}q)"/></mask>` +
    `<pattern id="${p}p" width="${passo}" height="${passo}" patternUnits="userSpaceOnUse"><circle cx="${passo / 2}" cy="${passo / 2}" r="2.4" fill="${t.tinta}"/></pattern>` +
    `<pattern id="${p}r" width="1" height="1" patternUnits="userSpaceOnUse"><path d="M1 0H0V1" fill="none" stroke="${t.tinta}" stroke-width=".03"/></pattern>` +
    `<linearGradient id="${p}l" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse"><stop stop-color="${t.traco2}"/><stop offset="1" stop-color="${t.traco1}"/></linearGradient>` +
    desfoque(`${p}b`, 0.55) + grao(p, semente) + '</defs>' +
    `<rect ${TELA} fill="url(#${p}f)"/><rect ${TELA} fill="url(#${p}k)"/><rect ${TELA} fill="url(#${p}h)"/>` +
    `<rect ${TELA} fill="url(#${p}p)" opacity="${claro ? '.2' : '.2'}"/>` +
    `<rect ${TELA} fill="url(#${p}p)" opacity="${claro ? '.5' : '.55'}" mask="url(#${p}m)"/>` +
    // a mesa de luz sob o desenho
    `<rect ${TELA} fill="url(#${p}t)"/>` +
    // a prancheta do desenhista: as guias que atravessam a tela e a grade de construção do lucide (24, keylines)
    `<path d="M0 ${cy}H${LARGURA}M${cx} 0V${ALTURA}" stroke="${t.tinta}" stroke-opacity="${claro ? '.22' : '.2'}" stroke-width="2" stroke-dasharray="2 10"/>` +
    `<g transform="translate(${x} ${y}) scale(${n(lado / 24)})" fill="none" stroke="${t.tinta}" stroke-opacity="${claro ? '.3' : '.28'}" stroke-width=".06">` +
    `<rect width="24" height="24" fill="url(#${p}r)" stroke="none" opacity=".55"/><circle cx="12" cy="12" r="10"/><rect x="3" y="3" width="18" height="18" rx="2"/><rect x="2" y="4" width="20" height="16" rx="2"/><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M0 0l24 24M24 0L0 24"/></g>` +
    // o decalque: o mesmo traço, deslocado e fino, como o lápis embaixo da tinta (o segundo plano)
    glifo(nome, x - 34, y + 30, lado, `stroke="${t.tinta}" stroke-width=".35" opacity="${claro ? '.35' : '.3'}"`) +
    glifo(nome, x, y, lado, `stroke="${t.cor}" stroke-width="2.6" opacity="${claro ? '.55' : '.75'}" filter="url(#${p}b)"`) +
    glifo(nome, x, y, lado, `stroke="url(#${p}l)" stroke-width="1.1"`, `${p}i`) +
    camadaDeGrao(p, tema)
  );
}

// ── C · Cena ────────────────────────────────────────────────────────────────────────────────────────────────────────

export type Peca = 'documento' | 'cartao' | 'bolha' | 'calendario' | 'grafico' | 'recibo' | 'lista';

/**
 * As três peças do trabalho de cada aplicativo (o fundo, o meio, a frente) — o que ele FAZ, em objetos. No card (pequeno)
 * só entram as duas da FRENTE (meio e frente), maiores: a cena que se lê a 300 px. Conserto B: a Renovação mostra a
 * apresentação sobre o calendário de vencimentos; o Checklist, a lista do dia sobre o calendário; o Follow-up e as
 * Tarefas, o lembrete no calendário; o Radar, a norma e o aviso; o Resumo, a conversa e a lista do que
 * ficou pendente. 📊 Dois cards vizinhos nunca repetem o par (capas.test.mjs, 5b).
 */
export const CENA: Readonly<Record<string, [Peca, Peca, Peca]>> = {
  renovacao: ['grafico', 'calendario', 'documento'],
  'renovacao-maxima': ['grafico', 'calendario', 'documento'],
  'cobranca-feita': ['cartao', 'recibo', 'bolha'],
  'checklist-6h': ['bolha', 'calendario', 'lista'],
  'sinistralidade-avancada': ['documento', 'lista', 'grafico'],
  'follow-up-whatsapp': ['lista', 'calendario', 'bolha'],
  'radar-mercado-regulacao': ['grafico', 'documento', 'bolha'],
  'resumo-atendimentos': ['documento', 'bolha', 'lista'],
  'tarefas-agendadas': ['bolha', 'lista', 'calendario'],
  cotacao: ['documento', 'recibo', 'grafico'],
  'quem-cobra-menos': ['cartao', 'recibo', 'grafico'],
  'caca-comissao': ['grafico', 'cartao', 'recibo'],
  'carteira-blindada': ['grafico', 'cartao', 'documento'],
  'clientes-perdidos': ['cartao', 'lista', 'bolha'],
  'contabilidade-pronta': ['grafico', 'documento', 'recibo'],
  'digitacao-zero': ['cartao', 'lista', 'documento'],
  'organizacao-completa': ['documento', 'calendario', 'lista'],
  'protecao-completa': ['lista', 'cartao', 'documento'],
  'resgatar-cliente': ['calendario', 'cartao', 'bolha'],
};
export const CENA_PADRAO: [Peca, Peca, Peca] = ['documento', 'lista', 'grafico'];

const TAMANHO: Record<Peca, [number, number]> = {
  documento: [240, 300], cartao: [340, 212], bolha: [330, 150], calendario: [260, 250], grafico: [340, 224],
  recibo: [220, 296], lista: [290, 232],
};

/** O desenho de uma peça em coordenadas locais (0,0 = canto superior esquerdo), sem a sombra. */
function peca(tipo: Peca, p: string, t: TokensDaCapa, tema: Tema): string {
  const claro = tema === 'claro';
  const [w, h] = TAMANHO[tipo];
  // Juiz de design 139 R2 (Galeria 1d): no escuro, `forte` (L .41) sobre a peça (L ~.36) sumia — o traço do gráfico
  // "azul-escuro sobre ardósia". No escuro o TRAÇO vai na luz do aplicativo e a MARCA (o disco do visto, o dia marcado)
  // na cor dele; no claro, nada muda. Só a cor troca: a geometria dos dois temas segue a mesma (capas.test.mjs, 4).
  const traco = claro ? t.forte : t.luz;
  const marca = claro ? t.forte : t.cor;
  const borda = `stroke="#fff" stroke-opacity="${claro ? '.95' : '.3'}" stroke-width="2"`;
  const base = (extra = '') => `<rect width="${w}" height="${h}" rx="22" fill="url(#${p}v)" ${borda}${extra}/>`;
  const linhas = (d: string, op = claro ? 0.2 : 0.42, larg = 10) =>
    `<path d="${d}" stroke="${t.tinta}" stroke-opacity="${n(op)}" stroke-width="${larg}" stroke-linecap="round" fill="none"/>`;
  const visto = (d: string, cor: string, larg = 6) =>
    `<path d="${d}" fill="none" stroke="${cor}" stroke-width="${larg}" stroke-linecap="round" stroke-linejoin="round"/>`;
  switch (tipo) {
    case 'documento':
      return base() + `<rect x="28" y="30" width="112" height="16" rx="8" fill="${t.cor}"/>` +
        linhas('M33 80h174M33 106h150M33 132h174M33 158h112') +
        `<circle cx="178" cy="240" r="30" fill="${marca}"/>` + visto('M165 240l9 9 17-19', t.glifo);
    case 'cartao':
      return `<rect width="${w}" height="${h}" rx="24" fill="url(#${p}pt)"/>` +
        `<path d="M0 150L230 0h60L0 190z" fill="#fff" opacity=".1"/>` +
        `<rect x="30" y="58" width="54" height="40" rx="9" fill="${t.acento}"/>` +
        `<path d="M36 150h150M36 176h86" stroke="#fff" stroke-opacity=".6" stroke-width="12" stroke-linecap="round"/>` +
        `<circle cx="266" cy="166" r="24" fill="#fff" opacity=".42"/><circle cx="292" cy="166" r="24" fill="#fff" opacity=".22"/>` +
        `<rect x="1" y="1" width="${w - 2}" height="${h - 2}" rx="23" fill="none" ${borda} stroke-opacity="${claro ? '.5' : '.32'}"/>`;
    case 'bolha':
      return `<path d="M24 0h282a24 24 0 0 1 24 24v78a24 24 0 0 1-24 24H62l-34 24 6-24h-10A24 24 0 0 1 0 102V24A24 24 0 0 1 24 0z" fill="url(#${p}v)" ${borda}/>` +
        `<circle cx="50" cy="56" r="24" fill="${t.cor}"/>` + linhas('M94 44h190M94 72h120') +
        visto('M246 100l8 8 14-16M262 108l14-16', traco, 5);
    case 'calendario': {
      let celulas = '';
      for (let j = 0; j < 3; j += 1) for (let i = 0; i < 4; i += 1) if (!(i === 2 && j === 1)) celulas += `M${26 + i * 54} ${86 + j * 50}h42v34h-42z`;
      return base() + `<path d="M0 22a22 22 0 0 1 22-22h216a22 22 0 0 1 22 22v40H0z" fill="${t.cor}"/>` +
        `<path d="M72 -12v32M188 -12v32" stroke="${t.forte}" stroke-width="12" stroke-linecap="round"/>` +
        `<path d="${celulas}" fill="${t.tinta}" opacity="${claro ? '.1' : '.26'}"/>` +
        `<rect x="134" y="136" width="42" height="34" rx="6" fill="${marca}"/>`;
    }
    case 'grafico':
      return base() + linhas('M26 188h288M26 140h288M26 92h288', claro ? 0.1 : 0.22, 2) +
        `<path d="M26 170L84 132L142 148L200 98L258 112L314 58V188H26z" fill="url(#${p}pa)"/>` +
        `<path d="M26 170L84 132L142 148L200 98L258 112L314 58" fill="none" stroke="${traco}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>` +
        `<circle cx="314" cy="58" r="20" fill="${t.cor}" opacity=".35"/><circle cx="314" cy="58" r="9" fill="${traco}"/>`;
    case 'recibo': {
      let serra = `M0 22a22 22 0 0 1 22-22h176a22 22 0 0 1 22 22V${h}`;
      for (let i = 0; i < 11; i += 1) serra += `l-10 -14l-10 14`;
      serra += 'z';
      return `<path d="${serra}" fill="url(#${p}v)" ${borda}/>` +
        linhas('M30 44h96M30 86h160M30 112h130M30 138h160') +
        `<rect x="30" y="176" width="160" height="34" rx="10" fill="${t.cor}" opacity=".9"/>` +
        `<circle cx="174" cy="244" r="20" fill="${marca}"/>` + visto('M165 244l6 6 12-13', t.glifo, 5);
    }
    case 'lista':
    default:
      return base() +
        `<circle cx="46" cy="54" r="17" fill="${marca}"/>` + visto('M38 54l6 6 11-12', t.glifo, 5) +
        `<circle cx="46" cy="116" r="17" fill="${marca}"/>` + visto('M38 116l6 6 11-12', t.glifo, 5) +
        `<circle cx="46" cy="178" r="15" fill="none" stroke="${t.tinta}" stroke-opacity=".35" stroke-width="4"/>` +
        linhas('M84 54h170M84 116h130M84 178h150');
  }
}

/**
 * Os ENQUADRAMENTOS da C (conserto B da SPEC-139, D-139-CB-02): a mesma cena, montada para o lugar onde ela aparece.
 *   card      — o card da loja (16:9, ~300 px): o selo maior (o tile saiu do card) e SÓ as duas peças da frente,
 *               grandes — a cena que se lê pequena (a prancha mostrou três peças embaralhadas no card);
 *   cabecalho — o topo da página (4:1 no computador = y 250..650; 5:2 no celular): selo e as três peças DENTRO da
 *               faixa, com a sombra — nada corta;
 *   destaque  — a vitrine do topo da loja: o selo e a cena à DIREITA, a esquerda limpa para o texto. O SVG ancora à
 *               direita (`xMaxYMid`): no celular (4:3) o corte come a esquerda vazia, nunca a cena.
 * Cada lugar: [centro x, centro y, escala] da peça; o selo: centro e lado.
 */
export type Enquadramento = 'card' | 'cabecalho' | 'destaque';

interface QuadroDaCena {
  selo: { cx: number; cy: number; lado: number };
  /** [x, y, escala] — com duas entradas, entram só as peças do meio e da frente */
  lugares: Array<[number, number, number]>;
  /** a luz da cena (o segundo tom) e o chão */
  luz: [number, number];
  chao: [number, number, number];
  /** a frequência do grão (por unidade do viewBox): proporcional à largura com que o quadro aparece na tela */
  grao: number;
}

const QUADROS_C: Readonly<Record<Enquadramento, QuadroDaCena>> = {
  card: { selo: { cx: 480, cy: 420, lado: 320 }, lugares: [[1060, 345, 1.45], [1310, 535, 1.5]], luz: [1150, 760], chao: [1190, 720, 420], grao: 0.2 },
  cabecalho: { selo: { cx: 520, cy: 450, lado: 220 }, lugares: [[1010, 430, 0.76], [1240, 445, 0.8], [1455, 455, 0.72]], luz: [1200, 760], chao: [1230, 610, 440], grao: 0.7 },
  destaque: { selo: { cx: 900, cy: 450, lado: 280 }, lugares: [[1215, 355, 0.88], [1435, 490, 0.94], [1175, 560, 0.86]], luz: [1250, 800], chao: [1260, 700, 380], grao: 0.7 },
};

function direcaoC(p: string, slug: string, nome: string, t: TokensDaCapa, tema: Tema, r: () => number, semente: number, enquadramento: Enquadramento): string {
  const claro = tema === 'claro';
  const q = QUADROS_C[enquadramento] ?? QUADROS_C.card;
  const { cx, cy, lado } = q.selo;
  const todas = CENA[slug] ?? CENA_PADRAO;
  // com dois lugares, as duas peças da FRENTE (meio e frente): o que o aplicativo entrega, sem o pano de fundo
  const pecas = q.lugares.length === 2 ? todas.slice(1) : todas;
  // cada peça leva a mesma perspectiva leve em torno do próprio centro — o plano "deitado" para trás, como cartas
  // sobre uma mesa de luz
  const jitter = () => Math.round((r() - 0.5) * 28);
  let cena = '';
  for (let i = 0; i < pecas.length; i += 1) {
    const [lx, ly, s] = q.lugares[i];
    const [w, h] = TAMANHO[pecas[i]];
    cena += `<g transform="translate(${lx + jitter()} ${ly + jitter()}) matrix(.97 -.16 .1 .96 0 0) scale(${s}) translate(${-w / 2} ${-h / 2})">` +
      `<rect x="14" y="36" width="${w}" height="${h}" rx="24" fill="${t.sombra}" opacity="${claro ? '.3' : '.62'}" filter="url(#${p}b)"/>` +
      peca(pecas[i], p, t, tema) + '</g>';
  }
  const pl = placa(p, 's', cx - lado / 2, cy - lado / 2, lado, lado / 2, t, tema, true);
  // o ícone ocupa ~49 % do disco (128 em 260, a proporção da prancha)
  const g = Math.round(lado * 0.49);
  const [chx, chy, chr] = q.chao;
  return (
    `<defs>${linear(`${p}f`, t.fundo, t.fundo2, 'x1="0" y1="0" x2="1" y2="1"')}` +
    radial(`${p}h`, cx, cy, lado * 1.6, claro ? t.luz : t.cor, claro ? 0.75 : 0.5) +
    radial(`${p}k`, q.luz[0], 120 + Math.round(r() * 200), q.luz[1], t.acento, claro ? 0.55 : 0.5) +
    // no escuro, uma luz da cor do aplicativo ATRÁS das peças: o vidro sai do fundo (antes ficava abafado)
    radial(`${p}m`, chx, chy - 220, chr * 1.5, claro ? t.cor : t.luz, claro ? 0.35 : 0.22) +
    linear(`${p}pt`, t.cor, t.forte, 'x1="0" y1="0" x2="1" y2="1"') +
    linear(`${p}pa`, t.cor, t.cor, 'x2="0" y2="1"', 0.55, 0) +
    linear(`${p}v`, t.peca, t.peca2) +
    desfoque(`${p}b`, 24) + pl.defs + grao(p, semente, q.grao) + '</defs>' +
    `<rect ${TELA} fill="url(#${p}f)"/><rect ${TELA} fill="url(#${p}k)"/><rect ${TELA} fill="url(#${p}m)"/><rect ${TELA} fill="url(#${p}h)"/>` +
    // o grão SÓ no fundo (juiz de design 139 R2, Galeria 1b): por cima de tudo, ele manchava a medalha e as peças
    camadaDeGrao(p, tema) +
    // o chão da cena: uma elipse de sombra sob as peças
    `<ellipse cx="${chx}" cy="${chy}" rx="${chr}" ry="60" fill="${t.sombra}" opacity="${claro ? '.05' : '.2'}" filter="url(#${p}b)"/>` +
    cena +
    // o selo: um anel de vidro (com borda de luz também no escuro) e o disco de esmalte com o ícone
    `<circle cx="${cx}" cy="${cy}" r="${Math.round(lado * 0.62)}" fill="${t.vidro}" fill-opacity="${claro ? '.55' : '.5'}" stroke="#fff" stroke-opacity="${claro ? '.95' : '.3'}" stroke-width="2"/>` +
    pl.corpo +
    glifo(nome, cx - g / 2, cy - g / 2 + 5, g, `stroke="${t.sombra}" stroke-opacity="${claro ? '.35' : '.6'}" stroke-width="1.6"`) +
    glifo(nome, cx - g / 2, cy - g / 2, g, `stroke="${t.glifo}" stroke-width="1.6"`, `${p}i`)
  );
}

// ── a entrada ───────────────────────────────────────────────────────────────────────────────────────────────────────

/** O <svg> inteiro da capa. Mesmo pedido → mesmos bytes (o teste confere). */
export function capaSvg({ slug, icone: iconePedido, matiz, direcao, tema, enquadramento = 'card' }: PedidoDaCapa): string {
  // com slug: a linha da tabela. Sem slug: o par ícone + matiz do catálogo (a mesma capa sempre para o mesmo par)
  // (um slug que a tabela ainda não conhece também cai no par: o aplicativo novo ganha a cor do laudo, não a padrão)
  const porSlug = slug ? visualDaCapa(slug) : null;
  // a regra mora em `visualDoPedido` (paleta.ts): a MESMA que o tile do ícone usa — capa e tile nunca discordam
  const visual = visualDoPedido({ slug, icone: iconePedido, matiz });
  // o par que É uma linha da tabela vira aquele aplicativo (a mesma capa, com ou sem slug)
  const daTabela = (porSlug === visual ? slug : null) || Object.keys(PALETA).find((k) => PALETA[k] === visual);
  const chave = daTabela || slug || `${visual.icone}|${visual.matiz}`;
  const t = tokensDaCapa(visual.h, tema);
  const semente = hash(chave);
  const r = sorteio(semente);
  // só a C tem enquadramentos; A e B desenham sempre o mesmo quadro
  const quadro: Enquadramento = direcao === 'C' && enquadramento in QUADROS_C ? enquadramento : 'card';
  // o prefixo dos ids: único por capa E por enquadramento, para várias capas conviverem na mesma página (a Renovação
  // aparece no destaque e no card ao mesmo tempo)
  const p = `c${hash(`${chave}|${direcao}|${tema}${quadro === 'card' ? '' : `|${quadro}`}`).toString(36)}`;
  const corpo =
    direcao === 'A' ? direcaoA(p, visual.icone, t, tema, r, semente)
      : direcao === 'B' ? direcaoB(p, visual.icone, t, tema, r, semente)
        : direcaoC(p, daTabela ?? '', visual.icone, t, tema, r, semente, quadro);
  const ancora = quadro === 'destaque' ? 'xMaxYMid' : 'xMidYMid';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${LARGURA} ${ALTURA}" preserveAspectRatio="${ancora} slice" aria-hidden="true" focusable="false">${corpo}</svg>`;
}
