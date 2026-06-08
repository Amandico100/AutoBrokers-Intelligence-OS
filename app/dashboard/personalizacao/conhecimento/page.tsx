import { ModulePlaceholder } from '@/components/modules/ModulePlaceholder';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Conhecimento · AutoBrokers' };

export default function ConhecimentoPage() {
  return (
    <ModulePlaceholder
      icon={icons.conhecimento}
      title="Conhecimento"
      subtitle="Documentos, memórias e fontes da corretora."
      breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Conhecimento' }]}
      description="A biblioteca de conhecimento aparecerá aqui."
    />
  );
}
