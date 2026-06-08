'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { cn } from '@/lib/utils';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { PILLARS, SECONDARY, isActiveRoute, type NavItem } from '@/lib/navigation';
import { BrandMark } from '@/components/BrandMark';
import { ThemeToggle } from '@/components/ThemeToggle';
import { clearSession } from '@/lib/session';

/**
 * Corpo da navegação tenant — usado pela sidebar desktop e pelo drawer mobile.
 * `onNavigate` fecha o drawer no mobile ao clicar num item.
 */
export function TenantNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const [company, setCompany] = useState('');
  const [userName, setUserName] = useState('');

  useEffect(() => {
    let active = true;
    fetch('/api/user/profile')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (active && d) {
          setCompany(d.companyName || '');
          setUserName(d.name || '');
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // segue para limpar sessão mesmo em caso de erro
    }
    clearSession();
    router.push('/login');
  };

  const handleNewConversation = () => {
    onNavigate?.();
    if (pathname === '/dashboard' || pathname === '/dashboard/chat') {
      window.dispatchEvent(new CustomEvent('autobrokers:new-conversation'));
    } else {
      router.push('/dashboard');
    }
  };

  const renderItem = (item: NavItem) => {
    const active = isActiveRoute(pathname, item.href);
    return (
      <Link
        key={item.key}
        href={item.href}
        onClick={onNavigate}
        className={cn(
          'relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
          active
            ? 'bg-surface-2 text-foreground'
            : 'text-muted-foreground hover:bg-surface-2/60 hover:text-foreground',
        )}
      >
        {active && (
          <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary" />
        )}
        <Icon icon={icons[item.icon]} size={18} className={active ? 'text-primary' : ''} />
        <span className="font-medium">{item.label}</span>
      </Link>
    );
  };

  return (
    <div className="flex h-full flex-col">
      {/* Marca */}
      <div className="px-4 py-4">
        <Link href="/dashboard" onClick={onNavigate}>
          <BrandMark size={24} withWordmark />
        </Link>
      </div>

      {/* Nova conversa */}
      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={handleNewConversation}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-surface-3"
        >
          <Icon icon={icons.novaConversa} size={16} className="text-primary" />
          Nova conversa
        </button>
      </div>

      {/* Pilares */}
      <nav className="flex flex-col gap-1 px-3">{PILLARS.map(renderItem)}</nav>

      <div className="mx-3 my-3 border-t border-border-soft" />

      {/* Secundário */}
      <nav className="flex flex-col gap-1 px-3">{SECONDARY.map(renderItem)}</nav>

      {/* Rodapé */}
      <div className="mt-auto border-t border-border-soft p-3">
        {(company || userName) && (
          <div className="mb-3 px-1">
            {company && <p className="truncate text-sm font-medium text-foreground">{company}</p>}
            {userName && <p className="truncate text-xs text-muted-foreground">{userName}</p>}
          </div>
        )}
        <div className="flex items-center gap-2">
          <button
            onClick={handleLogout}
            className="flex flex-1 items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <Icon icon={icons.sair} size={16} />
            Sair
          </button>
          <ThemeToggle />
        </div>
      </div>
    </div>
  );
}

export default TenantNav;
