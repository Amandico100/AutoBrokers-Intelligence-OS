'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, GalleryGrid, GalleryCard, DetailSection } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { fetchTemplates } from '@/lib/auxiliaries/api';
import type { AuxiliaryTemplate } from '@/lib/auxiliaries/types';

const SLUG_HREF: Record<string, string> = {
  'resumo-atendimentos': '/dashboard/auxiliares/galeria/resumo-atendimentos',
};
const SLUG_ICON: Record<string, typeof icons.auxiliares> = {
  'resumo-atendimentos': icons.auxiliares,
};

const FUTURE = [
  { key: 'cobranca', icon: icons.cobranca, title: 'Cobrança Inteligente', description: 'Prepara lembretes de pagamento e boletos pendentes.', category: 'Financeiro' },
  { key: 'followup', icon: icons.enviar, title: 'Follow-up de Propostas', description: 'Identifica propostas paradas e sugere a próxima mensagem.', category: 'Comercial' },
  { key: 'docs', icon: icons.documento, title: 'Conferência de Documentos', description: 'Verifica documentos faltantes em assistências e sinistros.', category: 'Documentos' },
];

// Fallback estático garante que o card do Resumo exista mesmo se a API falhar.
const FALLBACK_TEMPLATES: AuxiliaryTemplate[] = [
  { id: 'resumo-atendimentos', slug: 'resumo-atendimentos', name: 'Resumo de Atendimentos' },
];

function getStr(obj: Record<string, unknown>, key: string): string | undefined {
  const v = obj[key];
  return typeof v === 'string' ? v : undefined;
}

export default function GaleriaAuxiliaresPage() {
  const [templates, setTemplates] = useState<AuxiliaryTemplate[] | null>(null);

  useEffect(() => {
    let active = true;
    fetchTemplates()
      .then((d) => {
        if (active) setTemplates(d.templates?.length ? d.templates : FALLBACK_TEMPLATES);
      })
      .catch(() => {
        if (active) setTemplates(FALLBACK_TEMPLATES);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-8 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.galeria}
          title="Galeria de Auxiliares"
          subtitle="Modelos prontos para ativar na sua corretora."
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Galeria' }]}
        />

        {templates === null ? (
          <DetailSection>
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          </DetailSection>
        ) : (
          <GalleryGrid>
            {templates.map((t) => {
              const href = SLUG_HREF[t.slug];
              return (
                <GalleryCard
                  key={t.id || t.slug}
                  icon={SLUG_ICON[t.slug] || icons.auxiliares}
                  title={t.name || t.slug}
                  description={getStr(t, 'description') || 'Resume conversas, destaca pendências e sugere próximos passos.'}
                  category={getStr(t, 'category')}
                  status={{ tone: 'success', label: 'Pronto para ativar' }}
                  cta="Ver detalhes"
                  href={href}
                  disabled={!href}
                />
              );
            })}
          </GalleryGrid>
        )}

        <div className="space-y-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-faint">Em breve</p>
          <GalleryGrid>
            {FUTURE.map((f) => (
              <GalleryCard
                key={f.key}
                icon={f.icon}
                title={f.title}
                description={f.description}
                category={f.category}
                status={{ tone: 'neutral', label: 'Em breve' }}
                cta="Em breve"
                disabled
              />
            ))}
          </GalleryGrid>
        </div>
      </div>
    </div>
  );
}
