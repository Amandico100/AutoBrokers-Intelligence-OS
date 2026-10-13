// SPEC-131-B · conserto K2 (juiz de design, conserto 4) — o selo de estado das telas dos aplicativos.
//
// Por que não o `StatusPill` cru: ele sai em `font-mono text-[11px]` (o checklist §6 item 14 pede 0 texto de 10/11 px)
// e, no tema CLARO, o texto na cor do tom reprova AA (📊 juiz de design 13/10: `warning` 3,97:1 · `success` 4,45:1 ·
// `text-primary` 4,10–4,38:1). Os tokens globais ficam intocados (D-131-43): no claro o TEXTO vai escuro
// (`foreground-2`) e a cor do estado fica no PONTO e na borda; no escuro (o padrão, que passa) o texto volta à cor do
// tom. Nunca só cor: o ponto acompanha a palavra.

import { cn } from '@/lib/utils';

export type TomDoSelo = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'approval';

const TOM: Record<TomDoSelo, { borda: string; ponto: string; texto: string }> = {
  neutral: { borda: 'border-border', ponto: 'bg-muted-foreground', texto: 'text-muted-foreground' },
  info: { borda: 'border-primary/40 bg-brand-soft', ponto: 'bg-primary', texto: 'text-foreground-2 dark:text-primary' },
  success: { borda: 'border-success/40', ponto: 'bg-success', texto: 'text-foreground-2 dark:text-success' },
  warning: { borda: 'border-warning/40', ponto: 'bg-warning', texto: 'text-foreground-2 dark:text-warning' },
  danger: { borda: 'border-danger/40', ponto: 'bg-danger', texto: 'text-foreground-2 dark:text-danger' },
  approval: { borda: 'border-dashed border-primary/60 bg-brand-soft', ponto: 'bg-primary animate-pulse', texto: 'text-foreground-2 dark:text-primary' },
};

export function Selo({ tom = 'neutral', rotulo, className }: { tom?: TomDoSelo; rotulo: string; className?: string }) {
  const t = TOM[tom] ?? TOM.neutral;
  return (
    <span
      data-selo={tom}
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 font-sans text-xs font-medium leading-none',
        t.borda,
        t.texto,
        className,
      )}
    >
      <span aria-hidden="true" className={cn('h-1.5 w-1.5 shrink-0 rounded-full', t.ponto)} />
      {rotulo}
    </span>
  );
}

export default Selo;
