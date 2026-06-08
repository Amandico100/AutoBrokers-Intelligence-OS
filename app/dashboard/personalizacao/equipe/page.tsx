import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Equipe · AutoBrokers' };

export default function EquipePage() {
  return (
    <ModulePlaceholder
      icon={icons.equipe}
      title="Equipe"
      subtitle="Usuários e permissões da corretora."
      breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Equipe' }]}
      description="A gestão de equipe aparecerá aqui."
    />
  );
}
