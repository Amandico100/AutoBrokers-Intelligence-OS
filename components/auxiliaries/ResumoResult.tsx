import { StatusPill, type StatusTone } from '@/components/patterns';
import type { AuxiliaryRunOutput } from '@/lib/auxiliaries/types';

function ListBlock({ title, items }: { title: string; items?: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">{title}</p>
      <ul className="mt-1.5 space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2 text-sm text-foreground-2">
            <span className="text-primary">•</span>
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const confTone: Record<'low' | 'medium' | 'high', StatusTone> = {
  low: 'neutral',
  medium: 'info',
  high: 'success',
};

/** Renderiza o output estruturado do Resumo de Atendimentos (sem JSON cru). */
export function ResumoResult({ output }: { output: AuxiliaryRunOutput }) {
  const hasLists =
    (output.topics?.length || 0) +
      (output.decisions?.length || 0) +
      (output.pending_items?.length || 0) +
      (output.next_steps?.length || 0) >
    0;

  return (
    <div className="space-y-5">
      {output.summary ? (
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">Resumo</p>
          <p className="mt-1.5 whitespace-pre-wrap text-sm text-foreground">{output.summary}</p>
        </div>
      ) : null}

      <ListBlock title="Tópicos" items={output.topics} />
      <ListBlock title="Decisões" items={output.decisions} />
      <ListBlock title="Pendências" items={output.pending_items} />
      <ListBlock title="Próximos passos" items={output.next_steps} />

      {!output.summary && !hasLists && (
        <p className="text-sm text-muted-foreground">
          Resumo gerado, mas sem conteúdo estruturado retornado.
        </p>
      )}

      {output.confidence ? (
        <div className="flex items-center gap-2 pt-1">
          <span className="text-xs text-muted-foreground">Confiança:</span>
          <StatusPill tone={confTone[output.confidence] ?? 'neutral'} label={output.confidence} />
        </div>
      ) : null}
    </div>
  );
}

export default ResumoResult;
