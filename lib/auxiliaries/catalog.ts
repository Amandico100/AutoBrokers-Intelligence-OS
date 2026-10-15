// SPEC-064 Bloco C/D — o leitor ÚNICO do catálogo de Auxiliares.
//
// Existe um catálogo GLOBAL, e ele é o mesmo para todas as corretoras: Resulta,
// AutoFleet, Amandus e as próximas. O que muda por corretora são três coisas,
// e só elas:
//
//     1. quais ela LIGOU              (tenant_auxiliaries)
//     2. quais CONEXÕES ela tem       (tenant_connections + portal_accounts + integrations)
//     3. como ela PERSONALIZOU        (tenant_auxiliaries.config — Bloco F)
//
// A regra que o Founder cravou em 02/08/2026, e que este arquivo implementa:
//
//   "Se o portal da Allianz estiver conectado, ele deve servir para QUALQUER
//    auxiliar que precisar de acesso ao portal da Allianz, e não ter que fazer
//    novamente a conexão em cada auxiliar."
//
// Por isso a prontidão de conexão é calculada UMA VEZ por corretora e aplicada
// a todos os Auxiliares. Conectar é ato da corretora, não do Auxiliar.
//
// Server-only: usa service role.
import type { SupabaseClient } from '@supabase/supabase-js';

export type EstadoCatalogo = 'available' | 'coming_soon';

/** Como o corretor vê o Auxiliar agora. É derivado, nunca gravado. */
export type EstadoDoCard =
  | 'ligado'            // instalado e trabalhando
  | 'pausado'           // instalado, o corretor pausou
  | 'falta_conectar'    // pode ligar, mas depende de conexão que ela não tem
  | 'disponivel'        // pode ligar agora
  | 'em_breve';         // ainda não existe

export interface ConectorPendente {
  slug: string;
  nome: string;
  /** Onde o corretor resolve isso. */
  onde: string;
}

export interface TarefaDoAuxiliar {
  tarefa: string;
  frequencia: string;
}

/**
 * SPEC-131-B — uma conexão que o aplicativo usa, com NOME HUMANO (nunca o slug cru).
 * Conector de plataforma (Firecrawl, conversas internas) não entra: a AutoBrokers paga, a corretora não vê.
 */
export interface ConexaoDoAplicativo {
  slug: string;
  nome: string;
  /** true = conectado · false = falta · null = não deu para conferir agora */
  pronto: boolean | null;
  onde: string | null;
}

/** SPEC-131-B — a prova REAL do card: número medido no banco desta corretora, ou nada (D-131-26). */
export interface ProvaDoAplicativo {
  /** execuções em `routine_runs` das rotinas deste aplicativo, nesta corretora */
  execucoes: number;
  /** a mais recente de `routine_runs.started_at` (ou `last_run_at`, o que for mais novo) */
  ultima_execucao: string | null;
  /** Renovação: renovações que viraram `calculada` neste mês (renovacao_eventos); null = não se aplica */
  renovacoes_no_mes: number | null;
}

export interface DuvidaDoAplicativo {
  pergunta: string;
  resposta: string;
}

export interface ItemDoCatalogo {
  template_id: string;
  slug: string;
  nome: string;
  headline: string | null;
  categorias: string[];
  estado_catalogo: EstadoCatalogo;
  estado: EstadoDoCard;
  /** O que ele faz, com a frequência de cada tarefa. */
  o_que_faz: TarefaDoAuxiliar[];
  /** O que o corretor ganha — em número, ou o que será medido. */
  promessa: string | null;
  /** Transparência: de onde ele tira a informação. */
  fontes: string[];
  /** Só para 'em_breve': o que falta para existir. */
  falta_para_existir: string | null;
  descricao: string | null;
  resumo: string | null;
  /** Conexões que ele exige e que ESTA corretora ainda não tem. */
  conectores_pendentes: ConectorPendente[];
  /** Conexões que ele exige e que ela já tem — compartilhadas com os outros. */
  conectores_prontos: string[];
  instalado: boolean;
  install_id: string | null;
  ultima_execucao: string | null;
  /** Quantas Rotinas deste Auxiliar existem nesta corretora. */
  rotinas: number;
  /**
   * Tela própria de execução, quando este Auxiliar tem uma.
   *
   * Dois Auxiliares têm interface de execução escrita à mão, com API própria:
   * `follow-up-whatsapp` e `resumo-atendimentos`. Elas FUNCIONAM — não são
   * duplicata de descrição, são o lugar onde o corretor manda rodar.
   *
   * Portá-las para dentro desta rota é trabalho real e fica registrado como
   * dívida. O que não podia acontecer era elas ficarem órfãs: a estrutura nova
   * as alcança por aqui, em vez de o corretor precisar do endereço decorado.
   */
  tela_de_execucao: string | null;

  // ── SPEC-131-B · a loja e a casca ────────────────────────────────────────────
  /** o nome do ícone lucide (PascalCase); o componente sai de components/aplicativos/casca/icones.ts */
  icone: string;
  /** a matiz (0–360) da capa gerada */
  matiz: number;
  /** a capa do Founder (https), ou null → a capa gerada */
  cover_url: string | null;
  faq: DuvidaDoAplicativo[];
  /** 1 = o destaque do topo da loja */
  destaque: number | null;
  /** as conexões que ele usa, com nome humano, e se ESTA corretora já tem cada uma */
  conexoes: ConexaoDoAplicativo[];
  prova: ProvaDoAplicativo;
  /** aplicativo sem rotina (Cotação, Quem Cobra Menos — D-131-21): não se instala nem se liga; só se configura */
  sem_rotina: boolean;
}

/**
 * A tela onde cada Auxiliar é operado, quando ele tem uma.
 *
 * `checklist-6h` é a antiga `/dashboard/briefing` — 828 linhas que mostram o
 * briefing do dia. Ela mudou de casa inteira: apagar o conteúdo e mandar o
 * corretor para a ficha do Auxiliar teria deixado ele sem o briefing.
 *
 * SPEC-139 (P-16): as três telas viraram a ABA DO TRABALHO na casa do próprio aplicativo (`[slug]?aba=`). Os
 * endereços antigos (`checklist-6h/hoje`, `galeria/follow-up-whatsapp`, `galeria/resumo-atendimentos`) dão 307 para
 * cá — mas quem pergunta aqui já recebe o endereço NOVO, sem o salto. A aba de cada um é a de ABAS_DO_APLICATIVO (o
 * teste da loja confere que cada endereço daqui abre uma aba que existe).
 */
export const TELA_DE_EXECUCAO: Record<string, string> = {
  'checklist-6h': '/dashboard/auxiliares/checklist-6h?aba=hoje',
  'follow-up-whatsapp': '/dashboard/auxiliares/follow-up-whatsapp?aba=follow-ups',
  'resumo-atendimentos': '/dashboard/auxiliares/resumo-atendimentos?aba=resumos',
};

/**
 * SPEC-078 F.2 — a tela de execução deste Auxiliar, quando ele tem uma.
 *
 * 📊 17/08/2026: Entregas montava o href do briefing À MÃO, como
 * `/dashboard/auxiliares/checklist-6h`. Esse endereço é capturado pela rota
 * `[slug]`, que renderiza o CARTÃO DESCRITIVO do Auxiliar — não o briefing.
 * São 26 briefings da AutoFleet que levavam à descrição do trabalho em vez do
 * trabalho. O endereço certo já estava escrito no mapa acima e não era lido.
 *
 * Por isso este leitor existe: quem precisa de um endereço de Auxiliar
 * PERGUNTA aqui, em vez de concatenar strings. O próximo Auxiliar que ganhar
 * tela própria passa a funcionar de graça em toda tela que use estas funções.
 */
export function telaDeExecucao(slug: string | null | undefined): string | null {
  if (!slug) return null;
  return TELA_DE_EXECUCAO[slug] ?? null;
}

/**
 * Onde abrir este Auxiliar: a tela onde ele é OPERADO, e só na falta dela o
 * cartão descritivo.
 *
 * A ordem importa. O cartão é a resposta para "o que este Auxiliar faz?"; quem
 * clica numa entrega já sabe o que ele faz e quer ver o que ele FEZ.
 */
export function ondeAbrirAuxiliar(slug: string | null | undefined): string | null {
  if (!slug) return null;
  return telaDeExecucao(slug) ?? `/dashboard/auxiliares/${slug}`;
}

/**
 * As categorias da loja. SPEC-131-B: o emoji SAIU (DS-001 §14 — era o "infantil" do laudo de design §1); cada uma
 * tem um ícone linear (nome lucide, mapeado em components/aplicativos/casca/icones.ts).
 */
export const CATEGORIAS: Record<string, { rotulo: string; icone: string }> = {
  dinheiro_que_volta: { rotulo: 'Dinheiro que volta', icone: 'Coins' },
  dinheiro_novo:      { rotulo: 'Dinheiro novo',      icone: 'TrendingUp' },
  cliente_blindado:   { rotulo: 'Cliente blindado',   icone: 'HeartHandshake' },
  negociacao:         { rotulo: 'Negociação',         icone: 'Scale' },
  protecao_carteira:  { rotulo: 'Proteção',           icone: 'ShieldCheck' },
  tempo_livre:        { rotulo: 'Tempo livre',        icone: 'Clock' },
};

/**
 * SPEC-131-B (laudo de design §2.4) — o ícone linear e a matiz da capa de cada aplicativo. A migration
 * 20261014_01 grava o MESMO nome em `auxiliary_templates.icon`; quando a coluna traz um nome que a tela conhece, ela
 * vence — este mapa é o padrão (e o que vale enquanto a migration não foi aplicada). Matizes frias + 1 âmbar.
 */
export const APLICATIVO_VISUAL: Record<string, { icone: string; matiz: number }> = {
  'checklist-6h':            { icone: 'Sunrise',             matiz: 38 },
  'cobranca-feita':          { icone: 'ReceiptText',         matiz: 158 },
  'follow-up-whatsapp':      { icone: 'MessageSquareReply',  matiz: 200 },
  'radar-mercado-regulacao': { icone: 'Radar',               matiz: 262 },
  'resumo-atendimentos':     { icone: 'ScrollText',          matiz: 215 },
  'tarefas-agendadas':       { icone: 'CalendarClock',       matiz: 188 },
  renovacao:                 { icone: 'RefreshCcwDot',       matiz: 203 },
  'renovacao-maxima':        { icone: 'RefreshCcwDot',       matiz: 203 },
  cotacao:                   { icone: 'Calculator',          matiz: 195 },
  'quem-cobra-menos':        { icone: 'BadgePercent',        matiz: 165 },
  'caca-comissao':           { icone: 'HandCoins',           matiz: 150 },
  'carteira-blindada':       { icone: 'ShieldCheck',         matiz: 205 },
  'clientes-perdidos':       { icone: 'UserSearch',          matiz: 230 },
  'contabilidade-pronta':    { icone: 'BookOpenCheck',       matiz: 175 },
  'digitacao-zero':          { icone: 'ScanText',            matiz: 225 },
  'organizacao-completa':    { icone: 'FolderCheck',         matiz: 185 },
  'protecao-completa':       { icone: 'Umbrella',            matiz: 210 },
  'resgatar-cliente':        { icone: 'UserRoundCheck',      matiz: 250 },
  'sinistralidade-avancada': { icone: 'ChartNoAxesCombined', matiz: 240 },
};

/** O que a tela usa quando um aplicativo novo ainda não está no mapa acima. */
export const VISUAL_PADRAO = { icone: 'LayoutGrid', matiz: 205 } as const;

/** Os nomes de ícone que a casca sabe desenhar (o espelho de components/aplicativos/casca/icones.ts). */
export const ICONES_CONHECIDOS: ReadonlySet<string> = new Set([
  ...Object.values(APLICATIVO_VISUAL).map((v) => v.icone),
  VISUAL_PADRAO.icone,
]);

/**
 * SPEC-131-B (D-131-21) — aplicativos SEM rotina: Cotação Rápida e Quem Cobra Menos. Não se
 * instalam nem se ligam (as regras valem assim que salvas); o botão principal deles é "Configurar".
 */
export const APLICATIVOS_SEM_ROTINA: ReadonlySet<string> = new Set(['cotacao', 'quem-cobra-menos']);

/**
 * SPEC-131-B (BLOCO 0 B8) — aplicativos em que INSTALAR já é LIGAR: a madrugada da Renovação roda assim que o
 * aplicativo está instalado e `active` (`madrugada.aplicativo_ligado`). O botão diz "Ligar" e mostra o "Como
 * começar" ANTES de confirmar — nunca "Instalar" com o texto "instalar não liga nada".
 */
export const INSTALAR_JA_LIGA: ReadonlySet<string> = new Set(['renovacao']);

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// SPEC-131-B · as ABAS de cada aplicativo (`?aba=`) — o contrato G1 ↔ G2/G3
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

/**
 * Uma aba da página do aplicativo.
 *
 * `componente` = o módulo em `components/aplicativos/<pasta>/Aba<Nome>.tsx`, escrito como `'<pasta>/Aba<Nome>'`
 * (ex.: `'renovacao/AbaRenovacoes'`), carregado por import dinâmico pela casca. O módulo exporta `default` um
 * componente React que recebe `PropsDaAba`. `null` = a casca desenha (Início, Dúvidas, e o Configurar dos aplicativos
 * com rotina — o painel de rotinas de hoje). SPEC-139: a Cobrança saiu do modal e tem o Configurar PRÓPRIO
 * (`cobranca/AbaConfigurar`, o formulário extraído do painel, mesmo corpo gravado).
 *
 * 🔴 Um arquivo de aba que ainda não existe NÃO quebra o build nem a tela: o import dinâmico da casca é um contexto
 * do webpack (`webpackInclude` só de `Aba*.tsx`) — o que não está no disco simplesmente não entra no contexto, e a
 * aba diz "esta parte ainda está sendo preparada". O teste da loja lista os que faltam (`PENDENTES_DA_COSTURA`).
 */
export interface AbaDoAplicativo {
  id: string;
  rotulo: string;
  componente: string | null;
}

/** O que a casca entrega a toda aba carregada por import dinâmico. */
export interface PropsDaAba {
  item: ItemDoCatalogo;
  /** o id da aba aberta (`?aba=`) */
  aba: string;
}

const ABA_INICIO: AbaDoAplicativo = { id: 'inicio', rotulo: 'Início', componente: null };
const ABA_CONFIGURAR: AbaDoAplicativo = { id: 'configurar', rotulo: 'Configurar', componente: null };
const ABA_DUVIDAS: AbaDoAplicativo = { id: 'duvidas', rotulo: 'Dúvidas', componente: null };

/** As abas de quem não está em ABAS_DO_APLICATIVO: Início · Configurar (o painel de rotinas) · Dúvidas. */
export const ABAS_PADRAO: AbaDoAplicativo[] = [ABA_INICIO, ABA_CONFIGURAR, ABA_DUVIDAS];

export const ABAS_DO_APLICATIVO: Record<string, AbaDoAplicativo[]> = {
  renovacao: [
    ABA_INICIO,
    { id: 'configurar', rotulo: 'Configurar', componente: 'renovacao/AbaConfigurar' },   // G3
    { id: 'renovacoes', rotulo: 'Renovações', componente: 'renovacao/AbaRenovacoes' },   // G2
    ABA_DUVIDAS,
  ],
  // SPEC-132-B · B3 — a Cotação Rápida tão completa quanto a Renovação: Início · Configurar · Cotações · Dúvidas
  cotacao: [
    ABA_INICIO,
    { id: 'configurar', rotulo: 'Configurar', componente: 'cotacao/AbaConfigurar' },     // G3 + as regras (B3)
    { id: 'cotacoes', rotulo: 'Cotações', componente: 'cotacao/AbaCotacoes' },          // B3
    ABA_DUVIDAS,
  ],
  'quem-cobra-menos': [
    ABA_INICIO,
    { id: 'configurar', rotulo: 'Configurar', componente: 'quem-cobra-menos/AbaConfigurar' },   // G3
    ABA_DUVIDAS,
  ],
  // SPEC-139 · L2 — a Cobrança sai do modal e entra na casa: o Configurar é o formulário EXTRAÍDO do painel (o mesmo
  // corpo gravado — o teste dourado do ELO), e "Cobranças" é o que saiu (só leitura, só desta corretora)
  'cobranca-feita': [
    ABA_INICIO,
    { id: 'configurar', rotulo: 'Configurar', componente: 'cobranca/AbaConfigurar' },   // L2
    { id: 'cobrancas', rotulo: 'Cobranças', componente: 'cobranca/AbaCobrancas' },      // L2
    ABA_DUVIDAS,
  ],
  // SPEC-139 · L3 (P-16) — as telas que já funcionavam, MOVIDAS para a aba do trabalho. O Checklist tem o Configurar
  // PRÓPRIO (o perfil do briefing é da corretora — não exige instalar).
  'checklist-6h': [
    ABA_INICIO,
    { id: 'hoje', rotulo: 'Hoje', componente: 'checklist-6h/AbaHoje' },                          // L3
    { id: 'configurar', rotulo: 'Configurar', componente: 'checklist-6h/AbaConfigurar' },        // L3
    ABA_DUVIDAS,
  ],
  // D-139-L4-02 — Follow-up e Resumo são SOB DEMANDA: sem Configurar. 📊 B1 da L3 (15/10): 0 rotinas ligadas aos dois;
  // e o painel de rotinas não tem rotina para eles (`ROTINA_DO_AUXILIAR` em PainelDeRotinas só conhece a Cobrança) —
  // a aba seria um painel vazio que convida a criar uma rotina que não existe. O que se escolhe (o atendimento, o tom)
  // mora na própria aba do trabalho. (painel vazio 45 × sem Configurar 85)
  'follow-up-whatsapp': [
    ABA_INICIO,
    { id: 'follow-ups', rotulo: 'Follow-ups', componente: 'follow-up-whatsapp/AbaFollowUps' },   // L3
    ABA_DUVIDAS,
  ],
  'resumo-atendimentos': [
    ABA_INICIO,
    { id: 'resumos', rotulo: 'Resumos', componente: 'resumo-atendimentos/AbaResumos' },          // L3
    ABA_DUVIDAS,
  ],
};

/**
 * SPEC-139 (D-139-L4-02) — os aplicativos SOB DEMANDA e a aba onde se usa cada um: no "Como começar" o passo de
 * configurar vira "usar" e leva à aba do trabalho (não há Configurar para onde levar).
 */
export const APLICATIVOS_SOB_DEMANDA: Readonly<Record<string, { aba: string; rotulo: string; detalhe: string }>> = {
  'follow-up-whatsapp': { aba: 'follow-ups', rotulo: 'Follow-ups', detalhe: 'Escolha o atendimento e o tom, e peça o rascunho.' },
  'resumo-atendimentos': { aba: 'resumos', rotulo: 'Resumos', detalhe: 'Escolha o atendimento, ou deixe no automático, e peça o resumo.' },
};

/**
 * SPEC-139 — os aplicativos cujo Configurar PRÓPRIO também exige a instalação: a regra da Cobrança é uma rotina DA
 * instalação (a mesma que o modal gravava), então antes de instalar não há o que configurar — "Instalar" leva direto
 * ao Configurar (`AuxiliarDetalheClient`). A Renovação, a Cotação e o QCM configuram sem instalar.
 */
export const CONFIGURAR_EXIGE_INSTALAR: ReadonlySet<string> = new Set(['cobranca-feita']);

/**
 * As abas que ESTE aplicativo mostra: Dúvidas só com dúvida escrita; Configurar some no aplicativo com rotina que
 * ainda não foi instalado (o painel exige a instalação).
 *
 * 🔴 SPEC-139 (mutação 6 da régua): o "Em breve" é HONESTO — só Início e Dúvidas. Nada de Configurar nem da aba do
 * trabalho (não há trabalho), e o botão principal é o "Em breve" desabilitado (`botaoPrincipal`), nunca Ligar.
 */
export function abasDoAplicativo(
  item: Pick<ItemDoCatalogo, 'slug' | 'faq' | 'estado' | 'instalado' | 'sem_rotina'>,
): AbaDoAplicativo[] {
  const base = ABAS_DO_APLICATIVO[item.slug] ?? ABAS_PADRAO;
  return base.filter((a) => {
    if (a.id === 'duvidas') return item.faq.length > 0;
    if (item.estado === 'em_breve') return a.id === 'inicio';
    if (a.id === 'configurar') {
      const exigeInstalar = a.componente === null || CONFIGURAR_EXIGE_INSTALAR.has(item.slug);
      if (exigeInstalar && !item.sem_rotina && !item.instalado) return false;
    }
    return true;
  });
}

/**
 * K3 (juiz de design 2): as abas de trabalho em LISTA ganham largura (`max-w-7xl`); as de leitura ficam em 5xl.
 * Devolve as que ESTE aplicativo tem — a página (servidor) passa a lista pronta para a casca (cliente).
 * SPEC-139: "Cobranças" é lista (por dia) → larga. "Hoje", "Follow-ups" e "Resumos" eram telas de leitura em 5xl e
 * continuam assim (o conteúdo foi MOVIDO, não redesenhado).
 */
export const ABAS_LARGAS: readonly string[] = ['renovacoes', 'cotacoes', 'cobrancas'];
export function abasLargas(abas: AbaDoAplicativo[]): string[] {
  return abas.filter((a) => ABAS_LARGAS.includes(a.id)).map((a) => a.id);
}

/** A aba pedida na URL, se ela existe para este aplicativo; senão Início (aba inválida → Início). */
export function abaValida(abas: AbaDoAplicativo[], pedida: string | null | undefined): string {
  return abas.some((a) => a.id === pedida) ? String(pedida) : 'inicio';
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// SPEC-131-B · o que o CARD e o CABEÇALHO dizem — funções puras (testadas sem rede nem banco)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

export type TomDoSelo = 'neutral' | 'success' | 'warning';

/** O selo de estado (laudo de design §2.3). "Disponível" não tem selo. */
export function seloDoEstado(estado: EstadoDoCard): { rotulo: string; tom: TomDoSelo } | null {
  switch (estado) {
    case 'ligado': return { rotulo: 'Ligado', tom: 'success' };
    case 'pausado': return { rotulo: 'Desligado', tom: 'neutral' };
    case 'falta_conectar': return { rotulo: 'Falta conectar', tom: 'warning' };
    case 'em_breve': return { rotulo: 'Em breve', tom: 'neutral' };
    default: return null;
  }
}

/** "hoje" · "ontem" · "há 3 dias" · "há 2 meses" — o relógio é parâmetro (teste determinístico). */
export function haQuanto(iso: string, agora: Date = new Date()): string {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '';
  const dias = Math.floor((agora.getTime() - t) / 86_400_000);
  if (dias <= 0) return 'hoje';
  if (dias === 1) return 'ontem';
  if (dias < 31) return `há ${dias} dias`;
  const meses = Math.floor(dias / 30);
  return meses <= 1 ? 'há 1 mês' : `há ${meses} meses`;
}

/**
 * O rodapé do card: a PROVA real (número medido nesta corretora) ou o estado em palavras. Nunca número inventado,
 * nunca estrela (D-131-26). Zero execuções não vira "0 execuções": vira o estado.
 */
export function provaDoCard(
  item: Pick<ItemDoCatalogo, 'slug' | 'estado' | 'prova' | 'conectores_pendentes' | 'sem_rotina'>,
  agora: Date = new Date(),
): string {
  const { prova } = item;
  if (item.estado === 'em_breve') return 'Em breve';
  if (prova.renovacoes_no_mes !== null && prova.renovacoes_no_mes > 0) {
    const n = prova.renovacoes_no_mes;
    return n === 1 ? '1 renovação calculada este mês' : `${n} renovações calculadas este mês`;
  }
  if (prova.execucoes > 0) {
    const vezes = prova.execucoes === 1 ? '1 execução' : `${prova.execucoes} execuções`;
    const quando = prova.ultima_execucao ? haQuanto(prova.ultima_execucao, agora) : '';
    return quando ? `${vezes} · última ${quando}` : vezes;
  }
  if (item.estado === 'falta_conectar') {
    const nomes = item.conectores_pendentes.map((c) => c.nome).join(' e ');
    return nomes ? `Falta conectar ${nomes}` : 'Falta conectar';
  }
  if (item.sem_rotina) return 'Configure as regras';
  if (item.estado === 'ligado') return 'Ligado · ainda não rodou';
  if (item.estado === 'pausado') return 'Desligado · a configuração fica guardada';
  return 'Pronto para ligar';
}

/** O botão principal do cabeçalho, por estado (laudo de design §3; instalar ≠ ligar, SPEC-078). */
export type BotaoPrincipal =
  | { tipo: 'desabilitado'; rotulo: string; motivo: string | null }
  | { tipo: 'link'; rotulo: string; href: string }
  | { tipo: 'acao'; rotulo: string; acao: 'install' | 'resume' | 'pause'; confirmar: boolean; fantasma: boolean };

export function botaoPrincipal(
  item: Pick<ItemDoCatalogo, 'slug' | 'estado' | 'conectores_pendentes' | 'falta_para_existir' | 'sem_rotina'>,
): BotaoPrincipal {
  const aqui = `/dashboard/auxiliares/${item.slug}`;
  // 🔴 SPEC-139 (mutação 6 da régua): o "Em breve" NUNCA tem Ligar nem Instalar — vem ANTES de qualquer outra regra
  // (inclusive a da Renovação, em que instalar já liga). O teste da loja fica VERMELHO se isto virar ação.
  if (item.estado === 'em_breve') {
    return { tipo: 'desabilitado', rotulo: 'Em breve', motivo: item.falta_para_existir };
  }
  if (item.sem_rotina) return { tipo: 'link', rotulo: 'Configurar', href: `${aqui}?aba=configurar` };
  if (item.estado === 'falta_conectar') {
    const primeiro = item.conectores_pendentes[0];
    return {
      tipo: 'link',
      rotulo: primeiro ? `Conectar ${primeiro.nome}` : 'Conectar',
      href: primeiro?.onde ?? '/dashboard/personalizacao/conectores',
    };
  }
  if (item.estado === 'ligado') {
    return { tipo: 'acao', rotulo: 'Desligar', acao: 'pause', confirmar: false, fantasma: true };
  }
  if (item.estado === 'pausado') {
    return { tipo: 'acao', rotulo: 'Ligar', acao: 'resume', confirmar: true, fantasma: false };
  }
  // disponível e não instalado
  if (INSTALAR_JA_LIGA.has(item.slug)) {
    return { tipo: 'acao', rotulo: 'Ligar', acao: 'install', confirmar: true, fantasma: false };
  }
  return { tipo: 'acao', rotulo: 'Instalar', acao: 'install', confirmar: false, fantasma: false };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// SPEC-131-B · "Como começar" — os passos com estado, link e "N de M prontos"
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

export type EstadoDoPasso = 'pronto' | 'falta' | 'atencao' | 'nao_sei';

export interface PassoDoComoComecar {
  chave: string;
  titulo: string;
  detalhe: string;
  estado: EstadoDoPasso;
  link: string | null;
  rotuloDoLink: string | null;
}

/** Um passo como o backend devolve (`/api/servicos-da-corretora/prontidao` — a régua ÚNICA da configuração). */
export interface PassoDaProntidao {
  chave: string;
  titulo?: string;
  estado: string;
  detalhe?: string;
  link?: string;
  /** SPEC-132-B · B3 — no passo `servicos`: QUAL serviço já tem regra escolhida (cotacao, renovacao) */
  por_servico?: Record<string, boolean>;
}

export interface FontesDoComoComecar {
  /** os passos da prontidão (sistema de gestão · Agger da corretora · equipe · serviços); null = não deu para ler */
  prontidao: PassoDaProntidao[] | null;
  /** o Agger DA PESSOA da sessão está conectado? null = não deu para ler */
  meuAgger: boolean | null;
}

/** Meu perfil — onde a pessoa conecta o Agger dela e o WhatsApp de trabalho (G3). */
export const LINK_MEU_PERFIL = '/dashboard/configuracoes';
export const LINK_CONECTORES = '/dashboard/personalizacao/conectores';
export const LINK_EQUIPE = '/dashboard/personalizacao/equipe';

function estadoDoBackend(estado: string | undefined): EstadoDoPasso {
  if (estado === 'pronto') return 'pronto';
  if (estado === 'falta') return 'falta';
  if (estado === 'atencao' || estado === 'em_parte') return 'atencao';
  return 'nao_sei';
}

function daProntidao(
  fontes: FontesDoComoComecar, chave: string, titulo: string, link: string, rotuloDoLink: string,
): PassoDoComoComecar {
  const p = fontes.prontidao?.find((x) => x.chave === chave);
  return {
    chave,
    titulo,
    detalhe: p?.detalhe || (fontes.prontidao ? 'Ainda não conferido.' : 'Não deu para conferir agora.'),
    estado: p ? estadoDoBackend(p.estado) : 'nao_sei',
    link,
    rotuloDoLink,
  };
}

/**
 * Os passos do "Como começar" deste aplicativo. Puro: recebe o item e o que já foi lido (prontidão, meu Agger).
 *
 * Renovação (SPEC §4): sistema de gestão conectado → Agger da corretora → o SEU Agger (Meu perfil) → quem é quem
 * (Equipe) → Ligar. Cotação Rápida: Agger da corretora → o SEU Agger → as regras. Quem Cobra Menos: Agger da
 * corretora → as regras. Os outros: as conexões da
 * corretora que ele exige → configurar a rotina → ligar.
 */
export function passosDoComoComecar(
  item: Pick<ItemDoCatalogo, 'slug' | 'estado' | 'instalado' | 'rotinas' | 'conexoes' | 'sem_rotina'>,
  fontes: FontesDoComoComecar,
): PassoDoComoComecar[] {
  const aqui = `/dashboard/auxiliares/${item.slug}`;
  // SPEC-139 (mutação 6): o "Em breve" não tem passo nenhum — nem "Ligar" (não existe o que ligar). A casca mostra
  // "Ainda não está pronto" com o que falta, e o contador "N de M prontos" não aparece.
  if (item.estado === 'em_breve') return [];
  const ligado = item.estado === 'ligado';
  const passoLigar: PassoDoComoComecar = {
    chave: 'ligar',
    titulo: 'Ligar',
    detalhe: ligado ? 'Ligado e trabalhando.' : 'O último passo: depois de ligar, ele trabalha sozinho.',
    estado: ligado ? 'pronto' : 'falta',
    link: null,
    rotuloDoLink: null,
  };

  if (item.slug === 'renovacao') {
    const infocap = item.conexoes.find((c) => c.slug === 'infocap');
    const daTela = fontes.prontidao?.find((x) => x.chave === 'sistema_de_gestao');
    const gestao: PassoDoComoComecar = daTela
      ? daProntidao(fontes, 'sistema_de_gestao', 'Conectar o sistema de gestão (InfoCap)', LINK_CONECTORES, 'Conectar')
      : {
          chave: 'sistema_de_gestao',
          titulo: 'Conectar o sistema de gestão (InfoCap)',
          detalhe: infocap?.pronto ? 'A InfoCap está conectada.' : 'É dela que saem as apólices que vão vencer.',
          estado: infocap?.pronto ? 'pronto' : infocap?.pronto === false ? 'falta' : 'nao_sei',
          link: LINK_CONECTORES,
          rotuloDoLink: 'Conectar',
        };
    const meu: PassoDoComoComecar = {
      chave: 'meu_agger',
      titulo: 'Conectar o seu Agger',
      detalhe: fontes.meuAgger
        ? 'O seu Agger está conectado: os cálculos dos seus clientes ficam na sua conta.'
        : fontes.meuAgger === false
          ? 'Em Meu perfil, Minhas conexões. Sem ele, os seus clientes são calculados no Agger da corretora.'
          : 'Não deu para conferir agora.',
      estado: fontes.meuAgger ? 'pronto' : fontes.meuAgger === false ? 'falta' : 'nao_sei',
      link: LINK_MEU_PERFIL,
      rotuloDoLink: 'Abrir Meu perfil',
    };
    return [
      gestao,
      daProntidao(fontes, 'agger_da_corretora', 'Conectar o Agger da corretora', LINK_CONECTORES, 'Conectar'),
      meu,
      daProntidao(fontes, 'equipe', 'Dizer quem é quem na equipe', LINK_EQUIPE, 'Abrir Equipe'),
      // SPEC-131-B G5 (laudo de design §3: "→ Configure → Ligue"): as regras moram na aba Configurar DESTE aplicativo
      daProntidao(fontes, 'servicos', 'Escolher as regras da renovação', `${aqui}?aba=configurar`, 'Configurar'),
      passoLigar,
    ];
  }

  if (item.slug === 'cotacao') {
    // SPEC-132-B · B3 (SPEC §4): Agger da corretora (o reserva) → o SEU Agger (Meu perfil) → as regras do cálculo
    const meu: PassoDoComoComecar = {
      chave: 'meu_agger',
      titulo: 'Conectar o seu Agger',
      detalhe: fontes.meuAgger
        ? 'O seu Agger está conectado: as cotações que você pedir saem na sua conta.'
        : fontes.meuAgger === false
          ? 'Em Meu perfil, Minhas conexões. Sem ele, as suas cotações saem no Agger da corretora.'
          : 'Não deu para conferir agora.',
      estado: fontes.meuAgger ? 'pronto' : fontes.meuAgger === false ? 'falta' : 'nao_sei',
      link: LINK_MEU_PERFIL,
      rotuloDoLink: 'Abrir Meu perfil',
    };
    const servicos = fontes.prontidao?.find((x) => x.chave === 'servicos');
    const daCotacao = servicos?.por_servico ? servicos.por_servico.cotacao : undefined;
    const regras: PassoDoComoComecar =
      typeof daCotacao === 'boolean'
        ? {
            chave: 'servicos',
            titulo: 'Conferir as regras do cálculo',
            detalhe: daCotacao
              ? 'As regras da cotação estão escolhidas.'
              : 'Enquanto você não escolher, valem as regras padrão do AutoBrokers.',
            estado: daCotacao ? 'pronto' : 'falta',
            link: `${aqui}?aba=configurar`,
            rotuloDoLink: 'Configurar',
          }
        : daProntidao(fontes, 'servicos', 'Conferir as regras do cálculo', `${aqui}?aba=configurar`, 'Configurar');
    return [
      daProntidao(fontes, 'agger_da_corretora', 'Conectar o Agger da corretora', LINK_CONECTORES, 'Conectar'),
      meu,
      regras,
    ];
  }

  if (item.sem_rotina) {
    const regras = daProntidao(fontes, 'servicos', 'Escolher as regras', `${aqui}?aba=configurar`, 'Configurar');
    return [
      daProntidao(fontes, 'agger_da_corretora', 'Conectar o Agger da corretora', LINK_CONECTORES, 'Conectar'),
      regras,
    ];
  }

  const conexoes: PassoDoComoComecar[] = item.conexoes.map((c): PassoDoComoComecar => {
    const cobranca = item.slug === 'cobranca-feita' ? PASSOS_DA_COBRANCA[c.slug] : undefined;
    return {
      chave: `conexao:${c.slug}`,
      titulo: cobranca?.titulo ?? `Conectar ${c.nome}`,
      detalhe: c.pronto
        ? cobranca?.pronto ?? `${c.nome} está conectado.`
        : cobranca?.falta ?? `A conexão é da corretora: conecta uma vez, serve a todos os aplicativos.`,
      estado: c.pronto ? 'pronto' : c.pronto === false ? 'falta' : 'nao_sei',
      link: c.onde,
      rotuloDoLink: 'Conectar',
    };
  });
  const sobDemanda = APLICATIVOS_SOB_DEMANDA[item.slug];
  if (sobDemanda) {
    // D-139-L4-02: sem Configurar — o passo é USAR, na aba do trabalho
    const usar: PassoDoComoComecar = {
      chave: 'usar',
      titulo: `Usar na aba ${sobDemanda.rotulo}`,
      detalhe: sobDemanda.detalhe,
      estado: item.instalado ? 'pronto' : 'falta',
      link: `${aqui}?aba=${sobDemanda.aba}`,
      rotuloDoLink: 'Abrir',
    };
    return [...conexoes, usar, passoLigar];
  }
  const regrasDaCobranca = item.slug === 'cobranca-feita';
  const configurar: PassoDoComoComecar = {
    chave: 'configurar',
    titulo: regrasDaCobranca
      ? (item.instalado ? 'Escolher as regras da cobrança' : 'Instalar e escolher as regras da cobrança')
      : (item.instalado ? 'Configurar' : 'Instalar e configurar'),
    detalhe: item.rotinas > 0
      ? `${item.rotinas === 1 ? '1 rotina configurada' : `${item.rotinas} rotinas configuradas`}.`
      : regrasDaCobranca
        ? 'Para quem, quando e de que jeito o boleto sai.'
        : 'Diga o que ele faz, quando e para quem.',
    estado: item.rotinas > 0 ? 'pronto' : 'falta',
    link: item.instalado ? `${aqui}?aba=configurar` : null,
    rotuloDoLink: item.instalado ? 'Configurar' : null,
  };
  return [...conexoes, configurar, passoLigar];
}

/**
 * SPEC-139 §4.2 — o "Como começar" da Cobrança diz o que cada conexão É para ela: o portal (de onde sai o boleto) e o
 * número que envia (por onde o boleto chega ao cliente). Os outros aplicativos seguem "Conectar <nome>".
 */
const PASSOS_DA_COBRANCA: Record<string, { titulo: string; pronto: string; falta: string }> = {
  insurance_portal: {
    titulo: 'Conectar o portal da seguradora',
    pronto: 'O portal está conectado: é dele que saem as parcelas vencidas e os boletos.',
    falta: 'É do portal que saem as parcelas vencidas e os boletos. A conexão é da corretora e serve a todos os aplicativos.',
  },
  whatsapp_zapi: {
    titulo: 'Conectar o número que envia',
    pronto: 'O WhatsApp da corretora está conectado: os boletos saem por ele, espaçados.',
    falta: 'Os boletos chegam ao cliente pelo WhatsApp da corretora. Conecte o número antes de ligar.',
  },
};

/** "2 de 4 prontos" */
export function contagemDosPassos(passos: PassoDoComoComecar[]): { prontos: number; total: number } {
  return { prontos: passos.filter((p) => p.estado === 'pronto').length, total: passos.length };
}

/**
 * Onde o corretor vai resolver cada conexão.
 *
 * Só entram conectores de `scope='company'` ou `'user'` — os de plataforma
 * nunca ficam pendentes, então nunca precisam de destino.
 */
const ONDE_CONECTAR: Record<string, string> = {
  insurance_portal: '/dashboard/personalizacao/conectores/portais',
  infocap:          '/dashboard/personalizacao/conectores',
  whatsapp_zapi:    '/dashboard/personalizacao/corretora/whatsapp',
  google_drive:     '/dashboard/personalizacao/conectores',
  notion:           '/dashboard/personalizacao/conectores',
};

/**
 * SPEC-064 — a regra das três camadas, em uma frase:
 *
 *   A DEFINIÇÃO do conector é sempre global.
 *   O que muda é QUEM SEGURA A CREDENCIAL.
 *
 *     platform  a AutoBrokers paga e todas usam        Firecrawl, Tavily,
 *               → a corretora não conecta nada          fontes internas
 *     company   a conta da corretora                    InfoCap, portal, Drive
 *     user      a conta da pessoa                       Outlook, Gmail
 *
 * Conector de plataforma está SEMPRE pronto: a chave é nossa e vive no
 * ambiente. Tratá-lo como pendente travaria um Auxiliar que funciona — foi
 * exatamente o que aconteceu quando `firecrawl` entrou em `required_connectors`
 * sem esta distinção: a tela passou a pedir, a toda corretora, que conectasse
 * um serviço que já estava pago e ligado.
 *
 * Ver docs/canon/CAMADAS-DE-CONEXAO.md.
 */
const SCOPE_PLATAFORMA = 'platform';

/**
 * O que ESTA corretora tem conectado — calculado uma vez, vale para todos.
 *
 * Lê três fontes porque a verdade está espalhada em três lugares, por razões
 * históricas:
 *
 *   tenant_connections  o caminho novo (InfoCap, Drive, Notion, Firecrawl)
 *   portal_accounts     o portal_worker, que é quem entra na Allianz de verdade
 *   integrations        o WhatsApp, que veio antes do conceito de conector
 *
 * Unificar as três tabelas numa só é trabalho de outra SPEC. O que NÃO dá para
 * fazer é a tela responder "não conectado" para uma corretora que tem a conta
 * do portal funcionando — seria mentir para quem já fez o trabalho.
 */
export async function conexoesDaCorretora(
  supabase: SupabaseClient,
  companyId: string,
): Promise<Set<string>> {
  const prontos = new Set<string>();

  const [plataforma, conexoes, portais, integracoes] = await Promise.all([
    // O que a AutoBrokers paga já está pronto para todas, sempre.
    supabase.from('connector_templates')
      .select('slug')
      .eq('scope', SCOPE_PLATAFORMA)
      .eq('is_active', true),
    supabase.from('tenant_connections')
      .select('status, connector_template_id, connector_templates(slug)')
      .eq('company_id', companyId)
      .eq('status', 'connected'),
    supabase.from('portal_accounts')
      .select('portal_key, health')
      .eq('company_id', companyId),
    supabase.from('integrations')
      .select('provider, is_active')
      .eq('company_id', companyId)
      .eq('is_active', true),
  ]);

  for (const p of plataforma.data ?? []) prontos.add(p.slug);

  for (const c of conexoes.data ?? []) {
    const slug = (c as any)?.connector_templates?.slug;
    if (slug) prontos.add(slug);
  }

  // Uma conta de portal saudável satisfaz `insurance_portal` — qualquer que
  // seja a seguradora. Qual seguradora cada Auxiliar precisa é detalhe da
  // configuração dele (Bloco F), não do catálogo.
  if ((portais.data ?? []).some((p: any) => p.health !== 'failing')) {
    prontos.add('insurance_portal');
  }

  if ((integracoes.data ?? []).length > 0) prontos.add('whatsapp_zapi');

  return prontos;
}

function derivarEstado(
  estadoCatalogo: EstadoCatalogo,
  statusInstalacao: string | null,
  pendentes: number,
): EstadoDoCard {
  if (estadoCatalogo === 'coming_soon') return 'em_breve';
  if (statusInstalacao === 'active') return 'ligado';
  if (statusInstalacao === 'paused' || statusInstalacao === 'inactive') return 'pausado';
  if (pendentes > 0) return 'falta_conectar';
  return 'disponivel';
}

/** SPEC-131-B — o nome de gente das conexões que não têm linha em `connector_templates` (o Agger mora no cofre). */
export const NOME_HUMANO_DA_CONEXAO: Record<string, string> = {
  infocap: 'InfoCap',
  insurance_portal: 'Portal da Seguradora',
  portal_browser: 'Portal da Seguradora',
  whatsapp_zapi: 'WhatsApp',
  google_drive: 'Google Drive',
  notion: 'Notion',
  quiver: 'Quiver',
  agger: 'Agger',
};

const COLUNAS_DO_TEMPLATE =
  'id, slug, name, headline, categories, catalog_state, data_sources, ' +
  'what_it_does, value_promise, missing_for_launch, description, ' +
  'short_description, required_connectors, default_config, icon';

/**
 * Os templates ativos. SPEC-131-B: lê também `cover_url, faq, featured_rank` (migration 20261014_01). Se a coluna
 * ainda não existe no banco (o código chegou antes do APPLY), lê sem elas — a loja abre com a capa gerada, sem
 * destaque e sem dúvidas, em vez de abrir VAZIA (um select com coluna inexistente derruba a consulta inteira).
 */
async function lerTemplates(supabase: SupabaseClient): Promise<{ data: any[] | null }> {
  const novo = await supabase.from('auxiliary_templates')
    .select(`${COLUNAS_DO_TEMPLATE}, cover_url, faq, featured_rank`)
    .eq('status', 'active')
    .eq('is_active', true);
  if (!novo.error) return { data: (novo.data as any[]) ?? [] };
  const antigo = await supabase.from('auxiliary_templates')
    .select(COLUNAS_DO_TEMPLATE)
    .eq('status', 'active')
    .eq('is_active', true);
  return { data: (antigo.data as any[]) ?? [] };
}

/**
 * Quantas execuções as rotinas deste aplicativo tiveram NESTA corretora, e quando foi a última.
 * 🔴 Dois filtros: `company_id` da sessão E as rotinas desta corretora — e contagem por `count: 'exact'` (sem o
 * teto de mil linhas do PostgREST).
 */
async function execucoesDasRotinas(
  supabase: SupabaseClient, companyId: string, rotinaIds: string[],
): Promise<{ n: number; ultima: string | null }> {
  try {
    const [contagem, ultima] = await Promise.all([
      supabase.from('routine_runs')
        .select('id', { count: 'exact', head: true })
        .eq('company_id', companyId)
        .in('routine_id', rotinaIds),
      supabase.from('routine_runs')
        .select('started_at')
        .eq('company_id', companyId)
        .in('routine_id', rotinaIds)
        .order('started_at', { ascending: false })
        .limit(1),
    ]);
    return {
      n: typeof contagem.count === 'number' ? contagem.count : 0,
      ultima: (ultima.data as any[] | null)?.[0]?.started_at ?? null,
    };
  } catch {
    return { n: 0, ultima: null };
  }
}

/** O primeiro instante do mês corrente no fuso de São Paulo (o Brasil não tem horário de verão desde 2019). */
export function inicioDoMesEmSaoPaulo(agora: Date = new Date()): string {
  const partes = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit' })
    .formatToParts(agora);
  const ano = partes.find((p) => p.type === 'year')?.value ?? String(agora.getUTCFullYear());
  const mes = partes.find((p) => p.type === 'month')?.value ?? String(agora.getUTCMonth() + 1).padStart(2, '0');
  return `${ano}-${mes}-01T00:00:00-03:00`;
}

/** Renovações que viraram `calculada` neste mês (a trilha `renovacao_eventos` da 131-A), só desta corretora. */
async function renovacoesCalculadasNoMes(supabase: SupabaseClient, companyId: string): Promise<number | null> {
  try {
    const r = await supabase.from('renovacao_eventos')
      .select('id', { count: 'exact', head: true })
      .eq('company_id', companyId)
      .eq('para', 'calculada')
      .gte('criado_em', inicioDoMesEmSaoPaulo());
    if (r.error) return null;
    return typeof r.count === 'number' ? r.count : null;
  } catch {
    return null;
  }
}

/**
 * SPEC-139 — "O que faz" aceita as duas formas que o catálogo tem: `{tarefa, frequencia}` (a de todos) e o texto
 * solto (📊 15/10: `tarefas-agendadas` gravou 3 strings — a tela desenhava 3 linhas VAZIAS). O texto vira a tarefa,
 * sem frequência; o que não é nem uma coisa nem outra sai.
 */
export function lerTarefas(bruto: unknown): TarefaDoAuxiliar[] {
  if (!Array.isArray(bruto)) return [];
  const tarefas: TarefaDoAuxiliar[] = [];
  for (const t of bruto as unknown[]) {
    if (typeof t === 'string' && t.trim()) tarefas.push({ tarefa: t.trim(), frequencia: '' });
    else if (t && typeof t === 'object' && typeof (t as any).tarefa === 'string' && (t as any).tarefa.trim()) {
      tarefas.push({ tarefa: (t as any).tarefa, frequencia: typeof (t as any).frequencia === 'string' ? (t as any).frequencia : '' });
    }
  }
  return tarefas;
}

function lerFaq(bruto: unknown): DuvidaDoAplicativo[] {
  if (!Array.isArray(bruto)) return [];
  return bruto
    .filter((d: any) => d && typeof d.pergunta === 'string' && typeof d.resposta === 'string')
    .map((d: any) => ({ pergunta: d.pergunta, resposta: d.resposta }));
}

/** Uma linha da "Atividade recente" — da fonte REAL, nunca de `last_run_at`. */
export interface AtividadeDoAplicativo {
  quando: string;
  texto: string;
  tom: 'success' | 'warning' | 'neutral';
}

/**
 * SPEC-131-B — a atividade recente (as 3 últimas). Renovação: as madrugadas (`renovacao_dias`, 131-A). Os outros:
 * as execuções das rotinas dele (`routine_runs`). Sempre por `company_id` da sessão.
 */
export async function atividadeRecente(
  supabase: SupabaseClient, companyId: string, item: Pick<ItemDoCatalogo, 'slug' | 'install_id'>,
): Promise<AtividadeDoAplicativo[]> {
  try {
    if (item.slug === 'renovacao') {
      const r = await supabase.from('renovacao_dias')
        .select('dia, esperadas, calculadas, pendentes, falharam, faltaram')
        .eq('company_id', companyId)
        .order('dia', { ascending: false })
        .limit(3);
      return ((r.data as any[] | null) ?? []).map((d) => {
        const esperadas = Number(d.esperadas) || 0;
        const calculadas = Number(d.calculadas) || 0;
        const pendentes = Number(d.pendentes) || 0;
        const ruins = (Number(d.falharam) || 0) + (Number(d.faltaram) || 0);
        const partes = [`${calculadas} de ${esperadas} calculadas`];
        if (pendentes > 0) partes.push(pendentes === 1 ? '1 pendente' : `${pendentes} pendentes`);
        if (ruins > 0) partes.push(ruins === 1 ? '1 sem cálculo' : `${ruins} sem cálculo`);
        return {
          quando: `${d.dia}T12:00:00-03:00`,
          texto: `Madrugada: ${partes.join(' · ')}`,
          tom: ruins > 0 ? 'warning' : 'success',
        } as AtividadeDoAplicativo;
      });
    }
    if (!item.install_id) return [];
    const rot = await supabase.from('routines')
      .select('id')
      .eq('company_id', companyId)
      .eq('tenant_auxiliary_id', item.install_id);
    const ids = ((rot.data as any[] | null) ?? []).map((x) => String(x.id));
    if (ids.length === 0) return [];
    const runs = await supabase.from('routine_runs')
      .select('started_at, status')
      .eq('company_id', companyId)
      .in('routine_id', ids)
      .order('started_at', { ascending: false })
      .limit(3);
    return ((runs.data as any[] | null) ?? []).map((x) => ({
      quando: String(x.started_at),
      texto: x.status === 'ok' ? 'Execução concluída'
        : x.status === 'running' ? 'Execução em andamento'
        : x.status === 'error' ? 'Execução não concluiu'
        : 'Execução registrada',
      tom: x.status === 'ok' ? 'success' : x.status === 'error' ? 'warning' : 'neutral',
    }));
  } catch {
    return [];
  }
}

/**
 * O catálogo desta corretora: TODOS os Auxiliares globais, com o estado dela.
 *
 * Nenhum Auxiliar é escondido. Os que ela não pode ligar aparecem dizendo
 * exatamente por quê — "conecte o portal da seguradora" ou "em breve" — em vez
 * de simplesmente não estarem lá. Tela que esconde é tela que faz o corretor
 * achar que o produto não faz aquilo.
 */
export async function catalogoDaCorretora(
  supabase: SupabaseClient,
  companyId: string,
): Promise<{ ok: true; itens: ItemDoCatalogo[] }> {
  const [tpl, inst, conectores, prontos, rotinas] = await Promise.all([
    lerTemplates(supabase),
    supabase.from('tenant_auxiliaries')
      .select('id, slug, status, last_run_at')
      .eq('company_id', companyId),
    supabase.from('connector_templates').select('slug, name, scope'),
    conexoesDaCorretora(supabase, companyId),
    supabase.from('routines')
      .select('id, tenant_auxiliary_id')
      .eq('company_id', companyId)
      .not('tenant_auxiliary_id', 'is', null),
  ]);

  const instalado = new Map<string, any>();
  for (const i of inst.data ?? []) {
    if (i.status !== 'uninstalled' && i.status !== 'archived') instalado.set(i.slug, i);
  }

  const nomeConector = new Map<string, string>();
  const deplataforma = new Set<string>();
  for (const c of conectores.data ?? []) {
    nomeConector.set(c.slug, c.name);
    if ((c as any).scope === SCOPE_PLATAFORMA) deplataforma.add(c.slug);
  }

  const rotinasPorAux = new Map<string, string[]>();
  for (const r of rotinas.data ?? []) {
    const k = (r as any).tenant_auxiliary_id as string;
    rotinasPorAux.set(k, [...(rotinasPorAux.get(k) ?? []), String((r as any).id)]);
  }

  // SPEC-131-B — a prova REAL de cada aplicativo instalado (conserta o Histórico que mentia, laudo I2 F7)
  const instalados = Array.from(instalado.values());
  const execucoes = new Map<string, { n: number; ultima: string | null }>();
  await Promise.all(instalados.map(async (i: any) => {
    const ids = rotinasPorAux.get(i.id) ?? [];
    if (ids.length === 0) return;
    execucoes.set(i.id, await execucoesDasRotinas(supabase, companyId, ids));
  }));
  const temRenovacao = instalado.has('renovacao');
  const renovacoesNoMes = temRenovacao ? await renovacoesCalculadasNoMes(supabase, companyId) : null;

  const itens: ItemDoCatalogo[] = (tpl.data ?? [])
    .filter((t: any) => {
      // Auxiliar privado só aparece para o dono. Global aparece para todas.
      const vis = t.default_config?.visibility;
      return !vis || vis.type !== 'private' || vis.company_id === companyId;
    })
    .map((t: any) => {
      const exigidos: string[] = Array.isArray(t.required_connectors) ? t.required_connectors : [];
      const pendentes = exigidos
        .filter((s) => !prontos.has(s))
        .map((s) => ({
          slug: s,
          // SPEC-131-B: nunca o slug cru na tela
          nome: nomeConector.get(s) ?? NOME_HUMANO_DA_CONEXAO[s] ?? 'uma conexão',
          onde: ONDE_CONECTAR[s] ?? '/dashboard/personalizacao/conectores',
        }));

      const i = instalado.get(t.slug) ?? null;
      const estadoCatalogo: EstadoCatalogo =
        t.catalog_state === 'coming_soon' ? 'coming_soon' : 'available';

      const visual = APLICATIVO_VISUAL[t.slug] ?? VISUAL_PADRAO;
      const iconeDoBanco = typeof t.icon === 'string' && ICONES_CONHECIDOS.has(t.icon) ? t.icon : null;
      const exec = i?.id ? execucoes.get(i.id) : undefined;
      const ultimaPorRotina = exec?.ultima ?? null;
      const ultimaPorInstalacao: string | null = i?.last_run_at ?? null;
      const ultima = [ultimaPorRotina, ultimaPorInstalacao].filter(Boolean).sort().pop() ?? null;
      const conexoes: ConexaoDoAplicativo[] = exigidos
        .filter((s) => !deplataforma.has(s) && !s.startsWith('internal_'))
        .map((s) => ({
          slug: s,
          nome: nomeConector.get(s) ?? NOME_HUMANO_DA_CONEXAO[s] ?? 'Conexão',
          pronto: prontos.has(s),
          onde: ONDE_CONECTAR[s] ?? LINK_CONECTORES,
        }));

      return {
        template_id: t.id,
        slug: t.slug,
        nome: t.name,
        headline: t.headline ?? null,
        categorias: Array.isArray(t.categories) ? t.categories : [],
        estado_catalogo: estadoCatalogo,
        estado: derivarEstado(estadoCatalogo, i?.status ?? null, pendentes.length),
        o_que_faz: lerTarefas(t.what_it_does),
        promessa: t.value_promise ?? null,
        fontes: Array.isArray(t.data_sources) ? t.data_sources : [],
        falta_para_existir: t.missing_for_launch ?? null,
        descricao: t.description ?? null,
        resumo: t.short_description ?? null,
        conectores_pendentes: pendentes,
        conectores_prontos: exigidos.filter((s) => prontos.has(s)),
        instalado: Boolean(i),
        install_id: i?.id ?? null,
        // SPEC-131-B (I2 F7): a última execução vem de `routine_runs` — `last_run_at` ficava NULL com 18 execuções
        ultima_execucao: ultima,
        rotinas: i?.id ? (rotinasPorAux.get(i.id)?.length ?? 0) : 0,
        tela_de_execucao: TELA_DE_EXECUCAO[t.slug] ?? null,
        icone: iconeDoBanco ?? visual.icone,
        matiz: visual.matiz,
        cover_url: typeof t.cover_url === 'string' && /^https:\/\//.test(t.cover_url) ? t.cover_url : null,
        faq: lerFaq(t.faq),
        destaque: typeof t.featured_rank === 'number' ? t.featured_rank : null,
        conexoes,
        prova: {
          execucoes: exec?.n ?? 0,
          ultima_execucao: ultima,
          renovacoes_no_mes: t.slug === 'renovacao' ? renovacoesNoMes : null,
        },
        sem_rotina: APLICATIVOS_SEM_ROTINA.has(t.slug),
      };
    })
    // Ligados primeiro, depois o que dá para ligar, e "em breve" por último.
    .sort((a, b) => {
      const peso: Record<EstadoDoCard, number> = {
        ligado: 0, pausado: 1, disponivel: 2, falta_conectar: 3, em_breve: 4,
      };
      const d = peso[a.estado] - peso[b.estado];
      return d !== 0 ? d : a.nome.localeCompare(b.nome, 'pt-BR');
    });

  return { ok: true as const, itens };
}

/** Um Auxiliar, para a página dele. */
export async function auxiliarPorSlug(
  supabase: SupabaseClient,
  companyId: string,
  slug: string,
): Promise<ItemDoCatalogo | null> {
  const { itens } = await catalogoDaCorretora(supabase, companyId);
  return itens.find((i) => i.slug === slug) ?? null;
}

/**
 * Pode ligar? A resposta e o motivo, no mesmo lugar.
 *
 * O motivo importa tanto quanto a resposta: um botão desabilitado sem
 * explicação faz o corretor achar que o produto está quebrado.
 */
export function podeLigar(item: ItemDoCatalogo): { pode: boolean; motivo?: string } {
  if (item.estado_catalogo === 'coming_soon') {
    return {
      pode: false,
      motivo: item.falta_para_existir
        ? `Ainda não está pronto. ${item.falta_para_existir}`
        : 'Ainda não está pronto.',
    };
  }
  if (item.conectores_pendentes.length > 0) {
    const nomes = item.conectores_pendentes.map((c) => c.nome).join(' e ');
    return { pode: false, motivo: `Conecte ${nomes} para poder ligar.` };
  }
  return { pode: true };
}
