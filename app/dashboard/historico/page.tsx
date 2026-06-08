'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { Button } from '@/components/ui/button';

interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export default function HistoricoPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    // Middleware já garante autenticação, não precisa verificar aqui
    try {
      const response = await fetch('/api/conversations?include_counts=true');
      if (!response.ok) throw new Error('Failed to load conversations');

      const data = await response.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Erro ao carregar conversas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenConversation = (_conversationId: string) => {
    router.push('/dashboard/chat');
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-background text-muted-foreground">
        Carregando histórico…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icons.historico} size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Histórico</h1>
            <p className="text-sm text-muted-foreground">Conversas recentes e registros do AutoBrokers.</p>
          </div>
        </div>

        <div className="mt-8">
          {conversations.length === 0 ? (
            <div className="rounded-xl border border-border bg-surface p-12 text-center">
              <p className="mb-4 text-sm text-muted-foreground">Você ainda não tem conversas.</p>
              <Button onClick={() => router.push('/dashboard/chat')}>
                <Icon icon={icons.novaConversa} size={16} className="mr-2" />
                Iniciar primeira conversa
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => handleOpenConversation(conv.id)}
                  className="group flex w-full items-start justify-between gap-4 rounded-xl border border-border bg-surface p-5 text-left transition-colors hover:border-primary/40 hover:bg-surface-2"
                >
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold text-foreground">
                      {conv.title || 'Conversa sem título'}
                    </h3>
                    <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                      {typeof conv.message_count === 'number' && (
                        <span className="rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
                          {conv.message_count} msgs
                        </span>
                      )}
                      <span>
                        {formatDistanceToNow(new Date(conv.updated_at), { addSuffix: true, locale: ptBR })}
                      </span>
                    </div>
                  </div>
                  <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-primary">
                    Abrir
                    <Icon icon={icons.avancar} size={14} />
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
