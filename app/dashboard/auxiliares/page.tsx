import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { GalleryGrid, GalleryCard } from '@/components/patterns';
import { auxiliaresAreas, auxiliaresGaleria } from '@/lib/mock/tenant-modules';

export const metadata = { title: 'Auxiliares · AutoBrokers' };

export default function AuxiliaresPage() {
  const resumo = auxiliaresGaleria[0];

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-8 px-4 py-10 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icons.auxiliares} size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Auxiliares</h1>
            <p className="text-sm text-muted-foreground">
              Automações e rotinas inteligentes da corretora.
            </p>
          </div>
        </div>

        <GalleryGrid>
          {auxiliaresAreas.map((a) => (
            <GalleryCard key={a.key} icon={a.icon} title={a.title} description={a.description} href={a.href} cta="Abrir" />
          ))}
        </GalleryGrid>

        <div className="space-y-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-faint">Primeiro auxiliar</p>
          <div className="sm:max-w-md">
            <GalleryCard
              icon={resumo.icon}
              title={resumo.title}
              description={resumo.description}
              category={resumo.category}
              status={resumo.status}
              cta={resumo.cta}
              href={resumo.href}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
