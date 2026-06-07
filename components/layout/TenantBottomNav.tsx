'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@/lib/utils';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { PILLARS, isActiveRoute } from '@/lib/navigation';

/** Bottom nav mobile (lg-) — os 4 pilares. Fica no fluxo, abaixo do conteúdo. */
export function TenantBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="flex shrink-0 items-stretch border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden">
      {PILLARS.map((item) => {
        const active = isActiveRoute(pathname, item.href);
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              'flex flex-1 flex-col items-center gap-1 px-1 py-2.5 text-[10px] transition-colors',
              active ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon icon={icons[item.icon]} size={20} />
            <span className="font-medium leading-none">{item.short ?? item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default TenantBottomNav;
