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

// `origem_rotulo`, `fonte_rotulo` e `cadencia_humana` são o texto JÁ em português
// que o backend manda (SPEC-088 §4, rodada de conserto). São opcionais de
// propósito: enquanto não vierem, a tela usa um rótulo genérico — NUNCA o nome
// técnico (DS-001 §6.7: "Redis" não é palavra de corretor).
type Pulso = {
  ultimo: string | null;
  origem: string | null;
  origem_rotulo?: string | null;
  cadencia_humana?: string | null;
};

type Producao = {
  ultimo: string | null;
  fonte: string | null;
  cadencia_esperada_s: number | null;
  limiar_s: number | null;
  fonte_rotulo?: string | null;
  cadencia_humana?: string | null;
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

// 🔴 Um trabalhador que EXECUTOU não pode ter o painel do trabalho recolhido —
// nem quando o estado é ⚪ DESLIGADO. Foi assim que `execucoes_24h: 1` num card
// desligado ficou escondido: `ehProblema()` não inclui DESLIGADO, e a
// contradição — desligado que roda — é exatamente o que o Founder precisa ver.
function trabalhouRecentemente(t: Trabalho | null): boolean {
  if (!t) return false;
  return (t.execucoes_24h || 0) > 0 || (t.execucoes_7d || 0) > 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Português de gente — DS-001 §6.7.
//
// O Founder não lê `attendance_transcripts.created_at`, não lê "via redis" e
// não lê "1 dia(s)". O backend manda os rótulos humanos; ENQUANTO algum texto
// vier cru (motivo, descrição, propósito), este filtro traduz na exibição.
// Ele é rede de segurança, não desculpa: o rótulo certo nasce no backend.
// ─────────────────────────────────────────────────────────────────────────────

const NOME_TECNICO = /\b[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\b/g;
const NOME_DE_INFRA = /\b(redis|work_runs|work_run|workflow_key|workflow_keys|None|null)\b/gi;
const ESTADO_DE_MOTOR = /\((completed|failed|running|queued|pending|success|error)\)/gi;
const PLURAL_DE_FORMULARIO = /\(([a-zç]{1,3})\)/gi;

// Uma versão não-global (`.test()` com /g guarda estado entre chamadas) para
// PERGUNTAR se um rótulo é técnico, em vez de reescrevê-lo.
const TEM_NOME_TECNICO = /\b[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\b|\b(redis|work_runs?|workflow_keys?|None|null)\b/i;

function semJargao(t: string | null | undefined): string {
  if (!t) return '';
  return String(t)
    .replace(/\s*∪\s*/g, ' e ')
    .replace(NOME_TECNICO, 'a produção dele')
    .replace(NOME_DE_INFRA, 'o laço dele')
    .replace(ESTADO_DE_MOTOR, '')
    .replace(PLURAL_DE_FORMULARIO, '$1')
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+([·,.;])/g, '$1')
    .trim();
}

// O que a tela ainda não mede vem em chave ASCII (`custo`, `aprovacoes`). Chave
// não é frase: aqui ela vira o nome que o Founder usa. Chave desconhecida
// aparece como ela é — sem inventar tradução — e limpa de jargão.
const NOME_DO_QUE_FALTA: Record<string, string> = {
  custo: 'custo por trabalhador',
  aprovacoes: 'aprovações pendentes',
  artifacts: 'entregas',
  trabalho: 'execuções dos últimos 30 dias (leitura truncada)',
  leitura: 'a leitura do banco (indisponível nesta medição)',
};

function nomeDoQueFalta(chave: string): string {
  return NOME_DO_QUE_FALTA[chave] || semJargao(chave) || chave;
}

// 🔴 O campo cru (`producao.fonte`, `pulso.origem`) ora traz nome de tabela, ora
// já traz frase de gente — e vai trazer frase de gente sempre que o backend
// mandar `fonte_rotulo`. A tela não aposta: ela PERGUNTA. Texto com cara de
// nome técnico é substituído pelo rótulo genérico; texto que já é português
// passa inteiro, porque jogá-lo fora seria perder informação boa por medo.
function rotuloHumano(bruto: string | null | undefined, generico: string): string {
  const t = String(bruto || '').trim();
  if (!t) return '';
  return TEM_NOME_TECNICO.test(t) ? generico : semJargao(t);
}

const S = {
  page: { background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' } as React.CSSProperties,
  card: { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14, padding: '16px 18px' } as React.CSSProperties,
  mono: { fontFamily: 'Geist Mono, monospace' } as React.CSSProperties,
  rotulo: { fontSize: 9.5, letterSpacing: '0.08em', color: '#5A6577', fontFamily: 'Geist Mono, monospace' } as React.CSSProperties,
};

const CINZA_SEM_MEDIDA = '#5A6577';

// 🔴 O "agora" dos cards é o `gerado_em` do JSON, não o relógio do navegador.
// A frase do `motivo` foi escrita no servidor; se o "há N dias" ao lado dela
// contasse a partir do relógio local, as duas discordariam — e uma máquina com
// a hora adiantada chegava a mostrar tempo NEGATIVO. `Math.max(0, …)` fecha a
// segunda porta. O relógio do navegador continua valendo para UMA coisa: dizer
// quão velha está a página que o Founder tem na frente.
function ago(iso: string | null, agora: number): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '—';
  const s = Math.max(0, (agora - t) / 1000);
  if (s < 90) return `há ${Math.round(s)}s`;
  if (s < 5400) return `há ${Math.round(s / 60)} min`;
  if (s < 172800) return `há ${Math.round(s / 3600)} h`;
  return `há ${Math.round(s / 86400)} dias`;
}

/** Segundos → português. Sem `(s)`, sem `min`, sem `h`: "1 dia", "7 dias", "6 horas". */
function duracaoHumana(s: number | null | undefined): string | null {
  if (s == null || !Number.isFinite(s) || s <= 0) return null;
  if (s >= 86400) { const n = Math.round(s / 86400); return `${n} ${n === 1 ? 'dia' : 'dias'}`; }
  if (s >= 3600) { const n = Math.round(s / 3600); return `${n} ${n === 1 ? 'hora' : 'horas'}`; }
  const n = Math.max(1, Math.round(s / 60));
  return `${n} ${n === 1 ? 'minuto' : 'minutos'}`;
}

/** O ritmo esperado, preferindo a frase que o backend já escreveu em português. */
function ritmo(humana: string | null | undefined, segundos: number | null | undefined): string | null {
  const doBackend = semJargao(humana);
  return doBackend || duracaoHumana(segundos);
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
      proposito: 'a medição entregou estes trabalhadores sem um grupo que exista — a tela não adota ninguém por conta própria',
      resumo: `${orfaos.length} ${orfaos.length === 1 ? 'trabalhador' : 'trabalhadores'} sem grupo declarado`,
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

// O olho vai ao problema antes de ler o resumo. Um grupo com ≥1 PARADO, ≥1
// PULSA SEM PRODUZIR ou ≥1 estado fora do contrato ganha, no título, a marca do
// PIOR estado que ele contém — ponto colorido E texto, porque cor sozinha não
// informa (DS-001 §13).
const ESTADOS_QUE_DOEM = ['__desconhecido__', 'PARADO', 'PULSA_SEM_PRODUZIR'];

function piorEstadoDoGrupo(g: GrupoNaTela): { chave: string; rotulo: string; cor: string } | null {
  const doem = g.agentes
    .map((a) => (ESTADOS[a.estado]
      ? { chave: a.estado, rotulo: ESTADOS[a.estado].rotulo, cor: ESTADOS[a.estado].cor, ordem: ESTADOS[a.estado].ordem }
      : { chave: '__desconhecido__', rotulo: DESCONHECIDO.rotulo, cor: DESCONHECIDO.cor, ordem: DESCONHECIDO.ordem }))
    .filter((x) => ESTADOS_QUE_DOEM.includes(x.chave))
    .sort((a, b) => a.ordem - b.ordem);
  return doem.length > 0 ? { chave: doem[0].chave, rotulo: doem[0].rotulo, cor: doem[0].cor } : null;
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

function CardAgente({ agente, grupoDoCard, agora, memoria, memAberta, aoAbrirMemoria, trabAberto, aoAbrirTrabalho }: {
  agente: Agente;
  grupoDoCard: string;
  agora: number;
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

  const prod = agente.producao;
  const pul = agente.pulso;
  // Rótulo humano do backend quando ele vier; rótulo genérico quando não vier.
  // Em NENHUM dos dois caminhos o nome da tabela chega à tela.
  const ondeMedeProducao = semJargao(prod?.fonte_rotulo) || rotuloHumano(prod?.fonte, 'a produção dele');
  const ondeMedePulso = semJargao(pul?.origem_rotulo) || rotuloHumano(pul?.origem, 'o laço dele');
  const ritmoProducao = prod ? ritmo(prod.cadencia_humana, prod.cadencia_esperada_s) : null;
  const ritmoPulso = pul ? ritmo(pul.cadencia_humana, null) : null;

  // 🔴 Desligado que executa é contradição, e contradição não fica dobrada.
  const execucoes24h = t && t.execucoes_24h != null ? t.execucoes_24h : 0;
  const contradicao = agente.estado === 'DESLIGADO' && execucoes24h > 0
    ? `executou ${execucoes24h} ${execucoes24h === 1 ? 'vez' : 'vezes'} nas últimas 24h`
    : null;

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
        <div style={{ fontSize: 12.5, color: '#8A93A3', lineHeight: 1.5 }}>{semJargao(agente.descricao)}</div>
      ) : null}

      {/* O motivo do estado, em uma frase. É o que responde "por que esta cor?". */}
      <div style={{ fontSize: 12, color: est.cor, lineHeight: 1.5, background: '#080B10', border: `1px solid ${est.cor}33`, borderRadius: 8, padding: '8px 10px' }}>
        {semJargao(agente.motivo) || 'não veio explicação para este estado'}
      </div>

      {contradicao ? (
        <div data-contradicao="1" style={{ fontSize: 12, color: '#E2A94F', lineHeight: 1.5, background: '#080B10', border: '1px solid #E2A94F44', borderRadius: 8, padding: '8px 10px' }}>
          está dado como desligado e mesmo assim {contradicao}
        </div>
      ) : null}

      {divergente ? (
        <div style={{ ...S.mono, fontSize: 10, color: '#E06B6B' }}>
          declara o grupo <span style={{ color: '#E7EBF1' }}>{agente.grupo}</span> e veio dentro de <span style={{ color: '#E7EBF1' }}>{grupoDoCard}</span>
        </div>
      ) : null}

      <div style={{ ...S.mono, fontSize: 10.5, color: '#5A6577', display: 'flex', flexDirection: 'column', gap: 3, borderTop: '1px solid #131A23', paddingTop: 8 }}>
        <span>
          deu sinal de vida <span style={{ color: pul?.ultimo ? '#A9B2C0' : CINZA_SEM_MEDIDA }}>{pul?.ultimo ? ago(pul.ultimo, agora) : 'nunca'}</span>
          {ondeMedePulso ? <span> · medido por {ondeMedePulso}</span> : null}
          {ritmoPulso ? <span> · esperado a cada {ritmoPulso}</span> : null}
        </span>
        <span>
          entregou trabalho <span style={{ color: prod?.ultimo ? '#A9B2C0' : CINZA_SEM_MEDIDA }}>{prod?.ultimo ? ago(prod.ultimo, agora) : 'nunca'}</span>
          {ritmoProducao ? <span> · esperado a cada {ritmoProducao}</span> : prod ? <span> · sem ritmo declarado</span> : null}
        </span>
        {ondeMedeProducao ? <span style={{ color: '#4A4F5A' }}>medido por {ondeMedeProducao}</span> : null}
        {agente.desligado?.declara ? (
          <span>
            desligado{agente.desligado.todas_desligadas ? ' em todas as corretoras' : ''}
            {agente.desligado.desde ? ` · desde ${ago(agente.desligado.desde, agora)}` : ' · sem registro de quando'}
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
  const [decisaoAberta, setDecisaoAberta] = useState(false);

  const grupos = montarGrupos(status);
  const linhas = contarPorEstado(grupos);
  const total = linhas.reduce((a, b) => a + b.n, 0);

  // O "agora" dos cards: o instante da MEDIÇÃO. Sem `gerado_em`, o relógio local
  // é o que sobra — e aí o card admite isso mostrando idade a partir dele.
  const medidoEm = status?.gerado_em ? new Date(status.gerado_em).getTime() : NaN;
  const agora = Number.isFinite(medidoEm) ? medidoEm : Date.now();
  const foraPorDecisao = (status && status.sem_card_por_decisao) || [];

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
        {/* Esta é a ÚNICA idade que se conta pelo relógio do navegador: ela responde
            "quão velha está a página na minha frente?", e não "quando o agente produziu". */}
        {status?.gerado_em ? (
          <span>
            medido {ago(status.gerado_em, Date.now())}
            {duracaoHumana(status.cache_s) ? ` · remedido a cada ${duracaoHumana(status.cache_s)}` : ''}
          </span>
        ) : null}
        {carregando ? <span>carregando…</span> : null}
      </div>

      {erro ? (
        <div style={{ ...S.card, marginTop: 14, borderColor: '#E06B6B55', color: '#E06B6B', fontSize: 12.5 }}>{erro}</div>
      ) : null}

      {!erro && !carregando && grupos.length === 0 ? (
        <div style={{ ...S.card, marginTop: 14, borderColor: '#E06B6B55', color: '#E06B6B', fontSize: 12.5 }}>
          A medição não devolveu nenhum grupo. Isto é um defeito da medição, não uma casa vazia.
        </div>
      ) : null}

      {grupos.map((g) => {
        const pior = piorEstadoDoGrupo(g);
        return (
        <div key={g.id} style={{ marginTop: 22 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ ...S.mono, fontSize: 12, letterSpacing: '0.1em', color: g.sintetico ? '#E06B6B' : '#A9B2C0' }}>{g.titulo}</span>
            {pior ? (
              <span data-pior-estado={pior.chave} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, ...S.mono, fontSize: 9.5, letterSpacing: '0.08em', color: pior.cor }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: pior.cor }} />
                {pior.rotulo} AQUI DENTRO
              </span>
            ) : null}
            {g.proposito ? <span style={{ fontSize: 12, color: '#5A6577' }}>{semJargao(g.proposito)}</span> : null}
          </div>
          <div style={{ ...S.mono, fontSize: 11, color: g.sintetico ? '#E06B6B' : '#7C8798', marginTop: 5 }}>
            {semJargao(g.resumo) || 'sem resumo'} <span style={{ color: '#4A4F5A' }}>· {g.agentes.length} cards nesta tela</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12, marginTop: 11 }}>
            {g.agentes.map((a) => {
              // Abre por padrão quando dói OU quando houve execução — o trabalho de
              // um ⚪ que roda não pode ficar atrás de um triângulo fechado.
              const padraoAberto = ehProblema(a.estado) || trabalhouRecentemente(a.trabalho);
              const chave = `${g.id}:${a.id}`;
              const aberto = trabalhoTocado[chave] === undefined ? padraoAberto : trabalhoTocado[chave];
              return (
                <CardAgente
                  key={chave}
                  agente={a}
                  grupoDoCard={g.id}
                  agora={agora}
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
        );
      })}

      {/* O rodapé do que a tela NÃO mede. Sem ele, um zero silencioso vira fato.
          Mas 14 itens em prosa corrida NINGUÉM lê: o que saiu por decisão fica
          DOBRADO com a contagem à vista, e aberto vira uma linha por item. */}
      <div style={{ marginTop: 26, borderTop: '1px solid #131A23', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 7, ...S.mono, fontSize: 10, color: '#4A4F5A' }}>
        {status && status.nao_instrumentado && status.nao_instrumentado.length > 0 ? (
          <span>esta tela ainda não mede: {status.nao_instrumentado.map(nomeDoQueFalta).join(' · ')}</span>
        ) : null}
        {foraPorDecisao.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span
              role="button"
              tabIndex={0}
              onClick={() => setDecisaoAberta(!decisaoAberta)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setDecisaoAberta(!decisaoAberta); }}
              style={{ cursor: 'pointer', color: '#5A6577', letterSpacing: '0.06em' }}
            >
              {decisaoAberta ? '▾' : '▸'} fora da tela por decisão ({foraPorDecisao.length})
            </span>
            {decisaoAberta ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, paddingLeft: 12 }}>
                {foraPorDecisao.map((d) => (
                  <span key={d.workflow_key}>
                    <span style={{ color: '#7C8798' }}>{d.workflow_key}</span>
                    <span> — {semJargao(d.motivo)}</span>
                  </span>
                ))}
              </div>
            ) : null}
          </div>
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
