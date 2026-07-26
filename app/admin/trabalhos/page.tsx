'use client';

// SPEC-061 §15 — Central de Trabalhos.
//
// É para onde a caixa "O que precisa de mim" manda quando o item é um
// trabalho. O rótulo do menu diz o que a página responde: o que está rodando,
// o que travou, o que falhou.
//
// Agregado no topo, lista embaixo — CA-014. Uma lista dos últimos 50 responde
// bem com 5 corretoras e deixa de responder qualquer coisa com mil.
import { useCallback, useEffect, useState } from 'react';

type Resumo = {
  total: number;
  esperando_humano: number;
  com_problema: number;
  travados: number;
  corretoras_afetadas: number;
  por_estado: { estado: string; rotulo: string; n: number }[];
  tipos_mais_comuns: { workflow: string; n: number }[];
  mensagem: string;
};

type Trabalho = {
  id: string;
  company_id: string | null;
  tipo: string;
  titulo: string | null;
  estado: string;
  rotulo: string;
  erro: string | null;
  criado_em: string | null;
  parado: boolean;
};

const FILTROS = [
  { chave: '', rotulo: 'Todos' },
  { chave: 'failed', rotulo: 'Falharam' },
  { chave: 'running', rotulo: 'Em andamento' },
  { chave: 'pending_approval', rotulo: 'Esperando decisão' },
  { chave: 'completed', rotulo: 'Concluídos' },
] as const;

function quando(v: string | null): string {
  if (!v) return '—';
  try {
    return new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return '—';
  }
}

export default function TrabalhosPage() {
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [lista, setLista] = useState<Trabalho[]>([]);
  const [filtro, setFiltro] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [recado, setRecado] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const q = new URLSearchParams({ dias: '7', limite: '60' });
      if (filtro) q.set('estado', filtro);
      const r = await fetch(`/api/admin/control-plane/work-runs?${q}`, { cache: 'no-store' });
      if (r.status === 403) {
        setErro('Seu papel não inclui ver os trabalhos.');
        return;
      }
      const j = await r.json();
      setResumo(j?.resumo ?? null);
      setLista(j?.lista ?? []);
    } catch {
      setErro('Não consegui carregar. Tente de novo em instantes.');
    } finally {
      setCarregando(false);
    }
  }, [filtro]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function agir(t: Trabalho, acao: 'reprocessar' | 'cancelar') {
    const motivo = window.prompt(
      acao === 'reprocessar'
        ? 'Por que este trabalho deve voltar para a fila? (fica registrado)'
        : 'Por que este trabalho deve ser cancelado? (fica registrado)',
    );
    if (motivo === null) return;
    setOcupado(true);
    setRecado(null);
    try {
      const r = await fetch('/api/admin/control-plane/work-runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acao, run_id: t.id, company_id: t.company_id, reason: motivo }),
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
    <div className="p-6 max-w-6xl mx-auto">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Trabalhos em andamento</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            O que está rodando, o que travou e o que falhou — nos últimos 7 dias.
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

      {!erro && resumo && (
        <>
          <p className="text-sm mb-4">{resumo.mensagem}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            {[
              { r: 'Total no período', v: resumo.total },
              { r: 'Parados sem sinal', v: resumo.travados },
              { r: 'Com problema', v: resumo.com_problema },
              { r: 'Corretoras afetadas', v: resumo.corretoras_afetadas },
            ].map((c) => (
              <div
                key={c.r}
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4"
              >
                <p className="text-xs text-neutral-500">{c.r}</p>
                <p className="text-2xl font-semibold mt-1">{c.v}</p>
              </div>
            ))}
          </div>
        </>
      )}

      <nav className="flex gap-1 flex-wrap mb-4">
        {FILTROS.map((f) => (
          <button
            key={f.chave}
            onClick={() => setFiltro(f.chave)}
            className={`text-sm px-3 py-1 rounded-md border ${
              filtro === f.chave
                ? 'border-neutral-900 dark:border-neutral-100 font-medium'
                : 'border-neutral-300 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400'
            }`}
          >
            {f.rotulo}
          </button>
        ))}
      </nav>

      {recado && <p className="text-sm mb-4">{recado}</p>}
      {carregando && <p className="text-sm text-neutral-500">Carregando…</p>}

      {!carregando && !erro && lista.length === 0 && (
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-8 text-center">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Nenhum trabalho com esse filtro no período.
          </p>
        </div>
      )}

      {lista.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 dark:bg-neutral-900 text-left">
              <tr>
                <th className="px-4 py-2 font-medium">O quê</th>
                <th className="px-4 py-2 font-medium">Estado</th>
                <th className="px-4 py-2 font-medium">Quando</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((t) => (
                <tr key={t.id} className="border-t border-neutral-100 dark:border-neutral-800">
                  <td className="px-4 py-2">
                    <div className="font-medium">{t.titulo || t.tipo}</div>
                    <div className="text-xs text-neutral-500 font-mono">{t.tipo}</div>
                    {t.erro && (
                      <div className="text-xs text-red-600 dark:text-red-400 mt-0.5">{t.erro}</div>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {t.rotulo}
                    {t.parado && (
                      <span className="ml-2 text-xs px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200">
                        sem sinal
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap">{quando(t.criado_em)}</td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    {['failed', 'cancelled', 'paused'].includes(t.estado) && (
                      <button
                        disabled={ocupado}
                        onClick={() => agir(t, 'reprocessar')}
                        className="text-xs px-2 py-1 rounded border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900 disabled:opacity-50"
                      >
                        Tentar de novo
                      </button>
                    )}
                    {['running', 'queued', 'paused', 'pending_approval'].includes(t.estado) && (
                      <button
                        disabled={ocupado}
                        onClick={() => agir(t, 'cancelar')}
                        className="text-xs px-2 py-1 ml-1 rounded border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900 disabled:opacity-50"
                      >
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-neutral-500 mt-6">
        Reprocessar recoloca na fila e preserva as etapas já concluídas. Cancelar é cooperativo: o
        trabalho para na próxima etapa, sem interromper ação externa pela metade.
      </p>
    </div>
  );
}
