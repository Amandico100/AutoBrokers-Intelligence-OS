// SPEC-064 Bloco B/E — Entregas: tudo que o AutoBrokers fez pela corretora,
// numa linha do tempo só.
//
// O menu tinha TRÊS itens para a mesma pergunta — "o que já aconteceu aqui?":
//
//     Atividades   agent_activities        o que os agentes fizeram
//     Histórico    conversations           o que você conversou com o chat
//     Pesquisas    research_*              o que você mandou conferir
//
// E ainda faltavam dois que não tinham tela nenhuma: os **artifacts** (o
// entregável de primeira classe, que o corretor abre e manda ao cliente) e as
// **execuções de auxiliar**. O produto produzia e não mostrava.
//
// Três itens de menu para a mesma pergunta é como um menu vira lista. Aqui é
// um lugar só, com filtro por tipo — o mesmo princípio de "o menu não cresce".
//
// Nada aqui é motor novo: são leituras das tabelas que já existem,
// normalizadas numa forma comum. Não há tabela de "entrega".
//
// SPEC-078 Bloco F — e agora TUDO que a lista mostra tem para onde ir.
//
// 📊 17/08/2026, o que o Founder descreveu como "não consigo acessar as coisas
// que ficam prontas", medido linha a linha:
//
//     36 artifacts        href: null       não existia rota de visualização
//     77 briefings        href errado      levavam ao CARTÃO do Auxiliar
//    135 agent_activities href: null       nenhum destino
//
// Uma lista de entregas em que a entrega não abre não é uma lista de entregas:
// é um aviso de que alguma coisa aconteceu em algum lugar.
//
// SPEC-078 Bloco F.3 — e a SEXTA fonte, que era a maior de todas:
//
//     32 routine_runs     invisíveis    nenhuma fonte lia a tabela
//      4 auxiliary_runs   visíveis      a fonte "execuções" era só esta
//
// Oito vezes mais trabalho registrado do lado de fora da lista do que dentro
// dela. O único lugar que mostrava `routine_runs` era `/dashboard/auxiliares/
// rotinas` — a página que a SPEC-078 C.4 absorve. F.3 é PRÉ-REQUISITO de C.4
// por isso: absorver aquela página sem trazer o histórico para cá apagaria a
// única prova de que alguma coisa rodou.
//
// ─────────────────────────────────────────────────────────────────────────────
// SPEC-095 BLOCO A — a lista passa a DIZER o que cada coisa é.
//
// 📊 04/09/2026, a queixa do Founder sobre esta tela, medida:
//
//     40 pares duplicados   9,8% da lista e 32,0% da lente "Documentos": cada
//                           briefing entrava DUAS vezes (`briefing:` e
//                           `artifact:`), mesmo href, 3 s de diferença
//     origem = a.kind cru   a linha dizia "report", em inglês, enquanto o
//                           detalhe traduzia para "Relatório"
//     79 peças, 16 títulos  79,7% dos títulos se repetiam
//     35 peças de teste     100% dos relatórios "do chat" da Resulta eram
//                           canário de execução de SPEC, e nada os distinguia
//
// Nenhum desses defeitos trava. Todos respondem 200 (CLAUDE.md §9.5).
//
// Três mudanças, e nenhuma tabela nova:
//   A.4a  a publicação COM artifact é DOBRADA no card do artifact — o card que
//         fica é o do artifact, porque é ele que carrega o achado no título
//   A.4b  peça de teste (`tags @> {canario}`) não entra na biblioteca
//   A.3   o card devolve tipo humano · produtor · período · versões · etiqueta,
//         e o estado da entrega vira ETIQUETA em vez de comer o resumo
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { ondeAbrirAuxiliar } from '@/lib/auxiliaries/catalog';
import type { IconName } from '@/lib/icons';
import {
  ehPecaDeTeste,
  periodoDoRelatorio,
  produtor,
  tipoDoRelatorio,
} from '@/lib/relatorios/tipos';

export const dynamic = 'force-dynamic';

/** Os tipos que o corretor reconhece — não as tabelas que os produzem. */
export type TipoDeEntrega = 'documento' | 'conversa' | 'trabalho' | 'pesquisa';

interface Entrega {
  id: string;
  tipo: TipoDeEntrega;
  titulo: string;
  detalhe: string | null;
  quando: string;
  /** Para onde o corretor vai quando clicar. Null = não há para onde ir ainda. */
  href: string | null;
  /** Rótulo curto de origem: "Cobrança Feita", "Checklist das 6h"… */
  origem: string | null;

  // ── SPEC-095 A.3 · o que o card precisa dizer ────────────────────────────
  /** "Pulso 360", "Briefing do dia", "Conversa"… nunca a `template_key`. */
  tipoHumano?: string;
  /**
   * A chave do ícone no registro único (`lib/icons.ts`).
   *
   * Quem decide o ícone é o mesmo mapa que decide o tipo humano — mandá-lo daqui
   * evita que a tela faça uma busca reversa por `tipoHumano` para reencontrar a
   * linha do mapa que a rota já tinha em mãos.
   */
  icone?: IconName;
  /** Quem produziu, em português. */
  produtor?: string;
  /**
   * `declarado` = o publicador gravou `subject_ref.produtor`.
   * `inferido`  = veio do mapa por origin + template_key (`legacy_inferred`).
   * O card NÃO imprime a palavra; ela existe para o guarda e para a próxima
   * SPEC saber quantas peças ainda dependem do palpite.
   */
  produtorOrigem?: 'declarado' | 'inferido';
  /** O período de que a peça fala — não a hora em que foi escrita. */
  periodo?: string;
  /** Uma etiqueta, a mais forte. Ausente quando está tudo em ordem. */
  etiqueta?: string;
  /** `artifacts.current_version` — o card diz "N versões" quando > 1. */
  versoes?: number;
  /** A peça nasceu de um teste do produto. */
  teste?: boolean;
}

const LIMITE_POR_FONTE = 120;

/**
 * As colunas de `artifacts` que sustentam o card (SPEC-095 A.3 / emenda E3).
 *
 * 📊 04/09/2026 a consulta trazia `id, title, subtitle, kind, status,
 * created_at` — seis colunas. Os campos novos exigem CINCO a mais, e sem elas
 * o filtro de canário filtraria por uma coluna que a consulta não trouxe:
 *
 *     template_key      → tipo humano e ícone
 *     subject_ref       → produtor declarado e período
 *     current_version   → "N versões"
 *     tags              → peça de teste (e o filtro do A.4b)
 *     origin            → o produtor inferido, quando o template não diz
 *
 * 🔴 Numa constante e numa linha só de propósito: as DUAS consultas de
 * `artifacts` desta rota (a lista e a contagem de arquivados) projetam a mesma
 * coisa, e o supabase-js lê esta string em tempo de tipo — concatenada, ele
 * desiste e todo campo abaixo perde o tipo.
 */
const COLUNAS_DE_ARTIFACT =
  'id, title, subtitle, kind, status, created_at, archived_at, template_key, subject_ref, current_version, tags, origin';

/**
 * O Auxiliar dono de cada tipo de briefing.
 *
 * 📊 17/08/2026: os dois tipos que existem em `briefing_publications`
 * (`daily_operational`, 65 linhas; `weekly_executive`, 12) são produzidos pelo
 * mesmo Auxiliar. O mapa existe para que o terceiro tipo, quando nascer, seja
 * uma linha aqui — e não um `if` escondido no meio do laço.
 */
const AUXILIAR_DO_BRIEFING: Record<string, string> = {
  daily_operational: 'checklist-6h',
  weekly_executive: 'checklist-6h',
};

const AUXILIAR_PADRAO_DO_BRIEFING = 'checklist-6h';

/**
 * Para onde vai o clique numa atividade de agente.
 *
 * `agent_activities` só tem `category`, `title` e `detail` — não guarda o id da
 * coisa sobre a qual fala. Então o destino honesto é a TELA do assunto, não um
 * registro específico: quem clica em "varredura de qualidade concluída" quer
 * ver as conversas auditadas.
 *
 * 📊 17/08/2026, as categorias que existem no banco:
 *   atendimentos 108 · qualidade 26 · auxiliares 1  → 135 de 135 com destino.
 *
 * Categoria nova, sem entrada aqui, devolve null de propósito — e a lista
 * mostra a linha SEM cara de clicável (EntregasClient), em vez de oferecer um
 * clique que não leva a lugar nenhum.
 */
const DESTINO_DA_ATIVIDADE: Record<string, string> = {
  atendimentos: '/dashboard/atendimentos/conversas',
  qualidade: '/dashboard/atendimentos/conversas',
  auxiliares: '/dashboard/auxiliares',
};

/** A publicação de briefing, na forma mínima de que o card do artifact precisa. */
interface PublicacaoDeBriefing {
  id: string;
  briefing_type: string | null;
  delivery_status: string | null;
  critical_count: number | null;
  recommendation_count: number | null;
}

/**
 * A ETIQUETA da linha — uma só, a mais forte (SPEC-095 A.3).
 *
 * 📊 04/09/2026 o estado da entrega SUBSTITUÍA o resumo (`route.ts:257`): um
 * briefing entregue pela metade perdia a única linha que dizia o que ele achou,
 * e ganhava no lugar uma frase sobre canal. O estado vira etiqueta; o resumo
 * fica. É a mesma lição do §3 ③ (Datadog): a evidência mora DENTRO do card.
 *
 * 🔴 A ORDEM: um problema de ENTREGA vence "precisa de você". A SPEC lista os
 * dois na ordem inversa, e o guarda [4] mede o contrário — com razão: uma peça
 * que não chegou ao destino é um defeito do sistema, e uma recomendação é um
 * pedido de atenção do conteúdo. Quem não recebeu o relatório não tem como
 * agir sobre a recomendação dele.
 *
 * `sent` não devolve etiqueta nenhuma de propósito: etiqueta que aparece
 * sempre é etiqueta que ninguém lê.
 */
function etiquetaDaLinha(pub: PublicacaoDeBriefing | null): string | undefined {
  if (!pub) return undefined;
  if ((pub.critical_count ?? 0) > 0) return 'crítico';
  switch (pub.delivery_status) {
    case 'partial':
      return 'entrega parcial';
    case 'failed':
      return 'não entregue';
    case 'skipped':
      return 'entrega adiada';
    // `pending` só existe se o executor não rodou (SPEC-064 Bloco E). Ele ficava
    // em 100% das publicações porque `delivery_policy.decidir()` não tinha
    // chamador nenhum. Se voltar a aparecer aqui, é sinal de regressão — e por
    // isso ele continua visível, agora como etiqueta.
    case 'pending':
      return 'entrega não decidida';
    default:
      break;
  }
  if ((pub.recommendation_count ?? 0) > 0) return 'precisa de você';
  return undefined;
}

/**
 * A linha de resumo de uma execução de rotina.
 *
 * 🔴 Só a PRIMEIRA linha do preview entra aqui, e cortada. O relatório da
 * cobrança carrega CPF/CNPJ e telefone de segurado a partir da seção "Clientes
 * encontrados" (`billing_collection.py:1069-1140`); a primeira linha é o
 * cabeçalho ("Auxiliar de Cobranca — <nome da rotina>"). Despejar 500
 * caracteres numa lista poria dado de segurado numa tela de varredura, onde
 * ninguém foi ler isso. Quem quer o conteúdo abre a execução.
 *
 * `delegated` é o estado que a projeção de Work Run grava
 * (`routine_engine.py:553`): o trabalho existe, mas quem responde por ele é o
 * Work Run. Dizer isso é melhor que mostrar "executando como Work Run", que é
 * texto de máquina.
 */
function detalheDaExecucao(
  status: string | null,
  erro: string | null,
  preview: string | null,
): string | null {
  if (status === 'error') return erro || 'A execução falhou';
  if (status === 'running') return 'Em andamento';
  if (status === 'delegated') return 'Delegada ao motor de trabalhos';
  const primeira = (preview || '').split('\n').find((l) => l.trim().length > 0);
  if (!primeira) return null;
  return primeira.trim().slice(0, 140);
}

/**
 * A query string do pedido, sem presumir a forma do `NextRequest`.
 *
 * 🔴 Os guardas chamam `GET(...)` com um objeto sintético, e os dois da
 * SPEC-078 o chamam com `{}` — sem `nextUrl` e sem `url`. Ler direto
 * `req.nextUrl.searchParams` transformaria "esta rota não lê query" em
 * "esta rota explode no guarda", que é vermelho por endereço errado.
 */
function parametrosDe(req: NextRequest): URLSearchParams {
  try {
    const doNext = (req as unknown as { nextUrl?: { searchParams?: URLSearchParams } })?.nextUrl;
    if (doNext?.searchParams) return doNext.searchParams;
    const bruta = (req as unknown as { url?: string })?.url;
    if (bruta) return new URL(bruta).searchParams;
  } catch {
    /* pedido sem URL — a lista abre no modo normal */
  }
  return new URLSearchParams();
}

export async function GET(req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  // SPEC-095 A.4c — `?arquivados=1` mostra o que a limpeza tirou da biblioteca.
  //
  // 📊 A limpeza do BLOCO B.4 arquiva 35 peças de teste da Resulta. Arquivar é
  // reversível por UPDATE, mas só vale como decisão se o Founder puder OLHAR o
  // que saiu. Um LINK discreto no fim da lista, nunca uma aba: a Notion removeu
  // a dela (§3 ⑤) e 📊 arquivados = 0 no banco de hoje — uma aba permanente para
  // uma lista quase sempre vazia é um item de menu que envelhece vazio.
  //
  // O modo ignora a lente: só peça arquivável entra (conversa e trabalho não se
  // arquivam), e a peça de teste aparece aqui — é exatamente o que ele existe
  // para mostrar.
  if (parametrosDe(req).get('arquivados') === '1') {
    const { data: arquivados } = await supabase.from('artifacts')
      .select(COLUNAS_DE_ARTIFACT)
      .eq('company_id', empresa)
      .not('archived_at', 'is', null)
      .order('archived_at', { ascending: false }).limit(LIMITE_POR_FONTE);

    const itensArquivados = (arquivados ?? []).map((a) => cardDeArtifact(a, null, true));
    return NextResponse.json({
      ok: true,
      arquivados: true,
      itens: itensArquivados,
      contagem: { documento: itensArquivados.length },
    });
  }

  const [
    artefatos,
    briefings,
    execucoes,
    conversas,
    atividades,
    auxiliares,
    rotinas,
    execucoesDeRotina,
    quantosArquivados,
  ] = await Promise.all([
    supabase.from('artifacts')
      .select(COLUNAS_DE_ARTIFACT)
      .eq('company_id', empresa).is('archived_at', null)
      // SPEC-095 A.4b — a peça de teste não entra na biblioteca da corretora.
      // 📊 100% dos relatórios "do chat" da Resulta são canário de execução de
      // SPEC (14 Raio-X + 14 Radar em 18/08, 6 Pulsos em 03–04/09), e nada os
      // distinguia de um relatório que o dono pediu. `tags` é `'{}'` em 136/136
      // linhas de hoje — nunca NULL —, então o `not cs` não engole ninguém.
      .not('tags', 'cs', '{canario}')
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('briefing_publications')
      // `artifact_id` entra aqui porque 📊 40 das 46 publicações da Resulta JÁ
      // TÊM o relatório renderizado — e, desde o A.4a, é ele que vira o card.
      // `critical_count`/`recommendation_count` entram para a ETIQUETA (A.3).
      .select('id, headline, summary_text, briefing_type, published_at, created_at, delivery_status, critical_count, recommendation_count, artifact_id')
      .eq('company_id', empresa)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('auxiliary_runs')
      .select('id, tenant_auxiliary_id, status, run_type, error_message, started_at, finished_at, created_at')
      .eq('company_id', empresa)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('conversations')
      .select('id, session_id, title, channel, last_message_preview, updated_at, created_at')
      .eq('company_id', empresa)
      .order('updated_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('agent_activities')
      .select('id, category, title, detail, created_at')
      .eq('company_id', empresa)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    // Para dar NOME ao auxiliar que rodou. Sem isto a linha diria
    // "execução 4f2a-…", que não significa nada para o corretor.
    supabase.from('tenant_auxiliaries')
      .select('id, name, slug')
      .eq('company_id', empresa),

    // A rotina dá NOME e DONO à execução. 📊 `routines.tenant_auxiliary_id` é
    // NOT NULL desde a migration 20260817_03 (SPEC-078 C.1), então o dono
    // sempre existe — e "Cobrança Feita rodou" só é possível por causa disso.
    supabase.from('routines')
      .select('id, name, tenant_auxiliary_id')
      .eq('company_id', empresa),

    // 🔴 O filtro é `company_id` e não `routine_id in (…)` de propósito. Toda
    // outra fonte desta rota se protege com `.eq('company_id', empresa)`; uma
    // que se protegesse por lista de ids seria a exceção que o próximo a copiar
    // o padrão apagaria sem perceber. A coluna nasceu na migration
    // 20260817_04 justamente para que a regra continue verificável por leitura
    // (CLAUDE.md §7 — o backend usa service role; a policy não é a proteção).
    supabase.from('routine_runs')
      .select('id, routine_id, status, output_preview, error, started_at, finished_at')
      .eq('company_id', empresa)
      .order('started_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    // Quantas peças estão arquivadas — só o NÚMERO, para o link discreto do fim
    // da lista. `head: true` não traz linha nenhuma: é uma contagem, não uma
    // sétima fonte.
    supabase.from('artifacts')
      .select(COLUNAS_DE_ARTIFACT, { count: 'exact', head: true })
      .eq('company_id', empresa)
      .not('archived_at', 'is', null),
  ]);

  const nomeAux = new Map<string, { nome: string; slug: string }>();
  for (const a of auxiliares.data ?? []) {
    nomeAux.set(a.id, { nome: a.name ?? a.slug, slug: a.slug });
  }

  // SPEC-095 A.4a — a chave de colapso, escrita: `(artifact_id)`.
  //
  // 📊 40 pares duplicados na lista da Resulta. O briefing das 08:05 entrava
  // como `briefing:` e o relatório dele como `artifact:`, com o MESMO href e 3
  // segundos de diferença — as duas linhas ordenavam juntas, e o corretor via
  // dois cards para uma coisa só.
  //
  // 🔴 O card que FICA é o do artifact, não o do briefing: é ele que carrega o
  // título do achado (BLOCO D), as versões e a peça que abre. A publicação não
  // some — ela é DOBRADA: entrega o produtor e a etiqueta ao card do artifact.
  const publicacaoDoArtifact = new Map<string, PublicacaoDeBriefing>();
  for (const b of briefings.data ?? []) {
    if (b.artifact_id) publicacaoDoArtifact.set(b.artifact_id, b as PublicacaoDeBriefing);
  }

  const itens: Entrega[] = [];

  for (const a of artefatos.data ?? []) {
    itens.push(cardDeArtifact(a, publicacaoDoArtifact.get(a.id) ?? null, false));
  }

  for (const b of briefings.data ?? []) {
    // A publicação COM artifact já está dobrada no card dele (A.4a). A publicação
    // SEM artifact continua sendo card: 📊 6 das 46 da Resulta, e é o ramo que a
    // 078 F.2 consertou — apagá-lo tiraria da lista o único registro de que
    // aquele dia teve briefing.
    if (b.artifact_id) continue;

    const slugDoBriefing =
      AUXILIAR_DO_BRIEFING[b.briefing_type as string] ?? AUXILIAR_PADRAO_DO_BRIEFING;
    const tipo = tipoDoRelatorio(`briefing.${b.briefing_type ?? ''}`);
    itens.push({
      id: `briefing:${b.id}`,
      tipo: 'documento',
      titulo: b.headline || 'Checklist do dia',
      // O RESUMO fica. O estado da entrega, quando não é o esperado, vira
      // etiqueta — esconder o estado faria a lista parecer saudável enquanto um
      // canal está quebrado, e substituir o resumo por ele apagaria o achado.
      detalhe: b.summary_text ?? null,
      quando: b.published_at || b.created_at,
      // 📊 17/08/2026: o href era a string `/dashboard/auxiliares/checklist-6h`,
      // montada à mão. Esse endereço cai na rota `[slug]`, que renderiza o
      // cartão descritivo do Auxiliar — o corretor clicava no briefing de
      // quinta-feira e recebia a propaganda do Auxiliar. Eram 26 briefings da
      // AutoFleet apontando para a descrição do trabalho em vez do trabalho.
      //
      // A tela de execução do Auxiliar dono vem do mapa único em
      // lib/auxiliaries/catalog.ts — nunca concatenada aqui.
      href: ondeAbrirAuxiliar(slugDoBriefing),
      origem: 'Checklist das 6h',
      tipoHumano: tipo.tipoHumano,
      icone: tipo.icone,
      produtor: 'Checklist das 6h',
      produtorOrigem: 'inferido',
      periodo: periodoDoRelatorio(null, b.published_at || b.created_at),
      etiqueta: etiquetaDaLinha(b as PublicacaoDeBriefing),
      teste: false,
    });
  }

  for (const e of execucoes.data ?? []) {
    const aux = e.tenant_auxiliary_id ? nomeAux.get(e.tenant_auxiliary_id) : null;
    itens.push({
      id: `run:${e.id}`,
      tipo: 'trabalho',
      titulo: aux ? `${aux.nome} rodou` : 'Auxiliar rodou',
      detalhe: e.status === 'failed'
        ? (e.error_message || 'Falhou')
        : (e.run_type === 'manual' ? 'Execução manual' : null),
      quando: e.finished_at || e.started_at || e.created_at,
      // Mesma fonte única do briefing: quem tem tela de execução abre nela.
      // Uma execução do `checklist-6h` levava ao cartão; agora leva ao que ele
      // produziu.
      href: ondeAbrirAuxiliar(aux?.slug),
      origem: aux?.nome ?? null,
      tipoHumano: 'Execução de Auxiliar',
      icone: 'auxiliares',
      produtor: aux?.nome ?? 'Auxiliar',
    });
  }

  // SPEC-078 F.3 — as execuções de ROTINA, a fonte que faltava.
  //
  // O href nunca é null e nunca é o cartão do Auxiliar: é a página da própria
  // execução, `/dashboard/entregas/rotina/[runId]`, que mostra o relatório
  // INTEIRO (F.4). Levar ao cartão seria o mesmo defeito que F.2 acabou de
  // consertar nos briefings — clicar no trabalho e receber a propaganda.
  const rotinaPorId = new Map<string, { nome: string; auxiliarId: string | null }>();
  for (const r of rotinas.data ?? []) {
    rotinaPorId.set(r.id, { nome: r.name ?? 'Rotina', auxiliarId: r.tenant_auxiliary_id ?? null });
  }

  for (const e of execucoesDeRotina.data ?? []) {
    const rot = rotinaPorId.get(e.routine_id);
    const aux = rot?.auxiliarId ? nomeAux.get(rot.auxiliarId) : null;
    itens.push({
      id: `rotina:${e.id}`,
      tipo: 'trabalho',
      // O nome do Auxiliar vem primeiro porque é o que o corretor instalou e
      // reconhece. A rotina é o agendamento dentro dele — e 📊 as duas que
      // existem se chamam a mesma coisa ("Cobranca de boletos atrasados"),
      // então o nome da rotina sozinho não distinguiria nada.
      titulo: aux ? `${aux.nome} rodou` : `${rot?.nome ?? 'Rotina'} rodou`,
      detalhe: detalheDaExecucao(e.status, e.error, e.output_preview),
      quando: e.finished_at || e.started_at,
      href: `/dashboard/entregas/rotina/${e.id}`,
      origem: aux?.nome ?? rot?.nome ?? null,
      tipoHumano: 'Execução de rotina',
      icone: 'auxiliares',
      produtor: aux?.nome ?? rot?.nome ?? 'Auxiliar',
    });
  }

  for (const c of conversas.data ?? []) {
    const doChat = c.channel === 'web' || !c.channel;
    itens.push({
      id: `conversa:${c.id}`,
      tipo: 'conversa',
      titulo: c.title || 'Conversa com o AutoBrokers',
      detalhe: c.last_message_preview ?? null,
      quando: c.updated_at || c.created_at,
      href: doChat
        ? `/dashboard/chat?session=${c.session_id ?? ''}`
        : '/dashboard/atendimentos/conversas',
      origem: doChat ? 'Chat' : 'Atendimento',
      tipoHumano: doChat ? 'Conversa' : 'Atendimento',
      icone: doChat ? 'conversas' : 'atendimentos',
      produtor: doChat ? 'AutoBrokers' : 'Atendimento',
    });
  }

  for (const a of atividades.data ?? []) {
    itens.push({
      id: `atividade:${a.id}`,
      tipo: 'trabalho',
      titulo: a.title || 'Atividade',
      detalhe: a.detail ?? null,
      quando: a.created_at,
      // 📊 17/08/2026: era `href: null` fixo — 135 linhas sem destino, e com a
      // mesma aparência de linha clicável das outras.
      href: DESTINO_DA_ATIVIDADE[a.category ?? ''] ?? null,
      origem: a.category ?? null,
      tipoHumano: 'Atividade do agente',
      icone: 'historico',
      produtor: a.category ?? 'AutoBrokers',
    });
  }

  itens.sort((x, y) => (y.quando || '').localeCompare(x.quando || ''));

  return NextResponse.json({
    ok: true,
    itens: itens.slice(0, 400),
    // Contagem por tipo, para os filtros mostrarem números reais.
    contagem: itens.reduce<Record<string, number>>((acc, i) => {
      acc[i.tipo] = (acc[i.tipo] ?? 0) + 1;
      return acc;
    }, {}),
    // O número do link discreto "ver arquivados (N)". Zero esconde o link.
    arquivadosN: quantosArquivados.count ?? 0,
  });
}

/** A linha de `artifacts`, na forma que a rota já projetou. */
interface LinhaDeArtifact {
  id: string;
  title: string | null;
  subtitle: string | null;
  kind: string | null;
  created_at: string;
  archived_at: string | null;
  template_key: string | null;
  subject_ref: unknown;
  current_version: number | null;
  tags: unknown;
  origin: string | null;
}

/**
 * O card de uma peça — a anatomia da SPEC-095 A.3.
 *
 * Uma função só, usada pela lista e pelo modo arquivados, porque as duas
 * respondem a mesma pergunta ("o que é esta peça?") e responder em dois lugares
 * é como as duas telas passaram a discordar (o motivo de `lib/relatorios/
 * tipos.ts` existir).
 */
function cardDeArtifact(
  a: LinhaDeArtifact,
  pub: PublicacaoDeBriefing | null,
  arquivado: boolean,
): Entrega {
  const tipo = tipoDoRelatorio(a.template_key);
  const quem = produtor(a.origin, a.template_key, a.subject_ref);
  return {
    id: `artifact:${a.id}`,
    tipo: 'documento',
    // 🔴 O título é o que a peça ACHOU (BLOCO D), não o lote de onde ela saiu.
    titulo: a.title || 'Documento sem título',
    detalhe: a.subtitle ?? null,
    quando: a.created_at,
    // 📊 17/08/2026: aqui havia `href: null` com o comentário "ainda não há
    // rota de tenant". A rota agora existe — `/dashboard/entregas/[artifactId]`,
    // com filtro por company_id no repositório (CLAUDE.md §7).
    href: `/dashboard/entregas/${a.id}`,
    // 📊 04/09/2026 esta linha era `a.kind` cru: a lista dizia "report", em
    // inglês, enquanto o detalhe da mesma peça dizia "Relatório".
    origem: quem.nome,
    tipoHumano: tipo.tipoHumano,
    icone: tipo.icone,
    // A.4a diz que o card do briefing recebe `produtor = 'Checklist das 6h'` da
    // publicação dobrada — e recebe: `briefing.daily_operational` e
    // `briefing.weekly_executive` apontam para ele no mapa único. Não se lê o
    // produtor DA PUBLICAÇÃO aqui de propósito: isso sobrescreveria um produtor
    // DECLARADO pelo publicador com um palpite derivado do tipo de briefing.
    // O que a publicação dobrada realmente traz de novo é a ETIQUETA.
    produtor: quem.nome,
    produtorOrigem: quem.origem,
    periodo: periodoDoRelatorio(a.subject_ref, a.created_at),
    etiqueta: arquivado ? 'arquivado' : etiquetaDaLinha(pub),
    versoes: a.current_version ?? 1,
    teste: ehPecaDeTeste(a.tags),
  };
}
