import { DetailHeader, GalleryGrid, GalleryCard } from '@/components/patterns';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Agentes · AutoBrokers' };

export default function AgentesPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="Agentes"
          subtitle="Personalize os agentes da sua corretora. O AutoBrokers é o chat interno; a Even atende seus segurados."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Agentes' }]}
        />
        <GalleryGrid>
          <GalleryCard
            icon={icons.auxiliares}
            title="AutoBrokers"
            description="Seu chat principal interno. Apresenta-se como “AutoBrokers da sua corretora”. Ajuste tom, idioma e contexto."
            status={{ tone: 'success', label: 'Ativo' }}
            cta="Personalizar"
            href="/dashboard/personalizacao/agentes/autobrokers"
          />
          <GalleryCard
            icon={icons.atendimentos}
            title="Even — Atendimento"
            description="Atende seus segurados (assistência e sinistro) no WhatsApp. Ajuste nome, voz, tom, horários e handoff."
            status={{ tone: 'info', label: 'Provisionada' }}
            cta="Personalizar"
            href="/dashboard/personalizacao/agentes/even"
          />
        </GalleryGrid>
      </div>
    </div>
  );
}
