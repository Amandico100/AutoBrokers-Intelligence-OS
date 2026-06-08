import { cn } from '@/lib/utils';

export interface DetailSectionProps {
  title?: string;
  description?: string;
  children?: React.ReactNode;
  className?: string;
}

/** Bloco/seção do padrão Detalhe. */
export function DetailSection({ title, description, children, className }: DetailSectionProps) {
  return (
    <section className={cn('rounded-xl border border-border bg-surface p-5', className)}>
      {title && <h2 className="text-sm font-semibold text-foreground">{title}</h2>}
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      {children && <div className={cn(title || description ? 'mt-3' : undefined)}>{children}</div>}
    </section>
  );
}

export default DetailSection;
