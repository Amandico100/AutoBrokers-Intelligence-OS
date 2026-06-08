import Link from 'next/link';
import type { LucideIcon } from 'lucide-react';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { StatusPill, type StatusTone } from '@/components/patterns/StatusPill';

export interface DetailHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  status?: { tone: StatusTone; label: string };
  backHref?: string;
  backLabel?: string;
  breadcrumb?: { label: string; href?: string }[];
  actions?: React.ReactNode;
}

/** Cabeçalho do padrão Detalhe: breadcrumb/voltar + ícone + título + status + ações. */
export function DetailHeader({
  icon,
  title,
  subtitle,
  status,
  backHref,
  backLabel = 'Voltar',
  breadcrumb,
  actions,
}: DetailHeaderProps) {
  return (
    <div className="space-y-3">
      {breadcrumb && breadcrumb.length > 0 ? (
        <nav className="flex flex-wrap items-center gap-1 font-mono text-[11px] text-muted-foreground">
          {breadcrumb.map((b, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <span className="text-faint">/</span>}
              {b.href ? (
                <Link href={b.href} className="hover:text-foreground">
                  {b.label}
                </Link>
              ) : (
                <span className="text-foreground">{b.label}</span>
              )}
            </span>
          ))}
        </nav>
      ) : backHref ? (
        <Link
          href={backHref}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <Icon icon={icons.voltar} size={14} /> {backLabel}
        </Link>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icon} size={22} />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
              {status && <StatusPill tone={status.tone} label={status.label} />}
            </div>
            {subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export default DetailHeader;
