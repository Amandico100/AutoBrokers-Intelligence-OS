'use client';

import type { ReactNode } from 'react';
import { Info, Minus, Plus } from 'lucide-react';

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { cn } from '@/lib/utils';

/**
 * SPEC-131-B G3 — as peças da aba Configurar de todo aplicativo (laudo de design §4): o GRUPO (título + 1 linha + cartão
 * com linhas divididas), a LINHA (rótulo + ⓘ à esquerda, controle à direita), o ⓘ em POPOVER (tooltip não abre com
 * toque), o número com −/+ e a barra "Alterações não salvas" que só aparece quando há alteração.
 * Nenhum número comercial mora aqui: padrões e faixas vêm do backend (`config.py`, o guarda G8 da 130-A).
 */
export function Grupo({ titulo, descricao, children, id }: {
  titulo: string; descricao?: string; children: ReactNode; id?: string;
}) {
  return (
    <section className="space-y-3" aria-labelledby={id}>
      <div className="space-y-1">
        <h2 id={id} className="text-base font-semibold text-foreground">{titulo}</h2>
        {descricao && <p className="text-sm text-muted-foreground">{descricao}</p>}
      </div>
      <div className="divide-y divide-border-soft rounded-xl border border-border bg-surface">{children}</div>
    </section>
  );
}

export function Linha({ rotulo, info, children, htmlFor }: {
  rotulo: string; info?: ReactNode; children: ReactNode; htmlFor?: string;
}) {
  return (
    <div className="grid gap-2 p-4 sm:grid-cols-[1fr_1.3fr] sm:gap-6">
      <div className="flex items-start gap-1.5">
        {htmlFor ? (
          <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">{rotulo}</label>
        ) : (
          <span className="text-sm font-medium text-foreground">{rotulo}</span>
        )}
        {info && <Ajuda titulo={rotulo}>{info}</Ajuda>}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** O ⓘ: um Popover (abre com toque e com teclado), nunca um tooltip. */
export function Ajuda({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <Popover>
      <PopoverTrigger
        type="button"
        aria-label={`O que é: ${titulo}`}
        className="-m-3 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Info size={15} strokeWidth={1.6} aria-hidden />
      </PopoverTrigger>
      <PopoverContent className="w-80 border-border bg-surface text-sm leading-6 text-foreground-2">{children}</PopoverContent>
    </Popover>
  );
}

/** Número inteiro com − / + (h-10), dentro da faixa que veio do backend. */
export function NumeroComBotoes({ id, valor, min, max, onChange, sufixo, rotulo, desabilitado }: {
  id: string; valor: number; min: number; max: number; onChange: (n: number) => void; sufixo?: string; rotulo: string;
  desabilitado?: boolean;
}) {
  const limitar = (n: number) => Math.min(max, Math.max(min, Math.round(n)));
  const botao = 'inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background text-foreground hover:bg-surface-2 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
  return (
    <div className="flex items-center gap-2">
      <button type="button" className={botao} aria-label={`Menos — ${rotulo}`} disabled={desabilitado || valor <= min}
        onClick={() => onChange(limitar(valor - 1))}>
        <Minus size={16} strokeWidth={1.6} aria-hidden />
      </button>
      <input
        id={id}
        inputMode="numeric"
        disabled={desabilitado}
        className="h-10 w-16 rounded-lg border border-border bg-background px-2 text-center text-sm tabular-nums text-foreground"
        value={Number.isFinite(valor) ? String(valor) : ''}
        onChange={(e) => {
          const n = Number(e.target.value.replace(/\D/g, ''));
          if (e.target.value.trim() === '') return;
          onChange(limitar(n));
        }}
        aria-describedby={`${id}-faixa`}
      />
      <button type="button" className={botao} aria-label={`Mais — ${rotulo}`} disabled={desabilitado || valor >= max}
        onClick={() => onChange(limitar(valor + 1))}>
        <Plus size={16} strokeWidth={1.6} aria-hidden />
      </button>
      {sufixo && <span className="text-sm text-muted-foreground">{sufixo}</span>}
      <span id={`${id}-faixa`} className="sr-only">de {min} a {max}</span>
    </div>
  );
}

/** Segmentado acessível (radiogroup): 44 px no celular, 40 no notebook. Opção desabilitada mostra o porquê no rótulo. */
export function Segmentado<T extends string>({ valor, opcoes, onChange, rotulo, desabilitado }: {
  valor: T; rotulo: string; onChange: (v: T) => void; desabilitado?: boolean;
  opcoes: { valor: T; titulo: string; desabilitada?: boolean }[];
}) {
  return (
    <div role="radiogroup" aria-label={rotulo} className="inline-flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1">
      {opcoes.map((o) => (
        <button
          key={o.valor}
          type="button"
          role="radio"
          aria-checked={valor === o.valor}
          disabled={desabilitado || o.desabilitada}
          onClick={() => onChange(o.valor)}
          className={cn(
            'min-h-11 rounded-md px-3 text-sm sm:min-h-10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
            valor === o.valor ? 'bg-surface-2 font-medium text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {o.titulo}
        </button>
      ))}
    </div>
  );
}

/** A barra que só aparece com alteração: "Alterações não salvas" [Descartar] [Salvar]. */
export function BarraSalvar({ visivel, salvando, onDescartar, onSalvar, aviso, conflito, onRecarregar }: {
  visivel: boolean; salvando: boolean; onDescartar: () => void; onSalvar: () => void;
  aviso?: string; conflito?: boolean; onRecarregar?: () => void;
}) {
  if (!visivel && !aviso) return null;
  return (
    <div className="sticky bottom-0 z-20 border-t border-border bg-background/95 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:backdrop-blur" role="region" aria-label="Salvar alterações">
      <div className="mx-auto flex max-w-3xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className={cn('text-sm', conflito ? 'text-danger' : 'text-muted-foreground')} role="status">
          {aviso || 'Alterações não salvas'}
        </p>
        <div className="flex gap-2">
          {conflito && onRecarregar ? (
            <button type="button" onClick={onRecarregar}
              className="h-11 flex-1 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:flex-none">
              Recarregar
            </button>
          ) : visivel ? (
            <>
              <button type="button" onClick={onDescartar} disabled={salvando}
                className="h-11 flex-1 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:flex-none">
                Descartar
              </button>
              <button type="button" onClick={onSalvar} disabled={salvando}
                className={cn('h-11 flex-1 rounded-lg px-5 text-sm font-medium disabled:opacity-60 sm:flex-none', BOTAO_PRIMARIO, 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring')}>
                {salvando ? 'Salvando…' : 'Salvar'}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
