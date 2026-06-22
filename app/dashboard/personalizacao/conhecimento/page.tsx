import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { KnowledgeClient } from './KnowledgeClient';

export const metadata = { title: 'Conhecimento · AutoBrokers' };

export default function ConhecimentoPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.conhecimento}
          title="Conhecimento"
          subtitle="Documentos e fontes privadas da sua corretora, com status real de processamento."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Conhecimento' }]}
        />
        <KnowledgeClient />
      </div>
    </div>
  );
}
