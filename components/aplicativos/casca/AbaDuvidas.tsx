'use client';

// SPEC-131-B · G1 — a aba Dúvidas, genérica para todo aplicativo (laudo de design §3). A fonte é a coluna global
// `auxiliary_templates.faq` (nenhum nome de corretora). `limite` mostra só as primeiras (o bloco do Início).

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import type { DuvidaDoAplicativo } from '@/lib/auxiliaries/catalog';

export function AbaDuvidas({ faq, limite }: { faq: DuvidaDoAplicativo[]; limite?: number }) {
  const lista = typeof limite === 'number' ? faq.slice(0, limite) : faq;
  if (lista.length === 0) {
    return <p className="text-sm text-muted-foreground">Ainda não há dúvidas escritas para este aplicativo.</p>;
  }
  return (
    <Accordion type="single" collapsible className="max-w-3xl rounded-xl border border-border bg-surface px-4">
      {lista.map((d, i) => (
        <AccordionItem key={i} value={`duvida-${i}`} className="border-border-soft last:border-b-0">
          <AccordionTrigger className="min-h-[44px] text-left text-base font-medium text-foreground hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            {d.pergunta}
          </AccordionTrigger>
          <AccordionContent className="text-sm leading-6 text-muted-foreground">{d.resposta}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}

export default AbaDuvidas;
