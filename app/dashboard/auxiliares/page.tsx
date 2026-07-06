'use client';

// SPEC-019 — Auxiliares = Rotinas (motor F2, o caminho ÚNICO). "Rotinas prontas"
// (galeria de modelos que a corretora liga com 1 clique) + "Minhas rotinas" (as
// suas, criadas por chat ou manualmente). O antigo fluxo de "instalar auxiliar"
// (blueprints) saiu do caminho da corretora — Blueprint Studio segue no Admin,
// só para AGENTES (atendente/core), não para rotinas.

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { GalleryGrid, GalleryCard } from '@/components/patterns';

export default function AuxiliaresPage() {
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
              Rotinas inteligentes que rodam sozinhas e entregam onde você pedir. Ligue uma pronta ou crie a sua.
            </p>
          </div>
        </div>

        <GalleryGrid>
          <GalleryCard
            icon={icons.auxiliares}
            title="Rotinas prontas"
            description="Modelos prontos (notícias do setor, resumo do dia, cobrança…). 'Usar modelo' já preenche — você só ajusta e salva."
            href="/dashboard/auxiliares/galeria"
            cta="Abrir galeria"
          />
          <GalleryCard
            icon={icons.historico}
            title="Minhas rotinas"
            description="As rotinas da sua corretora: criar/editar, pausar e ver as execuções. Crie pelo chat ('todo dia às 8h…') ou aqui."
            href="/dashboard/auxiliares/rotinas"
            cta="Abrir"
          />
        </GalleryGrid>
      </div>
    </div>
  );
}
