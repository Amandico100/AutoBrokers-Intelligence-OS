'use client';

// SPEC-139 · L1 (sobre a G1 da SPEC-131-B) — a capa de um aplicativo (laudo de design §2.3).
//
// Com `cover_url` (a capa do Founder, 1600×900 WebP ≤ 150 KB, sem texto): a imagem, `loading="lazy"`; se ela não
// carregar, cai na gerada. Sem `cover_url`: a capa GERADA em código — o SVG de `capas/composicoes.ts` na direção do
// produto (DIRECAO_DO_PRODUTO), com a cor da paleta única (`capas/paleta.ts`). Sem foto, sem texto, zero requisição,
// a mesma capa sempre para o mesmo aplicativo.
//
// Claro e escuro: a MESMA composição com a outra tabela de cor; as duas vão no HTML e o tema escolhe qual aparece
// (`dark:`), sem esperar o JavaScript — nada pisca na troca de tema.
//
// O SVG entra por `dangerouslySetInnerHTML`: ele é gerado SÓ de constantes do código (a tabela, os desenhos lucide
// gerados) e de números; nada que venha do banco é escrito nele — o slug e o ícone só ESCOLHEM uma linha da tabela.

import { useMemo, useState, type CSSProperties } from 'react';

import { cn } from '@/lib/utils';
import { capaSvg, DIRECAO_DO_PRODUTO } from './capas/composicoes';

export interface CapaGeradaProps {
  icone: string;
  matiz: number;
  /** o aplicativo: escolhe a linha da paleta (sem ele, vale o par ícone + matiz) */
  slug?: string | null;
  coverUrl?: string | null;
  /** a classe de proporção (`aspect-[16/9]`, `aspect-[4/1]`…) e o arredondamento */
  className?: string;
  /** legado (a marca d'água da capa CSS da 131-B); a composição tem a escala própria. Aceito e ignorado. */
  marca?: number;
  /** esmaece para `surface` na base (o card) */
  esmaecer?: boolean;
  /** a imagem cresce no hover do card (`group`) — nunca com `prefers-reduced-motion` */
  crescerNoHover?: boolean;
}

/** `--app-h` = a matiz do laudo: ainda usada pelo tile do ícone (`.icone-aplicativo`). */
export function estiloDaMatiz(matiz: number): CSSProperties {
  return { ['--app-h' as string]: String(matiz) } as CSSProperties;
}

/** Os dois SVGs (claro e escuro) da capa gerada — puro, para o teste e para quem precisar do desenho fora do React. */
export function svgsDaCapa(pedido: { slug?: string | null; icone: string; matiz: number }): { claro: string; escuro: string } {
  const base = { slug: pedido.slug || undefined, icone: pedido.icone, matiz: pedido.matiz, direcao: DIRECAO_DO_PRODUTO };
  return { claro: capaSvg({ ...base, tema: 'claro' }), escuro: capaSvg({ ...base, tema: 'escuro' }) };
}

export function CapaGerada({
  icone, matiz, slug, coverUrl, className, esmaecer = false, crescerNoHover = false,
}: CapaGeradaProps) {
  const [quebrou, setQuebrou] = useState(false);
  const usarImagem = Boolean(coverUrl) && !quebrou;
  const svgs = useMemo(() => (usarImagem ? null : svgsDaCapa({ slug, icone, matiz })), [usarImagem, slug, icone, matiz]);
  const crescer = crescerNoHover
    ? 'transition-transform duration-300 group-hover:scale-[1.03] motion-reduce:transform-none motion-reduce:transition-none'
    : '';

  return (
    <div className={cn('relative overflow-hidden', className)} style={estiloDaMatiz(matiz)} aria-hidden="true">
      {usarImagem ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={coverUrl as string}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setQuebrou(true)}
          className={cn('h-full w-full object-cover', crescer)}
        />
      ) : svgs ? (
        <div className={cn('capa-aplicativo absolute inset-0', crescer)} data-capa="gerada" data-direcao={DIRECAO_DO_PRODUTO}>
          <div className="absolute inset-0 dark:hidden" dangerouslySetInnerHTML={{ __html: svgs.claro }} />
          <div className="absolute inset-0 hidden dark:block" dangerouslySetInnerHTML={{ __html: svgs.escuro }} />
        </div>
      ) : null}
      {esmaecer && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-b from-transparent to-surface" />
      )}
    </div>
  );
}

export default CapaGerada;
