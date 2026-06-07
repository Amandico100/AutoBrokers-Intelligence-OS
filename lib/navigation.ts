import type { IconName } from '@/lib/icons';

export interface NavItem {
  key: string;
  label: string;
  /** Rótulo curto para a bottom-nav mobile (opcional). */
  short?: string;
  href: string;
  icon: IconName;
}

/** Os 4 pilares da navegação tenant (UX-001). */
export const PILLARS: NavItem[] = [
  { key: 'autobrokers', label: 'AutoBrokers', href: '/dashboard', icon: 'autobrokers' },
  { key: 'atendimentos', label: 'Atendimentos', href: '/dashboard/atendimentos', icon: 'atendimentos' },
  { key: 'auxiliares', label: 'Auxiliares', href: '/dashboard/auxiliares', icon: 'auxiliares' },
  { key: 'personalizacao', label: 'Personalização', short: 'Config', href: '/dashboard/personalizacao', icon: 'personalizacao' },
];

/** Navegação secundária discreta (não polui o primeiro nível). */
export const SECONDARY: NavItem[] = [
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
