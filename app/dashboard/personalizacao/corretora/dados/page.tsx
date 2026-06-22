import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { CompanyProfileClient } from './CompanyProfileClient';

export const metadata = { title: 'Dados da Corretora · AutoBrokers' };

export default function CompanyProfilePage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.corretora}
          title="Dados da Corretora"
          subtitle="Identidade, contato e endereço da sua corretora. Usados pelo AutoBrokers nas apresentações."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Corretora', href: '/dashboard/personalizacao/corretora' }, { label: 'Dados' }]}
        />
        <CompanyProfileClient />
      </div>
    </div>
  );
}
