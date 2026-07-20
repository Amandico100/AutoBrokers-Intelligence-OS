import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

import { ConversasClient } from './ConversasClient';

export const metadata = { title: 'Conversas · Atendimentos' };

// SPEC-043: wrapper padrão do dashboard (mesmo respiro/alinhamento das demais
// páginas) + o client ocupa o restante da altura (mobile: tela cheia estilo
// WhatsApp — lista OU thread).
export default function ConversasPage() {
  return (
    <div className="flex h-full flex-col gap-3 px-3 pb-3 pt-4 sm:gap-4 sm:px-6 sm:pb-4 sm:pt-8">
      <div className="shrink-0">
        <DetailHeader
          icon={icons.conversas}
          title="Conversas"
          subtitle="Acompanhe o atendente IA em tempo real e assuma quando quiser."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Conversas' }]}
        />
      </div>
      <ConversasClient />
    </div>
  );
}
