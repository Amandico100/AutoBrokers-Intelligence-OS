import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Casos · Atendimentos' };

export default function CasosPage() {
  return (
    <ModulePlaceholder
      icon={icons.casos}
      title="Casos"
      subtitle="Detalhe, timeline e ações de cada atendimento."
      breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Casos' }]}
      description="Os casos de atendimento aparecerão aqui."
    />
  );
}
