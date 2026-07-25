'use client';

// SPEC-057 — Identidade da corretora.
//
// A tela mostra de onde veio cada coisa. Um painel que só exibe a cor capturada
// pede confiança cega; um que mostra "extraído do seu logo, 98% de confiança"
// permite conferir e discordar — e é a diferença entre automação e mágica.

import { useCallback, useEffect, useMemo, useState } from 'react';

type Proc = {
  field_path: string;
  source_kind: string;
  source_detail: string | null;
  confidence: number;
  human_edited: boolean;
};
type Fonte = { kind: string; url: string | null; status: string; http_status: number | null; error: string | null };
type Asset = {
  id: string; kind: string; storage_ref: string; width: number | null; height: number | null;
  has_transparency: boolean | null; ink_colors: { hex: string; ink_share: number }[]; confidence: number;
};
type Perfil = Record<string, any>;

const ORIGEM: Record<string, { rotulo: string; tom: string }> = {
  logo_pixels: { rotulo: 'medido no seu logo', tom: 'text-emerald-500' },
  website: { rotulo: 'do seu site', tom: 'text-sky-500' },
  instagram: { rotulo: 'do Instagram', tom: 'text-fuchsia-500' },
  linkedin: { rotulo: 'do LinkedIn', tom: 'text-sky-400' },
  google_business: { rotulo: 'do Google', tom: 'text-amber-500' },
  facebook: { rotulo: 'do Facebook', tom: 'text-blue-500' },
  human: { rotulo: 'você editou', tom: 'text-primary' },
  default: { rotulo: 'padrão da casa', tom: 'text-muted-foreground' },
  inferred: { rotulo: 'deduzido', tom: 'text-muted-foreground' },
};

const ABAS = [
  { id: 'visual', rotulo: 'Identidade visual' },
  { id: 'sobre', rotulo: 'Sobre a corretora' },
  { id: 'presenca', rotulo: 'Contato e presença' },
  { id: 'origem', rotulo: 'Procedência' },
] as const;

const ESTILOS = [
  { id: 'aurora', nome: 'Aurora', desc: 'Claro e editorial. Respiro largo, título em serifa.', para: 'Executivo, pesquisa, peça para o cliente' },
  { id: 'obsidian', nome: 'Obsidian', desc: 'Escuro e luminoso. Painel de vidro, gráfico com brilho.', para: 'Briefing diário, leitura em tela' },
  { id: 'meridian', nome: 'Meridian', desc: 'Claro e preciso. Grade apertada, numeral tabular.', para: 'Financeiro, carteira, sinistros' },
] as const;

const campoCls =
  'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground ' +
  'outline-none transition focus:border-primary/60 focus:ring-2 focus:ring-primary/15';

export function BrandIdentityClient() {
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [proc, setProc] = useState<Record<string, Proc>>({});
  const [fontes, setFontes] = useState<Fonte[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [aba, setAba] = useState<string>('visual');
  const [rascunho, setRascunho] = useState<Perfil>({});
  const [capturando, setCapturando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const j = await fetch('/api/dashboard/brand-identity').then((r) => r.json());
      if (j?.ok) {
        setPerfil(j.profile ?? {});
        setRascunho(j.profile ?? {});
        setProc(j.provenance ?? {});
        setFontes(j.sources ?? []);
        setAssets(j.assets ?? []);
        setErro('');
      } else setErro(j?.error || 'Não foi possível carregar a identidade.');
    } catch {
      setErro('Não foi possível carregar a identidade.');
    }
    setCarregando(false);
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const capturar = async () => {
    setCapturando(true); setAviso(''); setErro('');
    try {
      const r = await fetch('/api/dashboard/brand-identity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const j = await r.json();
      if (j?.ok) {
        const n = (j.campos_propostos || []).length;
        setAviso(
          `Identidade montada: ${n} ${n === 1 ? 'campo preenchido' : 'campos preenchidos'}.` +
          (j.avisos?.length ? ` Atenção: ${j.avisos.join('; ')}` : ''),
        );
        await carregar();
      } else setErro(j?.error || 'A captura não encontrou o suficiente. Confira o endereço do site.');
    } catch {
      setErro('Falha ao falar com o serviço de identidade.');
    }
    setCapturando(false);
  };

  const salvar = async (campos: Perfil) => {
    setSalvando(true); setAviso(''); setErro('');
    try {
      const r = await fetch('/api/dashboard/brand-identity', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ values: campos }),
      });
      const j = await r.json();
      if (j?.ok) { setAviso('Salvo. Isto não será sobrescrito por uma nova captura.'); await carregar(); }
      else setErro(j?.error || 'Não foi possível salvar.');
    } catch {
      setErro('Não foi possível salvar.');
    }
    setSalvando(false);
  };

  const paleta = (perfil?.palette || {}) as any;
  const temMarca = Boolean(paleta?.primary);
  const completude = Math.round(Number(perfil?.completeness || 0) * 100);
  const logo = assets.find((a) => a.kind === 'logo_primary') || assets[0];

  const auditoria = useMemo(() => {
    const a = paleta?.audit;
    if (!a) return null;
    const todos = [...(a.light || []), ...(a.dark || [])];
    return { total: todos.length, ok: todos.filter((x: any) => x.passa).length };
  }, [paleta]);

  if (carregando) {
    return <div className="rounded-xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">Carregando identidade…</div>;
  }

  const semFonte = !perfil?.website_url && !perfil?.instagram_url && !perfil?.linkedin_url;

  return (
    <div className="space-y-5">
      {/* ---------- cabeçalho da marca ---------- */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div
          className="flex flex-wrap items-center gap-6 p-6"
          style={temMarca ? {
            background: `linear-gradient(115deg, ${paleta.primary}14, transparent 62%)`,
          } : undefined}
        >
          <div
            className="flex h-20 w-32 flex-none items-center justify-center rounded-xl border border-border bg-background p-3"
            style={temMarca ? { borderColor: `${paleta.primary}33` } : undefined}
          >
            {logo?.storage_ref ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={logo.storage_ref} alt="Logo da corretora" className="max-h-full max-w-full object-contain" />
            ) : (
              <span className="text-xs text-muted-foreground">sem logo</span>
            )}
          </div>

          <div className="min-w-[220px] flex-1">
            <h2 className="text-xl font-semibold text-foreground">
              {perfil?.display_name || 'Sua corretora'}
            </h2>
            {perfil?.tagline && <p className="mt-1 text-sm text-muted-foreground">{perfil.tagline}</p>}
            <div className="mt-3 flex items-center gap-3">
              <div className="h-1.5 w-40 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${completude}%`, background: paleta?.primary || 'hsl(var(--primary))' }}
                />
              </div>
              <span className="text-xs font-medium text-muted-foreground">{completude}% completa</span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <button
              onClick={capturar}
              disabled={capturando || semFonte}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
            >
              {capturando ? 'Lendo seu site…' : temMarca ? 'Atualizar do site' : 'Montar identidade'}
            </button>
            {auditoria && (
              <span className="text-[11px] text-muted-foreground">
                acessibilidade: {auditoria.ok}/{auditoria.total} conferidos
              </span>
            )}
          </div>
        </div>
      </div>

      {aviso && <p className="rounded-lg border border-primary/25 bg-primary/10 px-4 py-3 text-sm text-foreground">{aviso}</p>}
      {erro && <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground">{erro}</p>}

      {/* ---------- fontes declaradas ---------- */}
      <section className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-foreground">Onde procurar</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Só olhamos os endereços que você informar aqui. Nada mais.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[
            ['website_url', 'Site da corretora', 'https://suacorretora.com.br'],
            ['instagram_url', 'Instagram', 'https://instagram.com/suacorretora'],
            ['linkedin_url', 'LinkedIn', 'https://linkedin.com/company/suacorretora'],
            ['google_business_url', 'Google Meu Negócio', 'link do seu perfil'],
          ].map(([chave, rotulo, dica]) => (
            <label key={chave} className="block">
              <span className="text-xs font-medium text-foreground-2">{rotulo}</span>
              <input
                className={`mt-1 ${campoCls}`}
                placeholder={dica}
                value={rascunho[chave] ?? ''}
                onChange={(e) => setRascunho({ ...rascunho, [chave]: e.target.value })}
              />
            </label>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={() => salvar({
              website_url: rascunho.website_url || null,
              instagram_url: rascunho.instagram_url || null,
              linkedin_url: rascunho.linkedin_url || null,
              google_business_url: rascunho.google_business_url || null,
            })}
            disabled={salvando}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40"
          >
            {salvando ? 'Salvando…' : 'Salvar endereços'}
          </button>
          {semFonte && <span className="text-xs text-muted-foreground">Informe ao menos o site para montar a identidade.</span>}
        </div>

        {fontes.length > 0 && (
          <ul className="mt-4 grid gap-1.5 border-t border-border pt-4">
            {fontes.slice(0, 5).map((f, i) => (
              <li key={i} className="flex items-center gap-3 text-xs">
                <span className={
                  f.status === 'fetched' ? 'text-emerald-500'
                    : f.status === 'blocked' ? 'text-amber-500' : 'text-destructive'
                }>●</span>
                <span className="w-32 text-foreground-2">{f.kind}</span>
                <span className="text-muted-foreground">
                  {f.status === 'fetched' ? 'lido com sucesso' : (f.error || `falhou (${f.http_status ?? '—'})`)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ---------- abas ---------- */}
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

      {aba === 'visual' && (
        <AbaVisual
          perfil={perfil} rascunho={rascunho} setRascunho={setRascunho}
          paleta={paleta} proc={proc} logo={logo} salvar={salvar} salvando={salvando}
        />
      )}
      {aba === 'sobre' && (
        <AbaSobre rascunho={rascunho} setRascunho={setRascunho} proc={proc} salvar={salvar} salvando={salvando} />
      )}
      {aba === 'presenca' && <AbaPresenca perfil={perfil} />}
      {aba === 'origem' && <AbaOrigem proc={proc} />}
    </div>
  );
}

// ==========================================================================

function Origem({ proc, campo }: { proc: Record<string, Proc>; campo: string }) {
  const p = proc[campo];
  if (!p) return null;
  const o = ORIGEM[p.human_edited ? 'human' : p.source_kind] || ORIGEM.inferred;
  return (
    <span className={`text-[11px] ${o.tom}`} title={p.source_detail || ''}>
      {o.rotulo}
      {!p.human_edited && p.confidence < 0.95 && ` · ${Math.round(p.confidence * 100)}%`}
    </span>
  );
}

function AbaVisual({ perfil, rascunho, setRascunho, paleta, proc, logo, salvar, salvando }: any) {
  const escala = paleta?.scales?.primary || {};
  const tema = paleta?.themes?.light;
  const auditoria = paleta?.audit;
  const falhas = auditoria
    ? [...(auditoria.light || []), ...(auditoria.dark || [])].filter((x: any) => !x.passa)
    : [];

  if (!paleta?.primary) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center">
        <p className="text-sm text-muted-foreground">
          Informe o site acima e clique em <strong className="text-foreground">Montar identidade</strong>.
          As cores vêm do seu logo — é a fonte mais confiável que existe.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-foreground">Cores da marca</h3>
          <Origem proc={proc} campo="palette" />
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[['primary', 'Primária'], ['accent', 'Acento']].map(([chave, rotulo]) => (
            <div key={chave} className="flex items-center gap-3 rounded-lg border border-border p-3">
              <div className="h-12 w-12 flex-none rounded-lg border border-border" style={{ background: paleta[chave] }} />
              <div className="min-w-0">
                <p className="text-xs text-muted-foreground">{rotulo}</p>
                <p className="font-mono text-sm font-semibold text-foreground">{paleta[chave]}</p>
              </div>
              <input
                type="color"
                value={paleta[chave]}
                onChange={(e) => setRascunho({
                  ...rascunho,
                  palette: { ...(rascunho.palette || paleta), [chave]: e.target.value },
                })}
                className="ml-auto h-8 w-8 cursor-pointer rounded border border-border bg-transparent"
                aria-label={`Trocar cor ${rotulo}`}
              />
            </div>
          ))}
        </div>

        {logo?.ink_colors?.length > 0 && (
          <p className="mt-3 text-xs text-muted-foreground">
            Medido no seu logo: {logo.ink_colors.slice(0, 2).map((c: any) =>
              `${c.hex} (${Math.round(c.ink_share * 100)}% da tinta)`).join(' · ')}
            {logo.has_transparency && ' — fundo transparente ignorado no cálculo'}
          </p>
        )}

        <div className="mt-5">
          <p className="text-xs font-medium text-foreground-2">Escala derivada</p>
          <div className="mt-2 flex overflow-hidden rounded-lg border border-border">
            {Object.entries(escala).map(([passo, cor]) => (
              <div key={passo} className="group relative h-10 flex-1" style={{ background: cor as string }} title={`${passo} · ${cor}`} />
            ))}
          </div>
        </div>

        {tema && (
          <div className="mt-5">
            <p className="text-xs font-medium text-foreground-2">Séries de gráfico</p>
            <div className="mt-2 flex gap-1.5">
              {tema.chart.map((c: string, i: number) => (
                <div key={i} className="h-8 flex-1 rounded" style={{ background: c }} title={c} />
              ))}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              As séries variam em cor e em claridade — o gráfico continua legível impresso em preto e branco.
            </p>
          </div>
        )}

        <div className={`mt-5 rounded-lg border px-4 py-3 text-xs ${
          falhas.length ? 'border-amber-500/30 bg-amber-500/10' : 'border-emerald-500/25 bg-emerald-500/10'
        }`}>
          {falhas.length === 0 ? (
            <>
              <strong className="text-foreground">Contraste conferido.</strong>{' '}
              <span className="text-muted-foreground">
                Todo texto passa no mínimo de acessibilidade, nos temas claro e escuro. Quando a cor da
                marca não tem contraste suficiente, ajustamos só a claridade — o tom continua sendo o seu.
              </span>
            </>
          ) : (
            <>
              <strong className="text-foreground">{falhas.length} combinações abaixo do mínimo.</strong>{' '}
              <span className="text-muted-foreground">{falhas.map((f: any) => f.par).join(', ')}</span>
            </>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-foreground">Estilo das peças</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Define grade, ritmo e densidade. Cada relatório já vem com o estilo que combina com ele;
          aqui você escolhe o padrão da casa.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {ESTILOS.map((e) => {
            const ativo = (rascunho.visual_style || perfil?.visual_style || 'aurora') === e.id;
            return (
              <button
                key={e.id}
                onClick={() => setRascunho({ ...rascunho, visual_style: e.id })}
                className={`rounded-xl border p-4 text-left transition ${
                  ativo ? 'border-primary bg-primary/5' : 'border-border hover:border-border-strong'
                }`}
              >
                <div
                  className="mb-3 h-14 rounded-lg border border-border"
                  style={{
                    background: e.id === 'obsidian'
                      ? `linear-gradient(140deg, #0d1115, ${paleta.primary}55)`
                      : e.id === 'meridian'
                        ? `linear-gradient(140deg, #fff, ${paleta.primary}18)`
                        : `linear-gradient(140deg, ${paleta.primary}14, ${paleta.accent}14)`,
                  }}
                />
                <p className="text-sm font-semibold text-foreground">{e.nome}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">{e.desc}</p>
                <p className="mt-2 text-[11px] text-foreground-2">{e.para}</p>
              </button>
            );
          })}
        </div>
      </section>

      <div className="flex justify-end">
        <button
          onClick={() => salvar({
            palette: rascunho.palette || paleta,
            visual_style: rascunho.visual_style || perfil?.visual_style || 'aurora',
          })}
          disabled={salvando}
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
        >
          {salvando ? 'Salvando…' : 'Salvar identidade visual'}
        </button>
      </div>
    </div>
  );
}

function AbaSobre({ rascunho, setRascunho, proc, salvar, salvando }: any) {
  const campos: [string, string, string, boolean?][] = [
    ['display_name', 'Nome da corretora', 'Como sua corretora se apresenta', false],
    ['legal_name', 'Razão social', '', false],
    ['tagline', 'Frase de marca', 'Aparece na capa dos relatórios', false],
    ['susep_code', 'Código SUSEP', 'Aparece no rodapé das peças', false],
    ['service_area', 'Onde vocês atendem', 'Ex.: Florianópolis - SC', false],
    ['about_md', 'Sobre a corretora', 'O que vocês fazem, em poucas linhas', true],
    ['mission', 'Missão', '', true],
  ];
  const servicos: any[] = Array.isArray(rascunho.services) ? rascunho.services : [];

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-foreground">Quem é a corretora</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Tudo aqui é seu para editar. Depois que você mexe num campo, nenhuma captura o sobrescreve.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {campos.map(([chave, rotulo, dica, longo]) => (
            <label key={chave} className={longo ? 'sm:col-span-2' : ''}>
              <span className="flex items-baseline justify-between gap-2">
                <span className="text-xs font-medium text-foreground-2">{rotulo}</span>
                <Origem proc={proc} campo={chave} />
              </span>
              {longo ? (
                <textarea
                  rows={3}
                  className={`mt-1 ${campoCls} resize-y`}
                  placeholder={dica}
                  value={rascunho[chave] ?? ''}
                  onChange={(e) => setRascunho({ ...rascunho, [chave]: e.target.value })}
                />
              ) : (
                <input
                  className={`mt-1 ${campoCls}`}
                  placeholder={dica}
                  value={rascunho[chave] ?? ''}
                  onChange={(e) => setRascunho({ ...rascunho, [chave]: e.target.value })}
                />
              )}
            </label>
          ))}
        </div>
      </section>

      {servicos.length > 0 && (
        <section className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">Ramos que vocês trabalham</h3>
            <Origem proc={proc} campo="services" />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {servicos.map((s: any, i: number) => (
              <span key={i} className="rounded-full border border-border bg-secondary px-3 py-1 text-xs text-foreground">
                {s?.name || String(s)}
              </span>
            ))}
          </div>
        </section>
      )}

      <div className="flex justify-end">
        <button
          onClick={() => salvar(Object.fromEntries(campos.map(([c]) => [c, rascunho[c] ?? null])))}
          disabled={salvando}
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
        >
          {salvando ? 'Salvando…' : 'Salvar'}
        </button>
      </div>
    </div>
  );
}

function AbaPresenca({ perfil }: any) {
  const c = perfil?.contact || {};
  const redes = [
    ['Site', perfil?.website_url], ['Instagram', perfil?.instagram_url],
    ['LinkedIn', perfil?.linkedin_url], ['Facebook', perfil?.facebook_url],
    ['Google Meu Negócio', perfil?.google_business_url],
  ].filter(([, v]) => v);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <section className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-foreground">Contato encontrado</h3>
        <dl className="mt-3 space-y-2 text-sm">
          {(c.phones || []).map((t: string, i: number) => (
            <div key={i} className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Telefone</dt>
              <dd className="text-foreground">{t}</dd>
            </div>
          ))}
          {(c.emails || []).map((e: string, i: number) => (
            <div key={i} className="flex justify-between gap-3">
              <dt className="text-muted-foreground">E-mail</dt>
              <dd className="truncate text-foreground">{e}</dd>
            </div>
          ))}
          {!(c.phones || []).length && !(c.emails || []).length && (
            <p className="text-xs text-muted-foreground">Nada encontrado ainda.</p>
          )}
        </dl>
      </section>

      <section className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-foreground">Presença</h3>
        <ul className="mt-3 space-y-2 text-sm">
          {redes.map(([r, u]) => (
            <li key={r as string} className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">{r}</span>
              <a href={u as string} target="_blank" rel="noopener noreferrer"
                 className="max-w-[60%] truncate text-primary hover:underline">
                {String(u).replace(/^https?:\/\//, '')}
              </a>
            </li>
          ))}
          {!redes.length && <p className="text-xs text-muted-foreground">Nenhum endereço informado.</p>}
        </ul>
      </section>
    </div>
  );
}

function AbaOrigem({ proc }: { proc: Record<string, Proc> }) {
  const linhas = Object.values(proc).sort((a, b) => a.field_path.localeCompare(b.field_path));
  if (!linhas.length) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center text-sm text-muted-foreground">
        Nada capturado ainda.
      </div>
    );
  }
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="border-b border-border px-5 py-4">
        <h3 className="text-sm font-semibold text-foreground">De onde veio cada informação</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Nada aqui foi inventado. Cada campo aponta a fonte e o quanto podemos confiar nela —
          para você conferir e discordar quando for o caso.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-5 py-3 font-semibold">Campo</th>
              <th className="px-5 py-3 font-semibold">Origem</th>
              <th className="px-5 py-3 font-semibold">Detalhe</th>
              <th className="px-5 py-3 text-right font-semibold">Confiança</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((p) => {
              const o = ORIGEM[p.human_edited ? 'human' : p.source_kind] || ORIGEM.inferred;
              return (
                <tr key={p.field_path} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 font-mono text-xs text-foreground">{p.field_path}</td>
                  <td className={`px-5 py-3 text-xs ${o.tom}`}>{o.rotulo}</td>
                  <td className="max-w-[280px] truncate px-5 py-3 text-xs text-muted-foreground" title={p.source_detail || ''}>
                    {p.source_detail || '—'}
                  </td>
                  <td className="px-5 py-3 text-right text-xs tabular-nums text-foreground">
                    {p.human_edited ? 'sua edição' : `${Math.round(p.confidence * 100)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
