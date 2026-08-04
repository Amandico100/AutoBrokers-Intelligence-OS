'use client';

// SPEC-043 — Histórico de atendimentos (mobile-first, linguagem humana).
// Tudo que já aconteceu: conversas, acionamentos e atendimentos observados,
// com busca e filtro simples. Toque abre a conversa correspondente.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { History, Loader2, Search } from 'lucide-react';

import { DetailHeader, StatusPill } from '@/components/patterns';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Item {
  key: string;
  stage: Stage;
  kind: 'conversa' | 'acionamento' | 'observacao';
  titulo: string;
  detalhe: string;
  cliente: string | null;
  telefone: string | null;
  quando: string | null;
  conversa_id: string | null;
  protocolo: string | null;
}

// O histórico é uma LISTA densa: aqui o rótulo é a versão curta ("Acionando",
// não "Acionando a seguradora"). Essa diferença é de tela, e por isso fica.
// O TOM vem da lista canônica — e `Record<Stage, string>` obriga a batizar todo
// estágio novo, em vez de deixá-lo cair num rótulo genérico.
const ROTULO_CURTO: Record<Stage, string> = {
  precisa_de_voce: 'Precisa de você',
  acionando: 'Acionando',
  protocolo: 'Protocolo garantido',
  monitorando: 'Acompanhando prestador',
  em_conversa: 'Em conversa',
  com_equipe: 'Com a equipe',
  observacao: 'Equipe (observado)',
  concluido: 'Concluído',
};

// 📊 O filtro "Concluídos" (auditoria de 04/08/2026) nunca encontrava um caso
// `encaminhado` nem `resolvido`: o defeito não era este teste, era o estágio
// que chegava da API — a rota mandava 'acionando' para os dois. Com
// `stageFromDispatchState` na rota, `concluido` passou a significar CONCLUÍDO,
// e este `===` finalmente vale o que promete.
const FILters: { id: string; label: string; test: (i: Item) => boolean }[] = [
  { id: 'todos', label: 'Todos', test: () => true },
  { id: 'andamento', label: 'Em andamento', test: (i) => i.stage !== 'concluido' },
  { id: 'urgente', label: 'Precisa de você', test: (i) => i.stage === 'precisa_de_voce' },
  { id: 'acionamentos', label: 'Acionamentos', test: (i) => i.kind === 'acionamento' },
  { id: 'concluidos', label: 'Concluídos', test: (i) => i.stage === 'concluido' },
];

function fmtWhen(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
    + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

export default function HistoricoClient() {
  const router = useRouter();
  const [items, setItems] = useState<Item[] | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('todos');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/atendimentos', { cache: 'no-store' });
      if (res.ok) setItems((await res.json()).items || []);
    } catch {
      /* próximo poll */
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const f = FILters.find((x) => x.id === filter) || FILters[0];
    return (items || [])
      .filter(f.test)
      .filter((i) => !q
        || i.titulo.toLowerCase().includes(q)
        || (i.cliente || '').toLowerCase().includes(q)
        || (i.telefone || '').includes(q.replace(/\D/g, '') || q)
        || (i.protocolo || '').toLowerCase().includes(q))
      .sort((a, b) => String(b.quando || '').localeCompare(String(a.quando || '')));
  }, [items, query, filter]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.conversas}
          title="Histórico de atendimentos"
          subtitle="Tudo que já aconteceu — busque por cliente, telefone ou protocolo."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Histórico' }]}
        />

        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por cliente, telefone ou protocolo"
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1">
          {FILters.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={cn(
                'shrink-0 rounded-full border px-3 py-1.5 text-xs transition-colors',
                filter === f.id
                  ? 'border-primary/50 bg-brand-soft text-primary'
                  : 'border-border bg-surface text-muted-foreground hover:text-foreground',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {items === null ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando histórico…
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <History className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">Nada por aqui ainda</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Cada atendimento concluído fica registrado aqui, com a conversa completa para você consultar quando quiser.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((i) => {
              const tom = STAGE_META[i.stage]?.tone || 'neutral';
              const rotulo = ROTULO_CURTO[i.stage] || i.stage;
              return (
                <button
                  key={i.key}
                  onClick={() => i.conversa_id && router.push(`/dashboard/atendimentos/ficha/${i.conversa_id}`)}
                  disabled={!i.conversa_id}
                  className={cn(
                    'w-full rounded-xl border border-border bg-surface p-3.5 text-left transition-colors',
                    i.conversa_id ? 'hover:bg-surface-2' : 'cursor-default',
                  )}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="min-w-0 truncate text-sm font-semibold text-foreground">{i.titulo}</p>
                    <span className="shrink-0 text-[11px] text-muted-foreground">{fmtWhen(i.quando)}</span>
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{i.detalhe}</p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <StatusPill tone={tom} label={rotulo} />
                    {i.protocolo && (
                      <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                        {i.protocolo}
                      </span>
                    )}
                    <span className="flex-1" />
                    {i.conversa_id && <span className="text-[11px] text-primary">ver ficha →</span>}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
