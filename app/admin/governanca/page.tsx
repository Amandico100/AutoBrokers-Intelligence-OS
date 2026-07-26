'use client';

// SPEC-061 §8 e §9 — "Quem pode o quê".
//
// O rótulo diz o que a página RESPONDE, não como ela é feita por dentro. Um
// item chamado "RBAC" ou "Role bindings" obrigaria o operador a saber o nome
// interno da coisa para achar a tela onde se tira o acesso de alguém.
//
// A tela responde três perguntas, nessa ordem:
//   1. quem tem acesso administrativo hoje?
//   2. o que cada papel permite?
//   3. o que foi feito, por quem, e por quê?
import { useEffect, useState } from 'react';

type Papel = { role_key: string; nome: string; descricao: string; quantidade_de_permissions: number };
type Vinculo = {
  id: string;
  user_id: string;
  role_key: string;
  nome_do_papel: string;
  status: string;
  expires_at: string | null;
  reason: string | null;
  created_at: string;
};
type Evento = {
  id: string;
  occurred_at: string;
  actor_user_id: string;
  action_key: string;
  risk_tier: string;
  target_type: string;
  company_id: string | null;
  reason_redacted: string | null;
  result_status: string;
};

const ABAS = [
  { chave: 'pessoas', rotulo: 'Quem tem acesso' },
  { chave: 'papeis', rotulo: 'O que cada papel permite' },
  { chave: 'historico', rotulo: 'O que foi feito' },
] as const;

function data(v: string | null): string {
  if (!v) return '—';
  try {
    return new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return '—';
  }
}

function corDoRisco(risco: string): string {
  if (risco === 'critical') return 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200';
  if (risco === 'high') return 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200';
  if (risco === 'medium') return 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200';
  return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300';
}

export default function GovernancaPage() {
  const [aba, setAba] = useState<(typeof ABAS)[number]['chave']>('pessoas');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [papeis, setPapeis] = useState<Papel[]>([]);
  const [vinculos, setVinculos] = useState<Vinculo[]>([]);
  const [eventos, setEventos] = useState<Evento[]>([]);

  useEffect(() => {
    let vivo = true;
    (async () => {
      setCarregando(true);
      setErro(null);
      try {
        const [rolesRes, auditRes] = await Promise.all([
          fetch('/api/admin/control-plane/roles', { cache: 'no-store' }),
          fetch('/api/admin/control-plane/audit?limite=60', { cache: 'no-store' }),
        ]);
        if (!vivo) return;

        if (rolesRes.status === 403) {
          setErro('Seu papel não inclui ver a governança de acesso.');
          return;
        }
        const roles = await rolesRes.json().catch(() => ({}));
        setPapeis(roles?.catalogo?.papeis ?? []);
        setVinculos(roles?.vinculos?.vinculos ?? []);

        const audit = await auditRes.json().catch(() => ({}));
        setEventos(audit?.eventos ?? []);
      } catch {
        if (vivo) setErro('Não consegui carregar. Tente de novo em instantes.');
      } finally {
        if (vivo) setCarregando(false);
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  const ativos = vinculos.filter((v) => v.status === 'active');

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Quem pode o quê</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
          Quem tem acesso administrativo, o que cada papel permite e o registro do que foi feito.
        </p>
      </header>

      <nav className="flex gap-1 border-b border-neutral-200 dark:border-neutral-800 mb-6">
        {ABAS.map((a) => (
          <button
            key={a.chave}
            onClick={() => setAba(a.chave)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px transition ${
              aba === a.chave
                ? 'border-neutral-900 dark:border-neutral-100 font-medium'
                : 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'
            }`}
          >
            {a.rotulo}
          </button>
        ))}
      </nav>

      {carregando && <p className="text-sm text-neutral-500">Carregando…</p>}

      {erro && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 p-4">
          <p className="text-sm text-amber-900 dark:text-amber-200">{erro}</p>
        </div>
      )}

      {!carregando && !erro && aba === 'pessoas' && (
        <section>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
            {ativos.length === 0
              ? 'Ninguém tem papel administrativo atribuído ainda. Quem entra hoje usa o acesso histórico.'
              : `${ativos.length} pessoa(s) com acesso ativo.`}
          </p>
          {ativos.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 dark:bg-neutral-900 text-left">
                  <tr>
                    <th className="px-4 py-2 font-medium">Pessoa</th>
                    <th className="px-4 py-2 font-medium">Papel</th>
                    <th className="px-4 py-2 font-medium">Vale até</th>
                    <th className="px-4 py-2 font-medium">Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {ativos.map((v) => (
                    <tr key={v.id} className="border-t border-neutral-100 dark:border-neutral-800">
                      <td className="px-4 py-2 font-mono text-xs">{v.user_id.slice(0, 8)}…</td>
                      <td className="px-4 py-2">{v.nome_do_papel}</td>
                      <td className="px-4 py-2">
                        {v.expires_at ? data(v.expires_at) : 'sem prazo'}
                      </td>
                      <td className="px-4 py-2 text-neutral-600 dark:text-neutral-400">
                        {v.reason || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {!carregando && !erro && aba === 'papeis' && (
        <section className="grid gap-3 md:grid-cols-2">
          {papeis.map((p) => (
            <article
              key={p.role_key}
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4"
            >
              <h2 className="font-medium">{p.nome}</h2>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{p.descricao}</p>
              <p className="text-xs text-neutral-500 mt-2">
                {p.quantidade_de_permissions} ação(ões) permitida(s)
              </p>
            </article>
          ))}
        </section>
      )}

      {!carregando && !erro && aba === 'historico' && (
        <section>
          {eventos.length === 0 ? (
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Nenhuma ação administrativa registrada ainda. O registro começa a partir de agora — ele
              não reconstrói o passado.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 dark:bg-neutral-900 text-left">
                  <tr>
                    <th className="px-4 py-2 font-medium">Quando</th>
                    <th className="px-4 py-2 font-medium">O que</th>
                    <th className="px-4 py-2 font-medium">Risco</th>
                    <th className="px-4 py-2 font-medium">Resultado</th>
                    <th className="px-4 py-2 font-medium">Por quê</th>
                  </tr>
                </thead>
                <tbody>
                  {eventos.map((e) => (
                    <tr key={e.id} className="border-t border-neutral-100 dark:border-neutral-800">
                      <td className="px-4 py-2 whitespace-nowrap">{data(e.occurred_at)}</td>
                      <td className="px-4 py-2">{e.action_key}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs ${corDoRisco(e.risk_tier)}`}>
                          {e.risk_tier}
                        </span>
                      </td>
                      <td className="px-4 py-2">{e.result_status}</td>
                      <td className="px-4 py-2 text-neutral-600 dark:text-neutral-400 max-w-md">
                        {e.reason_redacted || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
