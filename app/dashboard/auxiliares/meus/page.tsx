'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

import { DetailHeader, GalleryGrid, GalleryCard, DetailSection, type StatusTone } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { fetchInstalled } from '@/lib/auxiliaries/api';
import type { TenantAuxiliary } from '@/lib/auxiliaries/types';
import { auxiliaryContractBadges } from '@/lib/auxiliaries/contract';

const TITLES: Record<string, string> = {
  'resumo-atendimentos': 'Resumo de Atendimentos',
  'follow-up-whatsapp': 'Follow-up WhatsApp',
};
const DESCS: Record<string, string> = {
  'resumo-atendimentos': 'Resume conversas, destaca pendências e sugere próximos passos.',
  'follow-up-whatsapp': 'Gera rascunhos de retorno e envia para aprovação humana (dry-run).',
};
const HREFS: Record<string, string> = {
  'resumo-atendimentos': '/dashboard/auxiliares/galeria/resumo-atendimentos',
  'follow-up-whatsapp': '/dashboard/auxiliares/galeria/follow-up-whatsapp',
};

function installedStatus(s?: string): { tone: StatusTone; label: string } {
  switch (s) {
    case 'active':
      return { tone: 'success', label: 'Ativo' };
    case 'paused':
      return { tone: 'neutral', label: 'Pausado' };
    case 'needs_config':
      return { tone: 'warning', label: 'Precisa configurar' };
    case 'error':
      return { tone: 'danger', label: 'Com erro' };
    default:
      return { tone: 'neutral', label: s || 'Inativo' };
  }
}

function getStr(obj: Record<string, unknown>, key: string): string | undefined {
  const v = obj[key];
  return typeof v === 'string' ? v : undefined;
}

function fmtDateShort(s?: string): string | undefined {
  if (!s) return undefined;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? undefined : d.toLocaleDateString('pt-BR');
}

const KNOWN_EXECUTORS = ['resumo-atendimentos', 'follow-up-whatsapp'];

/** Badge discreto de runtime para a corretora (sem jargão técnico). */
function tenantRuntimeLabel(it: TenantAuxiliary): string {
  const cfg = it.config && typeof it.config === 'object' ? (it.config as Record<string, unknown>) : {};
  const rt = cfg.runtime && typeof cfg.runtime === 'object' ? (cfg.runtime as Record<string, unknown>) : {};
  if (typeof rt.agent_id === 'string' && rt.agent_id) return 'Motor inteligente vinculado';
  if (rt.kind === 'specific_executor' || KNOWN_EXECUTORS.includes(it.slug)) return 'Executor dedicado';
  return 'Em preparação';
}

export default function MeusAuxiliaresPage() {
  const [items, setItems] = useState<TenantAuxiliary[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    fetchInstalled()
      .then((d) => {
        if (active) setItems(d.installed || []);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="Meus Auxiliares"
          subtitle="Auxiliares ativados pela sua corretora."
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Meus Auxiliares' }]}
        />

        {error ? (
          <DetailSection>
            <p className="py-8 text-center text-sm text-muted-foreground">
              Não foi possível carregar seus Auxiliares agora. Tente novamente em alguns instantes.
            </p>
          </DetailSection>
        ) : items === null ? (
          <DetailSection>
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          </DetailSection>
        ) : items.length === 0 ? (
          <DetailSection>
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
                <Icon icon={icons.auxiliares} size={18} />
              </span>
              <p className="text-sm font-medium text-foreground">Você ainda não ativou nenhum Auxiliar.</p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Escolha um modelo pronto na Galeria e coloque o AutoBrokers para trabalhar por você.
              </p>
              <Link
                href="/dashboard/auxiliares/galeria"
                className="mt-1 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                <Icon icon={icons.galeria} size={16} />
                Ver galeria
              </Link>
            </div>
          </DetailSection>
        ) : (
          <GalleryGrid>
            {items.map((it) => {
              const slug = it.slug;
              const title = getStr(it, 'display_name') || TITLES[slug] || slug || 'Auxiliar';
              const created = fmtDateShort(getStr(it, 'created_at'));
              const tags = Array.from(
                new Set(
                  [
                    ...auxiliaryContractBadges(it).slice(0, 3),
                    tenantRuntimeLabel(it),
                    created ? `criado ${created}` : undefined,
                  ].filter((t): t is string => Boolean(t)),
                ),
              );
              const href = HREFS[slug] || `/dashboard/auxiliares/galeria/${slug}`;
              return (
                <GalleryCard
                  key={it.id}
                  icon={icons.auxiliares}
                  title={title}
                  description={DESCS[slug] || 'Auxiliar ativado pela corretora.'}
                  status={installedStatus(it.status)}
                  tags={tags}
                  cta={href ? 'Abrir' : 'Em breve'}
                  href={href}
                  disabled={!href}
                />
              );
            })}
          </GalleryGrid>
        )}
      </div>
    </div>
  );
}
