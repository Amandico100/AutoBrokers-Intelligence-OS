import { ModuleIndex } from '@/components/modules/ModuleIndex';
import { icons } from '@/lib/icons';
import { personalizacaoAreas } from '@/lib/mock/tenant-modules';

export const metadata = { title: 'Personalização · AutoBrokers' };

export default function PersonalizacaoPage() {
  return (
    <ModuleIndex
      icon={icons.personalizacao}
      title="Personalização"
      description="Conectores, seguradoras, conhecimento, corretora e equipe."
      areas={personalizacaoAreas}
    />
  );
}
