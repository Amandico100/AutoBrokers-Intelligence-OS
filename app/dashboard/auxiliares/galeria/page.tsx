import { DetailHeader, GalleryGrid, GalleryCard } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { auxiliaresGaleria } from '@/lib/mock/tenant-modules';

export const metadata = { title: 'Galeria de Auxiliares · AutoBrokers' };

export default function GaleriaAuxiliaresPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.galeria}
          title="Galeria de Auxiliares"
          subtitle="Modelos prontos para ativar na sua corretora."
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Galeria' }]}
        />
        <GalleryGrid>
          {auxiliaresGaleria.map((g) => (
            <GalleryCard
              key={g.key}
              icon={g.icon}
              title={g.title}
              description={g.description}
              category={g.category}
              status={g.status}
              cta={g.cta}
              href={g.href}
              disabled={!g.href}
            />
          ))}
        </GalleryGrid>
      </div>
    </div>
  );
}
