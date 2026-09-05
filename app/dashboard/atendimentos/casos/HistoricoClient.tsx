'use client';

// ─────────────────────────────────────────────────────────────────────────────
// CASOS — tudo o que já aconteceu, por EPISÓDIO (SPEC-097 · U5.2/R3/R10/R12).
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
// 🔎 E a busca é o atalho do SEGURADO (U5.5): digite o nome ou o telefone e a
// lista vira "os casos daquela pessoa". Não é um cadastro de clientes.
//
// 📱 MOBILE-FIRST (R12): a busca e os filtros ficam GRUDADOS no topo enquanto a
// lista rola — no celular, rolar de volta para trocar de filtro é o momento em
// que a pessoa desiste. A linha do caso é a mesma peça da Fila.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { History, Loader2, Search, TriangleAlert, X } from 'lucide-react';

import { DetailHeader } from '@/components/patterns';
import { LinhaDoCaso, fmtPhone } from '@/components/atendimento/caso-visual';
import type { Stage } from '@/lib/attendance/dispatch-states';
import type { Caso } from '@/lib/atendimento/casos';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Payload {
  items: Caso[];
  cursor: string | null;
  has_more: boolean;
  indisponivel?: Record<string, boolean>;
  /** o termo tinha só curinga e não sobrou letra nenhuma — a lista volta vazia
   *  DE PROPÓSITO, e a tela diz isso em vez de "nada encontrado". */
  busca_invalida?: boolean;
}

const FILTROS: { id: string; label: string; estagio?: Stage }[] = [
  { id: 'todos', label: 'Todos' },
  { id: 'precisa_de_voce', label: 'Precisa de você', estagio: 'precisa_de_voce' },
  { id: 'esperando', label: 'Esperando', estagio: 'esperando' },
  { id: 'parado', label: 'Parados', estagio: 'parado' },
  { id: 'concluido', label: 'Encerrados', estagio: 'concluido' },
];

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
  const [buscaInvalida, setBuscaInvalida] = useState(false);
  const pedido = useRef(0);

  // 🔴 A busca vai ao SERVIDOR — com uma pausa para não disparar uma consulta
  //    por tecla digitada. O que ela NÃO faz é filtrar o que já está na tela.
  useEffect(() => {
    const t = setTimeout(() => setTermo(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  const url = useCallback(
    (depoisDe?: string | null) => {
      const p = new URLSearchParams();
      if (termo) p.set('busca', termo);
      const f = FILTROS.find((x) => x.id === filtro);
      if (f?.estagio) p.set('estagio', f.estagio);
      if (depoisDe) p.set('cursor', depoisDe);
      return `/api/dashboard/atendimentos/casos?${p.toString()}`;
    },
    [termo, filtro],
  );

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
        setBuscaInvalida(Boolean(j.busca_invalida));
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

  /** Quando a busca é um telefone, a tela DIZ de quem são os casos: é o atalho
   *  vindo de Segurados, e sem esta linha ele parece uma busca qualquer. */
  const pessoaDaBusca = useMemo(() => {
    if (!termo || !lista.length) return null;
    const so = /^[\d\s()+-]+$/.test(termo);
    if (!so) return null;
    const nomes = Array.from(new Set(lista.map((i) => i.cliente).filter(Boolean)));
    return nomes.length === 1 ? nomes[0] : fmtPhone(termo);
  }, [termo, lista]);

  const abrir = (i: Caso) => {
    if (i.conversa_id) router.push(`/dashboard/atendimentos/ficha/${i.conversa_id}`);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.conversas}
          title="Casos"
          subtitle="Cada atendimento, do primeiro pedido ao desfecho — busque por nome, telefone ou protocolo."
          breadcrumb={[
            { label: 'Atendimentos', href: '/dashboard/atendimentos' },
            { label: 'Casos' },
          ]}
        />

        {/* 📱 A busca e os filtros GRUDAM no topo: no celular, subir a tela de
            volta só para trocar de filtro é onde a pessoa desiste. */}
        <div className="sticky top-0 z-20 -mx-4 mt-4 space-y-2 bg-background/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6">
          <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2.5 focus-within:border-primary/50">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar o segurado por nome, telefone ou protocolo"
              className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
            {items === null && (
              <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
            )}
            {Boolean(query) && items !== null && (
              <button
                onClick={() => setQuery('')}
                aria-label="Limpar a busca"
                className="shrink-0 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="flex gap-2 overflow-x-auto pb-0.5">
            {FILTROS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFiltro(f.id)}
                aria-pressed={filtro === f.id}
                className={cn(
                  'shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
                  filtro === f.id
                    ? 'border-primary/50 bg-brand-soft text-primary'
                    : 'border-border bg-surface text-muted-foreground hover:text-foreground',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 space-y-3">
          {pessoaDaBusca && items !== null && lista.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {lista.length} caso{lista.length > 1 ? 's' : ''} de{' '}
              <strong className="font-semibold text-foreground">{pessoaDaBusca}</strong>
              {temMais ? ' (há mais abaixo)' : ''}
            </p>
          )}

          {foraDoAr && (
            <p className="flex items-center gap-1.5 rounded-lg border border-warning/40 px-3 py-2 text-xs text-warning">
              <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
              Parte das informações não carregou agora — esta lista pode estar incompleta.
            </p>
          )}

          {items === null ? (
            <div className="space-y-2" aria-busy>
              {/* o esqueleto tem a ALTURA da linha real: a lista não pula quando
                  os casos chegam, e quem está lendo não perde o lugar. */}
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-[92px] animate-pulse rounded-xl border border-border bg-surface-2/50"
                />
              ))}
            </div>
          ) : lista.length === 0 ? (
            <div className="rounded-xl border border-border bg-surface p-8 text-center">
              <History className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm font-medium text-foreground">
                {buscaInvalida
                  ? 'Essa busca não tem nada para procurar'
                  : termo
                    ? `Nada encontrado para "${termo}"`
                    : 'Nada por aqui ainda'}
              </p>
              <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
                {buscaInvalida
                  ? 'Escreva pelo menos uma letra ou um número — um nome, um telefone ou um protocolo.'
                  : termo
                    ? 'Procuramos em todos os atendimentos da corretora — nome, telefone e protocolo.'
                    : 'Cada atendimento fica registrado aqui, com a conversa completa para consultar quando quiser.'}
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                {lista.map((i) => (
                  <LinhaDoCaso key={i.key} item={i} onOpen={abrir} />
                ))}
              </div>

              {/* Paginação por cursor — nunca um teto fixo que esconde o resto. */}
              {temMais && (
                <button
                  onClick={carregarMais}
                  disabled={carregandoMais}
                  className="mx-auto flex w-full max-w-xs items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  {carregandoMais && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Carregar mais casos
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
