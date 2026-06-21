import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { AgentConfigClient } from '../AgentConfigClient';

export const metadata = { title: 'Even · AutoBrokers' };

export default function EvenAgentPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.atendimentos}
          title="Even — Atendimento"
          subtitle="Atende seus segurados no WhatsApp. Ajuste nome, voz, tom, horários e handoff. O envio externo só liga após conectar um canal."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Agentes', href: '/dashboard/personalizacao/agentes' }, { label: 'Even' }]}
        />
        <AgentConfigClient agentKey="even" />
      </div>
    </div>
  );
}
