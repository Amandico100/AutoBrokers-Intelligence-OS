import type { LucideIcon } from 'lucide-react';

import { Icon } from '@/components/ui/Icon';
import { DetailHeader, DetailSection } from '@/components/patterns';

export interface ModulePlaceholderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  breadcrumb?: { label: string; href?: string }[];
  description?: string;
  children?: React.ReactNode;
}

/** Shell de subpágina de módulo: header (breadcrumb) + estado "em construção" (ou children). */
export function ModulePlaceholder({
  icon,
  title,
  subtitle,
  breadcrumb,
  description,
  children,
}: ModulePlaceholderProps) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader icon={icon} title={title} subtitle={subtitle} breadcrumb={breadcrumb} />
        {children ?? (
          <DetailSection>
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
                <Icon icon={icon} size={18} />
              </span>
              <p className="text-sm font-medium text-foreground">
                {description ?? 'Em construção planejada'}
              </p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Estamos preparando esta área. Nenhuma ação real é executada ainda.
              </p>
            </div>
          </DetailSection>
        )}
      </div>
    </div>
  );
}

export default ModulePlaceholder;
