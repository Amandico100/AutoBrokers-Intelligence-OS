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
  { key: 'configuracoes', label: 'Configurações', href: '/dashboard/configuracoes', icon: 'configuracoes' },
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
