'use client';

// ─────────────────────────────────────────────────────────────────────────────
// CASOS — tudo o que já aconteceu, por EPISÓDIO (SPEC-097 · U5.2/R3/R10).
// ─────────────────────────────────────────────────────────────────────────────
//
// 🔴 A busca saiu daqui e foi para o banco.
//
//   📊 §1.5  esta tela lia a rota da Fila (que trazia no máximo 120 linhas de
//            448 — 73% invisível) e filtrava a busca com `.filter()` EM MEMÓRIA.
//            Procurar um protocolo de 60 dias devolvia **"nada encontrado"**
//            sem que ninguém tivesse perguntado ao banco. Um zero só vale
//            quando quem disse zero foi o banco.
//   📊 §1.4  e a lista era por CONVERSA. São 5,8 episódios por contato: seis
//            atendimentos diferentes da mesma pessoa viravam uma linha só.
//
// ⚠️ "Histórico" saiu do nome: aqui não mora só o passado — mora o CASO, esteja
// ele parado, esperando ou encerrado.
//
// 🔎 E a busca é o atalho do SEGURADO: digite o nome ou o telefone e a lista
// vira "os casos daquela pessoa". Não é um cadastro de clientes.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { History, Loader2, Search, TriangleAlert } from 'lucide-react';

import { DetailHeader, StatusPill } from '@/components/patterns';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import type { Caso } from '@/lib/atendimento/casos';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Payload {
  items: Caso[];
  cursor: string | null;
  has_more: boolean;
  indisponivel?: Record<string, boolean>;
}

/** O rótulo curto — esta é uma lista densa. O TOM vem da lista canônica. */
const ROTULO_CURTO: Record<Stage, string> = {
  precisa_de_voce: 'Precisa de você',
  acionando: 'Acionando',
  protocolo: 'Protocolo garantido',
  monitorando: 'Acompanhando prestador',
  em_conversa: 'Em conversa',
  com_equipe: 'Com a equipe',
  esperando: 'Esperando resposta',
  observacao: 'Atendimento da equipe',
  parado: 'Parado',
  concluido: 'Encerrado',
};

const FILTROS: { id: string; label: string; estagio?: Stage }[] = [
  { id: 'todos', label: 'Todos' },
  { id: 'precisa_de_voce', label: 'Precisa de você', estagio: 'precisa_de_voce' },
  { id: 'esperando', label: 'Esperando', estagio: 'esperando' },
  { id: 'parado', label: 'Parados', estagio: 'parado' },
  { id: 'concluido', label: 'Encerrados', estagio: 'concluido' },
];

function fmtWhen(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
    + ' às ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function fmtPhone(p: string | null): string {
  if (!p) return '';
  const d = p.replace(/\D/g, '');
  if (d.length >= 12) return `(${d.slice(2, 4)}) ${d.slice(4, -4)}-${d.slice(-4)}`;
  return p;
}

export default function HistoricoClient() {
  const router = useRouter();
  const params = useSearchParams();
  const buscaInicial = params?.get('busca') || params?.get('segurado') || '';

  const [items, setItems] = useState<Caso[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [temMais, setTemMais] = useState(false);
  const [query, setQuery] = useState(buscaInicial);
  const [termo, setTermo] = useState(buscaInicial);
  const [filtro, setFiltro] = useState('todos');
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [foraDoAr, setForaDoAr] = useState(false);
  const pedido = useRef(0);

  // 🔴 A busca vai ao SERVIDOR — com uma pausa para não disparar uma consulta
  //    por tecla digitada. O que ela NÃO faz é filtrar o que já está na tela.
  useEffect(() => {
    const t = setTimeout(() => setTermo(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  const url = useCallback((depoisDe?: string | null) => {
    const p = new URLSearchParams();
    if (termo) p.set('busca', termo);
    const f = FILTROS.find((x) => x.id === filtro);
    if (f?.estagio) p.set('estagio', f.estagio);
    if (depoisDe) p.set('cursor', depoisDe);
    return `/api/dashboard/atendimentos/casos?${p.toString()}`;
  }, [termo, filtro]);

  useEffect(() => {
    const meu = pedido.current + 1;
    pedido.current = meu;
    setItems(null);
    (async () => {
      try {
        const res = await fetch(url(), { cache: 'no-store' });
        if (!res.ok || pedido.current !== meu) return;
        const j: Payload = await res.json();
        setItems(j.items || []);
        setCursor(j.cursor);
        setTemMais(Boolean(j.has_more));
        setForaDoAr(Object.values(j.indisponivel || {}).some(Boolean));
      } catch {
        if (pedido.current === meu) setItems([]);
      }
    })();
  }, [url]);

  const carregarMais = async () => {
    if (!cursor || carregandoMais) return;
    setCarregandoMais(true);
    try {
      const res = await fetch(url(cursor), { cache: 'no-store' });
      if (res.ok) {
        const j: Payload = await res.json();
        setItems((atual) => [...(atual || []), ...(j.items || [])]);
        setCursor(j.cursor);
        setTemMais(Boolean(j.has_more));
      }
    } finally {
      setCarregandoMais(false);
    }
  };

  const lista = useMemo(() => items || [], [items]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.conversas}
          title="Casos"
          subtitle="Cada atendimento, do primeiro pedido ao desfecho — busque por nome, telefone ou protocolo."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Casos' }]}
        />

        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar o segurado por nome, telefone ou protocolo"
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          {items === null && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />}
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1">
          {FILTROS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFiltro(f.id)}
              className={cn(
                'shrink-0 rounded-full border px-3 py-1.5 text-xs transition-colors',
                filtro === f.id
                  ? 'border-primary/50 bg-brand-soft text-primary'
                  : 'border-border bg-surface text-muted-foreground hover:text-foreground',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {foraDoAr && (
          <p className="flex items-center gap-1.5 rounded-lg border border-warning/40 px-3 py-2 text-xs text-warning">
            <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
            Parte das informações não carregou agora — esta lista pode estar incompleta.
          </p>
        )}

        {items === null ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Procurando…
          </div>
        ) : lista.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <History className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">
              {termo ? `Nada encontrado para "${termo}"` : 'Nada por aqui ainda'}
            </p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              {termo
                ? 'Procuramos em todos os atendimentos da corretora — nome, telefone e protocolo.'
                : 'Cada atendimento fica registrado aqui, com a conversa completa para consultar quando quiser.'}
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {lista.map((i) => {
                const meta = STAGE_META[i.stage];
                return (
                  <button
                    key={i.key}
                    onClick={() => i.conversa_id && router.push(`/dashboard/atendimentos/ficha/${i.conversa_id}`)}
                    disabled={!i.conversa_id}
                    className={cn(
                      'w-full rounded-xl border border-border bg-surface p-3.5 text-left transition-colors',
                      i.conversa_id ? 'hover:border-primary/40 hover:bg-surface-2' : 'cursor-default',
                    )}
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="min-w-0 truncate text-sm font-semibold text-foreground">
                        {i.cliente || fmtPhone(i.telefone) || 'Segurado'}
                      </p>
                      <span className="shrink-0 text-[11px] text-muted-foreground">{fmtWhen(i.ultimo_evento_em)}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {i.agora?.situacao || i.detalhe}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      <StatusPill tone={meta?.tone || 'neutral'} label={ROTULO_CURTO[i.stage] || i.stage} />
                      {i.protocolo && (
                        <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                          {i.protocolo}
                        </span>
                      )}
                      {i.sem_conversa_vinculada && (
                        <span className="text-[11px] text-faint">sem conversa vinculada</span>
                      )}
                      <span className="flex-1" />
                      {i.conversa_id && <span className="text-[11px] text-primary">abrir o caso →</span>}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Paginação por cursor — nunca um teto fixo que esconde o resto. */}
            {temMais && (
              <button
                onClick={carregarMais}
                disabled={carregandoMais}
                className="mx-auto flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                {carregandoMais && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Carregar mais casos
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
