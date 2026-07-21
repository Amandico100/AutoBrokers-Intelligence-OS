'use client';

import { useEffect, useState } from 'react';

type Group = { key: string; cost_brl: number; tokens: number };
type PerUser = { user_id: string; name: string; tokens: number; cost_usd: number };
type Data = { balance_brl: number; alert_80: boolean; alert_100: boolean; period_total_brl: number; period_tokens: number; by_agent: Group[]; by_model: Group[]; has_data: boolean; per_user?: PerUser[] };

const brl = (n: number) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const int = (n: number) => n.toLocaleString('pt-BR');

export function UsageClient() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => { fetch('/api/dashboard/usage').then((r) => r.json()).then((j) => { if (j?.ok) setD(j); }).catch(() => {}); }, []);
  if (!d) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className={`rounded-lg border p-4 ${d.alert_100 ? 'border-red-500/30 bg-red-500/5' : d.alert_80 ? 'border-amber-500/30 bg-amber-500/5' : 'border-border bg-card'}`}>
          <p className="text-[11px] uppercase tracking-wide text-faint">Saldo</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{brl(d.balance_brl)}</p>
          {d.alert_100 ? <p className="text-[11px] text-red-600">Saldo esgotado</p> : d.alert_80 ? <p className="text-[11px] text-amber-600">Saldo baixo</p> : null}
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-[11px] uppercase tracking-wide text-faint">Consumo (30 dias)</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{brl(d.period_total_brl)}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-[11px] uppercase tracking-wide text-faint">Tokens (30 dias)</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{int(d.period_tokens)}</p>
        </div>
      </div>

      {!d.has_data && <p className="text-sm text-muted-foreground">Ainda não há consumo registrado neste período.</p>}

      {d.by_agent.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-2 text-sm font-medium text-foreground">Por agente</p>
          {d.by_agent.map((g) => (
            <div key={g.key} className="flex items-center justify-between border-t border-border py-1.5 text-[12px] first:border-0">
              <span className="text-muted-foreground">{g.key}</span>
              <span className="text-foreground">{brl(g.cost_brl)} · {int(g.tokens)} tokens</span>
            </div>
          ))}
        </div>
      )}

      {(d.per_user?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-2 text-sm font-medium text-foreground">Por pessoa (Chat Principal, 30 dias)</p>
          {(() => {
            const total = d.per_user!.reduce((a, b) => a + b.tokens, 0) || 1;
            return d.per_user!.map((u) => (
              <div key={u.user_id} className="flex items-center justify-between border-t border-border py-1.5 text-[12px] first:border-0">
                <span className="text-muted-foreground">{u.name}</span>
                <span className="text-foreground">{int(u.tokens)} tokens · {Math.round((u.tokens / total) * 100)}% do uso</span>
              </div>
            ));
          })()}
        </div>
      )}

      {d.by_model.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-2 text-sm font-medium text-foreground">Por modelo</p>
          {d.by_model.map((g) => (
            <div key={g.key} className="flex items-center justify-between border-t border-border py-1.5 text-[12px] first:border-0">
              <span className="text-muted-foreground">{g.key}</span>
              <span className="text-foreground">{brl(g.cost_brl)} · {int(g.tokens)} tokens</span>
            </div>
          ))}
        </div>
      )}
      <p className="text-[10px] text-faint">Valores reais do seu consumo. Nenhum custo é estimado ou inventado.</p>
    </div>
  );
}
