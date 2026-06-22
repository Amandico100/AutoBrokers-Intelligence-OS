import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { TeamClient } from './TeamClient';

export const metadata = { title: 'Equipe · AutoBrokers' };

export default function EquipePage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.equipe}
          title="Equipe"
          subtitle="Quem tem acesso à sua corretora, com papel e status."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Equipe' }]}
        />
        <TeamClient />
      </div>
    </div>
  );
}
