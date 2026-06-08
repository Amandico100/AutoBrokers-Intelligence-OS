import { cn } from '@/lib/utils';

export type StatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'approval';

const toneStyles: Record<StatusTone, string> = {
  neutral: 'text-muted-foreground border-border',
  info: 'text-primary border-primary/40 bg-brand-soft',
  success: 'text-success border-success/40',
  warning: 'text-warning border-warning/40',
  danger: 'text-danger border-danger/40',
  approval: 'text-primary border-dashed border-primary/60 bg-brand-soft',
};

export interface StatusPillProps {
  tone?: StatusTone;
  label: string;
  className?: string;
}

/** Badge de status do AutoBrokers — cor + ponto + texto (nunca só cor). HANDOFF §3. */
export function StatusPill({ tone = 'neutral', label, className }: StatusPillProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 font-mono text-[11px] leading-none',
        toneStyles[tone],
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full bg-current', tone === 'approval' && 'animate-pulse')} />
      {label}
    </span>
  );
}

export default StatusPill;
