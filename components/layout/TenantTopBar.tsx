'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Menu } from 'lucide-react';

import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { BrandMark } from '@/components/BrandMark';
import { TenantNav } from '@/components/layout/TenantNav';

/** Top bar mobile (lg-): marca + menu (drawer com a navegação completa) + nova conversa. */
export function TenantTopBar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleNewConversation = () => {
    if (pathname === '/dashboard' || pathname === '/dashboard/chat') {
      window.dispatchEvent(new CustomEvent('autobrokers:new-conversation'));
    } else {
      router.push('/dashboard');
    }
  };

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-border bg-surface px-4 py-3 lg:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger
          aria-label="Abrir menu"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
        >
          <Icon icon={Menu} size={20} />
        </SheetTrigger>
        <SheetContent side="left" className="w-72 border-border bg-surface p-0">
          <SheetTitle className="sr-only">Navegação</SheetTitle>
          <TenantNav onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>

      <Link href="/dashboard" aria-label="AutoBrokers">
        <BrandMark size={22} withWordmark />
      </Link>

      <button
        type="button"
        onClick={handleNewConversation}
        aria-label="Nova conversa"
        className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
      >
        <Icon icon={icons.novaConversa} size={20} />
      </button>
    </header>
  );
}

export default TenantTopBar;
