'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { ChatWelcome } from '@/components/chat/ChatWelcome';
import { LinhaDeAtividade } from '@/components/chat/LinhaDeAtividade';
import { AvisoDoTurno } from '@/components/chat/AvisoDoTurno';
import { VoltarAoFim } from '@/components/chat/VoltarAoFim';
import { COLUNA_DA_CONVERSA } from '@/components/chat/coluna';
import { Composer } from '@/components/chat/composer/Composer';
import type { ComposerHandle } from '@/components/chat/composer/Composer';
import type { AnexoDoPedido, AnexoEnviado, OpcoesDoEnvio } from '@/components/chat/composer/tipos';
import { MessageBubble } from '@/components/MessageBubble';
import { TypingIndicator } from '@/components/TypingIndicator';
import { lerEventos, reduzirTurno } from '@/lib/chat/protocolo';
import type { Turno } from '@/lib/chat/protocolo';
import { supabase } from '@/lib/supabase'; // KEPT: Only for Realtime subscriptions
import { Message } from '@/lib/types';
import { useUserId } from '@/hooks/useUserId';
import { toast } from 'sonner';

/** A distância do fim, em pixels, dentro da qual a tela ainda acompanha (C.2). */
const PERTO_DO_FIM = 120;

/** Quantas mensagens cada "carregar anteriores" traz (R10). */
const PAGINA = 60;

/**
 * O turno em repouso. Escrito aqui, inteiro, em vez de importado: é o estado
 * inicial de um `useState` e ele precisa existir na primeira linha do primeiro
 * render, sem depender de nada.
 */
const TURNO_PARADO: Turno = {
  status: 'idle',
  clientRequestId: null,
  assistantMessageId: null,
  userMessageId: null,
  stage: null,
  transport: 'ok',
  aviso: null,
  artifacts: [],
};

/**
 * SPEC-132-A — o esforço que o pedido leva. Só os três passam (B8); qualquer outra coisa vira Equilibrado AQUI,
 * antes de sair da tela (o backend confere de novo).
 */
const ESFORCOS_DO_PEDIDO = ['rapido', 'equilibrado', 'maximo'];
function esforcoDoPedido(valor: unknown): string {
  return typeof valor === 'string' && ESFORCOS_DO_PEDIDO.includes(valor) ? valor : 'equilibrado';
}

interface EnvioDoTurno {
  message: string;
  /** SPEC-132-A — os anexos JÁ SUBIDOS (`POST /api/upload`); o pedido leva só `{bucket, path, nome, mime, bytes}` */
  anexos: AnexoEnviado[];
  esforco: string;
  clientRequestId: string;
  assistantMsgId: string;
  /** a bolha da pergunta NESTA sessão (o envio pelo composer); sai da conversa se o BFF recusar antes do turno */
  userMsgId?: string;
}

/**
 * 🔴 Conserto da SPEC-132-A (juiz P4) — a recusa veio do PRÓPRIO BFF, antes de gravar a conversa ou a pergunta?
 * O BFF recusa com 4xx e corpo `{error|message|motivo}`; o 4xx que ele só REPASSA do backend traz `status` no corpo
 * (a pergunta já foi gravada — aí vale o "Tentar de novo"). 404 tem caminho próprio (a conversa não é desta pessoa).
 */
function recusaAntesDoTurno(status: number, corpo: unknown): boolean {
  if (status < 400 || status >= 500 || status === 404) return false;
  const c = (corpo && typeof corpo === 'object' ? corpo : {}) as Record<string, unknown>;
  return !('status' in c);
}

/** A frase da recusa, em português: o `motivo`/`message` do BFF, ou uma genérica (nunca o código técnico). */
function textoDaRecusa(corpo: unknown): string {
  const c = (corpo && typeof corpo === 'object' ? corpo : {}) as Record<string, unknown>;
  for (const campo of ['motivo', 'message']) {
    const v = c[campo];
    if (typeof v === 'string' && v.trim() && !/^[A-Z0-9_]+$/.test(v.trim())) return v.trim();
  }
  return 'Não consegui enviar esta mensagem.';
}

/** Só o que o contrato do pedido pede — a URL e a miniatura local nunca saem da tela (D-132A-05). */
function anexosDoPedido(anexos: AnexoEnviado[]): AnexoDoPedido[] {
  return anexos.map((a) => ({ bucket: a.bucket, path: a.path, nome: a.nome, mime: a.mime, bytes: a.bytes }));
}

/**
 * "Tentar de novo" depois de recarregar a página: o envio é remontado da última pergunta GRAVADA (o mesmo
 * `client_request_id`, os mesmos anexos), porque o `envioRef` só vive enquanto a aba vive. Só vale quando a
 * resposta do AutoBrokers é a ÚLTIMA mensagem da conversa.
 */
function envioDaUltimaResposta(lista: Message[]): EnvioDoTurno | null {
  const ultima = lista.length > 0 ? lista[lista.length - 1] : null;
  if (!ultima || ultima.role !== 'assistant' || ultima.sender_user_id) return null;
  for (let i = lista.length - 2; i >= 0; i--) {
    const pergunta = lista[i];
    if (pergunta.role !== 'user') continue;
    const crid = pergunta.payload?.client_request_id;
    if (!crid) return null;
    const gravados = Array.isArray(pergunta.payload?.attachments) ? (pergunta.payload!.attachments as any[]) : [];
    const anexos: AnexoEnviado[] = gravados
      .filter((a) => a && typeof a.path === 'string' && a.path)
      .map((a) => ({
        bucket:
          (typeof a.bucket === 'string' && a.bucket) ||
          String(a.path).split('/').find((seg: string) => seg === 'chat-media' || seg === 'chat-docs') ||
          (String(a.mime || '').startsWith('image/') ? 'chat-media' : 'chat-docs'),
        path: a.path,
        nome: typeof a.nome === 'string' ? a.nome : 'arquivo',
        mime: typeof a.mime === 'string' ? a.mime : 'application/octet-stream',
        bytes: typeof a.bytes === 'number' ? a.bytes : 0,
      }));
    const gravadoNoTurno = (ultima.payload?.turn as { esforco?: unknown } | undefined)?.esforco;
    return {
      // SPEC-132-A (A4) — sem texto, o BFF gravou "[Anexo] nome…" como conteúdo. Reenviar ISSO como texto faria o
      // backend tratar a transcrição do áudio como bloco anexo de uma "pergunta" que o corretor nunca escreveu.
      message: anexos.length > 0 && /^\[Anexo\]\s/.test(pergunta.content || '') ? '' : pergunta.content,
      anexos,
      esforco: esforcoDoPedido(gravadoNoTurno),
      clientRequestId: crid,
      assistantMsgId: ultima.id,
    };
  }
  return null;
}

/* ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 * SPEC-132 · A5 — A RESPOSTA QUE CHEGA DEPOIS
 *
 * A Cotação Rápida responde FORA do turno: o Work Run `cotacao.chat` grava a mensagem do assistente na MESMA conversa
 * (com `payload.cotacao`) 1 a 6 min depois. 📊 14/10/2026, produção: `select tablename from pg_publication_tables
 * where pubname='supabase_realtime' and tablename in ('messages','conversations')` → 0 linhas — o `postgres_changes`
 * abaixo nunca recebe nada, e a resposta só aparecia recarregando. D-132B-09: a tela CONSULTA, de tempos em tempos,
 * a mesma rota que abre a conversa (`/api/conversations?session_id=`, que já filtra pelo dono da sessão), em vez de
 * abrir o Realtime de `messages`.
 *
 * ⛔ Mora aqui, e não num arquivo ao lado: os três testes que EXECUTAM esta página (o do shell, o do chat novo e o dos
 *    relatórios) resolvem imports desconhecidos como `{}` — um hook importado viraria "não é uma função" neles.
 * ───────────────────────────────────────────────────────────────────────────────────────────────────────────────── */

/** 💭 De quanto em quanto tempo a tela pergunta se a resposta chegou — com a aba visível. */
const ESPERA_INTERVALO_MS = 6_000;
/** 💭 Quanto tempo a tela espera. O Work Run desiste em 💭 6 min e grava a frase honesta; 10 min cobre a folga. */
const ESPERA_TETO_MS = 10 * 60_000;

/**
 * 🔴 COMO A TELA SABE QUE UMA COTAÇÃO FOI DISPARADA.
 *
 * O SSE não traz o NOME da ferramenta (`chat_eventos.estagio_da_tool` o troca por uma frase), e o `stage.completed`
 * não diz se ela deu certo: a recusa ("Esse ramo eu ainda não calculo por aqui") também completa. A prova de que o
 * cálculo COMEÇOU é a frase que a `cotacao_disparar`/`cotacao_ajustar` devolvem só quando abriram o Work Run
 * (`cotacao/resposta.py` · `frase_calculando`: "… — volto aqui com o resultado em 1 a 2 minutos") e que o agente é
 * instruído a repetir. Então:
 *   · a frase da promessa no texto final              → espera (funciona hoje, com o estágio genérico);
 *   · o estágio `quote.calculating` + "calculando"    → espera (quando o catálogo de estágios ganhar a chave, o
 *                                                       agente pode parafrasear a frase sem a tela perder a espera).
 * Recusa, erro, "o cálculo começou mas não consegui acompanhá-lo" e qualquer turno comum: não esperam.
 */
const CHAVES_DO_CALCULO = new Set(['quote.calculating']);
const PROMESSA_DO_CALCULO = /volto aqui com o resultado/i;
const FALA_DO_CALCULO = /\b(re)?calculando\b/i;

function prometeuCalcular(texto: string, viuOCalculo: boolean): boolean {
  const t = typeof texto === 'string' ? texto : '';
  if (PROMESSA_DO_CALCULO.test(t)) return true;
  return viuOCalculo && FALA_DO_CALCULO.test(t);
}

/** A espera em curso: até quando, e quantas respostas ainda faltam (um disparo e um ajuste = duas). */
interface EsperaDaResposta {
  ate: number;
  pendentes: number;
}

/**
 * Ao ABRIR uma conversa (ou relê-la): a regra é CONSERVADORA de propósito — só espera quando a ÚLTIMA resposta do
 * AutoBrokers é a PROMESSA do cálculo (a frase exata da ferramenta, não um "calculando" qualquer), ainda sem
 * `payload.cotacao` (não é a própria resposta da cotação), e tem menos de 10 min. Fora disso o resultado, se vier,
 * aparece ao recarregar — melhor do que uma linha "Calculando…" que mente.
 */
function esperaAoAbrir(lista: Message[], agora: number): EsperaDaResposta | null {
  let ultima: Message | null = null;
  for (let i = lista.length - 1; i >= 0; i--) {
    const m = lista[i];
    if (m.role === 'assistant' && !m.sender_user_id) {
      ultima = m;
      break;
    }
  }
  if (!ultima || ultima.payload?.cotacao) return null;
  if (!PROMESSA_DO_CALCULO.test(ultima.content || '')) return null;
  const quando = Date.parse(ultima.created_at);
  if (!Number.isFinite(quando) || agora - quando >= ESPERA_TETO_MS) return null;
  // relógio do aparelho atrasado em relação ao do servidor: a espera nunca passa de 10 min a partir de AGORA
  return { ate: Math.min(quando + ESPERA_TETO_MS, agora + ESPERA_TETO_MS), pendentes: 1 };
}

/**
 * 🔴 E10 — a MESMA regra do eco do Realtime: pelo ID DO ENVIO quando a mensagem tem um (a pergunta e a resposta do
 * turno, que a tela já desenhou com ids locais), pelo `id` quando não tem (a resposta da cotação). 📊 Comparar
 * `content` engolia a segunda pergunta igual.
 */
function jaEstaNaConversa(lista: Message[], nova: Message): boolean {
  const idDoEnvio = nova.payload?.client_request_id;
  return lista.some((m) =>
    idDoEnvio ? m.payload?.client_request_id === idDoEnvio && m.role === nova.role : m.id === nova.id,
  );
}

/**
 * SPEC-132-A (A4) — a transcrição do áudio chega DEPOIS da pergunta (um UPDATE em `payload.transcricao`). Só ela é
 * fundida: o resto da bolha (miniatura local, fichas) continua sendo o que a tela já tem. Sem mudança, a MESMA lista.
 */
function fundirTranscricao(lista: Message[], atual: Message): Message[] {
  const transcricao = atual?.payload?.transcricao;
  if (atual?.role !== 'user' || typeof transcricao !== 'string' || !transcricao.trim()) return lista;
  const idDoEnvio = atual.payload?.client_request_id;
  let mudou = false;
  const nova = lista.map((m) => {
    if (
      m.role === 'user' &&
      (m.id === atual.id || (idDoEnvio && m.payload?.client_request_id === idDoEnvio)) &&
      m.payload?.transcricao !== transcricao
    ) {
      mudou = true;
      return { ...m, payload: { ...(m.payload || {}), transcricao } };
    }
    return m;
  });
  return mudou ? nova : lista;
}

/** O que a consulta trouxe, juntado à conversa SEM duplicar; devolve também só o que é novo. */
function juntarChegadas(lista: Message[], chegadas: Message[]): { lista: Message[]; novas: Message[] } {
  let atual = lista;
  const novas: Message[] = [];
  for (const m of chegadas) {
    if (!m || typeof m.id !== 'string') continue;
    if (jaEstaNaConversa(atual, m)) {
      atual = fundirTranscricao(atual, m);
      continue;
    }
    novas.push(m);
    atual = [...atual, m];
  }
  return { lista: atual, novas };
}

export default function ChatPage() {
  const { userId, userAvatar, userName, isLoading: isLoadingUser } = useUserId();
  const [messages, setMessages] = useState<Message[]>([]);

  /**
   * SPEC-096 C.1 — o TURNO substitui o `isLoading`.
   *
   * 📊 §1.4: um booleano só sabia dizer "está carregando". Ele não sabia se o
   * trabalho tinha sido recusado pela política, se tinha sido parado pelo
   * corretor, se tinha falhado depois do primeiro pedaço de texto, nem se a
   * resposta tinha chegado inteira — e por não saber, a tela mostrava a mesma
   * bolinha para todos esses casos.
   */
  const [turno, setTurno] = useState<Turno>(TURNO_PARADO);

  // Sessão vem da URL (?session=) quando existe — é o que permite abrir uma
  // conversa do Histórico e sobreviver a refresh. Sem URL = conversa nova.
  const [sessionId, setSessionId] = useState(() => {
    if (typeof window !== 'undefined') {
      const fromUrl = new URLSearchParams(window.location.search).get('session');
      if (fromUrl && fromUrl.trim()) return fromUrl.trim();
    }
    return crypto.randomUUID();
  });
  const [conversationId, setConversationId] = useState<string | null>(null);

  // SPEC-095 BLOCO E — a pergunta que o relatório escreveu chega PRÉ-PREENCHIDA.
  //
  // 🔴 Inicializador SÍNCRONO, no molde do `sessionId` acima — nunca um efeito.
  // O `Composer` semeia o campo com `useState(initialText ?? '')`, e um
  // `useState` só lê o valor na MONTAGEM: um efeito chegaria depois de o campo
  // já ter nascido vazio, e a pergunta nunca apareceria.
  //
  // ⛔ E ele só PRÉ-PREENCHE. Nunca envia: 📊 um Pulso 360 custa 162 s de leitura
  // da InfoCap e uma versão nova da peça — um efeito que "só manda a pergunta"
  // gastaria isso a cada montagem, e a montagem acontece mais de uma vez.
  const [textoInicial, setTextoInicial] = useState(() => {
    if (typeof window !== 'undefined') {
      const daUrl = new URLSearchParams(window.location.search).get('pergunta');
      if (daUrl && daUrl.trim()) return daUrl;
    }
    return '';
  });

  // Mantém a URL espelhando a sessão atual: refresh volta na MESMA conversa e
  // "Nova conversa" gera URL nova (histórico do navegador não empilha).
  //
  // A URL perde o `?pergunta=` aqui — senão um refresh traria a pergunta de
  // volta. Mas o ESTADO não é zerado aqui.
  //
  // 🔴 📊 04/09/2026, red team, executando este componente de verdade: este
  // efeito roda no PRIMEIRO commit, e o composer ainda não existe nesse
  // momento — `if (isLoadingUser) return <Carregando/>` mais abaixo segura a
  // árvore até `/api/auth/me` responder. Zerar o estado aqui apagava a pergunta
  // ANTES de o `Composer` montar, e o campo nascia vazio: "Perguntar ao
  // AutoBrokers" abria um chat em branco. O guarda que só lia a FORMA da
  // declaração (inicializador síncrono + zeramento presentes) aprovou.
  //
  // O estado "já consumi" continua morando AQUI — e é zerado no ATO de enviar
  // (`handleSendMessage`), que é o único momento em que "consumir" tem sentido.
  // (SPEC-132-A: o composer agora é UM só e não remonta ao enviar a primeira
  // mensagem; zerar no envio continua certo — é o que um remount futuro exigiria.)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    let mudou = false;
    if (url.searchParams.get('session') !== sessionId) {
      url.searchParams.set('session', sessionId);
      mudou = true;
    }
    if (url.searchParams.has('pergunta')) {
      url.searchParams.delete('pergunta');
      mudou = true;
    }
    if (mudou) window.history.replaceState(null, '', url.toString());
  }, [sessionId]);

  // States do Agente
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [agentsLoaded, setAgentsLoaded] = useState(false);

  const [companyId, setCompanyId] = useState<string | null>(null);

  // Histórico paginado (D.1/D.3)
  const [temAnteriores, setTemAnteriores] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [carregandoAnteriores, setCarregandoAnteriores] = useState(false);

  const rolagemRef = useRef<HTMLDivElement>(null);
  const [longeDoFim, setLongeDoFim] = useState(false);

  // SPEC-132-A — arrastar arquivos sobre a conversa anexa (quem sobe é o composer)
  const [arrastando, setArrastando] = useState(false);
  const arrasteRef = useRef(0);
  const composerRef = useRef<ComposerHandle>(null);
  const mensagensRef = useRef<Message[]>([]);

  // SPEC-132 · A5 — a espera da resposta da cotação (ver `prometeuCalcular`). O estado desenha a linha; a ref é o
  // que o relógio lê (um tique não pode depender do render em que nasceu).
  const [esperaDaResposta, setEsperaDaResposta] = useState<EsperaDaResposta | null>(null);
  const esperaRef = useRef<EsperaDaResposta | null>(null);
  /** As respostas já contadas — a mesma pode chegar pela consulta e pelo Realtime, e conta UMA vez. */
  const respostasContadasRef = useRef<Set<string>>(new Set());

  // O que o turno em curso precisa lembrar entre um evento e outro.
  /**
   * 🔴 R3 — a trava do envio é uma REF, não um estado.
   *
   * 📊 Dois Enters rápidos produziam 1 pergunta gravada e 2 chamadas ao
   * backend, com identificadores diferentes: `disabled` é estado de React, e
   * estado de React chega no próximo render — o segundo Enter acontece antes
   * disso. Uma ref muda no MESMO instante em que é lida.
   */
  const enviandoRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const envioRef = useRef<EnvioDoTurno | null>(null);
  const turnoRef = useRef<Turno>(TURNO_PARADO);
  const textoDoAssistenteRef = useRef('');
  const pinturaAgendadaRef = useRef(false);

  useEffect(() => {
    turnoRef.current = turno;
  }, [turno]);

  useEffect(() => {
    mensagensRef.current = messages;
  }, [messages]);

  const mudarEspera = (proxima: EsperaDaResposta | null) => {
    esperaRef.current = proxima;
    setEsperaDaResposta(proxima);
  };

  /** Um disparo (ou ajuste) que começou: espera mais uma resposta, e o prazo recomeça. */
  const esperarMaisUmaResposta = () => {
    const atual = esperaRef.current;
    mudarEspera({ ate: Date.now() + ESPERA_TETO_MS, pendentes: (atual?.pendentes ?? 0) + 1 });
  };

  /**
   * Chegou mensagem nova do AutoBrokers (pela consulta ou pelo Realtime): cada uma é uma resposta esperada. A de um
   * HUMANO (atendimento) aparece, mas não encerra a espera — ela não é o resultado do cálculo.
   */
  const contarRespostas = (novas: Message[]) => {
    const atual = esperaRef.current;
    if (!atual) return;
    let chegaram = 0;
    for (const m of novas) {
      if (m.role !== 'assistant' || m.sender_user_id || respostasContadasRef.current.has(m.id)) continue;
      respostasContadasRef.current.add(m.id);
      chegaram += 1;
    }
    if (chegaram === 0) return;
    const restam = atual.pendentes - chegaram;
    mudarEspera(restam > 0 ? { ...atual, pendentes: restam } : null);
  };

  /**
   * 🔴 A consulta. Um relógio só, que se reagenda; pausa com a aba oculta (sem relógio nenhum — volta no
   * `visibilitychange`), não consulta enquanto um turno corre (o turno já desenha a conversa), e para no prazo.
   */
  const esperando = esperaDaResposta !== null;
  useEffect(() => {
    if (!esperando) return;
    let encerrado = false;
    let relogio: ReturnType<typeof setTimeout> | null = null;
    const sessaoDaEspera = sessionId;

    const consultar = async () => {
      relogio = null;
      const atual = esperaRef.current;
      if (encerrado || !atual) return;
      if (Date.now() >= atual.ate) {
        mudarEspera(null);
        return;
      }
      if (typeof document !== 'undefined' && document.hidden) return;
      if (!enviandoRef.current) {
        try {
          const resposta = await fetch(`/api/conversations?session_id=${sessaoDaEspera}`);
          if (!encerrado && resposta.ok) {
            const dados = await resposta.json();
            const chegadas: Message[] = Array.isArray(dados?.messages) ? dados.messages : [];
            if (!encerrado && chegadas.length > 0) {
              const { novas } = juntarChegadas(mensagensRef.current, chegadas);
              setMessages((prev) => juntarChegadas(prev, chegadas).lista);
              contarRespostas(novas);
            }
          }
        } catch {
          // a rede falhou nesta volta; a próxima tenta de novo
        }
      }
      if (!encerrado && esperaRef.current) agendarConsulta(ESPERA_INTERVALO_MS);
    };

    function agendarConsulta(ms: number) {
      if (relogio) clearTimeout(relogio);
      relogio = setTimeout(() => void consultar(), ms);
    }

    const aoVoltarParaAba = () => {
      if (!encerrado && typeof document !== 'undefined' && !document.hidden) agendarConsulta(0);
    };
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', aoVoltarParaAba);
    agendarConsulta(ESPERA_INTERVALO_MS);

    return () => {
      encerrado = true;
      if (relogio) clearTimeout(relogio);
      if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', aoVoltarParaAba);
    };
  }, [esperando, sessionId]);

  // 1. Busca Company e Permissões
  useEffect(() => {
    const fetchCompanyData = async () => {
      if (!userId) return;

      try {
        const response = await fetch('/api/user/company-data');
        if (!response.ok) return;

        const data = await response.json();
        setCompanyId(data.companyId);
      } catch (error) {
        console.error('[CHAT] Erro setup:', error);
      }
    };

    fetchCompanyData();
  }, [userId]);

  // 2. Busca Agentes
  useEffect(() => {
    const fetchAgents = async () => {
      if (!companyId) return;

      try {
        const response = await fetch('/api/agents');
        if (!response.ok) throw new Error('Falha ao buscar agentes');

        const data = await response.json();

        if (data.agents && data.agents.length > 0) {
          setAgents(data.agents);
          if (!selectedAgentId) {
            setSelectedAgentId(data.agents[0].id);
          }
        }

        setAgentsLoaded(true);
      } catch (error) {
        console.error('[CHAT] Erro agents:', error);
        setAgentsLoaded(true);
      }
    };

    fetchAgents();
  }, [companyId]);

  useEffect(() => {
    if (userId && agentsLoaded) {
      loadConversation();
    }
  }, [userId, sessionId, agentsLoaded]);

  /**
   * 🔴 SPEC-096 C.2 (E9) — o autoscroll INCONDICIONAL morreu.
   *
   * 📊 O efeito de `:147-149` rolava para o fim a cada mudança da lista de
   * mensagens, sem perguntar onde o corretor estava. Quem voltava para reler uma resposta anterior era arrancado
   * de lá no pedaço seguinte de texto — e ele brigaria de frente com o
   * "carregar anteriores", que insere mensagens ACIMA da posição atual.
   *
   * Agora a tela só acompanha quem já estava acompanhando (≤120 px do fim).
   */
  useEffect(() => {
    if (estaPertoDoFim()) {
      scrollToBottom();
    }
  }, [messages]);

  // 🔔 REALTIME: Receber mensagens instantaneamente (Human Handoff)
  useEffect(() => {
    if (!conversationId) return;

    const channel = supabase
      .channel(`messages:${conversationId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `conversation_id=eq.${conversationId}`,
        },
        async (payload) => {
          const newMessage = payload.new as Message;

          // 🔥 Mensagem humana (handoff): enriquece com os dados de quem enviou
          if (newMessage.sender_user_id && !newMessage.sender) {
            try {
              const res = await fetch(`/api/users/${newMessage.sender_user_id}`);
              if (res.ok) {
                const data = await res.json();
                if (data.user) {
                  newMessage.sender = {
                    first_name: data.user.first_name,
                    last_name: data.user.last_name,
                    avatar_url: data.user.avatar_url,
                  };
                }
              }
            } catch {
              // Silent fail - message will show without sender name
            }
          }

          // 🔴 E10 — o dedupe é pelo ID DO ENVIO, nunca pelo conteúdo.
          // 📊 Comparar `content` fazia a SEGUNDA pergunta igual sumir da
          // tela: quem repete "e o Pulso?" via a repetição ser engolida.
          // (SPEC-132 · A5: a mesma regra serve à consulta da espera — `jaEstaNaConversa`.)
          if (!jaEstaNaConversa(mensagensRef.current, newMessage)) contarRespostas([newMessage]);
          setMessages((prev) => (jaEstaNaConversa(prev, newMessage) ? prev : [...prev, newMessage]));
        },
      )
      .subscribe();

    // SPEC-132-A (A4) — a transcrição do áudio chega DEPOIS da pergunta: o backend a grava com um UPDATE em
    // `payload.transcricao` da mensagem do corretor (A3), e o INSERT acima não a vê. Sem isto, a bolha de voz só
    // mostrava o que o áudio disse depois de recarregar a página. Só a transcrição é fundida — o resto da bolha
    // (miniatura local, fichas) continua sendo o que a tela já tem.
    const canalDaTranscricao = supabase
      .channel(`messages-transcricao:${conversationId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'messages',
          filter: `conversation_id=eq.${conversationId}`,
        },
        (payload) => {
          const atual = payload.new as Message;
          setMessages((prev) => fundirTranscricao(prev, atual));
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      supabase.removeChannel(canalDaTranscricao);
    };
  }, [conversationId]);

  /**
   * 🔴 15/10 — "a caixa de texto sobe a cada pergunta". Quem rola é SÓ a lista: `el.scrollTo` mexe num elemento.
   * 📊 Antes era `fimDaLista.scrollIntoView()`, que rola TODOS os ancestrais roláveis — inclusive o `<main
   * overflow-hidden>` do casco (`TenantAppShell.tsx:21`), que o corretor não consegue rolar de volta. Com o
   * `sr-only` do "Copiado" (`MessageBubble.tsx`, `position:absolute`) escapando da lista, o `<main>` ganhava
   * rolagem a cada resposta, e o `scrollIntoView` (bloco `start`) o empurrava para cima: 📊 medido no Chromium
   * headless a 1280×800 (réplica com o tailwind.config.ts real), o topo da caixa foi 730 → 730 → 495 → 145 → 40 px
   * em cinco perguntas; com este conserto, 730 nas cinco. Guarda: scripts/a-caixa-fica-no-rodape.test.mjs.
   */
  const scrollToBottom = () => {
    const el = rolagemRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  };

  /** A tela só acompanha quem já estava no fim — e o fim tem 120 px de folga. */
  const estaPertoDoFim = () => {
    const el = rolagemRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight <= PERTO_DO_FIM;
  };

  const aoRolar = () => {
    setLongeDoFim(!estaPertoDoFim());
  };

  const voltarAoFim = () => {
    setLongeDoFim(false);
    scrollToBottom();
  };

  // === CARREGAMENTO DA CONVERSA (D.1) ===
  const loadConversation = useCallback(async () => {
    if (!userId) return;

    try {
      const response = await fetch(`/api/conversations?session_id=${sessionId}`);
      if (!response.ok) throw new Error('Falha ao carregar conversa');

      const data = await response.json();
      const conversation = data.conversation;

      if (conversation) {
        setConversationId(conversation.id);

        if (conversation.agent_id) {
          setSelectedAgentId(conversation.agent_id);
        }

        if (data.messages) {
          setMessages(data.messages);
          // SPEC-132 · A5 — a conversa reaberta no meio de um cálculo volta a esperar a resposta dele.
          const aoAbrir = Array.isArray(data.messages) ? esperaAoAbrir(data.messages, Date.now()) : null;
          if (aoAbrir && !esperaRef.current) mudarEspera(aoAbrir);
        }
        setTemAnteriores(Boolean(data.has_more));
        setCursor(data.cursor || null);
      } else {
        setConversationId(null);
        setMessages([]);
        setTemAnteriores(false);
        setCursor(null);
      }
    } catch (error) {
      console.error('[CHAT] Erro ao carregar conversa:', error);
    }
  }, [userId, sessionId]);

  /**
   * D.3 — "Carregar anteriores" pagina por CURSOR e **preserva a posição**.
   *
   * Sem guardar a altura antes e recolocá-la depois, inserir 60 mensagens no
   * topo joga o corretor para outro trecho da conversa — e ele perde o lugar
   * que estava lendo, que é justamente o motivo de ter subido.
   */
  const carregarAnteriores = async () => {
    if (!conversationId || !cursor || carregandoAnteriores) return;
    setCarregandoAnteriores(true);
    const el = rolagemRef.current;
    const alturaAntes = el ? el.scrollHeight : 0;

    try {
      const resposta = await fetch(
        `/api/messages?conversation_id=${conversationId}&before=${encodeURIComponent(cursor)}&limit=${PAGINA}`,
      );
      if (!resposta.ok) return;
      const dados = await resposta.json();
      const anteriores: Message[] = dados.messages || [];
      if (anteriores.length > 0) {
        setMessages((prev) => [...anteriores, ...prev]);
      }
      setTemAnteriores(Boolean(dados.has_more));
      setCursor(dados.cursor || null);

      if (el && typeof requestAnimationFrame === 'function') {
        requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight - alturaAntes;
        });
      }
    } catch (error) {
      console.error('[CHAT] Erro ao carregar anteriores:', error);
    } finally {
      setCarregandoAnteriores(false);
    }
  };

  /**
   * Só o ID. Quem escreve a conversa agora é o BFF do turno, e a tela precisa
   * do id para assinar o tempo real e para paginar o histórico.
   */
  const sincronizarIdDaConversa = async () => {
    try {
      const resposta = await fetch(`/api/conversations?session_id=${sessionId}`);
      if (!resposta.ok) return;
      const dados = await resposta.json();
      if (dados.conversation?.id) {
        setConversationId(dados.conversation.id);
        setTemAnteriores(Boolean(dados.has_more));
        setCursor(dados.cursor || null);
      }
    } catch (error) {
      console.error('[CHAT] Erro ao sincronizar a conversa:', error);
    }
  };

  /**
   * R11 — os pedaços de resposta são COALESCIDOS por quadro.
   *
   * 📊 §1.6: um `setMessages` por pedaço de texto significa um render por
   * pedaço. O acumulado mora numa ref (não provoca render) e a tela é pintada
   * no máximo uma vez por quadro.
   */
  const pintarResposta = (assistantMsgId: string) => {
    pinturaAgendadaRef.current = false;
    const conteudo = textoDoAssistenteRef.current;
    setMessages((prev) =>
      prev.map((m) => (m.id === assistantMsgId ? { ...m, content: conteudo } : m)),
    );
  };

  const agendarPintura = (assistantMsgId: string) => {
    if (pinturaAgendadaRef.current) return;
    pinturaAgendadaRef.current = true;
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(() => pintarResposta(assistantMsgId));
    } else {
      pintarResposta(assistantMsgId);
    }
  };

  /**
   * O turno, do envio ao fim. É esta função que o "Tentar de novo" reexecuta —
   * com o MESMO `client_request_id`, porque tentar de novo é a mesma pergunta
   * pedindo outra resposta, não uma pergunta nova (R3).
   */
  const executarTurno = async (envio: EnvioDoTurno, doComposer = false): Promise<'recusado' | void> => {
    const { message, anexos, esforco, clientRequestId, assistantMsgId } = envio;
    const attachments = anexosDoPedido(anexos);

    textoDoAssistenteRef.current = '';
    let turnoAtual: Turno = {
      ...TURNO_PARADO,
      status: 'submitting',
      clientRequestId,
      assistantMessageId: assistantMsgId,
    };
    setTurno(turnoAtual);

    const controlador = new AbortController();
    abortRef.current = controlador;
    let terminouLimpo = false;
    /** SPEC-132 · A5 — o turno passou pela ferramenta que começa o cálculo (quando o catálogo a nomear). */
    let viuOCalculo = false;

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatInput: message,
          sessionId: sessionId,
          client_request_id: clientRequestId,
          attachments,
          options: { esforco },
          assistantMessageId: assistantMsgId,
        }),
        signal: controlador.signal,
      });

      // 🔴 R5 — 404 aqui quer dizer "essa conversa não é sua".
      //
      // 📊 Abrir `?session=` de uma conversa alheia deixava o chat quebrado
      // PARA SEMPRE: o `session_id` é único no banco inteiro, o servidor não
      // achava a conversa (não é do corretor), tentava criar, batia no índice
      // — e todo envio seguinte repetia o mesmo erro, inclusive depois de
      // recarregar, porque a sessão continuava na URL. Aqui a tela sai do
      // beco: começa uma conversa nova e diz por quê.
      if (response.status === 404) {
        setMessages((prev) => prev.filter((m) => m.id !== assistantMsgId));
        setTurno(TURNO_PARADO);
        handleNewConversation();
        if (!doComposer) {
          toast.error('Essa conversa não é sua; começamos outra.');
          return;
        }
        toast.error('Essa conversa não é sua; começamos outra. Sua mensagem voltou para a caixa.');
        return 'recusado';
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        // 🔴 Conserto da SPEC-132-A (juiz P4): um 4xx do PRÓPRIO BFF (anexo de outra corretora, lista inválida,
        // sessão) chega ANTES de qualquer escrita — nada foi gravado. A pergunta sai da conversa e o texto e os
        // anexos VOLTAM para a caixa. (O 4xx repassado do backend traz `status` no corpo: a pergunta já foi gravada,
        // e aí vale o "Tentar de novo" de sempre.)
        if (doComposer && recusaAntesDoTurno(response.status, errorData)) {
          setMessages((prev) => prev.filter((m) => m.id !== assistantMsgId && m.id !== envio.userMsgId));
          setTurno(TURNO_PARADO);
          toast.error(`${textoDaRecusa(errorData)} Sua mensagem voltou para a caixa.`);
          return 'recusado';
        }
        throw new Error(
          errorData.message || errorData.error || `Falha ao falar com o AutoBrokers (${response.status})`,
        );
      }
      if (!response.body) throw new Error('O AutoBrokers não começou a responder.');

      for await (const evento of lerEventos(response.body)) {
        turnoAtual = reduzirTurno(turnoAtual, evento);
        setTurno(turnoAtual);
        if (evento.type === 'stage.started' && CHAVES_DO_CALCULO.has(String(evento.payload.key || ''))) {
          viuOCalculo = true;
        }

        if (evento.type === 'assistant.content.delta') {
          const pedaco = evento.payload.content ?? evento.payload.text ?? evento.payload.delta ?? '';
          textoDoAssistenteRef.current += typeof pedaco === 'string' ? pedaco : '';
          agendarPintura(assistantMsgId);
        } else if (evento.type === 'assistant.content.completed') {
          // 🔴 R6 — o campo do contrato é `content`. Lendo `text` vinha
          // `undefined`, e o evento que existe justamente para entregar a
          // resposta INTEIRA não fazia nada: um buraco no meio do caminho
          // (`transport: 'gap'`) ficava na tela para sempre. Este evento
          // SUBSTITUI o acumulado — é ele que conserta a lacuna.
          const inteiro = evento.payload.content ?? evento.payload.text;
          if (typeof inteiro === 'string' && inteiro.length > 0) {
            textoDoAssistenteRef.current = inteiro;
          }
          agendarPintura(assistantMsgId);
        } else if (evento.type === 'turn.completed') {
          terminouLimpo = true;
        }
      }

      // O conteúdo final e as peças produzidas ficam NA mensagem: é o que faz
      // o cartão da entrega sobreviver a um refresh (o servidor grava o mesmo).
      const conteudoFinal = textoDoAssistenteRef.current;
      const pecas = turnoAtual.artifacts;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: conteudoFinal,
                payload: {
                  ...(m.payload || {}),
                  client_request_id: clientRequestId,
                  turn: { ...(m.payload?.turn || {}), artifacts: pecas },
                },
              }
            : m,
        ),
      );

      // SPEC-132 · A5 — a cotação começou: a resposta dela vem DEPOIS deste turno, e a tela passa a esperá-la.
      if (turnoAtual.status !== 'failed' && turnoAtual.status !== 'stopped' && prometeuCalcular(conteudoFinal, viuOCalculo)) {
        esperarMaisUmaResposta();
      }

      // A conversa passou a nascer no SERVIDOR (A.2). Quando ela nasce, esta
      // tela ainda não sabe o id dela — e sem o id não há assinatura de tempo
      // real (o atendimento humano não chegaria sozinho) nem "carregar
      // anteriores". Então pergunta-se o id, e SÓ o id: reler as mensagens
      // aqui trocaria a resposta recém-pintada por outra cópia dela.
      if (!conversationId) {
        await sincronizarIdDaConversa();
      }

      if (!terminouLimpo && turnoAtual.status !== 'failed') {
        // A ligação caiu antes do fim. A geração NÃO foi cancelada — ela corre
        // no servidor e termina de gravar. Então não se reenvia a pergunta:
        // espera-se um instante e relê a conversa já gravada (R8).
        setTurno((t) => ({ ...t, transport: 'reconnecting' }));
        setTimeout(() => {
          loadConversation();
          setTurno((t) => ({ ...t, status: 'complete', transport: 'ok' }));
        }, 1500);
      }
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        // Parar foi um ato do corretor: o que já chegou fica, e isso não é erro.
        return;
      }
      console.error('[CHAT] Erro no turno:', error);
      setTurno({
        ...turnoAtual,
        status: 'failed',
        stage: null,
        aviso: {
          kind: 'error',
          code: 'transport',
          message_human:
            error instanceof Error ? error.message : 'Algo falhou no meio do caminho.',
        },
      });
    } finally {
      abortRef.current = null;
    }
  };

  const handleSendMessage = async (message: string, anexos: AnexoEnviado[] = [], opcoes?: Partial<OpcoesDoEnvio>) => {
    // 🔴 R3 — PRIMEIRA linha, antes de qualquer `await`: quem chegou primeiro
    // envia, quem chegou junto não envia nada. O §0 promete "Enter duas vezes:
    // UMA pergunta, UMA resposta", e é aqui que essa promessa é cumprida.
    if (enviandoRef.current) return false;
    enviandoRef.current = true;
    try {
      if (!userId) return false;

      // SPEC-095 BLOCO E — a pergunta pré-preenchida foi CONSUMIDA: quem envia,
      // envia. Zerar aqui (e só aqui) é o que impede uma remontagem do composer de
      // re-semear a pergunta por cima da conversa que começou.
      setTextoInicial('');

      if (!agentsLoaded) {
        // 🔴 juiz P4: `false` = recusado antes do turno — o composer devolve o texto e os anexos à caixa
        toast.error('Aguarde o carregamento dos agentes antes de enviar a mensagem. Sua mensagem voltou para a caixa.');
        return false;
      }

      if (!selectedAgentId || agents.length === 0) {
        toast.error('Nenhum agente ativo encontrado. Peça ao Admin para preparar o sandbox da empresa.');
        return false;
      }

      // 🔴 R3 — um identificador por ENVIO. É ele que faz a repetição continuar
      // sendo a MESMA pergunta, e o que dá ao Realtime como deduplicar sem
      // comparar texto.
      const clientRequestId = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();
      const convId = conversationId || '';

      const userMsgId = crypto.randomUUID();
      const tempUserMessage: Message = {
        id: userMsgId,
        conversation_id: convId,
        role: 'user',
        content: message,
        type: 'text',
        created_at: new Date().toISOString(),
        // SPEC-132-A — a bolha mostra as fichas JÁ, nesta sessão (a miniatura local e a URL do proxy). Depois de
        // recarregar, o que vale é o `payload.attachments` que o servidor gravou.
        payload: { client_request_id: clientRequestId, ...(anexos.length > 0 ? { attachments: anexos } : {}) },
      };

      const tempAssistantMessage: Message = {
        id: assistantMsgId,
        conversation_id: convId,
        role: 'assistant',
        content: '',
        type: 'text',
        created_at: new Date().toISOString(),
        payload: { client_request_id: clientRequestId },
      };

      // ⛔ A pergunta NÃO é mais gravada aqui. 📊 §1.3: o browser gravava sem
      // `await`, em paralelo com a resposta — e podia não gravar. Quem grava é o
      // servidor, antes de responder (A.2).
      setMessages((prev) => [...prev, tempUserMessage, tempAssistantMessage]);

      const envio: EnvioDoTurno = {
        message,
        anexos,
        esforco: esforcoDoPedido(opcoes?.esforco),
        clientRequestId,
        assistantMsgId,
        userMsgId,
      };
      envioRef.current = envio;

      return (await executarTurno(envio, true)) !== 'recusado';
    } finally {
      // A trava vale pelo TURNO inteiro — solta quando ele termina, falha ou
      // é parado, e também nos caminhos que nem chegam a enviar.
      enviandoRef.current = false;
    }
  };

  /**
   * "Tentar de novo" — mesma pergunta, nova tentativa. O identificador do envio
   * é REUSADO: gerar um novo transformaria o retry numa segunda pergunta, e o
   * corretor veria a dele duplicada na conversa (R3).
   */
  const tentarDeNovo = useCallback(() => {
    // Na sessão, o envio que a tela lembra (se ele é o da ÚLTIMA resposta); depois de recarregar, ou se a
    // última resposta é outra, o remontado da última pergunta gravada.
    const lembrado = envioRef.current;
    const lista = mensagensRef.current;
    const idDaUltima = lista.length > 0 ? lista[lista.length - 1].id : null;
    const envio =
      lembrado && (!idDaUltima || lembrado.assistantMsgId === idDaUltima)
        ? lembrado
        : envioDaUltimaResposta(lista) ?? lembrado;
    if (!envio) return;
    // A mesma trava do envio: dois cliques em "Tentar de novo" são um.
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    envioRef.current = envio;
    setMessages((prev) =>
      prev.map((m) => (m.id === envio.assistantMsgId ? { ...m, content: '' } : m)),
    );
    void executarTurno(envio).finally(() => {
      enviandoRef.current = false;
    });
  }, [sessionId]);

  /**
   * Parar. O pedido vai ao servidor (é lá que a geração corre) e a leitura
   * local é abortada. O parcial permanece na tela e no banco (R8/R9).
   */
  const pararTurno = useCallback(async () => {
    const idDoEnvio = turnoRef.current.clientRequestId;
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setTurno((t) => ({
      ...t,
      status: 'stopped',
      stage: null,
      aviso: {
        kind: 'notice',
        code: 'stopped_by_user',
        message_human: 'Resposta parada por você. O que já veio ficou salvo.',
      },
    }));
    if (!idDoEnvio) return;
    try {
      await fetch('/api/chat/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_request_id: idDoEnvio }),
      });
    } catch (error) {
      console.error('[CHAT] Erro ao parar:', error);
    }
  }, []);

  const handleNewConversation = useCallback(() => {
    const newSessionId = crypto.randomUUID();
    setSessionId(newSessionId);
    setConversationId(null);
    setMessages([]);
    setTurno(TURNO_PARADO);
    setTemAnteriores(false);
    setCursor(null);
    envioRef.current = null;
    mudarEspera(null);
  }, []);

  const handleSelectConversation = useCallback((newSessionId: string) => {
    setSessionId(newSessionId);
    setConversationId(null);
    setMessages([]);
    setTurno(TURNO_PARADO);
    envioRef.current = null;
    mudarEspera(null);
  }, []);

  // Reset determinístico de conversa via evento global (sidebar/topbar "Nova conversa")
  useEffect(() => {
    const handler = () => handleNewConversation();
    window.addEventListener('autobrokers:new-conversation', handler);
    return () => window.removeEventListener('autobrokers:new-conversation', handler);
  }, [handleNewConversation]);

  /**
   * SPEC-132-A — soltar arquivos sobre a conversa anexa. O contador existe porque o `dragleave` dispara a cada
   * filho que o ponteiro atravessa: sem ele, o aviso "Solte para anexar" piscaria.
   */
  const arrastaArquivos = (e: React.DragEvent) => Array.from(e.dataTransfer?.types || []).includes('Files');
  const aoEntrarArrastando = (e: React.DragEvent) => {
    if (!arrastaArquivos(e)) return;
    e.preventDefault();
    arrasteRef.current += 1;
    setArrastando(true);
  };
  const aoArrastarPorCima = (e: React.DragEvent) => {
    if (!arrastaArquivos(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };
  const aoSairArrastando = (e: React.DragEvent) => {
    if (!arrastaArquivos(e)) return;
    arrasteRef.current = Math.max(0, arrasteRef.current - 1);
    if (arrasteRef.current === 0) setArrastando(false);
  };
  const aoSoltar = (e: React.DragEvent) => {
    if (!arrastaArquivos(e)) return;
    e.preventDefault();
    arrasteRef.current = 0;
    setArrastando(false);
    const arquivos = Array.from(e.dataTransfer.files || []);
    if (arquivos.length > 0) composerRef.current?.adicionarArquivos(arquivos);
  };

  if (isLoadingUser) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Carregando…
      </div>
    );
  }

  const turnoCorrendo = turno.status === 'submitting' || turno.status === 'streaming';
  /**
   * 🔴 R4 — "Tentar de novo" é para o que PODE dar certo na segunda vez: um
   * erro de percurso, ou uma resposta que o corretor parou no meio. Um
   * `notice` ("um humano assumiu esta conversa", "nenhum agente ativo") e uma
   * recusa de política não mudam de resposta por insistência — oferecer o
   * botão ali seria empurrar o corretor contra a mesma parede.
   */
  const podeTentarDeNovo =
    turno.status === 'stopped' || (turno.status === 'failed' && turno.aviso?.kind === 'error');
  const ultima = messages.length > 0 ? messages[messages.length - 1] : null;

  /**
   * SPEC-132-A — "Tentar de novo" na bolha: só na ÚLTIMA resposta do AutoBrokers (não na de um humano), só quando
   * o turno não corre, e nunca junto do botão do aviso (um erro já oferece o dele).
   */
  const ultimaEhResposta = Boolean(ultima && ultima.role === 'assistant' && !ultima.sender_user_id && ultima.content);
  const tentarNaBolha =
    !turnoCorrendo &&
    ultimaEhResposta &&
    !(turno.aviso && podeTentarDeNovo) &&
    (envioRef.current?.assistantMsgId === ultima!.id || envioDaUltimaResposta(messages) !== null);
  const vazia = messages.length === 0;

  /**
   * 🔴 SPEC-132-A (D-132A-01/07) — UM composer, numa posição só da árvore: ele é sempre o 2º filho da coluna.
   * 📊 Antes ele era renderizado em DOIS lugares (conversa vazia e conversa ativa) e remontava na 1ª mensagem —
   * o texto, o foco e os anexos em curso se perdiam. Agora a conversa vazia só muda CLASSES: no notebook a coluna
   * centraliza saudação + caixa; depois da 1ª mensagem a caixa desce para o rodapé sem remontar. No celular ela
   * fica sempre embaixo.
   */
  return (
    <div
      className={`relative flex h-full min-h-0 flex-col bg-background ${vazia ? 'lg:justify-center lg:pb-[8vh]' : ''}`}
      onDragEnter={aoEntrarArrastando}
      onDragOver={aoArrastarPorCima}
      onDragLeave={aoSairArrastando}
      onDrop={aoSoltar}
    >
      <div className={`relative min-h-0 ${vazia ? 'flex flex-1 flex-col lg:flex-none' : 'flex-1'}`}>
        {vazia ? (
          /* CHAT-FIRST · a saudação; a caixa vem logo abaixo (notebook: as duas no meio) */
          <div className="flex flex-1 flex-col items-center justify-center px-4 pb-6 pt-10 lg:flex-none lg:pb-8 lg:pt-0">
            <ChatWelcome nome={userName} />
          </div>
        ) : (
          /* 🔴 `relative`: a lista é o bloco que contém o que nela é `absolute` (o `sr-only` do "Copiado" de cada
             resposta). Sem ele o pai era o `<div relative>` de fora — o `absolute` escapava da rolagem da lista
             e esticava o `<main>` do casco, e a caixa subia (15/10). */
          <div
            ref={rolagemRef}
            onScroll={aoRolar}
            className="relative h-full overflow-y-auto overscroll-contain px-4 pt-6"
          >
            <div className={`${COLUNA_DA_CONVERSA} pb-4`}>
              {temAnteriores && (
                <div className="mb-4 flex justify-center">
                  <button
                    type="button"
                    onClick={carregarAnteriores}
                    disabled={carregandoAnteriores}
                    className="rounded-full border border-border bg-surface px-4 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 disabled:opacity-60"
                  >
                    {carregandoAnteriores ? 'Carregando…' : 'Carregar anteriores'}
                  </button>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  userAvatar={userAvatar || undefined}
                  userName={userName || undefined}
                  emCurso={turnoCorrendo && msg.id === ultima?.id}
                  onRetry={tentarNaBolha && msg.id === ultima?.id ? tentarDeNovo : undefined}
                />
              ))}

              {/* UMA linha de atividade, abaixo da última mensagem. Ela nasce
                  do evento e some no primeiro pedaço de resposta (R6). */}
              {turno.stage && <LinhaDeAtividade label={turno.stage.label} />}

              {turnoCorrendo && !turno.stage && (!ultima || ultima.role !== 'assistant' || !ultima.content) && (
                <TypingIndicator />
              )}

              {/* SPEC-132 · A5 — a resposta da cotação vem depois do turno: uma linha discreta, que some quando
                  ela chega (ou no prazo). Enquanto outro turno corre, a atividade dele é a que aparece. */}
              {esperaDaResposta && !turnoCorrendo && (
                <p role="status" aria-live="polite" className="flex items-center gap-2 px-1 py-2 text-sm text-muted-foreground">
                  <span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-primary/70" />
                  Calculando a cotação… a resposta aparece aqui
                </p>
              )}

              {turno.transport === 'reconnecting' && (
                <div className="px-1 py-2 text-sm text-muted-foreground">Reconectando…</div>
              )}

              {turno.aviso && (
                <AvisoDoTurno
                  aviso={turno.aviso}
                  onRetry={podeTentarDeNovo ? tentarDeNovo : undefined}
                />
              )}

              <div className="h-4" />
            </div>
          </div>
        )}

        {/* A copy mora AQUI, na tela que a mostra: quem lê a conversa lê
            "Voltar ao fim" e não um nome de componente. */}
        {!vazia && longeDoFim && <VoltarAoFim onClick={voltarAoFim} rotulo="Voltar ao fim" />}
      </div>

      <div className="shrink-0 px-3 pb-[max(12px,env(safe-area-inset-bottom))] pt-2 sm:px-4">
        <Composer
          ref={composerRef}
          onSendMessage={handleSendMessage}
          onStop={pararTurno}
          turnStatus={turno.status}
          initialText={textoInicial}
          focoKey={sessionId}
        />
      </div>

      {arrastando && (
        <div className="pointer-events-none absolute inset-2 z-30 flex items-center justify-center rounded-3xl border-2 border-dashed border-primary/60 bg-background/80">
          <p className="text-base font-medium text-foreground">Solte para anexar</p>
        </div>
      )}
    </div>
  );
}
