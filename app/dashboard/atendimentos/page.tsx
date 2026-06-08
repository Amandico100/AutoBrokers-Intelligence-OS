import { ModuleIndex } from '@/components/modules/ModuleIndex';
import { icons } from '@/lib/icons';
import { atendimentoAreas } from '@/lib/mock/tenant-modules';

export const metadata = { title: 'Atendimentos · AutoBrokers' };

export default function AtendimentosPage() {
  return (
    <ModuleIndex
      icon={icons.atendimentos}
      title="Atendimentos"
      description="Operação de filas, casos, conversas e segurados."
      areas={atendimentoAreas}
    />
  );
}
