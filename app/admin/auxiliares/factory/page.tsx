'use client';

// SPEC-058 §12 — painel da Factory.
//
// A aba que muda o jeito de decidir: **Oportunidades**. Hoje um pedido que o
// sistema não atende morre na conversa, e a priorização de roadmap vira
// opinião. Aqui cada linha carrega quantas corretoras pediram a mesma coisa e
// desde quando — evidência em vez de palpite.

import { useCallback, useEffect, useState } from 'react';

type Lacuna = {
  id: string; gap_type: string; capability_key: string | null; provider: string | null;
  description_redacted: string; frequency_count: number;
  first_seen_at: string; last_seen_at: string; status: string;
};
type Pedido = { exemplo: string; padrao: string | null; vezes: number; atendidos: number };
type Template = {
  id: string; slug: string; name: string; category: string; short_description: string;
  instalacoes: number; ativas: number; degradadas: number; releases: number;
  runtime_kind: string | null; sem_release_publicada: boolean;
};
type Instalacao = {
  id: string; corretora: string | null; name: string; status: string;
  health: string; health_reason: string | null; current_revision: number;
  installed_at: string; last_run_at: string | null;
};

const ROTULO_LACUNA: Record<string, string> = {
  missing_skill: 'Falta uma Skill',
  missing_tool: 'Falta uma ferramenta',
  missing_connector: 'Falta um conector',
  missing_data: 'Falta o dado',
  missing_provider: 'Falta um provedor',
  missing_artifact: 'Falta um tipo de entrega',
  policy_blocked: 'Bloqueado por política',
  unsupported_trigger: 'Gatilho não suportado',
  unsupported_workflow: 'Fluxo não suportado',
};

const ROTULO_PADRAO: Record<string, string> = {
  one_shot_work_run: 'Trabalho único',
  saved_routine: 'Rotina',
  installed_auxiliary: 'Auxiliar instalado',
  workflow_instance: 'Fluxo',
  specialized_executor: 'Executor',
  agent_backed_auxiliary: 'Agent',
};

const ABAS = [
  { id: 'oportunidades', rotulo: 'Oportunidades' },
  { id: 'catalogo', rotulo: 'Catálogo' },
  { id: 'instalacoes', rotulo: 'Instalações' },
] as const;

function dataCurta(v?: string | null) {
  if (!v) return '—';
  try { return new Date(v).toLocaleDateString('pt-BR'); } catch { return '—'; }
}

export default function FactoryPage() {
  const [aba, setAba] = useState<string>('oportunidades');
  const [dados, setDados] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (qual: string) => {
    setCarregando(true); setErro('');
    try {
      const j = await fetch(`/api/admin/factory?aba=${qual}`).then((r) => r.json());
      if (j?.ok === false) setErro(j.error || 'Falha ao carregar.');
      setDados(j);
    } catch {
      setErro('Não foi possível carregar o painel.');
    }
    setCarregando(false);
  }, []);

  useEffect(() => { carregar(aba); }, [aba, carregar]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 sm:px-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Fábrica de Auxiliares
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            O catálogo, quem instalou o quê, como está a saúde de cada instalação — e o
            que as corretoras pediram e o sistema ainda não faz.
          </p>
        </header>

        <div className="flex gap-1 overflow-x-auto rounded-xl border border-border bg-card p-1">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition ${
                aba === a.id ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </div>

        {erro && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground">
            {erro}
          </p>
        )}

        {carregando ? (
          <div className="rounded-xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">
            Carregando…
          </div>
        ) : aba === 'oportunidades' ? (
          <Oportunidades dados={dados} />
        ) : aba === 'catalogo' ? (
          <Catalogo dados={dados} />
        ) : (
          <Instalacoes dados={dados} />
        )}
      </div>
    </div>
  );
}

// ==========================================================================

function Metrica({ rotulo, valor, nota }: { rotulo: string; valor: string | number; nota?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{rotulo}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums text-foreground">{valor}</p>
      {nota && <p className="mt-0.5 text-xs text-muted-foreground">{nota}</p>}
    </div>
  );
}

function Oportunidades({ dados }: { dados: any }) {
  const lacunas: Lacuna[] = dados?.lacunas || [];
  const pedidos: Pedido[] = dados?.mais_pedidos || [];
  const r = dados?.resumo || {};
  const maior = Math.max(1, ...lacunas.map((l) => l.frequency_count));

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-4">
        <Metrica rotulo="Lacunas abertas" valor={r.lacunas_abertas ?? 0} />
        <Metrica rotulo="Peso total" valor={r.peso_total ?? 0} nota="vezes que foram pedidas" />
        <Metrica rotulo="Pedidos analisados" valor={r.pedidos_analisados ?? 0} />
        <Metrica rotulo="Necessidades distintas" valor={r.necessidades_distintas ?? 0} />
      </div>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">O que ainda não fazemos</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Ordenado por quantas vezes foi pedido. A mesma falta pedida cem vezes é
            uma lacuna com peso cem — não cem itens de backlog.
          </p>
        </div>
        {lacunas.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhuma lacuna registrada ainda. Elas aparecem sozinhas conforme os
            corretores pedirem coisas que o sistema não atende.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {lacunas.map((l) => (
              <li key={l.id} className="flex items-start gap-4 px-5 py-4">
                <div className="flex w-14 flex-none flex-col items-center">
                  <span className="text-lg font-semibold tabular-nums text-foreground">
                    {l.frequency_count}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {l.frequency_count === 1 ? 'vez' : 'vezes'}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-border bg-secondary px-2.5 py-0.5 text-[11px] font-medium text-foreground">
                      {ROTULO_LACUNA[l.gap_type] || l.gap_type}
                    </span>
                    {l.capability_key && (
                      <code className="text-[11px] text-muted-foreground">{l.capability_key}</code>
                    )}
                    {l.provider && (
                      <span className="text-[11px] text-muted-foreground">via {l.provider}</span>
                    )}
                  </div>
                  <p className="mt-1.5 text-sm text-foreground">{l.description_redacted}</p>
                  <div className="mt-1.5 h-1 w-full max-w-md overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${(l.frequency_count / maior) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="flex-none text-right text-[11px] text-muted-foreground">
                  <div>1ª vez {dataCurta(l.first_seen_at)}</div>
                  <div>última {dataCurta(l.last_seen_at)}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">O que mais pedem</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Pedidos agrupados por assinatura — três formas de pedir a mesma coisa
            contam como uma necessidade só.
          </p>
        </div>
        {pedidos.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhum pedido registrado ainda.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {pedidos.map((p, i) => (
              <li key={i} className="flex items-center gap-4 px-5 py-3">
                <span className="w-10 flex-none text-right text-sm font-semibold tabular-nums text-foreground">
                  {p.vezes}×
                </span>
                <p className="min-w-0 flex-1 truncate text-sm text-foreground">{p.exemplo}</p>
                {p.padrao && (
                  <span className="flex-none rounded-full border border-border px-2.5 py-0.5 text-[11px] text-muted-foreground">
                    {ROTULO_PADRAO[p.padrao] || p.padrao}
                  </span>
                )}
                <span className="w-24 flex-none text-right text-[11px] text-muted-foreground">
                  {p.atendidos}/{p.vezes} atendidos
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Catalogo({ dados }: { dados: any }) {
  const templates: Template[] = dados?.templates || [];
  const r = dados?.resumo || {};
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-4">
        <Metrica rotulo="Templates" valor={r.templates ?? 0} />
        <Metrica rotulo="Instalações" valor={r.instalacoes ?? 0} />
        <Metrica rotulo="Degradadas" valor={r.degradadas ?? 0} nota="precisam de atenção" />
        <Metrica rotulo="Sem release publicada" valor={r.sem_release ?? 0} nota="não são imutáveis" />
      </div>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-5 py-3 font-semibold">Auxiliar</th>
                <th className="px-5 py-3 font-semibold">Como executa</th>
                <th className="px-5 py-3 text-right font-semibold">Instalações</th>
                <th className="px-5 py-3 text-right font-semibold">Ativas</th>
                <th className="px-5 py-3 text-right font-semibold">Degradadas</th>
                <th className="px-5 py-3 font-semibold">Release</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id} className="border-b border-border last:border-0">
                  <td className="px-5 py-3">
                    <p className="font-medium text-foreground">{t.name}</p>
                    <p className="max-w-md truncate text-xs text-muted-foreground">
                      {t.short_description}
                    </p>
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">
                    {t.runtime_kind === 'agent_backed' ? (
                      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-amber-600 dark:text-amber-400">
                        Agent
                      </span>
                    ) : (
                      t.runtime_kind || '—'
                    )}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-foreground">{t.instalacoes}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-foreground">{t.ativas}</td>
                  <td className={`px-5 py-3 text-right tabular-nums ${
                    t.degradadas ? 'font-semibold text-destructive' : 'text-muted-foreground'}`}>
                    {t.degradadas}
                  </td>
                  <td className="px-5 py-3 text-xs">
                    {t.sem_release_publicada ? (
                      <span className="text-amber-600 dark:text-amber-400">sem release</span>
                    ) : (
                      <span className="text-muted-foreground">{t.releases} versão(ões)</span>
                    )}
                  </td>
                </tr>
              ))}
              {templates.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-muted-foreground">
                  Nenhum template ativo.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Instalacoes({ dados }: { dados: any }) {
  const linhas: Instalacao[] = dados?.instalacoes || [];
  const problema = linhas.filter((i) => i.health === 'degraded' || i.health === 'error');

  return (
    <div className="space-y-5">
      {problema.length > 0 && (
        <section className="rounded-xl border border-destructive/30 bg-destructive/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            {problema.length} instalação(ões) precisando de atenção
          </h2>
          <ul className="mt-3 space-y-1.5">
            {problema.slice(0, 8).map((i) => (
              <li key={i.id} className="flex items-baseline gap-3 text-sm">
                <span className="font-medium text-foreground">{i.corretora || '—'}</span>
                <span className="text-muted-foreground">{i.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {i.health_reason || i.health}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-5 py-3 font-semibold">Corretora</th>
                <th className="px-5 py-3 font-semibold">Auxiliar</th>
                <th className="px-5 py-3 font-semibold">Situação</th>
                <th className="px-5 py-3 font-semibold">Saúde</th>
                <th className="px-5 py-3 text-right font-semibold">Revisão</th>
                <th className="px-5 py-3 text-right font-semibold">Último trabalho</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((i) => (
                <tr key={i.id} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 text-foreground">{i.corretora || '—'}</td>
                  <td className="px-5 py-3 text-foreground">{i.name}</td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">{i.status}</td>
                  <td className="px-5 py-3 text-xs">
                    <span className={
                      i.health === 'ok' ? 'text-emerald-600 dark:text-emerald-400'
                        : i.health === 'unknown' ? 'text-muted-foreground'
                        : 'text-destructive'
                    }>
                      {i.health}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-muted-foreground">
                    {i.current_revision}
                  </td>
                  <td className="px-5 py-3 text-right text-xs tabular-nums text-muted-foreground">
                    {dataCurta(i.last_run_at)}
                  </td>
                </tr>
              ))}
              {linhas.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-muted-foreground">
                  Nenhuma instalação ainda.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
