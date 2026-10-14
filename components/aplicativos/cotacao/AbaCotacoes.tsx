'use client';

// ─────────────────────────────────────────────────────────────────────────────
// A ABA COTAÇÕES — o lugar onde o corretor revê e envia as cotações (SPEC-132-B · B3).
// ─────────────────────────────────────────────────────────────────────────────
//
// Carregada pela casca do aplicativo (`?aba=cotacoes`). Celular primeiro: cada
// cotação é um cartão (cliente · carro ou risco · estado · a melhor parcela ·
// quem pediu · quando), com UM botão "Enviar" quando está pronta; no notebook, os
// mesmos cartões numa grade mais larga.
//
//   topo     Prontas · Calculando · Sem resposta (o número é a contagem)
//   barra    Minhas · Todas · busca
//   detalhe  `&item=<id>` — gaveta no notebook, tela cheia no celular
//
// 🔴 Os filtros moram na URL (`escopo`, `estado`, `item`): o link copiado abre
// igual e "voltar" fecha o detalhe. A BUSCA (nome, placa ou CPF) é a exceção:
// fica só no estado da tela e vai à API no cabeçalho `x-cotacoes-busca` — NUNCA
// na URL (a query acaba no log de acesso e no histórico do navegador).
// ⛔ Nada sai daqui para o cliente sozinho.

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Calculator, Loader2, MessageCircle, Search, X } from 'lucide-react';
import { toast } from 'sonner';

import { Skeleton } from '@/components/ui/skeleton';
import { Selo } from '@/components/aplicativos/casca/Selo';
import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { cn } from '@/lib/utils';
import { CABECALHO_DA_BUSCA } from '@/app/api/cotacoes/pedido';

import { DetalheDaCotacaoGaveta } from './DetalheDaCotacao';
import {
  FILTROS_DE_ESTADO,
  nomeDoCliente,
  parcela,
  quando,
  reais,
  tomDoEstado,
  type Cotacao,
  type EstadoDaCotacao,
  type ListaDeCotacoes,
} from './tipos';
import { useAcoesDaCotacao } from './useAcoesDaCotacao';

/** Enquanto alguma cotação calcula, a lista relê sozinha a cada tanto. */
const RELEITURA_MS = 15_000;

export default function AbaCotacoes() {
  return (
    <Suspense fallback={<Carregando />}>
      <AbaCotacoesConteudo />
    </Suspense>
  );
}

export { AbaCotacoes };

function AbaCotacoesConteudo() {
  const router = useRouter();
  const pathname = usePathname();
  const busca = useSearchParams();

  const escopoNaUrl = busca.get('escopo');
  const estado = (busca.get('estado') || '') as EstadoDaCotacao | '';
  const item = busca.get('item');
  const buscaVelhaNaUrl = busca.has('q');

  const [dados, setDados] = useState<ListaDeCotacoes | null>(null);
  const [erro, setErro] = useState(false);
  const [recarga, setRecarga] = useState(0);
  const [textoDaBusca, setTextoDaBusca] = useState('');
  const [termo, setTermo] = useState('');
  const abriuPorAqui = useRef(false);

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

  // a busca vale depois de uma pausa na digitação — e fica SÓ no estado (nunca na URL)
  useEffect(() => {
    const t = setTimeout(() => setTermo(textoDaBusca.trim()), 350);
    return () => clearTimeout(t);
  }, [textoDaBusca]);
  useEffect(() => {
    if (buscaVelhaNaUrl) mudar({ q: null });
  }, [buscaVelhaNaUrl, mudar]);

  const consulta = useMemo(() => {
    const p = new URLSearchParams();
    if (escopoNaUrl === 'minhas' || escopoNaUrl === 'todas') p.set('escopo', escopoNaUrl);
    return p.toString();
  }, [escopoNaUrl]);

  useEffect(() => {
    let vivo = true;
    setErro(false);
    const cabecalhos: Record<string, string> = termo ? { [CABECALHO_DA_BUSCA]: encodeURIComponent(termo) } : {};
    fetch(`/api/cotacoes?${consulta}`, { cache: 'no-store', headers: cabecalhos })
      .then(async (res) => {
        const j = await res.json().catch(() => null);
        if (!vivo) return;
        if (!res.ok || !j) {
          setErro(true);
          return;
        }
        setDados(j as ListaDeCotacoes);
      })
      .catch(() => vivo && setErro(true));
    return () => {
      vivo = false;
    };
  }, [consulta, termo, recarga]);

  const recarregar = useCallback(() => setRecarga((n) => n + 1), []);
  const acoes = useAcoesDaCotacao(recarregar);

  const algumaCalculando = Boolean(dados?.itens.some((c) => c.estado === 'calculando'));
  useEffect(() => {
    if (!algumaCalculando) return;
    const t = setTimeout(recarregar, RELEITURA_MS);
    return () => clearTimeout(t);
  }, [algumaCalculando, recarga, recarregar]);

  // o resultado de uma ação feita FORA do detalhe (no cartão) vira um aviso curto
  useEffect(() => {
    const r = acoes.resultado;
    if (!r || r.id === item) return;
    if (r.r.tipo === 'sem_telefone') {
      toast('O pedido não tem o celular do cliente.', { description: 'Abra a cotação e use "Copiar a mensagem".' });
    } else if (r.r.tipo === 'copiado') toast('Mensagem copiada. Cole no WhatsApp do cliente.');
    else if (r.r.tipo === 'erro') toast(r.r.mensagem);
    else if (r.r.tipo === 'copiar_a_mao') toast('O navegador não deixou copiar. Abra a cotação para copiar.');
  }, [acoes.resultado, item]);

  const escopo = dados?.escopo || (escopoNaUrl === 'todas' ? 'todas' : 'minhas');
  const visiveis = useMemo(
    () => (dados?.itens || []).filter((c) => !estado || c.estado === estado),
    [dados, estado],
  );

  const abrir = (c: Cotacao) => {
    abriuPorAqui.current = true;
    acoes.limpar();
    mudar({ item: c.id }, 'push');
  };
  const fechar = () => {
    if (abriuPorAqui.current) {
      abriuPorAqui.current = false;
      router.back();
    } else mudar({ item: null });
  };
  const algumFiltro = Boolean(estado) || Boolean(termo);
  const limpar = () => {
    setTextoDaBusca('');
    setTermo('');
    mudar({ estado: null });
  };

  return (
    <div className="space-y-4 pb-10">
      {/* ───────────── OS ESTADOS ───────────── */}
      <div
        role="group"
        aria-label="Filtrar por estado"
        className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-3 sm:overflow-visible sm:px-0"
      >
        {FILTROS_DE_ESTADO.map((f) => {
          const ativo = estado === f.id;
          const n = dados?.contagens?.[f.id];
          return (
            <button
              key={f.id}
              type="button"
              aria-pressed={ativo}
              onClick={() => mudar({ estado: ativo ? null : f.id })}
              className={cn(
                'flex min-h-11 shrink-0 items-center gap-2 rounded-xl border px-3.5 py-2 text-left transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                ativo
                  ? 'border-primary/60 bg-brand-soft text-foreground'
                  : 'border-border bg-surface text-foreground-2 hover:border-primary/40',
              )}
            >
              <span className="text-xl font-semibold tabular-nums text-foreground">{typeof n === 'number' ? n : '–'}</span>
              <span className="whitespace-nowrap text-sm font-medium">{f.rotulo}</span>
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
                'h-11 rounded-md px-3 text-sm font-medium transition-colors sm:h-9',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                escopo === v ? 'bg-brand-soft text-foreground dark:text-primary' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {rot}
            </button>
          ))}
        </div>

        <label className="relative w-full sm:w-72">
          <span className="sr-only">Buscar por nome, placa ou CPF</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="search"
            value={textoDaBusca}
            onChange={(e) => setTextoDaBusca(e.target.value)}
            placeholder="Nome, placa ou CPF"
            className="h-11 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none sm:h-10"
          />
        </label>

        {algumFiltro && (
          <button
            type="button"
            onClick={limpar}
            className="inline-flex h-11 items-center gap-1.5 rounded-lg px-1 text-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-primary sm:h-9"
          >
            <X className="h-4 w-4" aria-hidden />
            Limpar filtros
          </button>
        )}
      </div>

      {/* ───────────── O CONTEÚDO ───────────── */}
      {erro && !dados && (
        <div className="rounded-xl border border-border bg-surface p-8 text-center">
          <p className="text-base font-medium text-foreground">Não conseguimos carregar as cotações agora.</p>
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
          estado={estado}
          busca={Boolean(termo)}
          limpar={limpar}
          verTodas={() => mudar({ escopo: 'todas' })}
          escopo={escopo}
        />
      )}

      {dados && visiveis.length > 0 && (
        <ul className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {visiveis.map((c) => (
            <li key={c.id}>
              <CartaoDaCotacao c={c} onAbrir={abrir} onEnviar={() => acoes.enviar(c.id)}
                enviando={acoes.ocupado?.id === c.id && acoes.ocupado.acao === 'enviar'} ocupado={Boolean(acoes.ocupado)} />
            </li>
          ))}
        </ul>
      )}

      {dados?.truncou && (
        <p className="text-sm text-muted-foreground">
          A lista está mostrando parte das cotações. Use a busca para achar uma cotação mais antiga.
        </p>
      )}

      <DetalheDaCotacaoGaveta id={item} versao={recarga} onFechar={fechar} acoes={acoes} />
    </div>
  );
}

/** O CARTÃO — cliente · carro ou risco · estado · a melhor parcela · quem pediu · quando. Abre o detalhe. */
function CartaoDaCotacao({
  c,
  onAbrir,
  onEnviar,
  enviando,
  ocupado,
}: {
  c: Cotacao;
  onAbrir: (c: Cotacao) => void;
  onEnviar: () => void;
  enviando: boolean;
  ocupado: boolean;
}) {
  const p = c.melhor ? parcela(c.melhor.parcela) : null;
  return (
    <div className="relative h-full overflow-hidden rounded-xl border border-border bg-surface transition-colors hover:border-primary/40">
      <span
        aria-hidden
        className={cn(
          'absolute inset-y-0 left-0 w-[3px]',
          c.estado === 'pronta' ? 'bg-success/70' : c.estado === 'calculando' ? 'bg-primary/60' : 'bg-warning/70',
        )}
      />
      <button
        type="button"
        onClick={() => onAbrir(c)}
        className="block w-full p-3 pl-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-base font-semibold leading-tight text-foreground">{nomeDoCliente(c)}</p>
            <p className="mt-0.5 truncate text-sm text-muted-foreground">{c.risco || c.ramo_rotulo}</p>
          </div>
          <Selo tom={tomDoEstado(c.estado)} rotulo={c.estado_rotulo} className="shrink-0" />
        </div>
        <div className="mt-2 min-h-[2.75rem]">
          {c.estado === 'calculando' ? (
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              {c.seguradoras > 0
                ? `${c.seguradoras === 1 ? '1 seguradora já respondeu' : `${c.seguradoras} seguradoras já responderam`}`
                : 'Calculando nas seguradoras…'}
            </p>
          ) : c.melhor ? (
            <>
              <p className="text-base font-semibold tabular-nums text-foreground">{p || reais(c.melhor.a_vista)}</p>
              <p className="truncate text-xs text-muted-foreground">
                {[c.melhor.seguradora, p ? `à vista ${reais(c.melhor.a_vista)}` : null,
                  c.seguradoras > 1 ? `${c.seguradoras} seguradoras` : null].filter(Boolean).join(' · ')}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Nenhuma seguradora deu preço.</p>
          )}
        </div>
        <p className="mt-2 truncate text-xs text-muted-foreground">
          {[c.quem_pediu ? (c.quem_pediu.sou_eu ? 'Você pediu' : c.quem_pediu.nome) : null, quando(c.quando)]
            .filter(Boolean)
            .join(' · ')}
        </p>
      </button>
      {c.pode_enviar && (
        <div className="px-3 pb-3 pl-4">
          <button
            type="button"
            onClick={onEnviar}
            disabled={ocupado}
            aria-label={`Enviar a cotação de ${nomeDoCliente(c)} pelo WhatsApp`}
            className={cn(
              'inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold',
              BOTAO_PRIMARIO,
              'transition-opacity disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            )}
          >
            {enviando ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <MessageCircle className="h-4 w-4" aria-hidden />}
            Enviar
          </button>
        </div>
      )}
    </div>
  );
}

function Carregando() {
  return (
    <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3" aria-busy="true" aria-label="Carregando as cotações">
      {Array.from({ length: 6 }).map((_, k) => (
        <Skeleton key={k} className="h-32 w-full rounded-xl" />
      ))}
    </div>
  );
}

/** Os estados vazios, em português de gente. */
function Vazio({
  dados,
  estado,
  busca,
  limpar,
  verTodas,
  escopo,
}: {
  dados: ListaDeCotacoes;
  estado: EstadoDaCotacao | '';
  busca: boolean;
  limpar: () => void;
  verTodas: () => void;
  escopo: 'minhas' | 'todas';
}) {
  let titulo: string;
  let texto: React.ReactNode = null;
  let acao: React.ReactNode = null;
  const botao =
    'mt-3 inline-flex h-11 items-center rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2';
  if (!dados.tem_alguma) {
    titulo = 'Nenhuma cotação ainda';
    texto = (
      <>
        Peça no chat, escrevendo, mandando a apólice, uma foto ou um áudio. Por exemplo: &ldquo;cota o Onix 2022, placa
        ABC1D23&rdquo;. A cotação aparece aqui assim que você confirmar.
      </>
    );
    acao = (
      <Link href="/dashboard/chat" className={cn(botao, 'justify-center')}>
        Abrir o chat
      </Link>
    );
  } else if (busca || (estado && escopo === 'todas')) {
    titulo = busca ? 'Nenhuma cotação com essa busca.' : FILTROS_DE_ESTADO.find((f) => f.id === estado)?.vazio || 'Nada aqui.';
    acao = (
      <button type="button" onClick={limpar} className={botao}>
        Limpar filtros
      </button>
    );
  } else if (escopo === 'minhas') {
    titulo = estado ? FILTROS_DE_ESTADO.find((f) => f.id === estado)?.vazio || 'Nada aqui.' : 'Nenhuma cotação sua ainda';
    texto = 'As cotações que você pede no chat aparecem aqui.';
    acao = (
      <button type="button" onClick={verTodas} className={botao}>
        Ver todas da corretora
      </button>
    );
  } else {
    titulo = `Nenhuma cotação nos últimos ${dados.dias} dias`;
  }
  return (
    <div className="rounded-xl border border-border bg-surface p-8 text-center">
      <Calculator className="mx-auto h-8 w-8 text-muted-foreground" strokeWidth={1.6} aria-hidden />
      <p className="mt-3 text-base font-medium text-foreground">{titulo}</p>
      {texto && <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-muted-foreground">{texto}</p>}
      {acao}
    </div>
  );
}
