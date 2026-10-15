'use client';

// SPEC-139 · L2 — as Dúvidas da Cobrança, para quando a casca carrega a aba por import dinâmico
// (`cobranca-feita/AbaDuvidas`). É a MESMA peça da casca, sobre a coluna global `auxiliary_templates.faq` (o conteúdo é
// da migration da L4); aqui só o espaçamento da aba e o atalho para quem não achou a resposta.

import Link from 'next/link';

import { AbaDuvidas as DuvidasDaCasca } from '@/components/aplicativos/casca/AbaDuvidas';
import type { PropsDaAba } from '@/lib/auxiliaries/catalog';

export function AbaDuvidas({ item }: PropsDaAba) {
  return (
    <div className="space-y-4 pb-6">
      <DuvidasDaCasca faq={item.faq} />
      <p className="text-sm text-muted-foreground">
        Não achou? Veja o que já saiu em{' '}
        <Link href={`/dashboard/auxiliares/${item.slug}?aba=cobrancas`} scroll={false}
          className="font-medium text-foreground underline-offset-4 hover:underline dark:text-primary">
          Cobranças
        </Link>
        {' '}ou ajuste em{' '}
        <Link href={`/dashboard/auxiliares/${item.slug}?aba=configurar`} scroll={false}
          className="font-medium text-foreground underline-offset-4 hover:underline dark:text-primary">
          Configurar
        </Link>
        .
      </p>
    </div>
  );
}

export default AbaDuvidas;
