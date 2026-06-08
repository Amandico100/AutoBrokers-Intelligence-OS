import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Corretora · AutoBrokers' };

export default function CorretoraPage() {
  return (
    <ModulePlaceholder
      icon={icons.corretora}
      title="Corretora"
      subtitle="Dados e identidade da corretora."
      breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Corretora' }]}
      description="As configurações da corretora aparecerão aqui."
    />
  );
}
