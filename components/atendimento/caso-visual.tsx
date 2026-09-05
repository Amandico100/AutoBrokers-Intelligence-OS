'use client';

// ─────────────────────────────────────────────────────────────────────────────
// O JEITO DE MOSTRAR UM CASO — uma vez só (SPEC-097 · R10/R11/R12).
// ─────────────────────────────────────────────────────────────────────────────
//
// 🔴 POR QUE ESTE ARQUIVO EXISTE. A Fila e os Casos mostram a MESMA coisa: um
// atendimento, com o nome de quem pediu, o que foi pedido, em que pé está, há
// quanto tempo e quem cuida. Antes cada tela escrevia o seu próprio card, com o
// seu próprio jeito de dizer "há 3 dias" — e as duas divergiam no dia em que
// alguém mexia numa. Aqui há UM vocabulário visual, e as duas telas o leem.
//
// ⚠️ LINGUAGEM (R11): nada de nome de campo, status técnico ou id. O card diz
// "esperando a seguradora há 2 dias", "Ana está atendendo", "parado há 3 dias —
// ninguém encerrou". Se não dá para ler em voz alta para o corretor, não entra.
//
// 📱 DENSIDADE (R12): o card do celular tem CINCO informações e nada mais —
// segurado · pedido · estágio em palavras · há quanto tempo · quem cuida — mais
// UM chip de atenção. Dois chips num card de 84vw viram ruído e o polegar erra
// o alvo. A referência de densidade é o Trello; a de tipografia e estado, o
// Linear; a do quadro com contagem no cabeçalho e avatar no card, o Hermes.

import { StatusPill, type StatusTone } from '@/components/patterns';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import type { Caso } from '@/lib/atendimento/casos';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────────────────────────────────────
// As palavras
// ─────────────────────────────────────────────────────────────────────────────

/** O estágio em PALAVRAS, curto o bastante para caber no card. O TOM vem da
 *  lista canônica (`STAGE_META`), nunca de um segundo mapa de cores aqui. */
export const ROTULO_DO_ESTAGIO: Record<Stage, string> = {
  precisa_de_voce: 'Precisa de você',
  esperando: 'Esperando resposta',
  acionando: 'Acionando a seguradora',
  monitorando: 'Acompanhando o prestador',
  protocolo: 'Protocolo garantido',
  em_conversa: 'Em conversa',
  com_equipe: 'Com a equipe',
  observacao: 'Atendimento da equipe',
  parado: 'Parado',
  concluido: 'Encerrado',
};

/** Um chip só, e ele diz o PROBLEMA — não o nome do campo. */
export const CHIP_DE_ATENCAO: Record<string, { label: string; tone: StatusTone }> = {
  pediu_pessoa: { label: 'pediu uma pessoa', tone: 'danger' },
  trabalho_falhou: { label: 'o acionamento parou', tone: 'danger' },
  espera_vencida: { label: 'prazo vencido', tone: 'warning' },
  parado: { label: 'ninguém encerrou', tone: 'warning' },
};

/** A ordem em que a atenção compete pelo único chip do card. */
const PRIORIDADE_DO_CHIP = ['pediu_pessoa', 'trabalho_falhou', 'espera_vencida', 'parado'];

export function chipDeAtencao(item: Caso) {
  const razao = PRIORIDADE_DO_CHIP.find((r) => (item.agora?.atencao || []).includes(r as never));
  return razao ? CHIP_DE_ATENCAO[razao] : null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Os formatos
// ─────────────────────────────────────────────────────────────────────────────

export function fmtPhone(p: string | null): string {
  if (!p) return '';
  const d = p.replace(/\D/g, '');
  if (d.length >= 12) return `(${d.slice(2, 4)}) ${d.slice(4, -4)}-${d.slice(-4)}`;
  return p;
}

/** "há 3 dias" · "há 2 horas" · "agora há pouco" — nunca "3d 4h", nunca ISO. */
export function haQuantoTempo(item: Caso): string {
  const bruto = item.agora?.ha_quanto_tempo;
  if (!bruto) return '';
  const dias = /^(\d+)d/.exec(bruto);
  if (dias) return `há ${dias[1]} ${dias[1] === '1' ? 'dia' : 'dias'}`;
  const horas = /^(\d+)h/.exec(bruto);
  if (horas) return `há ${horas[1]} ${horas[1] === '1' ? 'hora' : 'horas'}`;
  const min = /^(\d+)min/.exec(bruto);
  if (min && Number(min[1]) > 5) return `há ${min[1]} minutos`;
  return 'agora há pouco';
}

export function fmtQuando(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const hoje = new Date();
  const hora = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  if (d.toDateString() === hoje.toDateString()) return `hoje às ${hora}`;
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} às ${hora}`;
}

export function nomeDoSegurado(item: Caso): string {
  return item.cliente || fmtPhone(item.telefone) || 'Segurado';
}

/** De quem se espera, em português. A chave do banco nunca sai daqui. */
export function deQuemSeEspera(kind: string | undefined): string {
  if (kind === 'esperando_cliente') return 'o segurado';
  if (kind === 'esperando_humano') return 'alguém da equipe';
  return 'a seguradora';
}

/** A frase do card. É ela que o corretor lê primeiro. */
export function oQueEstaAcontecendo(item: Caso): string {
  const quando = haQuantoTempo(item);
  if (item.stage === 'concluido') return item.agora?.situacao || 'Encerrado.';
  if (item.dono) return `${item.dono.nome} está atendendo${quando ? ` · ${quando}` : ''}`;
  if (item.esperando) {
    return `esperando ${deQuemSeEspera(item.esperando.kind)}${quando ? ` ${quando}` : ''}`;
  }
  // ⛔ [P3-1] sem relógio não há "há X": a frase da projeção já diz que não há
  //    movimento registrado, e "parado  — ninguém encerrou" com um buraco no
  //    meio parece defeito de carga.
  if (item.stage === 'parado') {
    return quando
      ? `parado ${quando} — ninguém encerrou`
      : item.agora?.situacao || 'sem movimento registrado';
  }
  if (item.stage === 'precisa_de_voce') {
    return item.agora?.proxima_acao?.regra === 'passo_do_trabalho'
      ? `o acionamento parou ${quando} e precisa de uma pessoa`
      : `pediu uma pessoa ${quando}`;
  }
  return `${item.agora?.situacao || 'Em andamento.'}${quando ? ` · ${quando}` : ''}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// As peças
// ─────────────────────────────────────────────────────────────────────────────

/** A inicial de quem cuida. Sem foto: o produto não tem avatar de verdade, e um
 *  círculo cinza honesto é melhor que um retrato inventado. */
export function Avatar({ nome, className }: { nome: string; className?: string }) {
  return (
    <span
      title={nome}
      className={cn(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
        'border border-primary/30 bg-brand-soft text-[10px] font-semibold uppercase leading-none text-primary',
        className,
      )}
    >
      {nome.trim().charAt(0) || '?'}
    </span>
  );
}

/** Quem cuida — ou o silêncio DECLARADO. "Sem ninguém" é uma resposta; um
 *  espaço em branco parece defeito de carga (§1.2: quem assumia sumia). */
export function QuemCuida({ item, className }: { item: Caso; className?: string }) {
  if (item.dono) {
    return (
      <span
        className={cn('flex min-w-0 items-center gap-1.5 text-[11px] text-foreground', className)}
      >
        <Avatar nome={item.dono.nome} />
        <span className="truncate">{item.dono.nome}</span>
      </span>
    );
  }
  if (item.stage === 'concluido') return null;
  return (
    <span className={cn('flex items-center gap-1.5 text-[11px] text-faint', className)}>
      <span className="h-5 w-5 shrink-0 rounded-full border border-dashed border-border" />
      sem ninguém
    </span>
  );
}

/** O que foi pedido, em uma palavra. */
export function ChipDoPedido({ pedido }: { pedido: string | null }) {
  if (!pedido) return null;
  return (
    <span className="shrink-0 rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
      {pedido}
    </span>
  );
}

/**
 * O CARD DO QUADRO — compacto, de leitura em um segundo.
 *
 *   linha 1  o segurado (o nome é o que o polegar procura)
 *   linha 2  o pedido · o estágio em palavras
 *   linha 3  a frase do que está acontecendo, com o "há X"
 *   rodapé   quem cuida  ·  UM chip de atenção
 */
export function CardDoCaso({ item, onOpen }: { item: Caso; onOpen: (i: Caso) => void }) {
  const chip = chipDeAtencao(item);
  const meta = STAGE_META[item.stage];
  const abre = Boolean(item.conversa_id);
  const urgente = item.stage === 'precisa_de_voce' || chip?.tone === 'danger';
  return (
    <button
      onClick={() => onOpen(item)}
      disabled={!abre}
      className={cn(
        'group relative w-full overflow-hidden rounded-lg border bg-surface p-3 text-left',
        'shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all',
        abre
          ? 'border-border hover:-translate-y-px hover:border-primary/40 hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]'
          : 'cursor-default border-border/70',
        urgente && 'border-danger/40',
      )}
    >
      {/* a lombada de cor: o estágio se lê de relance, e o texto continua lá
          para quem não distingue a cor (nunca só cor — HANDOFF §3). */}
      <span
        aria-hidden
        className={cn(
          'absolute inset-y-0 left-0 w-[3px]',
          meta?.tone === 'danger'
            ? 'bg-danger/70'
            : meta?.tone === 'warning'
              ? 'bg-warning/70'
              : meta?.tone === 'success'
                ? 'bg-success/70'
                : meta?.tone === 'info'
                  ? 'bg-primary/60'
                  : 'bg-border',
        )}
      />
      <p className="truncate pl-1.5 text-sm font-semibold leading-tight tracking-[-0.01em] text-foreground">
        {nomeDoSegurado(item)}
      </p>
      <div className="mt-1 flex flex-wrap items-center gap-1.5 pl-1.5">
        <ChipDoPedido pedido={item.pedido} />
        <span className="truncate text-[11px] font-medium text-muted-foreground">
          {ROTULO_DO_ESTAGIO[item.stage]}
        </span>
      </div>
      <p className="mt-1.5 line-clamp-2 pl-1.5 text-xs leading-relaxed text-muted-foreground">
        {oQueEstaAcontecendo(item)}
      </p>
      <div className="mt-2 flex items-center gap-2 pl-1.5">
        <QuemCuida item={item} />
        <span className="flex-1" />
        {chip && <StatusPill tone={chip.tone} label={chip.label} />}
      </div>
      {(item.protocolo || item.sem_conversa_vinculada) && (
        <div className="mt-1.5 flex items-center gap-2 pl-1.5 text-[10px] text-faint">
          {item.protocolo && <span className="font-mono">protocolo {item.protocolo}</span>}
          {item.sem_conversa_vinculada && <span>sem conversa vinculada</span>}
        </div>
      )}
    </button>
  );
}

/**
 * A LINHA DA LISTA — o mesmo caso, em uma faixa larga que o polegar acerta.
 * 📱 A altura mínima é 64px de propósito: é o alvo confortável de um toque.
 */
export function LinhaDoCaso({ item, onOpen }: { item: Caso; onOpen: (i: Caso) => void }) {
  const chip = chipDeAtencao(item);
  const meta = STAGE_META[item.stage];
  const abre = Boolean(item.conversa_id);
  return (
    <button
      onClick={() => onOpen(item)}
      disabled={!abre}
      className={cn(
        'flex w-full items-start gap-3 rounded-xl border border-border bg-surface p-3.5 text-left transition-colors',
        abre ? 'hover:border-primary/40 hover:bg-surface-2' : 'cursor-default',
      )}
    >
      <Avatar
        nome={nomeDoSegurado(item)}
        className="mt-0.5 h-9 w-9 border-border bg-surface-2 text-xs text-muted-foreground"
      />
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline gap-2">
          <span className="min-w-0 flex-1 truncate text-sm font-semibold tracking-[-0.01em] text-foreground">
            {nomeDoSegurado(item)}
          </span>
          <span className="shrink-0 text-[11px] text-muted-foreground">
            {fmtQuando(item.ultimo_evento_em)}
          </span>
        </span>
        <span className="mt-1 block line-clamp-2 text-xs leading-relaxed text-muted-foreground">
          {oQueEstaAcontecendo(item)}
        </span>
        <span className="mt-2 flex flex-wrap items-center gap-2">
          <StatusPill tone={meta?.tone || 'neutral'} label={ROTULO_DO_ESTAGIO[item.stage]} />
          <ChipDoPedido pedido={item.pedido} />
          {chip && <StatusPill tone={chip.tone} label={chip.label} />}
          <span className="flex-1" />
          <QuemCuida item={item} />
        </span>
        {(item.protocolo || item.sem_conversa_vinculada) && (
          <span className="mt-1.5 flex items-center gap-2 text-[10px] text-faint">
            {item.protocolo && <span className="font-mono">protocolo {item.protocolo}</span>}
            {item.sem_conversa_vinculada && <span>sem conversa vinculada</span>}
          </span>
        )}
      </span>
    </button>
  );
}
