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
          subtitle="Quanto a IA trabalhou para a sua corretora nos últimos 30 dias — por assistente e por modelo — e o que já foi cobrado."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Corretora', href: '/dashboard/personalizacao/corretora' },
            { label: 'Custos e Uso' },
          ]}
        />
        <UsageClient />
      </div>
    </div>
  );
}
