import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { ServicosClient } from './ServicosClient';

export const metadata = { title: 'Serviços · AutoBrokers' };

/**
 * SPEC-131-0 parte A · F4 — o manual de cada serviço (Cotação · Renovação · Quem Cobra Menos) e, no topo, a
 * configuração em 4 passos (D-131-0-07). Leitura e escrita pela rota `/api/dashboard/servicos`.
 */
export default function ServicosPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.auxiliares}
          title="Serviços"
          subtitle="O que o AutoBrokers faz em cada serviço: só calcular, calcular e entregar ao cliente, ou também negociar."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Serviços' }]}
        />
        <ServicosClient />
      </div>
    </div>
  );
}
