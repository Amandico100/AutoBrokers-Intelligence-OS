'use client';

// SPEC-059 §25 — Centro de Briefing.
//
// A tela responde uma pergunta só: **o que precisa de mim agora?**
//
// Duas decisões de desenho que vêm da SPEC e não do gosto:
//
// 1. Cada item mostra o FATO antes da leitura, e a leitura vem rotulada como
//    leitura (§13). Misturar os dois é o defeito que destrói a confiança
//    quando alguém confere o número.
// 2. Seção sem item não vira texto (§16.1). "Nenhum risco identificado" ocupa
//    espaço e ensina o corretor a pular seções — inclusive a que importa.

import { useCallback, useEffect, useState } from 'react';

type Item = {
  item_type: string;
  section: string;
  headline: string;
  summary?: string;
  evidence_summary?: string | null;
  confidence?: number | null;
  action_label?: string | null;
  action_payload?: Record<string, unknown>;
  priority_score?: number;
  finding_id?: string | null;
  recommendation_id?: string | null;
};
type Secao = { key: string; title: string; items: Item[] };
type Spec = {
  headline?: string;
  executive_summary?: string;
  sections?: Secao[];
  missing_data?: string[];
  methodology?: string;
  period?: { start?: string; end?: string };
};
type Publicacao = {
  id: string;
  headline?: string;
  summary_text?: string;
  payload?: Spec;
  period_start?: string;
  period_end?: string;
  item_count?: number;
  critical_count?: number;
  published_at?: string;
  artifact_id?: string | null;
  briefing_type?: string;
};
type Recomendacao = {
  id: string;
  title: string;
  summary: string;
  rationale?: string;
  confidence?: number;
  priority_score?: number;
  risk_level?: string;
  approval_required?: boolean;
  action_options?: { key: string; label: string; kind: string; executavel?: boolean }[];
  recommended_action_key?: string | null;
  expires_at?: string | null;
};
type Finding = {
  id: string;
  title: string;
  summary: string;
  fact_statement?: string | null;
  inference_statement?: string | null;
  missing_data?: string | null;
  next_step?: string | null;
  why_now?: string;
  severity?: string;
  priority_score?: number;
  confidence?: number;
};

const ABAS = [
  { id: 'hoje', rotulo: 'Hoje' },
  { id: 'semana', rotulo: 'Esta semana' },
  { id: 'oportunidades', rotulo: 'Oportunidades' },
  { id: 'historico', rotulo: 'Histórico' },
  { id: 'preferencias', rotulo: 'Preferências' },
] as const;

function dataCurta(v?: string | null) {
  if (!v) return '—';
  try {
    return new Date(v).toLocaleDateString('pt-BR');
  } catch {
    return '—';
  }
}

function faixaDePrioridade(score?: number): { rotulo: string; classe: string } {
  const s = Number(score || 0);
  if (s >= 85) return { rotulo: 'Crítico', classe: 'bg-destructive/15 text-destructive' };
  if (s >= 70) return { rotulo: 'Alto', classe: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' };
  if (s >= 50) return { rotulo: 'Médio', classe: 'bg-secondary text-muted-foreground' };
  return { rotulo: 'Informativo', classe: 'bg-secondary text-muted-foreground' };
}

export default function BriefingPage() {
  const [aba, setAba] = useState<string>('hoje');
  const [dados, setDados] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState('');

  const carregar = useCallback(async (qual: string) => {
    setCarregando(true);
    setErro('');
    try {
      const j = await fetch(`/api/dashboard/briefing?aba=${qual}`).then((r) => r.json());
      if (j?.ok === false) setErro(j.error || 'Não foi possível carregar.');
      setDados(j);
    } catch {
      setErro('Não foi possível carregar o briefing.');
    }
    setCarregando(false);
  }, []);

  useEffect(() => {
    carregar(aba);
  }, [aba, carregar]);

  const agir = useCallback(
    async (corpo: Record<string, unknown>) => {
      setOcupado(String(corpo.id || 'acao'));
      try {
        await fetch('/api/dashboard/briefing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(corpo),
        });
        await carregar(aba);
      } catch {
        setErro('A ação não foi registrada. Tente de novo.');
      }
      setOcupado('');
    },
    [aba, carregar],
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 sm:px-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Briefing</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            O que precisa de você, o que já foi resolvido e o que dá para deixar automático.
            Todo número aqui vem do que aconteceu na sua corretora — nada é estimado.
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
        ) : aba === 'hoje' ? (
          <Hoje dados={dados} agir={agir} ocupado={ocupado} recarregar={() => carregar('hoje')} />
        ) : aba === 'semana' ? (
          <Semana dados={dados} recarregar={() => carregar('semana')} />
        ) : aba === 'oportunidades' ? (
          <Oportunidades dados={dados} agir={agir} ocupado={ocupado} />
        ) : aba === 'historico' ? (
          <Historico dados={dados} />
        ) : (
          <Preferencias dados={dados} agir={agir} />
        )}
      </div>
    </div>
  );
}

// ==========================================================================

function Metrica({ rotulo, valor, nota }: { rotulo: string; valor: string | number; nota?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {rotulo}
      </p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums text-foreground">{valor}</p>
      {nota && <p className="mt-0.5 text-xs text-muted-foreground">{nota}</p>}
    </div>
  );
}

function SemDados({ texto }: { texto: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-card px-5 py-10 text-center">
      <p className="text-sm text-muted-foreground">{texto}</p>
    </div>
  );
}

function Hoje({
  dados,
  agir,
  ocupado,
  recarregar,
}: {
  dados: any;
  agir: (c: Record<string, unknown>) => void;
  ocupado: string;
  recarregar: () => void;
}) {
  const [gerando, setGerando] = useState(false);
  const publicacao: Publicacao | null = dados?.briefing?.briefing ?? null;
  const spec: Spec = publicacao?.payload ?? {};
  const findings: Finding[] = dados?.findings?.findings ?? [];
  const recomendacoes: Recomendacao[] = dados?.recomendacoes?.recomendacoes ?? [];
  const recPorFinding = new Map<string, Recomendacao>();
  for (const r of recomendacoes) {
    const fid = (r as any).finding_id;
    if (fid) recPorFinding.set(String(fid), r);
  }

  const criticos = findings.filter((f) => Number(f.priority_score || 0) >= 85).length;

  async function gerar() {
    setGerando(true);
    await fetch('/api/dashboard/briefing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acao: 'gerar', tipo: 'hoje' }),
    });
    setGerando(false);
    recarregar();
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metrica rotulo="Esperando você" valor={findings.length} />
        <Metrica rotulo="Crítico" valor={criticos} nota={criticos ? 'olhe primeiro' : 'nada urgente'} />
        <Metrica rotulo="Com ação disponível" valor={recomendacoes.length} />
      </div>

      {publicacao ? (
        <section className="rounded-xl border border-border bg-card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Resumo do dia
          </p>
          <h2 className="mt-1.5 text-lg font-semibold text-foreground">
            {publicacao.headline || spec.headline}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {publicacao.summary_text || spec.executive_summary}
          </p>
          <p className="mt-3 text-[11px] text-muted-foreground">
            Publicado em {dataCurta(publicacao.published_at)} · período{' '}
            {dataCurta(publicacao.period_start)} a {dataCurta(publicacao.period_end)}
          </p>
        </section>
      ) : (
        <section className="rounded-xl border border-dashed border-border bg-card p-5 text-center">
          <p className="text-sm text-muted-foreground">
            Ainda não há briefing publicado para hoje.
          </p>
          <button
            onClick={gerar}
            disabled={gerando}
            className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {gerando ? 'Montando…' : 'Montar agora'}
          </button>
        </section>
      )}

      {findings.length === 0 ? (
        <SemDados texto="Nada precisa de você agora. Quando algo mudar, aparece aqui." />
      ) : (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-foreground">Precisa de você</h2>
          {findings.map((f) => (
            <CartaoDeFinding
              key={f.id}
              finding={f}
              recomendacao={recPorFinding.get(String(f.id))}
              agir={agir}
              ocupado={ocupado}
            />
          ))}
        </section>
      )}

      {(spec.missing_data?.length ?? 0) > 0 && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground">O que ainda não dá para afirmar</h2>
          <ul className="mt-2 space-y-1.5">
            {(spec.missing_data || []).map((m, i) => (
              <li key={i} className="text-sm text-muted-foreground">
                • {m}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function CartaoDeFinding({
  finding,
  recomendacao,
  agir,
  ocupado,
}: {
  finding: Finding;
  recomendacao?: Recomendacao;
  agir: (c: Record<string, unknown>) => void;
  ocupado: string;
}) {
  const [aberto, setAberto] = useState(false);
  const faixa = faixaDePrioridade(finding.priority_score);
  const ocupadoAqui = ocupado === finding.id || ocupado === recomendacao?.id;

  return (
    <article className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-start gap-4 px-5 py-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${faixa.classe}`}>
              {faixa.rotulo}
            </span>
            {finding.confidence != null && (
              <span className="text-[11px] text-muted-foreground">
                confiança {Math.round(Number(finding.confidence) * 100)}%
              </span>
            )}
          </div>
          <h3 className="mt-1.5 text-sm font-semibold text-foreground">{finding.title}</h3>
          <p className="mt-0.5 text-sm text-muted-foreground">{finding.summary}</p>

          {/* O FATO vem antes, e separado. §13 — inferência nunca se apresenta
              como fato, e é por isso que os dois têm rótulos diferentes. */}
          {finding.fact_statement && (
            <p className="mt-2 text-xs text-foreground">
              <span className="font-semibold">Fato:</span> {finding.fact_statement}
            </p>
          )}
          {aberto && (
            <div className="mt-2 space-y-1.5 border-l-2 border-border pl-3">
              {finding.why_now && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">Por que agora:</span>{' '}
                  {finding.why_now}
                </p>
              )}
              {finding.inference_statement && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">Leitura (não confirmada):</span>{' '}
                  {finding.inference_statement}
                </p>
              )}
              {finding.missing_data && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">O que não se sabe:</span>{' '}
                  {finding.missing_data}
                </p>
              )}
              {finding.next_step && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">Próximo passo:</span>{' '}
                  {finding.next_step}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-border bg-secondary/30 px-5 py-3">
        <button
          onClick={() => setAberto((v) => !v)}
          className="rounded-lg border border-border px-3 py-1.5 text-xs text-foreground hover:bg-secondary"
        >
          {aberto ? 'Fechar' : 'Por que estou vendo isso?'}
        </button>
        {recomendacao && (
          <button
            disabled={ocupadoAqui}
            onClick={() =>
              agir({ acao: 'responder_recomendacao', id: recomendacao.id, resposta: 'accept' })
            }
            className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-60"
          >
            {recomendacao.action_options?.find((o) => o.key === recomendacao.recommended_action_key)
              ?.label || 'Resolver'}
          </button>
        )}
        <button
          disabled={ocupadoAqui}
          onClick={() => agir({ acao: 'responder_finding', id: finding.id, resposta: 'snooze', dias: 1 })}
          className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary disabled:opacity-60"
        >
          Me lembre amanhã
        </button>
        <button
          disabled={ocupadoAqui}
          onClick={() => agir({ acao: 'responder_finding', id: finding.id, resposta: 'dismiss' })}
          className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary disabled:opacity-60"
        >
          Dispensar
        </button>
        {recomendacao?.approval_required && (
          <span className="ml-auto text-[11px] text-amber-600 dark:text-amber-400">
            Esta ação precisa da sua aprovação antes de rodar
          </span>
        )}
      </div>
    </article>
  );
}

function Semana({ dados, recarregar }: { dados: any; recarregar: () => void }) {
  const [gerando, setGerando] = useState(false);
  const publicacao: Publicacao | null = dados?.briefing?.briefing ?? null;
  const spec: Spec = publicacao?.payload ?? {};

  async function gerar() {
    setGerando(true);
    await fetch('/api/dashboard/briefing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acao: 'gerar', tipo: 'semana' }),
    });
    setGerando(false);
    recarregar();
  }

  if (!publicacao) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">
          O briefing executivo desta semana ainda não foi publicado.
        </p>
        <button
          onClick={gerar}
          disabled={gerando}
          className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
        >
          {gerando ? 'Montando…' : 'Montar agora'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-border bg-card p-5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {dataCurta(publicacao.period_start)} a {dataCurta(publicacao.period_end)}
        </p>
        <h2 className="mt-1.5 text-lg font-semibold text-foreground">
          {publicacao.headline || spec.headline}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {publicacao.summary_text || spec.executive_summary}
        </p>
      </section>

      {(spec.sections || [])
        .filter((s) => (s.items || []).length > 0)
        .map((s) => (
          <section key={s.key} className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="border-b border-border px-5 py-3">
              <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
            </div>
            <ul className="divide-y divide-border">
              {s.items.map((i, idx) => (
                <li key={idx} className="px-5 py-3">
                  <p className="text-sm text-foreground">{i.headline}</p>
                  {i.summary && <p className="mt-0.5 text-xs text-muted-foreground">{i.summary}</p>}
                  {i.evidence_summary && (
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      <span className="font-semibold">Fato:</span> {i.evidence_summary}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}

      {(spec.missing_data?.length ?? 0) > 0 && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">
            O que ainda não dá para afirmar
          </h3>
          <ul className="mt-2 space-y-1.5">
            {(spec.missing_data || []).map((m, i) => (
              <li key={i} className="text-sm text-muted-foreground">
                • {m}
              </li>
            ))}
          </ul>
        </section>
      )}

      {spec.methodology && (
        <p className="text-[11px] text-muted-foreground">{spec.methodology}</p>
      )}
    </div>
  );
}

function Oportunidades({
  dados,
  agir,
  ocupado,
}: {
  dados: any;
  agir: (c: Record<string, unknown>) => void;
  ocupado: string;
}) {
  const recomendacoes: Recomendacao[] = dados?.recomendacoes?.recomendacoes ?? [];
  if (!recomendacoes.length) {
    return (
      <SemDados texto="Nenhuma oportunidade aberta. Elas aparecem quando o sistema encontra algo que dá para melhorar com evidência." />
    );
  }
  return (
    <div className="space-y-3">
      {recomendacoes.map((r) => {
        const faixa = faixaDePrioridade(r.priority_score);
        const principal = r.action_options?.find((o) => o.key === r.recommended_action_key);
        const indisponivel = r.action_options?.find((o) => o.key === 'indisponivel');
        return (
          <article key={r.id} className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="px-5 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${faixa.classe}`}>
                  {faixa.rotulo}
                </span>
                {r.confidence != null && (
                  <span className="text-[11px] text-muted-foreground">
                    confiança {Math.round(Number(r.confidence) * 100)}%
                  </span>
                )}
                {r.expires_at && (
                  <span className="text-[11px] text-muted-foreground">
                    relevante até {dataCurta(r.expires_at)}
                  </span>
                )}
              </div>
              <h3 className="mt-1.5 text-sm font-semibold text-foreground">{r.title}</h3>
              <p className="mt-0.5 text-sm text-muted-foreground">{r.summary}</p>
              {r.rationale && (
                <pre className="mt-2 whitespace-pre-wrap border-l-2 border-border pl-3 font-sans text-xs text-muted-foreground">
                  {r.rationale}
                </pre>
              )}
              {indisponivel && (
                <p className="mt-2 rounded-lg bg-secondary px-3 py-2 text-xs text-muted-foreground">
                  {indisponivel.label}
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2 border-t border-border bg-secondary/30 px-5 py-3">
              {principal && (
                <button
                  disabled={ocupado === r.id}
                  onClick={() => agir({ acao: 'responder_recomendacao', id: r.id, resposta: 'accept' })}
                  className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-60"
                >
                  {principal.label}
                </button>
              )}
              <button
                disabled={ocupado === r.id}
                onClick={() =>
                  agir({ acao: 'responder_recomendacao', id: r.id, resposta: 'snooze', dias: 7 })
                }
                className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary disabled:opacity-60"
              >
                Depois
              </button>
              <button
                disabled={ocupado === r.id}
                onClick={() =>
                  agir({ acao: 'responder_recomendacao', id: r.id, resposta: 'not_relevant' })
                }
                className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary disabled:opacity-60"
              >
                Não é relevante
              </button>
              <button
                disabled={ocupado === r.id}
                onClick={() =>
                  agir({ acao: 'responder_recomendacao', id: r.id, resposta: 'wrong_data' })
                }
                className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary disabled:opacity-60"
              >
                O número está errado
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function Historico({ dados }: { dados: any }) {
  const briefings: Publicacao[] = dados?.briefings?.briefings ?? [];
  const outcomes: any[] = dados?.outcomes?.outcomes ?? [];

  const rotuloDeOutcome: Record<string, string> = {
    realized: 'Resolveu',
    partially_realized: 'Melhorou em parte',
    inconclusive: 'Inconclusivo',
    negative: 'Não ajudou',
    pending: 'Aguardando janela',
    in_progress: 'Medindo',
    expired: 'Expirou',
  };

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Briefings publicados</h2>
        </div>
        {briefings.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhum briefing publicado ainda.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {briefings.map((b) => (
              <li key={b.id} className="flex items-center gap-4 px-5 py-3">
                <span className="w-24 flex-none text-xs text-muted-foreground">
                  {dataCurta(b.period_start)}
                </span>
                <p className="min-w-0 flex-1 truncate text-sm text-foreground">{b.headline}</p>
                <span className="flex-none text-[11px] text-muted-foreground">
                  {b.item_count ?? 0} item(ns)
                  {b.critical_count ? ` · ${b.critical_count} crítico(s)` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Resultados medidos</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            O que foi feito e o que mudou depois. Sem medição, o resultado aparece como
            inconclusivo — nunca como sucesso.
          </p>
        </div>
        {outcomes.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhuma medição fechada ainda.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {outcomes.map((o) => (
              <li key={o.id} className="px-5 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-foreground">
                    {rotuloDeOutcome[o.measurement_status] || o.measurement_status}
                  </span>
                  <span className="text-[11px] text-muted-foreground">{o.measurement_type}</span>
                  {o.automation_level === 'estimated' && (
                    <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground">
                      estimativa
                    </span>
                  )}
                  <span className="ml-auto text-[11px] text-muted-foreground">
                    {dataCurta(o.measured_at)}
                  </span>
                </div>
                {o.value_summary && (
                  <p className="mt-0.5 text-xs text-muted-foreground">{o.value_summary}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Preferencias({
  dados,
  agir,
}: {
  dados: any;
  agir: (c: Record<string, unknown>) => void;
}) {
  const perfil = dados?.perfil?.perfil ?? {};
  const [horario, setHorario] = useState<string>(perfil?.schedule_spec?.time || '08:00');
  const [detalhe, setDetalhe] = useState<string>(perfil?.detail_level || 'standard');
  const [maxPush, setMaxPush] = useState<number>(Number(perfil?.max_pushes_per_day ?? 3));
  const [ativo, setAtivo] = useState<boolean>(perfil?.is_active !== false);
  const [salvo, setSalvo] = useState(false);

  async function salvar() {
    await agir({
      acao: 'preferencias',
      cadencia: 'daily',
      campos: {
        schedule_spec: { time: horario },
        detail_level: detalhe,
        max_pushes_per_day: maxPush,
        is_active: ativo,
      },
    });
    setSalvo(true);
    setTimeout(() => setSalvo(false), 2500);
  }

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground">Como você quer receber</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Fora do horário combinado, só assunto crítico interrompe. O resto espera o próximo
          briefing.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-medium text-foreground">Horário do briefing diário</span>
            <input
              type="time"
              value={horario}
              onChange={(e) => setHorario(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
          </label>

          <label className="block">
            <span className="text-xs font-medium text-foreground">Nível de detalhe</span>
            <select
              value={detalhe}
              onChange={(e) => setDetalhe(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="minimal">Só o essencial</option>
              <option value="standard">Padrão</option>
              <option value="detailed">Detalhado</option>
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-medium text-foreground">
              Máximo de avisos por dia (fora do briefing)
            </span>
            <input
              type="number"
              min={0}
              max={20}
              value={maxPush}
              onChange={(e) => setMaxPush(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
          </label>

          <label className="flex items-center gap-2 self-end">
            <input
              type="checkbox"
              checked={ativo}
              onChange={(e) => setAtivo(e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-sm text-foreground">Briefing diário ligado</span>
          </label>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={salvar}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Salvar
          </button>
          {salvo && <span className="text-xs text-muted-foreground">Salvo.</span>}
        </div>

        <p className="mt-4 text-[11px] text-muted-foreground">
          Alerta de segurança e risco crítico continua chegando mesmo com o briefing pausado.
        </p>
      </section>
    </div>
  );
}
