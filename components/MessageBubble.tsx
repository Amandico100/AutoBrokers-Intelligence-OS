'use client';

import { memo, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy, RotateCcw, User } from 'lucide-react';

import { Message } from '@/lib/types';
import type { RefDeArtifact } from '@/lib/chat/protocolo';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { CardDeRelatorio } from './chat/CardDeRelatorio';
import { FichaDeAnexo } from './chat/composer/FichaDeAnexo';
import { PlayerDeAudio } from './chat/composer/PlayerDeAudio';
import { anexosDaMensagem, ehAudio, ehImagem, navegadorDesenha, urlDoAnexo } from './chat/composer/anexos';
import { copiarTexto, textoLimpoDoMarkdown } from './chat/composer/copiar';

interface MessageBubbleProps {
  message: Message;
  userAvatar?: string;
  userName?: string;
  onSendMessage?: (message: string) => void;
  /**
   * SPEC-132-A — "Tentar de novo" só na ÚLTIMA resposta do AutoBrokers, e só quando o turno não está correndo.
   * Quem decide é a página (ela conhece o turno); a bolha mostra o botão exatamente quando recebe `onRetry`.
   */
  onRetry?: () => void;
  /** a resposta ainda está chegando: a linha de Copiar só aparece quando ela termina */
  emCurso?: boolean;
}

/**
 * SPEC-132-A §4 — a linha discreta no fim de cada resposta: Copiar (texto limpo, "Copiado" por 2 s) e, na última,
 * Tentar de novo. 32 px de alvo no notebook; no celular o `::before` estende o toque a 44 px.
 */
function AcoesDaResposta({ markdown, onRetry }: { markdown: string; onRetry?: () => void }) {
  const [copiado, setCopiado] = useState(false);
  const relogio = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (relogio.current) clearTimeout(relogio.current);
  }, []);

  const copiar = async () => {
    const ok = await copiarTexto(textoLimpoDoMarkdown(markdown));
    if (!ok) return;
    setCopiado(true);
    if (relogio.current) clearTimeout(relogio.current);
    relogio.current = setTimeout(() => setCopiado(false), 2000);
  };

  const botao =
    "relative inline-flex h-8 items-center justify-center gap-1.5 rounded-lg px-2 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring before:absolute before:-inset-1.5 before:content-[''] lg:before:hidden";

  return (
    // `relative`: o `sr-only` do "Copiado" (position:absolute) fica preso a ESTA linha. Sem pai posicionado ele
    // escapava da rolagem da conversa e esticava o <main> do casco — a caixa de texto subia a cada resposta (15/10).
    <div className="relative mt-1.5 flex items-center gap-1">
      <button
        type="button"
        onClick={copiar}
        aria-label={copiado ? 'Resposta copiada' : 'Copiar resposta'}
        title="Copiar"
        className={botao}
      >
        {copiado ? <Check className="h-4 w-4" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
        {copiado && <span className="text-xs font-medium">Copiado</span>}
      </button>
      {onRetry && (
        <button type="button" onClick={onRetry} aria-label="Tentar de novo" title="Tentar de novo" className={botao}>
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
      <span className="sr-only" aria-live="polite">
        {copiado ? 'Copiado' : ''}
      </span>
    </div>
  );
}

/** Tabelas roláveis (o celular não corta coluna) e links que abrem fora do chat. */
const COMPONENTES_DO_MARKDOWN = {
  table: ({ node: _n, ...props }: any) => (
    <div className="not-prose my-3 max-w-full overflow-x-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-left text-sm" {...props} />
    </div>
  ),
  th: ({ node: _n, ...props }: any) => (
    <th className="whitespace-nowrap border-b border-border bg-surface-2 px-3 py-2 font-semibold text-foreground" {...props} />
  ),
  td: ({ node: _n, ...props }: any) => <td className="border-b border-border-soft px-3 py-2 align-top text-foreground" {...props} />,
  a: ({ node: _n, ...props }: any) => <a target="_blank" rel="noopener noreferrer" {...props} />,
};

/**
 * SPEC-096 · C.4 / R11 — MEMOIZADO, porque cada token é um render.
 *
 * 🔴 📊 §1.6: sem `React.memo`, cada delta do stream re-renderizava o Markdown
 * de TODAS as bolhas da conversa. Numa conversa de 129 mensagens (o p95) isso
 * é o parser de Markdown rodando 129 vezes por token — a tela engasga
 * exatamente quando a resposta está chegando, que é o momento em que o
 * corretor está olhando.
 */
function MessageBubbleBase({ message, onRetry, emCurso = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isVoice = message.type === 'voice';

  // 🔥 FIX: Detecta mensagem humana por sender_user_id (novo padrão) OU regex (fallback legado)
  const hasSenderFromDb = !!message.sender_user_id && !!message.sender;
  const humanMatch = !hasSenderFromDb && message.content?.match(/^\[👤\s+(.+?)\]/);
  const isHumanMessage = hasSenderFromDb || !!humanMatch;

  // Nome e avatar do remetente humano
  const humanSenderName = hasSenderFromDb
    ? `${message.sender?.first_name || ''} ${message.sender?.last_name || ''}`.trim()
    : humanMatch
      ? humanMatch[1]
      : null;
  const humanSenderAvatar = hasSenderFromDb ? message.sender?.avatar_url : null;

  // Remove o prefixo do conteúdo para exibição (apenas legado)
  const displayContent = humanMatch ? message.content.replace(/^\[👤\s+.+?\]\n?/, '') : message.content;

  // SPEC-096 C.3 — as peças que ESTE turno produziu viajam no `payload.turn`,
  // então o cartão sobrevive ao reload: ele não depende de o stream ainda
  // estar aberto.
  const pecas: RefDeArtifact[] = Array.isArray(message.payload?.turn?.artifacts)
    ? (message.payload!.turn!.artifacts as RefDeArtifact[])
    : [];

  // SPEC-132-A — os anexos que o corretor mandou (`payload.attachments`: nome, mime, bytes, path)
  const anexos = isUser ? anexosDaMensagem(message.payload) : [];
  const fotos = anexos.filter((a) => ehImagem(a.mime) && navegadorDesenha(a.mime));
  const audios = anexos.filter((a) => ehAudio(a.mime));
  const documentos = anexos.filter((a) => !fotos.includes(a) && !audios.includes(a));

  // SPEC-132-A (A4) — o que o áudio disse. O backend grava a transcrição em `payload.transcricao` da PERGUNTA (A3,
  // `chat.py:_gravar_a_transcricao`), não dentro de cada anexo: sem ler daqui, a bolha de voz nunca a mostrava.
  // O texto vale para a mensagem inteira (vários áudios = uma transcrição só), então vai sob o ÚLTIMO áudio —
  // a não ser que algum anexo já traga a sua.
  const transcricaoDoTurno =
    isUser && typeof message.payload?.transcricao === 'string' && message.payload.transcricao.trim()
      ? message.payload.transcricao.trim()
      : undefined;
  const algumAudioTemTranscricao = audios.some((a) => a.transcricao);

  // SPEC-132-A (A4) — sem texto do corretor, o BFF grava a pergunta como "[Anexo] nome1, nome2" (para a conversa
  // nunca ter uma linha vazia). Isso é marcação, não fala: as fichas e a bolha de voz já dizem o que foi mandado.
  const soMarcaDeAnexo = isUser && anexos.length > 0 && /^\[Anexo\]\s/.test(displayContent || '');

  const temTexto =
    Boolean(displayContent) &&
    !soMarcaDeAnexo &&
    displayContent !== '[Imagem]' &&
    !(isVoice && message.audio_url) &&
    !displayContent.includes('Imagem enviada') &&
    !displayContent.includes('Áudio enviado') &&
    displayContent !== '[Mensagem de voz]';

  const mostrarAcoes = !isUser && temTexto && !emCurso;

  return (
    <div className={`mb-6 flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* 📷 Avatar para mensagens humanas (lado esquerdo) */}
      {isHumanMessage && (
        <div className="mr-2 mt-5 flex-shrink-0 self-start">
          <Avatar className="h-6 w-6 border border-border">
            <AvatarImage src={humanSenderAvatar || ''} />
            <AvatarFallback className="bg-surface-2 text-[10px] text-muted-foreground">
              <User className="h-3 w-3" />
            </AvatarFallback>
          </Avatar>
        </div>
      )}

      <div className={`flex min-w-0 flex-col ${isUser ? 'max-w-[85%] items-end sm:max-w-[75%]' : 'w-full max-w-full items-start'}`}>
        {/* Nome do remetente para mensagens humanas */}
        {isHumanMessage && humanSenderName && (
          <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
            {humanSenderName}
          </div>
        )}

        {/* Fotos anexadas (SPEC-132-A) */}
        {fotos.length > 0 && (
          <div className={`mb-1.5 flex flex-wrap gap-1.5 ${isUser ? 'justify-end' : ''}`}>
            {fotos.map((f, i) => {
              const url = urlDoAnexo(f);
              return url ? (
                <a key={`${f.path || f.nome}-${i}`} href={url} target="_blank" rel="noopener noreferrer" aria-label={`Abrir ${f.nome}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={url}
                    alt={f.nome}
                    className="h-28 w-28 rounded-2xl border border-border object-cover sm:h-36 sm:w-36"
                  />
                </a>
              ) : null;
            })}
          </div>
        )}

        {/* Áudios (o áudio do chat é um anexo — D-132A-06) */}
        {audios.map((a, i) => {
          const url = urlDoAnexo(a);
          return url ? (
            <div key={`${a.path || a.nome}-${i}`} className="mb-1.5 rounded-3xl bg-surface-2 px-3 py-2.5">
              <PlayerDeAudio
                src={url}
                duracaoConhecida={a.duracaoSegundos}
                transcricao={
                  a.transcricao ?? (!algumAudioTemTranscricao && i === audios.length - 1 ? transcricaoDoTurno : undefined)
                }
              />
            </div>
          ) : null;
        })}

        {/* Documentos */}
        {documentos.length > 0 && (
          <div className={`mb-1.5 flex flex-wrap gap-1.5 ${isUser ? 'justify-end' : ''}`}>
            {documentos.map((d, i) => (
              <FichaDeAnexo
                key={`${d.path || d.nome}-${i}`}
                nome={d.nome}
                mime={d.mime}
                bytes={d.bytes}
                href={d.path || d.url ? urlDoAnexo(d) : null}
              />
            ))}
          </div>
        )}

        {/* Imagem legada (`image_url`) */}
        {message.image_url && (
          <div className="overflow-hidden rounded-2xl border border-border bg-surface-2 p-1.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={message.image_url}
              alt="Anexo"
              className="block h-auto max-h-[400px] w-full max-w-[400px] cursor-zoom-in rounded-xl object-cover transition-opacity hover:opacity-90"
              onClick={() => window.open(message.image_url, '_blank')}
            />
          </div>
        )}

        {/* Áudio legado (`audio_url`) */}
        {isVoice && message.audio_url && (
          <div className="rounded-3xl bg-surface-2 px-3 py-2.5">
            <PlayerDeAudio src={message.audio_url} />
          </div>
        )}

        {/* Mensagem de texto (texto acompanha a imagem quando enviados juntos) */}
        {temTexto && (
          <div
            className={
              isUser
                ? 'rounded-3xl rounded-br-lg bg-surface-2 px-4 py-2.5 text-foreground'
                : isHumanMessage
                  ? 'rounded-3xl rounded-bl-lg border border-primary/40 bg-brand-soft px-4 py-2.5 text-foreground'
                  : 'w-full max-w-full px-1 py-1 text-foreground' // Agent: No background, just text
            }
          >
            <div
              className={`prose max-w-none break-words text-base leading-relaxed text-inherit dark:prose-invert
              prose-p:my-2
              prose-headings:text-inherit
              prose-strong:text-inherit
              prose-code:rounded prose-code:bg-surface-2 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-inherit prose-code:before:content-none prose-code:after:content-none
              prose-pre:max-w-full prose-pre:overflow-x-auto prose-pre:border prose-pre:border-border prose-pre:bg-surface-2 prose-pre:text-foreground
              prose-ul:my-2 prose-li:my-0.5
              prose-a:text-primary`}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTES_DO_MARKDOWN}>
                {displayContent}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {!isUser && pecas.map((peca) => <CardDeRelatorio key={peca.artifact_id} artifact={peca} />)}

        {mostrarAcoes && <AcoesDaResposta markdown={displayContent} onRetry={onRetry} />}
      </div>
    </div>
  );
}

/**
 * A comparação é explícita: id, conteúdo (o que muda a cada token) e as peças
 * do turno. Sem ela o `memo` compararia `onSendMessage`, que nasce novo a cada
 * render do pai, e não memoizaria nada — um guarda que não pode falhar
 * (CLAUDE.md §9.3), mas em forma de otimização.
 *
 * SPEC-132-A: entram os anexos, o `emCurso` e o `onRetry` — este só existe na ÚLTIMA resposta, então só ela
 * re-renderiza quando a função do pai muda (e é ela que está mudando de qualquer jeito).
 */
export const MessageBubble = memo(MessageBubbleBase, (antes, depois) => {
  return (
    antes.message.id === depois.message.id &&
    antes.message.content === depois.message.content &&
    antes.message.image_url === depois.message.image_url &&
    antes.message.audio_url === depois.message.audio_url &&
    antes.message.payload?.turn?.artifacts === depois.message.payload?.turn?.artifacts &&
    antes.message.payload?.attachments === depois.message.payload?.attachments &&
    antes.message.payload?.transcricao === depois.message.payload?.transcricao &&
    antes.emCurso === depois.emCurso &&
    antes.onRetry === depois.onRetry &&
    antes.userAvatar === depois.userAvatar &&
    antes.userName === depois.userName
  );
});
