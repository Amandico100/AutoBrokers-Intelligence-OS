import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { InsurersClient } from './InsurersClient';

export const metadata = { title: 'Seguradoras · AutoBrokers' };

export default function SeguradorasPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.seguradoras}
          title="Seguradoras"
          subtitle="Contatos globais (leitura) e o estado dos corredores da sua corretora por seguradora."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Seguradoras' }]}
        />
        <InsurersClient />
      </div>
    </div>
  );
}
