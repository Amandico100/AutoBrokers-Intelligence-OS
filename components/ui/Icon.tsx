import type { LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface IconProps {
  /** Componente de ícone do lucide-react (use o mapa em `@/lib/icons`). */
  icon: LucideIcon;
  className?: string;
  size?: number;
  strokeWidth?: number;
  /** Quando o ícone é informativo, passe um rótulo; sem rótulo ele é decorativo. */
  label?: string;
}

/**
 * Wrapper único de ícones do AutoBrokers.
 * Padroniza traço (1.6), tamanho e acessibilidade. Cor herda de `currentColor`.
 * Base: lucide-react (ver mapa lógico em `@/lib/icons`).
 */
export function Icon({ icon: LucideComp, className, size = 18, strokeWidth = 1.6, label }: IconProps) {
  return (
    <LucideComp
      className={cn('shrink-0', className)}
      size={size}
      strokeWidth={strokeWidth}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? 'img' : undefined}
    />
  );
}

export default Icon;
