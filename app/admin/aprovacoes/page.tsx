'use client';

// SPEC-061 §16 — "Esperando decisão".
//
// A diferença para a Central de Trabalhos: lá o operador conserta, aqui ele
// decide. Dois estados de espera diferentes — misturá-los faz procurar defeito
// onde só falta alguém clicar.
//
// A ordem é por IDADE, não por severidade. Uma aprovação parada há três dias
// não é um item da lista: é um cliente sem resposta.
import { useCallback, useEffect, useState } from 'react';

type Item = {
  id: string;
  company_id: string;
  o_que: string;
  sobre: string;
  risco: string;
  previa: Record<string, unknown>;
  criado_em: string | null;
  horas_esperando: number | null;
  vencida: boolean;
  status: string;
};

function espera(h: number | null): string {
  if (h == null) return '';
  if (h < 1) return 'agora há pouco';
  if (h < 24) return `há ${Math.round(h)} h`;
  return `há ${Math.floor(h / 24)} dia(s)`;
}

export default function AprovacoesPage() {
  const [itens, setItens] = useState<Item[]>([]);
  const [mensagem, setMensagem] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [recado, setRecado] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const r = await fetch('/api/admin/control-plane/approvals', { cache: 'no-store' });
      if (r.status === 403) {
        setErro('Seu papel não inclui ver as aprovações.');
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

  async function decidir(item: Item, decisao: 'approved' | 'rejected') {
    const motivo =
      decisao === 'rejected'
        ? window.prompt('Por que está recusando? Quem pediu precisa saber o que corrigir.')
        : window.prompt('Quer registrar algum motivo? (opcional)') ?? '';
    if (decisao === 'rejected' && !motivo) return;

    setOcupado(true);
    setRecado(null);
    try {
      const r = await fetch('/api/admin/control-plane/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_id: item.id,
          company_id: item.company_id,
          decisao,
          motivo,
        }),
      });
      const j = await r.json().catch(() => ({}));
      setRecado(j?.mensagem || (r.ok ? 'Feito.' : 'Não foi possível.'));
      await carregar();
    } catch {
      setRecado('Não foi possível falar com o serviço.');
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Esperando decisão</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            Ações que só acontecem depois que alguém aprovar. Da mais antiga para a mais recente.
          </p>
        </div>
        <button
          onClick={carregar}
          className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900"
        >
          Atualizar
        </button>
      </header>

      {erro && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 p-4">
          <p className="text-sm text-amber-900 dark:text-amber-200">{erro}</p>
        </div>
      )}

      {!erro && mensagem && <p className="text-sm mb-4">{mensagem}</p>}
      {recado && <p className="text-sm mb-4">{recado}</p>}
      {carregando && <p className="text-sm text-neutral-500">Carregando…</p>}

      {!carregando && !erro && itens.length === 0 && (
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-8 text-center">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Nenhuma decisão esperando você.
          </p>
        </div>
      )}

      <ul className="space-y-3">
        {itens.map((i) => (
          <li
            key={i.id}
            className={`rounded-lg border border-neutral-200 dark:border-neutral-800 border-l-4 p-4 ${
              i.vencida
                ? 'border-l-red-500'
                : i.risco === 'high' || i.risco === 'critical'
                  ? 'border-l-amber-500'
                  : 'border-l-neutral-300 dark:border-l-neutral-700'
            }`}
          >
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="min-w-0">
                <p className="font-medium">{i.o_que}</p>
                {i.sobre && (
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">{i.sobre}</p>
                )}
                <p className="text-xs text-neutral-500 mt-1">
                  {espera(i.horas_esperando)}
                  {i.vencida ? ' · passou do prazo' : ''}
                  {i.risco !== 'low' ? ` · risco ${i.risco}` : ''}
                </p>

                {/* A prévia é o que a ação FARIA. Sem ela, "aprovar" é assinar
                    em branco. */}
                {Object.keys(i.previa || {}).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-neutral-500 cursor-pointer select-none">
                      Ver o que vai acontecer
                    </summary>
                    <pre className="text-xs mt-2 p-3 rounded bg-neutral-50 dark:bg-neutral-900 overflow-x-auto max-w-full">
                      {JSON.stringify(i.previa, null, 2)}
                    </pre>
                  </details>
                )}
              </div>

              <div className="flex gap-2 shrink-0">
                <button
                  disabled={ocupado}
                  onClick={() => decidir(i, 'approved')}
                  className="text-sm px-3 py-1.5 rounded-md bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 disabled:opacity-40"
                >
                  Aprovar
                </button>
                <button
                  disabled={ocupado}
                  onClick={() => decidir(i, 'rejected')}
                  className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900 disabled:opacity-40"
                >
                  Recusar
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {itens.length > 0 && (
        <p className="text-xs text-neutral-500 mt-6">
          Aprovar não dispensa as verificações que a ação já tinha — ela segue pelo caminho normal.
          Toda decisão fica registrada com quem decidiu e quando.
        </p>
      )}
    </div>
  );
}
