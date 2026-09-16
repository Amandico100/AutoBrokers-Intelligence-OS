// SPEC-097 — A OPERAÇÃO TEM UMA CASA. O read model ÚNICO do atendimento (R5).
//
// ─────────────────────────────────────────────────────────────────────────────
// POR QUE ESTE ARQUIVO NASCEU
// ─────────────────────────────────────────────────────────────────────────────
//
// 📊 Medição de 05/09/2026 (SPEC-097 §1), sobre a árvore em `7f3f3eb`:
//
//   §1.1  `atendimentos/route.ts:217-221` terminava numa cascata
//         `closed → HUMAN_REQUESTED → claimed_by → fresh(<48h) → else 'concluido'`.
//         584 de 668 conversas (87,4%) apareciam "encerradas" — e `resolvido_em`
//         era NULL em 728/728. **Ninguém encerrou nada.** O relógio encerrava.
//   §1.2  o único escritor de `claimed_by` gravava `status:'HUMAN_REQUESTED'`
//         junto, e a cascata testava o status ANTES do dono: a coluna "com a
//         equipe" era INALCANÇÁVEL.
//   §1.4  `attendance_sessions` tem 12.755 linhas e 5,8 episódios por contato.
//         O caso é o EPISÓDIO — e ele não tinha elo com a conversa.
//   §1.5  `.limit(120)` sobre 448 conversas da AutoFleet: 73% invisível. E a
//         busca do Histórico era `.filter()` no CLIENTE, sobre esses 120: um
//         protocolo de 60 dias devolvia "nada encontrado".
//   §1.1  o mesmo payload dizia `semana.terminaram: 0` e listava itens
//         "concluido" — duas verdades num JSON só.
//
// 🔴 Nenhum desses defeitos travava nada. Todos respondiam 200 (CLAUDE.md §9.5).
//
// ─────────────────────────────────────────────────────────────────────────────
// AS REGRAS QUE ESTE ARQUIVO É (SPEC-097 §2)
// ─────────────────────────────────────────────────────────────────────────────
//
//   R1  DESFECHO  'concluido' ⇔ `resolvido_em` escrito (da CONVERSA ou do
//                 EPISÓDIO). Nunca deduzido de relógio. Silêncio ⇒ `parado`.
//                 ⛔ E9: `attendance_sessions.status`, que o Atlas fecha por 6h
//                 de silêncio (`attendance_distiller:200-240`, para o RAG), NÃO
//                 é desfecho — a projeção o ignora para ENCERRADO.
//                 🔴 E5: UM relógio — `ultimo_evento_em =
//                 greatest(conversations.last_message_at, sessao.last_event_at)`.
//   R2  DONO      `claimed_by` é dimensão própria e é testado ANTES do status.
//   R3  EPISÓDIO  CASOS é por episódio; a FILA é por CONVERSA ativa (o episódio
//                 corrente dela — E11). Episódio órfão continua caso, rotulado
//                 "sem conversa vinculada" (📊 E7: 42,2% das sessões).
//   R4  ESPERA    só de `work_waits` ativo. Nunca deduzida do texto.
//   R5  UMA FUNÇÃO DE LEITURA. Paginação e busca NO BANCO. `indisponivel` POR
//                 FONTE — nunca zero silencioso.
//   R6  ATENÇÃO   só as 4 razões OBSERVÁVEIS. (E17 tirou `aprovacao_pendente`:
//                 `approval_requests` não tem conversa.)
//   R7  PRÓXIMA AÇÃO  precedência determinística, e a ausência tem NOME.
//   R9  TENANT    `company_id` em TODA consulta. O backend usa service role: a
//                 RLS não protege contra erro de filtro no código (CLAUDE.md §7).
//
// O guarda deste arquivo é `scripts/a-operacao-tem-uma-casa.test.mjs`, que o
// EXECUTA sobre dublês — e `backend/tests/test_o_clique_da_atendente_nao_apaga_da_fila.py`,
// que roda o mesmo arnês por `--fila-json`.

import { carregarNumerosDaCasa, ehNumeroDaCasa } from '@/lib/atendimento/numeros-da-casa';
import { getSupabaseAdmin } from '@/lib/vault/server';
import { type Stage, zeroCountsByStage } from '@/lib/attendance/dispatch-states';

// ─────────────────────────────────────────────────────────────────────────────
// Contratos
// ─────────────────────────────────────────────────────────────────────────────

/** As fontes que a projeção lê. Cada uma pode falhar SOZINHA (R5). */
export type Fonte = 'conversas' | 'sessoes' | 'esperas' | 'trabalhos' | 'aprovacoes';

/** 🔴 R6 — as ÚNICAS razões de atenção. Todas OBSERVÁVEIS, nenhuma inventada.
 *  `sla_at_risk` nunca teve escritor; `aprovacao_pendente` saiu por E17. */
export const RAZOES_DE_ATENCAO = [
  'pediu_pessoa',
  'trabalho_falhou',
  'parado',
  'espera_vencida',
] as const;
export type RazaoDeAtencao = (typeof RAZOES_DE_ATENCAO)[number];

/** 🔴 R7 — a precedência, em ordem. A última é a AUSÊNCIA COM NOME. */
export const PRECEDENCIA_DA_PROXIMA_ACAO = [
  'pessoa',
  'aprovacao',
  'passo_do_trabalho',
  'espera_com_prazo',
  'sem_proxima_acao_declarada',
] as const;
export type RegraDaProximaAcao = (typeof PRECEDENCIA_DA_PROXIMA_ACAO)[number];

export interface Dono {
  id: string;
  nome: string;
}

/** R4 — a espera SEMPRE traz o id da linha de `work_waits` que a produziu.
 *  Espera sem linha é espera DEDUZIDA, e é o que a SPEC proíbe. */
export interface Espera {
  kind: string;
  desde: string | null;
  /** 🔴 O NOME É O DA COLUNA REAL. 📊 05/09/2026, `information_schema.columns`:
   *  `work_waits` tem `vence_em` e **não tem** `due_at` — a projeção pedia as
   *  duas, o PostgREST devolvia 42703 e o `try/catch` engolia o erro, de modo
   *  que `indisponivel.esperas` era `true` em 100% das requisições e NENHUMA
   *  espera chegava à tela. Um campo com o nome errado mente para todo leitor
   *  seguinte (CLAUDE.md §12.1): aqui ele tem o nome do banco. */
  vence_em: string | null;
  vencida: boolean;
  fonte_id: string;
}

export interface ProximaAcao {
  texto: string;
  fonte: string;
  fonte_id: string | null;
  regra: RegraDaProximaAcao;
}

/** U6.1 — as SEIS dimensões do AGORA. */
export interface Agora {
  situacao: string;
  dono: Dono | null;
  esperando: Espera | null;
  ha_quanto_tempo: string | null;
  atencao: RazaoDeAtencao[];
  proxima_acao: ProximaAcao;
}

export interface Caso {
  key: string;
  stage: Stage;
  /** `episodio` quando a linha é um `attendance_sessions`; `conversa` quando não há episódio. */
  kind: 'episodio' | 'conversa';
  conversa_id: string | null;
  session_id: string | null;
  telefone: string | null;
  cliente: string | null;
  /** R12 — O QUE FOI PEDIDO, em uma palavra: "Guincho", "Bateria", "Sinistro".
   *  É a segunda linha do card no celular: sem ela, dez cards parecem iguais. */
  pedido: string | null;
  protocolo: string | null;
  /** R1/E5 — UM relógio de EXIBIÇÃO: o mais recente entre a conversa e o
   *  episódio. É ele que a tela mostra como "último movimento". */
  ultimo_evento_em: string | null;
  /**
   * 🔴 [P1-3] O RELÓGIO DA ORDEM — e ele é o do BANCO, não o derivado.
   *
   * A página é pedida ao banco por `attendance_sessions.last_event_at` (ou, no
   * caso implícito, por `conversations.last_message_at`) e ordenada, aqui, pelo
   * MESMO campo. Ordenar pelo `ultimo_evento_em` (que é o MAIOR dos dois)
   * misturava duas réguas: um episódio antigo numa conversa recente subia na
   * lista sem ter subido na consulta, e caía fora da janela do cursor da página
   * seguinte — sumindo entre a 1 e a 2, em silêncio.
   */
  ordem_em: string | null;
  parado_desde?: string | null;
  parado_ha?: string | null;
  resolvido_em: string | null;
  resolucao_motivo: string | null;
  dono: Dono | null;
  esperando: Espera | null;
  /** R3/E7 — o episódio que ainda não achou a conversa dele. */
  sem_conversa_vinculada?: boolean;
  /** o trabalho travado/falhado ligado a este caso — é por ele que o guarda do
   *  "clique da atendente" encontra o caso destravado na Fila. */
  work_run_id: string | null;
  /** o travamento DURÁVEL do acionamento, quando existe. A Fila usa isto para
   *  não deixar o estado quente do Redis apagar um travamento aberto. */
  unblock_state: string | null;
  agora: Agora;
  // ── o que a TELA lê (a Fila e os Casos de hoje, sem tela nova — R10) ──
  titulo: string;
  detalhe: string;
  quando: string | null;
}

export interface ResumoDaSemana {
  terminaram: number;
  ainda_esperam: number;
  morreram_esperando: number;
  por_motivo: Record<string, number>;
  por_kind: Record<string, number>;
  indisponivel: boolean;
}

export interface Projecao {
  items: Caso[];
  /** ⛔ [P2-7] o termo tinha só curinga (`%%%`, `___`) e não sobrou letra
   *  nenhuma depois da limpeza. A lista volta VAZIA e a tela DIZ por quê — o
   *  acervo inteiro seria a pior resposta, porque tem cara de resultado. */
  busca_invalida?: boolean;
  /** só com `group_by:'stage'` — o Quadro é uma LENTE da mesma função. */
  counts?: Record<Stage, number>;
  semana: ResumoDaSemana;
  /** R5 — POR FONTE. `true` só quando AQUELA consulta falhou. */
  indisponivel: Record<Fonte, boolean>;
  cursor: string | null;
  has_more: boolean;
}

export interface FiltroDeCasos {
  estagio?: Stage;
  so_ativos?: boolean;
  /** a Ficha pede UM caso — é o mesmo read model, com um `.eq('id', …)` a mais. */
  conversa_id?: string;
}

export interface OpcoesDeCasos {
  group_by?: 'stage';
  cursor?: string | null;
  busca?: string;
  limite?: number;
}

export interface ContextoDaSessao {
  companyId: string;
  userId?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────────────

/** 🔴 E11 — o LOTE. A Fila lê TODAS as conversas ativas em lotes deste tamanho
 *  (📊 ≤ 700 por corretora), e é também a primeira página de Casos. Nunca 120. */
const LOTE = 1000;
/** trava de segurança: 50 lotes = 50.000 linhas. Não é teto de produto, é
 *  cinto — um laço sem fim numa rota derruba a tela inteira. */
const MAX_LOTES = 50;
/**
 * 🔴 O TETO DAS FONTES DE CONTEXTO — esperas, trabalhos, aprovações.
 *
 * ⚠️ E ele é DECLARADO. Um teto silencioso é o mesmo defeito do `.limit(120)`
 * de §1.5: a tela mostra menos do que existe e não tem como saber disso. Toda
 * leitura que voltar CHEIA marca a sua fonte como `indisponivel` — a tela diz
 * "o que está aqui pode estar incompleto" em vez de mentir por omissão.
 */
const TETO_DE_CONTEXTO = 2000;
/** R1 — o silêncio que vira PARADO. Era o mesmo número que virava "concluido". */
const PARADO_APOS_MS = 48 * 3600e3;
const SEMANA_MS = 7 * 24 * 3600e3;
/** a janela do episódio órfão no QUADRO (ver `janelaDoOrfaoISO`). */
const JANELA_DO_ORFAO_MS = 30 * 24 * 3600e3;

/** ⚠️ Os `kind` que o CHECK de `work_waits` aceita. "documento" NEM É kind. */
const KINDS_DE_ESPERA = new Set(['esperando_cliente', 'esperando_seguradora', 'esperando_humano']);

const SERVICO_LABEL: Record<string, string> = {
  guincho: 'Guincho',
  bateria: 'Bateria',
  pneu: 'Pneu',
  chaveiro: 'Chaveiro',
  eletricista: 'Eletricista',
  encanador: 'Hidráulica',
  eletrodomesticos: 'Eletrodomésticos',
  vidros: 'Vidros',
  sinistro: 'Sinistro',
  consulta: 'Consulta',
};

/**
 * 🔴 R11 — o que o segurado PEDIU, dito como uma pessoa diria. O mapa acima
 * cobre os serviços conhecidos; o que vier de fora dele não pode chegar à tela
 * como `auto_socorro`, então o sublinhado vira espaço e a primeira letra sobe.
 * Um rótulo de máquina no card é exatamente o defeito que o guarda [13] vigia.
 */
function rotuloDoPedido(bruto: unknown): string | null {
  const chave = String(bruto ?? '').trim();
  if (!chave) return null;
  const conhecido = SERVICO_LABEL[chave.toLowerCase()];
  if (conhecido) return conhecido;
  const humano = chave.replace(/[_-]+/g, ' ').trim();
  if (!humano) return null;
  return humano.charAt(0).toUpperCase() + humano.slice(1);
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilidades
// ─────────────────────────────────────────────────────────────────────────────

type Linha = Record<string, any>;
type Cliente = ReturnType<typeof getSupabaseAdmin>;

const digitos = (v: unknown) => String(v ?? '').replace(/\D/g, '');
const ms = (iso: string | null | undefined) => (iso ? new Date(iso).getTime() : 0);

/** o mais recente de dois relógios — E5, e é UM campo. */
function maisRecente(a: string | null | undefined, b: string | null | undefined): string | null {
  if (!a) return b || null;
  if (!b) return a;
  return ms(a) >= ms(b) ? a : b;
}

/** "3d 4h" · "5h 20min" · "12min" — a frase que a Fila mostra em "parado há X". */
export function humanizarDuracao(desdeMs: number, ateMs: number): string {
  const d = Math.max(0, ateMs - desdeMs);
  const min = Math.floor(d / 60000);
  const horas = Math.floor(min / 60);
  const dias = Math.floor(horas / 24);
  if (dias >= 1) return `${dias}d${horas % 24 ? ` ${horas % 24}h` : ''}`;
  if (horas >= 1) return `${horas}h${min % 60 ? ` ${min % 60}min` : ''}`;
  return `${min}min`;
}

/**
 * 🔴 O cursor. Duas chaves — `(ultimo_evento_em, id)` — porque uma só não
 * desempata: sem o `id`, dois episódios com o mesmo instante somem ou repetem
 * ao acaso entre páginas.
 *
 * Aceita a forma crua `<iso>|<id>` e a base64 dela (é o que a URL carrega).
 */
const RE_ISO = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:?\d{2})?$/;
const RE_UUID = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
/** ⚠️ o banco usa UUID; o dublê do guarda usa id legível (`as-alfa-0100`). Os
 *  dois passam. O que NÃO passa é qualquer coisa com a sintaxe do `or()` do
 *  PostgREST dentro — ponto, vírgula, parêntese, aspas. */
const RE_ID_SEGURO = /^[A-Za-z0-9_-]{1,64}$/;

export function lerCursor(cursor: string | null | undefined): { at: string; id: string } | null {
  const bruto = String(cursor || '').trim();
  if (!bruto) return null;
  let texto = bruto;
  if (!texto.includes('|')) {
    try {
      texto = Buffer.from(bruto, 'base64').toString('utf8');
    } catch {
      return null;
    }
  }
  const corte = texto.indexOf('|');
  if (corte <= 0) return null;
  const at = texto.slice(0, corte);
  const id = texto.slice(corte + 1);
  if (!at || !id) return null;
  // 🔴 O CURSOR ENTRA CRU NUM `or(...)` DO POSTGREST, onde `,` `(` `)` `.` são
  //    SINTAXE. Um cursor forjado reescrevia o predicado da consulta a partir
  //    da URL — quem controla a query string controlava o filtro. Aqui ele tem
  //    de ter a FORMA de um instante e a de um id; o que não tem é DESCARTADO,
  //    e a lista volta para a primeira página em vez de virar outra consulta.
  if (!RE_ISO.test(at)) return null;
  if (!RE_UUID.test(id) && !RE_ID_SEGURO.test(id)) return null;
  return { at, id };
}

export function escreverCursor(at: string | null, id: string): string {
  return Buffer.from(`${at || ''}|${id}`, 'utf8').toString('base64');
}

/**
 * ⛔ O termo de busca vai para dentro de um `or(...)` do PostgREST, onde
 * `,` `(` `)` são SINTAXE. Um termo com vírgula viraria outro predicado.
 * Nada de aspas, nada de `%` do usuário: o curinga é NOSSO.
 */
function termoSeguro(busca: string | undefined): string {
  return (
    String(busca || '')
      // ⛔ `%` E `_` são os DOIS curingas do LIKE. Só o `%` era limpo, então uma
      //    busca por `____` casava qualquer coisa de quatro letras e devolvia o
      //    acervo inteiro com cara de resultado.
      .replace(/[,()*%_\\'"]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  );
}

/** Um resultado de fonte: dados OU a marca de que ELA falhou (R5). */
interface Leitura {
  linhas: Linha[];
  ok: boolean;
}

async function ler(
  consulta: PromiseLike<{ data: Linha[] | null; error: unknown }>,
): Promise<Leitura> {
  try {
    const { data, error } = await consulta;
    if (error) return { linhas: [], ok: false };
    return { linhas: data || [], ok: true };
  } catch {
    // ⛔ fonte fora do ar não estoura a tela — ela se DECLARA indisponível.
    return { linhas: [], ok: false };
  }
}

/** Lê TODAS as linhas em lotes de `LOTE` (E11). Sem teto, sem `.limit(120)`. */
async function lerEmLotes(
  monta: (de: number, ate: number) => PromiseLike<{ data: Linha[] | null; error: unknown }>,
): Promise<Leitura> {
  const linhas: Linha[] = [];
  for (let pagina = 0; pagina < MAX_LOTES; pagina += 1) {
    const de = pagina * LOTE;
    const r = await ler(monta(de, de + LOTE - 1));
    if (!r.ok) return { linhas, ok: false };
    linhas.push(...r.linhas);
    if (r.linhas.length < LOTE) break;
  }
  return { linhas, ok: true };
}

const COLUNAS_CONVERSA =
  'id, company_id, status, channel, user_phone, user_name, last_message_preview, last_message_at, ' +
  'created_at, session_id, claimed_by, claimed_by_name, claimed_at, resolvido_em, resolucao_motivo';

// 🔴 AS COLUNAS REAIS de `attendance_sessions` (📊 05/09/2026,
//    `information_schema.columns`): id · company_id · observer_number ·
//    counterparty · insurer_key · started_at · last_event_at · status · ramo ·
//    servico · summary · created_at — mais as TRÊS que a migration da 097
//    acrescenta (`conversation_id`, `resolvido_em`, `resolucao_motivo`).
//
// ⛔ NÃO EXISTE `protocolo`. Nem aqui, nem em lugar nenhum: 📊 uma varredura de
//    `information_schema.columns` por `column_name ilike '%protocol%'` no
//    schema `public` inteiro devolveu **ZERO colunas**, e `summary->'distilled'`
//    (9.196 sessões) não tem a chave em **nenhuma** delas. Pedir a coluna fazia
//    o PostgREST devolver 42703 na consulta INTEIRA — e, como toda leitura de
//    episódio passa por aqui, a tela de Casos devolvia ZERO episódios sempre.
//    O protocolo hoje só vive no estado quente do acionamento (o backend o
//    entrega na Ficha). Sem fonte durável, o campo é `null` e a tela diz "sem
//    protocolo" — uma coluna inventada é pior que uma ausência declarada.
const COLUNAS_SESSAO =
  'id, company_id, conversation_id, counterparty, status, started_at, last_event_at, ' +
  'resolvido_em, resolucao_motivo, summary, ramo, servico';

// ─────────────────────────────────────────────────────────────────────────────
// A projeção
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A ÚNICA função de leitura do atendimento (R5).
 *
 *   `group_by: 'stage'`  → a FILA/QUADRO: uma linha por CONVERSA ativa (E11),
 *                          lida em lotes de 1.000, agrupada e contada em memória
 *                          (estágio é DERIVADO — o PostgREST não agrega por ele).
 *   sem `group_by`       → CASOS: uma linha por EPISÓDIO, com cursor
 *                          `(ultimo_evento_em, id)` e busca NO BANCO.
 */
export async function projetarCasos(
  ctx: ContextoDaSessao,
  filtro: FiltroDeCasos = {},
  opcoes: OpcoesDeCasos = {},
): Promise<Projecao> {
  const supabase = getSupabaseAdmin();
  const companyId = ctx.companyId;
  const agoraMs = Date.now();
  const janelaDaSemanaISO = new Date(agoraMs - SEMANA_MS).toISOString();
  // 📊 A janela do episódio ÓRFÃO na Fila. Ele não tem conversa, então não há
  //    "conversa ativa" que o traga; sem janela nenhuma, os 1.314 órfãos com
  //    mais de 30 dias entrariam todos no quadro como `parado`. Trinta dias é
  //    o mês que o dono da corretora reconhece — e o que sair dela continua
  //    inteiro em Casos, que é a lista sem janela.
  const janelaDoOrfaoISO = new Date(agoraMs - JANELA_DO_ORFAO_MS).toISOString();

  const indisponivel: Record<Fonte, boolean> = {
    conversas: false,
    sessoes: false,
    esperas: false,
    trabalhos: false,
    aprovacoes: false,
  };

  const quadro = opcoes.group_by === 'stage';
  // ⛔ [P2-7] UM TERMO QUE SOBRA VAZIO NÃO É "SEM BUSCA".
  //    `%%%` e `___` são só curingas; depois da limpeza não sobra letra
  //    nenhuma. Tratar isso como "não buscou" devolvia o ACERVO INTEIRO para
  //    quem pediu uma coisa específica — a pior resposta possível, porque tem
  //    cara de resultado. Quem buscou e não deu nada recebe NADA, declarado.
  const pediuBusca = String(opcoes.busca || '').trim().length > 0;
  const limite = Math.max(1, Number(opcoes.limite) || LOTE);
  const cursor = lerCursor(opcoes.cursor);
  const busca = termoSeguro(opcoes.busca);
  const buscaVazia = pediuBusca && !busca;

  // ───────────────────────────────────────────────────────────────────────────
  // 1) As LINHAS-BASE: conversas (Fila) ou episódios (Casos)
  // ───────────────────────────────────────────────────────────────────────────
  let conversas: Linha[] = [];
  let sessoes: Linha[] = [];
  let sessaoPorConversa = new Map<string, Linha>();
  let has_more = false;
  let proximoCursor: string | null = null;

  if (quadro) {
    // 🔴 A FILA é o trabalho VIVO mais o que TERMINOU nesta semana. As duas
    //    consultas saem do MESMO campo `resolvido_em` — é isso que faz
    //    `semana.terminaram` e os itens "concluido" nunca se contradizerem (R1).
    // 🔴 PEDIR UMA CONVERSA PELO ID NÃO É VARRER A FILA.
    //
    // A Ficha chama esta mesma função com `conversa_id` — e as duas consultas
    // abaixo são as da FILA: "as que não terminaram" e "as que terminaram nesta
    // semana". Uma conversa encerrada há 8 dias não cabe em nenhuma das duas:
    // ela voltava VAZIA, e a Ficha, sem linha nenhuma, caía em "em conversa" —
    // dizendo que um atendimento encerrado no mês passado está acontecendo
    // agora. Quando o id é dado, a janela não se aplica: lê-se A LINHA.
    const porId = Boolean(filtro.conversa_id);
    const ativas = await lerEmLotes((de, ate) => {
      let q = supabase.from('conversations').select(COLUNAS_CONVERSA).eq('company_id', companyId); // 🔴 R9/§7
      if (porId) q = q.eq('id', filtro.conversa_id as string);
      else q = q.is('resolvido_em', null);
      return q
        .order('last_message_at', { ascending: false })
        .order('id', { ascending: false })
        .range(de, ate);
    });
    const daSemana = porId
      ? { linhas: [] as Linha[], ok: true }
      : await lerEmLotes((de, ate) =>
          supabase
            .from('conversations')
            .select(COLUNAS_CONVERSA)
            .eq('company_id', companyId) // 🔴 R9/§7
            .gte('resolvido_em', janelaDaSemanaISO)
            .order('resolvido_em', { ascending: false })
            .order('id', { ascending: false })
            .range(de, ate),
        );
    indisponivel.conversas = !ativas.ok || !daSemana.ok;
    const vistas = new Set<string>();
    for (const c of ativas.linhas.concat(daSemana.linhas)) {
      if (vistas.has(String(c.id))) continue;
      vistas.add(String(c.id));
      conversas.push(c);
    }

    // o EPISÓDIO CORRENTE de cada conversa (R3). Uma sessão COM
    // `conversation_id` mora DENTRO do card da conversa — ela não vira card
    // próprio. Era exatamente a duplicata de hoje: a mesma pessoa aparecia como
    // "conversa" e como "Atendimento da equipe (observado)".
    const episodios = await lerPorLotesDeIds(
      supabase,
      companyId,
      'conversation_id',
      conversas.map((c) => String(c.id)),
    );
    indisponivel.sessoes = !episodios.ok;
    sessaoPorConversa = correnteporConversa(episodios.linhas);

    // ⚠️ O episódio ÓRFÃO e ABERTO continua aparecendo: é a atendente
    //    conversando pelo celular dela, que o Atlas observa e que ainda não tem
    //    conversa no painel (📊 E7). Ele é o único caso que vira card PRÓPRIO.
    // ⛔ E NÃO SE FILTRA POR `status`. 📊 12.754 das 12.755 sessões estão
    //    `closed` — mas isso é o Atlas fechando por 6 h de silêncio para o RAG
    //    (`attendance_distiller`), não é desfecho (E9). `.eq('status','open')`
    //    escondia praticamente TODO episódio órfão da Fila e ressuscitava, por
    //    outro caminho, o defeito de §1.1: o relógio decidindo o fim.
    //    O órfão entra pelo RELÓGIO ÚNICO — e o silêncio dele vira `parado`,
    //    que é um estado visível, não um sumiço.
    const orfaos = porId
      ? { linhas: [] as Linha[], ok: true }
      : await ler(
          supabase
            .from('attendance_sessions')
            .select(COLUNAS_SESSAO)
            .eq('company_id', companyId) // 🔴 R9/§7
            .is('conversation_id', null)
            .is('resolvido_em', null)
            .gte('last_event_at', janelaDoOrfaoISO)
            .order('last_event_at', { ascending: false })
            .limit(LOTE),
        );
    if (!orfaos.ok) indisponivel.sessoes = true;
    // ⚠️ o teto DECLARADO: veio cheio, então há órfão que não coube.
    if (orfaos.linhas.length >= LOTE) indisponivel.sessoes = true;
    sessoes = orfaos.linhas;
  } else {
    // 🔴 CASOS: por EPISÓDIO, com cursor e busca NO BANCO. 📊 §1.5: a busca
    //    morava no cliente, sobre 120 linhas — um protocolo de 60 dias devolvia
    //    "nada encontrado", e o banco nunca tinha sido perguntado.
    let idsPorNome: string[] = [];
    if (busca) {
      const porNome = await ler(
        supabase
          .from('conversations')
          .select('id, user_phone')
          .eq('company_id', companyId) // 🔴 R9/§7
          .or(`user_name.ilike.%${busca}%,user_phone.ilike.%${digitos(busca) || busca}%`)
          .range(0, LOTE - 1),
      );
      if (!porNome.ok) indisponivel.conversas = true;
      idsPorNome = porNome.linhas.slice(0, 200).map((c) => String(c.id));
    }

    const pagina = await ler(
      (() => {
        let q = supabase
          .from('attendance_sessions')
          .select(COLUNAS_SESSAO)
          .eq('company_id', companyId); // 🔴 R9/§7
        if (busca) {
          // ⚠️ sem coluna de protocolo, a busca por protocolo não tem onde
          //    casar no episódio; ela continua chegando ao banco pelo telefone e
          //    pelo nome (via conversa). O que NÃO se faz é filtrar em memória e
          //    chamar o resultado de "nada encontrado" (§1.5).
          const alvos = [
            `counterparty.ilike.%${digitos(busca) || busca}%`,
            ...(idsPorNome.length ? [`conversation_id.in.(${idsPorNome.join(',')})`] : []),
          ];
          q = q.or(alvos.join(','));
        }
        if (cursor) {
          // as DUAS chaves, no BANCO — o desempate não pode ser do cliente.
          q = q.or(
            `last_event_at.lt.${cursor.at},and(last_event_at.eq.${cursor.at},id.lt.${cursor.id})`,
          );
        }
        return q
          .order('last_event_at', { ascending: false })
          .order('id', { ascending: false })
          .limit(limite + 1);
      })(),
    );
    indisponivel.sessoes = indisponivel.sessoes || !pagina.ok;
    sessoes = pagina.linhas.slice(0, limite);
    // 🔴 has_more é do RESULTADO UNIDO, não de uma das fontes. Ele olhava só
    //    `attendance_sessions`; as conversas sem episódio eram cortadas logo
    //    abaixo sem tocar nele, e o botão "carregar mais" sumia com casos ainda
    //    por mostrar. Qualquer fonte com sobra ⇒ há mais.
    has_more = pagina.linhas.length > limite;

    // as conversas destes episódios (para nome, telefone, dono e desfecho)
    const idsDeConversa = Array.from(
      new Set(
        sessoes
          .map((s) => s.conversation_id)
          .filter(Boolean)
          .map(String),
      ),
    );
    if (idsDeConversa.length) {
      const hidrata = await lerPorLotesDeIds(
        supabase,
        companyId,
        'id',
        idsDeConversa,
        'conversations',
        COLUNAS_CONVERSA,
      );
      if (!hidrata.ok) indisponivel.conversas = true;
      conversas = hidrata.linhas;
    }

    // 🔴 R3 — "conversa sem episódio ⇒ 1 caso implícito". Sem isto, uma conversa
    //    que nunca virou episódio SUMIRIA de Casos (e hoje ela aparece lá).
    //    A mesma janela de cursor, sobre a mesma chave, para o merge ser estável.
    const implicitas = await ler(
      (() => {
        let q = supabase.from('conversations').select(COLUNAS_CONVERSA).eq('company_id', companyId); // 🔴 R9/§7
        if (busca) {
          q = q.or(`user_name.ilike.%${busca}%,user_phone.ilike.%${digitos(busca) || busca}%`);
        }
        if (cursor) {
          q = q.or(
            `last_message_at.lt.${cursor.at},and(last_message_at.eq.${cursor.at},id.lt.${cursor.id})`,
          );
        }
        return q
          .order('last_message_at', { ascending: false })
          .order('id', { ascending: false })
          .range(0, limite);
      })(),
    );
    if (!implicitas.ok) indisponivel.conversas = true;
    if (implicitas.linhas.length > limite) has_more = true; // 🔴 a outra fonte também tem sobra
    const candidatas = implicitas.linhas.slice(0, limite);
    if (candidatas.length) {
      const comEpisodio = await lerPorLotesDeIds(
        supabase,
        companyId,
        'conversation_id',
        candidatas.map((c) => String(c.id)),
        'attendance_sessions',
        'id, company_id, conversation_id',
      );
      if (!comEpisodio.ok) indisponivel.sessoes = true;
      const temEpisodio = new Set(comEpisodio.linhas.map((s) => String(s.conversation_id)));
      const jaHidratada = new Set(conversas.map((c) => String(c.id)));
      for (const c of candidatas) {
        if (temEpisodio.has(String(c.id))) continue;
        if (jaHidratada.has(String(c.id))) continue;
        conversas.push({ ...c, __implicita: true });
      }
    }
  }

  // ⛔ [P2-7] nada casou porque nada foi perguntado: devolver o acervo aqui
  //    seria responder outra pergunta.
  if (buscaVazia) {
    return {
      items: [],
      busca_invalida: true,
      semana: await montarSemana(supabase, companyId, indisponivel),
      indisponivel,
      cursor: null,
      has_more: false,
    };
  }

  // 🔴 SPEC-EXTRA-001.3 BLOCO B — 2º DOS QUATRO EFEITOS: **nunca entra na Fila**.
  //
  // O fixo da loja, o comercial e o celular do sócio que não usa o painel não
  // são casos: são a própria corretora conversando consigo mesma. Eles somem
  // daqui e o contador da Fila para de contá-los.
  //
  // ⛔ Conjunto vazio no escuro — uma leitura ruim NUNCA some com o caso de um
  // segurado de verdade.
  const numerosDaCasa = await carregarNumerosDaCasa(supabase, companyId);
  if (numerosDaCasa.size) {
    const antes = conversas.length;
    conversas = conversas.filter((c) => !ehNumeroDaCasa(numerosDaCasa, (c as any).user_phone));
    if (conversas.length !== antes) {
      console.log(`[CASOS] ${antes - conversas.length} conversa(s) de número da casa fora da Fila`);
    }
  }

  const conversaPorId = new Map(conversas.map((c) => [String(c.id), c]));

  // ───────────────────────────────────────────────────────────────────────────
  // 2) As fontes de CONTEXTO — cada uma falha sozinha (R5)
  // ───────────────────────────────────────────────────────────────────────────
  // 🔴 AS COLUNAS REAIS de `work_waits` (📊 05/09/2026, `information_schema`):
  //    id · company_id · conversation_id · work_run_id · kind · scope · status ·
  //    vence_em · satisfeito_por · satisfeito_em · avisos · created_at · updated_at.
  //    ⛔ NÃO existem `attendance_session_id` nem `due_at` — pedi-los devolvia
  //    42703 na consulta INTEIRA, e o `try/catch` transformava isso em
  //    "esperas indisponíveis" todo dia, em silêncio. A espera se liga ao caso
  //    pela CONVERSA; não há coluna de episódio, e inventar uma é inventar
  //    junção.
  const esperas = await ler(
    supabase
      .from('work_waits')
      .select(
        'id, company_id, conversation_id, work_run_id, kind, scope, status, vence_em, created_at',
      )
      .eq('company_id', companyId) // 🔴 R9/§7
      .eq('status', 'ativo')
      .limit(TETO_DE_CONTEXTO),
  );
  indisponivel.esperas =
    !esperas.ok ||
    // ⚠️ o teto DECLARADO: se veio exatamente o teto, há espera que não coube —
    //    e um recorte silencioso é o zero silencioso outra vez (R5).
    esperas.linhas.length >= TETO_DE_CONTEXTO;

  // 🔴 DOIS recortes de `work_runs`, e é de propósito:
  //    (a) o trabalho que FALHOU  → R6 `trabalho_falhou`;
  //    (b) o TRAVAMENTO que já passou das 6h do Redis, incluindo
  //        `assumido_por_humano` — o caso que a atendente destravou e que
  //        `.eq('unblock_state','travado')` apagava da Fila.
  const runsFalhos = await ler(
    supabase
      .from('work_runs')
      .select(
        'id, company_id, conversation_id, status, runtime_kind, unblock_state, current_step_key, error_code, error_message, created_at, input_payload',
      )
      .eq('company_id', companyId) // 🔴 R9/§7
      .eq('status', 'failed')
      .order('created_at', { ascending: false })
      .limit(TETO_DE_CONTEXTO),
  );
  const runsTravados = await ler(
    supabase
      .from('work_runs')
      .select(
        'id, company_id, conversation_id, status, runtime_kind, unblock_state, current_step_key, error_code, error_message, created_at, input_payload',
      )
      .eq('company_id', companyId) // 🔴 R9/§7
      // 🔴 `assumido_por_humano` CONTINUA NA FILA.
      //
      // 📊 26/08/2026: o BLOCO C da SPEC-093 passou a gravar
      // `assumido_por_humano` quando alguém destrava pelo WhatsApp. Com
      // `.eq('unblock_state','travado')`, bastava a atendente mandar "só um
      // minuto" para o caso sumir da única Fila que existe — assim que o Redis
      // expirasse (TTL de 6h). E não voltava nunca: `_fechar_travamento`
      // (`dispatch_router.py:1126`) filtra `['travado','retomado_pelo_robo']`
      // de propósito, para não pisar neste estado. Terminal e invisível.
      //
      // 🔴 O motivo de produto é o desenho do Founder: **a atendente DESTRAVA,
      // ela não assume.** O caso continua sendo do robô e continua precisando
      // de olho.
      //
      // ⚠️ A lista vai LITERAL aqui, e não por uma constante: o guarda
      // `test_o_clique_da_atendente_nao_apaga_da_fila.py` lê a FORMA desta
      // declaração — e uma constante escondida dele é uma consulta que ele não vê.
      .in('unblock_state', ['travado', 'assumido_por_humano'])
      .order('created_at', { ascending: false })
      .limit(TETO_DE_CONTEXTO),
  );
  indisponivel.trabalhos =
    !runsFalhos.ok ||
    !runsTravados.ok ||
    // ⚠️ o teto DECLARADO: veio cheio, então há trabalho parado que não coube.
    runsFalhos.linhas.length >= TETO_DE_CONTEXTO ||
    runsTravados.linhas.length >= TETO_DE_CONTEXTO;
  const runsPorId = new Map<string, Linha>();
  for (const r of runsFalhos.linhas.concat(runsTravados.linhas)) runsPorId.set(String(r.id), r);
  const runs = Array.from(runsPorId.values());

  // E17 — `approval_requests` NÃO tem conversa. A ponte é run→conversa, e são
  // estas quatro linhas. Ela alimenta a PRÓXIMA AÇÃO (R7) e nada mais: a
  // aprovação pendente NÃO é razão de atenção (R6).
  const aprovacoesPorConversa = new Map<string, Linha>();
  if (runs.length) {
    const aprovacoes = await ler(
      supabase
        .from('approval_requests')
        // ⛔ NÃO existe `title` em `approval_requests` (📊 05/09/2026,
        //    `information_schema.columns`). O que existe é `preview` e
        //    `requested_preview`, os dois JSONB. Pedir `title` devolvia 42703 e
        //    derrubava a consulta inteira — nenhuma aprovação jamais chegou à
        //    próxima ação, e o erro morria no `try/catch`.
        .select(
          'id, company_id, work_run_id, status, action_type, preview, requested_preview, created_at',
        )
        .eq('company_id', companyId) // 🔴 R9/§7
        .eq('status', 'pending')
        .in(
          'work_run_id',
          runs.map((r) => String(r.id)),
        )
        .limit(TETO_DE_CONTEXTO),
    );
    indisponivel.aprovacoes = !aprovacoes.ok || aprovacoes.linhas.length >= TETO_DE_CONTEXTO; // ⚠️ o teto DECLARADO
    for (const a of aprovacoes.linhas) {
      const run = runsPorId.get(String(a.work_run_id));
      const conversa = run?.conversation_id ? String(run.conversation_id) : null;
      if (conversa && !aprovacoesPorConversa.has(conversa)) aprovacoesPorConversa.set(conversa, a);
    }
  }

  // ⚠️ UM índice só, pela CONVERSA — é a única chave que a tabela tem. O
  //    episódio herda a espera da conversa dele; o episódio ÓRFÃO (sem
  //    conversa) não tem espera, e a tela não finge que tem.
  //
  // 🔴 SPEC-097.1 U1.3/E6 — DUAS ESPERAS ATIVAS NA MESMA CONVERSA AGORA
  //    EXISTEM, e a escolha deixou de ser o acaso da ordem do `Map`.
  //
  //    O `UNIQUE uq_work_waits_ativo_por_escopo` é por ESCOPO: o travamento do
  //    corredor (`acionamento`) e a espera da seguradora (`pos_acionamento`)
  //    convivem de propósito. Até aqui, quem chegasse primeiro na lista
  //    ganhava — e a tela mostrava "esperando a equipe" para um caso cuja
  //    seguradora vence em duas horas, ou o contrário, sem regra nenhuma.
  //
  //    ⚠️ A regra é: **a de menor `vence_em`** (é a que cobra primeiro);
  //    empate → `pos_acionamento` (é a que o segurado está sentindo).
  //    ⛔ Espera SEM `vence_em` vai para o fim: ela não cobra ninguém.
  const esperaPorConversa = new Map<string, Linha>();
  const melhorEspera = (a: Linha, b: Linha): Linha => {
    const va = String(a.vence_em || '9999');
    const vb = String(b.vence_em || '9999');
    if (va !== vb) return va < vb ? a : b;
    if (String(a.scope) === 'pos_acionamento') return a;
    if (String(b.scope) === 'pos_acionamento') return b;
    return a;
  };
  for (const w of esperas.linhas) {
    if (!KINDS_DE_ESPERA.has(String(w.kind))) continue; // ⛔ fora do CHECK do banco
    if (!w.conversation_id) continue;
    const chave = String(w.conversation_id);
    const atual = esperaPorConversa.get(chave);
    esperaPorConversa.set(chave, atual ? melhorEspera(atual, w) : w);
  }
  const runPorConversa = new Map<string, Linha>();
  for (const r of runs) {
    if (!r.conversation_id) continue;
    if (!runPorConversa.has(String(r.conversation_id)))
      runPorConversa.set(String(r.conversation_id), r);
  }

  // ───────────────────────────────────────────────────────────────────────────
  // 3) Os CASOS
  // ───────────────────────────────────────────────────────────────────────────
  const items: Caso[] = [];

  if (quadro) {
    for (const c of conversas) {
      items.push(
        montarCaso({
          conversa: c,
          sessao: sessaoPorConversa.get(String(c.id)) || null,
          porEpisodio: false,
          esperaPorConversa,
          runPorConversa,
          aprovacoesPorConversa,
          agoraMs,
        }),
      );
    }
    for (const s of sessoes) {
      items.push(
        montarCaso({
          conversa: null,
          sessao: s,
          porEpisodio: false,
          esperaPorConversa,
          runPorConversa,
          aprovacoesPorConversa,
          agoraMs,
        }),
      );
    }
  } else {
    for (const s of sessoes) {
      items.push(
        montarCaso({
          conversa: s.conversation_id ? conversaPorId.get(String(s.conversation_id)) || null : null,
          sessao: s,
          porEpisodio: true,
          esperaPorConversa,
          runPorConversa,
          aprovacoesPorConversa,
          agoraMs,
        }),
      );
    }
    for (const c of conversas) {
      if (!c.__implicita) continue;
      items.push(
        montarCaso({
          conversa: c,
          sessao: null,
          porEpisodio: true,
          esperaPorConversa,
          runPorConversa,
          aprovacoesPorConversa,
          agoraMs,
        }),
      );
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // 4) O FILTRO, e ele vem ANTES do corte da página
  // ───────────────────────────────────────────────────────────────────────────
  //
  // ⚠️ O estágio é DERIVADO (dono, espera, run, relógio): o PostgREST não tem
  // como filtrá-lo. Mas filtrar DEPOIS de cortar a página devolvia "3 parados"
  // porque só 3 dos 50 da página estavam parados — e a página seguinte trazia
  // outros, sem que ninguém soubesse que a conta não era a da corretora. O
  // filtro roda sobre TUDO o que a janela do cursor trouxe, e só então a
  // página é cortada.
  const filtrados = items.filter((i) => {
    if (filtro.estagio && i.stage !== filtro.estagio) return false;
    if (filtro.so_ativos && i.stage === 'concluido') return false;
    return true;
  });

  // ───────────────────────────────────────────────────────────────────────────
  // 5) A PÁGINA — 🔴 P1-6: UM espaço de chave, ordenado UMA vez
  // ───────────────────────────────────────────────────────────────────────────
  //
  // A chave é `(ultimo_evento_em, id)`, e ela vale para as duas origens: o id
  // de um episódio é o da SESSÃO; o do caso implícito (conversa que nunca virou
  // episódio) é o da CONVERSA, sobre o MESMO campo derivado. Antes, os
  // episódios paginavam por `last_event_at` e as conversas por
  // `last_message_at`, e o desempate se fazia por `key` — string com prefixo
  // `epi:`/`conv:`, que é OUTRO espaço de chave. Duas réguas na mesma lista
  // fazem um caso sumir entre a página 1 e a 2, em silêncio.
  let paginados = filtrados;
  if (!quadro) {
    paginados = ordenarPelaChave(filtrados);
    if (paginados.length > limite) {
      paginados = paginados.slice(0, limite);
      has_more = true;
    }
    const ultimo = paginados[paginados.length - 1];
    if (ultimo) proximoCursor = escreverCursor(ultimo.ordem_em, idDaChave(ultimo));
  }

  const semana = await montarSemana(supabase, companyId, indisponivel);

  const projecao: Projecao = {
    items: paginados,
    semana,
    indisponivel,
    cursor: proximoCursor,
    has_more,
  };
  if (quadro) {
    const counts = zeroCountsByStage();
    for (const i of paginados) counts[i.stage] += 1;
    projecao.counts = counts;
  }
  return projecao;
}

// ─────────────────────────────────────────────────────────────────────────────
// As peças
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 🔴 P1-6 — O ID DA CHAVE DE PAGINAÇÃO. Um espaço só: o episódio entra pelo id
 * da sessão, o caso implícito pelo id da conversa. Nunca a `key` com prefixo,
 * que ordena `conv:` antes de `epi:` e não tem nada a ver com a ordem do banco.
 */
function idDaChave(c: Caso): string {
  return String(c.session_id || c.conversa_id || c.key);
}

/** A lista ordenada UMA vez pela chave `(ultimo_evento_em desc, id desc)` — a
 *  mesma ordem que as duas consultas pediram ao banco. */
function ordenarPelaChave(itens: Caso[]): Caso[] {
  return [...itens].sort((a, b) => {
    const t = String(b.ordem_em || '').localeCompare(String(a.ordem_em || ''));
    if (t !== 0) return t;
    return idDaChave(b).localeCompare(idDaChave(a));
  });
}

/** `.in(coluna, ids)` em lotes — uma URL do PostgREST não aguenta 4.000 ids. */
async function lerPorLotesDeIds(
  supabase: Cliente,
  companyId: string,
  coluna: string,
  ids: string[],
  tabela = 'attendance_sessions',
  colunas = COLUNAS_SESSAO,
): Promise<Leitura> {
  if (!ids.length) return { linhas: [], ok: true };
  const linhas: Linha[] = [];
  for (let i = 0; i < ids.length; i += 200) {
    const fatia = ids.slice(i, i + 200);
    const r = await ler(
      supabase
        .from(tabela)
        .select(colunas)
        .eq('company_id', companyId) // 🔴 R9/§7
        .in(coluna, fatia),
    );
    if (!r.ok) return { linhas, ok: false };
    linhas.push(...r.linhas);
  }
  return { linhas, ok: true };
}

/** 📊 §1.4 — 5,8 episódios por contato. O card da conversa mostra o CORRENTE. */
function correnteporConversa(sessoes: Linha[]): Map<string, Linha> {
  const mapa = new Map<string, Linha>();
  for (const s of sessoes) {
    const chave = String(s.conversation_id || '');
    if (!chave) continue;
    const atual = mapa.get(chave);
    if (!atual || ms(s.last_event_at) > ms(atual.last_event_at)) mapa.set(chave, s);
  }
  return mapa;
}

interface EntradaDoCaso {
  conversa: Linha | null;
  sessao: Linha | null;
  /** 🔴 P1-5 — QUAL É A UNIDADE desta linha.
   *
   *  `true`  CASOS: a linha É o episódio. O desfecho dele é o `resolvido_em`
   *          DA SESSÃO e de mais nada. Herdar o da conversa marcaria os 5,8
   *          episódios médios daquele telefone como encerrados de uma vez —
   *          fechar UM atendimento apagaria a história dos outros cinco.
   *  `false` FILA: a linha é a CONVERSA, com o episódio corrente dentro dela.
   *          Aí o desfecho é o da conversa OU o do episódio corrente: os dois
   *          encerram aquele card, e é o mesmo card.
   */
  porEpisodio: boolean;
  esperaPorConversa: Map<string, Linha>;
  runPorConversa: Map<string, Linha>;
  aprovacoesPorConversa: Map<string, Linha>;
  agoraMs: number;
}

function montarCaso(e: EntradaDoCaso): Caso {
  const { conversa, sessao, agoraMs } = e;
  const conversaId = conversa ? String(conversa.id) : null;
  const sessionId = sessao ? String(sessao.id) : null;

  // 🔴 E5 — UM relógio.
  const ultimo_evento_em = maisRecente(
    conversa?.last_message_at || conversa?.created_at || null,
    sessao?.last_event_at || sessao?.started_at || null,
  );

  // 🔴 R1 — o desfecho é ESCRITO. Da conversa OU do episódio (E8), nunca do
  //    relógio, e NUNCA de `attendance_sessions.status` (E9: o Atlas fecha a
  //    sessão por 6h de silêncio para o RAG; isso não é o fim do atendimento).
  const daSessao = Boolean(e.porEpisodio && sessao);
  const resolvido_em = daSessao
    ? sessao?.resolvido_em || null
    : conversa?.resolvido_em || sessao?.resolvido_em || null;
  const resolucao_motivo = daSessao
    ? sessao?.resolucao_motivo || null
    : conversa?.resolucao_motivo || sessao?.resolucao_motivo || null;

  const dono: Dono | null = conversa?.claimed_by
    ? {
        id: String(conversa.claimed_by),
        nome: String(conversa.claimed_by_name || 'Alguém da equipe'),
      }
    : null;

  const linhaDeEspera = (conversaId ? e.esperaPorConversa.get(conversaId) : null) || null;
  const esperando: Espera | null = linhaDeEspera
    ? {
        kind: String(linhaDeEspera.kind),
        desde: linhaDeEspera.created_at || null,
        vence_em: linhaDeEspera.vence_em || null,
        vencida: Boolean(linhaDeEspera.vence_em && ms(linhaDeEspera.vence_em) < agoraMs),
        fonte_id: String(linhaDeEspera.id),
      }
    : null;

  const run = conversaId ? e.runPorConversa.get(conversaId) || null : null;
  const aprovacao = conversaId ? e.aprovacoesPorConversa.get(conversaId) || null : null;

  // ── A CASCATA (R1/R2) ──────────────────────────────────────────────────────
  // 🔴 O dono vem ANTES do status. Era o inverso, e por isso "com a equipe" era
  //    inalcançável: o claim escrevia `HUMAN_REQUESTED` junto do dono, e o teste
  //    do status disparava primeiro (§1.2, ACHADO-1b).
  // ⛔ E NÃO existe mais um `else 'concluido'` no fim. O fim da cascata é
  //    `parado`: silêncio é silêncio, não é encerramento.
  const idadeMs = ultimo_evento_em ? agoraMs - ms(ultimo_evento_em) : Number.POSITIVE_INFINITY;
  const fresca = idadeMs < PARADO_APOS_MS;
  const pediuPessoa = !dono && String(conversa?.status || '') === 'HUMAN_REQUESTED';
  const trabalhoFalhou = Boolean(run);

  let stage: Stage;
  if (resolvido_em) stage = 'concluido';
  else if (dono) stage = 'com_equipe';
  else if (pediuPessoa) stage = 'precisa_de_voce';
  else if (trabalhoFalhou) stage = 'precisa_de_voce';
  else if (esperando) stage = 'esperando';
  else if (!conversa && sessao) stage = fresca ? 'observacao' : 'parado';
  else if (fresca) stage = 'em_conversa';
  else stage = 'parado';

  const parado = stage === 'parado';
  const distilada =
    (sessao?.summary as { distilled?: Record<string, string> } | null)?.distilled || {};
  const servico = rotuloDoPedido(sessao?.servico || distilada.servico);
  // 📊 ZERO das 9.196 sessões com `distilled` têm a chave `protocolo`; a
  //    coluna não existe. Fica lido de onde ele PODERIA vir, e null é null.
  const protocolo = (distilada.protocolo || null) as string | null;
  const telefone = digitos(conversa?.user_phone || sessao?.counterparty) || null;
  const cliente = (conversa?.user_name || '').trim() || null;

  const atencao: RazaoDeAtencao[] = [];
  if (pediuPessoa) atencao.push('pediu_pessoa');
  if (trabalhoFalhou) atencao.push('trabalho_falhou');
  if (parado) atencao.push('parado');
  if (esperando?.vencida) atencao.push('espera_vencida');

  const proxima_acao = escolherProximaAcao({
    pediuPessoa,
    aprovacao,
    run,
    esperando,
    conversaId,
  });

  // ⛔ [P3-2] RELÓGIO NO FUTURO É AGORA. 📊 um `last_message_at` adiantado
  //    (fuso do provedor, relógio do celular) produzia duração NEGATIVA, e
  //    "parado há -3 dias" é uma tela que ninguém acredita mais.
  //    [P3-1] E sem relógio nenhum a resposta é a AUSÊNCIA COM NOME — a tela
  //    dizia "Parado há —", que parece defeito de carga.
  const ha_quanto_tempo = ultimo_evento_em
    ? humanizarDuracao(Math.min(ms(ultimo_evento_em), agoraMs), agoraMs)
    : null;
  const situacao = frasesDaSituacao(stage, {
    dono,
    esperando,
    cliente,
    servico,
    resolucao_motivo,
    temRelogio: Boolean(ultimo_evento_em),
  });

  // 🔴 A CHAVE, e ela é a da UNIDADE. Em CASOS, dois episódios da mesma
  //    conversa são duas linhas — se a chave fosse a da conversa, eles
  //    colidiriam e o React mostraria um no lugar do outro.
  const caso: Caso = {
    key: daSessao || (sessionId && !conversaId) ? `epi:${sessionId}` : `conv:${conversaId}`,
    stage,
    kind: daSessao || (sessionId && !conversaId) ? 'episodio' : 'conversa',
    conversa_id: conversaId,
    session_id: sessionId,
    telefone,
    cliente,
    pedido: servico,
    protocolo,
    ultimo_evento_em,
    ordem_em:
      daSessao || (sessionId && !conversaId)
        ? sessao?.last_event_at || sessao?.started_at || null
        : conversa?.last_message_at || conversa?.created_at || null,
    resolvido_em,
    resolucao_motivo,
    dono,
    esperando,
    work_run_id: run ? String(run.id) : null,
    unblock_state: run ? (run.unblock_state ? String(run.unblock_state) : null) : null,
    agora: { situacao, dono, esperando, ha_quanto_tempo, atencao, proxima_acao },
    titulo:
      cliente ||
      (servico ? `${servico}${telefone ? ` · ${telefone}` : ''}` : null) ||
      telefone ||
      'Atendimento',
    detalhe: situacao,
    quando: ultimo_evento_em,
  };
  if (parado) {
    caso.parado_desde = ultimo_evento_em;
    caso.parado_ha = ha_quanto_tempo;
  }
  if (sessionId && !conversaId) caso.sem_conversa_vinculada = true;
  return caso;
}

/**
 * 🔴 R7 — a precedência, e ela é DETERMINÍSTICA. A ausência tem NOME: "sem
 * próxima ação declarada" é uma resposta, `null` mudo não é. E toda ação traz a
 * FONTE de onde saiu — sem autoridade, não há próxima ação; há ficção.
 */
/**
 * 🔴 R11 — O QUE O CORRETOR LÊ QUANDO O ACIONAMENTO PARA.
 *
 * `work_runs.error_message` é texto de máquina: `KeyError: 'x'`, um traceback,
 * um código. Ele ia CRU para o card e para a próxima ação. O CÓDIGO do erro
 * vira frase de gente aqui, e o que não estiver na lista cai na frase honesta —
 * nunca no texto do motor.
 */
const FRASE_DO_ERRO: Record<string, string> = {
  ura_timeout: 'A seguradora não respondeu a tempo.',
  ura_desconhecida: 'A seguradora mudou o atendimento e o sistema não reconheceu a tela.',
  tela_desconhecida: 'A seguradora mudou o atendimento e o sistema não reconheceu a tela.',
  sem_resposta: 'A seguradora não respondeu.',
  numero_invalido: 'O telefone do atendimento não foi aceito pela seguradora.',
  apolice_nao_encontrada: 'A seguradora não encontrou a apólice.',
  fora_do_horario: 'A seguradora está fora do horário de atendimento.',
  credenciais_invalidas: 'O acesso à seguradora foi recusado.',
  cancelado_pelo_humano: 'Alguém interrompeu o acionamento.',
};
const FRASE_PADRAO_DO_ERRO = 'O acionamento parou e precisa de uma pessoa.';

function fraseDoTrabalhoParado(run: Linha): string {
  const codigo = String(run.error_code || '')
    .trim()
    .toLowerCase();
  return FRASE_DO_ERRO[codigo] || FRASE_PADRAO_DO_ERRO;
}

/**
 * O TÍTULO da aprovação, tirado de onde ele REALMENTE mora: `preview` (ou
 * `requested_preview`), os dois JSONB. ⚠️ E é peneirado — 🔴 R11: o `preview` é
 * escrito pelo motor e pode trazer chave de máquina. Só um texto curto e
 * legível sai daqui; qualquer outra coisa vira a frase honesta de ausência.
 */
function tituloDaAprovacao(a: Linha): string {
  const previa = (a.preview || a.requested_preview) as Record<string, unknown> | null;
  const bruto =
    previa && typeof previa === 'object'
      ? (previa.titulo ?? previa.title ?? previa.resumo ?? previa.summary ?? previa.descricao)
      : null;
  const texto = String(bruto ?? '').trim();
  const legivel =
    texto &&
    texto.length <= 120 &&
    !/[_.]/.test(texto.replace(/[.]$/, '')) && // ⛔ `x.y` e `snake_case` não vão para a tela
    !/[{}[\]]/.test(texto);
  return legivel ? texto : 'há uma decisão esperando você';
}

function escolherProximaAcao(e: {
  pediuPessoa: boolean;
  aprovacao: Linha | null;
  run: Linha | null;
  esperando: Espera | null;
  conversaId: string | null;
}): ProximaAcao {
  if (e.pediuPessoa) {
    return {
      texto: 'Assuma a conversa — o cliente pediu para falar com uma pessoa.',
      fonte: 'conversa',
      fonte_id: e.conversaId,
      regra: 'pessoa',
    };
  }
  if (e.aprovacao) {
    return {
      texto: `Aprove ou recuse: ${tituloDaAprovacao(e.aprovacao)}.`,
      fonte: 'aprovacao',
      fonte_id: String(e.aprovacao.id),
      regra: 'aprovacao',
    };
  }
  if (e.run) {
    return {
      // ⛔ NUNCA `error_message`: é texto de motor (R11).
      texto: fraseDoTrabalhoParado(e.run),
      fonte: 'trabalho',
      fonte_id: String(e.run.id),
      regra: 'passo_do_trabalho',
    };
  }
  if (e.esperando?.vence_em) {
    return {
      texto: e.esperando.vencida
        ? 'O prazo da espera venceu — cobre quem está devendo a resposta.'
        : 'Aguardando a resposta dentro do prazo combinado.',
      fonte: 'espera',
      fonte_id: e.esperando.fonte_id,
      regra: 'espera_com_prazo',
    };
  }
  return {
    texto: 'Sem próxima ação declarada.',
    fonte: 'projecao',
    fonte_id: null,
    regra: 'sem_proxima_acao_declarada',
  };
}

const MOTIVO_EM_PORTUGUES: Record<string, string> = {
  acionamento_concluido: 'o acionamento foi concluído',
  encaminhado: 'a seguradora encaminhou o atendimento',
  resolvido_pelo_segurado: 'o segurado resolveu por conta',
  fechado_por_humano: 'a equipe encerrou',
  expirou: 'o prazo expirou',
};

function frasesDaSituacao(
  stage: Stage,
  e: {
    dono: Dono | null;
    esperando: Espera | null;
    cliente: string | null;
    servico: string | null;
    resolucao_motivo: string | null;
    /** 🔴 [P3-1] há relógio? Sem ele não se diz "parado há X" nem se inventa X. */
    temRelogio: boolean;
  },
): string {
  switch (stage) {
    case 'concluido':
      return `Encerrado — ${MOTIVO_EM_PORTUGUES[String(e.resolucao_motivo || '')] || 'desfecho registrado'}.`;
    case 'com_equipe':
      return `${e.dono?.nome || 'Alguém da equipe'} está atendendo.`;
    case 'precisa_de_voce':
      return 'Precisa de uma pessoa da corretora agora.';
    case 'esperando':
      return e.esperando?.kind === 'esperando_cliente'
        ? 'Esperando a resposta do segurado.'
        : e.esperando?.kind === 'esperando_humano'
          ? 'Esperando alguém da equipe.'
          : 'Esperando a seguradora.';
    case 'observacao':
      return `Atendimento da equipe${e.servico ? ` · ${e.servico}` : ''} (observado pelo sistema).`;
    case 'em_conversa':
      return 'Em conversa com o segurado.';
    case 'parado':
      // 🔴 O estado que a SPEC-097 cria. Antes disto, ele se chamava
      //    "concluído" — e 584 atendimentos que ninguém encerrou eram
      //    apresentados ao corretor como trabalho terminado.
      //    ⛔ [P3-1] E SEM RELÓGIO NENHUM A FRASE É OUTRA. Um caso sem
      //    `last_message_at` e sem `started_at` não tem "há quanto tempo": a
      //    tela mostrava "Parado há —", que parece defeito de carga. Dizer que
      //    não há movimento registrado é uma resposta; um travessão não é.
      return e.temRelogio
        ? 'Parado — ninguém falou nem trabalhou nisso, e não há desfecho escrito.'
        : 'Sem movimento registrado — não há nem uma data para dizer desde quando.';
    default:
      return 'Em andamento.';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 🔴 SPEC-086 BLOCO D — A PERGUNTA DA SEXTA-FEIRA, agora na projeção (U5.3)
// ─────────────────────────────────────────────────────────────────────────────
//
// > *"Dos atendimentos desta semana, quantos terminaram, quantos ainda esperam
// > alguém, e quantos morreram esperando?"*
//
// 🔴 Ela morava em `atendimentos/route.ts`, e por isso a Fila conseguia dizer
// `terminaram: 0` no MESMO payload em que listava itens "concluido" (§1.1): os
// dois números saíam de lugares diferentes. Aqui saem do MESMO campo
// `resolvido_em` que decide o estágio — não há como divergirem.
//
// 🔴 `morreram_esperando` fica FORA de `terminaram`. Tecnicamente `expirou`
// também é um fim; contá-lo junto faria a sexta-feira dizer *"12 terminaram"*
// num dia em que sete morreram esperando — e é essa diferença que a SPEC-086
// existe para criar.
//
// ⚠️ CONSEQUÊNCIA CONHECIDA (registrada, não escondida): uma conversa encerrada
// por `expirou` aparece na lista como 'concluido' (R1: o desfecho está ESCRITO)
// e NÃO entra em `terminaram`. É a única forma de os dois números diferirem, e
// é deliberada: ela morreu esperando, ela não terminou.
//
// ⛔ Falha SOZINHA. Se estas duas consultas caírem, a projeção continua
// devolvendo os casos — uma tela que não abre é pior que uma tela sem número.
// ─────────────────────────────────────────────────────────────────────────────
async function montarSemana(
  supabase: Cliente,
  companyId: string,
  indisponivel: Record<Fonte, boolean>,
): Promise<ResumoDaSemana> {
  const semana = new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString();

  // 🔴 A MESMA REGRA QUE PRODUZ O ESTÁGIO.
  //
  // 📊 O defeito de §1.1 era o payload se contradizer: itens "concluido" ao
  // lado de `terminaram: 0`. O conserto de então fez os dois saírem de
  // `resolvido_em` — mas de `conversations.resolvido_em` SÓ, e depois o estágio
  // passou a aceitar também o do EPISÓDIO. A contradição voltava pelo outro
  // lado: um episódio encerrado virava card "Encerrado" e não entrava na conta
  // da sexta-feira.
  //
  // Agora a conta é: EPISÓDIOS resolvidos na semana + as conversas resolvidas
  // na semana que NÃO têm episódio resolvido — sem dupla contagem, e é a mesma
  // unidade que a lista mostra.
  const [episodios, conversas, esperas] = await Promise.all([
    ler(
      supabase
        .from('attendance_sessions')
        .select('id, conversation_id, resolucao_motivo')
        .eq('company_id', companyId) // 🔴 §7
        .gte('resolvido_em', semana)
        .range(0, TETO_DE_CONTEXTO - 1),
    ),
    ler(
      supabase
        .from('conversations')
        .select('id, resolucao_motivo')
        .eq('company_id', companyId) // 🔴 §7
        .gte('resolvido_em', semana)
        .range(0, TETO_DE_CONTEXTO - 1),
    ),
    ler(
      supabase
        .from('work_waits')
        .select('kind, status')
        .eq('company_id', companyId) // 🔴 §7
        .eq('status', 'ativo')
        .range(0, TETO_DE_CONTEXTO - 1),
    ),
  ]);

  // ⚠️ Os motivos vivem no CHECK do banco; esta lista é a MESMA, e o guarda
  //    `test_o_atendimento_termina_e_o_produto_sabe` compara as duas.
  const SUCESSO = new Set([
    'acionamento_concluido',
    'encaminhado',
    'resolvido_pelo_segurado',
    'fechado_por_humano',
  ]);
  const porMotivo: Record<string, number> = {};
  let terminaram = 0;
  let morreram = 0;

  /**
   * ⛔ [P2-3] UM DESFECHO COM MOTIVO ESTRANHO AINDA É UM DESFECHO.
   *
   * O laço antigo contava `expirou` como "morreu esperando", os quatro do
   * sucesso como "terminaram" — e qualquer outro valor SUMIA: nem numa conta,
   * nem na outra. O caso aparecia "Encerrado" na lista e não existia na
   * sexta-feira. Motivo fora da lista conta como terminado e se DECLARA como
   * `outro` em `por_motivo`, para que a diferença apareça em vez de evaporar.
   */
  const conta = (motivo: string) => {
    const m = String(motivo || '').trim();
    if (!m) return;
    if (m === 'expirou') {
      porMotivo[m] = (porMotivo[m] || 0) + 1;
      morreram += 1;
      return;
    }
    if (SUCESSO.has(m)) {
      porMotivo[m] = (porMotivo[m] || 0) + 1;
      terminaram += 1;
      return;
    }
    porMotivo.outro = (porMotivo.outro || 0) + 1;
    terminaram += 1;
  };

  const conversasJaContadas = new Set(
    episodios.linhas.map((e) => String(e.conversation_id || '')).filter(Boolean),
  );
  for (const e of episodios.linhas) conta(String(e.resolucao_motivo || ''));
  for (const c of conversas.linhas) {
    // ⛔ a conversa cujo episódio já foi contado NÃO conta de novo: ela é o
    //    ESPELHO do mesmo desfecho (o BFF grava nos dois).
    if (conversasJaContadas.has(String(c.id))) continue;
    conta(String(c.resolucao_motivo || ''));
  }

  const porKind: Record<string, number> = {};
  for (const w of esperas.linhas) {
    const k = String(w.kind || '?');
    porKind[k] = (porKind[k] || 0) + 1;
  }

  // ⛔ O ZERO — E O NÚMERO TRUNCADO — DECLARADOS. Uma fonte fora do ar e um
  //    recorte no teto produzem o mesmo estrago: um número com cara de medido
  //    que não é o da corretora.
  const truncou =
    episodios.linhas.length >= TETO_DE_CONTEXTO ||
    conversas.linhas.length >= TETO_DE_CONTEXTO ||
    esperas.linhas.length >= TETO_DE_CONTEXTO;
  if (!episodios.ok) indisponivel.sessoes = true;
  if (!conversas.ok) indisponivel.conversas = true;
  if (!esperas.ok) indisponivel.esperas = true;

  return {
    terminaram,
    ainda_esperam: esperas.linhas.length,
    morreram_esperando: morreram,
    por_motivo: porMotivo,
    por_kind: porKind,
    indisponivel: !episodios.ok || !conversas.ok || !esperas.ok || truncou,
  };
}
