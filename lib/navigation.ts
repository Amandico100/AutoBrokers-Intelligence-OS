import type { IconName } from '@/lib/icons';

export interface NavItem {
  key: string;
  label: string;
  /** Rótulo curto para a bottom-nav mobile (opcional). */
  short?: string;
  href: string;
  icon: IconName;
}

/** Os pilares da navegação tenant (UX-001 + Memórias/SPEC-036 E3). */
export const PILLARS: NavItem[] = [
  { key: 'autobrokers', label: 'AutoBrokers', href: '/dashboard', icon: 'autobrokers' },
  // SPEC-059 §25.1 — o Briefing entra como pilar, ao lado do chat. Ele responde
  // "o que precisa de mim hoje?", que é a pergunta que o corretor faz antes de
  // qualquer outra. Escondê-lo no secundário faria o produto proativo depender
  // de o corretor lembrar de procurá-lo.
  { key: 'briefing', label: 'Briefing', href: '/dashboard/briefing', icon: 'aprovacao' },
  // SPEC-060 §30.2 — a pesquisa nasce no chat; esta é a tela onde ela é
  // reencontrada. Fica como pilar, e não no secundário, pela lição da 059:
  // tela sem link é tela que não existe para quem usa, e "Pesquisas" é o que
  // o corretor procura quando quer rever o que mandou conferir.
  { key: 'pesquisas', label: 'Pesquisas', href: '/dashboard/pesquisas', icon: 'buscar' },
  { key: 'atendimentos', label: 'Atendimentos', href: '/dashboard/atendimentos', icon: 'atendimentos' },
  { key: 'auxiliares', label: 'Auxiliares', href: '/dashboard/auxiliares', icon: 'auxiliares' },
  { key: 'memorias', label: 'Memórias', href: '/dashboard/memorias', icon: 'conhecimento' },
  { key: 'personalizacao', label: 'Personalização', short: 'Config', href: '/dashboard/personalizacao', icon: 'personalizacao' },
];

/** Navegação secundária discreta (não polui o primeiro nível). */
export const SECONDARY: NavItem[] = [
  { key: 'atividades', label: 'Atividades', href: '/dashboard/atividades', icon: 'success' },
  { key: 'historico', label: 'Histórico', href: '/dashboard/historico', icon: 'historico' },
  { key: 'conversas', label: 'Conversas', href: '/dashboard/conversas', icon: 'atendimentos' },
  { key: 'configuracoes', label: 'Configurações', href: '/dashboard/configuracoes', icon: 'configuracoes' },
];

/**
 * Administração DA CORRETORA — SPEC-061 §6.
 *
 * Estas quatro telas moravam em `/admin`, junto com a administração da
 * PLATAFORMA. A corretora entrava num endereço chamado "admin" e via um menu
 * que escondia metade dos itens — e esconder item de menu não protege nada:
 * quem digitasse o endereço chegava lá.
 *
 * Agora elas vivem na casa da corretora. O que muda para ela é só o endereço;
 * o que muda para a plataforma é que `/admin` passa a ser só dela.
 *
 * Ficam separadas dos PILLARS de propósito: são o que se configura de vez em
 * quando, não o trabalho do dia. Misturá-las com Briefing e Atendimentos
 * empurraria o trabalho diário para baixo.
 */
export const ADMINISTRACAO_DA_CORRETORA: NavItem[] = [
  { key: 'equipe', label: 'Minha equipe', href: '/dashboard/equipe', icon: 'atendimentos' },
  { key: 'agente', label: 'Meu agente', href: '/dashboard/agente', icon: 'autobrokers' },
  { key: 'documentos', label: 'Meus documentos', href: '/dashboard/documentos', icon: 'conhecimento' },
  { key: 'plano', label: 'Meu plano', href: '/dashboard/plano', icon: 'aprovacao' },
];

/**
 * Estado ativo da navegação.
 * AutoBrokers (/dashboard) também fica ativo em /dashboard/chat (mesma experiência).
 * Os demais usam match exato ou de subrota.
 */
export function isActiveRoute(pathname: string, href: string): boolean {
  if (href === '/dashboard') {
    return pathname === '/dashboard' || pathname === '/dashboard/chat';
  }
  return pathname === href || pathname.startsWith(href + '/');
}
