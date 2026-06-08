import { DetailHeader, GalleryGrid, GalleryCard } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { seguradoras } from '@/lib/mock/tenant-modules';

export const metadata = { title: 'Seguradoras · AutoBrokers' };

export default function SeguradorasPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.seguradoras}
          title="Seguradoras"
          subtitle="Canais, portais e corredores por seguradora. Reutilizam os conectores da corretora."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Seguradoras' }]}
        />
        <GalleryGrid>
          {seguradoras.map((s) => (
            <GalleryCard
              key={s.key}
              icon={s.icon}
              title={s.title}
              description={s.description}
              status={s.status}
            />
          ))}
        </GalleryGrid>
      </div>
    </div>
  );
}
