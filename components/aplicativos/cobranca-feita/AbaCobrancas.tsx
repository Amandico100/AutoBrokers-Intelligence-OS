'use client';

// SPEC-139 · L2 — a aba Cobranças: o TRABALHO FEITO da Cobrança (laudo de design §5, na forma de lista por dia).
//
//   Precisa de você   a fila que já existia (`PendenciasDaCobranca`): o que saiu e ainda espera alguém
//   O que saiu        cada boleto enviado, por dia: segurado mascarado, seguradora, recibo, situação
//
// Só LEITURA: a lista vem de `/api/dashboard/auxiliaries/cobranca/enviadas` (só a corretora da sessão, nome mascarado,
// nada de telefone — o filtro e a máscara moram no servidor). Nenhum número aqui é inventado: a contagem é a da lista,
// e "N a segurados" conta só o que chegou ao SEGURADO (`resumoDoQueSaiu` — o pacote da equipe e o teste têm nome).

import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';

import { resumoDoQueSaiu, type CobrancaQueSaiu } from '@/app/api/dashboard/auxiliaries/cobranca/enviadas/leitura';
import { Selo } from '@/components/aplicativos/casca/Selo';
import { Segmentado } from '@/components/aplicativos/configurar/pecas';
import { Skeleton } from '@/components/ui/skeleton';
import type { PropsDaAba } from '@/lib/auxiliaries/catalog';

import { PendenciasDaCobranca } from './PendenciasDaCobranca';

type Periodo = '7' | '30' | '90';
const FUSO = 'America/Sao_Paulo';

/** "2026-10-15" no fuso de São Paulo — a chave do dia. */
function diaEmSaoPaulo(iso: string): string {
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return '';
  return new Intl.DateTimeFormat('en-CA', { timeZone: FUSO, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
}

function tituloDoDia(dia: string, agora: Date): string {
  const hoje = diaEmSaoPaulo(agora.toISOString());
  const ontem = diaEmSaoPaulo(new Date(agora.getTime() - 86_400_000).toISOString());
  if (dia === hoje) return 'Hoje';
  if (dia === ontem) return 'Ontem';
  const d = new Date(`${dia}T12:00:00-03:00`);
  return d.toLocaleDateString('pt-BR', { timeZone: FUSO, weekday: 'long', day: 'numeric', month: 'long' });
}

function hora(iso: string): string {
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return '';
  return d.toLocaleTimeString('pt-BR', { timeZone: FUSO, hour: '2-digit', minute: '2-digit' });
}

export function AbaCobrancas(_props: Partial<PropsDaAba> = {}) {
  const [periodo, setPeriodo] = useState<Periodo>('30');
  const [itens, setItens] = useState<CobrancaQueSaiu[] | null>(null);
  const [limite, setLimite] = useState(0);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (p: Periodo) => {
    setErro('');
    setItens(null);
    try {
      const res = await fetch(`/api/dashboard/auxiliaries/cobranca/enviadas?periodo=${p}`, { cache: 'no-store' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || !j?.ok) {
        if (j?.details) console.error('[COBRANCAS]', j.details);
        setErro(j?.error || 'Não conseguimos carregar as cobranças agora.');
        setItens([]);
        return;
      }
      setLimite(Number(j.limite) || 0);
      setItens((j.itens || []) as CobrancaQueSaiu[]);
    } catch {
      setErro('Sem conexão com o servidor agora. Tente de novo em instantes.');
      setItens([]);
    }
  }, []);

  useEffect(() => { carregar(periodo); }, [carregar, periodo]);

  const porDia = useMemo(() => {
    const grupos = new Map<string, CobrancaQueSaiu[]>();
    for (const c of itens || []) {
      const dia = diaEmSaoPaulo(c.quando);
      if (!grupos.has(dia)) grupos.set(dia, []);
      grupos.get(dia)!.push(c);
    }
    return Array.from(grupos.entries());
  }, [itens]);

  const agora = new Date();
  const total = itens?.length ?? 0;

  return (
    <div className="space-y-10 pb-6">
      <PendenciasDaCobranca titulo="Precisa de você" />

      <section className="space-y-4" aria-labelledby="cobrancas-o-que-saiu">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="space-y-1">
            <h2 id="cobrancas-o-que-saiu" className="text-lg font-semibold text-foreground">O que saiu</h2>
            <p className="text-sm text-muted-foreground" data-contagem>
              {itens === null ? 'Carregando…' : resumoDoQueSaiu(itens, periodo)}
            </p>
          </div>
          <Segmentado<Periodo> rotulo="Período" valor={periodo} onChange={setPeriodo}
            opcoes={[{ valor: '7', titulo: '7 dias' }, { valor: '30', titulo: '30 dias' }, { valor: '90', titulo: '90 dias' }]} />
        </div>

        {erro ? (
          <div className="space-y-3 rounded-xl border border-border bg-surface p-6">
            <p className="text-sm text-foreground">{erro}</p>
            <button type="button" onClick={() => carregar(periodo)}
              className="inline-flex h-11 items-center gap-2 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <RefreshCw size={16} strokeWidth={1.6} aria-hidden /> Tentar de novo
            </button>
          </div>
        ) : itens === null ? (
          <div className="space-y-2" aria-busy="true">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
          </div>
        ) : total === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-base font-medium text-foreground">Nenhuma cobrança saiu nos últimos {periodo} dias.</p>
            <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
              Quando a cobrança rodar, cada boleto enviado aparece aqui, separado por dia — o segurado, o recibo e o que
              aconteceu com ele.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {porDia.map(([dia, lista]) => (
              <section key={dia} aria-label={tituloDoDia(dia, agora)}>
                <h3 className="sticky top-[var(--altura-das-abas,45px)] z-[5] -mx-1 bg-background/95 px-1 py-2 text-sm font-medium text-foreground sm:backdrop-blur">
                  <span className="first-letter:uppercase">{tituloDoDia(dia, agora)}</span>
                  <span className="ml-2 font-normal tabular-nums text-muted-foreground">{lista.length}</span>
                </h3>
                <ul className="divide-y divide-border-soft rounded-xl border border-border bg-surface">
                  {lista.map((c) => (
                    // juiz de design 139 (Cobranças §1): no celular EMPILHA — o nome em cima, sozinho na largura; o
                    // recibo, a situação e a hora embaixo. A partir de 640 px volta a ser uma linha.
                    <li key={c.id} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:gap-4" data-cobranca={c.id}>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{c.segurado || 'Segurado sem nome no portal'}</p>
                        <p className="mt-0.5 text-sm text-muted-foreground">
                          {c.seguradora}
                          {c.recibo ? ` · recibo ${c.recibo}` : ''}
                          {c.destino === 'equipe' ? ' · para a equipe' : ''}
                          {c.para_final ? ` · para …${c.para_final}` : ''}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:flex-nowrap">
                        {c.teste && <Selo tom="info" rotulo="Teste" />}
                        <Selo tom={c.tom} rotulo={c.situacao} />
                        <span className="text-sm tabular-nums text-muted-foreground sm:w-12 sm:text-right">{hora(c.quando)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
            {limite > 0 && total >= limite && (
              <p className="text-sm text-muted-foreground">Mostrando as {limite} mais recentes deste período.</p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default AbaCobrancas;
