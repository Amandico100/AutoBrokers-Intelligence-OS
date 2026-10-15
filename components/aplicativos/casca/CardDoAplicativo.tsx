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
import { tokensDaCapa, visualDoPedido } from './capas/paleta';
import { Selo } from './Selo';
import { iconeDoAplicativo } from './icones';

export function SeloDoAplicativo({ estado, className }: { estado: EstadoDoCard; className?: string }) {
  const selo = seloDoEstado(estado);
  if (!selo) return null;
  return <Selo tom={selo.tom} rotulo={selo.rotulo} className={className} />;
}

/** A tinta de cada matiz de capa, nos dois temas (uma conta por matiz — a paleta é determinística). */
const TINTA_POR_MATIZ = new Map<number, { claro: string; escuro: string }>();
function tintaDaMatiz(h: number): { claro: string; escuro: string } {
  let t = TINTA_POR_MATIZ.get(h);
  if (!t) {
    t = { claro: tokensDaCapa(h, 'claro').tinta, escuro: tokensDaCapa(h, 'escuro').tinta };
    TINTA_POR_MATIZ.set(h, t);
  }
  return t;
}

/**
 * SPEC-139 — o PONTO ÚNICO da cor do tile do ícone (o card, a linha do "Em breve" e o cabeçalho passam todos por
 * `TileDoIcone`, que lê SÓ daqui). A cor é a `tinta` da paleta das capas (`capas/paleta.ts`) na MESMA linha que a capa
 * usa (`visualDoPedido`: o slug; sem ele, o par ícone + matiz) — o tile bate com a capa (ex.: o Radar, 262° no laudo,
 * é 214° na capa e no tile). `--tile-claro` / `--tile-escuro` viram a cor em `.icone-aplicativo` (globals.css);
 * `--app-h` (a matiz do laudo) fica só como reserva do CSS. 📊 contraste do ícone sobre `surface-2` ≥ 5,6:1 nos dois
 * temas (o pior, depois do conserto B: resumo-atendimentos no claro, 5,64:1 —
 * `scripts/a-loja-de-aplicativos.test.mjs`, 15/10/2026).
 */
export function estiloDoTile({ slug, matiz, icone }: { slug?: string | null; matiz: number; icone?: string }): CSSProperties {
  const { claro, escuro } = tintaDaMatiz(visualDoPedido({ slug, icone, matiz }).h);
  return { ['--app-h' as string]: String(matiz), ['--tile-claro' as string]: claro, ['--tile-escuro' as string]: escuro } as CSSProperties;
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
      style={estiloDoTile({ slug, matiz, icone })}
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
          slug={item.slug}
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

      {/* Conserto B da SPEC-139 (D-139-CB-03, a regra do cabeçalho D-139-L6-01 levada ao card): a capa GERADA já traz o
          ícone no selo, grande e na cor do aplicativo — o tile de 48 px repetia o MESMO desenho a dois dedos dele, nos
          nove cards. O tile só volta com a capa do Founder (`cover_url`), que pode não trazer o ícone. */}
      {item.cover_url && (
        <TileDoIcone icone={item.icone} matiz={item.matiz} slug={item.slug} className="-mt-6 ml-4 ring-4 ring-surface relative" />
      )}

      <div className={cn('flex flex-1 flex-col px-4 pb-4', item.cover_url ? 'pt-3' : 'pt-1')}>
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

/**
 * O destaque do topo (`featured_rank = 1`): capa larga, nome grande, "Conhecer".
 *
 * Conserto B da SPEC-139 (juiz de design, galeria item 1): o ícone ficava ATRÁS do título e, no escuro, a película
 * acinzentava a capa. Agora a capa usa o enquadramento `destaque` (o selo e a cena à DIREITA, a esquerda limpa) e:
 *   · abaixo de `lg`: EMPILHADO — a capa em cima (4:3 no celular, 3:2 no tablet; o SVG ancora à direita, o corte come
 *     a esquerda vazia) e o texto embaixo, sobre `surface`. Nada se sobrepõe;
 *   · de `lg` em diante: o texto à esquerda, sobre a área livre da capa (3:1), com uma película que acaba em 45 % da
 *     largura — antes do selo (que começa em ~43 % do desenho e fica à direita do bloco de texto, max-w 40 %).
 */
export function DestaqueDoAplicativo({ item }: { item: ItemDoCatalogo }) {
  return (
    <Link
      href={`/dashboard/auxiliares/${item.slug}`}
      aria-label={`Em destaque: ${item.nome}`}
      data-destaque={item.slug}
      className={cn('group relative block overflow-hidden rounded-2xl border border-border bg-surface', FOCO)}
    >
      <div className="relative">
        <CapaGerada
          slug={item.slug}
          icone={item.icone}
          matiz={item.matiz}
          coverUrl={item.cover_url}
          enquadramento="destaque"
          className="aspect-[4/3] sm:aspect-[3/2] lg:aspect-[3/1]"
          crescerNoHover
        />
        <div aria-hidden="true" className="pointer-events-none absolute inset-y-0 left-0 hidden w-[45%] bg-gradient-to-r from-background/75 via-background/35 to-transparent lg:block" />
      </div>
      <div className="flex flex-col gap-3 p-5 sm:p-6 lg:absolute lg:inset-y-0 lg:left-0 lg:w-[40%] lg:justify-center lg:p-10">
        <span className="inline-flex w-fit items-center rounded-full border border-primary/40 bg-background/70 px-2.5 py-0.5 text-xs font-medium text-foreground">
          Em destaque
        </span>
        <span className="text-2xl font-semibold tracking-tight text-foreground lg:text-3xl">{item.nome}</span>
        <span className="line-clamp-2 text-base text-foreground-2">{item.headline || item.resumo}</span>
        <span className={`mt-1 inline-flex h-11 w-fit items-center gap-2 rounded-lg px-4 text-sm font-medium ${BOTAO_PRIMARIO}`}>
          Conhecer <ArrowRight className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}
