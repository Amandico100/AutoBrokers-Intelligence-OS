'use client';

import { useState } from 'react';

import { DetailHeader, GalleryGrid, GalleryCard, PermissionModal } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { conectores, connectorPermissions, type GalleryItem } from '@/lib/mock/tenant-modules';

export default function ConectoresPage() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<GalleryItem | null>(null);

  const openFor = (c: GalleryItem) => {
    setActive(c);
    setOpen(true);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.conectores}
          title="Conectores"
          subtitle="Integrações reutilizáveis por Atendimentos, Auxiliares e AutoBrokers."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Conectores' }]}
        />

        <GalleryGrid>
          {conectores.map((c) => (
            <GalleryCard
              key={c.key}
              icon={c.icon}
              title={c.title}
              description={c.description}
              category={c.category}
              status={c.status}
              cta="Conectar"
              onClick={() => openFor(c)}
            />
          ))}
        </GalleryGrid>

        <PermissionModal
          open={open}
          onOpenChange={setOpen}
          icon={active?.icon ?? icons.conectores}
          title={active ? `Conectar ${active.title} ao AutoBrokers` : 'Conectar'}
          description="Defina o que o AutoBrokers poderá fazer com esta conexão."
          groups={connectorPermissions}
          requiresHumanApproval
          confirmLabel="Permitir e continuar"
        />
      </div>
    </div>
  );
}
