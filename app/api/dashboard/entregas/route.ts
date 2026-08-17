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
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { ondeAbrirAuxiliar } from '@/lib/auxiliaries/catalog';

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
}

const LIMITE_POR_FONTE = 120;

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

/**
 * O estado da entrega, em português — e só quando ele não é o esperado.
 *
 * `sent` devolve null de propósito: dizer "entregue" numa lista de coisas
 * entregues é ruído. O que precisa aparecer é o que saiu do trilho.
 *
 * `pending` só existe se o executor não rodou (SPEC-064 Bloco E). Ele ficava
 * em 100% das publicações porque `delivery_policy.decidir()` não tinha
 * chamador nenhum. Se voltar a aparecer aqui, é sinal de regressão.
 */
function estadoDaEntrega(status: string | null): string | null {
  switch (status) {
    case 'partial':
      return 'Entregue em parte — um dos canais falhou';
    case 'failed':
      return 'Não foi possível entregar em nenhum canal';
    case 'skipped':
      return 'A política adiou a entrega — abra para ver o motivo';
    case 'pending':
      return 'Publicado — a entrega ainda não foi decidida';
    default:
      return null;
  }
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

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  const [
    artefatos,
    briefings,
    execucoes,
    conversas,
    atividades,
    auxiliares,
    rotinas,
    execucoesDeRotina,
  ] = await Promise.all([
    supabase.from('artifacts')
      .select('id, title, subtitle, kind, status, created_at')
      .eq('company_id', empresa).is('archived_at', null)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('briefing_publications')
      // `artifact_id` entra aqui porque 📊 36 das 77 publicações JÁ TÊM o
      // relatório renderizado. Para essas, o destino certo é o documento
      // daquele dia — não a tela "de hoje", que mostra outro conteúdo.
      .select('id, headline, summary_text, briefing_type, published_at, created_at, delivery_status, artifact_id')
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
  ]);

  const nomeAux = new Map<string, { nome: string; slug: string }>();
  for (const a of auxiliares.data ?? []) {
    nomeAux.set(a.id, { nome: a.name ?? a.slug, slug: a.slug });
  }

  const itens: Entrega[] = [];

  for (const a of artefatos.data ?? []) {
    itens.push({
      id: `artifact:${a.id}`,
      tipo: 'documento',
      titulo: a.title || 'Documento sem título',
      detalhe: a.subtitle ?? null,
      quando: a.created_at,
      // 📊 17/08/2026: aqui havia `href: null` com o comentário "ainda não há
      // rota de tenant". A rota agora existe — `/dashboard/entregas/[artifactId]`,
      // com filtro por company_id no repositório (CLAUDE.md §7).
      href: `/dashboard/entregas/${a.id}`,
      origem: a.kind ?? null,
    });
  }

  for (const b of briefings.data ?? []) {
    const slugDoBriefing =
      AUXILIAR_DO_BRIEFING[b.briefing_type as string] ?? AUXILIAR_PADRAO_DO_BRIEFING;
    itens.push({
      id: `briefing:${b.id}`,
      tipo: 'documento',
      titulo: b.headline || 'Checklist do dia',
      // O estado da entrega aparece quando ele NÃO é o esperado. Um briefing
      // que saiu em todos os canais não precisa dizer isso — mas um que ficou
      // pela metade, ou que a política adiou, precisa. Esconder isso faria a
      // lista parecer saudável enquanto um canal está quebrado.
      detalhe: estadoDaEntrega(b.delivery_status) ?? b.summary_text ?? null,
      quando: b.published_at || b.created_at,
      // 📊 17/08/2026: o href era a string `/dashboard/auxiliares/checklist-6h`,
      // montada à mão. Esse endereço cai na rota `[slug]`, que renderiza o
      // cartão descritivo do Auxiliar — o corretor clicava no briefing de
      // quinta-feira e recebia a propaganda do Auxiliar. Eram 26 briefings da
      // AutoFleet apontando para a descrição do trabalho em vez do trabalho.
      //
      // Agora são dois destinos, nesta ordem:
      //   1. o RELATÓRIO daquele dia, quando ele foi renderizado (36 de 77);
      //   2. a tela de execução do Auxiliar dono, lida do mapa único em
      //      lib/auxiliaries/catalog.ts — nunca concatenada aqui.
      href: b.artifact_id
        ? `/dashboard/entregas/${b.artifact_id}`
        : ondeAbrirAuxiliar(slugDoBriefing),
      origem: 'Checklist das 6h',
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
    });
  }

  for (const c of conversas.data ?? []) {
    itens.push({
      id: `conversa:${c.id}`,
      tipo: 'conversa',
      titulo: c.title || 'Conversa com o AutoBrokers',
      detalhe: c.last_message_preview ?? null,
      quando: c.updated_at || c.created_at,
      href: c.channel === 'web' || !c.channel
        ? `/dashboard/chat?session=${c.session_id ?? ''}`
        : '/dashboard/atendimentos/conversas',
      origem: c.channel === 'web' || !c.channel ? 'Chat' : 'Atendimento',
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
  });
}
