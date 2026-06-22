'use client';

import { useEffect, useState } from 'react';

type Member = { name: string; email: string | null; role_label: string; is_owner: boolean; status: string | null; last_login_at: string | null };

export function TeamClient() {
  const [members, setMembers] = useState<Member[] | null>(null);
  useEffect(() => { fetch('/api/dashboard/team').then((r) => r.json()).then((j) => { if (j?.ok) setMembers(j.members); }).catch(() => {}); }, []);
  if (!members) return <p className="text-sm text-muted-foreground">Carregando…</p>;
  if (members.length === 0) return <p className="text-sm text-muted-foreground">Nenhum membro cadastrado.</p>;

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-border bg-card divide-y divide-border">
        {members.map((m, i) => (
          <div key={i} className="flex items-center justify-between gap-3 p-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{m.name} {m.is_owner && <span className="ml-1 rounded-full border border-border px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-faint">dono</span>}</p>
              {m.email && <p className="truncate text-[11px] text-faint">{m.email}</p>}
            </div>
            <div className="shrink-0 text-right">
              <p className="text-[12px] text-muted-foreground">{m.role_label}</p>
              {m.status && <p className="text-[10px] text-faint">{m.status}</p>}
            </div>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-faint">Convite e alteração de papel reutilizam o fluxo seguro existente. Papéis são controlados (sem RBAC paralelo).</p>
    </div>
  );
}
