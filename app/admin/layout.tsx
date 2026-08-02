'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Building2,
  Users,
  UserCheck,
  Activity,
  Brain,
  Inbox,
  LayoutDashboard,
  ShieldCheck,
  LogOut,
  Shield,
  FileText,
  MessageSquare,
  Bot,
  Map,
  MessageCircle,
  DollarSign,
  Settings,
  CreditCard,
  Lock,
  Globe,
  CalendarClock,

} from 'lucide-react';
import { getAdminSession, clearAdminSession } from '@/lib/adminSession';
import { Button } from '@/components/ui/button';
import { useAdminRole } from '@/hooks/useAdminRole';
import { TermsAcceptanceModal } from '@/components/TermsAcceptanceModal';
import { ThemeToggle } from '@/components/ThemeToggle';
import BuscaGlobal from '@/components/admin/BuscaGlobal';

interface SubscriptionData {
  has_subscription: boolean;
  status: 'active' | 'past_due' | null;
  plan: { name: string; price_brl: number; display_credits: number } | null;
  credits_display: { remaining: number; used: number; total: number; percentage: number };
  usage: {
    agents: { used: number; limit: number };
    knowledge_bases: { used: number; limit: number };
  };
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { role, isLoading: roleLoading, companyId, isOwner } = useAdminRole();
  const [adminName, setAdminName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<string[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [termsOutdated, setTermsOutdated] = useState(false);
  const [activeTerms, setActiveTerms] = useState<{
    id: string; title: string; content: string; version: string;
  } | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch company name for Company Admin via API
  useEffect(() => {
    const fetchCompanyName = async () => {
      if (role === 'company_admin' && companyId) {
        try {
          const response = await fetch('/api/admin/me', { credentials: 'include' });
          if (response.ok) {
            const data = await response.json();
            if (data.company?.company_name) {
              setCompanyName(data.company.company_name);
            }
          }
        } catch (error) {
          console.error('[ADMIN LAYOUT] Error fetching company name:', error);
        }
      }
    };

    if (!roleLoading) {
      fetchCompanyName();
    }
  }, [role, companyId, roleLoading]);

  // Fetch subscription data for Company Admin
  useEffect(() => {
    const fetchSubscription = async () => {
      if (role === 'company_admin') {
        try {
          const response = await fetch('/api/billing/subscription', { credentials: 'include' });
          if (response.ok) {
            const data = await response.json();
            setSubscription(data);
          }
        } catch (error) {
          console.error('[ADMIN LAYOUT] Error fetching subscription:', error);
        }
      }
    };

    if (!roleLoading) {
      fetchSubscription();
    }
  }, [role, roleLoading]);

  // Check if company admin needs to re-accept terms
  useEffect(() => {
    const checkTerms = async () => {
      if (role === 'company_admin') {
        try {
          const res = await fetch('/api/auth/me', { credentials: 'include' });
          if (res.ok) {
            const data = await res.json();
            if (data.termsOutdated && data.activeTerms) {
              setTermsOutdated(true);
              setActiveTerms(data.activeTerms);
            }
          }
        } catch (error) {
          console.error('[ADMIN LAYOUT] Error checking terms:', error);
        }
      }
    };
    if (!roleLoading && role) {
      checkTerms();
    }
  }, [role, roleLoading]);

  useEffect(() => {
    if (!mounted) return;

    if (pathname === '/admin/login') {
      setLoading(false);
      return;
    }

    // Check for admin session in localStorage (not cookie - it's HttpOnly)
    const adminSession = getAdminSession();

    if (adminSession) {
      setAdminName(adminSession.name || 'Admin');
      setLoading(false);
      return;
    }

    // If no admin session, check if it's a company admin via useAdminRole
    // The useAdminRole hook will handle the user session check via API
    setAdminName('Loading...');
    setLoading(false);
  }, [mounted, pathname]);

  // SPEC-061 §6 — quem pode ficar em `/admin`.
  //
  // A lista `masterOnlyRoutes` que existia aqui SUMIU, e isso continua certo:
  // ela enumerava, no navegador, os endereços que o admin de corretora não
  // podia ver, e enumerar é frágil — toda tela nova precisava lembrar de entrar
  // na lista, e quem digitasse o endereço chegava lá de qualquer jeito.
  //
  // O que estava errado era a PERGUNTA. "Qual é o seu papel?" parece a mesma
  // coisa que "você é a plataforma?", e não é: o dono é as duas coisas ao mesmo
  // tempo — plataforma, e também usuário dentro de uma corretora. Qual das duas
  // respostas aparece depende de qual sessão sobreviveu, e há três, com
  // vocabulários e prazos diferentes:
  //
  //   localStorage `smith_admin_session`  →  diz "master",        dura 8 horas
  //   cookie       `smith_admin_session`  →  diz "master_admin",  morre ao fechar o navegador
  //   cookie       `smith_user_session`   →  diz "admin"/"owner", dura dias
  //
  // Quando as duas primeiras somem — oito horas depois, ou na segunda de manhã
  // com o navegador reiniciado — sobra a terceira. Aí `/api/admin/me` responde
  // "admin de corretora", que é VERDADE e é a resposta errada para esta
  // pergunta. A regra tratava isso como prova de "você não é a plataforma" e,
  // valendo para todo `/admin/*`, transformava cada endereço do Admin num pulo
  // para o `/dashboard`. Sem saída, porque o pulo acontecia antes de qualquer
  // tela carregar.
  //
  // A pergunta certa tem UM dono — o servidor — e TRÊS respostas. Era a
  // terceira que faltava: quem não tem sessão nenhuma pediu o portal da
  // plataforma e precisa receber a porta dele, não uma deportação silenciosa.
  useEffect(() => {
    if (!mounted) return;
    if (pathname === '/admin/login') return;

    let atual = true;

    (async () => {
      try {
        const resposta = await fetch('/api/admin/me', { credentials: 'include' });
        if (!atual) return;

        if (resposta.ok) {
          const dados = await resposta.json();
          // 1. É a plataforma. Fica.
          if (dados?.sessionType === 'master_admin') return;
          // 2. É corretora. A casa dela é outra, e existe.
          router.push('/dashboard');
          return;
        }

        // 3. Não é ninguém ainda. Quem pediu `/admin` recebe o login do
        //    `/admin` — é assim que se volta para dentro.
        router.push('/admin/login');
      } catch {
        // Falha de rede não é prova de que você não é a plataforma. Deixa
        // ficar: cada tela de dentro tem a própria checagem no servidor, e
        // expulsar por causa de wifi ruim é o defeito, não a proteção.
      }
    })();

    return () => {
      atual = false;
    };
  }, [mounted, pathname, router]);

  const handleLogout = async () => {
    try {
      // Try both logout endpoints
      await fetch('/api/admin/logout', { method: 'POST' });
      await fetch('/api/auth/logout', { method: 'POST' });

      clearAdminSession();

      // Clear all cookies
      document.cookie.split(';').forEach((c) => {
        document.cookie = c
          .replace(/^ +/, '')
          .replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
      });

      router.push('/admin/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  if (!mounted || (loading && pathname !== '/admin/login')) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground">Carregando...</div>
      </div>
    );
  }

  if (pathname === '/admin/login') {
    return <div className="min-h-screen bg-background">{children}</div>;
  }

  // SPEC-036 Etapa 1: navegação reorganizada em 10 destinos (operação primeiro,
  // gestão depois). Nenhuma rota morreu — páginas antigas viram filhos dos hubs.
  const masterMenuItems = [
    // SPEC-061 §10 — OITO hubs. Não é preferência estética: o Admin tinha 15
    // grupos de primeiro nível e 34 links, e o Founder relatou que "é uma
    // bagunça e não consigo entender".
    //
    // Quinze grupos obrigam a pessoa a saber ONDE uma coisa mora antes de
    // procurá-la. Oito hubs, nomeados pelo ASSUNTO, permitem eliminar sete
    // deles de cara e olhar dentro de um.
    //
    // Nenhuma rota morreu: toda página virou filha do hub a que pertence.
    // §10 diz "não adicionar novo item de primeiro nível sem revisão
    // canônica" — daí os oito, exatamente.
    //
    // A ordem é a do dia de trabalho: o que exige decisão primeiro
    // (Visão geral), o que está acontecendo depois (Operação), e o que só se
    // mexe de vez em quando por último (Governança).
    {
      href: '/admin',
      icon: LayoutDashboard,
      label: 'Visão geral',
      submenu: [
        { href: '/admin', label: 'Resumo' },
        { href: '/admin/inbox', label: 'O que precisa de mim' },
      ],
    },
    {
      href: '/admin/companies',
      icon: Building2,
      label: 'Corretoras',
      submenu: [
        { href: '/admin/companies', label: 'Todas as corretoras' },
        { href: '/admin/corretoras', label: 'Como cada uma está' },
        { href: '/admin/all-users', label: 'Pessoas' },
        { href: '/admin/pending-users', label: 'Esperando aprovação' },
      ],
    },
    {
      href: '/admin/trabalhos',
      icon: Activity,
      label: 'Operação',
      submenu: [
        { href: '/admin/trabalhos', label: 'Trabalhos em andamento' },
        // §16 — decidir é diferente de consertar. Dois destinos, não um.
        { href: '/admin/aprovacoes', label: 'Esperando decisão' },
        { href: '/admin/conversas', label: 'Atendimentos' },
        { href: '/admin/conversation-logs', label: 'Histórico de conversas' },
        { href: '/admin/espelho', label: 'Acompanhar um atendimento' },
        { href: '/admin/acionamentos', label: 'Acionamentos ao vivo' },
      ],
    },
    {
      href: '/admin/inteligencia',
      icon: Brain,
      label: 'Inteligência',
      // SPEC-064 Bloco I — o que mudou, e o que NÃO mudou, e por quê.
      //
      // A auditoria mediu o problema certo: este submenu tinha NOVE itens, e
      // quatro respondiam outra pergunta. "O que o sistema PERCEBEU" e "o que
      // o sistema SABE FAZER" são coisas diferentes, e estavam juntas.
      //
      // Eu cheguei a criar um nono hub "Catálogo" para separá-las — e o teste
      // da SPEC-061 §10 me pegou. Ele está certo: §10 diz "não adicionar novo
      // item de primeiro nível sem revisão canônica", e o Admin já chegou a
      // QUINZE grupos antes de o Founder dizer "é uma bagunça". Fazer isso
      // seria repetir, no admin, exatamente o que a SPEC-064 desfez no menu do
      // corretor. **O menu não cresce vale para os dois lados.**
      //
      // Então a separação acontece DENTRO do submenu, que é livre — a ordem
      // agrupa por pergunta, com os rótulos dizendo qual é qual.
      //
      // A reorganização de primeiro nível que a SPEC-064 I.3 propõe (seis
      // hubs em vez de oito) CONFLITA com a estrutura que o Founder aprovou na
      // SPEC-061. Registrada em FOUNDER-DECISIONS.md — é decisão dele, não
      // minha (CLAUDE.md §10).
      submenu: [
        // o que o sistema PERCEBEU
        { href: '/admin/inteligencia', label: 'O que o sistema percebeu' },
        { href: '/admin/pesquisa', label: 'O que buscamos na internet' },
        { href: '/admin/auxiliares/factory', label: 'O que as corretoras pediram' },
        { href: '/admin/insights', label: 'Garimpo (legado)' },
        // o que o sistema SABE FAZER — o catálogo, na ordem da ontologia:
        // quem faz · quem conversa · quando acontece · o que autoriza
        { href: '/admin/auxiliares', label: 'Catálogo: Auxiliares' },
        { href: '/admin/central-agentes', label: 'Catálogo: Agentes' },
        { href: '/admin/routine-templates', label: 'Catálogo: Modelos de rotina' },
        { href: '/admin/capacidades', label: 'Catálogo: Skills, ferramentas e conectores' },
        { href: '/admin/blueprint-center', label: 'Blueprint Center' },
      ],
    },
    // SPEC-064 Bloco H — o Portal Browser saiu daqui junto com o código.
    //
    // Este submenu tinha DOIS itens para o simulador ("Portais das
    // seguradoras" e "Navegador de portal"), e nenhum dos dois jamais acessou
    // um portal: todas as sessões tinham `real_action_allowed: false`, as
    // contas tinham `credential_ref: null`, e os canários da Resulta foram
    // abortados em 21/06.
    //
    // Quem entra na Allianz de verdade é o `portal_worker`, e a credencial da
    // corretora se cadastra na casa dela —
    // `/dashboard/personalizacao/conectores/portais`, que grava na tabela
    // `portal_accounts` que o worker lê.
    {
      href: '/admin/insurer-action-channels',
      icon: Globe,
      label: 'Conexões',
      submenu: [
        { href: '/admin/insurer-action-channels', label: 'Canais de seguradora' },
        { href: '/admin/atlas', label: 'Atlas de rotas' },
      ],
    },
    {
      href: '/admin/knowledge-base',
      icon: FileText,
      label: 'Conhecimento',
      submenu: [
        { href: '/admin/knowledge-base', label: 'Base de conhecimento' },
        { href: '/admin/knowledge-base/sanitize', label: 'Limpar documento' },
      ],
    },
    {
      href: '/admin/financeiro',
      icon: DollarSign,
      label: 'Financeiro',
      submenu: [
        { href: '/admin/financeiro', label: 'Receita e planos' },
        { href: '/admin/costs', label: 'Custo por corretora' },
        { href: '/admin/finops/usage', label: 'Consumo' },
        { href: '/admin/finops/pricing', label: 'Preços' },
        { href: '/admin/finops/plans', label: 'Planos' },
      ],
    },
    {
      href: '/admin/governanca',
      icon: ShieldCheck,
      label: 'Governança',
      submenu: [
        { href: '/admin/governanca', label: 'Quem pode o quê' },
        { href: '/admin/legal-documents', label: 'Termos e políticas' },
        { href: '/admin/logs', label: 'Registro técnico' },
        { href: '/admin/settings', label: 'Configurações' },
      ],
    },
  ];

  // SPEC-061 §6 — `companyAdminMenuItems` foi REMOVIDO.
  //
  // As cinco telas que ele listava eram da corretora e mudaram de casa:
  //
  //   /admin/team          -> /dashboard/equipe
  //   /admin/conversations -> /dashboard/conversas
  //   /admin/agent         -> /dashboard/agente
  //   /admin/documents     -> /dashboard/documentos
  //   /admin/billing       -> /dashboard/plano
  //
  // Os endereços antigos continuam existindo como redirecionamento: link
  // salvo não some quando a rota muda.
  //
  // O bloqueio por assinatura vencida (`isLocked`) saiu junto — ele só fazia
  // sentido para o menu da corretora, e a corretora não tem mais menu aqui.
  // A regra continua valendo onde ela pertence, no `/dashboard`.
  const menuItems = masterMenuItems;
  const isLocked = (_href: string) => false;

  return (
    <div className="h-screen bg-background flex text-foreground overflow-hidden">
      <aside className="w-64 bg-card border-r border-border flex flex-col">
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center overflow-hidden">
              <img src="/smith-logo.png" alt="AutoBrokers Logo" className="w-full h-full object-cover" />
            </div>
            <div>
              <h1 className="text-foreground font-bold text-lg">
                Admin AutoBrokers
              </h1>
              <div className="flex flex-col mt-0.5">
                <p className="text-[10px] text-black dark:text-muted-foreground font-medium truncate max-w-[140px]">
                  Logado como {adminName}
                </p>
                {role && role !== 'master' && (
                  <p className="text-[10px] text-blue-400 font-medium truncate max-w-[140px]">
                    {companyName || 'Carregando...'}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* SPEC-061 §11.3 — a busca fica ACIMA do menu, não dentro dele.
            Quem já sabe o que quer não precisa varrer oito hubs; quem não
            sabe continua tendo o menu logo abaixo. */}
        <div className="px-4 pt-4">
          <BuscaGlobal />
        </div>

        <nav className="flex-1 p-4 space-y-2 overflow-y-auto min-h-0">
          {menuItems.map((item: any) => {
            const hasSubmenu = item.submenu && item.submenu.length > 0;
            const isExpanded = expandedMenus.includes(item.href);
            const isActive = hasSubmenu ? pathname.startsWith(item.href) : pathname === item.href;

            if (hasSubmenu) {
              // SPEC-046: o item-pai NAVEGA para o próprio href (antes só
              // expandia — /admin/companies ficava inalcançável). A seta,
              // separada, expande/recolhe o submenu.
              return (
                <div key={item.href}>
                  <div
                    className={`flex items-center rounded-lg transition-colors ${isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-900/20'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                      }`}
                  >
                    <Link
                      href={item.href}
                      onClick={() => {
                        setExpandedMenus((prev) =>
                          prev.includes(item.href) ? prev : [...prev, item.href],
                        );
                      }}
                      className="flex flex-1 items-center gap-3 px-4 py-3"
                    >
                      <item.icon className="w-5 h-5" />
                      <span className="font-medium">{item.label}</span>
                    </Link>
                    <button
                      aria-label={`Expandir ${item.label}`}
                      onClick={() => {
                        setExpandedMenus((prev) =>
                          prev.includes(item.href)
                            ? prev.filter((h) => h !== item.href)
                            : [...prev, item.href],
                        );
                      }}
                      className="px-3 py-3"
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </button>
                  </div>
                  {isExpanded && (
                    <div className="ml-6 mt-1 space-y-1">
                      {item.submenu.map((sub: any) => (
                        <Link
                          key={sub.href}
                          href={sub.href}
                          className={`block px-4 py-2 rounded-lg text-sm transition-colors ${pathname === sub.href
                            ? 'text-white bg-blue-600 shadow-sm'
                            : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                            }`}
                        >
                          {sub.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              );
            }

            const itemLocked = isLocked(item.href);

            if (itemLocked) {
              return (
                <div
                  key={item.href}
                  className="flex items-center justify-between gap-3 px-4 py-3 rounded-lg text-muted-foreground/50 cursor-not-allowed opacity-50"
                  title="Indisponível"
                >
                  <div className="flex items-center gap-3">
                    <item.icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </div>
                  <Lock className="w-4 h-4" />
                </div>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-900/20'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
          {/* SPEC-061 §6 — o widget de créditos SAIU.
              Ele renderizava sob `role === 'company_admin'`, e depois da
              separação nenhum company_admin chega até este layout: ele é
              mandado para /dashboard na entrada. Eram 150 linhas de código
              morto — e código morto que menciona `/admin/billing` mantinha
              viva uma referência a uma tela que mudou de casa.

              Plano e créditos são assunto da corretora, e vivem em
              /dashboard/plano. */}

          {/* Version Info moved to bottom */}
          <div className="mt-auto pt-4 text-center">
            <p className="text-[10px] text-muted-foreground">
              AutoBrokers Intelligence OS
            </p>
          </div>
        </nav>

        <div className="p-4 border-t border-border">



          <div className="flex items-center gap-2">
            <Button
              onClick={handleLogout}
              variant="outline"
              className="flex-1 bg-transparent border-border text-muted-foreground hover:text-foreground hover:bg-accent"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Sair
            </Button>
            <div className="flex-shrink-0">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </aside >

      <main
        className={`flex-1 h-full flex flex-col relative ${pathname?.startsWith('/admin/conversations') ? 'overflow-hidden' : 'overflow-y-auto'
          }`}
      >
        {/* Payment Failed Banner */}
        {role === 'company_admin' && subscription?.status === 'past_due' && (
          <div className="bg-destructive/10 border-b border-destructive/30 px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="text-destructive font-semibold text-sm">
                  Pagamento falhou na renovação do plano
                </p>
                <p className="text-muted-foreground text-xs">
                  Atualize seu método de pagamento para continuar usando o serviço
                </p>
              </div>
            </div>
            <Button
              onClick={async () => {
                try {
                  const res = await fetch('/api/billing/portal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ return_url: window.location.href }),
                  });
                  const data = await res.json();
                  if (data.portal_url) window.location.href = data.portal_url;
                } catch (e) {
                  console.error('Error opening portal:', e);
                }
              }}
              size="sm"
              className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
            >
              Gerenciar Método de Pagamento
            </Button>
          </div>
        )}
        {children}
      </main>
      {
        termsOutdated && activeTerms && (
          <TermsAcceptanceModal
            activeTerms={activeTerms}
            onAccepted={() => setTermsOutdated(false)}
          />
        )
      }
    </div >
  );
}
