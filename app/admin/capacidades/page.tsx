'use client';

// SPEC-061 §10.4 — "O que o sistema sabe fazer".
//
// O rótulo não é "Skills e Tool Gateway". Esses são os nomes internos das
// peças; a pergunta que a tela responde é outra, e é essa que vira o título.
//
// O valor está no CRUZAMENTO, não na lista: uma ferramenta ativa cuja
// capability está desligada aparece como ativa e nunca executa. Hoje isso só
// se descobre quando o corretor pede alguma coisa e nada acontece.
import { useCallback, useEffect, useState } from 'react';

type Problema = { o_que: string; problema: string; efeito: string };
type Ferramenta = {
  tool_key: string;
  name: string;
  capability_key: string | null;
  side_effect_class: string;
  risk_level: string;
  requires_approval: boolean;
  is_active: boolean;
  poder_ativo: boolean | null;
};
type Skill = {
  skill_key: string;
  name: string;
  description: string;
  business_domain: string;
  is_active: boolean;
};
type Capacidade = {
  capability_key: string;
  name: string;
  category: string;
  risk: string;
  is_active: boolean;
};

const ABAS = [
  { chave: 'skills', rotulo: 'O que ele sabe fazer' },
  { chave: 'ferramentas', rotulo: 'Como ele faz' },
  { chave: 'poderes', rotulo: 'O que ele tem permissão de fazer' },
] as const;

const EFEITO: Record<string, string> = {
  none: 'não muda nada',
  read: 'só lê',
  prepare: 'prepara, não envia',
  write_reversible: 'altera, dá para desfazer',
  write_irreversible: 'altera e não desfaz',
  financial: 'mexe em dinheiro',
  communication: 'fala com alguém de fora',
  external_commitment: 'compromete a corretora',
};

export default function CapacidadesPage() {
  const [aba, setAba] = useState<(typeof ABAS)[number]['chave']>('skills');
  const [dados, setDados] = useState<{
    skills: Skill[];
    ferramentas: Ferramenta[];
    capacidades: Capacidade[];
    problemas: Problema[];
    mensagem: string;
    resumo: Record<string, number>;
  } | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const r = await fetch('/api/admin/control-plane/capabilities', { cache: 'no-store' });
      if (r.status === 403) {
        setErro('Seu papel não inclui ver as capacidades.');
        return;
      }
      setDados(await r.json());
    } catch {
      setErro('Não consegui carregar. Tente de novo em instantes.');
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">O que o sistema sabe fazer</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
          Os procedimentos que ele executa, as ferramentas que usa e os poderes que autorizam cada
          uma.
        </p>
        <p className="text-sm mt-2">
          Para ver isso <strong>de um agente específico</strong> — o que ele tem anexado agora e de
          onde veio a autorização —{' '}
          <a href="/admin/prompt-effective" className="underline underline-offset-2">
            abra o diagnóstico por agente
          </a>
          .
        </p>
      </header>

      {erro && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 p-4">
          <p className="text-sm text-amber-900 dark:text-amber-200">{erro}</p>
        </div>
      )}
      {carregando && <p className="text-sm text-neutral-500">Carregando…</p>}

      {dados && !erro && (
        <>
          {/* O cruzamento vem primeiro. É a única parte da tela que exige ação. */}
          {dados.problemas?.length > 0 ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 p-4 mb-6">
              <p className="text-sm font-medium text-amber-900 dark:text-amber-200 mb-2">
                {dados.mensagem}
              </p>
              <ul className="space-y-1">
                {dados.problemas.map((p) => (
                  <li key={p.o_que} className="text-sm text-amber-900 dark:text-amber-200">
                    <strong>{p.o_que}</strong>: {p.problema} — {p.efeito}.
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm mb-6">{dados.mensagem}</p>
          )}

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

          {aba === 'skills' && (
            <div className="grid gap-3 md:grid-cols-2">
              {dados.skills.map((s) => (
                <article
                  key={s.skill_key}
                  className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-medium">{s.name}</h2>
                    {!s.is_active && (
                      <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-500">
                        desligada
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                    {s.description}
                  </p>
                  <p className="text-xs text-neutral-500 mt-2 font-mono">{s.skill_key}</p>
                </article>
              ))}
            </div>
          )}

          {aba === 'ferramentas' && (
            <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 dark:bg-neutral-900 text-left">
                  <tr>
                    <th className="px-4 py-2 font-medium">Ferramenta</th>
                    <th className="px-4 py-2 font-medium">O que ela faz no mundo</th>
                    <th className="px-4 py-2 font-medium">Precisa aprovação</th>
                    <th className="px-4 py-2 font-medium">Poder que autoriza</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.ferramentas.map((t) => (
                    <tr
                      key={t.tool_key}
                      className="border-t border-neutral-100 dark:border-neutral-800"
                    >
                      <td className="px-4 py-2">
                        <div className={t.is_active ? '' : 'opacity-50'}>{t.name}</div>
                        <div className="text-xs text-neutral-500 font-mono">{t.tool_key}</div>
                      </td>
                      <td className="px-4 py-2">
                        {EFEITO[t.side_effect_class] || t.side_effect_class}
                      </td>
                      <td className="px-4 py-2">{t.requires_approval ? 'sim' : 'não'}</td>
                      <td className="px-4 py-2">
                        <span className="font-mono text-xs">{t.capability_key || '—'}</span>
                        {t.is_active && t.poder_ativo === false && (
                          <span className="ml-2 text-xs px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200">
                            desligado
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {aba === 'poderes' && (
            <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 dark:bg-neutral-900 text-left">
                  <tr>
                    <th className="px-4 py-2 font-medium">Poder</th>
                    <th className="px-4 py-2 font-medium">Assunto</th>
                    <th className="px-4 py-2 font-medium">Risco</th>
                    <th className="px-4 py-2 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.capacidades.map((c) => (
                    <tr
                      key={c.capability_key}
                      className="border-t border-neutral-100 dark:border-neutral-800"
                    >
                      <td className="px-4 py-2">
                        <div>{c.name}</div>
                        <div className="text-xs text-neutral-500 font-mono">
                          {c.capability_key}
                        </div>
                      </td>
                      <td className="px-4 py-2">{c.category}</td>
                      <td className="px-4 py-2">{c.risk}</td>
                      <td className="px-4 py-2">{c.is_active ? 'ativo' : 'desligado'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
