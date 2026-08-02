'use client';

// SPEC-060 §30 — Pesquisas da corretora.
//
// A pesquisa NASCE no chat (§30.1). Esta tela é onde ela é reencontrada: o
// resultado, as fontes de cada afirmação e os acompanhamentos ativos.
//
// Duas decisões vindas da SPEC, não do gosto:
//
// 1. Cada afirmação mostra a FONTE ao lado (§16.6). Citação agrupada no fim
//    não deixa conferir nada — e conferir é o ponto de ter fonte.
// 2. As limitações ficam visíveis, não escondidas num rodapé. O que a
//    pesquisa NÃO afirma é tão importante quanto o que ela afirma.

import { useCallback, useEffect, useState } from 'react';

type Pesquisa = {
  id: string;
  mode: string;
  question: string;
  status: string;
  result_summary?: string | null;
  limitations?: string | null;
  created_at: string;
};

type Citacao = {
  source_trust_tier: number;
  source_official: boolean;
  source_excerpt?: string | null;
  citation_role: string;
};

type Claim = {
  id: string;
  claim_text: string;
  claim_type: string;
  status: string;
  confidence: number;
  risk_level: string;
  citation_count: number;
  official_citation_count: number;
  citacoes?: Citacao[];
};

type Monitor = {
  id: string;
  name: string;
  monitor_type: string;
  cadence: string;
  is_active: boolean;
  health: string;
  health_reason?: string | null;
  last_run_at?: string | null;
  last_change_at?: string | null;
  url_filters?: string[];
};

const ABAS = [
  { id: 'recentes', rotulo: 'Minhas pesquisas' },
  { id: 'monitores', rotulo: 'O que estou acompanhando' },
] as const;

const ROTULO_DE_MODO: Record<string, string> = {
  quick: 'rápida',
  verified: 'verificada',
  deep: 'profunda',
  site_audit: 'análise de site',
  business_discovery: 'busca de empresas',
  monitor: 'acompanhamento',
  claim_check: 'verificação',
};

const ROTULO_DE_STATUS: Record<string, string> = {
  completed: 'concluída',
  partial: 'parcial',
  running: 'em andamento',
  planning: 'planejando',
  blocked: 'bloqueada',
  failed: 'falhou',
  cancelled: 'cancelada',
};

function dataCurta(v?: string | null) {
  if (!v) return '—';
  try {
    return new Date(v).toLocaleDateString('pt-BR');
  } catch {
    return '—';
  }
}

function rotuloDeFonte(tier: number, oficial: boolean): string {
  if (oficial) return 'fonte oficial';
  return (
    {
      0: 'fonte oficial',
      1: 'fonte da própria empresa',
      2: 'fonte especializada',
      3: 'imprensa',
      4: 'relato de comunidade',
      5: 'não verificada',
    }[tier] || 'fonte'
  );
}

export default function PesquisasPage() {
  const [aba, setAba] = useState<string>('recentes');
  const [dados, setDados] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [aberta, setAberta] = useState<string | null>(null);
  const [detalhe, setDetalhe] = useState<any>(null);
  const [pergunta, setPergunta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState('');

  const carregar = useCallback(async (qual: string) => {
    setCarregando(true);
    setErro('');
    try {
      const j = await fetch(`/api/dashboard/pesquisas?aba=${qual}`).then((r) => r.json());
      if (j?.ok === false) setErro(j.error || 'Não foi possível carregar.');
      setDados(j);
    } catch {
      setErro('Não foi possível carregar suas pesquisas.');
    }
    setCarregando(false);
  }, []);

  useEffect(() => {
    carregar(aba);
  }, [aba, carregar]);

  const abrir = useCallback(async (id: string) => {
    if (aberta === id) {
      setAberta(null);
      setDetalhe(null);
      return;
    }
    setAberta(id);
    setDetalhe(null);
    try {
      const j = await fetch(`/api/dashboard/pesquisas?id=${encodeURIComponent(id)}`).then((r) =>
        r.json(),
      );
      setDetalhe(j);
    } catch {
      setDetalhe({ ok: false });
    }
  }, [aberta]);

  async function pesquisar() {
    if (pergunta.trim().length < 8) {
      setAviso('Escreva a pergunta com um pouco mais de detalhe.');
      return;
    }
    setEnviando(true);
    setAviso('');
    try {
      const j = await fetch('/api/dashboard/pesquisas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acao: 'pesquisar', pergunta }),
      }).then((r) => r.json());
      setAviso(
        j?.mensagem ||
          (j?.ok
            ? 'Pesquisa concluída — veja abaixo.'
            : 'Não consegui pesquisar agora.'),
      );
      setPergunta('');
      await carregar('recentes');
      setAba('recentes');
    } catch {
      setAviso('Não consegui pesquisar agora.');
    }
    setEnviando(false);
  }

  async function agir(corpo: Record<string, unknown>) {
    await fetch('/api/dashboard/pesquisas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    });
    await carregar(aba);
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 sm:px-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Pesquisas</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            O que o AutoBrokers foi conferir na internet para você, com a fonte de cada
            afirmação e a data em que ela foi lida. Você também pode pedir uma pesquisa
            direto no chat.
          </p>
        </header>

        <section className="rounded-xl border border-border bg-card p-4">
          <label className="text-xs font-medium text-foreground">
            Perguntar agora
          </label>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              value={pergunta}
              onChange={(e) => setPergunta(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !enviando) pesquisar();
              }}
              placeholder="Ex.: o que mudou nas regras da SUSEP para seguro residencial?"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
            <button
              onClick={pesquisar}
              disabled={enviando}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
            >
              {enviando ? 'Pesquisando…' : 'Pesquisar'}
            </button>
          </div>
          {aviso && <p className="mt-2 text-xs text-muted-foreground">{aviso}</p>}
        </section>

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
        ) : aba === 'recentes' ? (
          <ListaDePesquisas
            pesquisas={dados?.pesquisas ?? []}
            aberta={aberta}
            detalhe={detalhe}
            abrir={abrir}
          />
        ) : (
          <ListaDeMonitores monitores={dados?.monitores ?? []} agir={agir} />
        )}
      </div>
    </div>
  );
}

// ==========================================================================

function ListaDePesquisas({
  pesquisas,
  aberta,
  detalhe,
  abrir,
}: {
  pesquisas: Pesquisa[];
  aberta: string | null;
  detalhe: any;
  abrir: (id: string) => void;
}) {
  if (!pesquisas.length) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card px-5 py-10 text-center">
        <p className="text-sm text-muted-foreground">
          Nenhuma pesquisa ainda. Pergunte acima, ou peça no chat — “pesquise o que
          mudou na SUSEP”.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {pesquisas.map((p) => (
        <article key={p.id} className="overflow-hidden rounded-xl border border-border bg-card">
          <button
            onClick={() => abrir(p.id)}
            className="w-full px-5 py-4 text-left transition hover:bg-secondary/40"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-border bg-secondary px-2.5 py-0.5 text-[11px] text-foreground">
                {ROTULO_DE_MODO[p.mode] || p.mode}
              </span>
              <span
                className={`text-[11px] ${
                  p.status === 'blocked'
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-muted-foreground'
                }`}
              >
                {ROTULO_DE_STATUS[p.status] || p.status}
              </span>
              <span className="ml-auto text-[11px] text-muted-foreground">
                {dataCurta(p.created_at)}
              </span>
            </div>
            <h3 className="mt-1.5 text-sm font-semibold text-foreground">{p.question}</h3>
            {p.result_summary && (
              <p className="mt-0.5 text-sm text-muted-foreground">{p.result_summary}</p>
            )}
          </button>

          {aberta === p.id && (
            <div className="border-t border-border bg-secondary/20 px-5 py-4">
              {!detalhe ? (
                <p className="text-sm text-muted-foreground">Carregando as fontes…</p>
              ) : (
                <Detalhe detalhe={detalhe} limitacoesDoPedido={p.limitations} />
              )}
            </div>
          )}
        </article>
      ))}
    </div>
  );
}

function Detalhe({
  detalhe,
  limitacoesDoPedido,
}: {
  detalhe: any;
  limitacoesDoPedido?: string | null;
}) {
  const claims: Claim[] = detalhe?.detalhe?.claims ?? [];
  const cobertura = detalhe?.detalhe?.cobertura_de_citacao;
  const fontes: any[] = detalhe?.fontes?.fontes ?? [];
  const sustentados = claims.filter(
    (c) => c.status === 'supported' || c.status === 'partially_supported',
  );

  return (
    <div className="space-y-4">
      {cobertura != null && (
        <p className="text-[11px] text-muted-foreground">
          {cobertura}% das afirmações têm pelo menos uma fonte anexada.
        </p>
      )}

      {sustentados.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhuma afirmação pôde ser sustentada com fonte. Isso não significa que a
          resposta não exista — significa que não a encontramos com procedência.
        </p>
      ) : (
        <ul className="space-y-3">
          {sustentados.map((c) => (
            <li key={c.id} className="border-l-2 border-border pl-3">
              <p className="text-sm text-foreground">{c.claim_text}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                {c.official_citation_count > 0 ? (
                  <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-emerald-700 dark:text-emerald-400">
                    fonte oficial
                  </span>
                ) : (
                  <span>{c.citation_count} fonte(s)</span>
                )}
                <span>confiança {Math.round(Number(c.confidence || 0) * 100)}%</span>
                {c.status === 'partially_supported' && <span>sustentação parcial</span>}
                {(c.risk_level === 'high' || c.risk_level === 'critical') && (
                  <span className="text-amber-600 dark:text-amber-400">assunto sensível</span>
                )}
              </div>
              {(c.citacoes || []).slice(0, 2).map((cit, i) => (
                <p key={i} className="mt-1 text-[11px] italic text-muted-foreground">
                  {rotuloDeFonte(cit.source_trust_tier, cit.source_official)}
                  {cit.source_excerpt ? `: “${cit.source_excerpt.slice(0, 180)}…”` : ''}
                </p>
              ))}
            </li>
          ))}
        </ul>
      )}

      {fontes.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-foreground">Fontes lidas</p>
          <ul className="mt-1 space-y-1">
            {fontes.slice(0, 8).map((f) => (
              <li key={f.id} className="text-[11px] text-muted-foreground">
                • lida em {dataCurta(f.retrieved_at)} · {f.word_count || 0} palavras
                {f.prompt_injection_status === 'quarentena' && (
                  <span className="ml-1 text-destructive">
                    (colocada em quarentena por tentativa de manipulação)
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {limitacoesDoPedido && (
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-xs font-semibold text-foreground">O que esta pesquisa não afirma</p>
          <p className="mt-1 whitespace-pre-line text-[11px] text-muted-foreground">
            {limitacoesDoPedido}
          </p>
        </div>
      )}
    </div>
  );
}

function ListaDeMonitores({
  monitores,
  agir,
}: {
  monitores: Monitor[];
  agir: (c: Record<string, unknown>) => void;
}) {
  if (!monitores.length) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card px-5 py-10 text-center">
        <p className="text-sm text-muted-foreground">
          Você ainda não acompanha nenhuma fonte. Peça no chat: “monitore a página de
          circulares da SUSEP e me avise quando mudar”.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {monitores.map((m) => (
        <article key={m.id} className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] ${
                  !m.is_active
                    ? 'bg-secondary text-muted-foreground'
                    : m.health === 'ok'
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
                      : m.health === 'unknown'
                        ? 'bg-secondary text-muted-foreground'
                        : 'bg-destructive/15 text-destructive'
                }`}
              >
                {!m.is_active
                  ? 'pausado'
                  : m.health === 'ok'
                    ? 'funcionando'
                    : m.health === 'unknown'
                      ? 'ainda não rodou'
                      : 'com problema'}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {m.cadence === 'daily'
                  ? 'todo dia'
                  : m.cadence === 'hourly'
                    ? 'a cada hora'
                    : m.cadence === 'weekly'
                      ? 'toda semana'
                      : 'todo mês'}
              </span>
              <span className="ml-auto text-[11px] text-muted-foreground">
                última verificação {dataCurta(m.last_run_at)}
              </span>
            </div>
            <h3 className="mt-1.5 text-sm font-semibold text-foreground">{m.name}</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {(m.url_filters || []).length} endereço(s) acompanhado(s)
              {m.last_change_at ? ` · última mudança em ${dataCurta(m.last_change_at)}` : ''}
            </p>
            {m.health_reason && (
              <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-400">
                {m.health_reason}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2 border-t border-border bg-secondary/30 px-5 py-3">
            <button
              onClick={() => agir({ acao: 'monitor_agora', id: m.id })}
              className="rounded-lg border border-border px-3 py-1.5 text-xs text-foreground hover:bg-secondary"
            >
              Verificar agora
            </button>
            <button
              onClick={() => agir({ acao: 'monitor_pausar', id: m.id, ativo: !m.is_active })}
              className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary"
            >
              {m.is_active ? 'Pausar' : 'Reativar'}
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
