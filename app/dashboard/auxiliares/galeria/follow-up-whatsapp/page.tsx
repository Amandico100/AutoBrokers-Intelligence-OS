'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { DetailShell, DetailSection } from '@/components/patterns';
import { fetchResumoConversations, draftFollowUpWhatsapp } from '@/lib/auxiliaries/api';
import type { ResumoConversation } from '@/lib/auxiliaries/types';
import { createApprovalRequest, fetchConnectorTemplates, fetchTenantConnections, fetchPermissions } from '@/lib/vault/api';

type DraftState = 'idle' | 'loading' | 'error';

const TONES: { value: string; label: string }[] = [
  { value: 'profissional', label: 'Profissional' },
  { value: 'consultivo', label: 'Consultivo' },
  { value: 'direto', label: 'Direto' },
  { value: 'acolhedor', label: 'Acolhedor' },
];

function fmtDateShort(s?: string | null): string {
  if (!s) return '';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('pt-BR');
}

/** Extrai o telefone de um session_id de WhatsApp: `whatsapp:{phone}:{company}:{agent}`. */
function waPhone(sessionId?: string): string | undefined {
  if (sessionId && sessionId.startsWith('whatsapp:')) {
    const p = sessionId.split(':')[1];
    if (p && /^\d{8,15}$/.test(p)) return p;
  }
  return undefined;
}

function SelectorRow({
  active,
  onClick,
  title,
  subtitle,
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  subtitle?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-colors',
        active ? 'border-primary/50 bg-brand-soft' : 'border-border hover:border-primary/30 hover:bg-surface-2',
      )}
    >
      <div className="min-w-0">
        <p className="truncate text-sm text-foreground">{title}</p>
        {subtitle && <p className="truncate text-[11px] text-muted-foreground">{subtitle}</p>}
      </div>
      <span className={cn('h-3.5 w-3.5 shrink-0 rounded-full border', active ? 'border-primary bg-primary' : 'border-border')} />
    </button>
  );
}

export default function FollowUpWhatsappPage() {
  const [convs, setConvs] = useState<ResumoConversation[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phone, setPhone] = useState('');
  const [objective, setObjective] = useState('');
  const [tone, setTone] = useState('profissional');
  const [draftState, setDraftState] = useState<DraftState>('idle');
  const [errorKind, setErrorKind] = useState<'generic' | 'credits'>('generic');
  const [errorMsg, setErrorMsg] = useState('');
  const [message, setMessage] = useState('');
  const [generated, setGenerated] = useState(false);
  const [waConn, setWaConn] = useState<{ id: string; name: string } | null>(null);
  const [permWarning, setPermWarning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdApproval, setCreatedApproval] = useState<{ id: string; status: string } | null>(null);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    fetchResumoConversations()
      .then((d) => setConvs(d.conversations || []))
      .catch(() => setConvs([]));
    Promise.all([fetchConnectorTemplates(), fetchTenantConnections()])
      .then(([t, c]) => {
        const wa = (t.templates || []).find((x) => x.slug === 'whatsapp_zapi');
        if (!wa) return;
        const conn = (c.connections || []).find(
          (x) => x.connector_template_id === wa.id && (x.status === 'connected' || Boolean(x.technical_ref_id)),
        );
        if (!conn) return;
        setWaConn({ id: conn.id, name: conn.name });
        // Verificação de permissão (não bloqueia o MVP).
        fetchPermissions(conn.id)
          .then((p) => {
            const ok = (p.permissions || []).some((g) => {
              const actions = Array.isArray(g.allowed_actions) ? (g.allowed_actions as string[]) : [];
              return (
                g.status === 'active' &&
                ['tenant_auxiliary', 'autobrokers'].includes(g.subject_type) &&
                (actions.includes('draft_message') || actions.includes('send_message'))
              );
            });
            setPermWarning(!ok);
          })
          .catch(() => setPermWarning(true));
      })
      .catch(() => undefined);
  }, []);

  const selectConversation = (c: ResumoConversation | null) => {
    setSelectedId(c?.id ?? null);
    const extracted = waPhone(c?.session_id);
    if (extracted) setPhone(extracted);
  };

  const generate = async () => {
    setDraftState('loading');
    setErrorMsg('');
    setErrorKind('generic');
    setCreatedApproval(null);
    setNotice('');
    try {
      const res = await draftFollowUpWhatsapp({ conversationId: selectedId ?? undefined, objective, tone });
      if (res.success && res.draft?.message) {
        setMessage(res.draft.message);
        setGenerated(true);
        setDraftState('idle');
      } else if (res.error === 'insufficient_credits') {
        setErrorKind('credits');
        setErrorMsg(res.message || 'Sua corretora não possui créditos suficientes para executar este auxiliar.');
        setDraftState('error');
      } else {
        setErrorMsg('Não foi possível gerar o rascunho agora. Tente novamente em alguns instantes.');
        setDraftState('error');
      }
    } catch {
      setErrorMsg('Não foi possível gerar o rascunho agora. Tente novamente em alguns instantes.');
      setDraftState('error');
    }
  };

  const createApproval = async () => {
    if (!waConn) {
      setNotice('Configure uma conexão WhatsApp em Conectores antes de criar a aprovação.');
      return;
    }
    const to = phone.trim();
    const msg = message.trim();
    if (!to) {
      setNotice('Informe o telefone de destino.');
      return;
    }
    if (!msg) {
      setNotice('Gere ou escreva a mensagem antes de criar a aprovação.');
      return;
    }
    setCreating(true);
    setNotice('');
    try {
      const res = await createApprovalRequest({
        tenant_connection_id: waConn.id,
        subject_type: 'tenant_auxiliary',
        action_type: 'whatsapp_send_message_dry_run',
        risk_level: 'medium',
        preview: { titulo: 'Follow-up WhatsApp', to_number: to, message: msg },
        request_payload: { to_number: to, message: msg, dry_run: true, source: 'auxiliary_follow_up_whatsapp' },
      });
      if (res.approval) {
        setCreatedApproval({ id: res.approval.id, status: res.approval.status });
      } else {
        setNotice(res.error || 'Não foi possível criar a aprovação.');
      }
    } catch {
      setNotice('Erro ao criar a aprovação.');
    } finally {
      setCreating(false);
    }
  };

  const newDraft = () => {
    setCreatedApproval(null);
    setGenerated(false);
    setMessage('');
    setNotice('');
  };

  const draftTab = (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
          <Icon icon={icons.cadeado} size={14} className="mt-0.5 shrink-0 text-primary" />
          <span>Nenhuma mensagem é enviada automaticamente.</span>
        </div>
        <div className="flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
          <Icon icon={icons.aprovacao} size={14} className="mt-0.5 shrink-0 text-primary" />
          <span>Usa aprovação humana e simulação WhatsApp (dry-run).</span>
        </div>
      </div>

      <div className="space-y-2">
        <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">Atendimento (opcional)</p>
        {convs === null ? (
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
            <Icon icon={icons.renovacao} size={14} className="animate-spin" /> Carregando conversas…
          </div>
        ) : (
          <div className="max-h-44 space-y-1.5 overflow-y-auto pr-1">
            <SelectorRow active={selectedId === null} onClick={() => selectConversation(null)} title="Sem atendimento específico" subtitle="Gera com base apenas no objetivo" />
            {convs.map((c) => (
              <SelectorRow
                key={c.id}
                active={selectedId === c.id}
                onClick={() => selectConversation(c)}
                title={c.title}
                subtitle={[typeof c.message_count === 'number' ? `${c.message_count} msgs` : '', fmtDateShort(c.updated_at || c.created_at)].filter(Boolean).join(' · ')}
              />
            ))}
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="fu-phone" className="text-foreground">Telefone de destino</Label>
          <Input id="fu-phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="5547999999999" className="bg-background" />
          <p className="text-[11px] text-muted-foreground">Use DDI+DDD+número. Ex.: 5547999999999.</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="fu-objective" className="text-foreground">Objetivo do follow-up</Label>
          <Input id="fu-objective" value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="retomar contato sobre a cotação de seguro auto" className="bg-background" />
        </div>
      </div>

      <div className="space-y-1.5">
        <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">Tom da mensagem</p>
        <div className="flex flex-wrap gap-1.5">
          {TONES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setTone(t.value)}
              className={cn(
                'rounded-full border px-3 py-1 text-xs transition-colors',
                tone === t.value ? 'border-primary/40 bg-brand-soft text-primary' : 'border-border text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <Button onClick={generate} disabled={draftState === 'loading'}>
        {draftState === 'loading' ? (
          <>
            <Icon icon={icons.renovacao} size={16} className="mr-2 animate-spin" /> Gerando rascunho…
          </>
        ) : (
          <>
            <Icon icon={icons.auxiliares} size={16} className="mr-2" /> Gerar rascunho
          </>
        )}
      </Button>

      {draftState === 'error' && (
        <DetailSection>
          {errorKind === 'credits' ? (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-warning/40 bg-surface-2 text-warning">
                <Icon icon={icons.alerta} size={18} />
              </span>
              <p className="text-sm font-medium text-foreground">Sem créditos suficientes para gerar o rascunho.</p>
              <Link href="/dashboard/configuracoes" className="text-xs font-medium text-primary hover:underline">
                Ver configurações →
              </Link>
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="mx-auto max-w-md text-sm font-medium text-foreground">{errorMsg}</p>
              <Button variant="outline" className="mt-4" onClick={generate}>Tentar novamente</Button>
            </div>
          )}
        </DetailSection>
      )}

      {generated && (
        <DetailSection title="Rascunho (edite antes de aprovar)">
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={5}
            className="bg-background"
            placeholder="A mensagem de follow-up aparecerá aqui."
          />
          <p className="mt-1 text-[11px] text-muted-foreground">{message.length} caracteres · nenhuma mensagem será enviada agora.</p>

          {!waConn && (
            <p className="mt-3 text-xs text-warning">
              Nenhuma conexão WhatsApp conectada. Configure em{' '}
              <Link href="/dashboard/personalizacao/conectores" className="underline">Conectores</Link>.
            </p>
          )}
          {waConn && permWarning && (
            <p className="mt-3 text-xs text-warning">
              Permissão específica ainda não configurada; usando aprovação humana obrigatória.
            </p>
          )}

          {createdApproval ? (
            <div className="mt-3 rounded-lg border border-success/40 bg-surface-2 p-3">
              <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Icon icon={icons.success} size={16} className="text-success" /> Aprovação criada
              </p>
              <p className="mt-1 font-mono text-[11px] text-faint">id: {createdApproval.id} · status: {createdApproval.status}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Link
                  href="/dashboard/personalizacao/conectores/aprovacoes"
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-primary/40"
                >
                  <Icon icon={icons.aprovacao} size={14} /> Ver em Aprovações
                </Link>
                <Button size="sm" variant="outline" onClick={newDraft}>Criar novo rascunho</Button>
              </div>
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button onClick={createApproval} disabled={creating}>
                <Icon icon={icons.aprovacao} size={14} className="mr-2" />
                {creating ? 'Criando…' : 'Criar aprovação'}
              </Button>
              <Link
                href="/dashboard/personalizacao/conectores/aprovacoes"
                className="text-xs font-medium text-primary hover:underline"
              >
                Ir para Aprovações →
              </Link>
            </div>
          )}

          {notice && <p className="mt-2 text-xs text-foreground-2">{notice}</p>}
        </DetailSection>
      )}

      {notice && !generated && <p className="text-xs text-foreground-2">{notice}</p>}
    </div>
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-4 py-10 sm:px-6">
        <DetailShell
          header={{
            icon: icons.whatsapp,
            title: 'Auxiliar de Follow-up WhatsApp',
            subtitle: 'Gere rascunhos humanos de retorno e envie para aprovação antes de qualquer execução.',
            status: { tone: 'success', label: 'Pronto para ativar' },
            breadcrumb: [
              { label: 'Auxiliares', href: '/dashboard/auxiliares' },
              { label: 'Galeria', href: '/dashboard/auxiliares/galeria' },
              { label: 'Follow-up WhatsApp' },
            ],
          }}
          tabs={[
            { value: 'draft', label: 'Rascunho', content: draftTab },
            {
              value: 'how',
              label: 'Como funciona',
              content: (
                <DetailSection
                  title="Como funciona"
                  description="Escolha um atendimento (ou só informe o objetivo), escolha o tom, gere um rascunho humano de follow-up, edite se quiser e crie um pedido de aprovação. A execução acontece em modo seguro (dry-run) após aprovação humana — nenhuma mensagem real é enviada."
                />
              ),
            },
          ]}
          side={
            <DetailSection title="Resumo">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Categoria</dt>
                  <dd className="text-foreground">Comunicação</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Risco</dt>
                  <dd className="text-warning">Médio</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Envio externo</dt>
                  <dd className="text-foreground">Não (dry-run)</dd>
                </div>
              </dl>
            </DetailSection>
          }
        />
      </div>
    </div>
  );
}
