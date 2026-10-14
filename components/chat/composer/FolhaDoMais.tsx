'use client';

import { useEffect, useRef } from 'react';
import Link from 'next/link';
import { Brain, Camera, Check, Globe, Images, LayoutGrid, Paperclip, Scale, Zap } from 'lucide-react';

import { cn } from '@/lib/utils';

import { ESFORCOS } from './useEsforco';
import type { Esforco } from './tipos';

/**
 * SPEC-132-A · A1 — o que o "+" abre (§4). No celular, uma FOLHA que sobe de baixo (o "Adicionar à sessão" do
 * Claude); no notebook, um menu suspenso logo acima do "+". Câmera (só celular) · Fotos · Arquivos · Esforço ·
 * Pesquisa na web (só quando a corretora permite — a regra de hoje) · Aplicativos.
 */
export interface FolhaDoMaisProps {
  aberto: boolean;
  onFechar: () => void;
  onCamera: () => void;
  onFotos: () => void;
  onArquivos: () => void;
  esforco: Esforco;
  onEsforco: (e: Esforco) => void;
  podePesquisarNaWeb?: boolean;
  pesquisaNaWeb?: boolean;
  onAlternarPesquisaNaWeb?: () => void;
}

const ICONE_DO_ESFORCO: Record<Esforco, typeof Zap> = { rapido: Zap, equilibrado: Scale, maximo: Brain };

export function FolhaDoMais({
  aberto,
  onFechar,
  onCamera,
  onFotos,
  onArquivos,
  esforco,
  onEsforco,
  podePesquisarNaWeb = false,
  pesquisaNaWeb = false,
  onAlternarPesquisaNaWeb,
}: FolhaDoMaisProps) {
  const painelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onFechar();
      }
    };
    window.addEventListener('keydown', aoTeclar, true);
    // o foco entra no painel: quem usa teclado segue com Tab/setas a partir do primeiro item visível
    // (há um "primeiro" por tamanho de tela; o visível é o que tem `offsetParent`)
    const visivel = Array.from(painelRef.current?.querySelectorAll<HTMLElement>('[data-primeiro]') ?? []).find(
      (el) => el.offsetParent !== null,
    );
    visivel?.focus({ preventScroll: true });
    return () => window.removeEventListener('keydown', aoTeclar, true);
  }, [aberto, onFechar]);

  if (!aberto) return null;

  const escolher = (acao: () => void) => () => {
    onFechar();
    acao();
  };

  const bloco = 'flex w-full items-center gap-3 rounded-xl px-3 text-left text-[15px] text-foreground transition-colors hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none';

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 animate-in fade-in-0 duration-150 lg:bg-transparent"
        onClick={onFechar}
        aria-hidden="true"
      />
      <div
        ref={painelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Adicionar à mensagem"
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 max-h-[85dvh] overflow-y-auto overscroll-contain rounded-t-[28px] border-t border-border bg-popover px-3 pt-2 text-popover-foreground shadow-modal',
          'pb-[max(16px,env(safe-area-inset-bottom))] animate-in slide-in-from-bottom duration-200',
          'lg:absolute lg:inset-x-auto lg:bottom-full lg:left-0 lg:mb-2 lg:w-80 lg:max-h-[70vh] lg:rounded-2xl lg:border lg:px-1.5 lg:py-1.5 lg:shadow-xl lg:slide-in-from-bottom-2',
        )}
      >
        {/* a alça da folha (celular) */}
        <div className="mx-auto mb-3 mt-1 h-1.5 w-10 rounded-full bg-foreground/20 lg:hidden" aria-hidden="true" />
        <p className="mb-3 px-1 text-base font-semibold text-foreground lg:hidden">Adicionar</p>

        {/* celular: três ladrilhos grandes */}
        <div className="mb-2 grid grid-cols-3 gap-2 lg:hidden">
          {[
            { rotulo: 'Câmera', Icone: Camera, acao: onCamera },
            { rotulo: 'Fotos', Icone: Images, acao: onFotos },
            { rotulo: 'Arquivos', Icone: Paperclip, acao: onArquivos },
          ].map(({ rotulo, Icone, acao }, i) => (
            <button
              key={rotulo}
              type="button"
              data-primeiro={i === 0 ? '' : undefined}
              onClick={escolher(acao)}
              className="flex h-[88px] flex-col items-center justify-center gap-2 rounded-2xl bg-surface-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Icone className="h-6 w-6" aria-hidden="true" />
              {rotulo}
            </button>
          ))}
        </div>

        {/* notebook: linhas */}
        <div className="hidden lg:block">
          <button type="button" data-primeiro="" onClick={escolher(onFotos)} className={cn(bloco, 'h-10')}>
            <Images className="h-[18px] w-[18px] text-muted-foreground" aria-hidden="true" />
            Fotos e imagens
          </button>
          <button type="button" onClick={escolher(onArquivos)} className={cn(bloco, 'h-10')}>
            <Paperclip className="h-[18px] w-[18px] text-muted-foreground" aria-hidden="true" />
            Arquivos
          </button>
        </div>

        <div className="my-2 border-t border-border-soft lg:mx-2" />

        <div role="radiogroup" aria-label="Esforço" className="py-1">
          <p className="px-3 pb-1 pt-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Esforço</p>
          {ESFORCOS.map(({ valor, rotulo, descricao }) => {
            const Icone = ICONE_DO_ESFORCO[valor];
            const marcado = valor === esforco;
            return (
              <button
                key={valor}
                type="button"
                role="radio"
                aria-checked={marcado}
                onClick={() => onEsforco(valor)}
                className={cn(bloco, 'min-h-[52px] py-2 lg:min-h-10 lg:py-1.5')}
              >
                <Icone className={cn('h-[18px] w-[18px] shrink-0', marcado ? 'text-primary' : 'text-muted-foreground')} aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium leading-5">{rotulo}</span>
                  <span className="block text-[13px] leading-4 text-muted-foreground">{descricao}</span>
                </span>
                {marcado && <Check className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />}
              </button>
            );
          })}
        </div>

        <div className="my-2 border-t border-border-soft lg:mx-2" />

        {podePesquisarNaWeb && onAlternarPesquisaNaWeb && (
          <button
            type="button"
            role="switch"
            aria-checked={pesquisaNaWeb}
            onClick={onAlternarPesquisaNaWeb}
            className={cn(bloco, 'min-h-[52px] lg:min-h-10')}
          >
            <Globe className={cn('h-[18px] w-[18px] shrink-0', pesquisaNaWeb ? 'text-primary' : 'text-muted-foreground')} aria-hidden="true" />
            <span className="flex-1">Pesquisa na web</span>
            <span
              aria-hidden="true"
              className={cn(
                'relative inline-flex h-6 w-10 shrink-0 items-center rounded-full transition-colors',
                pesquisaNaWeb ? 'bg-primary' : 'bg-foreground/20',
              )}
            >
              <span
                className={cn(
                  'inline-block h-5 w-5 rounded-full bg-background shadow transition-transform',
                  pesquisaNaWeb ? 'translate-x-[18px]' : 'translate-x-0.5',
                )}
              />
            </span>
          </button>
        )}

        <Link href="/dashboard/auxiliares" onClick={onFechar} className={cn(bloco, 'min-h-[52px] lg:min-h-10')}>
          <LayoutGrid className="h-[18px] w-[18px] shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="flex-1">Aplicativos</span>
        </Link>
      </div>
    </>
  );
}

export default FolhaDoMais;
