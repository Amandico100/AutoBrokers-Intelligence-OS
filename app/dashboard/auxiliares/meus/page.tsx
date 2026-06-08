import Link from 'next/link';

import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { DetailSection } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Meus Auxiliares · AutoBrokers' };

export default function MeusAuxiliaresPage() {
  return (
    <ModulePlaceholder
      icon={icons.auxiliares}
      title="Meus Auxiliares"
      subtitle="Auxiliares ativados pela sua corretora."
      breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Meus Auxiliares' }]}
    >
      <DetailSection>
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
            <Icon icon={icons.auxiliares} size={18} />
          </span>
          <p className="text-sm font-medium text-foreground">Você ainda não ativou nenhum Auxiliar.</p>
          <p className="max-w-sm text-xs text-muted-foreground">
            Escolha um modelo pronto na Galeria e coloque o AutoBrokers para trabalhar por você.
          </p>
          <Link
            href="/dashboard/auxiliares/galeria"
            className="mt-1 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <Icon icon={icons.galeria} size={16} />
            Ver galeria
          </Link>
        </div>
      </DetailSection>
    </ModulePlaceholder>
  );
}
