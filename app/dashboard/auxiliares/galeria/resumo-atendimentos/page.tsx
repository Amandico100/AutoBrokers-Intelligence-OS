'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { DetailShell, DetailSection, PermissionList } from '@/components/patterns';
import { ResumoResult } from '@/components/auxiliaries/ResumoResult';
import { resumoPermissions } from '@/lib/mock/tenant-modules';
import { runResumoAtendimentos, fetchResumoConversations, fetchRun } from '@/lib/auxiliaries/api';
import type { AuxiliaryRun, AuxiliaryRunOutput, ResumoConversation } from '@/lib/auxiliaries/types';

type RunState = 'idle' | 'loading' | 'success' | 'error';

function friendlyError(err?: string): string {
  const e = (err || '').toLowerCase();
  if (e.includes('conversa') || e.includes('mensage')) {
    return 'Ainda não encontramos conversas suficientes para resumir. Converse com o AutoBrokers ou aguarde novos atendimentos.';
  }
  if (e.includes('autoriz') || e.includes('unauthorized') || e.includes('permiss')) {
    return 'Sua sessão não tem permissão para executar este auxiliar.';
  }
  return 'Não foi possível executar este auxiliar agora. Tente novamente em alguns instantes.';
}

function fmtDateShort(s?: string | null): string {
  if (!s) return '';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('pt-BR');
}

function subtitleFor(c: ResumoConversation): string {
  const bits: string[] = [];
  if (typeof c.message_count === 'number') bits.push(`${c.message_count} msg${c.message_count === 1 ? '' : 's'}`);
  const d = fmtDateShort(c.updated_at || c.created_at);
  if (d) bits.push(d);
  return bits.join(' · ');
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
      <span
        className={cn('h-3.5 w-3.5 shrink-0 rounded-full border', active ? 'border-primary bg-primary' : 'border-border')}
      />
    </button>
  );
}

function RunMeta({ run }: { run: AuxiliaryRun | null }) {
  if (!run) return null;
  const tokens = run.token_usage?.total_tokens;
  const cost = typeof run.cost_usd === 'number' ? run.cost_usd : undefined;
  const start =
    (typeof run.started_at === 'string' && run.started_at) ||
    (typeof run.created_at === 'string' && run.created_at) ||
    '';
  const end = typeof run.finished_at === 'string' ? run.finished_at : '';
  let duration: string | undefined;
  if (start && end) {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms >= 0 && Number.isFinite(ms)) duration = `${(ms / 1000).toFixed(1)}s`;
  }
  const parts: string[] = [];
  if (typeof tokens === 'number') parts.push(`${tokens} tokens`);
  if (typeof cost === 'number' && cost > 0) parts.push(`$${cost.toFixed(4)}`);
  if (duration) parts.push(duration);
  if (parts.length === 0) return null;
  return <p className="font-mono text-[10px] text-faint">{parts.join(' · ')}</p>;
}

export default function ResumoAtendimentosDetailPage() {
  const [convs, setConvs] = useState<ResumoConversation[] | null>(null);
  const [convError, setConvError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [state, setState] = useState<RunState>('idle');
  const [output, setOutput] = useState<AuxiliaryRunOutput | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [fullRun, setFullRun] = useState<AuxiliaryRun | null>(null);

  useEffect(() => {
    let active = true;
    fetchResumoConversations()
      .then((d) => {
        if (active) setConvs(d.conversations || []);
      })
      .catch(() => {
        if (active) setConvError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const execute = async () => {
    setState('loading');
    setErrorMsg('');
    setOutput(null);
    setFullRun(null);
    try {
      const res = await runResumoAtendimentos(selectedId ?? undefined);
      if (res.success && res.run?.output) {
        setOutput(res.run.output);
        setState('success');
        const runId = res.run.id;
        if (runId) {
          fetchRun(runId)
            .then((d) => setFullRun(d.run))
            .catch(() => {});
        }
      } else if (res.success) {
        setErrorMsg('Resumo gerado, mas o formato retornado foi inesperado.');
        setState('error');
      } else {
        setErrorMsg(friendlyError(res.error));
        setState('error');
      }
    } catch {
      setErrorMsg('Não foi possível executar este auxiliar agora. Tente novamente em alguns instantes.');
      setState('error');
    }
  };

  const runTab = (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
        <Icon icon={icons.cadeado} size={14} className="mt-0.5 shrink-0 text-primary" />
        <span>
          Este auxiliar apenas <span className="font-medium text-foreground">lê</span> conversas da sua
          corretora e gera um resumo. Ele não envia mensagens, não altera atendimentos e não executa
          ações externas.
        </span>
      </div>

      <div className="space-y-2">
        <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">Escolha o atendimento</p>
        {convs === null && !convError ? (
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
            <Icon icon={icons.renovacao} size={14} className="animate-spin" /> Carregando conversas…
          </div>
        ) : convError ? (
          <div className="rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
            Não foi possível carregar as conversas. Será usado o atendimento mais recente.
          </div>
        ) : (
          <div className="max-h-64 space-y-1.5 overflow-y-auto pr-1">
            <SelectorRow
              active={selectedId === null}
              onClick={() => setSelectedId(null)}
              title="Atendimento mais recente"
              subtitle="O AutoBrokers escolhe automaticamente"
            />
            {(convs || []).map((c) => (
              <SelectorRow
                key={c.id}
                active={selectedId === c.id}
                onClick={() => setSelectedId(c.id)}
                title={c.title}
                subtitle={subtitleFor(c)}
              />
            ))}
            {convs && convs.length === 0 && (
              <p className="px-1 py-2 text-xs text-muted-foreground">
                Ainda não há conversas com mensagens para resumir.
              </p>
            )}
          </div>
        )}
      </div>

      <Button onClick={execute} disabled={state === 'loading'}>
        {state === 'loading' ? (
          <>
            <Icon icon={icons.renovacao} size={16} className="mr-2 animate-spin" />
            Executando…
          </>
        ) : (
          <>
            <Icon icon={icons.enviar} size={16} className="mr-2" />
            Executar resumo agora
          </>
        )}
      </Button>

      {state === 'loading' && (
        <DetailSection>
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Gerando resumo…
          </div>
        </DetailSection>
      )}

      {state === 'error' && (
        <DetailSection>
          <div className="py-6 text-center">
            <p className="mx-auto max-w-md text-sm font-medium text-foreground">{errorMsg}</p>
            <Button variant="outline" className="mt-4" onClick={execute}>
              Tentar novamente
            </Button>
          </div>
        </DetailSection>
      )}

      {state === 'success' && output && (
        <DetailSection title="Resultado">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-success/40 bg-surface-2 px-3 py-2">
            <span className="flex items-center gap-2 text-xs text-foreground-2">
              <Icon icon={icons.success} size={14} className="text-success" /> Resumo salvo em Execuções
            </span>
            <Link
              href="/dashboard/auxiliares/execucoes"
              className="text-xs font-medium text-primary hover:underline"
            >
              Ver em Execuções →
            </Link>
          </div>
          <ResumoResult output={output} />
          <div className="mt-3">
            <RunMeta run={fullRun} />
          </div>
        </DetailSection>
      )}
    </div>
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-4 py-10 sm:px-6">
        <DetailShell
          header={{
            icon: icons.auxiliares,
            title: 'Auxiliar de Resumo de Atendimentos',
            subtitle:
              'Resume conversas, identifica pendências e prepara próximos passos — sem envio externo.',
            status: { tone: 'success', label: 'Pronto para ativar' },
            breadcrumb: [
              { label: 'Auxiliares', href: '/dashboard/auxiliares' },
              { label: 'Galeria', href: '/dashboard/auxiliares/galeria' },
              { label: 'Resumo de Atendimentos' },
            ],
          }}
          tabs={[
            { value: 'run', label: 'Resumo', content: runTab },
            {
              value: 'how',
              label: 'Como funciona',
              content: (
                <DetailSection
                  title="Como funciona"
                  description="Você escolhe o atendimento (ou deixa no automático). O AutoBrokers analisa o histórico e devolve um resumo operacional com pendências e próximos passos sugeridos, prontos para revisar."
                />
              ),
            },
            {
              value: 'perms',
              label: 'Permissões',
              content: (
                <DetailSection title="Permissões">
                  <PermissionList groups={resumoPermissions} />
                </DetailSection>
              ),
            },
          ]}
          side={
            <DetailSection title="Resumo">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Categoria</dt>
                  <dd className="text-foreground">Análise</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Risco</dt>
                  <dd className="text-success">Baixo</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Envio externo</dt>
                  <dd className="text-foreground">Não</dd>
                </div>
              </dl>
            </DetailSection>
          }
        />
      </div>
    </div>
  );
}
