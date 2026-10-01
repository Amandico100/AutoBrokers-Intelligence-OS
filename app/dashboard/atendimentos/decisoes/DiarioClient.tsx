'use client';

// ─────────────────────────────────────────────────────────────────────────────
// DECISÕES DO AGENTE — o diário (SPEC-123 F4 · D7 do Founder).
// ─────────────────────────────────────────────────────────────────────────────
//
// Quando o roteiro fixo trava no WhatsApp da seguradora, o agente agora decide
// sozinho para destravar. Cada decisão vira UMA linha aqui, em português de gente:
// o que a seguradora perguntou, o que o agente fez, por quê, com que certeza e o
// que aconteceu depois. A corretora diz "certo" ou "errado" — e "errado" pede o
// que era o certo, porque é isso que ensina.
//
// 📱 MOBILE-FIRST (DS-001 §6.2): filtros GRUDADOS no topo, linha em cartão (nunca
// tabela), botões grandes o bastante para o polegar. Linguagem sem jargão (§6.7):
// nenhum nome de classe, de variável ou de modelo aparece na tela.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Loader2, NotebookPen, TriangleAlert, X } from 'lucide-react';

import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Decisao {
  id: string;
  quando: string;
  seguradora: string;
  ramo: string;
  servico: string;
  classe: string;
  acao: string;
  nota: number | null;
  modo: string;
  frase: string;
  tela: string;
  valor: string;
  segunda_opiniao_concordou: boolean | null;
  resultado: string;
  veredito: 'certo' | 'errado' | null;
  o_certo_era: string | null;
  sugere_regra: boolean;
  avaliado_em: string | null;
}

interface Payload {
  items: Decisao[];
  cursor: string | null;
  has_more: boolean;
}

const VEREDITOS = [
  { id: 'sem', label: 'Sem avaliação' },
  { id: 'certo', label: 'Certo' },
  { id: 'errado', label: 'Errado' },
  { id: 'todas', label: 'Todas' },
];

/** O nome da classe NUNCA aparece: aparece o que ela quer dizer. */
const CLASSES: { id: string; label: string }[] = [
  { id: '', label: 'Todo tipo de decisão' },
  { id: 'conduzir', label: 'Conduziu' },
  { id: 'responder_com_dado', label: 'Respondeu com dado do caso' },
  { id: 'deduzir', label: 'Deduziu' },
  { id: 'perguntar_ao_segurado', label: 'Perguntou ao segurado' },
  { id: 'nunca_sozinho', label: 'Chamou uma pessoa' },
];
const ROTULO_DA_CLASSE: Record<string, string> = Object.fromEntries(
  CLASSES.filter((c) => c.id).map((c) => [c.id, c.label]),
);

const FAIXAS = [
  { id: '', label: 'Qualquer certeza' },
  { id: '70-80', label: 'Certeza 70–80%' },
  { id: '80-90', label: 'Certeza 80–90%' },
  { id: '90-100', label: 'Certeza 90–100%' },
];

const PERIODOS = [
  { id: '7', label: 'Últimos 7 dias' },
  { id: '30', label: 'Últimos 30 dias' },
  { id: '90', label: 'Últimos 90 dias' },
  { id: '', label: 'Desde o começo' },
];

const O_QUE_ACONTECEU: Record<string, string> = {
  pendente: 'Ainda em andamento.',
  protocolo_saiu: 'Depois disso, o protocolo saiu.',
  seguradora_recusou: 'Depois disso, a seguradora recusou o pedido.',
  humano_corrigiu: 'Depois disso, uma pessoa da corretora corrigiu o rumo.',
  ura_fechou: 'Depois disso, a central da seguradora encerrou a conversa.',
};

function nomeDaSeguradora(chave: string): string {
  const s = String(chave || '').trim();
  if (!s) return 'Seguradora';
  return s.length <= 3 ? s.toUpperCase() : s.charAt(0).toUpperCase() + s.slice(1);
}

/** `{PLACA}` → `[placa]`: a marca do mascarador vira palavra. */
function semMarcas(texto: string): string {
  return String(texto || '').replace(/\{([A-Z][A-Z_]*)(?::[\w-]+)?\}/g, (_, n: string) => `[${n.toLowerCase().replace(/_/g, ' ')}]`);
}

function quando(iso: string): string {
  try {
    return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export default function DiarioClient() {
  const [items, setItems] = useState<Decisao[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [temMais, setTemMais] = useState(false);
  const [erro, setErro] = useState(false);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [veredito, setVeredito] = useState('sem');
  const [classe, setClasse] = useState('');
  const [faixa, setFaixa] = useState('');
  const [periodo, setPeriodo] = useState('30');
  const [seguradora, setSeguradora] = useState('');
  const [seguradorasVistas, setSeguradorasVistas] = useState<string[]>([]);
  const [tentativa, setTentativa] = useState(0);
  const pedido = useRef(0);

  const url = useCallback(
    (depoisDe?: string | null) => {
      const p = new URLSearchParams();
      p.set('veredito', veredito);
      if (classe) p.set('classe', classe);
      if (faixa) p.set('faixa', faixa);
      if (seguradora) p.set('seguradora', seguradora);
      if (periodo) p.set('desde', new Date(Date.now() - Number(periodo) * 86400000).toISOString());
      if (depoisDe) p.set('cursor', depoisDe);
      return `/api/dashboard/decisoes?${p.toString()}`;
    },
    [veredito, classe, faixa, seguradora, periodo],
  );

  useEffect(() => {
    const meu = pedido.current + 1;
    pedido.current = meu;
    setItems(null);
    setErro(false);
    (async () => {
      try {
        const res = await fetch(url(), { cache: 'no-store' });
        if (pedido.current !== meu) return;
        if (!res.ok) { setErro(true); setItems([]); return; }
        const j: Payload = await res.json();
        setItems(j.items || []);
        setCursor(j.cursor);
        setTemMais(Boolean(j.has_more));
        setSeguradorasVistas((antes) => Array.from(new Set([...antes, ...(j.items || []).map((i) => i.seguradora).filter(Boolean)])).sort());
      } catch {
        if (pedido.current === meu) { setErro(true); setItems([]); }
      }
    })();
  }, [url, tentativa]);

  const carregarMais = async () => {
    if (!cursor || carregandoMais) return;
    setCarregandoMais(true);
    try {
      const res = await fetch(url(cursor), { cache: 'no-store' });
      if (res.ok) {
        const j: Payload = await res.json();
        setItems((atual) => [...(atual || []), ...(j.items || [])]);
        setCursor(j.cursor);
        setTemMais(Boolean(j.has_more));
      }
    } finally {
      setCarregandoMais(false);
    }
  };

  const lista = useMemo(() => items || [], [items]);
  const atualizar = (d: Decisao) => setItems((atual) => (atual || []).map((i) => (i.id === d.id ? d : i)));

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.aprovacao}
          title="Decisões do agente"
          subtitle="Quando o atendimento travou, o agente decidiu sozinho. Diga se ele acertou — é assim que ele aprende."
          breadcrumb={[
            { label: 'Atendimentos', href: '/dashboard/atendimentos' },
            { label: 'Decisões do agente' },
          ]}
        />

        {/* 📱 Os filtros GRUDAM no topo (o mesmo desenho de Casos). */}
        <div className="sticky top-0 z-20 -mx-4 mt-4 space-y-2 bg-background/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6">
          <div className="flex gap-2 overflow-x-auto pb-0.5">
            {VEREDITOS.map((f) => (
              <button
                key={f.id}
                onClick={() => setVeredito(f.id)}
                aria-pressed={veredito === f.id}
                className={cn(
                  'shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
                  veredito === f.id
                    ? 'border-primary/50 bg-brand-soft text-primary'
                    : 'border-border bg-surface text-muted-foreground hover:text-foreground',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Seletor rotulo="Tipo de decisão" valor={classe} onChange={setClasse} opcoes={CLASSES} />
            <Seletor rotulo="Certeza" valor={faixa} onChange={setFaixa} opcoes={FAIXAS} />
            <Seletor
              rotulo="Seguradora"
              valor={seguradora}
              onChange={setSeguradora}
              opcoes={[{ id: '', label: 'Todas as seguradoras' }, ...seguradorasVistas.map((s) => ({ id: s, label: nomeDaSeguradora(s) }))]}
            />
            <Seletor rotulo="Período" valor={periodo} onChange={setPeriodo} opcoes={PERIODOS} />
          </div>
        </div>

        <div className="mt-3 space-y-3">
          {erro && (
            <div className="rounded-xl border border-warning/40 bg-surface p-4 text-sm">
              <p className="flex items-center gap-1.5 font-medium text-foreground">
                <TriangleAlert className="h-4 w-4 shrink-0 text-warning" />
                Não conseguimos carregar as decisões agora.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Tente novamente em alguns instantes.</p>
              <button
                onClick={() => setTentativa((t) => t + 1)}
                className="mt-3 rounded-lg border border-border px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-2"
              >
                Tentar de novo
              </button>
            </div>
          )}

          {items === null ? (
            <div className="space-y-2" aria-busy>
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-[148px] animate-pulse rounded-xl border border-border bg-surface-2/50" />
              ))}
            </div>
          ) : !erro && lista.length === 0 ? (
            <div className="rounded-xl border border-border bg-surface p-8 text-center">
              <NotebookPen className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm font-medium text-foreground">
                {veredito === 'sem' ? 'Nenhuma decisão esperando sua avaliação' : 'Nada por aqui com esses filtros'}
              </p>
              <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
                {veredito === 'sem'
                  ? 'Quando o agente decidir sozinho para destravar um atendimento, a decisão aparece aqui para você dizer se ele acertou.'
                  : 'Troque o período ou o tipo de decisão para ver mais.'}
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                {lista.map((d) => (
                  <LinhaDaDecisao key={d.id} d={d} onAvaliada={atualizar} onConflito={() => setTentativa((t) => t + 1)} />
                ))}
              </div>
              {temMais && (
                <button
                  onClick={carregarMais}
                  disabled={carregandoMais}
                  className="mx-auto flex w-full max-w-xs items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  {carregandoMais && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Carregar mais decisões
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Seletor({ rotulo, valor, onChange, opcoes }: {
  rotulo: string; valor: string; onChange: (v: string) => void; opcoes: { id: string; label: string }[];
}) {
  return (
    <label className="relative block">
      <span className="sr-only">{rotulo}</span>
      <select
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="w-full appearance-none rounded-lg border border-border bg-surface py-2 pl-3 pr-8 text-xs text-foreground outline-none focus:border-primary/50"
      >
        {opcoes.map((o) => (
          <option key={o.id || 'todos'} value={o.id}>{o.label}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
    </label>
  );
}

function LinhaDaDecisao({ d, onAvaliada, onConflito }: {
  d: Decisao; onAvaliada: (d: Decisao) => void; onConflito: () => void;
}) {
  const [abrindoErrado, setAbrindoErrado] = useState(false);
  const [oCertoEra, setOCertoEra] = useState('');
  const [pareceRegra, setPareceRegra] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [verTela, setVerTela] = useState(false);

  const enviar = async (veredito: 'certo' | 'errado') => {
    if (veredito === 'errado' && oCertoEra.trim().length < 3) {
      setAviso('Conte o que era o certo — é isso que ensina o agente.');
      return;
    }
    setSalvando(true);
    setAviso(null);
    try {
      const res = await fetch('/api/dashboard/decisoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: d.id, veredito, o_certo_era: oCertoEra.trim(), sugere_regra: pareceRegra }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.status === 409) {
        setAviso('Outra pessoa acabou de avaliar esta decisão. Atualizamos a lista.');
        onConflito();
        return;
      }
      if (!res.ok) {
        setAviso(j?.error || 'Não conseguimos salvar agora. Tente de novo em instantes.');
        return;
      }
      onAvaliada({
        ...d,
        veredito,
        o_certo_era: veredito === 'errado' ? oCertoEra.trim() : null,
        sugere_regra: veredito === 'errado' ? pareceRegra : false,
        avaliado_em: new Date().toISOString(),
      });
      setAbrindoErrado(false);
    } catch {
      setAviso('Não conseguimos salvar agora. Tente de novo em instantes.');
    } finally {
      setSalvando(false);
    }
  };

  return (
    <article className="rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{nomeDaSeguradora(d.seguradora)}</span>
        <span>·</span>
        <span>{quando(d.quando)}</span>
        {ROTULO_DA_CLASSE[d.classe] && (
          <span className="rounded-full border border-border px-2 py-0.5">{ROTULO_DA_CLASSE[d.classe]}</span>
        )}
        {d.modo === 'sombra' && (
          <span className="rounded-full border border-border px-2 py-0.5">Só observando — nada foi enviado</span>
        )}
      </div>

      <p className="mt-2 text-sm leading-relaxed text-foreground">{semMarcas(d.frase)}</p>
      <p className="mt-1.5 text-xs text-muted-foreground">{O_QUE_ACONTECEU[d.resultado] || ''}</p>

      {d.tela && (
        <button
          onClick={() => setVerTela((v) => !v)}
          className="mt-2 text-xs font-medium text-primary hover:underline"
          aria-expanded={verTela}
        >
          {verTela ? 'Esconder a mensagem da seguradora' : 'Ver a mensagem da seguradora'}
        </button>
      )}
      {verTela && (
        <pre className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-2/40 p-3 font-sans text-xs text-foreground">
          {semMarcas(d.tela)}
        </pre>
      )}

      {d.veredito ? (
        <div className={cn(
          'mt-3 rounded-lg border px-3 py-2 text-xs',
          d.veredito === 'certo' ? 'border-success/40 text-success' : 'border-danger/40 text-danger',
        )}>
          <p className="flex items-center gap-1.5 font-medium">
            {d.veredito === 'certo' ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
            {d.veredito === 'certo' ? 'Avaliada como certa.' : 'Avaliada como errada.'}
          </p>
          {d.veredito === 'errado' && d.o_certo_era && (
            <p className="mt-1 text-foreground">O certo era: {d.o_certo_era}</p>
          )}
          {d.veredito === 'errado' && d.sugere_regra && (
            <p className="mt-1 text-muted-foreground">Marcada como possível regra para outros casos.</p>
          )}
        </div>
      ) : (
        <div className="mt-3">
          {!abrindoErrado ? (
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => enviar('certo')}
                disabled={salvando}
                className="flex items-center justify-center gap-1.5 rounded-lg border border-success/40 px-3 py-2.5 text-sm font-medium text-success transition-colors hover:bg-success/10 disabled:opacity-60"
              >
                {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Certo
              </button>
              <button
                onClick={() => { setAbrindoErrado(true); setAviso(null); }}
                disabled={salvando}
                className="flex items-center justify-center gap-1.5 rounded-lg border border-danger/40 px-3 py-2.5 text-sm font-medium text-danger transition-colors hover:bg-danger/10 disabled:opacity-60"
              >
                <X className="h-4 w-4" />
                Errado
              </button>
            </div>
          ) : (
            <div className="space-y-2 rounded-lg border border-border p-3">
              <label className="block text-xs font-medium text-foreground" htmlFor={`certo-${d.id}`}>
                O certo era…
              </label>
              <textarea
                id={`certo-${d.id}`}
                value={oCertoEra}
                onChange={(e) => setOCertoEra(e.target.value)}
                rows={3}
                maxLength={1000}
                placeholder="Ex.: responder a opção 2, porque o segurado disse que o carro não liga."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary/50"
              />
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <input type="checkbox" checked={pareceRegra} onChange={(e) => setPareceRegra(e.target.checked)} className="h-4 w-4" />
                Parece uma regra — vale para outros casos iguais
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => { setAbrindoErrado(false); setAviso(null); }}
                  disabled={salvando}
                  className="rounded-lg border border-border px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground"
                >
                  Cancelar
                </button>
                <button
                  onClick={() => enviar('errado')}
                  disabled={salvando}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-danger/40 px-3 py-2.5 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                >
                  {salvando && <Loader2 className="h-4 w-4 animate-spin" />}
                  Salvar como errado
                </button>
              </div>
            </div>
          )}
          {aviso && <p className="mt-2 text-xs text-warning">{aviso}</p>}
        </div>
      )}
    </article>
  );
}
