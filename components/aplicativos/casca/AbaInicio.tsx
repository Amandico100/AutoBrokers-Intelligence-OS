'use client';

// SPEC-131-B · G1 — a aba Início, genérica para todo aplicativo (laudo de design §3, a ordem da Shopify):
//   o que é → o que faz → o que a corretora ganha → Como começar → atividade recente → dúvidas.
// Saíram "De onde ele tira a informação" e os slugs crus. A atividade vem da fonte REAL (`routine_runs`; na
// Renovação, as madrugadas de `renovacao_dias`) — o Histórico por `last_run_at` mentia (laudo I2 F7).

import Link from 'next/link';
import { Check } from 'lucide-react';

import { cn } from '@/lib/utils';
import type {
  AtividadeDoAplicativo,
  ItemDoCatalogo,
  PassoDoComoComecar,
} from '@/lib/auxiliaries/catalog';
import { AbaDuvidas } from './AbaDuvidas';
import { ComoComecar } from './ComoComecar';

function Bloco({ titulo, children, primeiro = false }: { titulo: string; children: React.ReactNode; primeiro?: boolean }) {
  return (
    <section className={cn('space-y-4 py-8', !primeiro && 'border-t border-border-soft')}>
      <h2 className="text-lg font-semibold text-foreground">{titulo}</h2>
      {children}
    </section>
  );
}

const TOM_DA_ATIVIDADE: Record<AtividadeDoAplicativo['tom'], string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  neutral: 'bg-muted-foreground',
};

function quandoFoi(iso: string): string {
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return '';
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export interface AbaInicioProps {
  item: ItemDoCatalogo;
  passos: PassoDoComoComecar[];
  atividade: AtividadeDoAplicativo[];
  /** o link de "Ver todas" as dúvidas (a aba Dúvidas) */
  hrefDuvidas: string;
}

export function AbaInicio({ item, passos, atividade, hrefDuvidas }: AbaInicioProps) {
  const ganhoComNumero =
    item.prova.renovacoes_no_mes !== null && item.prova.renovacoes_no_mes > 0
      ? {
          numero: item.prova.renovacoes_no_mes,
          legenda: item.prova.renovacoes_no_mes === 1 ? 'renovação calculada este mês' : 'renovações calculadas este mês',
        }
      : item.prova.execucoes > 0
        ? { numero: item.prova.execucoes, legenda: item.prova.execucoes === 1 ? 'execução até hoje' : 'execuções até hoje' }
        : null;
  const emBreve = item.estado === 'em_breve';

  return (
    <div>
      {item.descricao && (
        <Bloco titulo="O que é" primeiro>
          <div className="max-w-[65ch] space-y-3 text-base leading-7 text-foreground-2">
            {item.descricao.split('\n\n').map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </Bloco>
      )}

      {item.o_que_faz.length > 0 && (
        <Bloco titulo="O que faz" primeiro={!item.descricao}>
          <ul className="space-y-3">
            {item.o_que_faz.map((t, i) => (
              <li key={i} className="flex items-start gap-3">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" strokeWidth={2} aria-hidden="true" />
                <span>
                  <span className="block text-sm text-foreground">{t.tarefa}</span>
                  <span className="block text-xs text-muted-foreground">{t.frequencia}</span>
                </span>
              </li>
            ))}
          </ul>
        </Bloco>
      )}

      {(item.promessa || ganhoComNumero) && (
        <Bloco titulo="O que a corretora ganha">
          {/* Número só se for MEDIDO nesta corretora; senão, a promessa diz o que SERÁ medido (CLAUDE.md §12.1). */}
          <div className="rounded-xl border border-primary/20 bg-brand-soft p-5">
            {ganhoComNumero && (
              <p className="mb-2">
                <span className="text-3xl font-semibold tabular-nums text-foreground">{ganhoComNumero.numero}</span>{' '}
                <span className="text-sm text-foreground-2">{ganhoComNumero.legenda}</span>
              </p>
            )}
            {item.promessa && <p className="text-sm leading-6 text-foreground">{item.promessa}</p>}
          </div>
        </Bloco>
      )}

      {emBreve ? (
        <Bloco titulo="Ainda não está pronto">
          <p className="max-w-[65ch] text-sm text-muted-foreground">
            {item.falta_para_existir || 'Este aplicativo ainda está sendo construído.'}
          </p>
        </Bloco>
      ) : (
        <Bloco titulo="Como começar">
          <ComoComecar passos={passos} />
        </Bloco>
      )}

      {!emBreve && (
        <Bloco titulo="Atividade recente">
          {atividade.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {item.instalado ? 'Ainda não rodou nenhuma vez.' : 'Nada por aqui ainda: ele começa a trabalhar quando você ligar.'}
            </p>
          ) : (
            <ul className="space-y-2" data-atividade>
              {atividade.map((a, i) => (
                <li key={i} className="flex items-center gap-3 rounded-lg border border-border-soft bg-surface px-3 py-2.5">
                  <span className={cn('h-2 w-2 shrink-0 rounded-full', TOM_DA_ATIVIDADE[a.tom])} aria-hidden="true" />
                  <span className="flex-1 text-sm text-foreground">{a.texto}</span>
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{quandoFoi(a.quando)}</span>
                </li>
              ))}
            </ul>
          )}
          {item.instalado && item.prova.execucoes > 0 && (
            <Link href="/dashboard/entregas" className="inline-flex min-h-[44px] items-center text-sm font-medium text-foreground underline-offset-4 hover:underline dark:text-primary">
              Ver tudo que ele entregou →
            </Link>
          )}
        </Bloco>
      )}

      {item.faq.length > 0 && (
        <Bloco titulo="Dúvidas">
          <AbaDuvidas faq={item.faq} limite={3} />
          {item.faq.length > 3 && (
            <Link href={hrefDuvidas} scroll={false} className="inline-flex min-h-[44px] items-center text-sm font-medium text-foreground underline-offset-4 hover:underline dark:text-primary">
              Ver todas as dúvidas →
            </Link>
          )}
        </Bloco>
      )}
    </div>
  );
}

export default AbaInicio;
