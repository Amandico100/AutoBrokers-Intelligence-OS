'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, DetailSection, StatusPill } from '@/components/patterns';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import {
  fetchApprovalRequests,
  approveRequest,
  rejectRequest,
  createApprovalRequest,
} from '@/lib/vault/api';
import type { ApprovalRequest } from '@/lib/vault/types';
import { approvalStatusPill, riskPill, fmtDateTime } from '@/components/vault/labels';

function previewOf(a: ApprovalRequest): { titulo?: string; mensagem?: string } {
  const p = a.preview && typeof a.preview === 'object' ? (a.preview as Record<string, unknown>) : {};
  return {
    titulo: typeof p.titulo === 'string' ? p.titulo : undefined,
    mensagem: typeof p.mensagem === 'string' ? p.mensagem : undefined,
  };
}

export default function AprovacoesPage() {
  const [items, setItems] = useState<ApprovalRequest[] | null>(null);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const load = () => {
    setError(false);
    fetchApprovalRequests()
      .then((d) => setItems(d.approvals || []))
      .catch(() => setError(true));
  };

  useEffect(load, []);

  const act = async (id: string, kind: 'approve' | 'reject') => {
    setBusyId(id);
    try {
      const res = kind === 'approve' ? await approveRequest(id) : await rejectRequest(id);
      if (res.approval) load();
      else setNotice(res.error || 'Não foi possível atualizar o pedido.');
    } catch {
      setNotice('Erro ao atualizar o pedido.');
    } finally {
      setBusyId(null);
    }
  };

  const createTest = async () => {
    try {
      const res = await createApprovalRequest({
        subject_type: 'tenant_auxiliary',
        action_type: 'whatsapp_draft_message',
        risk_level: 'medium',
        preview: {
          titulo: 'Rascunho de mensagem',
          mensagem: 'Olá, este é um rascunho de teste. Nenhuma mensagem será enviada.',
        },
        request_payload: { dry_run: true },
      });
      setNotice(res.approval ? 'Aprovação de teste criada.' : res.error || 'Não foi possível criar.');
      if (res.approval) load();
    } catch {
      setNotice('Erro ao criar aprovação de teste.');
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.aprovacao}
          title="Aprovações"
          subtitle="Aprovação humana (HITL) antes de qualquer ação externa."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Conectores', href: '/dashboard/personalizacao/conectores' },
            { label: 'Aprovações' },
          ]}
          actions={
            <Button size="sm" variant="outline" onClick={createTest}>
              <Icon icon={icons.novaConversa} size={14} className="mr-2" />
              Criar aprovação de teste
            </Button>
          }
        />

        <div className="flex items-start gap-2 rounded-lg border border-dashed border-primary/50 bg-brand-soft p-3 text-xs text-foreground-2">
          <Icon icon={icons.aprovacao} size={16} className="mt-0.5 shrink-0 text-primary" />
          <span>
            Nesta fase, aprovar uma solicitação <span className="font-medium text-foreground">não executa</span> ação
            externa. Este fluxo valida o HITL antes de habilitar conectores reais.
          </span>
        </div>

        {notice && (
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-foreground-2">{notice}</div>
        )}

        {error ? (
          <DetailSection>
            <p className="py-6 text-center text-sm text-muted-foreground">Não foi possível carregar as aprovações agora.</p>
          </DetailSection>
        ) : items === null ? (
          <DetailSection>
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          </DetailSection>
        ) : items.length === 0 ? (
          <DetailSection>
            <p className="py-8 text-center text-sm text-muted-foreground">Nenhum pedido de aprovação ainda.</p>
          </DetailSection>
        ) : (
          <div className="space-y-3">
            {items.map((a) => {
              const sp = approvalStatusPill(a.status);
              const rp = riskPill(a.risk_level);
              const pv = previewOf(a);
              const pending = a.status === 'pending';
              return (
                <div key={a.id} className="rounded-xl border border-border bg-surface p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-foreground">{a.action_type}</span>
                    <StatusPill tone={sp.tone} label={sp.label} />
                    <StatusPill tone={rp.tone} label={rp.label} />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {a.subject_type} · {fmtDateTime(a.created_at)}
                  </p>
                  {(pv.titulo || pv.mensagem) && (
                    <div className="mt-2 rounded-lg border border-border-soft bg-surface-2 p-3">
                      {pv.titulo && <p className="text-xs font-medium text-foreground">{pv.titulo}</p>}
                      {pv.mensagem && <p className="mt-0.5 text-xs text-muted-foreground">{pv.mensagem}</p>}
                    </div>
                  )}
                  {pending && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button size="sm" onClick={() => act(a.id, 'approve')} disabled={busyId === a.id}>
                        <Icon icon={icons.success} size={14} className="mr-2" />
                        Aprovar
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => act(a.id, 'reject')} disabled={busyId === a.id}>
                        <Icon icon={icons.negado} size={14} className="mr-2" />
                        Rejeitar
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
