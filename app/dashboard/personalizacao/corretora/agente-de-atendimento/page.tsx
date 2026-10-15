import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
// SPEC-139 (EXTRA-001.9): a página mudou de casa (era agentes/even); o formulário é o MESMO
// que o AutoBrokers usa — mora em agentes/ e é importado de lá, nunca copiado.
import { AgentConfigClient } from '../../agentes/AgentConfigClient';

export const metadata = { title: 'Agente de Atendimento · AutoBrokers' };

// SPEC-045: papel, nunca nome próprio — cada corretora batiza o seu agente.
export default function AttendanceAgentPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.atendimentos}
          title="Agente de Atendimento"
          subtitle="Quem atende seus segurados no WhatsApp. Dê um nome, ajuste o tom — e ligue quando quiser que ele assuma."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Corretora', href: '/dashboard/personalizacao/corretora' },
            { label: 'Agente de Atendimento' },
          ]}
        />
        <AgentConfigClient agentKey="even" />
      </div>
    </div>
  );
}
