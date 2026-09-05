'use client';

// SPEC-043 — Segurados atendidos (lista real derivada dos atendimentos).
// SPEC-046 — o clique abre um PERFIL leve: dados + lista de atendimentos,
// e cada atendimento abre a Ficha (não mais a conversa crua direto).
//
// 🔴 SPEC-097 — ISTO NÃO É UM CRM, e passou a não fingir que é. Segurado é um
// ATALHO DE BUSCA: "ver todos os casos desta pessoa" leva para Casos com o
// telefone já buscado — a MESMA busca, no MESMO banco, com a mesma resposta.
// Uma segunda lista de pessoas, com a sua própria noção de "atendimento",
// seria o motor paralelo que o CLAUDE.md §5 proíbe.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronDown, Loader2, Search, Users } from 'lucide-react';

import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Atendimento {
  conversa_id: string;
  quando: string | null;
  preview: string | null;
}

interface Segurado {
  telefone: string;
  nome: string | null;
  atendimentos: number;
  ultimo_contato: string | null;
  conversa_id: string | null;
  historico: Atendimento[];
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
  const [openPhone, setOpenPhone] = useState<string | null>(null);

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
      (s) =>
        !q ||
        (s.nome || '').toLowerCase().includes(q) ||
        s.telefone.includes(q.replace(/\D/g, '') || q),
    );
  }, [segurados, query]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.equipe}
          title="Segurados"
          subtitle="Encontre a pessoa e veja os casos dela — a lista cresce sozinha a cada atendimento."
          breadcrumb={[
            { label: 'Atendimentos', href: '/dashboard/atendimentos' },
            { label: 'Segurados' },
          ]}
        />

        {/* 🔎 U5.5 — ISTO É UMA BUSCA, não um cadastro. Digitar aqui e apertar
            Enter leva DIRETO para os casos daquela pessoa, na mesma busca do
            mesmo banco. A lista abaixo é só o atalho de quem não quer digitar. */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const q = query.trim();
            if (q) router.push(`/dashboard/atendimentos/casos?busca=${encodeURIComponent(q)}`);
          }}
          className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2.5 focus-within:border-primary/50"
        >
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar o segurado por nome ou telefone"
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          {Boolean(query.trim()) && (
            <button
              type="submit"
              className="shrink-0 whitespace-nowrap text-xs font-medium text-primary"
            >
              ver os casos →
            </button>
          )}
        </form>

        {segurados === null ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando segurados…
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Users className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">
              Nenhum segurado registrado ainda
            </p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Assim que os atendimentos começarem, cada cliente atendido aparece aqui com o
              histórico dele.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((s) => {
              const aberto = openPhone === s.telefone;
              const podeAbrir = s.historico.length > 0;
              return (
                <div
                  key={s.telefone}
                  className="overflow-hidden rounded-xl border border-border bg-surface"
                >
                  {/* 🔴 O CLIQUE PRINCIPAL É A BUSCA: vai para os casos desta
                      pessoa. A gaveta (a seta) é o atalho para uma ficha
                      específica — o secundário, e ele parece secundário. */}
                  <div className="flex items-center">
                    <button
                      onClick={() =>
                        router.push(
                          `/dashboard/atendimentos/casos?busca=${encodeURIComponent(s.telefone)}`,
                        )
                      }
                      className="flex min-w-0 flex-1 items-center gap-3 p-3.5 text-left transition-colors hover:bg-surface-2"
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
                          <span>
                            · {s.atendimentos} atendimento{s.atendimentos > 1 ? 's' : ''}
                          </span>
                          <span className="flex-1" />
                          <span>{fmtWhen(s.ultimo_contato)}</span>
                        </span>
                      </span>
                      <span className="shrink-0 whitespace-nowrap text-[11px] text-primary">
                        ver os casos →
                      </span>
                    </button>
                    {podeAbrir && (
                      <button
                        onClick={() => setOpenPhone(aberto ? null : s.telefone)}
                        aria-label={
                          aberto
                            ? 'Fechar os atendimentos recentes'
                            : 'Ver os atendimentos recentes'
                        }
                        aria-expanded={aberto}
                        className="flex h-14 w-12 shrink-0 items-center justify-center border-l border-border/60 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
                      >
                        <ChevronDown
                          className={cn('h-4 w-4 transition-transform', aberto && 'rotate-180')}
                        />
                      </button>
                    )}
                  </div>

                  {aberto && (
                    <div className="border-t border-border/60 px-3.5 py-2.5">
                      <div className="mb-2 flex items-baseline gap-2">
                        <p className="text-[11px] font-medium text-muted-foreground">
                          Atendimentos deste segurado
                        </p>
                        <span className="flex-1" />
                        <button
                          onClick={() =>
                            router.push(
                              `/dashboard/atendimentos/casos?busca=${encodeURIComponent(s.telefone)}`,
                            )
                          }
                          className="text-[11px] text-primary hover:underline"
                        >
                          ver todos os casos →
                        </button>
                      </div>
                      <div className="space-y-1.5">
                        {s.historico.map((a) => (
                          <button
                            key={a.conversa_id}
                            onClick={() =>
                              router.push(`/dashboard/atendimentos/ficha/${a.conversa_id}`)
                            }
                            className="flex w-full items-baseline gap-2 rounded-lg border border-border/60 bg-surface-2 px-3 py-2 text-left transition-colors hover:bg-brand-soft"
                          >
                            <span className="shrink-0 text-[11px] text-muted-foreground">
                              {fmtWhen(a.quando)}
                            </span>
                            <span className="min-w-0 flex-1 truncate text-xs text-foreground">
                              {a.preview || 'Atendimento registrado'}
                            </span>
                            <span className="shrink-0 text-[11px] text-primary">ficha →</span>
                          </button>
                        ))}
                      </div>
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
