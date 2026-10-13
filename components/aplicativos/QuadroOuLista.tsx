'use client';

// ─────────────────────────────────────────────────────────────────────────────
// QUADRO OU LISTA — a mesma leitura do trabalho em duas formas (SPEC-131-B · G2).
// ─────────────────────────────────────────────────────────────────────────────
//
// Extraído da Fila de Atendimentos (`AttendanceQueueClient.tsx`), que continua a
// usá-lo — duas telas, um jeito de ler um quadro (laudo de design §5):
//
//   QUADRO   colunas que rolam na horizontal, uma por vez no celular (`snap`),
//            cada uma com a CONTAGEM no cabeçalho grudado e a própria rolagem.
//   LISTA    uma faixa por item, na ordem que a tela escolheu.
//
// A escolha entre as duas fica salva no aparelho (`useLeituraSalva`), por tela.
//
// ⛔ SEM ARRASTAR. A coluna de um item é DERIVADA do que aconteceu com ele
// (`colunaDe`), nunca de onde alguém soltou o card. Arrastar prometeria mudar o
// mundo e mudaria só a tela — por isso este componente não tem nenhum handler
// de arrasto, e nenhuma rota recebe "a coluna de destino".

import { Fragment, useEffect, useState, type ReactNode } from 'react';
import { Columns3, List } from 'lucide-react';

import { cn } from '@/lib/utils';

export type Leitura = 'quadro' | 'lista';

export interface ColunaDoQuadro {
  id: string;
  titulo: string;
  descricao?: string;
  /** o tom da régua do cabeçalho (o mesmo vocabulário do StatusPill) */
  tom?: string;
  /** some do quadro enquanto não tiver item (as colunas que quase nunca se usam) */
  esconderSeVazia?: boolean;
}

/** A cor da régua do cabeçalho da coluna — o TOM vem de quem chama. */
const REGUA_DO_TOM: Record<string, string> = {
  danger: 'bg-danger/70',
  warning: 'bg-warning/70',
  success: 'bg-success/70',
  info: 'bg-primary/60',
  neutral: 'bg-border',
  approval: 'bg-primary/60',
};

/** Quantos cards uma coluna mostra. Não é um teto de dados: é um teto de
 *  PINTURA — 600 nós numa coluna deixam o celular lento e ninguém rola até o
 *  fim de nenhuma delas. */
export const CARDS_POR_COLUNA = 50;

/**
 * A leitura escolhida (quadro ou lista), salva no aparelho por `preferencia`.
 * Em `try/catch` porque navegador com armazenamento bloqueado LANÇA ao ler
 * `localStorage` — e a escolha entre quadro e lista não é motivo para uma tela
 * inteira não abrir.
 */
export function useLeituraSalva(
  preferencia: string,
  padrao: Leitura = 'quadro',
): [Leitura, (v: Leitura) => void] {
  const [leitura, setLeitura] = useState<Leitura>(padrao);

  useEffect(() => {
    try {
      const salva = window.localStorage.getItem(preferencia);
      if (salva === 'lista' || salva === 'quadro') setLeitura(salva);
    } catch {
      /* sem preferência — fica o padrão */
    }
  }, [preferencia]);

  const escolher = (v: Leitura) => {
    setLeitura(v);
    try {
      window.localStorage.setItem(preferencia, v);
    } catch {
      /* sem drama */
    }
  };

  return [leitura, escolher];
}

/** Quadro × Lista — o segmentado, no tamanho do polegar. */
export function SeletorDeLeitura({
  leitura,
  onEscolher,
  className,
}: {
  leitura: Leitura;
  onEscolher: (v: Leitura) => void;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label="Ver como"
      className={cn('inline-flex rounded-lg border border-border bg-surface p-0.5', className)}
    >
      {(
        [
          ['quadro', 'Quadro', Columns3],
          ['lista', 'Lista', List],
        ] as const
      ).map(([v, rot, Icone]) => (
        <button
          key={v}
          type="button"
          onClick={() => onEscolher(v)}
          aria-pressed={leitura === v}
          className={cn(
            'inline-flex min-h-11 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium transition-colors sm:min-h-9 sm:text-xs',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            leitura === v ? 'bg-brand-soft text-foreground dark:text-primary' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <Icone className="h-3.5 w-3.5" aria-hidden />
          {rot}
        </button>
      ))}
    </div>
  );
}

export interface QuadroOuListaProps<T> {
  leitura: Leitura;
  /** os itens já filtrados, na ordem em que a LISTA os mostra (o quadro preserva a ordem dentro de cada coluna) */
  itens: T[];
  colunas: ColunaDoQuadro[];
  /** a coluna DERIVADA do item — `null` tira o item do quadro */
  colunaDe: (item: T) => string | null | undefined;
  chave: (item: T) => string;
  Card: (item: T) => ReactNode;
  Linha: (item: T) => ReactNode;
  /** a lista inteira, quando a tela tem a sua (ex.: agrupada por dia); sem ela, uma faixa por item */
  lista?: ReactNode;
  /** o que aparece numa coluna visível e vazia */
  colunaVazia?: ReactNode;
  /** o rodapé de uma coluna que passou do teto de pintura */
  maisNaColuna?: (restantes: number, coluna: ColunaDoQuadro) => ReactNode;
  cardsPorColuna?: number;
  className?: string;
}

export function QuadroOuLista<T>({
  leitura,
  itens,
  colunas,
  colunaDe,
  chave,
  Card,
  Linha,
  lista,
  colunaVazia,
  maisNaColuna,
  cardsPorColuna = CARDS_POR_COLUNA,
  className,
}: QuadroOuListaProps<T>) {
  if (leitura === 'lista') {
    return (
      lista ?? (
        <div className={cn('mx-auto max-w-3xl space-y-2', className)}>
          {itens.map((i) => (
            <Fragment key={chave(i)}>{Linha(i)}</Fragment>
          ))}
        </div>
      )
    );
  }

  return (
    <div className={cn('flex snap-x snap-mandatory gap-3 overflow-x-auto pb-3 sm:snap-none', className)}>
      {colunas.map((coluna) => {
        const grupo = itens.filter((i) => colunaDe(i) === coluna.id);
        if (grupo.length === 0 && coluna.esconderSeVazia) return null;
        return (
          <section
            key={coluna.id}
            aria-label={`${coluna.titulo}: ${grupo.length}`}
            className={cn(
              'flex w-[84vw] max-w-[19rem] shrink-0 snap-start flex-col rounded-xl',
              'border border-border bg-surface-2/40 sm:w-[19rem]',
              'sm:max-h-[calc(100vh-15rem)]',
            )}
          >
            {/* O CABEÇALHO COM A CONTAGEM — grudado no topo enquanto a coluna
                rola, senão a pessoa perde de vista onde está. */}
            <header className="sticky top-0 z-10 rounded-t-xl border-b border-border/60 bg-surface-2/95 px-3 py-2.5 sm:backdrop-blur">
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  className={cn('h-2 w-2 shrink-0 rounded-full', REGUA_DO_TOM[coluna.tom || ''] || 'bg-border')}
                />
                <h2 className="min-w-0 flex-1 truncate text-xs font-semibold tracking-[-0.01em] text-foreground">
                  {coluna.titulo}
                </h2>
                <span className="shrink-0 rounded-full border border-border bg-surface px-1.5 py-0.5 font-mono text-xs leading-none text-muted-foreground tabular-nums">
                  {grupo.length}
                </span>
              </div>
              {coluna.descricao && (
                <p className="mt-1 truncate text-xs leading-snug text-muted-foreground">{coluna.descricao}</p>
              )}
            </header>

            <div className="min-h-0 space-y-2 overflow-y-auto p-2.5">
              {grupo.slice(0, cardsPorColuna).map((i) => (
                <Fragment key={chave(i)}>{Card(i)}</Fragment>
              ))}
              {grupo.length === 0 && (
                <div className="px-1 py-4 text-center text-xs text-muted-foreground">
                  {colunaVazia ?? 'Nada aqui agora.'}
                </div>
              )}
              {grupo.length > cardsPorColuna && maisNaColuna?.(grupo.length - cardsPorColuna, coluna)}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default QuadroOuLista;
