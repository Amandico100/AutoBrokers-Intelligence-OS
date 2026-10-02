/**
 * O PLACAR do diário de decisões — SPEC-125 S6.
 *
 * Poucos números que ajudam a DECIDIR (ligar mais, pausar uma seguradora, ensinar o agente),
 * calculados sobre as linhas de `diario_de_decisoes` que a rota JÁ filtrou por corretora
 * (a da corretora: `.eq('company_id', sessão)`; a do master: todas, ou uma escolhida).
 * Função PURA: recebe as linhas e o "agora", devolve os números — o teste confere à mão.
 *
 * As definições (cada uma diz POR QUE é assim — CLAUDE.md §9.5):
 *  · ATENDIMENTO = a conversa (`conversation_id`) ou o acionamento (`work_run_id`); sem nenhum
 *    dos dois, a própria linha. O Founder pergunta "de 100 atendimentos, quantos chamaram gente?",
 *    não "de 100 decisões".
 *  · RESOLVIDO SEM ATENDENTE = nenhuma decisão daquele atendimento chamou uma pessoa
 *    (`acao='chamou_pessoa'`) nem terminou com o segurado pedindo pessoa / uma pessoa corrigindo.
 *  · VIROU PERGUNTA AO SEGURADO = decisões em que o agente perguntou ao segurado, entre as que
 *    AGIRAM (modo `on`) — sombra não conta, porque nada saiu.
 *  · ERRO GRAVE (meta 0) = o agente AGIU sozinho (respondeu à URA, ao portal ou ao segurado) e
 *    (a) a decisão era do tipo que só uma pessoa pode tomar (`nunca_sozinho`), ou (b) era uma
 *    DEDUÇÃO e a corretora marcou "errado". Erro em conduzir/responder com dado do caso é LEVE:
 *    a URA ou o segurado corrigem no turno seguinte.
 *  · TENDÊNCIA = últimos 7 dias × os 7 anteriores.
 */

export interface LinhaDoPlacar {
  id: string;
  created_at: string;
  company_id?: string;
  seguradora?: string | null;
  classe?: string | null;
  acao?: string | null;
  modo?: string | null;
  resultado?: string | null;
  veredito?: string | null;
  work_run_id?: string | null;
  conversation_id?: string | null;
}

export interface Contagem { certo: number; errado: number; sem: number; total: number }

export interface Semana { decisoes: number; pct_sem_atendente: number | null; pct_certo: number | null }

export interface Placar {
  janela_dias: number;
  decisoes: number;
  atendimentos: number;
  pct_sem_atendente: number | null;
  pct_pergunta_ao_segurado: number | null;
  avaliadas: Contagem;
  por_seguradora: Record<string, Contagem>;
  por_classe: Record<string, Contagem>;
  erros_graves: number;
  erros_leves: number;
  semana: Semana;
  semana_anterior: Semana;
}

const AGIU = new Set(['respondeu_ura', 'respondeu_portal', 'respondeu_segurado']);
const CHAMOU_GENTE_DEPOIS = new Set(['segurado_pediu_pessoa', 'humano_corrigiu']);
const ERRO_LEVE = new Set(['segurado_corrigiu', 'segurado_repetiu', 'segurado_pediu_pessoa', 'agente_repetiu_pergunta']);
const DIA = 86_400_000;

const pct = (n: number, d: number): number | null => (d > 0 ? Math.round((100 * n) / d) : null);

function somar(c: Contagem, veredito: string | null | undefined) {
  c.total += 1;
  if (veredito === 'certo') c.certo += 1;
  else if (veredito === 'errado') c.errado += 1;
  else c.sem += 1;
}

function contar(alvo: Record<string, Contagem>, chave: string, veredito: string | null | undefined) {
  somar((alvo[chave] = alvo[chave] || { certo: 0, errado: 0, sem: 0, total: 0 }), veredito);
}

function chaveDoAtendimento(l: LinhaDoPlacar): string {
  return l.conversation_id ? `c:${l.conversation_id}` : l.work_run_id ? `r:${l.work_run_id}` : `l:${l.id}`;
}

function semAtendente(linhas: LinhaDoPlacar[]): { atendimentos: number; sem: number } {
  const chamou = new Map<string, boolean>();
  for (const l of linhas) {
    const k = chaveDoAtendimento(l);
    const gente = l.acao === 'chamou_pessoa' || CHAMOU_GENTE_DEPOIS.has(String(l.resultado || ''));
    chamou.set(k, Boolean(chamou.get(k)) || gente);
  }
  let sem = 0;
  chamou.forEach((v) => { if (!v) sem += 1; });
  return { atendimentos: chamou.size, sem };
}

function semana(linhas: LinhaDoPlacar[]): Semana {
  const s = semAtendente(linhas);
  const avaliadas = linhas.filter((l) => l.veredito === 'certo' || l.veredito === 'errado');
  return {
    decisoes: linhas.length,
    pct_sem_atendente: pct(s.sem, s.atendimentos),
    pct_certo: pct(avaliadas.filter((l) => l.veredito === 'certo').length, avaliadas.length),
  };
}

export function eErroGrave(l: LinhaDoPlacar): boolean {
  if (l.modo !== 'on' || !AGIU.has(String(l.acao || ''))) return false;
  return l.classe === 'nunca_sozinho' || (l.classe === 'deduzir' && l.veredito === 'errado');
}

export function calcularPlacar(linhas: LinhaDoPlacar[], agora: Date = new Date(), janelaDias = 30): Placar {
  const t = agora.getTime();
  const naJanela = linhas.filter((l) => t - Date.parse(l.created_at) <= janelaDias * DIA);
  const s = semAtendente(naJanela);
  const agiram = naJanela.filter((l) => l.modo === 'on' && l.acao !== 'nao_agiu');
  const avaliadas: Contagem = { certo: 0, errado: 0, sem: 0, total: 0 };
  const porSeguradora: Record<string, Contagem> = {};
  const porClasse: Record<string, Contagem> = {};
  for (const l of naJanela) {
    somar(avaliadas, l.veredito);
    contar(porSeguradora, String(l.seguradora || 'sem seguradora'), l.veredito);
    contar(porClasse, String(l.classe || '?'), l.veredito);
  }
  const idade = (l: LinhaDoPlacar) => t - Date.parse(l.created_at);
  return {
    janela_dias: janelaDias,
    decisoes: naJanela.length,
    atendimentos: s.atendimentos,
    pct_sem_atendente: pct(s.sem, s.atendimentos),
    pct_pergunta_ao_segurado: pct(agiram.filter((l) => l.acao === 'perguntou_segurado').length, agiram.length),
    avaliadas,
    por_seguradora: porSeguradora,
    por_classe: porClasse,
    erros_graves: naJanela.filter(eErroGrave).length,
    erros_leves: naJanela.filter((l) => ERRO_LEVE.has(String(l.resultado || ''))).length,
    semana: semana(naJanela.filter((l) => idade(l) <= 7 * DIA)),
    semana_anterior: semana(naJanela.filter((l) => idade(l) > 7 * DIA && idade(l) <= 14 * DIA)),
  };
}

/** As colunas que o placar lê — as rotas pedem SÓ estas (nunca a tela completa). */
export const COLUNAS_DO_PLACAR =
  'id, created_at, company_id, seguradora, classe, acao, modo, resultado, veredito, work_run_id, conversation_id';
