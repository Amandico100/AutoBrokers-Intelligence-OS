'use client';

import { useEffect, useState } from 'react';

type Channel = { label: string; kind: 'whatsapp' | 'phone'; available: boolean; number: string | null };
type Item = { insurer_key: string; display_name: string; active_corridors: number; has_active_corridor: boolean; channels: Channel[]; glass_service_portal_url: string | null; notes: string | null };

export function InsurersClient() {
  const [items, setItems] = useState<Item[] | null>(null);
  useEffect(() => { fetch('/api/dashboard/insurers').then((r) => r.json()).then((j) => { if (j?.ok) setItems(j.items); }).catch(() => {}); }, []);
  if (!items) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-3">
      {items.map((it) => (
        <div key={it.insurer_key} className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-foreground">{it.display_name}</p>
            {it.has_active_corridor
              ? <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">{it.active_corridors} corredor(es) ativo(s)</span>
              : <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">Sem corredor ativo</span>}
          </div>
          {it.channels.length > 0 && (
            <div className="mt-3 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {it.channels.map((c) => (
                <div key={c.label} className="flex items-center justify-between rounded-md border border-border bg-background px-2.5 py-1.5 text-[11px]">
                  <span className="text-muted-foreground">{c.label}{c.kind === 'whatsapp' ? ' 💬' : ''}</span>
                  <span className="font-mono text-foreground">{c.number ?? '—'}</span>
                </div>
              ))}
            </div>
          )}
          {it.glass_service_portal_url && <p className="mt-2 text-[11px] text-faint">Portal de vidros: {it.glass_service_portal_url}</p>}
        </div>
      ))}
      <p className="text-[10px] text-faint">Contatos globais curados pela plataforma (somente leitura). A Even usa apenas os corredores que sua corretora ativar.</p>
    </div>
  );
}
