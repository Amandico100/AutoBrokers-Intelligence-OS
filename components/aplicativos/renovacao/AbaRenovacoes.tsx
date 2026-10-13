'use client';

// ─────────────────────────────────────────────────────────────────────────────
// A ABA RENOVAÇÕES — o lugar onde o comercial confere e envia (SPEC-131-B · G2).
// ─────────────────────────────────────────────────────────────────────────────
//
// Carregada pela casca do aplicativo (`?aba=renovacoes`, contrato da G1). Celular
// primeiro: no telefone a lista vira cartões com UM botão "Enviar"; no notebook,
// a lista agrupada por dia de vencimento, com a linha que expande nos cálculos.
//
//   topo     4 atalhos-filtro (o número é a contagem do que ele mostra)
//   barra    Minhas · Todas · busca · filtros (no celular, "Filtros (n)" embaixo)
//            · Quadro × Lista
//   quadro   Vai calcular · Calculada · Enviada (+ 4 escondidas até alguém
//            chegar lá) — SEM arrastar: a coluna vem do estado
//   detalhe  `&item=<id>` — gaveta no notebook, tela cheia no celular
//
// 🔴 Todo filtro mora na URL (`escopo`, `atalho`, `estado`, `ramo`,
// `seguradora`, `periodo`, `q`, `item`): o link copiado abre igual, e "voltar"
// fecha o detalhe. ⛔ Nada sai daqui para o cliente sozinho.

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { RefreshCcwDot, Search, SlidersHorizontal, X } from 'lucide-react';
import { toast } from 'sonner';

import { QuadroOuLista, SeletorDeLeitura, useLeituraSalva } from '@/components/aplicativos/QuadroOuLista';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { DetalheDaRenovacaoGaveta } from './DetalheDaRenovacao';
import { CardDaRenovacao, LinhaDaRenovacao } from './PecasDaRenovacao';
import {
  ATALHOS,
  COLUNAS_DA_RENOVACAO,
  tituloDoDia,
  type Atalho,
  type ListaDeRenovacoes,
  type Renovacao,
} from './tipos';
import { useAcoesDaRenovacao } from './useAcoesDaRenovacao';

const PREFERENCIA_DE_LEITURA = 'autobrokers.aplicativos.renovacao.leitura';

const PERIODOS = [
  { id: '', rotulo: 'Todo o período' },
  { id: 'hoje', rotulo: 'Vence hoje' },
  { id: '7d', rotulo: 'Próximos 7 dias' },
  { id: '30d', rotulo: 'Próximos 30 dias' },
] as const;

const ESTADOS_DO_FILTRO = [
  { id: '', rotulo: 'Todos os estados' },
  ...COLUNAS_DA_RENOVACAO.map((c) => ({ id: c.id, rotulo: c.titulo })),
];

/** AAAA-MM-DD do dia LOCAL de quem olha (a renovação vence num dia do calendário). */
function diaLocal(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function intervaloDoPeriodo(periodo: string): { de?: string; ate?: string } {
  const hoje = new Date();
  const mais = (n: number) => diaLocal(new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + n));
  if (periodo === 'hoje') return { de: mais(0), ate: mais(0) };
  if (periodo === '7d') return { de: mais(0), ate: mais(7) };
  if (periodo === '30d') return { de: mais(0), ate: mais(30) };
  return {};
}

export default function AbaRenovacoes() {
  return (
    <Suspense fallback={<Carregando />}>
      <AbaRenovacoesConteudo />
    </Suspense>
  );
}

export { AbaRenovacoes };

function AbaRenovacoesConteudo() {
  const router = useRouter();
  const pathname = usePathname();
  const busca = useSearchParams();

  const escopoNaUrl = busca.get('escopo');
  const atalho = (busca.get('atalho') || '') as Atalho | '';
  const estado = busca.get('estado') || '';
  const ramo = busca.get('ramo') || '';
  const seguradora = busca.get('seguradora') || '';
  const periodo = busca.get('periodo') || '';
  const q = busca.get('q') || '';
  const item = busca.get('item');

  const [dados, setDados] = useState<ListaDeRenovacoes | null>(null);
  const [erro, setErro] = useState(false);
  const [recarga, setRecarga] = useState(0);
  const [abertas, setAbertas] = useState<Set<string>>(new Set());
  const [filtrosNoCelular, setFiltrosNoCelular] = useState(false);
  const [leitura, escolherLeitura] = useLeituraSalva(PREFERENCIA_DE_LEITURA, 'lista');
  const [textoDaBusca, setTextoDaBusca] = useState(q);
  const abriuPorAqui = useRef(false);

  /** Troca parâmetros da URL sem rolar a página e sem perder os outros (inclusive `aba`). */
  const mudar = useCallback(
    (novos: Record<string, string | null>, modo: 'replace' | 'push' = 'replace') => {
      const p = new URLSearchParams(busca.toString());
      for (const [k, v] of Object.entries(novos)) {
        if (v) p.set(k, v);
        else p.delete(k);
      }
      const url = `${pathname}?${p.toString()}`;
      if (modo === 'push') router.push(url, { scroll: false });
      else router.replace(url, { scroll: false });
    },
    [busca, pathname, router],
  );

  // a busca vai à URL depois de uma pausa na digitação
  useEffect(() => setTextoDaBusca(q), [q]);
  useEffect(() => {
    if (textoDaBusca === q) return;
    const t = setTimeout(() => mudar({ q: textoDaBusca.trim() || null }), 350);
    return () => clearTimeout(t);
  }, [textoDaBusca, q, mudar]);

  const consulta = useMemo(() => {
    const p = new URLSearchParams();
    if (escopoNaUrl === 'minhas' || escopoNaUrl === 'todas') p.set('escopo', escopoNaUrl);
    if (estado) p.set('estado', estado);
    if (ramo) p.set('ramo', ramo);
    if (seguradora) p.set('seguradora', seguradora);
    if (q) p.set('q', q);
    const { de, ate } = intervaloDoPeriodo(periodo);
    if (de) p.set('de', de);
    if (ate) p.set('ate', ate);
    return p.toString();
  }, [escopoNaUrl, estado, ramo, seguradora, q, periodo]);

  useEffect(() => {
    let vivo = true;
    setErro(false);
    fetch(`/api/renovacoes?${consulta}`, { cache: 'no-store' })
      .then(async (res) => {
        const j = await res.json().catch(() => null);
        if (!vivo) return;
        if (!res.ok || !j) {
          setErro(true);
          return;
        }
        setDados(j as ListaDeRenovacoes);
      })
      .catch(() => vivo && setErro(true));
    return () => {
      vivo = false;
    };
  }, [consulta, recarga]);

  const recarregar = useCallback(() => setRecarga((n) => n + 1), []);
  const acoes = useAcoesDaRenovacao(recarregar);

  // o resultado de uma ação feita FORA do detalhe (na linha, no cartão) vira um aviso curto
  useEffect(() => {
    const r = acoes.resultado;
    if (!r || r.id === item) return;
    if (r.r.tipo === 'sem_telefone') {
      toast('Não achamos o celular deste cliente no cadastro.', {
        description: 'Abra a renovação e use "Copiar a mensagem".',
      });
    } else if (r.r.tipo === 'copiado') toast('Mensagem copiada. Cole no WhatsApp do cliente.');
    else if (r.r.tipo === 'erro') toast(r.r.mensagem);
    else if (r.r.tipo === 'copiar_a_mao') toast('O navegador não deixou copiar. Abra a renovação para copiar.');
  }, [acoes.resultado, item]);

  const escopo = dados?.escopo || (escopoNaUrl === 'todas' ? 'todas' : 'minhas');
  const itensDoFiltro = useMemo(() => dados?.itens || [], [dados]);
  const visiveis = useMemo(
    () => (atalho ? itensDoFiltro.filter((i) => i.atalhos.includes(atalho)) : itensDoFiltro),
    [itensDoFiltro, atalho],
  );

  const abrir = (r: Renovacao) => {
    abriuPorAqui.current = true;
    acoes.limpar();
    mudar({ item: r.id }, 'push');
  };
  const fechar = () => {
    if (abriuPorAqui.current) {
      abriuPorAqui.current = false;
      router.back();
    } else mudar({ item: null });
  };
  const alternar = (id: string) =>
    setAbertas((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const filtrosAtivos = [estado, ramo, seguradora, periodo].filter(Boolean).length;
  const algumFiltro = filtrosAtivos > 0 || Boolean(q) || Boolean(atalho);
  const limparFiltros = () =>
    mudar({ estado: null, ramo: null, seguradora: null, periodo: null, q: null, atalho: null });

  return (
    <div className="space-y-4 pb-10">
      {/* ───────────── OS ATALHOS ───────────── */}
      <div
        role="group"
        aria-label="Atalhos"
        className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-4 sm:overflow-visible sm:px-0"
      >
        {ATALHOS.map((a) => {
          const ativo = atalho === a.id;
          const n = dados?.contagens?.[a.id];
          return (
            <button
              key={a.id}
              type="button"
              aria-pressed={ativo}
              onClick={() => mudar({ atalho: ativo ? null : a.id })}
              className={cn(
                'flex min-h-11 shrink-0 items-center gap-2 rounded-xl border px-3.5 py-2 text-left transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                ativo
                  ? 'border-primary/60 bg-brand-soft text-foreground'
                  : 'border-border bg-surface text-foreground-2 hover:border-primary/40',
              )}
            >
              <span
                className={cn(
                  'text-xl font-semibold tabular-nums',
                  a.id === 'precisa_de_voce' && (n || 0) > 0 ? 'text-warning' : 'text-foreground',
                )}
              >
                {typeof n === 'number' ? n : '–'}
              </span>
              <span className="whitespace-nowrap text-sm font-medium">{a.rotulo}</span>
            </button>
          );
        })}
      </div>

      {/* ───────────── A BARRA ───────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label="De quem" className="inline-flex rounded-lg border border-border bg-surface p-0.5">
          {(
            [
              ['minhas', 'Minhas'],
              ['todas', 'Todas'],
            ] as const
          ).map(([v, rot]) => (
            <button
              key={v}
              type="button"
              aria-pressed={escopo === v}
              onClick={() => mudar({ escopo: v })}
              className={cn(
                'h-9 rounded-md px-3 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                escopo === v ? 'bg-brand-soft text-primary' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {rot}
            </button>
          ))}
        </div>

        <label className="relative order-last w-full sm:order-none sm:w-64">
          <span className="sr-only">Buscar por nome ou CPF</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="search"
            value={textoDaBusca}
            onChange={(e) => setTextoDaBusca(e.target.value)}
            placeholder="Nome ou CPF"
            className="h-11 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none sm:h-10"
          />
        </label>

        <div className="hidden items-center gap-2 lg:flex">
          <Filtros
            dados={dados}
            estado={estado}
            ramo={ramo}
            seguradora={seguradora}
            periodo={periodo}
            mudar={mudar}
          />
        </div>

        <button
          type="button"
          onClick={() => setFiltrosNoCelular(true)}
          className="inline-flex h-11 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-foreground-2 lg:hidden"
        >
          <SlidersHorizontal className="h-4 w-4" aria-hidden />
          Filtros{filtrosAtivos > 0 ? ` (${filtrosAtivos})` : ''}
        </button>

        <span className="hidden flex-1 sm:block" />
        <SeletorDeLeitura leitura={leitura} onEscolher={escolherLeitura} />
      </div>

      {algumFiltro && (
        <button
          type="button"
          onClick={limparFiltros}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg px-1 text-sm font-medium text-primary hover:underline"
        >
          <X className="h-4 w-4" aria-hidden />
          Limpar filtros
        </button>
      )}

      {/* ───────────── O CONTEÚDO ───────────── */}
      {erro && !dados && (
        <div className="rounded-xl border border-border bg-surface p-8 text-center">
          <p className="text-base font-medium text-foreground">Não conseguimos carregar as renovações agora.</p>
          <button
            type="button"
            onClick={recarregar}
            className="mt-3 inline-flex h-11 items-center rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2"
          >
            Tentar de novo
          </button>
        </div>
      )}

      {!erro && !dados && <Carregando />}

      {dados && visiveis.length === 0 && (
        <Vazio
          dados={dados}
          atalho={atalho}
          outrosFiltros={filtrosAtivos > 0 || Boolean(q)}
          limpar={limparFiltros}
          verTodas={() => mudar({ escopo: 'todas' })}
          escopo={escopo}
        />
      )}

      {dados && visiveis.length > 0 && (
        <QuadroOuLista
          leitura={leitura}
          itens={visiveis}
          colunas={COLUNAS_DA_RENOVACAO}
          colunaDe={(r) => r.coluna}
          chave={(r) => r.id}
          Card={(r) => <CardDaRenovacao r={r} onAbrir={abrir} />}
          Linha={(r) => (
            <LinhaDaRenovacao r={r} aberta={abertas.has(r.id)} onAlternar={alternar} onAbrir={abrir} acoes={acoes} />
          )}
          lista={
            <ListaPorDia
              itens={visiveis}
              hoje={dados.hoje}
              render={(r) => (
                <LinhaDaRenovacao
                  r={r}
                  aberta={abertas.has(r.id)}
                  onAlternar={alternar}
                  onAbrir={abrir}
                  acoes={acoes}
                />
              )}
            />
          }
          maisNaColuna={(restantes) => (
            <button
              type="button"
              onClick={() => escolherLeitura('lista')}
              className="px-0.5 pt-1 text-left text-xs font-medium text-primary hover:underline"
            >
              e mais {restantes} — ver na lista
            </button>
          )}
        />
      )}

      {/* ───────────── OS FILTROS NO CELULAR ───────────── */}
      <Sheet open={filtrosNoCelular} onOpenChange={setFiltrosNoCelular}>
        <SheetContent side="bottom" className="max-h-[85dvh] overflow-y-auto rounded-t-2xl pb-[max(1rem,env(safe-area-inset-bottom))]">
          <SheetTitle>Filtros</SheetTitle>
          <SheetDescription>Escolha o que quer ver. A lista muda na hora.</SheetDescription>
          <div className="mt-4 grid gap-3">
            <Filtros
              dados={dados}
              estado={estado}
              ramo={ramo}
              seguradora={seguradora}
              periodo={periodo}
              mudar={mudar}
              grande
            />
          </div>
          <button
            type="button"
            onClick={() => setFiltrosNoCelular(false)}
            className="mt-4 inline-flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground"
          >
            Ver {visiveis.length === 1 ? '1 renovação' : `${visiveis.length} renovações`}
          </button>
        </SheetContent>
      </Sheet>

      <DetalheDaRenovacaoGaveta id={item} versao={recarga} onFechar={fechar} acoes={acoes} />
    </div>
  );
}

function Filtros({
  dados,
  estado,
  ramo,
  seguradora,
  periodo,
  mudar,
  grande,
}: {
  dados: ListaDeRenovacoes | null;
  estado: string;
  ramo: string;
  seguradora: string;
  periodo: string;
  mudar: (n: Record<string, string | null>) => void;
  grande?: boolean;
}) {
  const classe = cn(
    'rounded-lg border border-border bg-surface px-2.5 text-sm text-foreground focus:border-primary focus:outline-none',
    grande ? 'h-11 w-full' : 'h-10',
  );
  return (
    <>
      <label className={cn(grande && 'grid gap-1')}>
        <span className={grande ? 'text-sm font-medium text-foreground' : 'sr-only'}>Vencimento</span>
        <select className={classe} value={periodo} onChange={(e) => mudar({ periodo: e.target.value || null })}>
          {PERIODOS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.rotulo}
            </option>
          ))}
        </select>
      </label>
      <label className={cn(grande && 'grid gap-1')}>
        <span className={grande ? 'text-sm font-medium text-foreground' : 'sr-only'}>Ramo</span>
        <select className={classe} value={ramo} onChange={(e) => mudar({ ramo: e.target.value || null })}>
          <option value="">Todos os ramos</option>
          {(dados?.ramos || []).map((r) => (
            <option key={r.id} value={r.id}>
              {r.rotulo}
            </option>
          ))}
        </select>
      </label>
      <label className={cn(grande && 'grid gap-1')}>
        <span className={grande ? 'text-sm font-medium text-foreground' : 'sr-only'}>Seguradora atual</span>
        <select
          className={classe}
          value={seguradora}
          onChange={(e) => mudar({ seguradora: e.target.value || null })}
        >
          <option value="">Todas as seguradoras</option>
          {(dados?.seguradoras || []).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label className={cn(grande && 'grid gap-1')}>
        <span className={grande ? 'text-sm font-medium text-foreground' : 'sr-only'}>Estado</span>
        <select className={classe} value={estado} onChange={(e) => mudar({ estado: e.target.value || null })}>
          {ESTADOS_DO_FILTRO.map((s) => (
            <option key={s.id} value={s.id}>
              {s.rotulo}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

/** A lista agrupada por DIA DE VENCIMENTO, com o cabeçalho do dia grudado enquanto se rola. */
function ListaPorDia({
  itens,
  hoje,
  render,
}: {
  itens: Renovacao[];
  hoje: string;
  render: (r: Renovacao) => React.ReactNode;
}) {
  const grupos = useMemo(() => {
    const mapa = new Map<string, Renovacao[]>();
    for (const r of itens) {
      const k = r.vence_em || '';
      if (!mapa.has(k)) mapa.set(k, []);
      mapa.get(k)!.push(r);
    }
    return Array.from(mapa.entries());
  }, [itens]);
  return (
    <div className="space-y-5">
      {grupos.map(([dia, lista]) => (
        <section key={dia || 'sem-data'} aria-label={tituloDoDia(dia || null, hoje)}>
          <h3 className="sticky top-[var(--altura-das-abas,45px)] z-10 -mx-1 mb-2 flex items-baseline gap-2 bg-background/95 px-1 py-1.5 text-sm font-semibold text-foreground sm:backdrop-blur">
            {tituloDoDia(dia || null, hoje)}
            <span className="text-xs font-normal text-muted-foreground tabular-nums">
              {lista.length === 1 ? '1 renovação' : `${lista.length} renovações`}
            </span>
          </h3>
          <div className="space-y-2">
            {lista.map((r) => (
              <div key={r.id}>{render(r)}</div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function Carregando() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Carregando as renovações">
      {Array.from({ length: 6 }).map((_, k) => (
        <Skeleton key={k} className="h-16 w-full rounded-xl" />
      ))}
    </div>
  );
}

/** Os estados vazios, em português de gente (DS-001 §8.9). */
function Vazio({
  dados,
  atalho,
  outrosFiltros,
  limpar,
  verTodas,
  escopo,
}: {
  dados: ListaDeRenovacoes;
  atalho: Atalho | '';
  outrosFiltros: boolean;
  limpar: () => void;
  verTodas: () => void;
  escopo: 'minhas' | 'todas';
}) {
  let titulo: string;
  let texto: React.ReactNode = null;
  let acao: React.ReactNode = null;
  if (!dados.tem_alguma) {
    titulo = 'Nenhuma renovação ainda';
    texto = dados.ligado ? (
      'A madrugada prepara as renovações dos próximos dias e elas aparecem aqui antes das 7h.'
    ) : (
      <>
        Quando o aplicativo estiver ligado, a madrugada calcula as renovações dos próximos dias e elas aparecem aqui
        antes das 7h. Ligue o aplicativo em{' '}
        <Link href="?aba=inicio" className="font-medium text-primary hover:underline">
          Início → Como começar
        </Link>
        .
      </>
    );
  } else if (atalho && !outrosFiltros) {
    titulo = ATALHOS.find((a) => a.id === atalho)?.vazio || 'Nada aqui agora.';
  } else if (outrosFiltros) {
    titulo = 'Nenhuma renovação com esses filtros.';
    acao = (
      <button
        type="button"
        onClick={limpar}
        className="mt-3 inline-flex h-11 items-center rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2"
      >
        Limpar filtros
      </button>
    );
  } else if (escopo === 'minhas') {
    titulo = 'Nenhuma renovação sua agora';
    texto = 'As renovações em que você é o dono ou o responsável aparecem aqui.';
    acao = (
      <button
        type="button"
        onClick={verTodas}
        className="mt-3 inline-flex h-11 items-center rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2"
      >
        Ver todas da corretora
      </button>
    );
  } else {
    titulo = 'Nenhuma renovação no período';
  }
  return (
    <div className="rounded-xl border border-border bg-surface p-8 text-center">
      <RefreshCcwDot className="mx-auto h-8 w-8 text-muted-foreground" strokeWidth={1.6} aria-hidden />
      <p className="mt-3 text-base font-medium text-foreground">{titulo}</p>
      {texto && <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-muted-foreground">{texto}</p>}
      {acao}
    </div>
  );
}
