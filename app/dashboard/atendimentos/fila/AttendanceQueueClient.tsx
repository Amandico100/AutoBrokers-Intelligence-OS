'use client';

// SPEC-043 — Fila de Atendimentos (pipeline ao vivo, mobile-first).
// O corretor vê em linguagem humana o que está acontecendo AGORA: quem precisa
// dele (topo, vermelho), o que está sendo acionado, o que já tem protocolo e
// o que o atendente/equipe está conversando. Estágios mudam sozinhos (poll).

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Headphones, Loader2, RefreshCw } from 'lucide-react';

import { DetailHeader, StatusPill } from '@/components/patterns';
import { STAGE_META, STAGES_EM_VOO, type Stage } from '@/lib/attendance/dispatch-states';
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

// O que é DESTA tela é a ORDEM — urgência primeiro, porque é assim que o
// corretor varre a fila. Rótulo, tom e a própria existência de cada estágio
// vêm da lista canônica; `Record<Stage, number>` obriga a dar posição a todo
// estágio novo, em vez de deixá-lo sumir da fila sem ninguém perceber.
const ORDEM_NA_FILA: Record<Stage, number> = {
  precisa_de_voce: 1,
  acionando: 2,
  monitorando: 3,
  protocolo: 4,
  em_conversa: 5,
  com_equipe: 6,
  observacao: 7,
  concluido: 99, // não entra na fila: vive na seção "Concluídos hoje"
};

const STAGES = [...STAGES_EM_VOO]
  .sort((a, b) => ORDEM_NA_FILA[a] - ORDEM_NA_FILA[b])
  .map((id) => ({ id, ...STAGE_META[id] }));

function fmtWhen(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
    + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function fmtPhone(p: string | null): string {
  if (!p) return '';
  const d = p.replace(/\D/g, '');
  if (d.length >= 12) return `(${d.slice(2, 4)}) ${d.slice(4, -4)}-${d.slice(-4)}`;
  return p;
}

export default function AttendanceQueueClient() {
  const router = useRouter();
  const [items, setItems] = useState<Item[] | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (manual?: boolean) => {
    if (manual) setRefreshing(true);
    try {
      const res = await fetch('/api/dashboard/atendimentos', { cache: 'no-store' });
      if (res.ok) {
        const j = await res.json();
        setItems(j.items || []);
      }
    } catch {
      /* próximo poll tenta de novo */
    } finally {
      if (manual) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => load(), 10000);
    return () => clearInterval(t);
  }, [load]);

  // SPEC-046: o clique abre a FICHA (dossiê vivo) — a conversa completa
  // vira um botão dentro dela.
  const open = (i: Item) => {
    if (i.conversa_id) router.push(`/dashboard/atendimentos/ficha/${i.conversa_id}`);
  };

  const live = (items || []).filter((i) => i.stage !== 'concluido');
  const doneToday = (items || []).filter((i) => {
    if (i.stage !== 'concluido' || !i.quando) return false;
    return new Date(i.quando).toDateString() === new Date().toDateString();
  });

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-5 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.conversas}
          title="Fila de Atendimentos"
          subtitle="Tudo que está acontecendo agora, em tempo real — o estágio muda sozinho."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Fila' }]}
        />

        <div className="flex items-center gap-3">
          <p className="text-xs text-muted-foreground">
            {items === null ? 'Carregando…' : `${live.length} em andamento · ${doneToday.length} concluído(s) hoje`}
          </p>
          <span className="flex-1" />
          <button
            onClick={() => load(true)}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Atualizar
          </button>
        </div>

        {items !== null && live.length === 0 && (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Headphones className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">Nenhum atendimento em andamento agora</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Quando um segurado chamar no WhatsApp — ou uma atendente iniciar um atendimento —
              ele aparece aqui na hora, com o estágio atualizado automaticamente.
            </p>
          </div>
        )}

        {STAGES.map((s) => {
          const group = live.filter((i) => i.stage === s.id);
          if (group.length === 0) return null;
          return (
            <section key={s.id}>
              <div className="mb-2 flex items-center gap-2">
                <StatusPill tone={s.tone} label={`${s.label} · ${group.length}`} />
                <span className="hidden text-[11px] text-muted-foreground sm:inline">{s.desc}</span>
              </div>
              <div className="space-y-2">
                {group.map((i) => (
                  <button
                    key={i.key}
                    onClick={() => open(i)}
                    disabled={!i.conversa_id}
                    className={cn(
                      'w-full rounded-xl border border-border bg-surface p-3.5 text-left transition-colors',
                      i.conversa_id ? 'hover:bg-surface-2' : 'cursor-default',
                      s.id === 'precisa_de_voce' && 'border-danger/40',
                    )}
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="min-w-0 truncate text-sm font-semibold text-foreground">
                        {i.titulo}
                        {i.cliente && i.kind === 'acionamento' ? ` — ${i.cliente}` : ''}
                      </p>
                      <span className="shrink-0 text-[11px] text-muted-foreground">{fmtWhen(i.quando)}</span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{i.detalhe}</p>
                    <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                      {i.telefone && <span className="font-mono">{fmtPhone(i.telefone)}</span>}
                      {i.protocolo && (
                        <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono">
                          protocolo {i.protocolo}
                        </span>
                      )}
                      <span className="flex-1" />
                      {i.conversa_id && <span className="text-primary">abrir ficha →</span>}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          );
        })}

        {doneToday.length > 0 && (
          <section>
            <div className="mb-2 flex items-center gap-2">
              <StatusPill tone="neutral" label={`Concluídos hoje · ${doneToday.length}`} />
            </div>
            <div className="space-y-2">
              {doneToday.slice(0, 10).map((i) => (
                <button
                  key={i.key}
                  onClick={() => open(i)}
                  disabled={!i.conversa_id}
                  className={cn(
                    'w-full rounded-xl border border-border/60 bg-surface p-3 text-left opacity-80 transition-opacity',
                    i.conversa_id ? 'hover:opacity-100' : 'cursor-default',
                  )}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="min-w-0 truncate text-sm text-foreground">{i.titulo}</p>
                    <span className="shrink-0 text-[11px] text-muted-foreground">{fmtWhen(i.quando)}</span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{i.detalhe}</p>
                </button>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              O histórico completo, com busca, está em{' '}
              <a href="/dashboard/atendimentos/casos" className="text-primary">Histórico</a>.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
