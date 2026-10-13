'use client';

// SPEC-131-B · G2 — o DETALHE de uma renovação (`&item=<id>` na URL; "voltar" fecha).
//   notebook  gaveta à direita, 520 px
//   celular   tela cheia (`100dvh`), com a barra fixa embaixo, acima da área segura do aparelho
// Barra: [Enviar pelo WhatsApp] [Ver apresentação] + "Copiar a mensagem". "Abrir no Agger" pelo link direto.
// ⛔ Nenhum telefone aparece aqui: o envio abre o WhatsApp do aparelho de quem clicou, com a mensagem pronta.

import { useEffect, useState } from 'react';
import { Copy, ExternalLink, Loader2, MessageCircle, Presentation, TriangleAlert } from 'lucide-react';

import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { Selo } from '@/components/aplicativos/casca/Selo';
import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { cn } from '@/lib/utils';

import { CalculosLadoALado, SeloPrecisaDeVoce, Variacao } from './PecasDaRenovacao';
import { dataCurta, horaCurta, reais, tomDoEstado, venceEm, type DetalheDaRenovacao } from './tipos';
import type { Resultado } from './useAcoesDaRenovacao';

export function DetalheDaRenovacaoGaveta({
  id,
  versao,
  onFechar,
  acoes,
}: {
  id: string | null;
  /** muda quando a lista recarrega (depois de uma ação) — o detalhe relê junto */
  versao: number;
  onFechar: () => void;
  acoes: {
    enviar: (id: string) => void;
    apresentar: (id: string) => void;
    copiar: (id: string) => void;
    ocupado: { id: string; acao: string } | null;
    resultado: { id: string; r: Resultado } | null;
  };
}) {
  const [dado, setDado] = useState<DetalheDaRenovacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setDado(null);
      setErro(null);
      return;
    }
    let vivo = true;
    setErro(null);
    fetch(`/api/renovacoes/${encodeURIComponent(id)}`, { cache: 'no-store' })
      .then(async (res) => {
        const j = await res.json().catch(() => ({}));
        if (!vivo) return;
        if (!res.ok) {
          setErro(typeof j?.error === 'string' ? j.error : 'Não conseguimos abrir esta renovação agora.');
          return;
        }
        setDado(j as DetalheDaRenovacao);
      })
      .catch(() => vivo && setErro('Não conseguimos abrir esta renovação agora.'));
    return () => {
      vivo = false;
    };
  }, [id, versao]);

  const atual = dado && dado.id === id ? dado : null;
  const ocupada = acoes.ocupado?.id === id ? acoes.ocupado.acao : null;
  const resultado = acoes.resultado?.id === id ? acoes.resultado.r : null;

  return (
    <Sheet open={Boolean(id)} onOpenChange={(aberto) => !aberto && onFechar()}>
      <SheetContent
        side="right"
        className={cn(
          'flex h-[100dvh] w-full max-w-full flex-col gap-0 p-0',
          'sm:w-[520px] sm:max-w-[520px]',
        )}
      >
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-6 pt-5 sm:px-6">
          {erro && (
            <div className="mt-8 text-center">
              <SheetTitle className="text-base">Não deu para abrir</SheetTitle>
              <SheetDescription className="mt-1">{erro}</SheetDescription>
            </div>
          )}
          {!erro && !atual && (
            <div className="space-y-3 pt-6" aria-busy="true">
              <SheetTitle className="sr-only">Carregando a renovação</SheetTitle>
              <SheetDescription className="sr-only">Um instante.</SheetDescription>
              <Skeleton className="h-7 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}
          {!erro && atual && <Conteudo d={atual} />}
        </div>

        {/* A BARRA FIXA — acima da área segura do celular */}
        {!erro && atual && (
          <div className="shrink-0 border-t border-border bg-background px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6">
            {resultado && <AvisoDoResultado r={resultado} onCopiar={() => acoes.copiar(atual.id)} />}
            {atual.pode_enviar ? (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => acoes.enviar(atual.id)}
                    aria-label="Enviar pelo WhatsApp"
                    disabled={Boolean(acoes.ocupado)}
                    className={cn(
                      'inline-flex h-11 items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold',
                      BOTAO_PRIMARIO,
                      'transition-opacity disabled:opacity-60',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    )}
                  >
                    {ocupada === 'enviar' ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <MessageCircle className="h-4 w-4" aria-hidden />
                    )}
                    {/* no celular a barra tem metade da largura: o rótulo curto não quebra em duas linhas */}
                    <span className="whitespace-nowrap sm:hidden">Enviar</span>
                    <span className="hidden whitespace-nowrap sm:inline">Enviar pelo WhatsApp</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => acoes.apresentar(atual.id)}
                    disabled={Boolean(acoes.ocupado)}
                    className={cn(
                      'inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3',
                      'text-sm font-medium text-foreground transition-colors hover:bg-surface-2 disabled:opacity-60',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    )}
                  >
                    {ocupada === 'apresentar' ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Presentation className="h-4 w-4" aria-hidden />
                    )}
                    Ver apresentação
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => acoes.copiar(atual.id)}
                  disabled={Boolean(acoes.ocupado)}
                  className="mt-1 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg text-sm font-medium text-foreground hover:bg-brand-soft dark:text-primary disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {ocupada === 'copiar' ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <Copy className="h-4 w-4" aria-hidden />
                  )}
                  Copiar a mensagem
                </button>
              </>
            ) : (
              <p className="py-2 text-center text-sm text-muted-foreground">
                O envio aparece aqui quando o cálculo ficar pronto.
              </p>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Conteudo({ d }: { d: DetalheDaRenovacao }) {
  return (
    <div className="space-y-6">
      {/* o cabeçalho, com o PRÓXIMO PASSO */}
      <header className="pr-8">
        <SheetTitle className="text-xl font-semibold tracking-tight">
          {d.cliente || 'Cliente sem nome no cadastro'}
        </SheetTitle>
        <SheetDescription className="mt-1 text-sm text-muted-foreground">
          {[d.ramo_rotulo, d.documento, d.vence_em ? `vence ${dataCurta(d.vence_em)} (${venceEm(d.dias_para_vencer)})` : null]
            .filter(Boolean)
            .join(' · ')}
        </SheetDescription>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Selo tom={tomDoEstado(d)} rotulo={d.estado_rotulo} />
          {d.precisa_de_voce && <SeloPrecisaDeVoce />}
        </div>
        <p
          className={cn(
            'mt-3 rounded-lg border p-3 text-sm',
            d.precisa_de_voce ? 'border-warning/40 text-foreground' : 'border-border-soft bg-surface text-foreground-2',
          )}
        >
          {d.precisa_de_voce && <TriangleAlert className="mr-1.5 inline h-4 w-4 text-warning" aria-hidden />}
          {d.proximo_passo}
        </p>
      </header>

      <section aria-labelledby="hoje-x-renovacao">
        <h3 id="hoje-x-renovacao" className="text-base font-semibold text-foreground">
          O seguro hoje × a renovação
        </h3>
        <dl className="mt-2 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-border bg-surface p-3">
            <dt className="text-xs text-muted-foreground">Hoje</dt>
            <dd className="mt-0.5 text-base font-semibold tabular-nums text-foreground">{reais(d.premio_atual)}</dd>
            <dd className="truncate text-xs text-muted-foreground">{d.seguradora_atual || '—'}</dd>
          </div>
          <div className="rounded-lg border border-border bg-surface p-3">
            <dt className="text-xs text-muted-foreground">Na renovação</dt>
            <dd className="mt-0.5 flex items-baseline gap-2">
              <span className="text-base font-semibold tabular-nums text-foreground">{reais(d.premio_novo)}</span>
              <Variacao pct={d.variacao_pct} />
            </dd>
            <dd className="truncate text-xs text-muted-foreground">{d.seguradora_nova || '—'}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="os-calculos">
        <h3 id="os-calculos" className="text-base font-semibold text-foreground">
          Os cálculos
        </h3>
        <div className="mt-2">
          <CalculosLadoALado r={d} />
        </div>
        {d.agger_url && (
          <div className="mt-3">
            <a
              href={d.agger_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-11 items-center gap-2 rounded-lg px-1 text-sm font-medium text-foreground underline-offset-4 hover:underline dark:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ExternalLink className="h-4 w-4" aria-hidden />
              Abrir no Agger
            </a>
            <p className="text-xs text-muted-foreground">Se o Agger pedir login, entre e abra de novo.</p>
          </div>
        )}
      </section>

      {d.eventos.length > 0 && (
        <section aria-labelledby="linha-do-tempo">
          <h3 id="linha-do-tempo" className="text-base font-semibold text-foreground">
            O que aconteceu
          </h3>
          <ol className="mt-2 space-y-2 border-l border-border-soft pl-4">
            {d.eventos.map((e, k) => (
              <li key={k} className="relative">
                <span aria-hidden className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-border" />
                <p className="text-sm text-foreground">{e.frase}</p>
                <p className="text-xs text-muted-foreground">{horaCurta(e.quando)}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

/** O que a última ação deixou (sem telefone, copiado, erro) — anunciado ao leitor de tela. */
export function AvisoDoResultado({ r, onCopiar }: { r: Resultado; onCopiar: () => void }) {
  if (r.tipo === 'aberto') return null;
  return (
    <div role="status" aria-live="polite" className="mb-2 rounded-lg border border-border bg-surface p-3 text-sm">
      {r.tipo === 'sem_telefone' && (
        <>
          <p className="text-foreground">
            Não achamos o celular deste cliente no cadastro. Copie a mensagem e envie pelo seu WhatsApp.
          </p>
          <button
            type="button"
            onClick={onCopiar}
            className="mt-2 inline-flex h-11 items-center gap-2 rounded-lg px-1 font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-primary"
          >
            <Copy className="h-4 w-4" aria-hidden />
            Copiar a mensagem
          </button>
        </>
      )}
      {r.tipo === 'copiado' && <p className="text-foreground">Mensagem copiada. Cole no WhatsApp do cliente.</p>}
      {r.tipo === 'copiar_a_mao' && (
        <>
          <p className="text-foreground">O navegador não deixou copiar sozinho. Selecione e copie:</p>
          <textarea
            readOnly
            value={r.texto}
            onFocus={(e) => e.currentTarget.select()}
            className="mt-2 h-28 w-full rounded-lg border border-border bg-background p-2 text-sm text-foreground"
            aria-label="A mensagem para o cliente"
          />
        </>
      )}
      {r.tipo === 'erro' && <p className="text-danger">{r.mensagem}</p>}
    </div>
  );
}
