'use client';

import { useState } from 'react';
import { ArrowDown, ArrowUp, X } from 'lucide-react';

import { cn } from '@/lib/utils';

import type { DadosServicos, Excecao, Modo, Preferencias } from './servicos';
import { reais } from './servicos';

/**
 * SPEC-131-B G3 — os campos que a antiga tela "Serviços" tinha, no padrão da aba Configurar: o "O que fazer" em cartões
 * (radiogroup), as exceções por ramo/valor e as seguradoras preferidas por ramo (estas duas no Avançado, recolhidas).
 */
export type OpcaoDeModo = { valor: Modo; titulo: string; explica: string; curto: string; emBreve?: boolean };

export function CartoesDeModo({ opcoes, valor, onChange, nome, desabilitado }: {
  opcoes: OpcaoDeModo[]; valor: Modo; onChange: (m: Modo) => void; nome: string; desabilitado?: boolean;
}) {
  return (
    <div role="radiogroup" aria-label={nome} className="grid gap-2 p-4">
      {opcoes.map((m) => {
        const marcado = valor === m.valor;
        const bloqueado = desabilitado || (m.emBreve && !marcado);
        return (
          <button
            key={m.valor}
            type="button"
            role="radio"
            aria-checked={marcado}
            disabled={bloqueado}
            onClick={() => onChange(m.valor)}
            className={cn(
              'flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed',
              marcado ? 'border-primary bg-brand-soft' : 'border-border hover:bg-surface-2',
              bloqueado && !marcado && 'opacity-60',
            )}
          >
            <span aria-hidden className={cn('mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border',
              marcado ? 'border-primary' : 'border-border')}>
              {marcado && <span className="h-2 w-2 rounded-full bg-primary" />}
            </span>
            <span className="min-w-0">
              <span className="flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
                {m.titulo}
                {m.emBreve && <span className="rounded-full border border-border px-2 py-0.5 text-xs font-normal text-muted-foreground">Em breve</span>}
              </span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{m.explica}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function textoDaExcecao(e: Excecao, ramos: DadosServicos['ramos'], modos: OpcaoDeModo[]): string {
  const partes: string[] = [];
  if (e.ramo) partes.push(ramos.find((r) => r.codigo === e.ramo)?.nome ?? `Ramo ${e.ramo}`);
  if (typeof e.valor_acima_de === 'number') partes.push(`acima de ${reais(e.valor_acima_de)}`);
  const modo = modos.find((m) => m.valor === e.modo)?.curto ?? e.modo;
  return `${partes.join(', ')}: ${modo}`;
}

export function Excecoes({ excecoes, ramos, modos, onChange, desabilitado }: {
  excecoes: Excecao[]; ramos: DadosServicos['ramos']; modos: OpcaoDeModo[]; onChange: (e: Excecao[]) => void;
  desabilitado?: boolean;
}) {
  const disponiveis = modos.filter((m) => !m.emBreve);
  const [ramo, setRamo] = useState('');
  const [valor, setValor] = useState('');
  const [modo, setModo] = useState<Modo>(disponiveis[0]?.valor ?? 'calcular');
  const [erro, setErro] = useState('');
  const adicionar = () => {
    const v = valor.trim() === '' ? undefined : Number(valor.replace(/\./g, '').replace(',', '.'));
    if (!ramo && v === undefined) { setErro('Escolha um ramo ou um valor.'); return; }
    if (v !== undefined && (!Number.isFinite(v) || v < 0)) { setErro('O valor precisa ser um número.'); return; }
    const e: Excecao = { modo };
    if (ramo) e.ramo = ramo;
    if (v !== undefined) e.valor_acima_de = v;
    onChange([...excecoes, e]);
    setRamo(''); setValor(''); setErro('');
  };
  const campo = 'h-10 rounded-lg border border-border bg-background px-2 text-sm text-foreground';
  return (
    <div className="space-y-2">
      {excecoes.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhuma exceção: vale a escolha de cima para tudo.</p>
      ) : (
        <ul className="space-y-1">
          {excecoes.map((e, i) => (
            <li key={i} className="flex items-center justify-between gap-2 rounded-lg border border-border-soft px-3 py-2 text-sm">
              <span className="min-w-0 text-foreground">{textoDaExcecao(e, ramos, modos)}</span>
              <button type="button" disabled={desabilitado} onClick={() => onChange(excecoes.filter((_, j) => j !== i))}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:text-danger disabled:opacity-50"
                aria-label={`Tirar a exceção ${textoDaExcecao(e, ramos, modos)}`}>
                <X size={16} strokeWidth={1.6} aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
      {!desabilitado && (
        <div className="grid gap-2 sm:grid-cols-[1fr_1fr_1.4fr_auto]">
          <select aria-label="Ramo da exceção" value={ramo} onChange={(e) => setRamo(e.target.value)} className={campo}>
            <option value="">Qualquer ramo</option>
            {ramos.map((x) => <option key={x.codigo} value={x.codigo}>{x.nome}</option>)}
          </select>
          <input aria-label="Valor acima de, em reais (opcional)" inputMode="decimal" placeholder="Acima de R$ (opcional)"
            value={valor} onChange={(e) => setValor(e.target.value)} className={campo} />
          <select aria-label="O que fazer nesta exceção" value={modo} onChange={(e) => setModo(e.target.value as Modo)} className={campo}>
            {disponiveis.map((m) => <option key={m.valor} value={m.valor}>{m.titulo}</option>)}
          </select>
          <button type="button" onClick={adicionar}
            className="h-10 rounded-lg border border-border px-3 text-sm font-medium text-foreground hover:bg-surface-2">
            Adicionar
          </button>
        </div>
      )}
      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}
    </div>
  );
}

export function Preferidas({ ramos, lista, igualParaTodos, comum, nomeDoServico, onChange, desabilitado }: {
  ramos: DadosServicos['ramos']; lista: Preferencias; igualParaTodos: boolean; comum: Preferencias;
  nomeDoServico: string; desabilitado?: boolean;
  onChange: (p: { preferencias: Preferencias; igualParaTodos: boolean }) => void;
}) {
  const [novo, setNovo] = useState<Record<string, string>>({});
  const trocar = (ramo: string, itens: (string | number)[]) =>
    onChange({ preferencias: { ...lista, [ramo]: itens }, igualParaTodos });
  const mover = (ramo: string, i: number, d: number) => {
    const itens = [...(lista[ramo] || [])];
    const j = i + d;
    if (j < 0 || j >= itens.length) return;
    [itens[i], itens[j]] = [itens[j], itens[i]];
    trocar(ramo, itens);
  };
  const icone = 'inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground disabled:opacity-40';
  return (
    <div className="space-y-3">
      <div role="radiogroup" aria-label="De quem é a lista de seguradoras preferidas" className="flex flex-wrap gap-2">
        {[{ v: true, t: 'A lista da corretora' }, { v: false, t: `Uma lista só da ${nomeDoServico}` }].map((o) => (
          <button key={String(o.v)} type="button" role="radio" aria-checked={igualParaTodos === o.v} disabled={desabilitado}
            onClick={() => onChange({ igualParaTodos: o.v, preferencias: o.v ? JSON.parse(JSON.stringify(comum)) : lista })}
            className={cn('min-h-[40px] rounded-lg border px-3 text-sm',
              igualParaTodos === o.v ? 'border-primary bg-brand-soft text-foreground' : 'border-border text-muted-foreground hover:text-foreground')}>
            {o.t}
          </button>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">
        Em ordem: a primeira é a preferida. As outras continuam sendo cotadas — a preferida só aparece marcada e ganha no empate.
        {igualParaTodos ? ' Mudar aqui muda a lista de todos os aplicativos.' : ''}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {ramos.map((ramo) => (
          <div key={ramo.codigo} className="space-y-2 rounded-lg border border-border-soft p-3">
            <p className="text-sm font-medium text-foreground">{ramo.nome}</p>
            {(lista[ramo.codigo] || []).length === 0 && (
              <p className="text-sm text-muted-foreground">Nenhuma preferida: todas são comparadas igual.</p>
            )}
            <ol className="space-y-1">
              {(lista[ramo.codigo] || []).map((seg, i) => (
                <li key={`${seg}-${i}`} className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 truncate text-foreground">{i + 1}. {String(seg)}</span>
                  {!desabilitado && (
                    <span className="flex shrink-0 gap-1">
                      <button type="button" aria-label={`Subir ${seg}`} onClick={() => mover(ramo.codigo, i, -1)} className={icone}><ArrowUp size={14} aria-hidden /></button>
                      <button type="button" aria-label={`Descer ${seg}`} onClick={() => mover(ramo.codigo, i, 1)} className={icone}><ArrowDown size={14} aria-hidden /></button>
                      <button type="button" aria-label={`Tirar ${seg}`} onClick={() => trocar(ramo.codigo, (lista[ramo.codigo] || []).filter((_, j) => j !== i))} className={icone}><X size={14} aria-hidden /></button>
                    </span>
                  )}
                </li>
              ))}
            </ol>
            {!desabilitado && (
              <div className="flex gap-2">
                <input aria-label={`Seguradora preferida em ${ramo.nome}`} placeholder="Nome da seguradora"
                  value={novo[ramo.codigo] || ''} onChange={(e) => setNovo({ ...novo, [ramo.codigo]: e.target.value })}
                  className="h-10 min-w-0 flex-1 rounded-lg border border-border bg-background px-2 text-sm" />
                <button type="button"
                  onClick={() => {
                    const nome = (novo[ramo.codigo] || '').trim();
                    if (!nome) return;
                    trocar(ramo.codigo, [...(lista[ramo.codigo] || []), nome]);
                    setNovo({ ...novo, [ramo.codigo]: '' });
                  }}
                  className="h-10 rounded-lg border border-border px-3 text-sm font-medium text-foreground hover:bg-surface-2">
                  Pôr
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
