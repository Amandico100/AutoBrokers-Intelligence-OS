import Link from 'next/link';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

/** Os 2 atalhos discretos abaixo do composer no estado inicial. */
export function ChatShortcutCards() {
  return (
    <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
      <Link
        href="/dashboard/atendimentos"
        className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-sm text-foreground-2 transition-colors hover:border-primary/40 hover:text-foreground"
      >
        <Icon icon={icons.atendimentos} size={16} className="text-muted-foreground" />
        Ver atendimentos
      </Link>
      <Link
        href="/dashboard/auxiliares"
        className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-sm text-foreground-2 transition-colors hover:border-primary/40 hover:text-foreground"
      >
        <Icon icon={icons.auxiliares} size={16} className="text-muted-foreground" />
        Novo auxiliar
      </Link>
    </div>
  );
}

export default ChatShortcutCards;
