import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { AgentConfigClient } from '../AgentConfigClient';

export const metadata = { title: 'AutoBrokers · AutoBrokers' };

export default function AutoBrokersAgentPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="AutoBrokers"
          subtitle="Seu chat principal interno. Personalize tom, idioma e identidade com segurança."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Agentes', href: '/dashboard/personalizacao/agentes' }, { label: 'AutoBrokers' }]}
        />
        <AgentConfigClient agentKey="autobrokers" />
      </div>
    </div>
  );
}
