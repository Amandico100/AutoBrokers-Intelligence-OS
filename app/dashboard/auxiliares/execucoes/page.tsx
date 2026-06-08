'use client';

import { useCallback, useEffect, useState } from 'react';

import { DetailHeader, DetailSection, StatusPill, type StatusTone } from '@/components/patterns';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';
import { icons } from '@/lib/icons';
import { fetchRuns, fetchTemplates } from '@/lib/auxiliaries/api';
import type { AuxiliaryRun } from '@/lib/auxiliaries/types';
import { ResumoResult } from '@/components/auxiliaries/ResumoResult';

type Filter = 'all' | 'succeeded' | 'failed';

function runPill(status?: string): { tone: StatusTone; label: string } {
  switch (status) {
    case 'succeeded':
      return { tone: 'success', label: 'Concluído' };
    case 'failed':
      return { tone: 'danger', label: 'Erro' };
    case 'running':
    case 'pending':
      return { tone: 'info', label: 'Em andamento' };
    case 'awaiting_approval':
      return { tone: 'approval', label: 'Aguardando aprovação' };
    default:
      return { tone: 'neutral', label: status || 'Desconhecido' };
  }
}

function fmtDate(s?: string | null): string {
  if (!s) return '';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('pt-BR');
}

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Todos' },
  { key: 'succeeded', label: 'Concluídas' },
  { key: 'failed', label: 'Erro' },
];

export default function ExecucoesPage() {
  const [runs, setRuns] = useState<AuxiliaryRun[] | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [error, setError] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(false);
    try {
      const [r, t] = await Promise.all([
        fetchRuns(),
        fetchTemplates().catch(() => ({ templates: [] })),
      ]);
      setRuns(r.runs || []);
      const map: Record<string, string> = {};
      for (const tpl of t.templates || []) map[tpl.id] = tpl.name;
      setNames(map);
    } catch {
      setError(true);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const titleFor = (run: AuxiliaryRun): string => {
    const tid = typeof run.template_id === 'string' ? run.template_id : '';
    return names[tid] || 'Auxiliar de Resumo de Atendimentos';
  };

  const visible = (runs || []).filter((r) => filter === 'all' || r.status === filter);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.historico}
          title="Execuções"
          subtitle="Histórico do que os Auxiliares fizeram (status, resultado e custo)."
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Execuções' }]}
          actions={
            <Button size="sm" variant="outline" onClick={load} disabled={refreshing}>
              <Icon icon={icons.renovacao} size={14} className={cn('mr-2', refreshing && 'animate-spin')} />
              Atualizar
            </Button>
          }
        />

        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              className={cn(
                'rounded-full border px-3 py-1 text-xs transition-colors',
                filter === f.key
                  ? 'border-primary/40 bg-brand-soft text-primary'
                  : 'border-border text-muted-foreground hover:text-foreground',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error ? (
          <DetailSection>
            <p className="py-8 text-center text-sm text-muted-foreground">
              Não foi possível carregar as execuções agora. Tente novamente em alguns instantes.
            </p>
          </DetailSection>
        ) : runs === null ? (
          <DetailSection>
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
            </div>
          </DetailSection>
        ) : visible.length === 0 ? (
          <DetailSection>
            <p className="py-8 text-center text-sm text-muted-foreground">
              {filter === 'all' ? 'Nenhuma execução ainda.' : 'Nenhuma execução neste filtro.'}
            </p>
          </DetailSection>
        ) : (
          <div className="space-y-3">
            {visible.map((run) => {
              const pill = runPill(typeof run.status === 'string' ? run.status : undefined);
              const open = openId === run.id;
              const summary = run.output?.summary?.trim();
              const usage = run.token_usage as { total_tokens?: number } | null | undefined;
              const totalTokens =
                usage && typeof usage.total_tokens === 'number' ? usage.total_tokens : undefined;
              const cost = typeof run.cost_usd === 'number' && run.cost_usd > 0 ? run.cost_usd : undefined;
              const hasConversation = typeof run.conversation_id === 'string' && run.conversation_id;
              return (
                <div key={run.id} className="rounded-xl border border-border bg-surface">
                  <button
                    type="button"
                    onClick={() => setOpenId(open ? null : run.id)}
                    className="flex w-full items-start justify-between gap-3 p-4 text-left transition-colors hover:bg-surface-2"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-foreground">{titleFor(run)}</span>
                        <StatusPill tone={pill.tone} label={pill.label} />
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{fmtDate(run.created_at)}</span>
                        {hasConversation && <span className="text-faint">· Conversa vinculada</span>}
                      </div>
                      {summary && <p className="mt-1.5 line-clamp-2 text-xs text-foreground-2">{summary}</p>}
                      {run.status === 'failed' && run.error_message && (
                        <p className="mt-1.5 text-xs text-danger">{String(run.error_message)}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      {typeof totalTokens === 'number' && (
                        <span className="font-mono text-[10px] text-faint">{totalTokens} tokens</span>
                      )}
                      {typeof cost === 'number' && (
                        <span className="font-mono text-[10px] text-faint">${cost.toFixed(4)}</span>
                      )}
                      <Icon
                        icon={icons.avancar}
                        size={14}
                        className={cn('text-muted-foreground transition-transform', open && 'rotate-90')}
                      />
                    </div>
                  </button>
                  {open && (
                    <div className="border-t border-border p-4">
                      {run.output ? (
                        <ResumoResult output={run.output} />
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Sem resultado estruturado para esta execução.
                        </p>
                      )}
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
