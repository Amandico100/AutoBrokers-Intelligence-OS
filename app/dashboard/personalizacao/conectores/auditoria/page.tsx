'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, DetailSection, StatusPill } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { fetchAuditLog } from '@/lib/vault/api';
import type { VaultAuditLog } from '@/lib/vault/types';
import { riskPill, fmtDateTime } from '@/components/vault/labels';

const EVENT_LABELS: Record<string, string> = {
  connection_created: 'Conexão criada',
  connection_updated: 'Conexão atualizada',
  connection_tested: 'Conexão testada',
  connection_revoked: 'Conexão revogada',
  permission_granted: 'Permissão concedida',
  permission_revoked: 'Permissão revogada',
  approval_requested: 'Aprovação solicitada',
  approval_approved: 'Aprovação aprovada',
  approval_rejected: 'Aprovação rejeitada',
  action_executed: 'Ação executada',
  action_failed: 'Ação falhou',
};

export default function AuditoriaPage() {
  const [items, setItems] = useState<VaultAuditLog[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchAuditLog()
      .then((d) => setItems(d.events || []))
      .catch(() => setError(true));
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.historico}
          title="Auditoria"
          subtitle="Eventos recentes de conexões, permissões e aprovações da corretora."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Conectores', href: '/dashboard/personalizacao/conectores' },
            { label: 'Auditoria' },
          ]}
        />

        {error ? (
          <DetailSection>
            <p className="py-6 text-center text-sm text-muted-foreground">Não foi possível carregar a auditoria agora.</p>
          </DetailSection>
        ) : items === null ? (
          <DetailSection>
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          </DetailSection>
        ) : items.length === 0 ? (
          <DetailSection>
            <p className="py-8 text-center text-sm text-muted-foreground">Nenhum evento registrado ainda.</p>
          </DetailSection>
        ) : (
          <div className="space-y-2">
            {items.map((e) => {
              const rp = e.risk_level ? riskPill(e.risk_level) : null;
              return (
                <div key={e.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-4 py-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-foreground">
                        {EVENT_LABELS[e.event_type] || e.event_type}
                      </span>
                      {rp && <StatusPill tone={rp.tone} label={rp.label} />}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {[e.action, e.status].filter(Boolean).join(' · ') || '—'}
                    </p>
                  </div>
                  <span className="shrink-0 font-mono text-[10px] text-faint">{fmtDateTime(e.created_at)}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
