'use client';

// SPEC-057 — Identidade da corretora.
// SPEC-098 · U1.2 / U1.4 / U2.4 — a tela diz a verdade, e o Jeito de atender existe.
//
// A tela mostra de onde veio cada coisa. Um painel que só exibe a cor capturada
// pede confiança cega; um que mostra "extraído do seu logo, 98% de confiança"
// permite conferir e discordar — e é a diferença entre automação e mágica.
//
// 🔴 O que a SPEC-098 consertou aqui, medido em 06/09/2026:
//
//  · `capture_status` tinha ZERO leitores em `.tsx`. Os cinco estados da
//    captura — nunca rodou, rodando, falhou, veio pela metade, você preencheu —
//    apareciam todos iguais. Uma captura que FALHOU exibia a paleta de reserva
//    como se fosse a marca da corretora: o produto afirmando uma coisa que não
//    aconteceu. Agora cada estado tem cara própria e o fracasso é vermelho.
//  · A fonte que não respondeu mostrava o número cru do erro da rede e o
//    nome interno da fonte
//    (`google_business`). Agora mostra o motivo em português e o que fazer.
//  · A procedência imprimia o caminho do campo no banco em fonte de código
//    (`about_md`, `display_name`). Nome de coluna não é linguagem de corretora.
//  · O contrato estava quebrado: o backend serializava `erro` e a tela lia
//    `error` — TODA falha virava a mesma frase genérica. Corrigido no backend;
//    aqui a faixa passa a mostrar o que de fato voltou.

import { useCallback, useEffect, useMemo, useState } from 'react';

type Proc = {
  field_path: string;
  source_kind: string;
  source_detail: string | null;
  confidence: number;
  human_edited: boolean;
};
type Fonte = {
  kind: string;
  url: string | null;
  status: string;
  http_status: number | null;
  error: string | null;
  error_humano?: string | null;
};
type Asset = {
  id: string; kind: string; storage_ref: string; width: number | null; height: number | null;
  has_transparency: boolean | null; ink_colors: { hex: string; ink_share: number }[]; confidence: number;
};
type Perfil = Record<string, any>;

type ItemDeLista = { texto: string; sinalizado?: boolean; confirmado?: boolean };
type Jeito = Record<string, any>;

const ORIGEM: Record<string, { rotulo: string; tom: string }> = {
  logo_pixels: { rotulo: 'medido no seu logo', tom: 'text-emerald-500' },
  website: { rotulo: 'do seu site', tom: 'text-sky-500' },
  leitura_do_site: { rotulo: 'lido no seu site', tom: 'text-sky-500' },
  conversas: { rotulo: 'aprendido das suas conversas', tom: 'text-violet-500' },
  instagram: { rotulo: 'do Instagram', tom: 'text-fuchsia-500' },
  linkedin: { rotulo: 'do LinkedIn', tom: 'text-sky-400' },
  google_business: { rotulo: 'do Google', tom: 'text-amber-500' },
  facebook: { rotulo: 'do Facebook', tom: 'text-blue-500' },
  colada: { rotulo: 'você colou', tom: 'text-primary' },
  human: { rotulo: 'você editou', tom: 'text-primary' },
  proposto: { rotulo: 'proposta ainda não aprovada', tom: 'text-amber-500' },
  default: { rotulo: 'padrão da casa', tom: 'text-muted-foreground' },
  inferred: { rotulo: 'deduzido', tom: 'text-muted-foreground' },
};

/**
 * 🔴 R10/R11 — o nome do endereço é o que o corretor chama, nunca a chave.
 * `google_business` é nome de coluna; "Google Meu Negócio" é onde ele mesmo
 * publica o horário da corretora.
 */
const FONTE_ROTULO: Record<string, string> = {
  website: 'Seu site',
  instagram: 'Instagram',
  linkedin: 'LinkedIn',
  facebook: 'Facebook',
  google_business: 'Google Meu Negócio',
  colada: 'Texto que você colou',
};

function rotuloDaFonte(kind: string): string {
  return FONTE_ROTULO[kind] || 'Outro endereço informado';
}

/**
 * O motivo em PORTUGUÊS de uma fonte que não respondeu.
 *
 * A frase certa vem do backend (`error_humano`, U1.2). Este mapa é a rede de
 * segurança para a linha antiga que ainda não passou pela captura nova — e ele
 * NUNCA imprime o número do erro: um código de rede não diz nada a um corretor, e
 * "a rede bloqueia a leitura automática" diz tudo, inclusive o que fazer.
 */
function motivoDaFonte(f: Fonte): string {
  if (f.status === 'fetched') return 'lido com sucesso';
  if (f.error_humano) return f.error_humano;
  if (f.http_status === 429 || f.status === 'blocked') {
    return 'a rede bloqueia a leitura automática — cole abaixo a descrição do perfil';
  }
  if (f.http_status === 402) return 'o serviço de leitura profunda está sem crédito; lemos o site diretamente';
  if (f.http_status === 404) return 'este endereço não existe mais';
  if (f.http_status === 403) return 'este endereço não deixa ler de fora';
  if (typeof f.http_status === 'number' && f.http_status >= 500) return 'o site estava fora do ar na hora da leitura';
  if (f.status === 'timeout') return 'o site demorou demais para responder';
  return 'não conseguimos ler este endereço';
}

/** Avisos da captura, em português. Código que sobrar vira frase, nunca chave. */
const AVISOS: Record<string, string> = {
  sem_logo: 'Não encontramos um logo no site — as cores ficaram com o padrão da casa.',
  logo_pequeno: 'O logo do site é pequeno; nas peças ele pode sair sem nitidez.',
  contraste_ajustado: 'A cor da marca precisou de um ajuste de claridade para o texto continuar legível.',
  sem_texto: 'O site respondeu, mas quase não havia texto para ler.',
  poucos_campos: 'O site trouxe pouca coisa. Vale conferir e completar à mão.',
  paleta_padrao: 'Usamos as cores padrão da casa até conseguirmos ler o seu logo.',
  sem_credito: 'A leitura profunda está sem crédito; lemos o site diretamente.',
};

function frasearAviso(a: string): string {
  if (AVISOS[a]) return AVISOS[a];
  // Um aviso que ainda é código não pode aparecer como código na tela.
  if (/^[A-Za-z0-9_.:-]+$/.test(a)) return 'Um detalhe da leitura ficou pendente — confira os campos abaixo.';
  return a;
}

/** O nome do campo em linguagem de corretora. Nunca o caminho no banco. */
const CAMPO_ROTULO: Record<string, string> = {
  display_name: 'Nome da corretora',
  legal_name: 'Razão social',
  tagline: 'Frase de marca',
  susep_code: 'Código SUSEP',
  service_area: 'Onde vocês atendem',
  about_md: 'Sobre a corretora',
  mission: 'Missão',
  services: 'Ramos que vocês trabalham',
  insurers: 'Seguradoras que vocês representam',
  differentiators: 'Diferenciais',
  founded_year: 'Desde',
  palette: 'Cores da marca',
  visual_style: 'Estilo das peças',
  logo: 'Logo',
  tone: 'Jeito de atender',
  contact: 'Contato',
  website_url: 'Site',
  instagram_url: 'Instagram',
  linkedin_url: 'LinkedIn',
  facebook_url: 'Facebook',
  google_business_url: 'Google Meu Negócio',
  bio_colada: 'Descrição que você colou',
};

function rotuloDoCampo(caminho: string): string {
  return CAMPO_ROTULO[caminho] || CAMPO_ROTULO[caminho.split('.')[0]] || 'Outro dado da identidade';
}

/**
 * 🔴 U1.2 — cada estado da captura com CARA PRÓPRIA.
 *
 * 📊 06/09/2026: os cinco estados eram indistinguíveis na tela, e o pior deles
 * — `failed` — era o mais parecido com sucesso, porque a paleta de reserva
 * aparecia como se fosse a marca.
 */
const ESTADOS: Record<
  string,
  { titulo: string; frase: string; anel: string; ponto: string }
> = {
  empty: {
    titulo: 'Ainda não montamos a identidade',
    frase: 'Informe o endereço do site abaixo e clique em Montar identidade.',
    anel: 'border-border bg-card',
    ponto: 'bg-muted-foreground',
  },
  capturing: {
    titulo: 'Lendo o seu site…',
    frase: 'Isto costuma levar menos de um minuto. Pode deixar a tela aberta.',
    anel: 'border-primary/40 bg-primary/5',
    ponto: 'bg-primary animate-pulse',
  },
  failed: {
    titulo: 'A leitura não foi adiante',
    frase: 'Nada foi preenchido a partir do site. Veja o motivo logo abaixo.',
    anel: 'border-destructive/45 bg-destructive/10',
    ponto: 'bg-destructive',
  },
  partial: {
    titulo: 'Identidade montada em parte',
    frase: 'O site respondeu, mas nem tudo foi encontrado. Complete o que faltou.',
    anel: 'border-amber-500/40 bg-amber-500/10',
    ponto: 'bg-amber-500',
  },
  captured: {
    titulo: 'Identidade montada a partir do seu site',
    frase: 'Confira o que veio. Tudo aqui é seu para corrigir.',
    anel: 'border-emerald-500/35 bg-emerald-500/10',
    ponto: 'bg-emerald-500',
  },
  manual: {
    titulo: 'Identidade preenchida por você',
    frase: 'Nada aqui foi capturado — foi você quem escreveu. Nenhuma captura sobrescreve.',
    anel: 'border-primary/35 bg-primary/5',
    ponto: 'bg-primary',
  },
};

const ABAS = [
  { id: 'visual', rotulo: 'Identidade visual' },
  { id: 'sobre', rotulo: 'Sobre a corretora' },
  { id: 'jeito', rotulo: 'Jeito de atender' },
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
  const [bruto, setBruto] = useState<any>(null);
  const [proc, setProc] = useState<Record<string, Proc>>({});
  const [fontes, setFontes] = useState<Fonte[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [aba, setAba] = useState<string>('visual');
  const [rascunho, setRascunho] = useState<Perfil>({});
  const [capturando, setCapturando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [avisosDaCaptura, setAvisosDaCaptura] = useState<string[]>([]);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const j = await fetch('/api/dashboard/brand-identity').then((r) => r.json());
      if (j?.ok) {
        setBruto(j);
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
    setCapturando(true); setAviso(''); setErro(''); setAvisosDaCaptura([]);
    try {
      const r = await fetch('/api/dashboard/brand-identity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const j = await r.json();
      if (j?.ok) {
        const n = (j.campos_propostos || j.campos || []).length;
        setAviso(`Identidade montada: ${n} ${n === 1 ? 'campo preenchido' : 'campos preenchidos'}.`);
        setAvisosDaCaptura((j.avisos || []).map(frasearAviso));
        if (Array.isArray(j.sources)) setFontes(j.sources);
        await carregar();
      } else {
        // 🔴 U1.2/E14 — o contrato é `error`. Quando o backend tem uma frase
        // para dar, ela chega aqui inteira; a frase genérica é o último recurso,
        // não o único.
        setErro(j?.error || 'A leitura não foi adiante. Confira o endereço do site.');
        if (Array.isArray(j?.sources)) setFontes(j.sources);
      }
    } catch {
      setErro('Não foi possível falar com o serviço de identidade.');
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
  const completude = Math.round(Number(perfil?.completeness || 0) * 100);
  const logo = assets.find((a) => a.kind === 'logo_primary') || assets[0];

  const estadoId: string = capturando
    ? 'capturing'
    : (perfil?.capture_status && ESTADOS[perfil.capture_status] ? perfil.capture_status : 'empty');
  const estado = ESTADOS[estadoId];
  const falhou = estadoId === 'failed';

  // 🔴 Numa captura que FALHOU, a paleta que está no banco é a de reserva.
  // Exibi-la como marca é o produto afirmando o que não aconteceu.
  const temMarca = Boolean(paleta?.primary) && !falhou;

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
  const motivoDaFalha = perfil?.capture_error || null;

  return (
    <div className="space-y-5">
      {/* ---------- cabeçalho da marca ---------- */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div
          className="flex flex-col gap-5 p-5 sm:flex-row sm:flex-wrap sm:items-center sm:gap-6 sm:p-6"
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

          <div className="min-w-0 flex-1 sm:min-w-[220px]">
            <h2 className="text-xl font-semibold text-foreground">
              {perfil?.display_name || 'Sua corretora'}
            </h2>
            {perfil?.tagline && <p className="mt-1 text-sm text-muted-foreground">{perfil.tagline}</p>}
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <div className="h-1.5 w-40 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${completude}%`, background: temMarca ? paleta.primary : 'hsl(var(--primary))' }}
                />
              </div>
              <span className="text-xs font-medium text-muted-foreground">{completude}% completa</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:items-end">
            <button
              onClick={capturar}
              disabled={capturando || semFonte}
              className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40 sm:w-auto"
            >
              {capturando ? 'Lendo seu site…' : temMarca ? 'Atualizar do site' : 'Montar identidade'}
            </button>
            {auditoria && !falhou && (
              <span className="text-[11px] text-muted-foreground">
                acessibilidade: {auditoria.ok} de {auditoria.total} combinações conferidas
              </span>
            )}
          </div>
        </div>

        {/* 🔴 U1.2 — a faixa de estado. Cada situação com a sua cor e a sua frase. */}
        <div className={`flex items-start gap-3 border-t px-5 py-4 sm:px-6 ${estado.anel}`}>
          <span className={`mt-1.5 h-2 w-2 flex-none rounded-full ${estado.ponto}`} />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">{estado.titulo}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{estado.frase}</p>
            {falhou && motivoDaFalha && (
              <p className="mt-2 text-xs font-medium text-foreground">{motivoDaFalha}</p>
            )}
            {falhou && paleta?.primary && (
              <p className="mt-2 text-xs text-muted-foreground">
                As cores mostradas nas abas são as do padrão da casa, não as da sua marca.
              </p>
            )}
          </div>
        </div>
      </div>

      {aviso && <p className="rounded-lg border border-primary/25 bg-primary/10 px-4 py-3 text-sm text-foreground">{aviso}</p>}
      {erro && <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground">{erro}</p>}
      {avisosDaCaptura.length > 0 && (
        <ul className="space-y-1.5 rounded-lg border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm text-foreground">
          {avisosDaCaptura.map((a, i) => <li key={i}>{a}</li>)}
        </ul>
      )}

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

        {/* P-098-REDES-BLOQUEIAM-LEITURA — 📊 as redes devolveram 429 nas três
            tentativas que existem no acervo, e nenhuma linha de LinkedIn ou
            Facebook jamais respondeu. Enquanto a leitura automática não passa,
            o corretor cola o texto que ele mesmo escreveu no perfil. */}
        <label className="mt-4 block">
          <span className="text-xs font-medium text-foreground-2">
            Descrição do seu Instagram ou LinkedIn (cole aqui)
          </span>
          <textarea
            rows={3}
            className={`mt-1 ${campoCls} resize-y`}
            placeholder="As redes bloqueiam a leitura automática. Cole aqui a descrição do perfil e ela entra na identidade."
            value={rascunho.bio_colada ?? ''}
            onChange={(e) => setRascunho({ ...rascunho, bio_colada: e.target.value })}
          />
        </label>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <button
            onClick={() => salvar({
              website_url: rascunho.website_url || null,
              instagram_url: rascunho.instagram_url || null,
              linkedin_url: rascunho.linkedin_url || null,
              google_business_url: rascunho.google_business_url || null,
              bio_colada: rascunho.bio_colada || null,
            })}
            disabled={salvando}
            className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40"
          >
            {salvando ? 'Salvando…' : 'Salvar endereços'}
          </button>
          {semFonte && <span className="text-xs text-muted-foreground">Informe ao menos o site para montar a identidade.</span>}
        </div>

        {fontes.length > 0 && (
          <ul className="mt-4 grid gap-2 border-t border-border pt-4">
            {fontes.slice(0, 6).map((f, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-xs">
                <span className={
                  f.status === 'fetched' ? 'text-emerald-500'
                    : f.status === 'blocked' ? 'text-amber-500' : 'text-destructive'
                }>●</span>
                <span className="w-40 font-medium text-foreground-2">{rotuloDaFonte(f.kind)}</span>
                <span className="min-w-0 flex-1 text-muted-foreground">{motivoDaFonte(f)}</span>
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
          falhou={falhou}
        />
      )}
      {aba === 'sobre' && (
        <AbaSobre rascunho={rascunho} setRascunho={setRascunho} proc={proc} salvar={salvar} salvando={salvando} />
      )}
      {aba === 'jeito' && (
        <AbaJeito perfil={perfil} bruto={bruto} recarregar={carregar} />
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

function AbaVisual({ perfil, rascunho, setRascunho, paleta, proc, logo, salvar, salvando, falhou }: any) {
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
      {falhou && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground">
          A última leitura do site não foi adiante. As cores abaixo são o padrão da
          casa, e não as da sua marca — corrija o endereço e leia de novo, ou
          escolha as cores à mão.
        </p>
      )}

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
          <p className="text-xs font-medium text-foreground-2">Do mais claro ao mais escuro</p>
          <div className="mt-2 flex overflow-hidden rounded-lg border border-border">
            {Object.entries(escala).map(([passo, cor]) => (
              <div
                key={passo}
                className="group relative h-10 flex-1"
                style={{ background: cor as string }}
                title={`Tom derivado da sua cor · ${cor}`}
              />
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Os tons saem todos da sua cor. É o que dá fundo, borda e realce nas peças.
          </p>
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
              <strong className="text-foreground">
                {falhas.length === 1
                  ? 'Uma combinação de cores ficou abaixo do mínimo de leitura.'
                  : `${falhas.length} combinações de cores ficaram abaixo do mínimo de leitura.`}
              </strong>{' '}
              <span className="text-muted-foreground">
                Nas peças usamos uma variação mais clara ou mais escura da sua cor nesses pontos, para
                o texto não sumir no fundo.
              </span>
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
          className="w-full rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40 sm:w-auto"
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
          className="w-full rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40 sm:w-auto"
        >
          {salvando ? 'Salvando…' : 'Salvar'}
        </button>
      </div>
    </div>
  );
}

// ==========================================================================
// SPEC-098 · U2.4 — O JEITO DE ATENDER
//
// 🔴 O nome da peça é "Jeito de atender". Não é "Soul", não é "tom", não é
// "persona": o corretor não tem palavra para essas três, e tem para esta.
//
// 📊 Medido em 06/09/2026: a coluna que guarda isto estava `{}` nas três
// corretoras do produto, inclusive na publicada. O agente falava com a voz da
// AutoBrokers em todas elas — e o acervo prova que a voz de cada corretora é
// diferente: uma abre "Oieee, tudo bem?" e a outra trata por "Sr./Sra." e
// explica o procedimento.
//
// R2: o modelo PROPÕE, a corretora PUBLICA. O estado inicial é vazio e visível
// — nunca semeado com um jeito que ninguém escolheu.
// ==========================================================================

const FRASE_DO_ESCOPO =
  'Isto muda como o agente fala. Não muda o que ele pode fazer, nem para quem fala.';

const ESCOLHAS: {
  chave: string;
  titulo: string;
  ajuda: string;
  opcoes: { valor: string; rotulo: string; exemplo: string }[];
}[] = [
  {
    chave: 'saudacao',
    titulo: 'Como o atendimento começa',
    ajuda: 'A primeira linha de toda conversa.',
    opcoes: [
      { valor: 'afetiva', rotulo: 'Calorosa', exemplo: 'Oi! Tudo bem com você?' },
      { valor: 'cordial', rotulo: 'Cordial', exemplo: 'Olá, bom dia!' },
      { valor: 'direta', rotulo: 'Direta', exemplo: 'Vai direto ao assunto.' },
    ],
  },
  {
    chave: 'tratamento',
    titulo: 'Como o cliente é chamado',
    ajuda: 'Vale para toda a conversa.',
    opcoes: [
      { valor: 'voce', rotulo: 'Por você', exemplo: 'Você já tem o número do chamado?' },
      { valor: 'senhor_senhora', rotulo: 'Por senhor e senhora', exemplo: 'O senhor já tem o número do chamado?' },
      { valor: 'pelo_nome', rotulo: 'Pelo primeiro nome', exemplo: 'Maria, você já tem o número do chamado?' },
    ],
  },
  {
    chave: 'emoji',
    titulo: 'Emoji',
    ajuda: 'No WhatsApp faz diferença; num e-mail formal, também.',
    opcoes: [
      { valor: 'nao', rotulo: 'Não usar', exemplo: 'Nenhum, em nenhuma mensagem.' },
      { valor: 'pontual', rotulo: 'De vez em quando', exemplo: 'Um ou outro, em boas notícias.' },
      { valor: 'livre', rotulo: 'À vontade', exemplo: 'Como vocês já escrevem hoje. 🙏' },
    ],
  },
  {
    chave: 'formalidade',
    titulo: 'Formalidade',
    ajuda: 'O quanto a escrita se aproxima da conversa falada.',
    opcoes: [
      { valor: 'informal', rotulo: 'Informal', exemplo: 'Pode deixar que eu resolvo!' },
      { valor: 'cordial', rotulo: 'Cordial', exemplo: 'Pode deixar comigo, eu cuido disso.' },
      { valor: 'formal', rotulo: 'Formal', exemplo: 'Providenciaremos o atendimento.' },
    ],
  },
  {
    chave: 'explicacao',
    titulo: 'Como explicar',
    ajuda: 'Quando o cliente precisa fazer alguma coisa.',
    opcoes: [
      { valor: 'passo_a_passo', rotulo: 'Passo a passo', exemplo: 'Primeiro isto, depois aquilo.' },
      { valor: 'direta', rotulo: 'Direta, em poucas linhas', exemplo: 'Só o essencial.' },
    ],
  },
];

const LISTAS: { chave: string; titulo: string; ajuda: string; teto: number; tamanho: number }[] = [
  {
    chave: 'principios',
    titulo: 'Princípios do atendimento',
    ajuda: 'O que vocês sempre fazem. Ex.: "confirmar o endereço antes de encerrar".',
    teto: 5,
    tamanho: 140,
  },
  {
    chave: 'termos_preferidos',
    titulo: 'Palavras que vocês usam',
    ajuda: 'Ex.: "acionamento" no lugar de "sinistro".',
    teto: 10,
    tamanho: 40,
  },
  {
    chave: 'evitar',
    titulo: 'Palavras que vocês evitam',
    ajuda: 'Ex.: jargão de seguradora que o cliente não entende.',
    teto: 10,
    tamanho: 40,
  },
  {
    chave: 'exemplos_aprovados',
    titulo: 'Mensagens que vocês aprovam',
    ajuda: 'Uma frase real que traduz o jeito de vocês.',
    teto: 3,
    tamanho: 220,
  },
];

function normalizarItem(x: any): ItemDeLista {
  if (x && typeof x === 'object') {
    return {
      texto: String(x.texto ?? x.valor ?? ''),
      sinalizado: x.sinalizado === true,
      confirmado: x.confirmado === true,
    };
  }
  return { texto: String(x ?? '') };
}

function listaDoJeito(jeito: Jeito | null, chave: string): ItemDeLista[] {
  const bruta = jeito?.[chave];
  if (!Array.isArray(bruta)) return [];
  return bruta.map(normalizarItem).filter((i) => i.texto.length > 0);
}

/** Vazio mede CONTEÚDO, não presença: `{}` continua sendo "ainda não declarado". */
function jeitoVazio(jeito: Jeito | null | undefined): boolean {
  if (!jeito || typeof jeito !== 'object') return true;
  const temEscolha = ESCOLHAS.some((e) => typeof jeito[e.chave] === 'string' && jeito[e.chave]);
  const temLista = LISTAS.some((l) => listaDoJeito(jeito, l.chave).length > 0);
  return !temEscolha && !temLista;
}

function frasearOrigemDaProposta(origem: string | null, evidencia: any): string {
  if (origem === 'conversas') {
    const lidas = Number(evidencia?.lidas ?? evidencia?.conversas_lidas ?? 0);
    const descartadas = Number(evidencia?.descartadas ?? evidencia?.conversas_descartadas ?? 0);
    if (lidas || descartadas) {
      return `aprendido das suas conversas: lidas ${lidas}, descartadas ${descartadas} por serem pessoais`;
    }
    return 'aprendido das suas conversas';
  }
  if (origem === 'administrador') return 'proposto por alguém da corretora';
  return 'proposto a partir do seu site';
}

function AbaJeito({ perfil, bruto, recarregar }: { perfil: Perfil | null; bruto: any; recarregar: () => Promise<void> }) {
  const ativo: Jeito | null = (perfil?.tone as Jeito) ?? null;
  const proposto: Jeito | null =
    (perfil?.tone_proposto as Jeito) ?? (bruto?.tone_proposto as Jeito) ?? null;
  const origemProposta: string | null =
    perfil?.tone_proposto_origem ?? bruto?.tone_proposto_origem ?? null;
  const evidencia = perfil?.tone_evidencia ?? bruto?.tone_evidencia ?? null;
  const versoes: any[] = Array.isArray(bruto?.versions)
    ? bruto.versions
    : Array.isArray(bruto?.brand_profile_versions)
      ? bruto.brand_profile_versions
      : [];

  const semAtivo = jeitoVazio(ativo);
  const temProposta = !jeitoVazio(proposto);

  // O que a tela edita: a proposta quando existe, senão o jeito ativo.
  const [rascunho, setRascunho] = useState<Jeito>(() =>
    JSON.parse(JSON.stringify(temProposta ? proposto : (ativo || {}))),
  );
  const [editando, setEditando] = useState(false);
  const [ocupado, setOcupado] = useState<'' | 'site' | 'conversas' | 'aprovar'>('');
  const [recado, setRecado] = useState('');
  const [problema, setProblema] = useState('');

  useEffect(() => {
    setRascunho(JSON.parse(JSON.stringify(temProposta ? proposto : (ativo || {}))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perfil, bruto]);

  const chamar = async (corpo: Record<string, unknown>, marca: '' | 'site' | 'conversas' | 'aprovar') => {
    setOcupado(marca); setRecado(''); setProblema('');
    try {
      const r = await fetch('/api/dashboard/brand-identity/jeito', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
      });
      const j = await r.json();
      if (j?.ok) {
        setRecado(
          marca === 'aprovar'
            ? 'Pronto. A partir de agora o agente fala assim.'
            : 'Proposta pronta. Confira abaixo antes de usar.',
        );
        setEditando(false);
        await recarregar();
      } else {
        setProblema(j?.error || 'Não foi possível concluir. Tente de novo.');
      }
    } catch {
      setProblema('Não foi possível falar com o serviço de identidade.');
    }
    setOcupado('');
  };

  const itens = (chave: string) => listaDoJeito(rascunho, chave);

  const trocarItem = (chave: string, i: number, campo: keyof ItemDeLista, valor: any) => {
    const lista = itens(chave);
    lista[i] = { ...lista[i], [campo]: valor };
    setRascunho({ ...rascunho, [chave]: lista });
  };

  const removerItem = (chave: string, i: number) => {
    const lista = itens(chave);
    lista.splice(i, 1);
    setRascunho({ ...rascunho, [chave]: lista });
  };

  const adicionarItem = (chave: string) => {
    setRascunho({ ...rascunho, [chave]: [...itens(chave), { texto: '' }] });
  };

  const podeEditar = editando || temProposta || !semAtivo;

  return (
    <div className="space-y-4">
      {/* ---- o que isto é, e o que isto não é ---- */}
      <section className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-foreground">Jeito de atender</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          É a forma de falar da sua corretora: como o atendimento abre, como o cliente é
          chamado, o que vocês sempre dizem e o que nunca dizem.
        </p>
        <p className="mt-3 rounded-lg border border-border bg-secondary/50 px-4 py-3 text-xs font-medium text-foreground">
          {FRASE_DO_ESCOPO}
        </p>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <button
            onClick={() => chamar({ acao: 'propor', origem: 'site' }, 'site')}
            disabled={ocupado !== ''}
            className="w-full rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40 sm:w-auto"
          >
            {ocupado === 'site' ? 'Lendo o site…' : 'Propor a partir do site'}
          </button>
          <button
            onClick={() => chamar({ acao: 'propor', origem: 'conversas' }, 'conversas')}
            disabled={ocupado !== ''}
            className="w-full rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40 sm:w-auto"
          >
            {ocupado === 'conversas' ? 'Lendo as conversas…' : 'Aprender com as conversas'}
          </button>
        </div>

        {recado && (
          <p className="mt-3 rounded-lg border border-primary/25 bg-primary/10 px-4 py-3 text-sm text-foreground">{recado}</p>
        )}
        {problema && (
          <p className="mt-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground">{problema}</p>
        )}
      </section>

      {/* ---- estado vazio ---- */}
      {semAtivo && !temProposta && (
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <p className="text-sm font-medium text-foreground">Ainda não declarado</p>
          <p className="mx-auto mt-2 max-w-lg text-sm text-muted-foreground">
            Enquanto ninguém escolher, o agente fala com a voz padrão da casa. Peça uma
            proposta a partir do site, deixe-o aprender com as suas conversas, ou preencha
            você mesma abaixo.
          </p>
          <button
            onClick={() => setEditando(true)}
            className="mt-4 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-secondary"
          >
            Preencher à mão
          </button>
        </div>
      )}

      {/* ---- a proposta, com origem e evidência ---- */}
      {temProposta && (
        <section className="rounded-xl border border-amber-500/35 bg-amber-500/5 p-5">
          <p className="text-sm font-semibold text-foreground">
            Há uma proposta esperando a sua decisão
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {frasearOrigemDaProposta(origemProposta, evidencia)}. Nada disso vale enquanto
            você não aprovar.
          </p>
          <EvidenciaDaProposta evidencia={evidencia} />
        </section>
      )}

      {/* ---- as cinco escolhas ---- */}
      {(podeEditar || temProposta) && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">As cinco escolhas</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            São fechadas de propósito: uma escolha entre três é uma decisão; um campo livre
            é uma redação que ninguém revisa.
          </p>

          <div className="mt-4 space-y-5">
            {ESCOLHAS.map((e) => (
              <fieldset key={e.chave}>
                <legend className="text-xs font-semibold text-foreground-2">{e.titulo}</legend>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{e.ajuda}</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {e.opcoes.map((o) => {
                    const marcado = rascunho[e.chave] === o.valor;
                    return (
                      <label
                        key={o.valor}
                        className={`flex cursor-pointer flex-col gap-1 rounded-lg border p-3 transition ${
                          marcado ? 'border-primary bg-primary/5' : 'border-border hover:border-border-strong'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <input
                            type="radio"
                            checked={marcado}
                            onChange={() => setRascunho({ ...rascunho, [e.chave]: o.valor })}
                            aria-label={`${e.titulo}: ${o.rotulo}`}
                            className="h-3.5 w-3.5 accent-[hsl(var(--primary))]"
                          />
                          <span className="text-sm font-medium text-foreground">{o.rotulo}</span>
                        </span>
                        <span className="text-[11px] text-muted-foreground">{o.exemplo}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            ))}
          </div>
        </section>
      )}

      {/* ---- as quatro listas ---- */}
      {(podeEditar || temProposta) && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">O que sempre dizer, e o que nunca</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Cada lista tem um teto. O que passar do teto fica guardado aqui e não entra na
            conversa — um jeito longo demais deixa de ser um jeito e vira um manual.
          </p>

          <div className="mt-4 space-y-6">
            {LISTAS.map((l) => {
              const lista = itens(l.chave);
              const cheio = lista.length >= l.teto;
              return (
                <div key={l.chave}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-xs font-semibold text-foreground-2">{l.titulo}</span>
                    <span className={`text-[11px] ${cheio ? 'text-amber-500' : 'text-muted-foreground'}`}>
                      {lista.length} de {l.teto} · até {l.tamanho} caracteres cada
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">{l.ajuda}</p>

                  <div className="mt-2 space-y-2">
                    {lista.map((item, i) => (
                      <div key={i} className="rounded-lg border border-border p-2.5">
                        <div className="flex items-start gap-2">
                          <textarea
                            rows={l.tamanho > 60 ? 2 : 1}
                            maxLength={l.tamanho}
                            className={`${campoCls} resize-y`}
                            value={item.texto}
                            onChange={(ev) => trocarItem(l.chave, i, 'texto', ev.target.value.slice(0, l.tamanho))}
                          />
                          <button
                            onClick={() => removerItem(l.chave, i)}
                            className="mt-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                            aria-label="Remover este item"
                          >
                            remover
                          </button>
                        </div>

                        {/* 🔴 R4 ③ — o item que parece dar uma ORDEM ao sistema não é
                            descartado em silêncio: ele é mostrado, explicado, e só
                            entra na conversa se a administradora confirmar que é
                            regra de atendimento. Descartar calado ensinaria o
                            corretor a não confiar no que ele escreve. */}
                        {item.sinalizado && (
                          <div className="mt-2 rounded-md border border-amber-500/35 bg-amber-500/10 px-3 py-2">
                            <p className="text-[11px] text-foreground">
                              Este item parece dar uma ordem ao sistema, e não descrever um
                              jeito de atender. Confirme que é uma regra de atendimento para
                              ele valer.
                            </p>
                            <label className="mt-2 flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={item.confirmado === true}
                                onChange={(ev) => trocarItem(l.chave, i, 'confirmado', ev.target.checked)}
                                className="h-3.5 w-3.5 accent-[hsl(var(--primary))]"
                              />
                              <span className="text-[11px] font-medium text-foreground">
                                confirmo que é regra de atendimento
                              </span>
                            </label>
                          </div>
                        )}
                      </div>
                    ))}

                    {!cheio && (
                      <button
                        onClick={() => adicionarItem(l.chave)}
                        className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground transition hover:border-primary/40 hover:text-foreground"
                      >
                        + acrescentar
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col gap-2 border-t border-border pt-5 sm:flex-row sm:justify-end">
            <button
              onClick={() => {
                setRascunho(JSON.parse(JSON.stringify(temProposta ? proposto : (ativo || {}))));
                setEditando(true);
              }}
              disabled={ocupado !== ''}
              className="w-full rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40 sm:w-auto"
            >
              Ajustar
            </button>
            <button
              onClick={() => chamar({ acao: 'aprovar', ajustes: rascunho }, 'aprovar')}
              disabled={ocupado !== ''}
              className="w-full rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-40 sm:w-auto"
            >
              {ocupado === 'aprovar' ? 'Aplicando…' : 'Usar este jeito'}
            </button>
          </div>
          <p className="mt-3 text-right text-[11px] text-muted-foreground">{FRASE_DO_ESCOPO}</p>
        </section>
      )}

      {/* ---- o que vale hoje ---- */}
      {!semAtivo && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">O que vale hoje</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            É assim que o agente fala com o seu cliente neste momento.
          </p>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2">
            {ESCOLHAS.map((e) => {
              const o = e.opcoes.find((x) => x.valor === ativo?.[e.chave]);
              if (!o) return null;
              return (
                <div key={e.chave} className="flex justify-between gap-3 rounded-lg border border-border px-3 py-2">
                  <dt className="text-xs text-muted-foreground">{e.titulo}</dt>
                  <dd className="text-xs font-medium text-foreground">{o.rotulo}</dd>
                </div>
              );
            })}
          </dl>
        </section>
      )}

      {/* ---- histórico ---- */}
      {versoes.length > 0 && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">Como isto mudou</h3>
          <ul className="mt-3 space-y-2">
            {versoes.slice(0, 10).map((v: any, i: number) => (
              <li key={i} className="flex flex-wrap justify-between gap-2 border-b border-border pb-2 text-xs last:border-0">
                <span className="text-foreground">{v?.motivo_humano || 'Jeito de atender aprovado'}</span>
                <span className="text-muted-foreground">
                  {v?.created_at ? new Date(v.created_at).toLocaleDateString('pt-BR') : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function EvidenciaDaProposta({ evidencia }: { evidencia: any }) {
  const frases: string[] = Array.isArray(evidencia?.frases)
    ? evidencia.frases
    : Array.isArray(evidencia)
      ? evidencia
      : [];
  if (!frases.length) return null;
  return (
    <div className="mt-3">
      <p className="text-[11px] font-medium text-foreground-2">Em que a proposta se apoia</p>
      <ul className="mt-1.5 space-y-1">
        {frases.slice(0, 3).map((f, i) => (
          <li key={i} className="border-l-2 border-amber-500/40 pl-3 text-xs italic text-muted-foreground">
            {String(f)}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ==========================================================================

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
          para você conferir e discordar quando for o caso. Só aparece o que tem valor
          preenchido: um campo vazio não tem procedência.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-5 py-3 font-semibold">Informação</th>
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
                  {/* 🔴 R10/R11 — o nome que o corretor usa, nunca o caminho no banco. */}
                  <td className="px-5 py-3 text-xs text-foreground">{rotuloDoCampo(p.field_path)}</td>
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
