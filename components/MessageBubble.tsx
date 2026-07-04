import { Message } from '@/lib/types';
import VoiceMessage from './VoiceMessage';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
  userAvatar?: string;
  userName?: string;
  onSendMessage?: (message: string) => void;
}

export function MessageBubble({
  message,
  userAvatar,
  userName,
}: MessageBubbleProps) {
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
  const rawContent = humanMatch ? message.content.replace(/^\[👤\s+.+?\]\n?/, '') : message.content;

  let displayContent = rawContent;

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      {/* 📷 Avatar para mensagens humanas (lado esquerdo) */}
      {isHumanMessage && (
        <div className="flex-shrink-0 mr-2 self-start mt-5">
          <Avatar className="h-6 w-6 border border-zinc-600">
            <AvatarImage src={humanSenderAvatar || ''} />
            <AvatarFallback className="bg-zinc-700 text-zinc-300 text-[10px]">
              <User className="h-3 w-3" />
            </AvatarFallback>
          </Avatar>
        </div>
      )}

      <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Nome do remetente para mensagens humanas */}
        {isHumanMessage && humanSenderName && (
          <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
            {humanSenderName}
          </div>
        )}

        {/* Imagem (Se houver) */}
        {message.image_url && (
          <div
            className={`${isHumanMessage ? 'bg-[#18181b] border border-[#27272a]' : 'bg-black'} rounded-2xl p-2 overflow-hidden`}
          >
            <img
              src={message.image_url}
              alt="Anexo"
              className="block w-full h-auto max-h-[400px] max-w-[400px] object-cover cursor-zoom-in hover:opacity-90 transition-opacity rounded-xl"
              onClick={() => window.open(message.image_url, '_blank')}
            />
          </div>
        )}

        {/* Áudio (Se houver) */}
        {isVoice && message.audio_url && (
          <div
            className={`${isHumanMessage ? 'bg-[#18181b] border border-[#27272a]' : 'bg-black'} rounded-2xl px-4 py-3`}
          >
            <VoiceMessage audioUrl={message.audio_url} transcription={undefined} />
          </div>
        )}

        {/* Mensagem de texto (apenas se não for placeholder de mídia) */}
        {displayContent &&
          !message.image_url &&
          !(isVoice && message.audio_url) &&
          !displayContent.includes('Imagem enviada') &&
          !displayContent.includes('Áudio enviado') &&
          displayContent !== '[Mensagem de voz]' && (
            <div
              className={`${isUser
                ? 'rounded-2xl rounded-br-sm border border-primary/40 bg-brand-soft px-4 py-3 text-foreground shadow-sm'
                : isHumanMessage
                  ? 'rounded-2xl rounded-bl-sm border border-primary/50 bg-brand-soft px-4 py-3 text-foreground shadow-sm'
                  : 'text-foreground px-1 py-1' // Agent: No background, just text
                }`}
            >
              <div
                className={`text-base leading-relaxed prose prose-invert max-w-none
              prose-p:my-2 
              prose-headings:text-inherit
              prose-strong:text-inherit
              prose-code:bg-black/20 prose-code:text-inherit prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
              prose-pre:bg-black/20 prose-pre:border prose-pre:border-white/10
              prose-ul:my-2 prose-li:my-0.5
              text-inherit
            `}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown>
              </div>
            </div>
          )}
      </div>
    </div>
  );
}
