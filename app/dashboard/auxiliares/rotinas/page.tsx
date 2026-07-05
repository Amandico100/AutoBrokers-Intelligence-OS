'use client';

// F2 — Rotinas agendadas da corretora: lista, pausa/ativa, exclui e mostra as
// últimas execuções. Criação acontece pelo Chat Principal ("todo dia às 8h...").

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Pause, Play, Trash2 } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { StatusPill } from '@/components/patterns/StatusPill';
import { icons } from '@/lib/icons';

interface Routine {
  id: string;
  name: string;
  instructions: string;
  schedule: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
  delivery: { channel?: string; number?: string };
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  consecutive_failures: number;
}

interface Run {
  id: string;
  routine_id: string;
  started_at: string;
  status: string;
  output_preview: string | null;
  error: string | null;
}

const DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];

function scheduleLabel(s: Routine['schedule']) {
  if (s?.kind === 'interval') return `a cada ${s.minutes} min`;
  const days = s?.weekdays?.length ? ` (${s.weekdays.map((d) => DIAS[d] ?? d).join(', ')})` : '';
  return `diária às ${s?.time || '?'}${days}`;
}

function fmt(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export default function RotinasPage() {
  const [routines, setRoutines] = useState<Routine[] | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/rotinas', { cache: 'no-store' });
      const j = await res.json();
      if (!res.ok) {
        setNotice(j.error || 'Erro ao carregar rotinas.');
        setRoutines([]);
        return;
      }
      setRoutines(j.routines || []);
      setRuns(j.runs || []);
    } catch {
      setNotice('Falha de conexão.');
      setRoutines([]);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  const act = async (id: string, action: 'pause' | 'activate' | 'delete') => {
    if (action === 'delete' && !confirm('Excluir esta rotina? O histórico de execuções também será removido.')) return;
    setNotice('');
    const res = await fetch('/api/dashboard/rotinas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, action }),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setNotice(j.error || 'Não foi possível concluir a ação.');
    }
    load();
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.historico}
          title="Rotinas agendadas"
          subtitle="Tarefas que o agente executa sozinho e entrega onde você pediu. Crie pelo chat: 'todo dia às 8h, me mande…'"
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Rotinas' }]}
        />

        {notice && <p className="text-sm text-danger">{notice}</p>}

        {routines === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando rotinas…
          </div>
        ) : routines.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">Nenhuma rotina ainda</p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              Abra o chat AutoBrokers e peça, por exemplo: &quot;Crie uma rotina que todo dia às 8h
              me mande no WhatsApp um resumo das notícias de seguros&quot;. Ela aparece aqui.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {routines.map((r) => {
              const rRuns = runs.filter((x) => x.routine_id === r.id).slice(0, 3);
              return (
                <div key={r.id} className="rounded-xl border border-border bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">{r.name}</p>
                        <StatusPill
                          tone={r.is_active ? 'success' : 'neutral'}
                          label={r.is_active ? 'ativa' : 'pausada'}
                        />
                        {r.consecutive_failures >= 5 && (
                          <StatusPill tone="danger" label="desativada por falhas" />
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {scheduleLabel(r.schedule)} · entrega: {r.delivery?.channel || 'histórico'}
                        {r.delivery?.number ? ` (${r.delivery.number})` : ''} · próxima: {fmt(r.next_run_at)} · última: {fmt(r.last_run_at)}
                      </p>
                      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{r.instructions}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {r.is_active ? (
                        <button
                          onClick={() => act(r.id, 'pause')}
                          className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                          title="Pausar rotina"
                        >
                          <Pause className="h-3.5 w-3.5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => act(r.id, 'activate')}
                          className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                          title="Reativar rotina"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => act(r.id, 'delete')}
                        className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-danger"
                        title="Excluir rotina"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {rRuns.length > 0 && (
                    <div className="mt-3 space-y-1 border-t border-border pt-2">
                      {rRuns.map((run) => (
                        <p key={run.id} className="truncate text-[11px] text-muted-foreground">
                          <span className={run.status === 'ok' ? 'text-success' : run.status === 'error' ? 'text-danger' : ''}>
                            {run.status === 'ok' ? '✓' : run.status === 'error' ? '✗' : '…'}
                          </span>{' '}
                          {fmt(run.started_at)} · {run.error || run.output_preview || 'executando…'}
                        </p>
                      ))}
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
