'use client';

// SPEC-064 Bloco C — a página ÚNICA de Auxiliares. SPEC-131-B (D-131-38/39) — vira a LOJA de Aplicativos, na
// MESMA rota: "Aplicativo" é o nome na tela; o código segue `auxiliary` (D-131-18).
//
// Antes eram três cliques para ver o que deveria estar na primeira tela, e os Auxiliares de verdade não estavam em
// nenhuma das três. Agora é uma tela só, com TODOS — os ligados, os disponíveis e os que ainda não existem. Nenhum é
// escondido: o que não dá para ligar diz por quê. Tela que esconde faz o corretor achar que o produto não faz aquilo.
//
// O desenho (laudo de design §2): destaque no topo · segmentado Todos/Ligados/Disponíveis/Em breve · categorias com
// ícone (sem emoji) · cards com capa 16:9 para Ligados e Disponíveis · linha compacta para "Em breve" · prova REAL
// ou nada (D-131-26) · grid 1/2/3/4.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { Skeleton } from '@/components/ui/skeleton';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';
import { CATEGORIAS, type ItemDoCatalogo, type EstadoDoCard } from '@/lib/auxiliaries/catalog';
import { CardDoAplicativo, DestaqueDoAplicativo, LinhaEmBreve } from '@/components/aplicativos/casca/CardDoAplicativo';
import { iconeDoAplicativo } from '@/components/aplicativos/casca/icones';

type Visao = 'todos' | 'ligados' | 'disponiveis' | 'em_breve';

const GRUPOS: { chave: Exclude<Visao, 'todos'>; titulo: string; subtitulo: string; estados: EstadoDoCard[] }[] = [
  {
    chave: 'ligados',
    titulo: 'Ligados',
    subtitulo: 'Trabalhando para você agora.',
    estados: ['ligado'],
  },
  {
    chave: 'disponiveis',
    titulo: 'Disponíveis',
    subtitulo: 'Prontos para ligar quando você quiser — os que pedem uma conexão dizem qual.',
    estados: ['disponivel', 'pausado', 'falta_conectar'],
  },
  {
    chave: 'em_breve',
    titulo: 'Em breve',
    subtitulo: 'Já sabemos o que farão e o que falta para existirem.',
    estados: ['em_breve'],
  },
];

const FOCO = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

function Esqueleto() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-label="Carregando aplicativos">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="overflow-hidden rounded-2xl border border-border bg-surface">
          <Skeleton className="aspect-[16/9] w-full rounded-none" />
          <div className="space-y-2 p-4">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AuxiliaresClient() {
  const [itens, setItens] = useState<ItemDoCatalogo[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [visao, setVisao] = useState<Visao>('todos');
  const [categoria, setCategoria] = useState<string | null>(null);
  const [busca, setBusca] = useState('');

  const carregar = useCallback(async () => {
    setFalhou(false);
    setItens(null);
    try {
      const r = await fetch('/api/dashboard/auxiliaries', { cache: 'no-store' });
      const j = await r.json().catch(() => null);
      if (!r.ok || !j?.ok) {
        // o detalhe técnico vai para o log; a tela fala português (laudo de design §1, item 17)
        console.error('[APLICATIVOS] catálogo não carregou', r.status, j?.error);
        setFalhou(true);
        setItens([]);
        return;
      }
      setItens(j.itens || []);
    } catch (e) {
      console.error('[APLICATIVOS] falha de conexão', e);
      setFalhou(true);
      setItens([]);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const termo = busca.trim().toLowerCase();
  const filtrados = useMemo(() => {
    if (!itens) return [];
    return itens.filter((i) => {
      if (categoria && !i.categorias.includes(categoria)) return false;
      if (!termo) return true;
      return (
        i.nome.toLowerCase().includes(termo) ||
        (i.headline || '').toLowerCase().includes(termo) ||
        (i.resumo || '').toLowerCase().includes(termo)
      );
    });
  }, [itens, categoria, termo]);

  const contagem = useMemo(() => {
    const c: Record<Exclude<Visao, 'todos'>, number> = { ligados: 0, disponiveis: 0, em_breve: 0 };
    for (const g of GRUPOS) c[g.chave] = (itens ?? []).filter((i) => g.estados.includes(i.estado)).length;
    return c;
  }, [itens]);

  // o destaque só aparece na vista inteira, sem busca nem filtro — ele é a vitrine, não um resultado
  const destaque = useMemo(() => {
    if (!itens || termo || categoria || visao !== 'todos') return null;
    const comRank = itens.filter((i) => i.destaque !== null && i.estado !== 'em_breve');
    comRank.sort((a, b) => (a.destaque ?? 99) - (b.destaque ?? 99));
    return comRank[0] ?? null;
  }, [itens, termo, categoria, visao]);

  const grupos = GRUPOS.filter((g) => visao === 'todos' || visao === g.chave);
  const algumResultado = grupos.some((g) => filtrados.some((i) => g.estados.includes(i.estado)));

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-7xl space-y-8 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="Aplicativos"
          subtitle="Ligue o que trabalha por você. Todos começam desligados — você liga o que quiser."
        />

        {destaque && <DestaqueDoAplicativo item={destaque} />}

        {/* A barra: estado (segmentado) · categoria (chips com ícone, sem emoji) · busca */}
        <div className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <ToggleGroup
              type="single"
              value={visao}
              onValueChange={(v) => v && setVisao(v as Visao)}
              aria-label="Mostrar"
              className="w-full justify-start overflow-x-auto rounded-lg border border-border bg-surface p-1 sm:w-auto"
            >
              {(
                [
                  ['todos', 'Todos'],
                  ['ligados', `Ligados (${contagem.ligados})`],
                  ['disponiveis', `Disponíveis (${contagem.disponiveis})`],
                  ['em_breve', `Em breve (${contagem.em_breve})`],
                ] as [Visao, string][]
              ).map(([v, rotulo]) => (
                <ToggleGroupItem
                  key={v}
                  value={v}
                  className="h-10 shrink-0 whitespace-nowrap px-3 text-sm text-muted-foreground data-[state=on]:bg-surface-2 data-[state=on]:text-foreground"
                >
                  {rotulo}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>

            <label className="relative block w-full sm:w-72">
              <span className="sr-only">Buscar aplicativo</span>
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                strokeWidth={1.6}
                aria-hidden="true"
              />
              <input
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar aplicativo"
                className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              {busca && (
                <button
                  type="button"
                  onClick={() => setBusca('')}
                  aria-label="Limpar busca"
                  className={cn('absolute right-1 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:text-foreground', FOCO)}
                >
                  <X className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
                </button>
              )}
            </label>
          </div>

          {/* Categorias: por RESULTADO, nunca por módulo do sistema. Rolagem horizontal no celular. */}
          <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Categoria">
            {Object.entries(CATEGORIAS).map(([chave, cat]) => {
              const Icone: LucideIcon = iconeDoAplicativo(cat.icone);
              const ativo = categoria === chave;
              return (
                <button
                  key={chave}
                  type="button"
                  aria-pressed={ativo}
                  onClick={() => setCategoria(ativo ? null : chave)}
                  className={cn(
                    'inline-flex h-10 shrink-0 items-center gap-1.5 rounded-full border px-3 text-sm transition-colors',
                    ativo
                      ? 'border-primary bg-brand-soft text-foreground'
                      : 'border-border bg-surface text-muted-foreground hover:border-primary/40 hover:text-foreground',
                    FOCO,
                  )}
                >
                  <Icone className="h-3.5 w-3.5" strokeWidth={1.6} aria-hidden="true" />
                  {cat.rotulo}
                </button>
              );
            })}
          </div>
        </div>

        {itens === null ? (
          <Esqueleto />
        ) : falhou ? (
          <div className="rounded-2xl border border-border bg-surface p-8 text-center">
            <p className="text-base font-medium text-foreground">Não conseguimos carregar os aplicativos agora.</p>
            <button
              type="button"
              onClick={carregar}
              className={cn('mt-4 inline-flex h-11 items-center rounded-lg border border-border bg-surface-2 px-4 text-sm font-medium text-foreground hover:border-primary/40', FOCO)}
            >
              Tentar de novo
            </button>
          </div>
        ) : !algumResultado ? (
          <div className="rounded-2xl border border-border bg-surface p-8 text-center">
            {termo || categoria ? (
              <>
                <p className="text-base font-medium text-foreground">
                  Nenhum aplicativo com {termo ? `“${busca.trim()}”` : 'essa categoria'}.
                </p>
                <button
                  type="button"
                  onClick={() => { setBusca(''); setCategoria(null); }}
                  className={cn('mt-4 inline-flex h-11 items-center rounded-lg border border-border bg-surface-2 px-4 text-sm font-medium text-foreground hover:border-primary/40', FOCO)}
                >
                  Limpar busca
                </button>
              </>
            ) : visao === 'ligados' ? (
              <p className="text-base font-medium text-foreground">Nenhum aplicativo ligado ainda.</p>
            ) : (
              <p className="text-base font-medium text-foreground">Nada por aqui ainda.</p>
            )}
          </div>
        ) : (
          grupos.map((grupo, n) => {
            const doGrupo = filtrados.filter((i) => grupo.estados.includes(i.estado));
            if (doGrupo.length === 0) return null;
            const emBreve = grupo.chave === 'em_breve';
            return (
              <section
                key={grupo.chave}
                aria-labelledby={`grupo-${grupo.chave}`}
                className={cn('space-y-4', n > 0 && 'border-t border-border-soft pt-8')}
              >
                <div>
                  <h2 id={`grupo-${grupo.chave}`} className="text-lg font-semibold text-foreground">
                    {grupo.titulo} <span className="font-normal text-muted-foreground">· {doGrupo.length}</span>
                  </h2>
                  <p className="mt-0.5 text-sm text-muted-foreground">{grupo.subtitulo}</p>
                </div>
                {emBreve ? (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {doGrupo.map((i) => <LinhaEmBreve key={i.slug} item={i} />)}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {doGrupo.map((i) => <CardDoAplicativo key={i.slug} item={i} />)}
                  </div>
                )}
              </section>
            );
          })
        )}
      </div>
    </div>
  );
}
