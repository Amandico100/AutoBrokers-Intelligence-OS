'use client';

// SPEC-131-B · G1 — "Como começar": cada passo com estado, link e o topo "N de M prontos" (laudo de design §3).
// Os passos vêm prontos de `passosDoComoComecar` (puro, testado); aqui só se desenha. O passo pronto vira
// "✓ Conectado · mudar" — o decidido não vira campo.

import Link from 'next/link';
import { Check } from 'lucide-react';

import { Progress } from '@/components/ui/progress';
import { Selo, type TomDoSelo as StatusTone } from './Selo';
import { cn } from '@/lib/utils';
import { contagemDosPassos, type EstadoDoPasso, type PassoDoComoComecar } from '@/lib/auxiliaries/catalog';

const PILULA: Record<EstadoDoPasso, { rotulo: string; tom: StatusTone }> = {
  pronto: { rotulo: 'Pronto', tom: 'success' },
  falta: { rotulo: 'Falta', tom: 'neutral' },
  atencao: { rotulo: 'Precisa de atenção', tom: 'warning' },
  nao_sei: { rotulo: 'Não deu para conferir', tom: 'neutral' },
};

export function ComoComecar({ passos }: { passos: PassoDoComoComecar[] }) {
  const { prontos, total } = contagemDosPassos(passos);
  if (total === 0) return null;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <p className="shrink-0 text-sm font-medium text-foreground" data-como-comecar-contagem>
          {prontos} de {total} prontos
        </p>
        <Progress value={(prontos / total) * 100} className="h-1.5 flex-1" aria-label={`${prontos} de ${total} prontos`} />
      </div>
      <ol className="divide-y divide-border-soft rounded-xl border border-border bg-surface">
        {passos.map((p, i) => {
          const pronto = p.estado === 'pronto';
          const pilula = PILULA[p.estado];
          return (
            // K3 (juiz de design 5): no celular o link desce para baixo do texto (alinhado ao texto, não ao número) —
            // ao lado, ele espremia o passo numa coluna de ~150 px; a partir de 640 volta para a direita
            <li key={p.chave} className="flex flex-wrap gap-x-3 gap-y-1 p-4 sm:flex-nowrap" data-passo={p.chave} data-estado={p.estado}>
              <span
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm font-medium tabular-nums',
                  pronto ? 'border-success/40 text-success' : 'border-border text-muted-foreground',
                )}
                aria-hidden="true"
              >
                {pronto ? <Check className="h-4 w-4" strokeWidth={2} /> : i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <p className="text-sm font-medium text-foreground">{p.titulo}</p>
                  <Selo tom={pilula.tom} rotulo={pilula.rotulo} />
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">{p.detalhe}</p>
              </div>
              {p.link && (
                <div className="basis-full pl-10 sm:basis-auto sm:shrink-0 sm:self-center sm:pl-0">
                  <Link
                    href={p.link}
                    className="-ml-2 inline-flex min-h-[44px] items-center rounded-md px-2 text-sm sm:ml-0 font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-primary"
                  >
                    {pronto ? (
                      <span className="inline-flex items-center gap-1">
                        <Check className="h-4 w-4 text-success" strokeWidth={2} aria-hidden="true" />
                        {p.titulo.startsWith('Conectar') ? 'Conectado' : 'Pronto'} · mudar
                      </span>
                    ) : (
                      `${p.rotuloDoLink ?? 'Abrir'} →`
                    )}
                  </Link>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default ComoComecar;
