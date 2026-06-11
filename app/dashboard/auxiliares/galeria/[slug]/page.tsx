'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

import { DetailHeader, DetailSection } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { fetchTemplates, fetchInstalled } from '@/lib/auxiliaries/api';
import type { AuxiliaryTemplate, TenantAuxiliary } from '@/lib/auxiliaries/types';
import { parseRuntimeConfig } from '@/lib/admin/auxiliary-runtime';

function str(v: unknown): string {
  return typeof v === 'string' ? v : '';
}

/** Detalhe genérico para Auxiliares sem página dedicada (ex.: runtime smith_agent). Nunca quebra. */
export default function AuxiliaryDetailPage() {
  const params = useParams();
  const slug = typeof params?.slug === 'string' ? params.slug : Array.isArray(params?.slug) ? params.slug[0] : '';
  const [template, setTemplate] = useState<AuxiliaryTemplate | null | undefined>(undefined);
  const [installed, setInstalled] = useState<TenantAuxiliary | null>(null);

  useEffect(() => {
    if (!slug) return;
    fetchTemplates()
      .then((d) => setTemplate((d.templates || []).find((t) => t.slug === slug) || null))
      .catch(() => setTemplate(null));
    fetchInstalled()
      .then((d) => setInstalled((d.installed || []).find((i) => i.slug === slug) || null))
      .catch(() => undefined);
  }, [slug]);

  const cfg = installed && typeof installed.config === 'object' ? (installed.config as Record<string, unknown>) : {};
  const tenantRt = cfg.runtime && typeof cfg.runtime === 'object' ? (cfg.runtime as Record<string, unknown>) : {};
  const hasAgent = typeof tenantRt.agent_id === 'string' && Boolean(tenantRt.agent_id);
  const rtKind = template ? parseRuntimeConfig(template.default_config, slug).kind : 'none';
  const title = template?.name || slug;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title={title}
          subtitle={str(template?.description) || 'Auxiliar da sua corretora.'}
          breadcrumb={[
            { label: 'Auxiliares', href: '/dashboard/auxiliares' },
            { label: 'Galeria', href: '/dashboard/auxiliares/galeria' },
            { label: title },
          ]}
        />

        {template === undefined ? (
          <DetailSection>
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          </DetailSection>
        ) : (
          <>
            <DetailSection title="Motor inteligente">
              {hasAgent ? (
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p className="flex items-center gap-2 text-foreground">
                    <Icon icon={icons.cadeado} size={16} className="text-primary" /> Motor inteligente vinculado
                  </p>
                  <p>
                    Este Auxiliar usa um motor inteligente (Agent) vinculado à sua corretora. A execução direta pelo
                    painel será habilitada em breve.
                  </p>
                </div>
              ) : rtKind === 'specific_executor' ? (
                <p className="text-sm text-muted-foreground">Executor dedicado — use a página específica do Auxiliar para executar.</p>
              ) : (
                <p className="text-sm text-muted-foreground">Em preparação. O runtime deste Auxiliar ainda será configurado.</p>
              )}
            </DetailSection>

            <DetailSection title="Resumo">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Instalado</dt>
                  <dd className="text-foreground">{installed ? 'Sim' : 'Não'}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Categoria</dt>
                  <dd className="text-foreground">{str(template?.category) || '—'}</dd>
                </div>
              </dl>
              <div className="mt-4">
                <Link href="/dashboard/auxiliares/meus" className="text-xs font-medium text-primary hover:underline">
                  ← Meus Auxiliares
                </Link>
              </div>
            </DetailSection>
          </>
        )}
      </div>
    </div>
  );
}
