'use client';

// SPEC-019 C — CRUD master das Rotinas Prontas (routine_templates) que aparecem
// na galeria das corretoras. Elementos nativos (o /admin renderiza portais Radix
// fora do tema — regra do guia). "Usar modelo" na corretora pré-preenche a rotina.

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Trash2, Pencil, Power } from 'lucide-react';

type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  instructions: string;
  schedule_default: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
  delivery_default: { channel?: string };
  required: Record<string, boolean>;
  is_active: boolean;
  sort_order: number;
};

type FormState = {
  id: string;
  name: string;
  description: string;
  category: string;
  instructions: string;
  kind: string;
  time: string;
  weekdays: string;
  minutes: number;
  channel: string;
  req_whatsapp: boolean;
  req_web: boolean;
  req_infocap: boolean;
  req_portal: boolean;
  is_active: boolean;
  sort_order: number;
};

const EMPTY: FormState = {
  id: '', name: '', description: '', category: 'Geral', instructions: '',
  kind: 'daily', time: '08:00', weekdays: '', minutes: 60, channel: 'whatsapp',
  req_whatsapp: true, req_web: false, req_infocap: false, req_portal: false,
  is_active: true, sort_order: 100,
};

const inputCls =
  'w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring';

export default function AdminRoutineTemplatesPage() {
  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/routine-templates', { cache: 'no-store' });
      const j = await res.json();
      if (!res.ok) { setNotice(j.error || 'Erro ao carregar.'); setTemplates([]); return; }
      setTemplates(j.templates || []);
    } catch { setNotice('Falha de conexão.'); setTemplates([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const editFrom = (t: Template) => {
    const s = t.schedule_default || {};
    const req = t.required || {};
    setForm({
      id: t.id, name: t.name, description: t.description || '', category: t.category || 'Geral',
      instructions: t.instructions, kind: s.kind === 'interval' ? 'interval' : 'daily',
      time: s.time || '08:00', weekdays: (s.weekdays || []).join(','), minutes: s.minutes || 60,
      channel: t.delivery_default?.channel === 'none' ? 'none' : 'whatsapp',
      req_whatsapp: !!req.whatsapp, req_web: !!req.web, req_infocap: !!req.infocap, req_portal: !!req.portal,
      is_active: t.is_active, sort_order: t.sort_order ?? 100,
    });
  };

  const save = async () => {
    if (!form) return;
    setSaving(true); setNotice('');
    const schedule_default = form.kind === 'interval'
      ? { kind: 'interval', minutes: Number(form.minutes) }
      : {
          kind: 'daily', time: form.time,
          ...(form.weekdays.trim()
            ? { weekdays: form.weekdays.split(',').map((d) => parseInt(d.trim(), 10)).filter((n) => !isNaN(n)) }
            : {}),
        };
    const required: Record<string, boolean> = {};
    if (form.req_whatsapp) required.whatsapp = true;
    if (form.req_web) required.web = true;
    if (form.req_infocap) required.infocap = true;
    if (form.req_portal) required.portal = true;

    const res = await fetch('/api/admin/routine-templates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: form.id || undefined,
        name: form.name, description: form.description, category: form.category,
        instructions: form.instructions, schedule_default,
        delivery_default: { channel: form.channel }, required,
        is_active: form.is_active, sort_order: Number(form.sort_order),
      }),
    });
    const j = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) { setNotice(j.error || 'Erro ao salvar.'); return; }
    setForm(null); load();
  };

  const toggleActive = async (t: Template) => {
    await fetch('/api/admin/routine-templates', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...t, is_active: !t.is_active }),
    });
    load();
  };

  const del = async (t: Template) => {
    if (!confirm(`Excluir o modelo "${t.name}"?`)) return;
    await fetch(`/api/admin/routine-templates?id=${t.id}`, { method: 'DELETE' });
    load();
  };

  return (
    <div className="p-8">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Rotinas Prontas</h1>
            <p className="text-sm text-muted-foreground">Modelos globais que aparecem na galeria das corretoras (&quot;Usar modelo&quot;).</p>
          </div>
          <button
            onClick={() => setForm({ ...EMPTY })}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="h-4 w-4" /> Novo modelo
          </button>
        </div>

        {notice && <p className="text-sm text-amber-600">{notice}</p>}

        {templates === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Carregando…</div>
        ) : (
          <div className="space-y-2">
            {templates.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">Nenhum modelo. Crie o primeiro.</p>}
            {templates.map((t) => (
              <div key={t.id} className="flex items-start justify-between gap-3 rounded-lg border border-border bg-surface p-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-foreground">{t.name}</p>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] ${t.is_active ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' : 'border-border bg-surface-2 text-muted-foreground'}`}>
                      {t.is_active ? 'ativo' : 'inativo'}
                    </span>
                    <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">{t.category}</span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{t.description}</p>
                  <p className="mt-0.5 text-[11px] text-faint">
                    {t.schedule_default?.kind === 'interval' ? `a cada ${t.schedule_default?.minutes} min` : `diária às ${t.schedule_default?.time || '08:00'}`}
                    {' · requer: '}{Object.keys(t.required || {}).filter((k) => (t.required as Record<string, boolean>)[k]).join(', ') || 'nada'}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <button onClick={() => toggleActive(t)} title={t.is_active ? 'Desativar' : 'Ativar'} className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground hover:text-foreground"><Power className="h-3.5 w-3.5" /></button>
                  <button onClick={() => editFrom(t)} title="Editar" className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground hover:text-foreground"><Pencil className="h-3.5 w-3.5" /></button>
                  <button onClick={() => del(t)} title="Excluir" className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground hover:text-danger"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            ))}
          </div>
        )}

        {form && (
          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-base font-semibold text-foreground">{form.id ? 'Editar modelo' : 'Novo modelo'}</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Nome</label>
                <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Categoria</label>
                <input className={inputCls} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Ordem (menor = topo)</label>
                <input type="number" className={inputCls} value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value || '100', 10) })} />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Descrição (card da galeria)</label>
                <input className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Instruções (o que o agente faz em cada execução)</label>
                <textarea rows={4} className={`${inputCls} resize-y`} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Agenda</label>
                <select className={`${inputCls} [color-scheme:dark]`} value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                  <option value="daily">Diária (horário fixo)</option>
                  <option value="interval">A cada N minutos</option>
                </select>
              </div>
              {form.kind === 'daily' ? (
                <div className="flex gap-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">Horário</label>
                    <input type="time" className={`${inputCls} [color-scheme:dark]`} value={form.time} onChange={(e) => setForm({ ...form, time: e.target.value })} />
                  </div>
                  <div className="flex-1">
                    <label className="mb-1 block text-xs font-medium text-muted-foreground">Dias (0=seg…6=dom; vazio=todos)</label>
                    <input className={inputCls} placeholder="0,1,2,3,4" value={form.weekdays} onChange={(e) => setForm({ ...form, weekdays: e.target.value })} />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">Intervalo (min, mín. 5)</label>
                  <input type="number" min={5} className={inputCls} value={form.minutes} onChange={(e) => setForm({ ...form, minutes: parseInt(e.target.value || '5', 10) })} />
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Entrega padrão</label>
                <select className={`${inputCls} [color-scheme:dark]`} value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })}>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="none">Só histórico</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Requer (mostra o que falta conectar na galeria)</label>
                <div className="flex flex-wrap gap-3 text-xs text-foreground">
                  <label className="flex items-center gap-1.5"><input type="checkbox" checked={form.req_whatsapp} onChange={(e) => setForm({ ...form, req_whatsapp: e.target.checked })} /> WhatsApp</label>
                  <label className="flex items-center gap-1.5"><input type="checkbox" checked={form.req_web} onChange={(e) => setForm({ ...form, req_web: e.target.checked })} /> Web search</label>
                  <label className="flex items-center gap-1.5"><input type="checkbox" checked={form.req_infocap} onChange={(e) => setForm({ ...form, req_infocap: e.target.checked })} /> InfoCap</label>
                  <label className="flex items-center gap-1.5"><input type="checkbox" checked={form.req_portal} onChange={(e) => setForm({ ...form, req_portal: e.target.checked })} /> Portais</label>
                  <label className="ml-auto flex items-center gap-1.5"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Ativo (visível na galeria)</label>
                </div>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setForm(null)} disabled={saving} className="rounded-md border border-border bg-surface-2 px-4 py-2 text-sm text-foreground">Cancelar</button>
              <button onClick={save} disabled={saving || form.name.trim().length < 3 || form.instructions.trim().length < 10} className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}{form.id ? 'Salvar' : 'Criar modelo'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
