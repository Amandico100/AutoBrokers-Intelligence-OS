import Link from 'next/link';
import type { LucideIcon } from 'lucide-react';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { GalleryGrid, GalleryCard, type StatusTone } from '@/components/patterns';

export interface ModuleArea {
  key: string;
  icon: LucideIcon;
  title: string;
  description: string;
  href?: string;
  status?: { tone: StatusTone; label: string };
  cta?: string;
}

export interface ModuleIndexProps {
  icon: LucideIcon;
  title: string;
  description: string;
  areas: ModuleArea[];
  showOpenChat?: boolean;
}

/** Página-central de módulo: header + grade de áreas (cards) + atalho ao AutoBrokers. */
export function ModuleIndex({ icon, title, description, areas, showOpenChat = true }: ModuleIndexProps) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icon} size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>

        <div className="mt-8">
          <GalleryGrid>
            {areas.map((a) => (
              <GalleryCard
                key={a.key}
                icon={a.icon}
                title={a.title}
                description={a.description}
                status={a.status}
                cta={a.cta ?? 'Abrir'}
                href={a.href}
              />
            ))}
          </GalleryGrid>
        </div>

        {showOpenChat && (
          <div className="mt-8">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:border-primary/40"
            >
              <Icon icon={icons.autobrokers} size={16} className="text-primary" />
              Abrir o AutoBrokers
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default ModuleIndex;
