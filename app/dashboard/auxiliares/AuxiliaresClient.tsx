'use client';

// SPEC-064 Bloco C — a página ÚNICA de Auxiliares.
//
// Antes eram três cliques para ver o que deveria estar na primeira tela:
//
//     Auxiliares → 2 cards ("Rotinas prontas" / "Minhas rotinas")
//                → clica num card
//                   → aí sim a galeria
//
// E os Auxiliares de verdade não estavam em nenhuma das três: moravam em
// /dashboard/auxiliares/meus, sem link no menu.
//
// Agora é uma tela só, com TODOS — os ligados, os disponíveis e os que ainda
// não existem. Nenhum é escondido: o que não dá para ligar diz por quê, em vez
// de simplesmente não aparecer. Tela que esconde faz o corretor achar que o
// produto não faz aquilo.

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2, Search } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';
import { CATEGORIAS, type ItemDoCatalogo, type EstadoDoCard } from '@/lib/auxiliaries/catalog';

const SELO: Record<EstadoDoCard, { texto: string; classe: string }> = {
  ligado: {
    texto: 'ligado',
    classe: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600',
  },
  pausado: {
    texto: 'desligado',
    classe: 'border-border bg-surface-2 text-muted-foreground',
  },
  disponivel: {
    texto: 'disponível',
    classe: 'border-primary/30 bg-primary/10 text-primary',
  },
  falta_conectar: {
    texto: 'falta conectar',
    classe: 'border-amber-500/30 bg-amber-500/10 text-amber-600',
  },
  em_breve: {
    texto: 'em breve',
    classe: 'border-border bg-surface-2 text-faint',
  },
};

const GRUPOS: { chave: string; titulo: string; subtitulo: string; estados: EstadoDoCard[] }[] = [
  {
    chave: 'trabalhando',
    titulo: 'Trabalhando para você',
    subtitulo: 'Ligados e em operação.',
    estados: ['ligado'],
  },
  {
    chave: 'disponiveis',
    titulo: 'Disponíveis',
    subtitulo: 'Prontos para ligar quando você quiser.',
    estados: ['disponivel', 'pausado', 'falta_conectar'],
  },
  {
    chave: 'em_breve',
    titulo: 'Em breve',
    subtitulo: 'Já sabemos o que farão e o que falta para existirem.',
    estados: ['em_breve'],
  },
];

function Card({ item }: { item: ItemDoCatalogo }) {
  const selo = SELO[item.estado];
  return (
    <Link
      href={`/dashboard/auxiliares/${item.slug}`}
      className="flex flex-col rounded-xl border border-border bg-surface p-4 transition-colors hover:border-primary/40"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-foreground">{item.nome}</p>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${selo.classe}`}
        >
          {selo.texto}
        </span>
      </div>

      {/* A headline vende o RESULTADO. Não é a descrição técnica. */}
      <p className="mt-1.5 flex-1 text-xs leading-relaxed text-muted-foreground">
        {item.headline || item.resumo}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {item.categorias.map((c) => {
          const cat = CATEGORIAS[c];
          if (!cat) return null;
          return (
            <span
              key={c}
              className="rounded-md border border-border bg-surface-2 px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              {cat.emoji} {cat.rotulo}
            </span>
          );
        })}
      </div>

      {/* O motivo de não dar para ligar aparece no card, não só na página.
          Botão desabilitado sem explicação parece produto quebrado. */}
      {item.conectores_pendentes.length > 0 && item.estado_catalogo === 'available' && (
        <p className="mt-2 text-[11px] font-medium text-amber-600">
          Falta conectar: {item.conectores_pendentes.map((c) => c.nome).join(', ')}
        </p>
      )}

      {item.estado === 'ligado' && item.rotinas > 0 && (
        <p className="mt-2 text-[11px] text-faint">
          {item.rotinas} {item.rotinas === 1 ? 'rotina' : 'rotinas'}
          {item.ultima_execucao
            ? ` · última execução ${new Date(item.ultima_execucao).toLocaleDateString('pt-BR')}`
            : ' · ainda não rodou'}
        </p>
      )}
    </Link>
  );
}

export default function AuxiliaresClient() {
  const [itens, setItens] = useState<ItemDoCatalogo[] | null>(null);
  const [aviso, setAviso] = useState('');
  const [filtro, setFiltro] = useState<string>('todos');
  const [busca, setBusca] = useState('');

  const carregar = useCallback(async () => {
    try {
      const r = await fetch('/api/dashboard/auxiliaries', { cache: 'no-store' });
      const j = await r.json();
      if (!r.ok || !j?.ok) {
        setAviso(j?.error || 'Não foi possível carregar os Auxiliares.');
        setItens([]);
        return;
      }
      setItens(j.itens || []);
    } catch {
      setAviso('Falha de conexão.');
      setItens([]);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const filtrados = useMemo(() => {
    if (!itens) return [];
    const termo = busca.trim().toLowerCase();
    return itens.filter((i) => {
      if (filtro === 'ligados' && i.estado !== 'ligado') return false;
      if (filtro !== 'todos' && filtro !== 'ligados' && !i.categorias.includes(filtro)) return false;
      if (!termo) return true;
      return (
        i.nome.toLowerCase().includes(termo) ||
        (i.headline || '').toLowerCase().includes(termo) ||
        (i.resumo || '').toLowerCase().includes(termo)
      );
    });
  }, [itens, filtro, busca]);

  const ligados = itens?.filter((i) => i.estado === 'ligado').length ?? 0;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="Auxiliares"
          subtitle="Trabalhadores que cuidam da sua corretora enquanto você cuida do cliente. Todos começam desligados — você liga o que quiser."
          breadcrumb={[{ label: 'Auxiliares' }]}
        />

        {aviso && <p className="text-sm text-danger">{aviso}</p>}

        {/* Filtros. Por RESULTADO, nunca por módulo do sistema. */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setFiltro('todos')}
            className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
              filtro === 'todos'
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-surface text-muted-foreground hover:border-primary/40'
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setFiltro('ligados')}
            className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
              filtro === 'ligados'
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-surface text-muted-foreground hover:border-primary/40'
            }`}
          >
            Ligados{ligados > 0 ? ` (${ligados})` : ''}
          </button>
          {Object.entries(CATEGORIAS).map(([chave, cat]) => (
            <button
              key={chave}
              onClick={() => setFiltro(chave)}
              className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                filtro === chave
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-surface text-muted-foreground hover:border-primary/40'
              }`}
            >
              {cat.emoji} {cat.rotulo}
            </button>
          ))}

          <div className="relative ml-auto">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="buscar"
              className="w-40 rounded-md border border-border bg-surface py-1 pl-7 pr-2 text-xs text-foreground placeholder:text-faint focus:border-primary focus:outline-none"
            />
          </div>
        </div>

        {itens === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando Auxiliares…
          </div>
        ) : (
          GRUPOS.map((grupo) => {
            const doGrupo = filtrados.filter((i) => grupo.estados.includes(i.estado));
            if (doGrupo.length === 0) return null;
            return (
              <section key={grupo.chave} className="space-y-3">
                <div>
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {grupo.titulo}
                  </h2>
                  <p className="text-[11px] text-faint">{grupo.subtitulo}</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {doGrupo.map((i) => (
                    <Card key={i.slug} item={i} />
                  ))}
                </div>
              </section>
            );
          })
        )}

        {itens !== null && filtrados.length === 0 && (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">Nada com esse filtro</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Tente outra categoria, ou limpe a busca.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
