'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

import { cn } from '@/lib/utils';
import { DetailHeader, DetailSection, GalleryGrid, GalleryCard, StatusPill } from '@/components/patterns';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import {
  fetchConnectorTemplates,
  fetchTenantConnections,
  createApprovalRequest,
} from '@/lib/vault/api';
import type { ConnectorTemplate, TenantConnection } from '@/lib/vault/types';
import { CreateConnectionModal } from '@/components/vault/CreateConnectionModal';
import { PermissionGrantPanel } from '@/components/vault/PermissionGrantPanel';
import { riskPill, connectionStatusPill, slugIcon, fmtDateTime } from '@/components/vault/labels';

type Tab = 'catalog' | 'connections';

function Loading() {
  return (
    <DetailSection>
      <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
        <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
      </div>
    </DetailSection>
  );
}

export default function ConectoresPage() {
  const [tab, setTab] = useState<Tab>('catalog');
  const [templates, setTemplates] = useState<ConnectorTemplate[] | null>(null);
  const [connections, setConnections] = useState<TenantConnection[] | null>(null);
  const [error, setError] = useState(false);
  const [modalTemplate, setModalTemplate] = useState<ConnectorTemplate | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [openConnId, setOpenConnId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const loadConnections = () =>
    fetchTenantConnections()
      .then((d) => setConnections(d.connections || []))
      .catch(() => setError(true));

  useEffect(() => {
    fetchConnectorTemplates()
      .then((d) => setTemplates(d.templates || []))
      .catch(() => setError(true));
    loadConnections();
  }, []);

  const openCreate = (t: ConnectorTemplate) => {
    setModalTemplate(t);
    setModalOpen(true);
  };

  const onCreated = () => {
    setNotice('Conexão preparada em modo rascunho.');
    setTab('connections');
    loadConnections();
  };

  const createTestApproval = async (conn: TenantConnection) => {
    try {
      const res = await createApprovalRequest({
        tenant_connection_id: conn.id,
        subject_type: 'tenant_auxiliary',
        action_type: 'whatsapp_draft_message',
        risk_level: 'medium',
        preview: {
          titulo: 'Rascunho de mensagem',
          mensagem: 'Olá, este é um rascunho de teste. Nenhuma mensagem será enviada.',
        },
        request_payload: { dry_run: true },
      });
      setNotice(res.approval ? 'Aprovação de teste criada. Veja em Aprovações.' : res.error || 'Não foi possível criar a aprovação.');
    } catch {
      setNotice('Erro ao criar aprovação de teste.');
    }
  };

  const tabButton = (value: Tab, label: string) => (
    <button
      type="button"
      onClick={() => setTab(value)}
      className={cn(
        'rounded-full border px-3 py-1 text-xs transition-colors',
        tab === value ? 'border-primary/40 bg-brand-soft text-primary' : 'border-border text-muted-foreground hover:text-foreground',
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.conectores}
          title="Conectores"
          subtitle="Conecte serviços e autorize o uso seguro por AutoBrokers, Auxiliares e Atendimentos."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Conectores' }]}
          actions={
            <div className="flex items-center gap-2">
              <Link
                href="/dashboard/personalizacao/conectores/aprovacoes"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-primary/40"
              >
                <Icon icon={icons.aprovacao} size={14} />
                Aprovações
              </Link>
              <Link
                href="/dashboard/personalizacao/conectores/auditoria"
                className="text-xs font-medium text-primary hover:underline"
              >
                Auditoria
              </Link>
            </div>
          }
        />

        {notice && (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-success/40 bg-surface-2 px-3 py-2 text-xs text-foreground-2">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice('')} className="text-faint hover:text-foreground">
              <Icon icon={icons.negado} size={14} />
            </button>
          </div>
        )}

        <div className="flex gap-1.5">
          {tabButton('catalog', 'Catálogo')}
          {tabButton('connections', 'Minhas conexões')}
        </div>

        {error && (
          <DetailSection>
            <p className="py-6 text-center text-sm text-muted-foreground">
              Não foi possível carregar os conectores agora. Tente novamente em alguns instantes.
            </p>
          </DetailSection>
        )}

        {tab === 'catalog' &&
          (templates === null ? (
            <Loading />
          ) : (
            <GalleryGrid>
              {templates.map((t) => (
                <GalleryCard
                  key={t.id}
                  icon={slugIcon(t.slug)}
                  title={t.name}
                  description={typeof t.description === 'string' ? t.description : undefined}
                  category={t.category}
                  status={riskPill(t.risk_level)}
                  tags={[t.auth_type]}
                  cta="Preparar conexão"
                  onClick={() => openCreate(t)}
                />
              ))}
            </GalleryGrid>
          ))}

        {tab === 'connections' &&
          (connections === null ? (
            <Loading />
          ) : connections.length === 0 ? (
            <DetailSection>
              <div className="py-10 text-center">
                <p className="text-sm font-medium text-foreground">Nenhuma conexão ainda.</p>
                <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
                  Vá ao Catálogo e prepare uma conexão (modo rascunho, sem credenciais).
                </p>
                <Button className="mt-4" variant="outline" onClick={() => setTab('catalog')}>
                  Ver catálogo
                </Button>
              </div>
            </DetailSection>
          ) : (
            <div className="space-y-3">
              {connections.map((c) => {
                const open = openConnId === c.id;
                const sp = connectionStatusPill(c.status);
                return (
                  <div key={c.id} className="rounded-xl border border-border bg-surface">
                    <div className="flex items-start justify-between gap-3 p-4">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-foreground">{c.name}</span>
                          <StatusPill tone={sp.tone} label={sp.label} />
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {fmtDateTime(c.created_at)}
                          {c.health_status ? ` · saúde: ${c.health_status}` : ''}
                        </p>
                      </div>
                      <Button size="sm" variant="outline" onClick={() => setOpenConnId(open ? null : c.id)}>
                        {open ? 'Fechar' : 'Permissões'}
                      </Button>
                    </div>
                    {open && (
                      <div className="space-y-4 border-t border-border p-4">
                        <PermissionGrantPanel connectionId={c.id} />
                        <div className="flex flex-wrap items-center gap-2 border-t border-border-soft pt-3">
                          <Button size="sm" variant="outline" onClick={() => createTestApproval(c)}>
                            <Icon icon={icons.aprovacao} size={14} className="mr-2" />
                            Criar aprovação de teste
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
      </div>

      <CreateConnectionModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        template={modalTemplate}
        onCreated={onCreated}
      />
    </div>
  );
}
