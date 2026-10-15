import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { UsageClient } from './UsageClient';

export const metadata = { title: 'Custos e Uso · AutoBrokers' };

export default function CustosPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.cobranca}
          title="Custos e Uso"
          subtitle="Saldo e consumo reais da sua corretora, por agente e por modelo (últimos 30 dias)."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Custos e Uso' }]}
        />
        <UsageClient />
      </div>
    </div>
  );
}
