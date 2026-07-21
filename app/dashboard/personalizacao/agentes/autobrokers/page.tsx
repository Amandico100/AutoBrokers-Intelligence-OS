import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { AgentConfigClient } from '../AgentConfigClient';

export const metadata = { title: 'AutoBrokers — Chat Principal' };

export default function AutoBrokersAgentPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="AutoBrokers — Chat Principal"
          subtitle="O copiloto interno da sua corretora."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'AutoBrokers' },
          ]}
        />

        {/* SPEC-045: o corretor precisa entender O QUE é o AutoBrokers */}
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm font-semibold text-foreground">O que é o AutoBrokers?</p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            É o <span className="font-medium text-foreground">Chat Principal</span> — o assistente
            interno que toda a equipe usa. Ele consulta apólices e clientes na InfoCap, enxerga os
            atendimentos e acionamentos em andamento, usa o conhecimento da corretora (e o global da
            plataforma), cria rotinas automáticas e responde o que o corretor precisar para operar.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Suas conversas com ele são <span className="font-medium text-foreground">suas</span> —
            cada pessoa da equipe tem o próprio histórico. A inteligência e as conexões são da
            corretora, compartilhadas por todos.
          </p>
        </div>

        <AgentConfigClient agentKey="autobrokers" />
      </div>
    </div>
  );
}
