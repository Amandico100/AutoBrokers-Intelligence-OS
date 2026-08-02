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
}

/**
 * A tela onde cada Auxiliar é operado, quando ele tem uma.
 *
 * `checklist-6h` é a antiga `/dashboard/briefing` — 828 linhas que mostram o
 * briefing do dia. Ela mudou de casa inteira: apagar o conteúdo e mandar o
 * corretor para a ficha do Auxiliar teria deixado ele sem o briefing.
 *
 * As outras duas ainda moram sob `galeria/` e o port é dívida registrada.
 */
const TELA_DE_EXECUCAO: Record<string, string> = {
  'checklist-6h': '/dashboard/auxiliares/checklist-6h/hoje',
  'follow-up-whatsapp': '/dashboard/auxiliares/galeria/follow-up-whatsapp',
  'resumo-atendimentos': '/dashboard/auxiliares/galeria/resumo-atendimentos',
};

export const CATEGORIAS: Record<string, { rotulo: string; emoji: string }> = {
  dinheiro_que_volta: { rotulo: 'Dinheiro que volta', emoji: '💰' },
  dinheiro_novo:      { rotulo: 'Dinheiro novo',      emoji: '📈' },
  cliente_blindado:   { rotulo: 'Cliente blindado',   emoji: '🤝' },
  negociacao:         { rotulo: 'Negociação',         emoji: '⚖️' },
  protecao_carteira:  { rotulo: 'Proteção',           emoji: '🛡️' },
  tempo_livre:        { rotulo: 'Tempo livre',        emoji: '⏱️' },
};

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
    supabase.from('auxiliary_templates')
      .select('id, slug, name, headline, categories, catalog_state, data_sources, ' +
              'what_it_does, value_promise, missing_for_launch, description, ' +
              'short_description, required_connectors, default_config')
      .eq('status', 'active')
      .eq('is_active', true),
    supabase.from('tenant_auxiliaries')
      .select('id, slug, status, last_run_at')
      .eq('company_id', companyId),
    supabase.from('connector_templates').select('slug, name'),
    conexoesDaCorretora(supabase, companyId),
    supabase.from('routines')
      .select('tenant_auxiliary_id')
      .eq('company_id', companyId)
      .not('tenant_auxiliary_id', 'is', null),
  ]);

  const instalado = new Map<string, any>();
  for (const i of inst.data ?? []) {
    if (i.status !== 'uninstalled' && i.status !== 'archived') instalado.set(i.slug, i);
  }

  const nomeConector = new Map<string, string>();
  for (const c of conectores.data ?? []) nomeConector.set(c.slug, c.name);

  const rotinasPorAux = new Map<string, number>();
  for (const r of rotinas.data ?? []) {
    const k = (r as any).tenant_auxiliary_id as string;
    rotinasPorAux.set(k, (rotinasPorAux.get(k) ?? 0) + 1);
  }

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
          nome: nomeConector.get(s) ?? s,
          onde: ONDE_CONECTAR[s] ?? '/dashboard/personalizacao/conectores',
        }));

      const i = instalado.get(t.slug) ?? null;
      const estadoCatalogo: EstadoCatalogo =
        t.catalog_state === 'coming_soon' ? 'coming_soon' : 'available';

      return {
        template_id: t.id,
        slug: t.slug,
        nome: t.name,
        headline: t.headline ?? null,
        categorias: Array.isArray(t.categories) ? t.categories : [],
        estado_catalogo: estadoCatalogo,
        estado: derivarEstado(estadoCatalogo, i?.status ?? null, pendentes.length),
        o_que_faz: Array.isArray(t.what_it_does) ? t.what_it_does : [],
        promessa: t.value_promise ?? null,
        fontes: Array.isArray(t.data_sources) ? t.data_sources : [],
        falta_para_existir: t.missing_for_launch ?? null,
        descricao: t.description ?? null,
        resumo: t.short_description ?? null,
        conectores_pendentes: pendentes,
        conectores_prontos: exigidos.filter((s) => prontos.has(s)),
        instalado: Boolean(i),
        install_id: i?.id ?? null,
        ultima_execucao: i?.last_run_at ?? null,
        rotinas: i?.id ? (rotinasPorAux.get(i.id) ?? 0) : 0,
        tela_de_execucao: TELA_DE_EXECUCAO[t.slug] ?? null,
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
