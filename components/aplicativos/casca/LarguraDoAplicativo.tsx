'use client';

// SPEC-131-B · conserto K3 (juiz de design 2) — a largura da página de um aplicativo POR ABA. O texto (Início,
// Configurar, Dúvidas) fica em `max-w-5xl`, a medida de leitura; a aba de LISTA (Renovações) vai a `max-w-7xl`, porque
// 9 colunas em 5xl cortavam o nome do cliente e a seguradora. Lê a aba da URL (`?aba=`), como as abas; quais abas são
// largas vem PRONTO do servidor (`abasLargas` em lib/auxiliaries/catalog.ts).

import type { ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';

import { cn } from '@/lib/utils';

export function LarguraDoAplicativo({ largas, children }: { largas: string[]; children: ReactNode }) {
  const aba = useSearchParams()?.get('aba') ?? '';
  const larga = largas.includes(aba);
  return (
    <div
      className={cn('mx-auto w-full px-4 pb-16 pt-6 sm:px-6 sm:pt-8', larga ? 'max-w-7xl' : 'max-w-5xl')}
      data-largura={larga ? 'larga' : 'leitura'}
    >
      {children}
    </div>
  );
}

export default LarguraDoAplicativo;
