'use client';

// SPEC-139 · L3 (P-16) — a aba "Resumos" do aplicativo Resumo de atendimentos
// (`/dashboard/auxiliares/resumo-atendimentos?aba=resumos`).
// O conteúdo é a tela que morava em `app/dashboard/auxiliares/galeria/resumo-atendimentos/page.tsx`, MOVIDO (não
// reescrito): a mesma escolha de atendimento, as mesmas chamadas (`fetchResumoConversations`,
// `runResumoAtendimentos`, `fetchRun`), o mesmo resultado (`ResumoResult`) e as mesmas permissões. Saiu daqui só a
// moldura que a casca já dá (cabeçalho, migalhas, a coluna "Resumo") e o "Como funciona", que é conteúdo do Início.
// O endereço antigo redireciona para cá (307). Carregada pela casca por import dinâmico (ABAS_DO_APLICATIVO).

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Sparkles } from 'lucide-react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { DetailSection, PermissionList } from '@/components/patterns';
import { ResumoResult } from '@/components/auxiliaries/ResumoResult';
import { resumoPermissions } from '@/lib/mock/tenant-modules';
import { runResumoAtendimentos, fetchResumoConversations, fetchRun } from '@/lib/auxiliaries/api';
import type { AuxiliaryRun, AuxiliaryRunOutput, ResumoConversation } from '@/lib/auxiliaries/types';

type RunState = 'idle' | 'loading' | 'success' | 'error';

// Conserto B da SPEC-139 (juiz de design, Resumos 79): o rótulo mono de 10 px em `text-faint` vira `text-sm` legível;
// "Executar resumo agora" usa `BOTAO_PRIMARIO`; o rodapé do resultado não fala "tokens" nem custo em dólar (é dado de
// operação, não do corretor) — só quanto tempo levou. As chamadas de dados são as mesmas (as-telas-no-lugar guarda).

function friendlyError(err?: string): string {
  const e = (err || '').toLowerCase();
  if (e.includes('conversa') || e.includes('mensage')) {
    return 'Ainda não encontramos conversas suficientes para resumir. Converse com o AutoBrokers ou aguarde novos atendimentos.';
  }
  if (e.includes('autoriz') || e.includes('unauthorized') || e.includes('permiss')) {
    return 'Sua sessão não tem permissão para executar este aplicativo.';
  }
  return 'Não foi possível executar este aplicativo agora. Tente novamente em alguns instantes.';
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
        {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <span
        className={cn('h-3.5 w-3.5 shrink-0 rounded-full border', active ? 'border-primary bg-primary' : 'border-border')}
      />
    </button>
  );
}

function RunMeta({ run }: { run: AuxiliaryRun | null }) {
  if (!run) return null;
  const start =
    (typeof run.started_at === 'string' && run.started_at) ||
    (typeof run.created_at === 'string' && run.created_at) ||
    '';
  const end = typeof run.finished_at === 'string' ? run.finished_at : '';
  let duration: string | undefined;
  if (start && end) {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms >= 0 && Number.isFinite(ms)) duration = `${(ms / 1000).toFixed(1).replace('.', ',')} segundos`;
  }
  if (!duration) return null;
  return <p className="text-xs text-muted-foreground">Resumo pronto em {duration}.</p>;
}

export default function AbaResumos() {
  const [convs, setConvs] = useState<ResumoConversation[] | null>(null);
  const [convError, setConvError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [state, setState] = useState<RunState>('idle');
  const [output, setOutput] = useState<AuxiliaryRunOutput | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [errorKind, setErrorKind] = useState<'generic' | 'credits'>('generic');
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
    setErrorKind('generic');
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
      } else if (res.error === 'insufficient_credits') {
        setErrorKind('credits');
        setErrorMsg(
          res.message || 'Sua corretora não possui créditos suficientes para executar este aplicativo.',
        );
        setState('error');
      } else {
        setErrorMsg(friendlyError(res.error));
        setState('error');
      }
    } catch {
      setErrorMsg('Não foi possível executar este aplicativo agora. Tente novamente em alguns instantes.');
      setState('error');
    }
  };

  const runTab = (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
        <Icon icon={icons.cadeado} size={14} className="mt-0.5 shrink-0 text-primary" />
        <span>
          Este aplicativo apenas <span className="font-medium text-foreground">lê</span> conversas da sua
          corretora e gera um resumo. Ele não envia mensagens, não altera atendimentos e não executa
          ações externas.
        </span>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">Escolha o atendimento</p>
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

      <button
        type="button"
        onClick={execute}
        disabled={state === 'loading'}
        className={`inline-flex h-11 items-center justify-center gap-2 rounded-lg px-5 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50 ${BOTAO_PRIMARIO}`}
      >
        {state === 'loading' ? (
          <>
            <Icon icon={icons.renovacao} size={16} className="animate-spin" />
            Resumindo…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
            Resumir agora
          </>
        )}
      </button>

      {state === 'loading' && (
        <DetailSection>
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Gerando resumo…
          </div>
        </DetailSection>
      )}

      {state === 'error' && (
        <DetailSection>
          {errorKind === 'credits' ? (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-warning/40 bg-surface-2 text-warning">
                <Icon icon={icons.alerta} size={18} />
              </span>
              <p className="text-sm font-medium text-foreground">
                Sem créditos suficientes para executar este aplicativo.
              </p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Recarregue os créditos da corretora ou ajuste o plano antes de executar novas rotinas de IA.
              </p>
              <div className="mt-1 flex flex-wrap items-center justify-center gap-3">
                <Link
                  href="/dashboard/configuracoes"
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/40"
                >
                  <Icon icon={icons.configuracoes} size={16} />
                  Ver configurações
                </Link>
                <Link
                  href="/dashboard/auxiliares/execucoes"
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Ver execuções →
                </Link>
              </div>
            </div>
          ) : (
            <div className="py-6 text-center">
              <p className="mx-auto max-w-md text-sm font-medium text-foreground">{errorMsg}</p>
              <Button variant="outline" className="mt-4" onClick={execute}>
                Tentar novamente
              </Button>
            </div>
          )}
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
    <div className="max-w-3xl space-y-6">
      {runTab}
      <DetailSection title="Permissões">
        <PermissionList groups={resumoPermissions} />
      </DetailSection>
    </div>
  );
}