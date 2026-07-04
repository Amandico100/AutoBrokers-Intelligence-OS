import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

import { ConversasClient } from './ConversasClient';

export const metadata = { title: 'Conversas · Atendimentos' };

export default function ConversasPage() {
  return (
    <div className="space-y-4">
      <DetailHeader
        icon={icons.conversas}
        title="Conversas"
        subtitle="Acompanhe o atendente IA em tempo real e assuma quando quiser."
        breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Conversas' }]}
      />
      <ConversasClient />
    </div>
  );
}
