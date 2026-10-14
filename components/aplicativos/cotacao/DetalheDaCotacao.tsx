'use client';

// SPEC-132-B · B3 — o DETALHE de uma cotação (`&item=<id>` na URL; "voltar" fecha). O molde é o da Renovação:
//   notebook  gaveta à direita, 520 px
//   celular   tela cheia (`100dvh`), com a barra fixa embaixo, acima da área segura do aparelho
// Barra: [Enviar pelo WhatsApp] [Ver apresentação] + "Copiar a mensagem". "Abrir no Agger" pelo link direto.
// ⛔ Nenhum telefone aparece aqui: o envio abre o WhatsApp do aparelho de quem clicou, com a mensagem pronta.

import { useEffect, useState } from 'react';
import { Copy, ExternalLink, Info, Loader2, MessageCircle, Presentation } from 'lucide-react';

import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { Selo } from '@/components/aplicativos/casca/Selo';
import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { cn } from '@/lib/utils';

import { nomeDoCliente, parcela, quando, reais, tomDoEstado, type DetalheDaCotacao, type OpcaoDaCotacao } from './tipos';
import type { Resultado } from './useAcoesDaCotacao';

/** Enquanto calcula, o detalhe relê sozinho a cada tanto (o cálculo costuma fechar em 1–2 min). */
const RELEITURA_MS = 10_000;

export function DetalheDaCotacaoGaveta({
  id,
  versao,
  onFechar,
  acoes,
}: {
  id: string | null;
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
  const [dado, setDado] = useState<DetalheDaCotacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [tique, setTique] = useState(0);

  useEffect(() => {
    if (!id) {
      setDado(null);
      setErro(null);
      return;
    }
    let vivo = true;
    setErro(null);
    fetch(`/api/cotacoes/${encodeURIComponent(id)}`, { cache: 'no-store' })
      .then(async (res) => {
        const j = await res.json().catch(() => ({}));
        if (!vivo) return;
        if (!res.ok) {
          setErro(typeof j?.error === 'string' ? j.error : 'Não conseguimos abrir esta cotação agora.');
          return;
        }
        setDado(j as DetalheDaCotacao);
      })
      .catch(() => vivo && setErro('Não conseguimos abrir esta cotação agora.'));
    return () => {
      vivo = false;
    };
  }, [id, versao, tique]);

  const atual = dado && dado.id === id ? dado : null;
  const calculando = atual?.estado === 'calculando';
  useEffect(() => {
    if (!calculando) return;
    const t = setTimeout(() => setTique((n) => n + 1), RELEITURA_MS);
    return () => clearTimeout(t);
  }, [calculando, tique]);

  const ocupada = acoes.ocupado?.id === id ? acoes.ocupado.acao : null;
  const resultado = acoes.resultado?.id === id ? acoes.resultado.r : null;

  return (
    <Sheet open={Boolean(id)} onOpenChange={(aberto) => !aberto && onFechar()}>
      <SheetContent
        side="right"
        className={cn(
          'flex h-[100dvh] w-full max-w-full flex-col gap-0 p-0',
          'sm:w-[520px] sm:max-w-[520px]',
          '[&>button:last-child]:right-2 [&>button:last-child]:top-2 [&>button:last-child]:inline-flex',
          '[&>button:last-child]:h-11 [&>button:last-child]:w-11 [&>button:last-child]:items-center [&>button:last-child]:justify-center',
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
              <SheetTitle className="sr-only">Carregando a cotação</SheetTitle>
              <SheetDescription className="sr-only">Um instante.</SheetDescription>
              <Skeleton className="h-7 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}
          {!erro && atual && <Conteudo d={atual} />}
        </div>

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
                {calculando
                  ? 'O envio aparece aqui quando a cotação ficar pronta.'
                  : 'Sem preço, não há o que enviar. Peça a cotação de novo no chat.'}
              </p>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function CartaoDaOpcao({ o }: { o: OpcaoDaCotacao }) {
  const p = parcela(o.parcela_do_menor);
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-foreground">{o.rotulo}</p>
        <p className="text-xs text-muted-foreground">
          {o.seguradoras > 0
            ? o.seguradoras === 1
              ? '1 seguradora'
              : `${o.seguradoras} seguradoras`
            : o.status_rotulo}
        </p>
      </div>
      {o.menor_preco ? (
        <>
          <p className="mt-1 text-base font-semibold tabular-nums text-foreground">{p || reais(o.menor_preco)}</p>
          <p className="text-xs text-muted-foreground">
            {[o.seguradora_do_menor, p ? `à vista ${reais(o.menor_preco)}` : null, o.franquia_do_menor ? `franquia ${reais(o.franquia_do_menor)}` : null]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </>
      ) : (
        <p className="mt-1 text-sm text-muted-foreground">Nenhuma seguradora deu preço nesta versão.</p>
      )}
      {o.agger_url && (
        <a
          href={o.agger_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-flex h-11 items-center gap-1.5 text-sm font-medium text-foreground underline-offset-4 hover:underline dark:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ExternalLink className="h-4 w-4" aria-hidden />
          Ver no Agger
        </a>
      )}
    </li>
  );
}

function Conteudo({ d }: { d: DetalheDaCotacao }) {
  return (
    <div className="space-y-6">
      <header className="pr-8">
        <SheetTitle className="text-xl font-semibold tracking-tight">{nomeDoCliente(d)}</SheetTitle>
        <SheetDescription className="mt-1 text-sm text-muted-foreground">
          {[d.risco, d.placa && !(d.risco || '').includes(d.placa) ? d.placa : null, d.documento, d.quando ? `pedida ${quando(d.quando)}` : null].filter(Boolean).join(' · ')}
        </SheetDescription>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Selo tom={tomDoEstado(d.estado)} rotulo={d.estado_rotulo} />
          {d.quem_pediu && (
            <span className="text-xs text-muted-foreground">
              {d.quem_pediu.sou_eu ? 'Você pediu' : `Pedida por ${d.quem_pediu.nome}`}
            </span>
          )}
        </div>
        <p className="mt-3 rounded-lg border border-border-soft bg-surface p-3 text-sm text-foreground-2">
          {d.estado === 'calculando' && <Loader2 className="mr-1.5 inline h-4 w-4 animate-spin" aria-hidden />}
          {d.proximo_passo}
        </p>
        {d.conta.frase && (
          <p className="mt-2 flex items-start gap-1.5 text-sm text-muted-foreground">
            <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{d.conta.frase}</span>
          </p>
        )}
      </header>

      {d.melhor && (
        <section aria-labelledby="a-melhor">
          <h3 id="a-melhor" className="text-base font-semibold text-foreground">
            O menor preço
          </h3>
          <div className="mt-2 rounded-lg border border-border bg-surface p-3">
            <p className="text-lg font-semibold tabular-nums text-foreground">
              {parcela(d.melhor.parcela) || reais(d.melhor.a_vista)}
            </p>
            <p className="text-sm text-muted-foreground">
              {[d.melhor.seguradora, `à vista ${reais(d.melhor.a_vista)}`, d.melhor.opcao].filter(Boolean).join(' · ')}
            </p>
          </div>
        </section>
      )}

      <section aria-labelledby="as-versoes">
        <h3 id="as-versoes" className="text-base font-semibold text-foreground">
          As versões calculadas
        </h3>
        {d.opcoes.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Ainda não há cálculo desta cotação.</p>
        ) : (
          <ul className="mt-2 grid gap-2">
            {d.opcoes.map((o) => (
              <CartaoDaOpcao key={o.opcao} o={o} />
            ))}
          </ul>
        )}
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
            O pedido não tem o celular do cliente. Copie a mensagem e envie pelo seu WhatsApp.
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
