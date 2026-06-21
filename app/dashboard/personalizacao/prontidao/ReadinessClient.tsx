'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type Item = { key: string; label: string; status: 'ready' | 'pending' | 'not_applicable' | 'blocked'; reason: string; action: string; href: string | null; critical: boolean };
type Data = { items: Item[]; production_ready: boolean; ready_count: number; total: number };

const STATUS: Record<string, { label: string; cls: string; dot: string }> = {
  ready: { label: 'Pronto', cls: 'text-emerald-600', dot: 'bg-emerald-500' },
  pending: { label: 'Pendente', cls: 'text-amber-600', dot: 'bg-amber-500' },
  blocked: { label: 'Bloqueado', cls: 'text-red-600', dot: 'bg-red-500' },
  not_applicable: { label: 'Opcional', cls: 'text-muted-foreground', dot: 'bg-border' },
};

export function ReadinessClient() {
  const [data, setData] = useState<Data | null>(null);
  useEffect(() => { fetch('/api/dashboard/readiness').then((r) => r.json()).then((j) => { if (j?.ok) setData(j); }).catch(() => {}); }, []);
  if (!data) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-4">
      <div className={`rounded-lg border p-4 ${data.production_ready ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-amber-500/30 bg-amber-500/5'}`}>
        <p className="text-sm font-semibold text-foreground">
          {data.production_ready ? 'Tudo pronto para o piloto entrar no ar.' : 'Ainda faltam itens para o piloto entrar no ar.'}
        </p>
        <p className="mt-1 text-[12px] text-muted-foreground">{data.ready_count} de {data.total} itens prontos. Os itens críticos precisam estar prontos antes de operar de verdade.</p>
      </div>

      <div className="rounded-lg border border-border bg-card divide-y divide-border">
        {data.items.map((it) => {
          const s = STATUS[it.status] ?? STATUS.pending;
          return (
            <div key={it.key} className="flex items-start gap-3 p-3">
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${s.dot}`} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-foreground">{it.label}</p>
                  {it.critical && <span className="rounded-full border border-border px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-faint">crítico</span>}
                  <span className={`text-[11px] ${s.cls}`}>{s.label}</span>
                </div>
                <p className="mt-0.5 text-[12px] text-muted-foreground">{it.reason}</p>
              </div>
              {it.href && it.status !== 'ready' && (
                <Link href={it.href} className="shrink-0 rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2">{it.action}</Link>
              )}
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-faint">Esta tela apenas reflete a configuração. Não liga canais, não abre portais e não envia mensagens.</p>
    </div>
  );
}
