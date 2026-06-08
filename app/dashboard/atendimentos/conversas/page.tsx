import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Conversas · Atendimentos' };

export default function ConversasPage() {
  return (
    <ModulePlaceholder
      icon={icons.conversas}
      title="Conversas"
      subtitle="Histórico de conversas por canal."
      breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Conversas' }]}
      description="As conversas de atendimento aparecerão aqui."
    />
  );
}
