import { DetailHeader, GalleryGrid, GalleryCard } from '@/components/patterns';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Corretora · AutoBrokers' };

export default function CorretoraPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.corretora}
          title="Corretora"
          subtitle="Dados, identidade e configurações operacionais da corretora."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Corretora' }]}
        />
        <GalleryGrid>
          <GalleryCard
            icon={icons.atendimentos}
            title="Suporte humano"
            description="Destino para dossiês e transferências quando o agente precisar escalar um atendimento."
            status={{ tone: 'info', label: 'MVP ativo' }}
            cta="Configurar"
            href="/dashboard/personalizacao/corretora/suporte-humano"
          />
        </GalleryGrid>
      </div>
    </div>
  );
}
