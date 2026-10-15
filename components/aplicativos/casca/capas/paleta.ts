// SPEC-139 · L1 — a paleta das capas: UMA tabela, slug → ícone + matiz → as cores de cada tema.
//
// O laudo de design (131/DESIGN-DO-PADRAO-DE-APLICATIVO.md §2.4) deu a cada aplicativo um ícone lucide e uma matiz HSL
// (`APLICATIVO_VISUAL` em lib/auxiliaries/catalog.ts). Aqui essa matiz vira uma matiz OKLCH (`h`): o espaço em que
// luminosidade e croma iguais PARECEM iguais ao olho — nenhum aplicativo "grita" mais que o vizinho.
//
// ⚠️ Por que `h` não é a matiz do laudo convertida (decisão D-139-L1-01, nota 86 × conversão literal 58):
//    as matizes do laudo são 17 frias espremidas em 112° (150–262) — oito delas entre 185° e 215°. Convertidas literalmente,
//    a grade dos 18 seria oito azuis-petróleo quase iguais. A tabela abaixo PRESERVA A ORDEM do laudo (o verde continua
//    verde, o violeta continua violeta, o âmbar continua sozinho) e espalha as frias em passos iguais de 9,5° no arco
//    148°–300° do OKLCH. 📊 Em ordem alfabética de slug (a ordem da galeria dentro de um mesmo estado), vizinhos ficam a
//    ≥ 19° (o teste `capas.test.mjs` mede).
// ⚠️ Os valores são LITERAIS de propósito: um aplicativo novo ganha a sua linha sem mexer na cor de nenhum outro
//    (a mesma capa hoje e daqui a um ano).

export type Tema = 'claro' | 'escuro';

export interface VisualDaCapa {
  /** o nome do ícone lucide (o mesmo de APLICATIVO_VISUAL) */
  icone: string;
  /** a matiz HSL do laudo §2.4 — referência; quem desenha usa `h` */
  matiz: number;
  /** a matiz OKLCH da capa */
  h: number;
}

/** A tabela única. `renovacao-maxima` saiu da vitrine (migration 20261014_01) e herda a Renovação. */
export const PALETA: Readonly<Record<string, VisualDaCapa>> = {
  'caca-comissao':           { icone: 'HandCoins',           matiz: 150, h: 148 },
  'carteira-blindada':       { icone: 'ShieldCheck',         matiz: 205, h: 234 },
  'checklist-6h':            { icone: 'Sunrise',             matiz: 38,  h: 58 },
  'clientes-perdidos':       { icone: 'UserSearch',          matiz: 230, h: 272 },
  'cobranca-feita':          { icone: 'ReceiptText',         matiz: 158, h: 158 },
  'contabilidade-pronta':    { icone: 'BookOpenCheck',       matiz: 175, h: 177 },
  cotacao:                   { icone: 'Calculator',          matiz: 195, h: 205 },
  'digitacao-zero':          { icone: 'ScanText',            matiz: 225, h: 262 },
  'follow-up-whatsapp':      { icone: 'MessageSquareReply',  matiz: 200, h: 215 },
  'organizacao-completa':    { icone: 'FolderCheck',         matiz: 185, h: 186 },
  'protecao-completa':       { icone: 'Umbrella',            matiz: 210, h: 243 },
  'quem-cobra-menos':        { icone: 'BadgePercent',        matiz: 165, h: 167 },
  'radar-mercado-regulacao': { icone: 'Radar',               matiz: 262, h: 300 },
  renovacao:                 { icone: 'RefreshCcwDot',       matiz: 203, h: 224 },
  'resgatar-cliente':        { icone: 'UserRoundCheck',      matiz: 250, h: 291 },
  'resumo-atendimentos':     { icone: 'ScrollText',          matiz: 215, h: 253 },
  'sinistralidade-avancada': { icone: 'ChartNoAxesCombined', matiz: 240, h: 281 },
  'tarefas-agendadas':       { icone: 'CalendarClock',       matiz: 188, h: 196 },
};

const APELIDOS: Readonly<Record<string, string>> = { 'renovacao-maxima': 'renovacao' };

/** O aplicativo que ainda não está na tabela: o ícone padrão e uma matiz neutra fria (o VISUAL_PADRAO do catálogo). */
export const VISUAL_PADRAO_DA_CAPA: VisualDaCapa = { icone: 'LayoutGrid', matiz: 205, h: 230 };

/** Os slugs que aparecem na loja, em ordem alfabética (a ordem da grade dos 18). */
export const SLUGS_DA_LOJA: readonly string[] = Object.keys(PALETA).sort();

export function visualDaCapa(slug: string): VisualDaCapa {
  return PALETA[APELIDOS[slug] ?? slug] ?? VISUAL_PADRAO_DA_CAPA;
}

/**
 * Sem slug (quem chama só tem o ícone e a matiz do catálogo): o aplicativo da tabela com o MESMO ícone e a MESMA matiz;
 * se não houver, a matiz do laudo vira matiz de capa pela mesma régua da tabela (interpolação entre os pontos dela,
 * na ordem), e o ícone fica o pedido. Determinístico: o mesmo par dá sempre a mesma cor.
 */
export function visualPorIconeEMatiz(icone: string, matiz: number): VisualDaCapa {
  const m = Number.isFinite(matiz) ? ((Math.round(matiz) % 360) + 360) % 360 : VISUAL_PADRAO_DA_CAPA.matiz;
  for (const v of Object.values(PALETA)) if (v.icone === icone && v.matiz === m) return v;
  const pontos = Object.values(PALETA).filter((v) => v.matiz > 120).map((v) => [v.matiz, v.h] as const)
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let h: number;
  if (m <= 120) h = PALETA['checklist-6h'].h; // a única quente da tabela: toda quente nova vira âmbar
  else if (m <= pontos[0][0]) h = pontos[0][1];
  else if (m >= pontos[pontos.length - 1][0]) h = pontos[pontos.length - 1][1];
  else {
    const i = pontos.findIndex(([x]) => x >= m);
    const [x0, y0] = pontos[i - 1];
    const [x1, y1] = pontos[i];
    h = x1 === x0 ? y1 : Math.round(y0 + ((m - x0) * (y1 - y0)) / (x1 - x0));
  }
  return { icone: icone || VISUAL_PADRAO_DA_CAPA.icone, matiz: m, h };
}

/**
 * A linha da paleta de UM pedido — a regra única que a capa (`capaSvg`) e o tile do ícone (`estiloDoTile`) usam, para
 * os dois nunca discordarem (SPEC-139 · costura L6): com slug conhecido, a linha do slug; sem slug (ou um slug que a
 * tabela ainda não conhece, quando o pedido traz o ícone), o par ícone + matiz do catálogo.
 */
export function visualDoPedido(pedido: { slug?: string | null; icone?: string; matiz?: number }): VisualDaCapa {
  const porSlug = pedido.slug ? visualDaCapa(pedido.slug) : null;
  return porSlug && (porSlug !== VISUAL_PADRAO_DA_CAPA || pedido.icone === undefined)
    ? porSlug
    : visualPorIconeEMatiz(pedido.icone ?? '', pedido.matiz ?? Number.NaN);
}

// ── as cores ────────────────────────────────────────────────────────────────────────────────────────────────────────
// Cada papel tem UMA luminosidade (L) e UM croma (C) por tema, iguais para todos os aplicativos; só a matiz muda
// (`dh` desloca a matiz para o segundo tom do degradê). O claro e o escuro são a MESMA arte com outra tabela.

export interface TokensDaCapa {
  /** o fundo e o fim do degradê do fundo */
  fundo: string; fundo2: string;
  /** a luz (halo, brilho) */
  luz: string;
  /** a cor do aplicativo, a mais funda e o segundo tom */
  cor: string; forte: string; acento: string;
  /** linhas finas, pontos, texto falso das cenas */
  tinta: string;
  /** a sombra colorida */
  sombra: string;
  /** a placa de vidro (cartões das cenas): o alto e a base do degradê */
  vidro: string; vidro2: string;
  /** o desenho do ícone sobre a placa */
  glifo: string;
  /** as duas pontas do traço grande (direção B) */
  traco1: string; traco2: string;
}

type Papel = keyof TokensDaCapa;
type Receita = Record<Papel, [L: number, C: number, dh?: number]>;

const RECEITAS: Record<Tema, Receita> = {
  claro: {
    fundo: [0.955, 0.035], fundo2: [0.885, 0.07, 32], luz: [0.995, 0.012],
    cor: [0.72, 0.13], forte: [0.53, 0.14], acento: [0.8, 0.11, 40],
    tinta: [0.47, 0.1], sombra: [0.42, 0.12], vidro: [0.995, 0.006], vidro2: [0.955, 0.022],
    glifo: [1, 0], traco1: [0.44, 0.13], traco2: [0.6, 0.15, 40],
  },
  escuro: {
    fundo: [0.25, 0.06], fundo2: [0.16, 0.045, 32], luz: [0.76, 0.14],
    cor: [0.62, 0.13], forte: [0.41, 0.11], acento: [0.56, 0.12, 40],
    tinta: [0.84, 0.07], sombra: [0.09, 0.025], vidro: [0.41, 0.05], vidro2: [0.3, 0.04],
    glifo: [0.985, 0.015], traco1: [0.93, 0.06], traco2: [0.72, 0.14, 40],
  },
};

/** OKLCH → sRGB (0–1, sem limitar). Björn Ottosson, "A perceptual color space for image processing" (2020). */
function oklchParaRgb(L: number, C: number, h: number): [number, number, number] {
  const a = C * Math.cos((h * Math.PI) / 180);
  const b = C * Math.sin((h * Math.PI) / 180);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  return lin.map((v) => (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055)) as [number, number, number];
}

const DENTRO = (rgb: number[]) => rgb.every((v) => v >= -0.0005 && v <= 1.0005);

/**
 * A cor em hex. Se o croma pedido sai do sRGB naquela matiz (o ciano escuro, por exemplo), o croma DESCE até caber —
 * a luminosidade e a matiz nunca mudam (nada de "cortar o canal", que entorta a matiz).
 */
export function oklchHex(L: number, C: number, h: number): string {
  let c = C;
  let rgb = oklchParaRgb(L, c, h);
  if (!DENTRO(rgb)) {
    let lo = 0;
    let hi = C;
    for (let i = 0; i < 24; i += 1) {
      c = (lo + hi) / 2;
      if (DENTRO(oklchParaRgb(L, c, h))) lo = c;
      else hi = c;
    }
    c = lo;
    rgb = oklchParaRgb(L, c, h);
  }
  return `#${rgb.map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, '0')).join('')}`;
}

export function tokensDaCapa(h: number, tema: Tema): TokensDaCapa {
  const receita = RECEITAS[tema];
  const saida = {} as TokensDaCapa;
  // o segundo tom anda para o lado FRIO (+) — exceto nas matizes quentes (< 120°), onde +40 cairia no verde-oliva
  // (medido na prancha: o âmbar virava lodo no escuro); ali ele anda para o laranja (−)
  const sentido = h < 120 ? -1 : 1;
  for (const papel of Object.keys(receita) as Papel[]) {
    const [L, C, dh = 0] = receita[papel];
    // e nas quentes os tons ESCUROS andam mais 8° para o vermelho (como o pintor faz): o âmbar escuro em OKLCH ~60°
    // é marrom-oliva; em ~50°, é cobre
    const desvio = sentido < 0 && L < 0.6 ? -8 : 0;
    saida[papel] = oklchHex(L, C, (h + sentido * dh + desvio + 360) % 360);
  }
  return saida;
}
