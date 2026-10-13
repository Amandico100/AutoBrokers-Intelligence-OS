'use client';

// SPEC-131-B · G2 — as peças que mostram UMA renovação: o card do quadro, o cartão do celular e a linha da lista
// (que expande nos cálculos). O mesmo vocabulário do card do atendimento (`caso-visual.tsx`): a lombada de cor, o nome
// que o polegar procura, UM selo de atenção — e nunca só cor.

import { ChevronDown, Copy, Loader2, MessageCircle, Presentation, TriangleAlert } from 'lucide-react';

import { StatusPill } from '@/components/patterns/StatusPill';
import { cn } from '@/lib/utils';

import { reais, tomDoEstado, variacao, venceEm, dataCurta, type CalculoDaOpcao, type Renovacao } from './tipos';

export function SeloPrecisaDeVoce({ className }: { className?: string }) {
  return <StatusPill tone="warning" label="Precisa de você" className={className} />;
}

export function Variacao({ pct, className }: { pct: number | null; className?: string }) {
  const v = variacao(pct);
  if (!v) return null;
  return (
    <span
      className={cn(
        'whitespace-nowrap text-xs font-medium tabular-nums',
        v.tom === 'sobe' ? 'text-warning' : v.tom === 'desce' ? 'text-success' : 'text-muted-foreground',
        className,
      )}
    >
      <span aria-hidden>{v.tom === 'sobe' ? '▲ ' : v.tom === 'desce' ? '▼ ' : ''}</span>
      <span className="sr-only">{v.tom === 'sobe' ? 'aumento de ' : v.tom === 'desce' ? 'redução de ' : 'variação de '}</span>
      {v.texto}
    </span>
  );
}

function Lombada({ r }: { r: Renovacao }) {
  const tom = tomDoEstado(r);
  return (
    <span
      aria-hidden
      className={cn(
        'absolute inset-y-0 left-0 w-[3px]',
        tom === 'warning'
          ? 'bg-warning/70'
          : tom === 'success'
            ? 'bg-success/70'
            : tom === 'info'
              ? 'bg-primary/60'
              : 'bg-border',
      )}
    />
  );
}

function nomeDoCliente(r: Renovacao) {
  return r.cliente || 'Cliente sem nome no cadastro';
}

/** O CARD DO QUADRO — nome · ramo e vence em · prêmio e Δ · responsável · UM selo. Abre o detalhe. */
export function CardDaRenovacao({ r, onAbrir }: { r: Renovacao; onAbrir: (r: Renovacao) => void }) {
  return (
    <button
      type="button"
      onClick={() => onAbrir(r)}
      className={cn(
        'group relative w-full overflow-hidden rounded-lg border bg-surface p-3 text-left',
        'border-border shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:-translate-y-px hover:border-primary/40',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transform-none',
        r.precisa_de_voce && 'border-warning/40',
      )}
    >
      <Lombada r={r} />
      <p className="truncate pl-1.5 text-sm font-semibold leading-tight tracking-[-0.01em] text-foreground">
        {nomeDoCliente(r)}
      </p>
      <p className="mt-1 truncate pl-1.5 text-xs text-muted-foreground">
        {[r.ramo_rotulo, r.vence_em ? `vence ${dataCurta(r.vence_em)} (${venceEm(r.dias_para_vencer)})` : null]
          .filter(Boolean)
          .join(' · ')}
      </p>
      <div className="mt-1.5 flex items-baseline gap-2 pl-1.5">
        <span className="text-sm font-semibold tabular-nums text-foreground">
          {r.premio_novo ? reais(r.premio_novo) : reais(r.premio_atual)}
        </span>
        <Variacao pct={r.variacao_pct} />
      </div>
      {r.precisa_de_voce && r.motivo_frase && (
        <p className="mt-1 line-clamp-2 pl-1.5 text-xs leading-relaxed text-muted-foreground">{r.motivo_frase}</p>
      )}
      <div className="mt-2 flex items-center gap-2 pl-1.5">
        <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          {r.responsavel ? r.responsavel.nome : 'Sem responsável'}
        </span>
        {r.precisa_de_voce && <SeloPrecisaDeVoce />}
      </div>
    </button>
  );
}

/** Os cálculos lado a lado (a linha que expande e o detalhe). A "Sua renovação" vem em 1º, como na página. */
export function CalculosLadoALado({ r, compacto }: { r: Renovacao; compacto?: boolean }) {
  if (r.calculos.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {r.precisa_de_voce && r.motivo_frase ? r.motivo_frase : 'Ainda não há cálculo desta renovação.'}
      </p>
    );
  }
  return (
    <ul className={cn('grid gap-2', compacto ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-1')}>
      {r.calculos.map((c) => (
        <CartaoDoCalculo key={c.opcao} c={c} atual={r.premio_atual} />
      ))}
    </ul>
  );
}

function CartaoDoCalculo({ c, atual }: { c: CalculoDaOpcao; atual: number | null }) {
  const pct = c.menor_preco && atual ? Math.round(((c.menor_preco - atual) / atual) * 1000) / 10 : null;
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{c.rotulo}</p>
        {c.status !== 'fechado' && <span className="text-xs text-muted-foreground">{c.status_rotulo}</span>}
      </div>
      {c.menor_preco ? (
        <>
          <p className="mt-1 flex items-baseline gap-2">
            <span className="text-base font-semibold tabular-nums text-foreground">{reais(c.menor_preco)}</span>
            <Variacao pct={pct} />
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {c.seguradora_do_menor || 'Seguradora'}
            {c.franquia_do_menor ? ` · franquia ${reais(c.franquia_do_menor)}` : ''}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {c.seguradoras === 1 ? '1 seguradora deu preço' : `${c.seguradoras} seguradoras deram preço`}
          </p>
        </>
      ) : (
        <p className="mt-1 text-xs text-muted-foreground">Nenhuma seguradora deu preço nesta opção.</p>
      )}
    </li>
  );
}

export interface AcoesDaLinha {
  enviar: (id: string) => void;
  apresentar: (id: string) => void;
  copiar: (id: string) => void;
  ocupado: { id: string; acao: string } | null;
}

function BotaoIcone({
  rotulo,
  onClick,
  carregando,
  children,
  desabilitado,
}: {
  rotulo: string;
  onClick: () => void;
  carregando?: boolean;
  desabilitado?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={rotulo}
      title={rotulo}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      disabled={desabilitado}
      className={cn(
        'inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors',
        'hover:bg-surface-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'disabled:cursor-not-allowed disabled:opacity-40',
      )}
    >
      {carregando ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : children}
    </button>
  );
}

/**
 * A LINHA DA LISTA. Três desenhos, uma marcação de dados:
 *   celular (< 640)      cartão: nome · vence em · prêmio e Δ · estado · UM botão grande "Enviar"
 *   640–1023             linha com a 2ª linha (ramo, seguradoras, responsável)
 *   ≥ 1024               a linha inteira: Cliente · Ramo · Vence · Seguradora atual → nova · Prêmio atual → novo (Δ)
 *                        · Responsável · Estado · ações-ícone
 * O chevron expande nos cálculos lado a lado.
 */
export function LinhaDaRenovacao({
  r,
  aberta,
  onAlternar,
  onAbrir,
  acoes,
}: {
  r: Renovacao;
  aberta: boolean;
  onAlternar: (id: string) => void;
  onAbrir: (r: Renovacao) => void;
  acoes: AcoesDaLinha;
}) {
  const ocupada = acoes.ocupado?.id === r.id ? acoes.ocupado.acao : null;
  const idCalculos = `calculos-${r.id}`;
  const estado = (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {r.precisa_de_voce ? <SeloPrecisaDeVoce /> : <StatusPill tone={tomDoEstado(r)} label={r.estado_rotulo} />}
    </span>
  );
  return (
    <article className="relative overflow-hidden rounded-xl border border-border bg-surface">
      <Lombada r={r} />

      {/* ── celular: o cartão ── */}
      <div className="p-3 pl-4 sm:hidden">
        <button
          type="button"
          onClick={() => onAbrir(r)}
          className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <div className="flex items-start justify-between gap-2">
            <p className="min-w-0 truncate text-base font-semibold text-foreground">{nomeDoCliente(r)}</p>
            {estado}
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {[r.ramo_rotulo, venceEm(r.dias_para_vencer)].filter(Boolean).join(' · ')}
          </p>
          <p className="mt-1 flex items-baseline gap-2">
            <span className="text-base font-semibold tabular-nums text-foreground">
              {r.premio_novo ? reais(r.premio_novo) : reais(r.premio_atual)}
            </span>
            <Variacao pct={r.variacao_pct} />
          </p>
          {r.precisa_de_voce && r.motivo_frase && (
            <p className="mt-1 text-sm text-muted-foreground">{r.motivo_frase}</p>
          )}
        </button>
        {r.pode_enviar && (
          <button
            type="button"
            onClick={() => acoes.enviar(r.id)}
            disabled={Boolean(acoes.ocupado)}
            className={cn(
              'mt-3 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary text-sm font-semibold',
              'text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            )}
          >
            {ocupada === 'enviar' ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <MessageCircle className="h-4 w-4" aria-hidden />
            )}
            Enviar
          </button>
        )}
      </div>

      {/* ── 640 em diante: a linha ── */}
      <div
        className={cn(
          'hidden min-h-14 items-center gap-x-3 gap-y-1 py-2 pl-2 pr-2 sm:grid',
          'grid-cols-[2.25rem_minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1.2fr)_auto]',
          'lg:grid-cols-[2.25rem_minmax(0,1.5fr)_4.5rem_6rem_minmax(0,1.4fr)_minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1.1fr)_auto]',
        )}
      >
        <button
          type="button"
          onClick={() => onAlternar(r.id)}
          aria-expanded={aberta}
          aria-controls={idCalculos}
          aria-label={aberta ? 'Esconder os cálculos' : 'Mostrar os cálculos'}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronDown className={cn('h-4 w-4 transition-transform', aberta && 'rotate-180')} aria-hidden />
        </button>

        <button
          type="button"
          onClick={() => onAbrir(r)}
          className="min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="block truncate text-sm font-semibold text-foreground">{nomeDoCliente(r)}</span>
          <span className="block truncate font-mono text-xs text-muted-foreground">{r.documento || ''}</span>
        </button>

        <span className="hidden truncate text-sm text-foreground-2 lg:block">{r.ramo_rotulo || '—'}</span>

        <span className="text-sm text-foreground lg:order-none">
          <span className="block tabular-nums">{dataCurta(r.vence_em)}</span>
          <span className="block text-xs text-muted-foreground">{venceEm(r.dias_para_vencer)}</span>
        </span>

        <span className="hidden min-w-0 text-sm lg:block">
          <span className="block truncate text-foreground-2">{r.seguradora_atual || '—'}</span>
          {r.seguradora_nova && (
            <span className="block truncate text-xs text-muted-foreground">→ {r.seguradora_nova}</span>
          )}
        </span>

        <span className="min-w-0 text-sm">
          <span className="block truncate tabular-nums text-muted-foreground">
            {reais(r.premio_atual)} <span aria-hidden>→</span>
            <span className="sr-only">passa para</span>
          </span>
          <span className="flex items-baseline gap-2">
            <span className="font-semibold tabular-nums text-foreground">{reais(r.premio_novo)}</span>
            <Variacao pct={r.variacao_pct} />
          </span>
        </span>

        <span className="hidden truncate text-sm text-foreground-2 lg:block">
          {r.responsavel ? r.responsavel.nome : 'Sem responsável'}
        </span>

        <span className="hidden lg:block">{estado}</span>

        <span className="flex items-center justify-end gap-0.5">
          <BotaoIcone
            rotulo="Ver apresentação"
            onClick={() => acoes.apresentar(r.id)}
            desabilitado={!r.pode_enviar || Boolean(acoes.ocupado)}
            carregando={ocupada === 'apresentar'}
          >
            <Presentation className="h-4 w-4" aria-hidden />
          </BotaoIcone>
          <BotaoIcone
            rotulo="Enviar pelo WhatsApp"
            onClick={() => acoes.enviar(r.id)}
            desabilitado={!r.pode_enviar || Boolean(acoes.ocupado)}
            carregando={ocupada === 'enviar'}
          >
            <MessageCircle className="h-4 w-4" aria-hidden />
          </BotaoIcone>
          <BotaoIcone
            rotulo="Copiar a mensagem"
            onClick={() => acoes.copiar(r.id)}
            desabilitado={!r.pode_enviar || Boolean(acoes.ocupado)}
            carregando={ocupada === 'copiar'}
          >
            <Copy className="h-4 w-4" aria-hidden />
          </BotaoIcone>
        </span>

        {/* 640–1023: a 2ª linha */}
        <p className="col-span-full flex flex-wrap items-center gap-x-2 gap-y-1 pl-[2.75rem] text-xs text-muted-foreground lg:hidden">
          {estado}
          <span>{r.ramo_rotulo || 'Ramo não informado'}</span>
          <span aria-hidden>·</span>
          <span className="truncate">
            {r.seguradora_atual || 'Seguradora atual'}
            {r.seguradora_nova ? ` → ${r.seguradora_nova}` : ''}
          </span>
          <span aria-hidden>·</span>
          <span>{r.responsavel ? r.responsavel.nome : 'Sem responsável'}</span>
        </p>
      </div>

      {aberta && (
        <div id={idCalculos} className="hidden border-t border-border-soft bg-surface-2/40 p-3 sm:block">
          {r.precisa_de_voce && r.motivo_frase && (
            <p className="mb-2 flex items-center gap-1.5 text-sm text-warning">
              <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
              {r.motivo_frase}
            </p>
          )}
          <CalculosLadoALado r={r} compacto />
        </div>
      )}
    </article>
  );
}
