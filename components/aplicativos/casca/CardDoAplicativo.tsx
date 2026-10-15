'use client';

// SPEC-131-B · G1 — o card de um aplicativo na loja (laudo de design §2.3), a linha compacta do "Em breve" e o
// destaque do topo.
//
// Um `Link` só por card; o nome acessível é nome + estado. A prova é número REAL desta corretora ou o estado em
// palavras (`provaDoCard`) — nunca estrela, nunca contagem inventada (D-131-26). Cor de estado só pelo `Selo` da casca
// (nunca emerald/amber cru); texto informativo em `muted-foreground` (nunca `faint`, que reprova AA).

import type { CSSProperties } from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

import { cn } from '@/lib/utils';
import { provaDoCard, seloDoEstado, type EstadoDoCard, type ItemDoCatalogo } from '@/lib/auxiliaries/catalog';
import { CapaGerada } from './CapaGerada';
import { Selo } from './Selo';
import { iconeDoAplicativo } from './icones';

export function SeloDoAplicativo({ estado, className }: { estado: EstadoDoCard; className?: string }) {
  const selo = seloDoEstado(estado);
  if (!selo) return null;
  return <Selo tom={selo.tom} rotulo={selo.rotulo} className={className} />;
}

/**
 * SPEC-139 · L4 — o PONTO ÚNICO da cor do tile do ícone (o card, a linha do "Em breve" e o cabeçalho passam todos
 * por `TileDoIcone`, que lê SÓ daqui). Hoje: a matiz do catálogo em `--app-h`, que `.icone-aplicativo` (globals.css)
 * transforma na cor do ícone nos dois temas.
 *
 * 🧵 COSTURA (L1 × L4): quando a paleta nova existir (`components/aplicativos/casca/capas/paleta.ts`, da L1), é o
 * corpo DESTA função que passa a ler a cor da paleta pelo `slug` (com a matiz como reserva para o slug que a paleta
 * não conhece). Nenhum outro arquivo calcula a cor do tile — o teste da loja confere.
 */
export function estiloDoTile({ slug, matiz }: { slug?: string | null; matiz: number }): CSSProperties {
  void slug; // a paleta da L1 lê por slug (costura); até lá a matiz decide
  return { ['--app-h' as string]: String(matiz) } as CSSProperties;
}

/** O tile do ícone: 48 px no card, 40 no "em breve", 72 no cabeçalho. A cor vem de `estiloDoTile` (ponto único). */
export function TileDoIcone({
  icone, matiz, slug, tamanho = 48, className, apagado = false,
}: { icone: string; matiz: number; slug?: string | null; tamanho?: 40 | 48 | 72; className?: string; apagado?: boolean }) {
  const Icone = iconeDoAplicativo(icone);
  const lado = tamanho === 72 ? 'h-[72px] w-[72px] rounded-2xl' : tamanho === 48 ? 'h-12 w-12 rounded-xl' : 'h-10 w-10 rounded-lg';
  const tamIcone = tamanho === 72 ? 34 : tamanho === 48 ? 24 : 20;
  return (
    <span
      style={estiloDoTile({ slug, matiz })}
      className={cn(
        'flex shrink-0 items-center justify-center border border-border bg-surface-2',
        lado,
        apagado ? 'text-muted-foreground' : 'icone-aplicativo',
        className,
      )}
      aria-hidden="true"
    >
      <Icone size={tamIcone} strokeWidth={1.6} />
    </span>
  );
}

/**
 * O botão principal com contraste AA nos dois temas (D-131-43, laudo §0 B4): no claro, branco sobre `primary` dá
 * 4,38:1 (reprova texto de 14 px) — vai `foreground`/`background` (o preto do tema); no escuro, `primary` (6,9:1).
 */
export const BOTAO_PRIMARIO = 'bg-foreground text-background hover:opacity-90 dark:bg-primary dark:text-primary-foreground';

const FOCO = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

export function CardDoAplicativo({ item }: { item: ItemDoCatalogo }) {
  const selo = seloDoEstado(item.estado);
  const prova = provaDoCard(item);
  return (
    <Link
      href={`/dashboard/auxiliares/${item.slug}`}
      aria-label={`${item.nome}${selo ? ` — ${selo.rotulo}` : ''}`}
      data-aplicativo={item.slug}
      className={cn(
        'group flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-surface transition',
        'hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-card motion-reduce:transform-none motion-reduce:transition-none',
        FOCO,
      )}
    >
      <div className="relative">
        <CapaGerada
          icone={item.icone}
          matiz={item.matiz}
          coverUrl={item.cover_url}
          className="aspect-[16/9]"
          esmaecer
          crescerNoHover
        />
        {selo && (
          <span className="absolute left-3 top-3 rounded-full bg-background/70 sm:backdrop-blur">
            <SeloDoAplicativo estado={item.estado} />
          </span>
        )}
      </div>

      <TileDoIcone icone={item.icone} matiz={item.matiz} slug={item.slug} className="-mt-6 ml-4 ring-4 ring-surface relative" />

      <div className="flex flex-1 flex-col px-4 pb-4 pt-3">
        <h3 className="line-clamp-1 text-base font-semibold tracking-tight text-foreground">{item.nome}</h3>
        <p className="mt-1 line-clamp-2 min-h-[2.5rem] text-sm text-muted-foreground">
          {item.headline || item.resumo}
        </p>
      </div>

      {/* K3 (juiz de design 7): a prova é a frase que convence — quebra em 2 linhas, nunca "este m…" */}
      <div className="flex items-end justify-between gap-3 border-t border-border-soft px-4 py-3">
        <span className="line-clamp-2 min-w-0 text-xs leading-snug text-foreground-2" data-prova>{prova}</span>
        <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-foreground dark:text-primary">
          Abrir <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.6} aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}

/** "Em breve": linha compacta, só o ícone — não pesa como os que existem. */
export function LinhaEmBreve({ item }: { item: ItemDoCatalogo }) {
  return (
    <Link
      href={`/dashboard/auxiliares/${item.slug}`}
      aria-label={`${item.nome} — Em breve`}
      data-aplicativo={item.slug}
      className={cn(
        'flex items-center gap-3 rounded-xl border border-border-soft bg-surface/60 p-3 transition-colors hover:border-border',
        FOCO,
      )}
    >
      <TileDoIcone icone={item.icone} matiz={item.matiz} slug={item.slug} tamanho={40} apagado />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">{item.nome}</span>
        <span className="line-clamp-2 text-sm text-muted-foreground">{item.headline || item.resumo}</span>
      </span>
      <SeloDoAplicativo estado="em_breve" className="shrink-0" />
    </Link>
  );
}

/** O destaque do topo (`featured_rank = 1`): capa larga, nome grande, "Conhecer". */
export function DestaqueDoAplicativo({ item }: { item: ItemDoCatalogo }) {
  return (
    <Link
      href={`/dashboard/auxiliares/${item.slug}`}
      aria-label={`Em destaque: ${item.nome}`}
      className={cn('group relative block overflow-hidden rounded-2xl border border-border bg-surface', FOCO)}
    >
      <CapaGerada
        icone={item.icone}
        matiz={item.matiz}
        coverUrl={item.cover_url}
        className="aspect-[4/3] sm:aspect-[3/1]"
        marca={220}
        crescerNoHover
      />
      {/* K3 (juiz de design 7): no claro a esmaecida cobria a capa inteira (um vazio pálido) — ela fica só sob o texto
          (até ~45 %), e a cor aparece; no escuro segue como era */}
      <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/40 to-transparent sm:bg-gradient-to-r sm:from-background/80 sm:via-background/20 sm:via-45% sm:to-transparent dark:sm:from-background/85 dark:sm:via-background/40 dark:sm:via-50%" />
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-3 p-5 sm:inset-y-0 sm:right-auto sm:max-w-xl sm:justify-center sm:p-8">
        <span className="inline-flex w-fit items-center rounded-full border border-primary/40 bg-background/70 px-2.5 py-0.5 text-xs font-medium text-foreground">
          Em destaque
        </span>
        <span className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{item.nome}</span>
        <span className="line-clamp-2 text-base text-foreground-2">{item.headline || item.resumo}</span>
        <span className={`mt-1 inline-flex h-11 w-fit items-center gap-2 rounded-lg px-4 text-sm font-medium ${BOTAO_PRIMARIO}`}>
          Conhecer <ArrowRight className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}
