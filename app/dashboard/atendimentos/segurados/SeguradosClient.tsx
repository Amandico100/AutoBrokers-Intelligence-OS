'use client';

// SPEC-043 — Segurados atendidos (lista real derivada dos atendimentos).
// Mobile-first: busca + cartões com contato e último atendimento.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Search, Users } from 'lucide-react';

import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Segurado {
  telefone: string;
  nome: string | null;
  atendimentos: number;
  ultimo_contato: string | null;
  conversa_id: string | null;
}

function fmtPhone(p: string): string {
  const d = p.replace(/\D/g, '');
  if (d.length >= 12) return `(${d.slice(2, 4)}) ${d.slice(4, -4)}-${d.slice(-4)}`;
  return p;
}

function fmtWhen(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return 'hoje ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

export default function SeguradosClient() {
  const router = useRouter();
  const [segurados, setSegurados] = useState<Segurado[] | null>(null);
  const [query, setQuery] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/atendimentos/segurados', { cache: 'no-store' });
      if (res.ok) setSegurados((await res.json()).segurados || []);
    } catch {
      /* próximo poll */
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (segurados || []).filter(
      (s) => !q || (s.nome || '').toLowerCase().includes(q) || s.telefone.includes(q.replace(/\D/g, '') || q),
    );
  }, [segurados, query]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.equipe}
          title="Segurados"
          subtitle="Clientes atendidos pela corretora — a lista cresce sozinha a cada atendimento."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Segurados' }]}
        />

        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por nome ou telefone"
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
        </div>

        {segurados === null ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando segurados…
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Users className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">Nenhum segurado registrado ainda</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Assim que os atendimentos começarem, cada cliente atendido aparece aqui com o histórico dele.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {filtered.map((s) => (
              <button
                key={s.telefone}
                onClick={() => s.conversa_id && router.push(`/dashboard/atendimentos/conversas?open=${s.conversa_id}`)}
                disabled={!s.conversa_id}
                className={cn(
                  'flex items-center gap-3 rounded-xl border border-border bg-surface p-3.5 text-left transition-colors',
                  s.conversa_id ? 'hover:bg-surface-2' : 'cursor-default',
                )}
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 text-sm font-semibold text-muted-foreground">
                  {(s.nome || s.telefone).charAt(0).toUpperCase()}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">
                    {s.nome || fmtPhone(s.telefone)}
                  </span>
                  <span className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                    <span className="font-mono">{fmtPhone(s.telefone)}</span>
                    <span>· {s.atendimentos} atendimento{s.atendimentos > 1 ? 's' : ''}</span>
                    <span className="flex-1" />
                    <span>{fmtWhen(s.ultimo_contato)}</span>
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
