'use client';

// SPEC-059 §26 — Central de Inteligência.
//
// A aba que muda a forma de operar é **Regras**: cada detector mostra quanto
// produziu e quanto foi dispensado, e dá para pausar ou recalibrar sem deploy.
// Sem isso, um detector barulhento só se conserta no próximo release — e até
// lá ele ensina o corretor a ignorar avisos.
//
// Privacidade (§26.7): tudo aqui é agregado ou já redigido na origem. Nenhuma
// citação literal de conversa, nenhum dado de segurado.

import { useCallback, useEffect, useState } from 'react';

const ABAS = [
  { id: 'visao', rotulo: 'Visão geral' },
  { id: 'sinais', rotulo: 'Sinais' },
  { id: 'findings', rotulo: 'Diagnósticos' },
  { id: 'demanda', rotulo: 'Demanda' },
  { id: 'regras', rotulo: 'Regras' },
] as const;

function dataCurta(v?: string | null) {
  if (!v) return '—';
  try {
    return new Date(v).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '—';
  }
}

export default function InteligenciaPage() {
  const [aba, setAba] = useState<string>('visao');
  const [dados, setDados] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (qual: string) => {
    setCarregando(true);
    setErro('');
    try {
      const j = await fetch(`/api/admin/intelligence?aba=${qual}`).then((r) => r.json());
      if (j?.ok === false) setErro(j.error || 'Falha ao carregar.');
      setDados(j);
    } catch {
      setErro('Não foi possível carregar o painel.');
    }
    setCarregando(false);
  }, []);

  useEffect(() => {
    carregar(aba);
  }, [aba, carregar]);

  const agir = useCallback(
    async (corpo: Record<string, unknown>) => {
      await fetch('/api/admin/intelligence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
      });
      await carregar(aba);
    },
    [aba, carregar],
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 sm:px-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Central de Inteligência
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            O que o sistema percebeu, o que virou recomendação, quanto foi aceito e o que as
            corretoras estão pedindo. Tudo agregado ou já redigido na origem.
          </p>
        </header>

        <div className="flex gap-1 overflow-x-auto rounded-xl border border-border bg-card p-1">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition ${
                aba === a.id
                  ? 'bg-secondary text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
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
        ) : aba === 'visao' ? (
          <Visao dados={dados} />
        ) : aba === 'sinais' ? (
          <Sinais dados={dados} />
        ) : aba === 'findings' ? (
          <Diagnosticos dados={dados} />
        ) : aba === 'demanda' ? (
          <Demanda dados={dados} agir={agir} />
        ) : (
          <Regras dados={dados} agir={agir} />
        )}
      </div>
    </div>
  );
}

// ==========================================================================

function Metrica({
  rotulo,
  valor,
  nota,
  alerta,
}: {
  rotulo: string;
  valor: string | number;
  nota?: string;
  alerta?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        alerta ? 'border-destructive/40 bg-destructive/5' : 'border-border bg-card'
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {rotulo}
      </p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums text-foreground">{valor}</p>
      {nota && <p className="mt-0.5 text-xs text-muted-foreground">{nota}</p>}
    </div>
  );
}

function Visao({ dados }: { dados: any }) {
  const o = dados?.overview ?? {};
  const q = o?.qualidade ?? {};
  const mem = dados?.memoria?.diagnostico ?? {};

  const taxa = (v: number | null | undefined) =>
    v == null ? '—' : `${Number(v).toFixed(0)}%`;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Metrica rotulo="Sinais (7d)" valor={o.sinais ?? 0} />
        <Metrica rotulo="Suprimidos" valor={o.sinais_suprimidos ?? 0} nota="dedupe funcionando" />
        <Metrica rotulo="Diagnósticos ativos" valor={o.findings_ativos ?? 0} />
        <Metrica rotulo="Recomendações" valor={o.recomendacoes ?? 0} />
        <Metrica rotulo="Briefings" valor={o.briefings ?? 0} />
        <Metrica rotulo="Candidatos a conhecimento" valor={o.candidatos_conhecimento ?? 0} />
      </div>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground">Qualidade das recomendações</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          {q.observacao ||
            'Taxas calculadas sobre o que foi efetivamente entregue no período. Sem entrega, não há taxa — e isso aparece como “—”, não como zero.'}
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <Metrica rotulo="Entregues" valor={q.entregues ?? 0} />
          <Metrica rotulo="Aceitação" valor={taxa(q.taxa_aceitacao)} />
          <Metrica rotulo="Dispensa" valor={taxa(q.taxa_dispensa)} />
          <Metrica
            rotulo="Dado errado"
            valor={taxa(q.taxa_dado_errado)}
            alerta={Number(q.taxa_dado_errado || 0) > 10}
            nota={Number(q.taxa_dado_errado || 0) > 10 ? 'investigar a fonte' : undefined}
          />
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground">Saúde da memória</h2>
        <p className="mt-1 text-xs text-muted-foreground">{mem.observacao}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-5">
          <Metrica rotulo="Conversas" valor={mem.conversas ?? '—'} />
          <Metrica
            rotulo="Resumos de sessão"
            valor={mem.session_summaries ?? '—'}
            alerta={mem.saudavel === false}
          />
          <Metrica rotulo="Memórias pessoais" valor={mem.user_memories ?? '—'} />
          <Metrica rotulo="Memórias da corretora" valor={mem.company_memories ?? '—'} />
          <Metrica rotulo="Candidatos" valor={mem.knowledge_candidates ?? '—'} />
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Última execução por regra</h2>
        </div>
        <ul className="divide-y divide-border">
          {(o.regras || []).map((r: any) => (
            <li key={r.rule_key} className="flex items-center gap-4 px-5 py-2.5">
              <code className="w-64 flex-none truncate text-xs text-muted-foreground">
                {r.rule_key}
              </code>
              <span className="min-w-0 flex-1 truncate text-sm text-foreground">{r.name}</span>
              <span
                className={`flex-none text-[11px] ${
                  r.status === 'active'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-muted-foreground'
                }`}
              >
                {r.status}
              </span>
              <span className="w-40 flex-none text-right text-[11px] text-muted-foreground">
                {dataCurta(r.last_run_at)}
              </span>
              <span className="w-16 flex-none text-right text-[11px] tabular-nums text-muted-foreground">
                {r.last_run_signals ?? 0}
              </span>
            </li>
          ))}
          {!(o.regras || []).length && (
            <li className="px-5 py-10 text-center text-sm text-muted-foreground">
              Nenhuma regra publicada.
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}

function Sinais({ dados }: { dados: any }) {
  const sinais: any[] = dados?.sinais ?? [];
  const TIER: Record<number, string> = {
    0: 'dado vivo',
    1: 'evento do sistema',
    2: 'documento',
    3: 'análise',
    4: 'declaração',
    5: 'inferência',
  };
  if (!sinais.length) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card px-5 py-10 text-center text-sm text-muted-foreground">
        Nenhum sinal registrado ainda. Eles aparecem sozinhos conforme os detectores rodam.
      </div>
    );
  }
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-5 py-3 font-semibold">Sinal</th>
              <th className="px-5 py-3 font-semibold">Tipo</th>
              <th className="px-5 py-3 font-semibold">Base</th>
              <th className="px-5 py-3 font-semibold">Severidade</th>
              <th className="px-5 py-3 text-right font-semibold">Prioridade</th>
              <th className="px-5 py-3 text-right font-semibold">Vezes</th>
              <th className="px-5 py-3 font-semibold">Situação</th>
            </tr>
          </thead>
          <tbody>
            {sinais.map((s) => (
              <tr key={s.id} className="border-b border-border last:border-0">
                <td className="max-w-md px-5 py-3">
                  <p className="truncate text-foreground">{s.summary_redacted}</p>
                  <code className="text-[10px] text-muted-foreground">
                    {s.rule_key}@{s.rule_version}
                  </code>
                </td>
                <td className="px-5 py-3 text-xs text-muted-foreground">{s.signal_type}</td>
                <td className="px-5 py-3 text-xs text-muted-foreground">
                  {TIER[Number(s.trust_tier)] ?? s.trust_tier}
                </td>
                <td className="px-5 py-3 text-xs">
                  <span
                    className={
                      s.severity === 'critical' || s.severity === 'high'
                        ? 'text-destructive'
                        : 'text-muted-foreground'
                    }
                  >
                    {s.severity}
                  </span>
                </td>
                <td className="px-5 py-3 text-right tabular-nums text-foreground">
                  {Number(s.priority_score || 0).toFixed(0)}
                </td>
                <td className="px-5 py-3 text-right tabular-nums text-muted-foreground">
                  {s.occurrence_count}
                </td>
                <td className="px-5 py-3 text-xs text-muted-foreground">{s.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Diagnosticos({ dados }: { dados: any }) {
  const findings: any[] = dados?.findings?.findings ?? [];
  const briefings: any[] = dados?.briefings?.briefings ?? [];
  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Diagnósticos</h2>
        </div>
        {findings.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhum diagnóstico registrado.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {findings.map((f) => (
              <li key={f.id} className="flex items-start gap-4 px-5 py-3">
                <span className="w-12 flex-none text-right text-sm font-semibold tabular-nums text-foreground">
                  {Number(f.priority_score || 0).toFixed(0)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-foreground">{f.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{f.summary}</p>
                </div>
                <span className="w-28 flex-none text-right text-[11px] text-muted-foreground">
                  {f.status}
                </span>
                <span className="w-20 flex-none text-right text-[11px] text-muted-foreground">
                  {f.delivery_count ?? 0}× entregue
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Briefings publicados</h2>
        </div>
        {briefings.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhum briefing publicado.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {briefings.map((b) => (
              <li key={b.id} className="flex items-center gap-4 px-5 py-2.5">
                <span className="w-32 flex-none text-xs text-muted-foreground">
                  {b.briefing_type}
                </span>
                <p className="min-w-0 flex-1 truncate text-sm text-foreground">{b.headline}</p>
                <span className="flex-none text-[11px] text-muted-foreground">
                  {b.item_count ?? 0} itens
                </span>
                <span className="w-32 flex-none text-right text-[11px] text-muted-foreground">
                  {dataCurta(b.published_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Demanda({ dados, agir }: { dados: any; agir: (c: Record<string, unknown>) => void }) {
  const clusters: any[] = dados?.clusters?.clusters ?? [];
  const candidatos: any[] = dados?.candidatos?.candidatos ?? [];
  const maior = Math.max(1, ...clusters.map((c) => Number(c.tenant_count || 0)));

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">O que as corretoras querem delegar</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Ordenado por número de corretoras distintas, não por número de pedidos: dez pedidos de
            uma corretora são um caso; um pedido de dez corretoras é um produto.
          </p>
        </div>
        {clusters.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhuma necessidade agrupada ainda.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {clusters.map((c) => (
              <li key={c.id} className="flex items-start gap-4 px-5 py-4">
                <div className="flex w-16 flex-none flex-col items-center">
                  <span className="text-lg font-semibold tabular-nums text-foreground">
                    {c.tenant_count}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {Number(c.tenant_count) === 1 ? 'corretora' : 'corretoras'}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-foreground">{c.canonical_problem}</p>
                  <div className="mt-1.5 h-1 w-full max-w-md overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${(Number(c.tenant_count || 0) / maior) * 100}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {c.request_count} pedido(s) · demanda {Number(c.demand_score || 0).toFixed(0)}
                  </p>
                </div>
                <select
                  value={c.status}
                  onChange={(e) => agir({ acao: 'cluster', id: c.id, status: e.target.value })}
                  className="flex-none rounded-lg border border-border bg-background px-2 py-1 text-xs text-foreground"
                >
                  {['new', 'triaged', 'researching', 'planned', 'building', 'released', 'rejected'].map(
                    (s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ),
                  )}
                </select>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">Fila de conhecimento</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Candidatos aguardando curadoria. Nada aqui está publicado — nenhuma fonte publica
            direto no conhecimento das corretoras.
          </p>
        </div>
        {candidatos.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhum candidato na fila.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {candidatos.map((k) => (
              <li key={k.id} className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                    {k.scope}
                  </span>
                  {k.risk_level !== 'low' && (
                    <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">
                      risco {k.risk_level}
                    </span>
                  )}
                  {k.status === 'conflicted' && (
                    <span className="rounded-full bg-destructive/15 px-2 py-0.5 text-[10px] text-destructive">
                      contradiz conhecimento aprovado
                    </span>
                  )}
                  <span className="ml-auto text-[11px] text-muted-foreground">
                    {k.source_count} fonte(s)
                  </span>
                </div>
                <p className="mt-1 text-sm text-foreground">{k.title}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                  {k.statement_redacted}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Regras({ dados, agir }: { dados: any; agir: (c: Record<string, unknown>) => void }) {
  const regras: any[] = dados?.regras?.regras ?? [];
  const registrados: string[] = dados?.regras?.detectores_registrados ?? [];
  const semDetector = regras.filter((r) => !registrados.includes(r.rule_key));
  // SPEC-059 (melhoria): "o número está errado" é informação sobre o DETECTOR,
  // não sobre o silêncio. Três corretoras distintas dizendo o mesmo significa
  // que o limiar ou a fonte estão errados — e isso precisa de olho humano.
  // Nada é recalibrado automaticamente, de propósito.
  const paraRevisar = regras.filter((r) => r.qualidade?.revisar_limiar);

  return (
    <div className="space-y-5">
      {paraRevisar.length > 0 && (
        <section className="rounded-xl border border-destructive/30 bg-destructive/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            {paraRevisar.length} regra(s) com o número contestado por várias corretoras
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Quando corretoras diferentes dizem que o mesmo detector erra, o problema
            não é preferência — é o limiar, a fonte ou a conta. Nada foi ajustado
            automaticamente: a decisão é sua.
          </p>
          <ul className="mt-3 space-y-2">
            {paraRevisar.map((r) => (
              <li key={r.rule_key} className="flex items-start gap-3 text-sm">
                <span className="w-8 flex-none text-right font-semibold tabular-nums text-destructive">
                  {r.qualidade.dado_errado_tenants}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground">{r.name}</p>
                  <p className="text-xs text-muted-foreground">{r.qualidade.motivo_revisao}</p>
                </div>
                <button
                  onClick={() => agir({ acao: 'regra', rule_key: r.rule_key, status: 'paused' })}
                  className="flex-none rounded-lg border border-border px-3 py-1 text-xs text-foreground hover:bg-secondary"
                >
                  Pausar até revisar
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {semDetector.length > 0 && (
        <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            {semDetector.length} regra(s) sem detector registrado
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Elas nunca vão produzir sinal. Regra sem código é pior que regra pausada, porque
            parece ligada.
          </p>
          <ul className="mt-2 space-y-1">
            {semDetector.map((r) => (
              <li key={r.rule_key} className="text-xs text-muted-foreground">
                • <code>{r.rule_key}</code>
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
                <th className="px-5 py-3 font-semibold">Regra</th>
                <th className="px-5 py-3 font-semibold">Versão</th>
                <th className="px-5 py-3 text-right font-semibold">Sinais</th>
                <th className="px-5 py-3 text-right font-semibold">Rejeição</th>
                <th className="px-5 py-3 text-right font-semibold">Nº errado</th>
                <th className="px-5 py-3 font-semibold">Último run</th>
                <th className="px-5 py-3 font-semibold">Ação</th>
              </tr>
            </thead>
            <tbody>
              {regras.map((r) => {
                const q = r.qualidade || {};
                const barulhenta = Number(q.taxa_rejeicao || 0) > 40;
                return (
                  <tr key={r.rule_key} className="border-b border-border last:border-0">
                    <td className="px-5 py-3">
                      <p className="font-medium text-foreground">{r.name}</p>
                      <code className="text-[10px] text-muted-foreground">{r.rule_key}</code>
                    </td>
                    <td className="px-5 py-3 text-xs text-muted-foreground">{r.version}</td>
                    <td className="px-5 py-3 text-right tabular-nums text-foreground">
                      {q.sinais ?? 0}
                    </td>
                    <td
                      className={`px-5 py-3 text-right tabular-nums ${
                        barulhenta ? 'font-semibold text-destructive' : 'text-muted-foreground'
                      }`}
                    >
                      {q.taxa_rejeicao != null ? `${q.taxa_rejeicao}%` : '—'}
                    </td>
                    <td
                      className={`px-5 py-3 text-right tabular-nums ${
                        q.revisar_limiar ? 'font-semibold text-destructive' : 'text-muted-foreground'
                      }`}
                      title={
                        q.dado_errado_tenants
                          ? `${q.dado_errado_tenants} corretora(s) distinta(s) contestaram o número`
                          : 'ninguém contestou o número desta regra'
                      }
                    >
                      {q.dado_errado ? `${q.dado_errado} (${q.dado_errado_tenants ?? 0})` : '—'}
                    </td>
                    <td className="px-5 py-3 text-xs text-muted-foreground">
                      {dataCurta(r.last_run_at)}
                    </td>
                    <td className="px-5 py-3">
                      <button
                        onClick={() =>
                          agir({
                            acao: 'regra',
                            rule_key: r.rule_key,
                            status: r.status === 'active' ? 'paused' : 'active',
                          })
                        }
                        className="rounded-lg border border-border px-3 py-1 text-xs text-foreground hover:bg-secondary"
                      >
                        {r.status === 'active' ? 'Pausar' : 'Ativar'}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {regras.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    Nenhuma regra publicada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
