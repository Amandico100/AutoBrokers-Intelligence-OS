'use client';

// SPEC-061 §13 — "O que precisa de mim".
//
// O operador da plataforma não abre nove telas de manhã. Ele abre uma, e a
// pergunta é sempre a mesma. O rótulo do menu é essa pergunta.
//
// Linguagem humana, como o Founder pediu: "Trabalho parado no meio" e não
// "work_run stale lease". O termo técnico fica no detalhe, para quem for
// executar.
import { useCallback, useEffect, useState } from 'react';

type Item = {
  fonte: string;
  chave: string;
  titulo: string;
  detalhe: string;
  severidade: string;
  company_id: string | null;
  empresas_afetadas: number;
  itens_agrupados: number;
  ocorrido_em: string | null;
  href: string | null;
  acao_sugerida: string | null;
  prioridade: number;
  estado: string;
};

const CORES: Record<string, string> = {
  critical: 'border-l-red-500',
  high: 'border-l-amber-500',
  medium: 'border-l-blue-400',
  low: 'border-l-neutral-300 dark:border-l-neutral-700',
};

const NOME_DA_FONTE: Record<string, string> = {
  approval: 'Aprovação',
  work_run: 'Trabalho',
  research_monitor: 'Pesquisa',
  signal: 'Inteligência',
  knowledge: 'Conhecimento',
  incident: 'Incidente',
};

function quando(v: string | null): string {
  if (!v) return '';
  try {
    const d = new Date(v);
    const min = Math.floor((Date.now() - d.getTime()) / 60000);
    if (min < 1) return 'agora';
    if (min < 60) return `há ${min} min`;
    if (min < 1440) return `há ${Math.floor(min / 60)} h`;
    return `há ${Math.floor(min / 1440)} d`;
  } catch {
    return '';
  }
}

export default function InboxPage() {
  const [itens, setItens] = useState<Item[]>([]);
  const [mensagem, setMensagem] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const r = await fetch('/api/admin/control-plane/inbox', { cache: 'no-store' });
      if (r.status === 403) {
        setErro('Seu papel não inclui ver esta caixa.');
        return;
      }
      const j = await r.json();
      setItens(j?.itens ?? []);
      setMensagem(j?.mensagem ?? '');
    } catch {
      setErro('Não consegui carregar. Tente de novo em instantes.');
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function marcar(item: Item, estado: string) {
    // Otimista: o operador que dispensa dez itens não pode esperar dez
    // ida-e-voltas. Se o servidor recusar, `carregar()` traz a verdade.
    setItens((atual) => atual.filter((x) => !(x.fonte === item.fonte && x.chave === item.chave)));
    try {
      const r = await fetch('/api/admin/control-plane/inbox', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fonte: item.fonte, chave: item.chave, estado }),
      });
      if (!r.ok) await carregar();
    } catch {
      await carregar();
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">O que precisa de mim</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            Aprovações, trabalhos parados, fontes que não puderam ser lidas e incidentes — em um
            lugar só, do mais urgente para o menos.
          </p>
        </div>
        <button
          onClick={carregar}
          className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900"
        >
          Atualizar
        </button>
      </header>

      {carregando && <p className="text-sm text-neutral-500">Carregando…</p>}

      {erro && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 p-4">
          <p className="text-sm text-amber-900 dark:text-amber-200">{erro}</p>
        </div>
      )}

      {!carregando && !erro && itens.length === 0 && (
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-8 text-center">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {mensagem || 'Nada precisa de você agora.'}
          </p>
        </div>
      )}

      <ul className="space-y-3">
        {itens.map((item) => (
          <li
            key={`${item.fonte}:${item.chave}`}
            className={`rounded-lg border border-neutral-200 dark:border-neutral-800 border-l-4 ${
              CORES[item.severidade] ?? CORES.low
            } p-4`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400">
                    {NOME_DA_FONTE[item.fonte] ?? item.fonte}
                  </span>
                  {item.itens_agrupados > 1 && (
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-200">
                      {item.itens_agrupados} casos com a mesma causa
                    </span>
                  )}
                  {item.empresas_afetadas > 1 && (
                    <span className="text-xs px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200">
                      {item.empresas_afetadas} corretoras
                    </span>
                  )}
                  <span className="text-xs text-neutral-500">{quando(item.ocorrido_em)}</span>
                </div>
                <h2 className="font-medium mt-2">{item.titulo}</h2>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                  {item.detalhe}
                </p>
                {item.acao_sugerida && (
                  <p className="text-sm mt-2">
                    <span className="text-neutral-500">Sugestão: </span>
                    {item.href ? (
                      <a href={item.href} className="underline underline-offset-2">
                        {item.acao_sugerida}
                      </a>
                    ) : (
                      item.acao_sugerida
                    )}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-1 shrink-0">
                <button
                  onClick={() => marcar(item, 'acknowledged')}
                  className="text-xs px-2 py-1 rounded border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900"
                >
                  Já vi
                </button>
                <button
                  onClick={() => marcar(item, 'dismissed')}
                  className="text-xs px-2 py-1 rounded border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900"
                  title="Some da sua caixa. O item original continua onde está."
                >
                  Dispensar
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {itens.length > 0 && (
        <p className="text-xs text-neutral-500 mt-6">
          Dispensar tira o item da sua caixa e não muda nada no objeto original — a aprovação
          continua pendente, o trabalho continua parado.
        </p>
      )}
    </div>
  );
}
