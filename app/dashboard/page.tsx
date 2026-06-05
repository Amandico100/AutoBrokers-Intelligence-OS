'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  Bot,
  Building2,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  History,
  MessageSquare,
  PlugZap,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Wallet,
} from 'lucide-react';
import { UnifiedSidebar } from '@/components/UnifiedSidebar';
import { useUserId } from '@/hooks/useUserId';

interface UserProfile {
  name: string;
  email: string;
  companyName: string;
}

interface AgentSummary {
  id: string;
  name: string;
}

interface ConversationSummary {
  id: string;
  title: string | null;
  session_id: string;
  updated_at: string;
  agents?: { name: string } | null;
}

interface BillingSummary {
  has_subscription?: boolean;
  plan?: { name?: string; display_credits?: number } | null;
  balance_brl?: number;
  credits_display?: {
    remaining?: number;
    total?: number;
    percentage?: number;
  };
}

interface HomeData {
  profile: UserProfile;
  agents: AgentSummary[];
  conversations: ConversationSummary[];
  billing: BillingSummary | null;
}

const emptyProfile: UserProfile = {
  name: '',
  email: '',
  companyName: 'Corretora',
};

function formatCurrency(value: number | undefined) {
  return Number(value || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  });
}

function formatShortDate(dateString: string) {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return 'Atualizada recentemente';

  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function DashboardPage() {
  const router = useRouter();
  const { userId } = useUserId();
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [homeData, setHomeData] = useState<HomeData>({
    profile: emptyProfile,
    agents: [],
    conversations: [],
    billing: null,
  });

  useEffect(() => {
    if (!userId) return;

    let isMounted = true;

    async function loadHomeData() {
      setIsLoading(true);

      try {
        const [profileRes, agentsRes, conversationsRes, billingRes] = await Promise.allSettled([
          fetch('/api/user/profile'),
          fetch('/api/agents'),
          fetch('/api/conversations?limit=5'),
          fetch('/api/billing/subscription'),
        ]);

        const nextData: HomeData = {
          profile: emptyProfile,
          agents: [],
          conversations: [],
          billing: null,
        };

        if (profileRes.status === 'fulfilled' && profileRes.value.ok) {
          const profile = await profileRes.value.json();
          nextData.profile = {
            name: profile.name || '',
            email: profile.email || '',
            companyName: profile.companyName || 'Corretora',
          };
        }

        if (agentsRes.status === 'fulfilled' && agentsRes.value.ok) {
          const data = await agentsRes.value.json();
          nextData.agents = data.agents || [];
        }

        if (conversationsRes.status === 'fulfilled' && conversationsRes.value.ok) {
          const data = await conversationsRes.value.json();
          nextData.conversations = data.conversations || [];
        }

        if (billingRes.status === 'fulfilled' && billingRes.value.ok) {
          nextData.billing = await billingRes.value.json();
        }

        if (isMounted) setHomeData(nextData);
      } catch (error) {
        console.error('[DASHBOARD HOME] Error loading home data:', error);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadHomeData();

    return () => {
      isMounted = false;
    };
  }, [userId]);

  const primaryAgentName = homeData.agents[0]?.name || 'AutoBrokers';
  const hasActiveAgent = homeData.agents.length > 0;
  const balanceBrl = Number(homeData.billing?.balance_brl || 0);
  const hasCredits = balanceBrl > 0;
  const companyName = homeData.profile.companyName || 'Corretora';
  const userDisplayName = homeData.profile.name || 'Usuário';

  const setupStatus = useMemo(() => {
    if (!hasActiveAgent) return 'Agente em configuração';
    if (!hasCredits) return 'Créditos pendentes';
    return 'Pronto para conversa';
  }, [hasActiveAgent, hasCredits]);

  const openChat = (message?: string) => {
    const cleanMessage = message?.trim();

    if (cleanMessage && typeof window !== 'undefined') {
      window.sessionStorage.setItem('autobrokers.homePrompt', cleanMessage);
    }

    router.push('/dashboard/chat');
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    openChat(prompt);
  };

  const quickActions = [
    {
      label: 'Abrir chat do AutoBrokers',
      description: 'Continuar no modo conversa completo',
      icon: MessageSquare,
      onClick: () => openChat(),
      enabled: true,
    },
    {
      label: 'Ver histórico',
      description: 'Revisar conversas recentes',
      icon: History,
      href: '/dashboard/historico',
      enabled: true,
    },
    {
      label: 'Configurações',
      description: 'Perfil e segurança da conta',
      icon: Settings,
      href: '/dashboard/configuracoes',
      enabled: true,
    },
    {
      label: 'Preparar mensagem para cliente',
      description: 'Assistência operacional em breve',
      icon: FileText,
      enabled: false,
    },
    {
      label: 'Consultar cliente/apólice',
      description: 'Depende das integrações da corretora',
      icon: ShieldCheck,
      enabled: false,
    },
    {
      label: 'Base de conhecimento',
      description: 'Curadoria e documentos entram na próxima fase',
      icon: Database,
      enabled: false,
    },
  ];

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {userId && <UnifiedSidebar userId={userId} />}

      <main className="flex-1 lg:ml-64">
        <div className="min-h-screen px-5 py-5 sm:px-6 lg:px-8">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
            <header className="flex flex-col gap-3 border-b border-border/70 pb-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-400">
                  {companyName}
                </p>
                <h1 className="mt-1 text-2xl font-semibold text-foreground sm:text-3xl">
                  Home da corretora
                </h1>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-emerald-300">
                  <CheckCircle2 className="h-4 w-4" />
                  AutoBrokers {hasActiveAgent ? 'ativo' : 'em configuração'}
                </span>
                <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-muted-foreground">
                  {userDisplayName}
                </span>
              </div>
            </header>

            <section className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
              <div className="rounded-2xl border border-border bg-card/70 p-5 shadow-sm sm:p-7">
                <div className="flex flex-col gap-6">
                  <div className="flex items-start gap-4">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-blue-500/25 bg-blue-500/10">
                      <Bot className="h-7 w-7 text-blue-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm text-blue-300">Seu copiloto operacional para seguros</p>
                      <h2 className="mt-1 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                        AutoBrokers
                      </h2>
                      <p className="mt-3 max-w-2xl text-base text-muted-foreground">
                        Como posso ajudar sua corretora hoje?
                      </p>
                    </div>
                  </div>

                  <form onSubmit={handleSubmit} className="rounded-2xl border border-border bg-background/80 p-4">
                    <label htmlFor="autobrokers-home-prompt" className="sr-only">
                      Mensagem para o AutoBrokers
                    </label>
                    <textarea
                      id="autobrokers-home-prompt"
                      value={prompt}
                      onChange={(event) => setPrompt(event.target.value)}
                      placeholder="Peça para preparar uma resposta, organizar uma pendência ou revisar o próximo passo..."
                      className="min-h-28 w-full resize-none bg-transparent text-base text-foreground outline-none placeholder:text-muted-foreground"
                    />
                    <div className="mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="text-xs text-muted-foreground">
                        O envio abre o chat completo e preserva a lógica atual de streaming.
                      </div>
                      <button
                        type="submit"
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-500"
                      >
                        Enviar para o AutoBrokers
                        <Send className="h-4 w-4" />
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              <aside className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
                <StatusCard
                  icon={Bot}
                  label="Agente principal"
                  value={primaryAgentName}
                  detail={hasActiveAgent ? 'Disponível para chat' : 'Prepare o sandbox no Admin'}
                  tone={hasActiveAgent ? 'good' : 'warn'}
                />
                <StatusCard
                  icon={Wallet}
                  label="Créditos IA"
                  value={hasCredits ? formatCurrency(balanceBrl) : 'Em configuração'}
                  detail={
                    homeData.billing?.plan?.name
                      ? `Plano ${homeData.billing.plan.name}`
                      : 'Sem plano ativo encontrado'
                  }
                  tone={hasCredits ? 'good' : 'warn'}
                />
                <StatusCard
                  icon={Building2}
                  label="Setup da corretora"
                  value={setupStatus}
                  detail={companyName}
                  tone={hasActiveAgent && hasCredits ? 'good' : 'neutral'}
                />
              </aside>
            </section>

            <section className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.05fr)]">
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">Atalhos rápidos</h3>
                    <p className="text-sm text-muted-foreground">
                      Ações seguras para este primeiro ciclo do produto.
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {quickActions.map((action) => {
                    const Icon = action.icon;
                    const content = (
                      <>
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border bg-background">
                          <Icon className="h-5 w-5 text-blue-400" />
                        </div>
                        <div className="min-w-0 flex-1 text-left">
                          <p className="text-sm font-semibold text-foreground">{action.label}</p>
                          <p className="mt-0.5 text-xs text-muted-foreground">{action.description}</p>
                        </div>
                        {action.enabled ? (
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <span className="rounded-full border border-border px-2 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                            em breve
                          </span>
                        )}
                      </>
                    );

                    if (action.href && action.enabled) {
                      return (
                        <Link
                          key={action.label}
                          href={action.href}
                          className="flex min-h-24 items-center gap-3 rounded-xl border border-border bg-card/70 p-4 transition hover:border-blue-500/50 hover:bg-accent/60"
                        >
                          {content}
                        </Link>
                      );
                    }

                    return (
                      <button
                        key={action.label}
                        type="button"
                        disabled={!action.enabled}
                        onClick={action.enabled ? action.onClick : undefined}
                        className="flex min-h-24 items-center gap-3 rounded-xl border border-border bg-card/70 p-4 transition enabled:hover:border-blue-500/50 enabled:hover:bg-accent/60 disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        {content}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">Histórico recente</h3>
                    <p className="text-sm text-muted-foreground">
                      Últimas conversas disponíveis para continuar no chat.
                    </p>
                  </div>
                  <Link
                    href="/dashboard/historico"
                    className="text-sm font-medium text-blue-400 transition hover:text-blue-300"
                  >
                    Ver tudo
                  </Link>
                </div>

                <div className="rounded-xl border border-border bg-card/70">
                  {isLoading ? (
                    <div className="p-5 text-sm text-muted-foreground">Carregando conversas...</div>
                  ) : homeData.conversations.length > 0 ? (
                    <div className="divide-y divide-border">
                      {homeData.conversations.map((conversation) => (
                        <Link
                          key={conversation.id}
                          href="/dashboard/chat"
                          className="flex items-center justify-between gap-4 p-4 transition hover:bg-accent/60"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-foreground">
                              {conversation.title || 'Conversa sem título'}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {conversation.agents?.name || 'AutoBrokers'} ·{' '}
                              {formatShortDate(conversation.updated_at)}
                            </p>
                          </div>
                          <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <div className="p-5">
                      <p className="text-sm font-medium text-foreground">Ainda sem conversas recentes</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Inicie uma conversa com o AutoBrokers para criar o primeiro histórico.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <OperationalStatus
                icon={MessageSquare}
                label="Chat"
                value="Ativo"
                detail="Fluxo atual preservado"
              />
              <OperationalStatus
                icon={Sparkles}
                label="LLM"
                value={hasActiveAgent ? 'Configurado' : 'Pendente'}
                detail={hasActiveAgent ? 'Agente ativo encontrado' : 'Configure o agente no Admin'}
              />
              <OperationalStatus
                icon={Database}
                label="Base de conhecimento"
                value="Em configuração"
                detail="RAG mínimo entra em fase posterior"
              />
              <OperationalStatus
                icon={PlugZap}
                label="Integrações"
                value="Em breve"
                detail="WhatsApp, portais e canais seguem desligados"
              />
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusCard({
  icon: Icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: typeof Bot;
  label: string;
  value: string;
  detail: string;
  tone: 'good' | 'warn' | 'neutral';
}) {
  const toneClass =
    tone === 'good'
      ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
      : tone === 'warn'
        ? 'border-amber-500/25 bg-amber-500/10 text-amber-300'
        : 'border-blue-500/25 bg-blue-500/10 text-blue-300';

  return (
    <div className="rounded-2xl border border-border bg-card/70 p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl border ${toneClass}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 truncate text-lg font-semibold text-foreground">{value}</p>
        </div>
      </div>
      <p className="mt-4 text-sm text-muted-foreground">{detail}</p>
    </div>
  );
}

function OperationalStatus({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof Clock3;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card/60 p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-background">
          <Icon className="h-4 w-4 text-blue-400" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{value}</p>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}
