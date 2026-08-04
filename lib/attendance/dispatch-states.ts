// A LISTA CANÔNICA DE ESTADOS DO ACIONAMENTO — no TypeScript.
//
// Espelho de `DISPATCH_STATES`, em
// `backend/app/services/insurer_dispatch_service.py`. O backend é a autoridade:
// é ele que produz os estados. Este arquivo existe para que o front pare de
// reinventá-los, um arquivo por vez.
//
// ─────────────────────────────────────────────────────────────────────────────
// POR QUE ELE PRECISOU NASCER
//
// 📊 Auditoria de 04/08/2026. `encaminhado` — o SEGUNDO desfecho de sucesso do
// produto (a seguradora não abre chamado por aquele canal, entrega o formulário
// ou a orientação, e o corredor entrega isso ao segurado) — existia no Python
// desde 03/08 e **não existia em lugar nenhum do TypeScript**. Nem `resolvido`,
// criado no mesmo dia, que é o desfecho que o produto existe para produzir.
//
// O preço não foi um erro visível. Foi uma tela que MENTE:
//
//   app/api/dashboard/atendimentos/route.ts   a cadeia de ternários terminava
//     em 'acionando'. Um caso ENCERRADO COM SUCESSO aparecia para o corretor
//     como "Conversando com a seguradora agora para abrir o serviço."
//   ...e os contadores somavam o mesmo caso em "Acionando", de modo que a
//     MÉTRICA DE SUCESSO do produto era publicada como trabalho em andamento.
//   app/admin/acionamentos/page.tsx           sem a chave, cinza de "estado
//     desconhecido" em vez de verde de concluído.
//   .../casos/HistoricoClient.tsx             o filtro "Concluídos" testa
//     `stage === 'concluido'`; caso encaminhado NUNCA entrava nele.
//
// E a causa não foi distração: **cada arquivo mantinha a sua própria lista**.
// Sete listas, escritas à mão, em sete arquivos. Um estado novo nasce órfão em
// seis delas por construção — e ninguém fica sabendo, porque o
// `Record<string, X>` de TypeScript não reclama de chave que falta.
//
// Aqui há UMA lista. Os mapas abaixo são `Record<DispatchState, …>` **exaustivos
// por tipo**: acrescentar um estado a `DISPATCH_STATES` sem lhe dar rótulo,
// estágio e tom passa a ser erro de compilação, não um cinza silencioso na tela.
//
// E `scripts/atendimento-estados.test.mjs` lê o PYTHON e compara com esta
// lista: o dia em que o backend criar um estado que o front não conhece, o
// teste fica vermelho antes de a tela mentir.

/**
 * Os estados do acionamento, na ordem da máquina de estados do backend.
 * Espelho literal de `insurer_dispatch_service.DISPATCH_STATES`.
 */
export const DISPATCH_STATES = [
  'preparing',
  'ready_to_send',
  'ura',
  'human_phase',
  'captured',
  'monitoring',
  'encaminhado',
  'resolvido',
  'test_aborted',
  'needs_human',
] as const;

export type DispatchState = (typeof DISPATCH_STATES)[number];

/**
 * ENCERRADOS: a máquina não fala mais com a seguradora por conta própria.
 * Espelho de `FASES_ENCERRADAS` + `test_aborted`.
 */
export const DISPATCH_STATES_ENCERRADOS = [
  'encaminhado',
  'resolvido',
  'test_aborted',
  'needs_human',
] as const;

/** Os estágios em linguagem humana — o que o corretor lê na tela. */
export const ATTENDANCE_STAGES = [
  'precisa_de_voce',
  'acionando',
  'protocolo',
  'monitorando',
  'em_conversa',
  'com_equipe',
  'observacao',
  'concluido',
] as const;

export type Stage = (typeof ATTENDANCE_STAGES)[number];

/** Mesmos valores de `StatusTone` (components/patterns/StatusPill).
 *  Repetido aqui — e só aqui — porque este arquivo não importa NADA: ele é
 *  transpilado e executado sozinho pelo teste, sem resolver o alias `@/`. */
export type StageTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'approval';

/**
 * Estado do motor → estágio que o corretor lê.
 *
 * `encaminhado`, `resolvido` e `test_aborted` são `concluido`: os três são
 * TERMINAIS. Um caso encaminhado não está "acionando" coisa nenhuma — o
 * segurado já está com o formulário na mão.
 */
export const STAGE_BY_DISPATCH_STATE: Record<DispatchState, Stage> = {
  preparing: 'acionando',
  ready_to_send: 'acionando',
  ura: 'acionando',
  human_phase: 'acionando',
  captured: 'protocolo',
  monitoring: 'monitorando',
  encaminhado: 'concluido',
  resolvido: 'concluido',
  test_aborted: 'concluido',
  needs_human: 'precisa_de_voce',
};

/**
 * O estágio de um estado do motor. Estado DESCONHECIDO cai em `acionando` — o
 * mesmo comportamento da cadeia de ternários que existia antes, de propósito:
 * um estado que este arquivo ainda não conhece é, quase por definição, trabalho
 * em voo. Quem impede que ele fique desconhecido é o teste, não este `??`.
 */
export function stageFromDispatchState(state: string | null | undefined): Stage {
  const key = String(state || '') as DispatchState;
  return STAGE_BY_DISPATCH_STATE[key] || 'acionando';
}

export function isDispatchStateEncerrado(state: string | null | undefined): boolean {
  return (DISPATCH_STATES_ENCERRADOS as readonly string[]).includes(String(state || ''));
}

/**
 * O que cada estado do motor mostra numa lista de acionamentos.
 * `detalhe` é a frase que o corretor lê — em linguagem de gente, não de máquina.
 */
export const DISPATCH_STATE_META: Record<DispatchState, { label: string; tone: StageTone; detalhe: string }> = {
  preparing: {
    label: 'Preparando',
    tone: 'neutral',
    detalhe: 'Reunindo os dados do caso antes de falar com a seguradora.',
  },
  ready_to_send: {
    label: 'Pronto para acionar',
    tone: 'neutral',
    detalhe: 'Tudo o que a seguradora vai pedir já está em mãos.',
  },
  ura: {
    label: 'Respondendo a URA',
    tone: 'info',
    detalhe: 'Conversando com a seguradora agora para abrir o serviço.',
  },
  human_phase: {
    label: 'Especialista da seguradora',
    tone: 'info',
    detalhe: 'Falando com o especialista da assistência para abrir o serviço.',
  },
  captured: {
    label: 'Protocolo capturado',
    tone: 'success',
    detalhe: 'Protocolo garantido — serviço confirmado na seguradora.',
  },
  monitoring: {
    label: 'Acompanhando o prestador',
    tone: 'success',
    detalhe: 'Serviço confirmado — acompanhando a chegada do prestador.',
  },
  // O desfecho que faltava. A frase diz o que ACONTECEU, e não o que a máquina
  // fez: encaminhar não é falhar, é o desfecho correto naquela seguradora.
  encaminhado: {
    label: 'Resolvido por encaminhamento',
    tone: 'success',
    detalhe: 'A seguradora não abre chamado por este canal — o formulário/orientação já foi entregue ao segurado.',
  },
  resolvido: {
    label: 'Resolvido',
    tone: 'success',
    detalhe: 'Serviço prestado e ciclo encerrado com o segurado.',
  },
  test_aborted: {
    label: 'Teste concluído',
    tone: 'success',
    detalhe: 'Corredor executado ponta a ponta em modo teste e cancelado antes de abrir o serviço.',
  },
  needs_human: {
    label: 'Precisa de você',
    tone: 'danger',
    detalhe: 'O acionamento precisa de uma pessoa — o dossiê já foi entregue à equipe.',
  },
};

export function dispatchStateMeta(state: string | null | undefined): { label: string; tone: StageTone; detalhe: string } {
  const key = String(state || '') as DispatchState;
  return DISPATCH_STATE_META[key] || {
    label: 'Acionando',
    tone: 'info',
    detalhe: 'Conversando com a seguradora agora para abrir o serviço.',
  };
}

/** O rótulo de cada ESTÁGIO — o que aparece na pílula da fila e do histórico. */
export const STAGE_META: Record<Stage, { label: string; tone: StageTone; desc: string }> = {
  precisa_de_voce: {
    label: 'Precisa de você',
    tone: 'danger',
    desc: 'aguardando uma pessoa da corretora',
  },
  acionando: {
    label: 'Acionando a seguradora',
    tone: 'info',
    desc: 'o sistema está abrindo o serviço agora',
  },
  protocolo: {
    label: 'Protocolo garantido',
    tone: 'success',
    desc: 'serviço confirmado na seguradora',
  },
  monitorando: {
    label: 'Acompanhando o prestador',
    tone: 'success',
    desc: 'serviço confirmado — monitorando a chegada',
  },
  em_conversa: {
    label: 'Em conversa',
    tone: 'info',
    desc: 'o atendente está falando com o segurado',
  },
  com_equipe: {
    label: 'Com a equipe',
    tone: 'warning',
    desc: 'alguém da corretora assumiu',
  },
  observacao: {
    label: 'Atendimento da equipe (observado)',
    tone: 'neutral',
    desc: 'a atendente conversa e o sistema registra',
  },
  concluido: {
    label: 'Concluído',
    tone: 'neutral',
    desc: 'o trabalho terminou',
  },
};

/** Os estágios que a FILA mostra (o que está acontecendo agora). `concluido`
 *  fica de fora: fila é trabalho vivo. */
export const STAGES_EM_VOO: readonly Stage[] = ATTENDANCE_STAGES.filter((s) => s !== 'concluido');

/** Contadores zerados, um por estágio — sem repetir a lista à mão. */
export function zeroCountsByStage(): Record<Stage, number> {
  const counts = {} as Record<Stage, number>;
  for (const stage of ATTENDANCE_STAGES) counts[stage] = 0;
  return counts;
}
