'use client';

// F2 — Rotinas agendadas da corretora: lista, pausa/ativa, exclui e mostra as
// últimas execuções. Criação acontece pelo Chat Principal ("todo dia às 8h...").

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Pause, Pencil, Play, Plus, Trash2 } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { StatusPill } from '@/components/patterns/StatusPill';
import { icons } from '@/lib/icons';

interface Routine {
  id: string;
  name: string;
  instructions: string;
  knowledge?: string | null;
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
  // SPEC-019 B — modal de criação/edição manual (paridade Claude Rotinas)
  const [editing, setEditing] = useState<Routine | 'new' | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: '', instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '' as string,
    minutes: 60, channel: 'whatsapp', number: '',
  });

  const openEditor = (r: Routine | 'new') => {
    if (r === 'new') {
      setForm({ name: '', instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '', minutes: 60, channel: 'whatsapp', number: '' });
    } else {
      setForm({
        name: r.name,
        instructions: r.instructions,
        knowledge: r.knowledge || '',
        kind: r.schedule?.kind === 'interval' ? 'interval' : 'daily',
        time: r.schedule?.time || '08:00',
        weekdays: (r.schedule?.weekdays || []).join(','),
        minutes: r.schedule?.minutes || 60,
        channel: r.delivery?.channel || 'whatsapp',
        number: r.delivery?.number || '',
      });
    }
    setEditing(r);
  };

  // SPEC-019 C — "Usar modelo": abre a Nova rotina já preenchida pelo template.
  const openEditorFromTemplate = (t: {
    name: string;
    instructions: string;
    schedule_default?: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
    delivery_default?: { channel?: string };
  }) => {
    const s = t.schedule_default || {};
    setForm({
      name: t.name,
      instructions: t.instructions,
      knowledge: '',
      kind: s.kind === 'interval' ? 'interval' : 'daily',
      time: s.time || '08:00',
      weekdays: (s.weekdays || []).join(','),
      minutes: s.minutes || 60,
      channel: t.delivery_default?.channel === 'none' ? 'none' : 'whatsapp',
      number: '',
    });
    setEditing('new');
  };

  const saveRoutine = async () => {
    setSaving(true);
    setNotice('');
    const schedule: Record<string, unknown> = form.kind === 'interval'
      ? { kind: 'interval', minutes: Number(form.minutes) }
      : {
          kind: 'daily', time: form.time,
          ...(form.weekdays.trim()
            ? { weekdays: form.weekdays.split(',').map((d) => parseInt(d.trim(), 10)).filter((n) => !isNaN(n)) }
            : {}),
        };
    const delivery = form.channel === 'whatsapp' ? { channel: 'whatsapp', number: form.number } : { channel: 'none' };
    const res = await fetch('/api/dashboard/rotinas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: editing === 'new' ? 'create' : 'update',
        id: editing !== 'new' && editing ? editing.id : undefined,
        name: form.name, instructions: form.instructions, knowledge: form.knowledge, schedule, delivery,
      }),
    });
    const j = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setNotice(j.error || 'Erro ao salvar rotina.');
      return;
    }
    setEditing(null);
    load();
  };

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

  // SPEC-019 C — chegou de "Usar modelo" (?template=<id>): abre a Nova rotina
  // pré-preenchida. Lê via window para não exigir Suspense do useSearchParams.
  useEffect(() => {
    const tid = new URLSearchParams(window.location.search).get('template');
    if (!tid) return;
    (async () => {
      try {
        const res = await fetch('/api/dashboard/routine-templates', { cache: 'no-store' });
        const j = await res.json();
        const t = (j.templates || []).find((x: { id: string }) => x.id === tid);
        if (t) openEditorFromTemplate(t);
      } catch {
        /* ignora — o corretor pode criar do zero */
      }
      window.history.replaceState({}, '', '/dashboard/auxiliares/rotinas');
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

        <div className="flex items-center justify-between gap-3">
          {notice ? <p className="text-sm text-danger">{notice}</p> : <span />}
          <button
            onClick={() => openEditor('new')}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Plus className="h-4 w-4" /> Nova rotina
          </button>
        </div>

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
                      <button
                        onClick={() => openEditor(r)}
                        className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                        title="Editar rotina"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
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

        {editing !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !saving && setEditing(null)}>
            <div
              className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-surface p-5"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-base font-semibold text-foreground">
                {editing === 'new' ? 'Nova rotina' : 'Editar rotina'}
              </h2>
              <div className="mt-4 space-y-3 text-sm">
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">Nome</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="ex.: Notícias de seguros diárias"
                    className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">O que fazer em cada execução (instruções do agente)</label>
                  <textarea
                    value={form.instructions}
                    onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                    rows={4}
                    placeholder="Descreva a tarefa completa, como se instruísse um assistente…"
                    className="w-full resize-y rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">Conhecimento (opcional) — usado em toda execução (argumentos, FAQ, tom de voz)</label>
                  <textarea
                    value={form.knowledge}
                    onChange={(e) => setForm({ ...form, knowledge: e.target.value })}
                    rows={3}
                    placeholder="Ex.: argumentos de venda, objeções comuns, FAQ do produto, tom de voz do outreach…"
                    className="w-full resize-y rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                <div className="flex gap-2">
                  {(['daily', 'interval'] as const).map((k) => (
                    <button
                      key={k}
                      onClick={() => setForm({ ...form, kind: k })}
                      className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${form.kind === k ? 'border-primary/60 bg-brand-soft text-foreground' : 'border-border bg-surface-2 text-muted-foreground'}`}
                    >
                      {k === 'daily' ? 'Diária (horário fixo)' : 'A cada N minutos'}
                    </button>
                  ))}
                </div>
                {form.kind === 'daily' ? (
                  <div className="flex gap-3">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">Horário (Brasília)</label>
                      <input
                        type="time"
                        value={form.time}
                        onChange={(e) => setForm({ ...form, time: e.target.value })}
                        className="rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none [color-scheme:dark]"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">Dias (0=seg … 6=dom; vazio = todos)</label>
                      <input
                        value={form.weekdays}
                        onChange={(e) => setForm({ ...form, weekdays: e.target.value })}
                        placeholder="ex.: 0,1,2,3,4"
                        className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none"
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">Intervalo (minutos, mín. 5)</label>
                    <input
                      type="number"
                      min={5}
                      value={form.minutes}
                      onChange={(e) => setForm({ ...form, minutes: parseInt(e.target.value || '5', 10) })}
                      className="w-32 rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none"
                    />
                  </div>
                )}
                <div className="flex gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">Entrega</label>
                    <div className="flex gap-2">
                      {(['whatsapp', 'none'] as const).map((c) => (
                        <button
                          key={c}
                          onClick={() => setForm({ ...form, channel: c })}
                          className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${form.channel === c ? 'border-primary/60 bg-brand-soft text-foreground' : 'border-border bg-surface-2 text-muted-foreground'}`}
                        >
                          {c === 'whatsapp' ? 'WhatsApp' : 'Só histórico'}
                        </button>
                      ))}
                    </div>
                  </div>
                  {form.channel === 'whatsapp' && (
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-medium text-muted-foreground">Número (DDI+DDD+número)</label>
                      <input
                        value={form.number}
                        onChange={(e) => setForm({ ...form, number: e.target.value })}
                        placeholder="5547999998888"
                        className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-foreground outline-none"
                      />
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-5 flex justify-end gap-2">
                <button
                  onClick={() => setEditing(null)}
                  disabled={saving}
                  className="rounded-md border border-border bg-surface-2 px-4 py-2 text-sm text-foreground"
                >
                  Cancelar
                </button>
                <button
                  onClick={saveRoutine}
                  disabled={saving || form.name.trim().length < 3 || form.instructions.trim().length < 10}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editing === 'new' ? 'Criar rotina' : 'Salvar alterações'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
