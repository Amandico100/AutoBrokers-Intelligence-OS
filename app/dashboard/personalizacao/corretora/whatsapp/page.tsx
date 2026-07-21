import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';

import { WhatsAppHubClient } from './WhatsAppHubClient';

export const metadata = { title: 'WhatsApp da corretora · AutoBrokers' };

// SPEC-045 — números por FUNÇÃO, nunca por pessoa. Máximo 2 funções.
export default function WhatsAppHubPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.whatsapp}
          title="WhatsApp da corretora"
          subtitle="Números por função — nunca por pessoa. Um número só já atende tudo com segurança."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Corretora', href: '/dashboard/personalizacao/corretora' },
            { label: 'WhatsApp' },
          ]}
        />
        <WhatsAppHubClient />
      </div>
    </div>
  );
}
