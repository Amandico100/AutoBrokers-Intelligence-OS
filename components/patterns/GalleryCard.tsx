import Link from 'next/link';
import type { LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { StatusPill, type StatusTone } from '@/components/patterns/StatusPill';

export interface GalleryCardProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  category?: string;
  tags?: string[];
  status?: { tone: StatusTone; label: string };
  cta?: string;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

/** Card do padrão Galeria (Auxiliares, Conectores, Seguradoras…). Visual, sem lógica. */
export function GalleryCard({
  icon,
  title,
  description,
  category,
  tags,
  status,
  cta,
  href,
  onClick,
  disabled,
  className,
}: GalleryCardProps) {
  const inner = (
    <div
      className={cn(
        'flex h-full flex-col rounded-xl border border-border bg-surface p-4 text-left transition-colors',
        disabled ? 'opacity-60' : 'hover:border-primary/40 hover:bg-surface-2',
        className,
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
          <Icon icon={icon} size={18} />
        </span>
        {status && <StatusPill tone={status.tone} label={status.label} />}
      </div>

      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{description}</p>}

      {(category || (tags && tags.length > 0)) && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {category && (
            <span className="rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
              {category}
            </span>
          )}
          {tags?.map((t) => (
            <span key={t} className="rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
              {t}
            </span>
          ))}
        </div>
      )}

      {cta && (
        <div className="mt-4 flex items-center gap-1 text-xs font-medium text-primary">
          {cta}
          <Icon icon={icons.avancar} size={14} />
        </div>
      )}
    </div>
  );

  if (href && !disabled) {
    return (
      <Link href={href} className="block h-full">
        {inner}
      </Link>
    );
  }
  if (onClick && !disabled) {
    return (
      <button type="button" onClick={onClick} className="block h-full w-full">
        {inner}
      </button>
    );
  }
  return <div className="h-full">{inner}</div>;
}

export default GalleryCard;
