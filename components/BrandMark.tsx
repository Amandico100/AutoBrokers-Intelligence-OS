import { cn } from '@/lib/utils';

interface BrandMarkProps {
  size?: number;
  className?: string;
  /** Mostra o texto "AutoBrokers" ao lado do símbolo. */
  withWordmark?: boolean;
}

/**
 * BrandMark provisório do AutoBrokers (B0): monograma geométrico abstrato.
 * Símbolo herda a cor via `currentColor` (accent por padrão). Não é o logo final.
 */
export function BrandMark({ size = 24, className, withWordmark = false }: BrandMarkProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-2', className)}
      aria-label={withWordmark ? undefined : 'AutoBrokers'}
      role={withWordmark ? undefined : 'img'}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 22 22"
        fill="none"
        aria-hidden="true"
        className="text-primary"
      >
        <rect x="1.2" y="1.2" width="19.6" height="19.6" rx="6" stroke="currentColor" strokeWidth="1.4" />
        <rect
          x="7.2"
          y="7.2"
          width="7.6"
          height="7.6"
          rx="2"
          transform="rotate(45 11 11)"
          stroke="currentColor"
          strokeWidth="1.4"
        />
      </svg>
      {withWordmark && (
        <span className="text-[15px] font-semibold tracking-tight text-foreground">AutoBrokers</span>
      )}
    </span>
  );
}

export default BrandMark;
