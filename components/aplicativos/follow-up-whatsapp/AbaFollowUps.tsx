'use client';

// SPEC-139 · L3 (P-16) — a aba "Follow-ups" do aplicativo Follow-up do WhatsApp
// (`/dashboard/auxiliares/follow-up-whatsapp?aba=follow-ups`).
// O conteúdo é a tela que morava em `app/dashboard/auxiliares/galeria/follow-up-whatsapp/page.tsx`, MOVIDO (não
// reescrito): o mesmo rascunho, as mesmas chamadas (`fetchResumoConversations`, `draftFollowUpWhatsapp`,
// `createApprovalRequest` com o MESMO `action_type`/`request_payload`, conexões e permissões do cofre). Saiu daqui só
// a moldura que a casca já dá (cabeçalho, migalhas, a coluna "Resumo") e o "Como funciona", que é conteúdo do Início
// (`what_it_does`/dúvidas do catálogo). Nenhuma mensagem é enviada: continua pedido de aprovação em simulação.
// O endereço antigo redireciona para cá (307). Carregada pela casca por import dinâmico (ABAS_DO_APLICATIVO).

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PenLine } from 'lucide-react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { DetailSection } from '@/components/patterns';
import { fetchResumoConversations, draftFollowUpWhatsapp } from '@/lib/auxiliaries/api';
import type { ResumoConversation } from '@/lib/auxiliaries/types';
import { createApprovalRequest, fetchConnectorTemplates, fetchTenantConnections, fetchPermissions } from '@/lib/vault/api';

type DraftState = 'idle' | 'loading' | 'error';

// Conserto B da SPEC-139 (juiz de design, Follow-ups 78): os rótulos mono de 10 px em `text-faint` (2,75:1) viram
// `text-sm font-medium text-foreground`; os chips de tom têm 44 px de toque no celular; "Gerar rascunho" e "Criar
// aprovação" usam `BOTAO_PRIMARIO` (o branco sobre azul reprovava AA no claro); depois de criar, uma FRASE — nunca
// `id:`/`status:` crus. As chamadas de dados são as mesmas (scripts/as-telas-no-lugar.test.mjs guarda).
const ROTULO = 'text-sm font-medium text-foreground';
const BOTAO = `inline-flex h-11 items-center justify-center gap-2 rounded-lg px-5 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50 ${BOTAO_PRIMARIO}`;

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
        {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <span className={cn('h-3.5 w-3.5 shrink-0 rounded-full border', active ? 'border-primary bg-primary' : 'border-border')} />
    </button>
  );
}

export default function AbaFollowUps() {
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
        setErrorMsg(res.message || 'Sua corretora não possui créditos suficientes para executar este aplicativo.');
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
          <span>Usa aprovação humana e simulação do WhatsApp — nada sai para o cliente.</span>
        </div>
      </div>

      <div className="space-y-2">
        <p className={ROTULO}>Atendimento (opcional)</p>
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
                subtitle={[typeof c.message_count === 'number' ? `${c.message_count} ${c.message_count === 1 ? 'mensagem' : 'mensagens'}` : '', fmtDateShort(c.updated_at || c.created_at)].filter(Boolean).join(' · ')}
              />
            ))}
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="fu-phone" className="text-foreground">Telefone de destino</Label>
          <Input id="fu-phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="5511900000000" className="bg-background" />
          <p className="text-xs text-muted-foreground">Com o código do país e o DDD, só números. Ex.: 5511900000000.</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="fu-objective" className="text-foreground">Objetivo do follow-up</Label>
          <Input id="fu-objective" value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="retomar contato sobre a cotação de seguro auto" className="bg-background" />
        </div>
      </div>

      <div className="space-y-1.5">
        <p className={ROTULO}>Tom da mensagem</p>
        <div className="flex flex-wrap gap-1.5">
          {TONES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => setTone(t.value)}
              aria-pressed={tone === t.value}
              className={cn(
                'inline-flex h-11 items-center rounded-full border px-4 text-sm transition-colors sm:h-9',
                tone === t.value ? 'border-primary/40 bg-brand-soft font-medium text-foreground' : 'border-border text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <button type="button" onClick={generate} disabled={draftState === 'loading'} className={BOTAO}>
        {draftState === 'loading' ? (
          <>
            <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Gerando rascunho…
          </>
        ) : (
          <>
            <PenLine className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" /> Gerar rascunho
          </>
        )}
      </button>

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
          <p className="mt-1 text-xs text-muted-foreground">{message.length} caracteres · nenhuma mensagem será enviada agora.</p>

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
                <Icon icon={icons.success} size={16} className="text-success" /> Pedido de aprovação criado
              </p>
              <p className="mt-1 text-sm text-muted-foreground">Aguardando você em Aprovações — nada sai para o cliente antes disso.</p>
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
              <button type="button" onClick={createApproval} disabled={creating} className={BOTAO}>
                <Icon icon={icons.aprovacao} size={14} />
                {creating ? 'Criando…' : 'Pedir minha aprovação'}
              </button>
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

  return <div className="max-w-3xl">{draftTab}</div>;
}
