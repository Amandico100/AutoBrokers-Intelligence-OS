import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { ReadinessClient } from './ReadinessClient';

export const metadata = { title: 'Prontidão · AutoBrokers' };

export default function ProntidaoPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.casos}
          title="Prontidão"
          subtitle="O que já está pronto e o que falta para sua corretora colocar o atendimento no ar — em linguagem simples."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Prontidão' }]}
        />
        <ReadinessClient />
      </div>
    </div>
  );
}
