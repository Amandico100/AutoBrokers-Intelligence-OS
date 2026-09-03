'use client';

// SPEC-088 BLOCO D — A Central de Agentes diz a verdade.
//
// O QUE MUDOU, E POR QUÊ.
//
// Esta tela tinha DUAS listas de agentes: a do backend e a `COLORS` daqui,
// com 9 ids contra 14 do `heartbeat.py`. Cinco trabalhadores (observador,
// tecelao, sentinela_rotas, espelho_atendimento, conselho) não tinham cor
// porque ninguém lembrou de acrescentá-los na segunda lista — e ninguém
// lembra, porque uma segunda lista não avisa que envelheceu.
//
// 🔴 Agora o frontend NÃO SABE NENHUM AGENTE. Nome, descrição, cor, grupo e
// estado vêm do JSON (SPEC-088 §4). Um trabalhador novo aparece sem tocar
// neste arquivo — é o gate ② do BLOCO D, e é a referência ⑥ (Datadog Software
// Catalog: grupo e dono são metadado da entidade; a UI só lê).
//
// E o verde ficou difícil: o estado vem do backend com cinco valores, e a
// ausência de sinal NUNCA pinta o estado benigno (referência ⑤, Claude Code
// agent teams: "hidden, not stopped"). Um estado que esta tela não conhece
// aparece em VERMELHO, não em cinza.
//
// A tela é `require_master_admin`. Ela mostra contagens, estados, ids e
// horários — nunca conteúdo de conversa (referência ⑦).

import { useEffect, useState } from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// O contrato da rota — SPEC-088 §4, congelado. Nenhuma chave fora desta lista.
// ─────────────────────────────────────────────────────────────────────────────

type Pulso = { ultimo: string | null; origem: string | null };

type Producao = {
  ultimo: string | null;
  fonte: string | null;
  cadencia_esperada_s: number | null;
  limiar_s: number | null;
};

type Desligamento = {
  declara: boolean;
  todas_desligadas: boolean | null;
  desde: string | null;
};

type Trabalho = {
  eixo: string[] | null;
  execucoes_24h: number | null;
  execucoes_7d: number | null;
  falhas_7d: number | null;
  duracao_media_s: number | null;
  fila_media_s: number | null;
  artifacts_7d: number | null;
  aprovacoes_pendentes: number | null;
  travados: number | null;
  custo_brl_30d: number | null;
};

type Agente = {
  id: string;
  nome: string;
  descricao: string | null;
  cor: string | null;
  grupo: string | null;
  estado: string;
  motivo: string | null;
  pulso: Pulso | null;
  producao: Producao | null;
  desligado: Desligamento | null;
  trabalho: Trabalho | null;
  acoes_hoje: number | null;
};

type Grupo = {
  id: string;
  titulo: string;
  proposito: string | null;
  resumo: string | null;
  agentes: Agente[];
};

type Status = {
  gerado_em: string | null;
  cache_s: number | null;
  grupos: Grupo[];
  nao_instrumentado: string[];
  sem_card_por_decisao: { workflow_key: string; motivo: string }[];
};

type BlocoDeMemoria = { key: string; content: string; updated_at: string };

// ─────────────────────────────────────────────────────────────────────────────
// Estados. A cor é DO ESTADO; a cor do agente vive no JSON e só pinta o losango.
// A ordem coloca o problema primeiro: quem lê a tela precisa ver o que dói.
// ─────────────────────────────────────────────────────────────────────────────

const ESTADOS: Record<string, { rotulo: string; cor: string; ordem: number }> = {
  PARADO: { rotulo: 'PARADO', cor: '#E06B6B', ordem: 1 },
  PULSA_SEM_PRODUZIR: { rotulo: 'PULSA SEM PRODUZIR', cor: '#E2A94F', ordem: 2 },
  NAO_MEDIDO: { rotulo: 'NÃO MEDIDO', cor: '#4A4F5A', ordem: 3 },
  DESLIGADO: { rotulo: 'DESLIGADO', cor: '#8A93A3', ordem: 4 },
  SAUDAVEL: { rotulo: 'SAUDÁVEL', cor: '#43C08C', ordem: 5 },
};

// Um estado que esta tela não conhece é um defeito de contrato, não um agente
// tranquilo. Ele vai para o topo, em vermelho.
const DESCONHECIDO = { rotulo: 'ESTADO DESCONHECIDO', cor: '#E06B6B', ordem: 0 };

const ORDEM_DA_BARRA = ['PARADO', 'PULSA_SEM_PRODUZIR', 'NAO_MEDIDO', 'DESLIGADO', 'SAUDAVEL'];

function estadoDe(e: string) {
  return ESTADOS[e] || DESCONHECIDO;
}

function ehProblema(e: string): boolean {
  return e === 'PARADO' || e === 'PULSA_SEM_PRODUZIR' || e === 'NAO_MEDIDO' || !ESTADOS[e];
}

const S = {
  page: { background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' } as React.CSSProperties,
  card: { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14, padding: '16px 18px' } as React.CSSProperties,
  mono: { fontFamily: 'Geist Mono, monospace' } as React.CSSProperties,
  rotulo: { fontSize: 9.5, letterSpacing: '0.08em', color: '#5A6577', fontFamily: 'Geist Mono, monospace' } as React.CSSProperties,
};

const CINZA_SEM_MEDIDA = '#5A6577';

function ago(iso: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '—';
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 90) return `há ${Math.round(s)}s`;
  if (s < 5400) return `há ${Math.round(s / 60)} min`;
  if (s < 172800) return `há ${Math.round(s / 3600)} h`;
  return `há ${Math.round(s / 86400)} dias`;
}

function cadencia(s: number | null): string {
  if (s == null) return 'sem cadência declarada';
  if (s >= 86400) return `espera 1× a cada ${Math.round(s / 86400)} dia(s)`;
  if (s >= 3600) return `espera 1× a cada ${Math.round(s / 3600)} h`;
  return `espera 1× a cada ${Math.round(s / 60)} min`;
}

/** Número que pode não existir. Null NUNCA vira zero — vira o texto honesto. */
function Numero({ v, sufixo, casas }: { v: number | null | undefined; sufixo?: string; casas?: number }) {
  if (v == null) {
    return <span style={{ color: CINZA_SEM_MEDIDA, fontSize: 10.5 }}>não instrumentado</span>;
  }
  const texto = casas != null ? v.toFixed(casas).replace('.', ',') : String(v);
  return (
    <span style={{ color: '#E7EBF1' }}>
      {texto}
      {sufixo ? <span style={{ color: '#5A6577', fontSize: 10 }}> {sufixo}</span> : null}
    </span>
  );
}

function Metrica({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={S.rotulo}>{rotulo}</span>
      <span style={{ ...S.mono, fontSize: 13 }}>{children}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Agrupamento. O grupo vem do JSON; o que NÃO tem grupo conhecido não some —
// aparece num grupo sintético vermelho. É a mutação do gate ② do BLOCO D.
// ─────────────────────────────────────────────────────────────────────────────

const SEM_GRUPO = '__sem_grupo__';

type GrupoNaTela = Grupo & { sintetico?: boolean };

function montarGrupos(status: Status | null): GrupoNaTela[] {
  if (!status || !Array.isArray(status.grupos)) return [];
  const conhecidos = new Set(status.grupos.map((g) => g && g.id).filter(Boolean));
  const orfaos: Agente[] = [];

  const grupos: GrupoNaTela[] = status.grupos.map((g) => {
    const agentes = (g.agentes || []).filter((a) => {
      const sem = !a.grupo || !conhecidos.has(a.grupo);
      if (sem) orfaos.push(a);
      return !sem;
    });
    return { ...g, agentes: ordenar(agentes) };
  });

  if (orfaos.length > 0) {
    grupos.push({
      id: SEM_GRUPO,
      titulo: 'SEM GRUPO',
      proposito: 'o JSON entregou estes trabalhadores sem um grupo que exista — a tela não adota ninguém por conta própria',
      resumo: `${orfaos.length} trabalhador(es) sem grupo declarado`,
      agentes: ordenar(orfaos),
      sintetico: true,
    });
  }
  return grupos;
}

function ordenar(agentes: Agente[]): Agente[] {
  return [...agentes].sort((a, b) => {
    const d = estadoDe(a.estado).ordem - estadoDe(b.estado).ordem;
    return d !== 0 ? d : (a.nome || a.id).localeCompare(b.nome || b.id);
  });
}

function contarPorEstado(grupos: GrupoNaTela[]): { chave: string; rotulo: string; cor: string; n: number }[] {
  const contas = new Map<string, number>();
  grupos.forEach((g) => g.agentes.forEach((a) => {
    const chave = ESTADOS[a.estado] ? a.estado : '__desconhecido__';
    contas.set(chave, (contas.get(chave) || 0) + 1);
  }));
  const linhas = ORDEM_DA_BARRA.map((e) => ({ chave: e, rotulo: ESTADOS[e].rotulo, cor: ESTADOS[e].cor, n: contas.get(e) || 0 }));
  const desconhecidos = contas.get('__desconhecido__') || 0;
  if (desconhecidos > 0) {
    linhas.unshift({ chave: '__desconhecido__', rotulo: DESCONHECIDO.rotulo, cor: DESCONHECIDO.cor, n: desconhecidos });
  }
  return linhas;
}

// ─────────────────────────────────────────────────────────────────────────────
// O card de um trabalhador.
// ─────────────────────────────────────────────────────────────────────────────

function CardAgente({ agente, grupoDoCard, memoria, memAberta, aoAbrirMemoria, trabAberto, aoAbrirTrabalho }: {
  agente: Agente;
  grupoDoCard: string;
  memoria: BlocoDeMemoria[];
  memAberta: boolean;
  aoAbrirMemoria: () => void;
  trabAberto: boolean;
  aoAbrirTrabalho: () => void;
}) {
  const est = estadoDe(agente.estado);
  const corDoAgente = agente.cor || '#7FB7E8';
  const t = agente.trabalho;
  const divergente = !!agente.grupo && grupoDoCard !== SEM_GRUPO && agente.grupo !== grupoDoCard;

  return (
    <div style={{ ...S.card, display: 'flex', flexDirection: 'column', gap: 9 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
        <span style={{ width: 11, height: 11, borderRadius: 3, background: corDoAgente, transform: 'rotate(45deg)', boxShadow: `0 0 6px ${corDoAgente}` }} />
        <span style={{ fontSize: 14.5, fontWeight: 600 }}>{agente.nome || agente.id}</span>
        <span style={{ flex: 1 }} />
        <span style={{ ...S.mono, fontSize: 9.5, letterSpacing: '0.08em', padding: '3px 9px', borderRadius: 999, border: `1px solid ${est.cor}55`, color: est.cor, whiteSpace: 'nowrap' }}>
          {est.rotulo}
        </span>
      </div>

      {agente.descricao ? (
        <div style={{ fontSize: 12.5, color: '#8A93A3', lineHeight: 1.5 }}>{agente.descricao}</div>
      ) : null}

      {/* O motivo do estado, em uma frase. É o que responde "por que esta cor?". */}
      <div style={{ fontSize: 12, color: est.cor, lineHeight: 1.5, background: '#080B10', border: `1px solid ${est.cor}33`, borderRadius: 8, padding: '8px 10px' }}>
        {agente.motivo || 'o backend não explicou este estado'}
      </div>

      {divergente ? (
        <div style={{ ...S.mono, fontSize: 10, color: '#E06B6B' }}>
          declara o grupo <span style={{ color: '#E7EBF1' }}>{agente.grupo}</span> e veio dentro de <span style={{ color: '#E7EBF1' }}>{grupoDoCard}</span>
        </div>
      ) : null}

      <div style={{ ...S.mono, fontSize: 10.5, color: '#5A6577', display: 'flex', flexDirection: 'column', gap: 3, borderTop: '1px solid #131A23', paddingTop: 8 }}>
        <span>
          pulso <span style={{ color: agente.pulso?.ultimo ? '#A9B2C0' : CINZA_SEM_MEDIDA }}>{agente.pulso?.ultimo ? ago(agente.pulso.ultimo) : 'sem pulso registrado'}</span>
          {agente.pulso?.origem ? <span> · via {agente.pulso.origem}</span> : null}
        </span>
        <span>
          produção <span style={{ color: agente.producao?.ultimo ? '#A9B2C0' : CINZA_SEM_MEDIDA }}>{agente.producao?.ultimo ? ago(agente.producao.ultimo) : 'sem produção registrada'}</span>
          {agente.producao ? <span> · {cadencia(agente.producao.cadencia_esperada_s)}</span> : null}
        </span>
        {agente.producao?.fonte ? <span style={{ color: '#4A4F5A' }}>fonte: {agente.producao.fonte}</span> : null}
        {agente.desligado?.declara ? (
          <span>
            desligado{agente.desligado.todas_desligadas ? ' em todas as corretoras' : ''}
            {agente.desligado.desde ? ` · desde ${ago(agente.desligado.desde)}` : ' · sem registro de quando'}
          </span>
        ) : null}
      </div>

      {/* TRABALHO — o que este trabalhador FEZ. Sem eixo declarado, dizemos isso. */}
      {t == null ? (
        <div style={{ ...S.mono, fontSize: 10.5, color: CINZA_SEM_MEDIDA, borderTop: '1px solid #131A23', paddingTop: 8 }}>
          sem eixo de trabalho
        </div>
      ) : (
        <div style={{ borderTop: '1px solid #131A23', paddingTop: 8 }}>
          <span
            role="button"
            tabIndex={0}
            onClick={aoAbrirTrabalho}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') aoAbrirTrabalho(); }}
            style={{ ...S.mono, fontSize: 10, color: '#7FB7E8', cursor: 'pointer', letterSpacing: '0.06em' }}
          >
            {trabAberto ? '▾ TRABALHO' : '▸ TRABALHO (o que este trabalhador fez)'}
          </span>
          {trabAberto ? (
            <div style={{ marginTop: 9, display: 'flex', flexDirection: 'column', gap: 9 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(96px, 1fr))', gap: 9 }}>
                <Metrica rotulo="EXECUÇÕES 24H"><Numero v={t.execucoes_24h} /></Metrica>
                <Metrica rotulo="EXECUÇÕES 7D"><Numero v={t.execucoes_7d} /></Metrica>
                <Metrica rotulo="FALHAS 7D"><Numero v={t.falhas_7d} /></Metrica>
                <Metrica rotulo="DURAÇÃO MÉDIA"><Numero v={t.duracao_media_s} sufixo="s" casas={1} /></Metrica>
                <Metrica rotulo="ESPERA NA FILA"><Numero v={t.fila_media_s} sufixo="s" casas={1} /></Metrica>
                <Metrica rotulo="ENTREGAS 7D"><Numero v={t.artifacts_7d} /></Metrica>
                <Metrica rotulo="APROVAÇÕES ABERTAS"><Numero v={t.aprovacoes_pendentes} /></Metrica>
                <Metrica rotulo="TRAVADOS"><Numero v={t.travados} /></Metrica>
                <Metrica rotulo="CUSTO 30D"><Numero v={t.custo_brl_30d} sufixo="BRL" casas={2} /></Metrica>
              </div>
              <div style={{ ...S.mono, fontSize: 9.5, color: '#4A4F5A' }}>
                eixo: {t.eixo && t.eixo.length > 0 ? t.eixo.join(' · ') : 'sem eixo declarado'}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* SPEC-041: memória por agente ("o que cada um sabe") — reescrita 1x/dia. */}
      {memoria.length > 0 ? (
        <div style={{ borderTop: '1px solid #131A23', paddingTop: 8 }}>
          <span
            role="button"
            tabIndex={0}
            onClick={aoAbrirMemoria}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') aoAbrirMemoria(); }}
            style={{ ...S.mono, fontSize: 10, color: '#E2A94F', cursor: 'pointer', letterSpacing: '0.06em' }}
          >
            {memAberta ? '▾ MEMÓRIA' : '▸ MEMÓRIA (o que este agente sabe)'}
          </span>
          {memAberta
            ? memoria.map((b) => (
              <div key={b.key} style={{ fontSize: 11.5, color: '#A9B2C0', lineHeight: 1.55, marginTop: 7, background: '#080B10', border: '1px solid #131A23', borderRadius: 8, padding: '9px 11px' }}>
                {b.content}
              </div>
            ))
            : null}
        </div>
      ) : null}

      <div style={{ display: 'flex', alignItems: 'center', ...S.mono, fontSize: 10.5, color: '#5A6577', borderTop: '1px solid #131A23', paddingTop: 8 }}>
        <span style={{ flex: 1 }} />
        <span>
          {agente.acoes_hoje == null
            ? <span style={{ color: CINZA_SEM_MEDIDA }}>ações de hoje: não instrumentado</span>
            : <span><span style={{ color: '#A9B2C0' }}>{agente.acoes_hoje}</span> ações · hoje</span>}
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// A tela. Função pura de (status, memórias) → árvore: é ela que o guarda
// `scripts/central-de-agentes-mostra-o-trabalho.test.mjs` renderiza.
// ─────────────────────────────────────────────────────────────────────────────

function Central({ status, memorias, carregando, erro }: {
  status: Status | null;
  memorias: Record<string, { blocks: BlocoDeMemoria[] }>;
  carregando: boolean;
  erro: string | null;
}) {
  const [memAberta, setMemAberta] = useState<string | null>(null);
  const [trabalhoTocado, setTrabalhoTocado] = useState<Record<string, boolean>>({});

  const grupos = montarGrupos(status);
  const linhas = contarPorEstado(grupos);
  const total = linhas.reduce((a, b) => a + b.n, 0);

  return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Central de Agentes</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>
          Quem está trabalhando, quem parou de produzir e o que cada um fez — por grupo de propósito.
        </div>
      </div>

      <div style={{ ...S.card, marginTop: 14, padding: '11px 16px', display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', ...S.mono, fontSize: 11, color: '#7C8798' }}>
        <span>{total} trabalhadores</span>
        {linhas.map((l) => (
          <span key={l.chave} style={{ display: 'flex', alignItems: 'center', gap: 6, color: l.n > 0 ? l.cor : '#39404C' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: l.n > 0 ? l.cor : '#39404C' }} />
            {l.n} {l.rotulo}
          </span>
        ))}
        <span style={{ flex: 1 }} />
        {status?.gerado_em ? <span>medido {ago(status.gerado_em)}{status.cache_s ? ` · cache ${status.cache_s}s` : ''}</span> : null}
        {carregando ? <span>carregando…</span> : null}
      </div>

      {erro ? (
        <div style={{ ...S.card, marginTop: 14, borderColor: '#E06B6B55', color: '#E06B6B', fontSize: 12.5 }}>{erro}</div>
      ) : null}

      {!erro && !carregando && grupos.length === 0 ? (
        <div style={{ ...S.card, marginTop: 14, borderColor: '#E06B6B55', color: '#E06B6B', fontSize: 12.5 }}>
          A rota não devolveu grupos. Isto é um defeito da medição, não uma casa vazia.
        </div>
      ) : null}

      {grupos.map((g) => (
        <div key={g.id} style={{ marginTop: 22 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ ...S.mono, fontSize: 12, letterSpacing: '0.1em', color: g.sintetico ? '#E06B6B' : '#A9B2C0' }}>{g.titulo}</span>
            {g.proposito ? <span style={{ fontSize: 12, color: '#5A6577' }}>{g.proposito}</span> : null}
          </div>
          <div style={{ ...S.mono, fontSize: 11, color: g.sintetico ? '#E06B6B' : '#7C8798', marginTop: 5 }}>
            {g.resumo || 'sem resumo'} <span style={{ color: '#4A4F5A' }}>· {g.agentes.length} cards nesta tela</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12, marginTop: 11 }}>
            {g.agentes.map((a) => {
              const padraoAberto = ehProblema(a.estado);
              const chave = `${g.id}:${a.id}`;
              const aberto = trabalhoTocado[chave] === undefined ? padraoAberto : trabalhoTocado[chave];
              return (
                <CardAgente
                  key={chave}
                  agente={a}
                  grupoDoCard={g.id}
                  memoria={memorias[a.id]?.blocks || []}
                  memAberta={memAberta === chave}
                  aoAbrirMemoria={() => setMemAberta(memAberta === chave ? null : chave)}
                  trabAberto={aberto}
                  aoAbrirTrabalho={() => setTrabalhoTocado({ ...trabalhoTocado, [chave]: !aberto })}
                />
              );
            })}
          </div>
        </div>
      ))}

      {/* O rodapé do que a tela NÃO mede. Sem ele, um zero silencioso vira fato. */}
      <div style={{ marginTop: 26, borderTop: '1px solid #131A23', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 5, ...S.mono, fontSize: 10, color: '#4A4F5A' }}>
        {status && status.nao_instrumentado && status.nao_instrumentado.length > 0 ? (
          <span>esta tela ainda não mede: {status.nao_instrumentado.join(' · ')}</span>
        ) : null}
        {status && status.sem_card_por_decisao && status.sem_card_por_decisao.length > 0 ? (
          <span>
            fora da tela por decisão: {status.sem_card_por_decisao.map((d) => `${d.workflow_key} (${d.motivo})`).join(' · ')}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export default function CentralAgentesPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [memorias, setMemorias] = useState<Record<string, { blocks: BlocoDeMemoria[] }>>({});
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const carregar = () =>
      fetch('/api/admin/spec034/agents-status', { cache: 'no-store' })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((d: Status) => { setStatus(d); setErro(null); })
        .catch(() => setErro('Não consegui ler a saúde dos agentes. O que está na tela pode estar velho.'))
        .finally(() => setCarregando(false));
    const carregarMemorias = () =>
      fetch('/api/admin/atlas/central/memorias', { cache: 'no-store' })
        .then((r) => r.json())
        .then((d) => { if (d && d.ok) setMemorias(d.memorias || {}); })
        .catch(() => undefined);

    carregar();
    carregarMemorias();
    const t = setInterval(carregar, 20000);
    const tm = setInterval(carregarMemorias, 120000);
    return () => { clearInterval(t); clearInterval(tm); };
  }, []);

  return <Central status={status} memorias={memorias} carregando={carregando} erro={erro} />;
}
