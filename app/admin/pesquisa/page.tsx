'use client';

// SPEC-060 §31 — o que buscamos na internet.
//
// A tela responde quatro perguntas de quem opera a plataforma:
//   1. Os provedores estão funcionando, e o que já custaram?
//   2. Quais fontes conhecemos, e com que autoridade?
//   3. Os monitores estão avisando de verdade — ou só fazendo barulho?
//   4. O conteúdo da web tentou nos manipular?
//
// Escala (CA-014): cada aba abre por AGREGADO. Lista só aparece
// depois, e sempre ordenada por relevância — nunca por ordem de chegada.

import { useCallback, useEffect, useState } from 'react';

const ABAS = [
  { id: 'visao', rotulo: 'Como está funcionando' },
  { id: 'fontes', rotulo: 'Fontes que conhecemos' },
  { id: 'monitores', rotulo: 'Monitores e ruído' },
  { id: 'custos', rotulo: 'Custo e segurança' },
] as const;

const ROTULO_DE_TIER: Record<number, string> = {
  0: 'oficial',
  1: 'primária',
  2: 'especializada',
  3: 'imprensa',
  4: 'comunidade',
  5: 'não verificada',
};

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

export default function PesquisaAdminPage() {
  const [aba, setAba] = useState<string>('visao');
  const [dados, setDados] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (qual: string) => {
    setCarregando(true);
    setErro('');
    try {
      const j = await fetch(`/api/admin/research?aba=${qual}`).then((r) => r.json());
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

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 sm:px-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            O que buscamos na internet
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Provedores, fontes conhecidas, monitores e o custo de tudo isso. Nenhuma
            pergunta de corretora aparece aqui — só o agregado da operação.
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
        ) : aba === 'fontes' ? (
          <Fontes dados={dados} recarregar={() => carregar('fontes')} />
        ) : aba === 'monitores' ? (
          <Monitores dados={dados} />
        ) : (
          <Custos dados={dados} />
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
  const providers: any[] = dados?.providers?.providers ?? [];
  const indisponiveis = providers.filter((p) => !p.disponivel);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Metrica rotulo="Pesquisas (30d)" valor={o.pesquisas ?? 0} />
        <Metrica
          rotulo="Bloqueadas"
          valor={o.bloqueadas ?? 0}
          alerta={Number(o.bloqueadas || 0) > 0}
          nota={Number(o.bloqueadas || 0) > 0 ? 'sem crédito de provedor' : undefined}
        />
        <Metrica rotulo="Afirmações" valor={o.claims ?? 0} />
        <Metrica
          rotulo="Com fonte"
          valor={q.cobertura_de_citacao != null ? `${q.cobertura_de_citacao}%` : '—'}
        />
        <Metrica rotulo="Monitores" valor={o.monitores ?? 0} />
        <Metrica rotulo="Fontes conhecidas" valor={o.fontes ?? 0} />
      </div>

      {Number(q.criticos_sem_fonte_oficial || 0) > 0 && (
        <section className="rounded-xl border border-destructive/30 bg-destructive/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            {q.criticos_sem_fonte_oficial} afirmação(ões) de assunto sensível sem fonte
            oficial
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Elas NÃO foram apresentadas como confirmadas — o banco recusa. Mas o número
            indica que a pesquisa está esbarrando em assunto regulatório sem alcançar a
            fonte que ele exige. Vale conferir se as fontes oficiais estão acessíveis.
          </p>
        </section>
      )}

      {indisponiveis.length > 0 && (
        <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            {indisponiveis.length} provedor(es) indisponível(is)
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            A pesquisa continua funcionando com os que restam, e cada resultado declara
            o que não pôde ser lido. Nada falha em silêncio.
          </p>
          <ul className="mt-2 space-y-1">
            {indisponiveis.map((p) => (
              <li key={p.provider} className="text-xs text-muted-foreground">
                • <code>{p.provider}</code> — {p.motivo || 'indisponível'}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Provedores</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-5 py-3 font-semibold">Provedor</th>
                <th className="px-5 py-3 font-semibold">Estado</th>
                <th className="px-5 py-3 text-right font-semibold">Chamadas</th>
                <th className="px-5 py-3 text-right font-semibold">Erros</th>
                <th className="px-5 py-3 text-right font-semibold">Sem crédito</th>
                <th className="px-5 py-3 text-right font-semibold">Latência</th>
                <th className="px-5 py-3 font-semibold">Última</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.provider} className="border-b border-border last:border-0">
                  <td className="px-5 py-3">
                    <p className="font-medium text-foreground">{p.provider}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {(p.operacoes || []).join(', ')}
                    </p>
                  </td>
                  <td className="px-5 py-3 text-xs">
                    {p.disponivel ? (
                      <span className="text-emerald-600 dark:text-emerald-400">ativo</span>
                    ) : (
                      <span className="text-muted-foreground">{p.motivo || 'inativo'}</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-foreground">
                    {p.chamadas ?? 0}
                  </td>
                  <td
                    className={`px-5 py-3 text-right tabular-nums ${
                      Number(p.erros || 0) > 0 ? 'text-destructive' : 'text-muted-foreground'
                    }`}
                  >
                    {p.erros ?? 0}
                  </td>
                  <td
                    className={`px-5 py-3 text-right tabular-nums ${
                      Number(p.sem_credito || 0) > 0
                        ? 'font-semibold text-amber-600 dark:text-amber-400'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {p.sem_credito ?? 0}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-muted-foreground">
                    {p.latencia_media_ms != null ? `${p.latencia_media_ms}ms` : '—'}
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">
                    {dataCurta(p.ultima_chamada)}
                  </td>
                </tr>
              ))}
              {!providers.length && (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    Nenhum provedor registrado.
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

function Fontes({ dados, recarregar }: { dados: any; recarregar: () => void }) {
  const politicas: any[] = dados?.politicas ?? [];
  const fontes: any[] = dados?.fontes ?? [];
  const [semeando, setSemeando] = useState(false);

  async function semear() {
    setSemeando(true);
    await fetch('/api/admin/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acao: 'semear_fontes' }),
    });
    setSemeando(false);
    recarregar();
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Fontes com política declarada
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              O que cada fonte pode sustentar. Uma afirmação sobre cobertura ou norma só
              é aceita com fonte oficial — o banco recusa o contrário.
            </p>
          </div>
          <button
            onClick={semear}
            disabled={semeando}
            className="flex-none rounded-lg border border-border px-3 py-1.5 text-xs text-foreground hover:bg-secondary disabled:opacity-60"
          >
            {semeando ? 'Publicando…' : 'Publicar catálogo'}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-5 py-3 font-semibold">Fonte</th>
                <th className="px-5 py-3 font-semibold">Domínio</th>
                <th className="px-5 py-3 font-semibold">Autoridade</th>
                <th className="px-5 py-3 font-semibold">Categoria</th>
                <th className="px-5 py-3 font-semibold">Retenção</th>
              </tr>
            </thead>
            <tbody>
              {politicas.map((p) => (
                <tr key={p.id || p.policy_key} className="border-b border-border last:border-0">
                  <td className="px-5 py-3">
                    <p className="font-medium text-foreground">{p.name}</p>
                    {p.notes && (
                      <p className="max-w-md text-[10px] text-muted-foreground">{p.notes}</p>
                    )}
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">
                    <code>{p.domain_pattern}</code>
                  </td>
                  <td className="px-5 py-3 text-xs">
                    <span
                      className={
                        p.official
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-muted-foreground'
                      }
                    >
                      {ROTULO_DE_TIER[Number(p.trust_tier)] ?? p.trust_tier}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">{p.category}</td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">
                    {p.retention_class}
                  </td>
                </tr>
              ))}
              {!politicas.length && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    Catálogo ainda não publicado. Use o botão acima.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">Fontes já consultadas</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            As mais recentes. A identidade da fonte é global; a pesquisa que a consultou
            continua privada de cada corretora.
          </p>
        </div>
        {fontes.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-muted-foreground">
            Nenhuma fonte consultada ainda.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {fontes.slice(0, 40).map((f) => (
              <li key={f.id} className="flex items-center gap-4 px-5 py-2.5">
                <span className="w-24 flex-none text-[11px] text-muted-foreground">
                  {ROTULO_DE_TIER[Number(f.trust_tier)] ?? f.trust_tier}
                </span>
                <p className="min-w-0 flex-1 truncate text-sm text-foreground">
                  {f.title || f.canonical_url}
                </p>
                <span className="w-40 flex-none truncate text-[11px] text-muted-foreground">
                  {f.normalized_domain}
                </span>
                <span className="w-32 flex-none text-right text-[11px] text-muted-foreground">
                  {dataCurta(f.last_seen_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Monitores({ dados }: { dados: any }) {
  const monitores: any[] = dados?.monitores ?? [];
  const barulhentos = monitores.filter(
    (m) => m.ruido && Number(m.ruido.verificacoes || 0) >= 10 && Number(m.ruido.relevantes || 0) === 0,
  );
  const comProblema = monitores.filter((m) => m.health === 'error' || m.health === 'degraded');

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metrica rotulo="Monitores" valor={monitores.length} />
        <Metrica
          rotulo="Com problema"
          valor={comProblema.length}
          alerta={comProblema.length > 0}
          nota={comProblema.length ? 'fontes não estão sendo lidas' : undefined}
        />
        <Metrica
          rotulo="Nunca acharam nada"
          valor={barulhentos.length}
          nota="10+ verificações sem mudança relevante"
        />
      </div>

      {barulhentos.length > 0 && (
        <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            {barulhentos.length} monitor(es) verificando sem nunca encontrar nada
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Isso pode ser bom sinal (a fonte realmente não muda) ou defeito (o endereço
            errado, ou o filtro de termos apertado demais). Vale olhar antes de o
            corretor concluir que o acompanhamento não serve.
          </p>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-5 py-3 font-semibold">Monitor</th>
                <th className="px-5 py-3 font-semibold">Saúde</th>
                <th className="px-5 py-3 text-right font-semibold">Verificações</th>
                <th className="px-5 py-3 text-right font-semibold">Relevantes</th>
                <th className="px-5 py-3 text-right font-semibold">Silêncio</th>
                <th className="px-5 py-3 font-semibold">Última</th>
              </tr>
            </thead>
            <tbody>
              {monitores.map((m) => {
                const r = m.ruido || {};
                return (
                  <tr key={m.id} className="border-b border-border last:border-0">
                    <td className="px-5 py-3">
                      <p className="font-medium text-foreground">{m.name}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {m.monitor_type} · {m.cadence}
                        {!m.is_active && ' · pausado'}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-xs">
                      <span
                        className={
                          m.health === 'ok'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : m.health === 'unknown'
                              ? 'text-muted-foreground'
                              : 'text-destructive'
                        }
                      >
                        {m.health}
                      </span>
                      {m.health_reason && (
                        <p className="text-[10px] text-muted-foreground">{m.health_reason}</p>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-foreground">
                      {r.verificacoes ?? 0}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-foreground">
                      {r.relevantes ?? 0}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-muted-foreground">
                      {r.taxa_de_silencio != null ? `${r.taxa_de_silencio}%` : '—'}
                    </td>
                    <td className="px-5 py-3 text-xs text-muted-foreground">
                      {dataCurta(m.last_run_at)}
                    </td>
                  </tr>
                );
              })}
              {!monitores.length && (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-sm text-muted-foreground">
                    Nenhum monitor criado ainda.
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

function Custos({ dados }: { dados: any }) {
  const custos = dados?.custos ?? {};
  const seguranca = dados?.seguranca ?? {};
  const porCorretora: any[] = custos?.por_corretora ?? [];
  const padroes: Record<string, number> = seguranca?.padroes_detectados ?? {};

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground">Consumo por corretora</h2>
        <p className="mt-1 text-xs text-muted-foreground">{custos.observacao}</p>
        {porCorretora.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">
            Nenhum consumo registrado no período.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-border">
            {porCorretora.slice(0, 20).map((c) => (
              <li key={c.company_id} className="flex items-center gap-4 py-2.5">
                <code className="w-64 flex-none truncate text-[11px] text-muted-foreground">
                  {c.company_id}
                </code>
                <span className="flex-1 text-xs text-muted-foreground">
                  {c.chamadas} chamada(s) · {c.cache_hits} reaproveitada(s) do cache
                </span>
                <span className="flex-none text-sm font-semibold tabular-nums text-foreground">
                  {Number(c.unidades || 0).toFixed(1)}
                </span>
                <span className="w-24 flex-none text-right text-[10px] text-muted-foreground">
                  {c.tudo_estimado ? 'estimado' : 'medido'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground">
          Defesa contra manipulação de conteúdo
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">{seguranca.observacao}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Metrica rotulo="Páginas lidas" valor={seguranca.paginas_lidas ?? 0} />
          <Metrica rotulo="Suspeitas" valor={seguranca.suspeitas ?? 0} />
          <Metrica
            rotulo="Em quarentena"
            valor={seguranca.quarentenadas ?? 0}
            alerta={Number(seguranca.quarentenadas || 0) > 0}
            nota="não foram enviadas ao modelo"
          />
        </div>
        {Object.keys(padroes).length > 0 && (
          <ul className="mt-4 space-y-1">
            {Object.entries(padroes)
              .sort((a, b) => b[1] - a[1])
              .map(([nome, n]) => (
                <li key={nome} className="text-xs text-muted-foreground">
                  • <code>{nome}</code>: {n} ocorrência(s)
                </li>
              ))}
          </ul>
        )}
      </section>
    </div>
  );
}
