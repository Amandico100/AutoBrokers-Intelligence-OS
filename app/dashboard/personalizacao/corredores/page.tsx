import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { CorridorGalleryClient } from './CorridorGalleryClient';

export const metadata = { title: 'Corredores · AutoBrokers' };

export default function CorredoresPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        {/* SPEC-063 — um card por (seguradora × ramo), lido do CÓDIGO que
            executa o acionamento. O subtítulo diz o que o card entrega e o que
            ele não entrega: alguns corredores abrem o chamado, outros só
            encaminham, e ativar aqui não muda o que o motor sabe fazer. */}
        <DetailHeader
          icon={icons.seguradoras}
          title="Corredores"
          subtitle="Um corredor por seguradora e ramo, com os serviços que vão no pacote. Ative os que sua corretora usa — sem ligar nada externo."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Corredores' }]}
        />
        <CorridorGalleryClient />
      </div>
    </div>
  );
}
