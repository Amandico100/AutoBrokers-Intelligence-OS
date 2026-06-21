import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { CorridorGalleryClient } from './CorridorGalleryClient';

export const metadata = { title: 'Corredores · AutoBrokers' };

export default function CorredoresPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.seguradoras}
          title="Corredores"
          subtitle="Os fluxos de atendimento por seguradora e ramo. Ative os que sua corretora vai usar — sem ligar nada externo."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Corredores' }]}
        />
        <CorridorGalleryClient />
      </div>
    </div>
  );
}
