import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Fila · Atendimentos' };

export default function FilaPage() {
  return (
    <ModulePlaceholder
      icon={icons.fila}
      title="Fila"
      subtitle="Casos aguardando atendimento."
      breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Fila' }]}
      description="A fila de atendimentos aparecerá aqui."
    />
  );
}
