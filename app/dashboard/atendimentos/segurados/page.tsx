import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Segurados · Atendimentos' };

export default function SeguradosPage() {
  return (
    <ModulePlaceholder
      icon={icons.equipe}
      title="Segurados"
      subtitle="Clientes e apólices da corretora."
      breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Segurados' }]}
      description="Os segurados aparecerão aqui."
    />
  );
}
