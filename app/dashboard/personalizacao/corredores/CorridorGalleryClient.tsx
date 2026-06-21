'use client';

import { useCallback, useEffect, useState } from 'react';

type Item = {
  template_id: string;
  title: string;
  insurer_key: string | null;
  line_kind: string | null;
  macro_service: string | null;
  status: 'available' | 'active' | 'paused' | 'needs_channel' | 'needs_portal';
  installed: boolean;
  requirements: string[];
  next_step: string;
};

const STATUS_META: Record<string, { label: string; cls: string }> = {
  active: { label: 'Ativo', cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' },
  paused: { label: 'Pausado', cls: 'border-amber-500/30 bg-amber-500/10 text-amber-600' },
  available: { label: 'Disponível', cls: 'border-border bg-surface-2 text-muted-foreground' },
};

export function CorridorGalleryClient() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [busy, setBusy] = useState<string>('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    const j = await fetch('/api/dashboard/corridors').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) setItems(j.items);
    else setNotice(j?.error || 'Falha ao carregar.');
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (templateId: string, action: 'activate' | 'pause' | 'resume') => {
    setBusy(templateId); setNotice('');
    const r = await fetch(`/api/dashboard/corridors/${templateId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) await load(); else setNotice(`Falha: ${j?.error || r.status}`);
    setBusy('');
  };

  if (!items) return <p className="text-sm text-muted-foreground">Carregando…</p>;
  if (items.length === 0) return <p className="text-sm text-muted-foreground">Nenhum corredor disponível ainda.</p>;

  return (
    <div className="space-y-3">
      {notice && <p className="text-[12px] text-amber-600">{notice}</p>}
      {items.map((it) => {
        const meta = STATUS_META[it.status] ?? STATUS_META.available;
        const subtitle = [it.insurer_key, it.line_kind, it.macro_service].filter(Boolean).join(' · ');
        return (
          <div key={it.template_id} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">{it.title}</p>
                {subtitle && <p className="mt-0.5 text-[11px] text-faint">{subtitle}</p>}
              </div>
              <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${meta.cls}`}>{meta.label}</span>
            </div>

            {it.requirements.length > 0 && (
              <ul className="mt-3 space-y-0.5 text-[11px] text-muted-foreground">
                {it.requirements.map((r) => <li key={r}>• {r}</li>)}
              </ul>
            )}
            <p className="mt-2 text-[11px] text-faint">{it.next_step}</p>

            <div className="mt-3 flex flex-wrap gap-2">
              {it.status !== 'active' && it.status !== 'paused' && (
                <button onClick={() => act(it.template_id, 'activate')} disabled={busy === it.template_id} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Ativar</button>
              )}
              {it.status === 'active' && (
                <button onClick={() => act(it.template_id, 'pause')} disabled={busy === it.template_id} className="rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Pausar</button>
              )}
              {it.status === 'paused' && (
                <button onClick={() => act(it.template_id, 'resume')} disabled={busy === it.template_id} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Retomar</button>
              )}
            </div>
          </div>
        );
      })}
      <p className="text-[10px] text-faint">Ativar um corredor apenas o disponibiliza para a corretora. Nenhuma ação externa, envio ou portal é executado aqui.</p>
    </div>
  );
}
