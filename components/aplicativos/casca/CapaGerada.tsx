'use client';

// SPEC-131-B · G1 — a capa de um aplicativo (laudo de design §2.3).
//
// Com `cover_url` (a capa do Founder, 1600×900 WebP ≤ 150 KB, sem texto): a imagem, `loading="lazy"`; se ela não
// carregar, cai na gerada. Sem `cover_url`: a capa GERADA — sem foto e sem texto, a matiz do aplicativo em CSS
// (`.capa-aplicativo` em app/globals.css) e o ícone como marca d'água. Zero bytes.

import { useState, type CSSProperties } from 'react';

import { cn } from '@/lib/utils';
import { iconeDoAplicativo } from './icones';

export interface CapaGeradaProps {
  icone: string;
  matiz: number;
  coverUrl?: string | null;
  /** a classe de proporção (`aspect-[16/9]`, `aspect-[4/1]`…) e o arredondamento */
  className?: string;
  /** o tamanho da marca d'água em px */
  marca?: number;
  /** esmaece para `surface` na base (o card) */
  esmaecer?: boolean;
  /** a imagem cresce no hover do card (`group`) */
  crescerNoHover?: boolean;
}

export function estiloDaMatiz(matiz: number): CSSProperties {
  return { ['--app-h' as string]: String(matiz) } as CSSProperties;
}

export function CapaGerada({
  icone, matiz, coverUrl, className, marca = 120, esmaecer = false, crescerNoHover = false,
}: CapaGeradaProps) {
  const [quebrou, setQuebrou] = useState(false);
  const Icone = iconeDoAplicativo(icone);
  const usarImagem = Boolean(coverUrl) && !quebrou;
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
      ) : (
        <div className={cn('capa-aplicativo absolute inset-0', crescer)} data-capa="gerada">
          <Icone
            className="icone-aplicativo absolute -bottom-4 right-3 opacity-[.12]"
            size={marca}
            strokeWidth={1.6}
            aria-hidden="true"
          />
        </div>
      )}
      {esmaecer && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-b from-transparent to-surface" />
      )}
    </div>
  );
}

export default CapaGerada;
