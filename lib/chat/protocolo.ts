/**
 * SPEC-096 · C.1 — O PROTOCOLO DA INTERAÇÃO, DO LADO DA TELA
 *
 * O chat deixa de adivinhar o que está acontecendo lendo o TEXTO que chega.
 * 📊 Medição de 04/09/2026 (SPEC-096 §1.4): tudo saía como `{"token": "…"}` e a
 * tela parseava `{"type":"ucp_` do conteúdo para descobrir estágio — o que não
 * era resposta virava resposta, e virava MEMÓRIA.
 *
 * Aqui o chat passa a falar tipado: `autobrokers.interaction.v1` (R4).
 *
 * ⛔ Este módulo é PURO: sem React, sem fetch, sem DOM. É o que permite que o
 * guarda o execute em memória (`scripts/o-chat-responde-e-continua.test.mjs`
 * [11]/[12]) sem subir servidor nenhum.
 */

export const PROTOCOLO = 'autobrokers.interaction.v1';

export type TipoDeEvento =
  | 'turn.accepted'
  | 'stage.started'
  | 'stage.completed'
  | 'assistant.content.delta'
  | 'assistant.content.completed'
  | 'artifact.ready'
  | 'policy.blocked'
  | 'notice'
  | 'error'
  | 'turn.completed'
  | 'heartbeat';

export interface Envelope {
  protocol: string;
  seq: number;
  type: TipoDeEvento;
  turn: unknown;
  payload: Record<string, unknown>;
  occurred_at?: string;
  /** 🔴 marcado pelo PARSER, nunca pelo servidor: o `seq` saltou. */
  transport?: 'gap';
}

/** A peça pronta que o turno produziu — o cartão que a conversa mostra. */
export interface RefDeArtifact {
  artifact_id: string;
  title: string;
  kind_human: string;
  href: string;
}

export type StatusDoTurno =
  | 'idle'
  | 'submitting'
  | 'streaming'
  | 'stopped'
  | 'complete'
  | 'failed';

export interface AvisoDoTurnoDados {
  code: string;
  message_human: string;
  kind: 'policy' | 'notice' | 'error';
}

export interface Turno {
  status: StatusDoTurno;
  clientRequestId: string | null;
  assistantMessageId: string | null;
  userMessageId: string | null;
  /** UMA linha de atividade por vez (R11) — nunca a árvore de execução. */
  stage: { key: string; label: string } | null;
  transport: 'ok' | 'gap' | 'reconnecting';
  aviso: AvisoDoTurnoDados | null;
  artifacts: RefDeArtifact[];
}

export const TURNO_INICIAL: Turno = {
  status: 'idle',
  clientRequestId: null,
  assistantMessageId: null,
  userMessageId: null,
  stage: null,
  transport: 'ok',
  aviso: null,
  artifacts: [],
};

/** O turno começa: o eco local é imediato, e o id é o MESMO do retry (R3). */
export function turnoNovo(clientRequestId: string, assistantMessageId: string): Turno {
  return {
    ...TURNO_INICIAL,
    status: 'submitting',
    clientRequestId,
    assistantMessageId,
    artifacts: [],
  };
}

function texto(v: unknown): string {
  return typeof v === 'string' ? v : '';
}

/**
 * O parser SSE do envelope v1.
 *
 * · `data: {json}` por evento; `data: [DONE]` encerra.
 * · protocolo diferente de v1 é IGNORADO (com aviso no console) — o widget
 *   legado e o painel dividem o mesmo cano.
 * · 🔴 `seq` monotônico: se ele salta, o evento que chegou depois do buraco sai
 *   marcado com `transport: 'gap'`. Sem isso o buraco no stream passa
 *   despercebido e a resposta fica com um pedaço faltando, calada.
 */
export async function* lerEventos(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<Envelope> {
  const leitor = body.getReader();
  const decodificador = new TextDecoder();
  let sobra = '';
  let ultimoSeq: number | null = null;

  try {
    while (true) {
      const { done, value } = await leitor.read();
      if (done) break;

      sobra += decodificador.decode(value, { stream: true });
      const partes = sobra.split('\n\n');
      sobra = partes.pop() || '';

      for (const parte of partes) {
        const linha = parte.trim();
        if (!linha.startsWith('data:')) continue;

        const cru = linha.slice(linha.indexOf(':') + 1).trim();
        if (cru === '[DONE]') return;
        if (!cru) continue;

        let bruto: any;
        try {
          bruto = JSON.parse(cru);
        } catch {
          console.warn('[chat] evento ilegível descartado');
          continue;
        }

        if (!bruto || typeof bruto !== 'object') continue;
        if (bruto.protocol !== PROTOCOLO) {
          console.warn(`[chat] evento de outro protocolo ignorado: ${String(bruto.protocol)}`);
          continue;
        }

        const evento: Envelope = {
          protocol: bruto.protocol,
          seq: Number(bruto.seq),
          type: bruto.type,
          turn: bruto.turn,
          payload: bruto.payload && typeof bruto.payload === 'object' ? bruto.payload : {},
          occurred_at: bruto.occurred_at,
        };

        if (
          ultimoSeq !== null &&
          Number.isFinite(evento.seq) &&
          evento.seq > ultimoSeq + 1
        ) {
          evento.transport = 'gap';
        }
        if (Number.isFinite(evento.seq)) ultimoSeq = evento.seq;

        yield evento;
      }
    }
  } finally {
    try {
      leitor.releaseLock();
    } catch {
      /* o stream já terminou */
    }
  }
}

/**
 * O reducer do Turno. PURO — mesma entrada, mesma saída, sem relógio.
 *
 * 🔴 R5: `policy.blocked` e `notice` viram AVISO, nunca conteúdo do assistente.
 * 📊 Hoje eles viram mensagem gravada — e viram memória da corretora.
 *
 * 🔴 R6: o estágio nasce do EVENTO (`stage.started`/`stage.completed`) e some
 * no `stage.completed` ou no primeiro delta. Nunca de `setTimeout`.
 */
export function reduzirTurno(turno: Turno, ev: Envelope): Turno {
  const base: Turno =
    ev.transport === 'gap' && turno.transport === 'ok'
      ? { ...turno, transport: 'gap' }
      : turno;

  switch (ev.type) {
    case 'turn.accepted':
      return {
        ...base,
        status: 'streaming',
        userMessageId: texto(ev.payload.user_message_id) || base.userMessageId,
        assistantMessageId:
          texto(ev.payload.assistant_message_id) || base.assistantMessageId,
      };

    case 'stage.started':
      return {
        ...base,
        status: base.status === 'submitting' ? 'streaming' : base.status,
        stage: {
          key: texto(ev.payload.key) || 'trabalho',
          label: texto(ev.payload.label) || 'Trabalhando nisso…',
        },
      };

    case 'stage.completed':
      return { ...base, stage: null };

    case 'assistant.content.delta':
      // O primeiro pedaço de resposta apaga a linha de atividade: a partir daqui
      // a evidência do trabalho é o próprio texto.
      return { ...base, status: 'streaming', stage: null };

    case 'assistant.content.completed':
      return { ...base, stage: null };

    case 'artifact.ready': {
      const artifactId = texto(ev.payload.artifact_id);
      if (!artifactId) return base;
      if (base.artifacts.some((a) => a.artifact_id === artifactId)) return base;
      const ref: RefDeArtifact = {
        artifact_id: artifactId,
        title: texto(ev.payload.title) || 'Entrega',
        kind_human: texto(ev.payload.kind_human) || 'Entrega',
        href: texto(ev.payload.href) || `/dashboard/entregas/${artifactId}`,
      };
      return { ...base, artifacts: [...base.artifacts, ref] };
    }

    case 'policy.blocked':
      return {
        ...base,
        status: 'failed',
        stage: null,
        aviso: {
          kind: 'policy',
          code: texto(ev.payload.code) || 'policy',
          message_human:
            texto(ev.payload.message_human) || 'Não posso seguir com este pedido.',
        },
      };

    case 'notice':
      return {
        ...base,
        status: 'failed',
        stage: null,
        aviso: {
          kind: 'notice',
          code: texto(ev.payload.code) || 'notice',
          message_human: texto(ev.payload.message_human) || 'Sem resposta desta vez.',
        },
      };

    case 'error':
      return {
        ...base,
        status: 'failed',
        stage: null,
        aviso: {
          kind: 'error',
          code: texto(ev.payload.code) || 'unknown',
          message_human:
            texto(ev.payload.message_human) ||
            'Algo falhou no meio do caminho. Pode tentar de novo.',
        },
      };

    case 'turn.completed':
      return {
        ...base,
        status: base.status === 'failed' || base.status === 'stopped' ? base.status : 'complete',
        stage: null,
        transport: base.transport === 'gap' ? 'gap' : 'ok',
      };

    case 'heartbeat':
      return base;

    default:
      return base;
  }
}

/** O nome curto que a SPEC usa no texto; o guarda procura `reduzirTurno`. */
export const reduzir = reduzirTurno;

/** "Parar" foi do corretor: preserva o parcial e não é erro (R8). */
export function turnoParado(turno: Turno): Turno {
  return {
    ...turno,
    status: 'stopped',
    stage: null,
    aviso: {
      kind: 'notice',
      code: 'stopped_by_user',
      message_human: 'Resposta parada por você. O que já veio ficou salvo.',
    },
  };
}
