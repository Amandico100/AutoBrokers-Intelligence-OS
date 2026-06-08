'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, DetailSection, StatusPill } from '@/components/patterns';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import {
  fetchApprovalRequests,
  approveRequest,
  rejectRequest,
  createApprovalRequest,
  executeApproval,
  fetchTenantConnections,
  fetchConnectorTemplates,
} from '@/lib/vault/api';
import type { ApprovalRequest } from '@/lib/vault/types';
import { approvalStatusPill, riskPill, fmtDateTime } from '@/components/vault/labels';

const DEFAULT_TEST_MESSAGE = 'Olá, este é um teste seguro do AutoBrokers. Nenhuma mensagem será enviada.';

function str(v: unknown): string | undefined {
  return typeof v === 'string' && v.trim() ? v : undefined;
}

function previewOf(a: ApprovalRequest): { titulo?: string; mensagem?: string; toNumber?: string } {
  const p = a.preview && typeof a.preview === 'object' ? (a.preview as Record<string, unknown>) : {};
  const rp = a.request_payload && typeof a.request_payload === 'object' ? (a.request_payload as Record<string, unknown>) : {};
  return {
    titulo: str(p.titulo),
    mensagem: str(p.mensagem) || str(p.message) || str(rp.message),
    toNumber: str(p.to_number) || str(rp.to_number),
  };
}

export default function AprovacoesPage() {
  const [items, setItems] = useState<ApprovalRequest[] | null>(null);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [waConn, setWaConn] = useState<{ id: string; name: string } | null>(null);
  const [testPhone, setTestPhone] = useState('');
  const [creating, setCreating] = useState(false);

  const load = () => {
    setError(false);
    fetchApprovalRequests()
      .then((d) => setItems(d.approvals || []))
      .catch(() => setError(true));
  };

  useEffect(() => {
    load();
    // Resolve a conexão WhatsApp conectada (para vincular a aprovação de teste).
    Promise.all([fetchConnectorTemplates(), fetchTenantConnections()])
      .then(([t, c]) => {
        const waTemplate = (t.templates || []).find((x) => x.slug === 'whatsapp_zapi');
        if (!waTemplate) return;
        const conn = (c.connections || []).find(
          (x) =>
            x.connector_template_id === waTemplate.id &&
            (x.status === 'connected' || Boolean(x.technical_ref_id)),
        );
        if (conn) setWaConn({ id: conn.id, name: conn.name });
      })
      .catch(() => undefined);
  }, []);

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

  const execute = async (id: string) => {
    setBusyId(id);
    try {
      const res = await executeApproval(id);
      setNotice(res.message || res.error || (res.success ? 'Simulação executada.' : 'Não foi possível executar.'));
      load();
    } catch {
      setNotice('Erro ao executar a simulação.');
    } finally {
      setBusyId(null);
    }
  };

  const createTest = async () => {
    if (!waConn) {
      setNotice('Configure uma conexão WhatsApp em Conectores primeiro.');
      return;
    }
    const phone = testPhone.trim();
    if (!phone) {
      setNotice('Informe um telefone de destino para a simulação.');
      return;
    }
    setCreating(true);
    try {
      const res = await createApprovalRequest({
        tenant_connection_id: waConn.id,
        subject_type: 'tenant_auxiliary',
        action_type: 'whatsapp_send_message_dry_run',
        risk_level: 'medium',
        preview: { titulo: 'Mensagem WhatsApp em simulação', to_number: phone, message: DEFAULT_TEST_MESSAGE },
        request_payload: { to_number: phone, message: DEFAULT_TEST_MESSAGE, dry_run: true },
      });
      if (res.approval) {
        setNotice('Aprovação de teste criada.');
        setTestPhone('');
        load();
      } else {
        setNotice(res.error || 'Não foi possível criar a aprovação.');
      }
    } catch {
      setNotice('Erro ao criar aprovação de teste.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.aprovacao}
          title="Aprovações"
          subtitle="Aprovação humana (HITL) → execução controlada → provider WhatsApp → auditoria."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Conectores', href: '/dashboard/personalizacao/conectores' },
            { label: 'Aprovações' },
          ]}
        />

        <div className="flex items-start gap-2 rounded-lg border border-dashed border-primary/50 bg-brand-soft p-3 text-xs text-foreground-2">
          <Icon icon={icons.cadeado} size={16} className="mt-0.5 shrink-0 text-primary" />
          <span>
            Execução em <span className="font-medium text-foreground">modo seguro (dry-run)</span>: nenhuma mensagem
            real será enviada. Aprovar libera apenas a simulação pelo provider.
          </span>
        </div>

        {/* Criar aprovação de teste WhatsApp dry-run */}
        <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
          <p className="text-sm font-medium text-foreground">Criar aprovação de teste (WhatsApp dry-run)</p>
          {waConn ? (
            <>
              <p className="text-xs text-muted-foreground">
                Conexão: <span className="text-foreground-2">{waConn.name}</span>. Nenhuma mensagem real será enviada.
              </p>
              <div className="flex flex-wrap items-end gap-2">
                <div className="space-y-1">
                  <Label htmlFor="test-phone" className="text-xs text-foreground">Telefone de destino</Label>
                  <Input
                    id="test-phone"
                    value={testPhone}
                    onChange={(e) => setTestPhone(e.target.value)}
                    placeholder="5547999999999"
                    className="h-9 w-52 bg-background"
                  />
                </div>
                <Button size="sm" onClick={createTest} disabled={creating}>
                  <Icon icon={icons.novaConversa} size={14} className="mr-2" />
                  {creating ? 'Criando…' : 'Criar aprovação de teste'}
                </Button>
              </div>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">
              Configure uma conexão WhatsApp em{' '}
              <span className="text-foreground-2">Conectores</span> para criar uma simulação.
            </p>
          )}
        </div>

        {notice && (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-foreground-2">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice('')} className="text-faint hover:text-foreground">
              <Icon icon={icons.negado} size={14} />
            </button>
          </div>
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
              const errMsg = typeof a.error_message === 'string' ? a.error_message : undefined;
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
                  {(pv.titulo || pv.mensagem || pv.toNumber) && (
                    <div className="mt-2 rounded-lg border border-border-soft bg-surface-2 p-3">
                      {pv.titulo && <p className="text-xs font-medium text-foreground">{pv.titulo}</p>}
                      {pv.toNumber && <p className="mt-0.5 text-xs text-muted-foreground">Para: {pv.toNumber}</p>}
                      {pv.mensagem && <p className="mt-0.5 text-xs text-muted-foreground">{pv.mensagem}</p>}
                    </div>
                  )}

                  {a.status === 'pending' && (
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

                  {a.status === 'approved' && (
                    <div className="mt-3 space-y-2">
                      <p className="text-[11px] text-muted-foreground">
                        Esta execução está em modo seguro: nenhuma mensagem real será enviada.
                      </p>
                      <Button size="sm" onClick={() => execute(a.id)} disabled={busyId === a.id}>
                        <Icon icon={icons.whatsapp} size={14} className="mr-2" />
                        {busyId === a.id ? 'Executando…' : 'Executar simulação'}
                      </Button>
                    </div>
                  )}

                  {a.status === 'executed' && (
                    <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-success">
                      <Icon icon={icons.success} size={14} /> Simulação executada — nenhuma mensagem foi enviada.
                    </p>
                  )}

                  {a.status === 'failed' && (
                    <p className="mt-3 text-xs text-danger">{errMsg || 'Falha ao executar a simulação.'}</p>
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
