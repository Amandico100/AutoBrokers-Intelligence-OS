import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Execuções · Auxiliares' };

export default function ExecucoesPage() {
  return (
    <ModulePlaceholder
      icon={icons.historico}
      title="Execuções"
      subtitle="Histórico do que os Auxiliares fizeram (custo, duração e resultado)."
      breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Execuções' }]}
      description="Nenhuma execução ainda."
    />
  );
}
