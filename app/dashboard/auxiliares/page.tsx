'use client';

import { useEffect, useState } from 'react';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { GalleryGrid, GalleryCard } from '@/components/patterns';
import { auxiliaresAreas, auxiliaresGaleria } from '@/lib/mock/tenant-modules';
import { fetchInstalled, fetchTemplates, fetchRuns } from '@/lib/auxiliaries/api';

export default function AuxiliaresPage() {
  const resumo = auxiliaresGaleria[0];
  const [counts, setCounts] = useState<{ installed?: number; templates?: number; runs?: number }>({});

  useEffect(() => {
    let active = true;
    Promise.allSettled([fetchInstalled(), fetchTemplates(), fetchRuns()]).then((rs) => {
      if (!active) return;
      const [inst, tpl, run] = rs;
      setCounts({
        installed: inst.status === 'fulfilled' ? inst.value.installed?.length : undefined,
        templates: tpl.status === 'fulfilled' ? tpl.value.templates?.length : undefined,
        runs: run.status === 'fulfilled' ? run.value.runs?.length : undefined,
      });
    });
    return () => {
      active = false;
    };
  }, []);

  const tagsFor = (key: string): string[] | undefined => {
    if (key === 'meus' && typeof counts.installed === 'number')
      return [`${counts.installed} ativo${counts.installed === 1 ? '' : 's'}`];
    if (key === 'galeria' && typeof counts.templates === 'number')
      return [`${counts.templates} modelo${counts.templates === 1 ? '' : 's'}`];
    if (key === 'execucoes' && typeof counts.runs === 'number')
      return [`${counts.runs} execuç${counts.runs === 1 ? 'ão' : 'ões'}`];
    return undefined;
  };

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
            <GalleryCard
              key={a.key}
              icon={a.icon}
              title={a.title}
              description={a.description}
              href={a.href}
              cta="Abrir"
              tags={tagsFor(a.key)}
            />
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
