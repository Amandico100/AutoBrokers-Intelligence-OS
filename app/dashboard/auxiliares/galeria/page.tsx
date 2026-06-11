'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, GalleryGrid, GalleryCard, DetailSection } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { fetchTemplates } from '@/lib/auxiliaries/api';
import type { AuxiliaryTemplate } from '@/lib/auxiliaries/types';
import { parseRuntimeConfig } from '@/lib/admin/auxiliary-runtime';

const SLUG_HREF: Record<string, string> = {
  'resumo-atendimentos': '/dashboard/auxiliares/galeria/resumo-atendimentos',
  'follow-up-whatsapp': '/dashboard/auxiliares/galeria/follow-up-whatsapp',
};
const SLUG_ICON: Record<string, typeof icons.auxiliares> = {
  'resumo-atendimentos': icons.auxiliares,
  'follow-up-whatsapp': icons.whatsapp,
};

const FUTURE = [
  { key: 'cobranca', icon: icons.cobranca, title: 'Cobrança Inteligente', description: 'Prepara lembretes de pagamento e boletos pendentes.', category: 'Financeiro' },
  { key: 'docs', icon: icons.documento, title: 'Conferência de Documentos', description: 'Verifica documentos faltantes em assistências e sinistros.', category: 'Documentos' },
];

// Auxiliares locais garantidos no catálogo (aparecem mesmo que o template ainda não exista no banco).
const LOCAL_TEMPLATES: AuxiliaryTemplate[] = [
  { id: 'resumo-atendimentos', slug: 'resumo-atendimentos', name: 'Resumo de Atendimentos', description: 'Resume conversas, destaca pendências e sugere próximos passos.', category: 'Análise' },
  { id: 'follow-up-whatsapp', slug: 'follow-up-whatsapp', name: 'Follow-up WhatsApp', description: 'Gera rascunhos de retorno e envia para aprovação humana (dry-run).', category: 'Comunicação' },
];

function mergeTemplates(db: AuxiliaryTemplate[]): AuxiliaryTemplate[] {
  const bySlug = new Map<string, AuxiliaryTemplate>();
  for (const t of db) if (t.slug) bySlug.set(t.slug, t);
  for (const l of LOCAL_TEMPLATES) if (!bySlug.has(l.slug)) bySlug.set(l.slug, l);
  return Array.from(bySlug.values());
}

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
        if (active) setTemplates(mergeTemplates(d.templates || []));
      })
      .catch(() => {
        if (active) setTemplates(LOCAL_TEMPLATES);
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
              const href = SLUG_HREF[t.slug] || `/dashboard/auxiliares/galeria/${t.slug}`;
              const rtKind = parseRuntimeConfig(t.default_config, t.slug).kind;
              const rtLabel =
                rtKind === 'smith_agent_blueprint'
                  ? 'Motor inteligente'
                  : rtKind === 'specific_executor'
                    ? 'Executor dedicado'
                    : rtKind === 'workflow'
                      ? 'Workflow'
                      : undefined;
              return (
                <GalleryCard
                  key={t.id || t.slug}
                  icon={SLUG_ICON[t.slug] || icons.auxiliares}
                  title={t.name || t.slug}
                  description={getStr(t, 'description') || 'Resume conversas, destaca pendências e sugere próximos passos.'}
                  category={getStr(t, 'category')}
                  tags={rtLabel ? [rtLabel] : undefined}
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
