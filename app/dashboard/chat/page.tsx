'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { ChatWelcome } from '@/components/chat/ChatWelcome';
import { ChatShortcutCards } from '@/components/chat/ChatShortcutCards';
import { LinhaDeAtividade } from '@/components/chat/LinhaDeAtividade';
import { AvisoDoTurno } from '@/components/chat/AvisoDoTurno';
import { VoltarAoFim } from '@/components/chat/VoltarAoFim';
import InputArea from '@/components/InputArea';
import { MessageBubble } from '@/components/MessageBubble';
import { TypingIndicator } from '@/components/TypingIndicator';
import { lerEventos, reduzirTurno } from '@/lib/chat/protocolo';
import type { Turno } from '@/lib/chat/protocolo';
import { sendTextToN8N, sendVoiceToN8N } from '@/lib/n8nClient';
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

interface EnvioDoTurno {
  message: string;
  imageUrl?: string;
  fileUrl?: string;
  fileName?: string;
  clientRequestId: string;
  assistantMsgId: string;
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
  // O `InputArea` semeia o campo com `useState(initialText ?? '')`, e um
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
  // ANTES de o `InputArea` montar, e o campo nascia vazio: "Perguntar ao
  // AutoBrokers" abria um chat em branco. O guarda que só lia a FORMA da
  // declaração (inicializador síncrono + zeramento presentes) aprovou.
  //
  // O estado "já consumi" continua morando AQUI, acima da fronteira de
  // remontagem (o composer é renderizado em duas posições da árvore e remonta
  // ao enviar a primeira mensagem) — mas ele é zerado no ATO de enviar
  // (`handleSendMessage`), que é o único momento em que "consumir" tem sentido.
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

  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [isWebSearchAllowed, setIsWebSearchAllowed] = useState(false);
  const [companyId, setCompanyId] = useState<string | null>(null);

  // Histórico paginado (D.1/D.3)
  const [temAnteriores, setTemAnteriores] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [carregandoAnteriores, setCarregandoAnteriores] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const rolagemRef = useRef<HTMLDivElement>(null);
  const [longeDoFim, setLongeDoFim] = useState(false);

  // O que o turno em curso precisa lembrar entre um evento e outro.
  const abortRef = useRef<AbortController | null>(null);
  const envioRef = useRef<EnvioDoTurno | null>(null);
  const turnoRef = useRef<Turno>(TURNO_PARADO);
  const textoDoAssistenteRef = useRef('');
  const pinturaAgendadaRef = useRef(false);

  useEffect(() => {
    turnoRef.current = turno;
  }, [turno]);

  // 1. Busca Company e Permissões
  useEffect(() => {
    const fetchCompanyData = async () => {
      if (!userId) return;

      try {
        const response = await fetch('/api/user/company-data');
        if (!response.ok) return;

        const data = await response.json();
        setCompanyId(data.companyId);
        setIsWebSearchAllowed(data.allowWebSearch || false);
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
          setMessages((prev) => {
            const idDoEnvio = newMessage.payload?.client_request_id;
            const exists = prev.some((m) =>
              idDoEnvio
                ? m.payload?.client_request_id === idDoEnvio && m.role === newMessage.role
                : m.id === newMessage.id,
            );
            if (exists) return prev;
            return [...prev, newMessage];
          });
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [conversationId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

  const saveMessage = async (
    convId: string,
    role: 'user' | 'assistant',
    content: string,
    type: 'text' | 'voice' = 'text',
    audioUrl?: string,
    imageUrl?: string,
  ) => {
    const response = await fetch('/api/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: convId,
        role,
        content,
        type,
        audio_url: audioUrl,
        image_url: imageUrl,
      }),
    });

    if (!response.ok) throw new Error('Falha ao salvar mensagem');

    const data = await response.json();
    return data.message;
  };

  const ensureConversation = async () => {
    if (conversationId) return conversationId;
    if (!userId || !companyId) throw new Error('Init failed');

    const response = await fetch('/api/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        agent_id: selectedAgentId,
        title: 'Nova Conversa',
      }),
    });

    if (!response.ok) throw new Error('Falha ao criar conversa');

    const data = await response.json();
    setConversationId(data.conversation.id);
    return data.conversation.id;
  };

  // === 🚀 LÓGICA DE TROCA DE AGENTE ===
  const handleAgentChange = (newAgentId: string) => {
    if (newAgentId === selectedAgentId) return;

    const agentName = agents.find((a) => a.id === newAgentId)?.name;
    setSelectedAgentId(newAgentId);
    handleNewConversation();
    toast.success(`Chat iniciado com ${agentName}`);
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
  const executarTurno = async (envio: EnvioDoTurno) => {
    const { message, imageUrl, fileUrl, fileName, clientRequestId, assistantMsgId } = envio;

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

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatInput: message,
          sessionId: sessionId,
          client_request_id: clientRequestId,
          imageUrl: imageUrl,
          fileUrl: fileUrl,
          fileName: fileName,
          options: { web_search: webSearchEnabled },
          assistantMessageId: assistantMsgId,
        }),
        signal: controlador.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || errorData.error || `Falha ao falar com o AutoBrokers (${response.status})`,
        );
      }
      if (!response.body) throw new Error('O AutoBrokers não começou a responder.');

      for await (const evento of lerEventos(response.body)) {
        turnoAtual = reduzirTurno(turnoAtual, evento);
        setTurno(turnoAtual);

        if (evento.type === 'assistant.content.delta') {
          const pedaco = evento.payload.text ?? evento.payload.delta ?? '';
          textoDoAssistenteRef.current += typeof pedaco === 'string' ? pedaco : '';
          agendarPintura(assistantMsgId);
        } else if (evento.type === 'assistant.content.completed') {
          const inteiro = evento.payload.text;
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

  const handleSendMessage = async (message: string, imageUrl?: string, fileUrl?: string, fileName?: string) => {
    if (!userId) return;

    // SPEC-095 BLOCO E — a pergunta pré-preenchida foi CONSUMIDA: quem envia,
    // envia. Zerar aqui (e só aqui) é o que impede a remontagem do composer de
    // re-semear a pergunta por cima da conversa que começou.
    setTextoInicial('');

    if (!agentsLoaded) {
      toast.error('Aguarde o carregamento dos agentes antes de enviar a mensagem.');
      return;
    }

    if (!selectedAgentId || agents.length === 0) {
      toast.error('Nenhum agente ativo encontrado. Peça ao Admin para preparar o sandbox da empresa.');
      return;
    }

    // 🔴 R3 — um identificador por ENVIO. É ele que faz a repetição continuar
    // sendo a MESMA pergunta, e o que dá ao Realtime como deduplicar sem
    // comparar texto.
    const clientRequestId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();
    const convId = conversationId || '';

    const tempUserMessage: Message = {
      id: crypto.randomUUID(),
      conversation_id: convId,
      role: 'user',
      content: message,
      type: 'text',
      image_url: imageUrl,
      created_at: new Date().toISOString(),
      payload: { client_request_id: clientRequestId },
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
      imageUrl,
      fileUrl,
      fileName,
      clientRequestId,
      assistantMsgId,
    };
    envioRef.current = envio;

    await executarTurno(envio);
  };

  /**
   * "Tentar de novo" — mesma pergunta, nova tentativa. O identificador do envio
   * é REUSADO: gerar um novo transformaria o retry numa segunda pergunta, e o
   * corretor veria a dele duplicada na conversa (R3).
   */
  const tentarDeNovo = useCallback(() => {
    const envio = envioRef.current;
    if (!envio) return;
    setMessages((prev) =>
      prev.map((m) => (m.id === envio.assistantMsgId ? { ...m, content: '' } : m)),
    );
    executarTurno(envio);
  }, [sessionId, webSearchEnabled]);

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

  const handleSendVoice = async (audioBase64: string, audioBlob: Blob) => {
    if (!userId) return;
    setTurno((t) => ({ ...t, status: 'submitting' }));

    try {
      let audioUrl: string | null = null;
      try {
        const { uploadVoiceMessage } = await import('@/lib/storageSetup');
        audioUrl = await uploadVoiceMessage(audioBlob);
      } catch (e) {
        console.warn('Upload audio fail', e);
      }

      const convId = await ensureConversation();

      const tempUserMessage: Message = {
        id: crypto.randomUUID(),
        conversation_id: convId,
        role: 'user',
        content: '[Mensagem de voz]',
        type: 'voice',
        audio_url: audioUrl || undefined,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMessage]);

      // A voz continua no contrato de hoje (R12): ela grava a própria pergunta.
      await saveMessage(convId, 'user', '[Mensagem de voz]', 'voice', audioUrl || undefined);

      const response = await sendVoiceToN8N(
        audioBase64,
        sessionId,
        selectedAgentId,
        companyId!,
        userId,
      );

      if (response && response.output) {
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          conversation_id: convId,
          role: 'assistant',
          content: response.output,
          type: 'text',
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => {
          const exists = prev.some((m) => m.role === 'assistant' && m.content === response.output);
          if (exists) return prev;
          return [...prev, assistantMessage];
        });
      }
    } catch (error) {
      console.error('[AUDIO] Erro:', error);
    } finally {
      setTurno((t) => ({ ...t, status: 'complete' }));
    }
  };

  const handleNewConversation = useCallback(() => {
    const newSessionId = crypto.randomUUID();
    setSessionId(newSessionId);
    setConversationId(null);
    setMessages([]);
    setTurno(TURNO_PARADO);
    setTemAnteriores(false);
    setCursor(null);
  }, []);

  const handleSelectConversation = useCallback((newSessionId: string) => {
    setSessionId(newSessionId);
    setConversationId(null);
    setMessages([]);
    setTurno(TURNO_PARADO);
  }, []);

  // Reset determinístico de conversa via evento global (sidebar/topbar "Nova conversa")
  useEffect(() => {
    const handler = () => handleNewConversation();
    window.addEventListener('autobrokers:new-conversation', handler);
    return () => window.removeEventListener('autobrokers:new-conversation', handler);
  }, [handleNewConversation]);

  if (isLoadingUser) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        Carregando...
      </div>
    );
  }

  const turnoCorrendo = turno.status === 'submitting' || turno.status === 'streaming';
  const podeTentarDeNovo = turno.status === 'failed' || turno.status === 'stopped';
  const ultima = messages.length > 0 ? messages[messages.length - 1] : null;

  const composer = (
    <InputArea
      onSendMessage={handleSendMessage}
      onSendVoice={handleSendVoice}
      disabled={turnoCorrendo}
      showWebSearch={isWebSearchAllowed}
      allowWebSearch={webSearchEnabled}
      onToggleWebSearch={() => setWebSearchEnabled(!webSearchEnabled)}
      companyId={companyId || undefined}
      agents={agents}
      selectedAgentId={selectedAgentId}
      onAgentChange={handleAgentChange}
      showAgentSelector={false}
      initialText={textoInicial}
      turnStatus={turno.status}
      onStop={pararTurno}
    />
  );

  return (
    <div className="flex h-full flex-col bg-background">
      {messages.length === 0 ? (
        /* CHAT-FIRST · estado inicial (sem mensagens) */
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col items-center justify-center px-4 py-10">
            <ChatWelcome />
            <div className="mt-8 w-full">{composer}</div>
            <ChatShortcutCards />
          </div>
        </div>
      ) : (
        /* Conversa ativa */
        <>
          <div className="relative flex-1 overflow-hidden">
            <div
              ref={rolagemRef}
              onScroll={aoRolar}
              className="h-full overflow-y-auto px-4 py-6 scroll-smooth"
            >
              <div className="mx-auto w-full max-w-3xl pb-4">
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
                    onSendMessage={(text) => handleSendMessage(text)}
                  />
                ))}

                {/* UMA linha de atividade, abaixo da última mensagem. Ela nasce
                    do evento e some no primeiro pedaço de resposta (R6). */}
                {turno.stage && <LinhaDeAtividade label={turno.stage.label} />}

                {turnoCorrendo && !turno.stage && (!ultima || ultima.role !== 'assistant' || !ultima.content) && (
                  <TypingIndicator />
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

                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>

            {/* A copy mora AQUI, na tela que a mostra: quem lê a conversa lê
                "Voltar ao fim" e não um nome de componente. */}
            {longeDoFim && <VoltarAoFim onClick={voltarAoFim} rotulo="Voltar ao fim" />}
          </div>

          <div className="shrink-0 bg-gradient-to-t from-background via-background to-transparent pt-3">
            {composer}
          </div>
        </>
      )}
    </div>
  );
}
