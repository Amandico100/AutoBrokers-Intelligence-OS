'use client';

// ─────────────────────────────────────────────────────────────────────────────
// A FILA — o QUADRO do que está acontecendo agora (SPEC-097 · U1.1/U5.2/R10/R12).
// ─────────────────────────────────────────────────────────────────────────────
//
// 🔴 O que mudou, e por quê:
//
//   📊 §1.1  a lista chegava com 87,4% dos atendimentos marcados "concluído" —
//            e `resolvido_em` estava NULL em 728 de 728. Ninguém tinha
//            encerrado nada: a rota deduzia o fim do RELÓGIO. Agora existe
//            **Parado**, e ele diz há quanto tempo e que ninguém encerrou.
//   📊 §1.4  a mesma pessoa aparecia DUAS vezes — uma como conversa, outra como
//            "Atendimento da equipe (observado)". O episódio do Atlas agora
//            mora DENTRO do card da conversa; só o episódio sem conversa
//            vinculada vira card próprio.
//   ⛔ §1.2  quem assumia virava "precisa de você". Agora quem cuida aparece no
//            card, e a coluna "Com a equipe" finalmente existe.
//
// 📱 MOBILE-FIRST (R12). Duas leituras, e a escolha fica salva:
//
//   QUADRO   as colunas rolam na horizontal, uma por vez (`snap`), cada uma com
//            a CONTAGEM no cabeçalho e cards compactos. No desktop as mesmas
//            colunas ficam lado a lado, cada uma com a sua própria rolagem, e o
//            cabeçalho fica grudado no topo.
//   LISTA    uma faixa por caso, larga, na ordem de urgência — a leitura de quem
//            está com o celular na mão e uma mão só.
//
// ⛔ Sem arrastar: o estágio é DERIVADO do que aconteceu, não de onde alguém
// soltou o card. Arrastar prometeria mudar o mundo e mudaria só a tela.
//
// ⚠️ O vocabulário visual (card, linha, chip, quem cuida) mora em
// `components/atendimento/caso-visual.tsx` — a mesma peça que a tela de Casos
// usa. Duas telas, um jeito de mostrar um caso.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Columns3, Headphones, List, Loader2, RefreshCw, TriangleAlert } from 'lucide-react';

import { DetailHeader } from '@/components/patterns';
import { CardDoCaso, LinhaDoCaso, ROTULO_DO_ESTAGIO } from '@/components/atendimento/caso-visual';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import type { Caso } from '@/lib/atendimento/casos';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Payload {
  items: Caso[];
  counts?: Record<Stage, number>;
  semana?: {
    terminaram: number;
    ainda_esperam: number;
    morreram_esperando: number;
    indisponivel: boolean;
  };
  indisponivel?: Record<string, boolean>;
}

// A ORDEM é desta tela — urgência primeiro, porque é assim que se varre um
// quadro. Rótulo, tom e a existência de cada coluna vêm da lista canônica;
// `Record<Stage, number>` obriga a dar posição a todo estágio novo, em vez de
// deixá-lo sumir do quadro sem ninguém perceber.
const ORDEM_NO_QUADRO: Record<Stage, number> = {
  precisa_de_voce: 1,
  esperando: 2,
  acionando: 3,
  monitorando: 4,
  protocolo: 5,
  em_conversa: 6,
  com_equipe: 7,
  observacao: 8,
  parado: 9,
  concluido: 10,
};

/** O título de cada coluna, na voz de quem trabalha — não na do banco. */
const TITULO_DA_COLUNA: Record<Stage, string> = {
  ...ROTULO_DO_ESTAGIO,
  concluido: 'Encerrados nesta semana',
};

const COLUNAS = (Object.keys(ORDEM_NO_QUADRO) as Stage[]).sort(
  (a, b) => ORDEM_NO_QUADRO[a] - ORDEM_NO_QUADRO[b],
);

/** A cor da régua do cabeçalho da coluna — o TOM vem da lista canônica. */
const REGUA_DO_TOM: Record<string, string> = {
  danger: 'bg-danger/70',
  warning: 'bg-warning/70',
  success: 'bg-success/70',
  info: 'bg-primary/60',
  neutral: 'bg-border',
  approval: 'bg-primary/60',
};

const PREFERENCIA_DE_LEITURA = 'autobrokers.atendimentos.fila.leitura';

/** Quantos cards uma coluna mostra antes de mandar para a lista completa. Não é
 *  um teto de dados (a rota lê tudo): é um teto de PINTURA — 600 nós numa
 *  coluna deixam o celular lento e ninguém rola até o fim de nenhuma delas. */
const CARDS_POR_COLUNA = 50;

export default function AttendanceQueueClient() {
  const router = useRouter();
  const [dados, setDados] = useState<Payload | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [responsavel, setResponsavel] = useState('todos');
  const [leitura, setLeitura] = useState<'quadro' | 'lista'>('quadro');

  // A leitura escolhida sobrevive ao refresh. Em `try/catch` porque navegador
  // com armazenamento bloqueado LANÇA ao ler `localStorage` — e a escolha entre
  // quadro e lista não é motivo para uma tela inteira não abrir.
  useEffect(() => {
    try {
      const salva = window.localStorage.getItem(PREFERENCIA_DE_LEITURA);
      if (salva === 'lista' || salva === 'quadro') setLeitura(salva);
    } catch {
      /* sem preferência — quadro */
    }
  }, []);

  const escolherLeitura = (v: 'quadro' | 'lista') => {
    setLeitura(v);
    try {
      window.localStorage.setItem(PREFERENCIA_DE_LEITURA, v);
    } catch {
      /* sem drama */
    }
  };

  const load = useCallback(async (manual?: boolean) => {
    if (manual) setRefreshing(true);
    try {
      const res = await fetch('/api/dashboard/atendimentos', { cache: 'no-store' });
      if (res.ok) setDados(await res.json());
    } catch {
      /* próximo poll tenta de novo */
    } finally {
      if (manual) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => load(), 15000);
    return () => clearInterval(t);
  }, [load]);

  const items = useMemo(() => dados?.items || [], [dados]);

  const donos = useMemo(() => {
    const mapa = new Map<string, string>();
    for (const i of items) if (i.dono) mapa.set(i.dono.id, i.dono.nome);
    return Array.from(mapa.entries()).sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'));
  }, [items]);

  const visiveis = useMemo(
    () =>
      items.filter((i) => {
        if (responsavel === 'todos') return true;
        if (responsavel === 'ninguem') return !i.dono;
        return i.dono?.id === responsavel;
      }),
    [items, responsavel],
  );

  /** A LISTA usa a mesma ordem do quadro: urgência primeiro, e dentro do
   *  estágio o que se moveu por último em cima. */
  const emOrdem = useMemo(
    () =>
      [...visiveis].sort((a, b) => {
        const d = ORDEM_NO_QUADRO[a.stage] - ORDEM_NO_QUADRO[b.stage];
        if (d !== 0) return d;
        return String(b.ultimo_evento_em || '').localeCompare(String(a.ultimo_evento_em || ''));
      }),
    [visiveis],
  );

  const emAndamento = visiveis.filter((i) => i.stage !== 'concluido').length;
  const precisamDeVoce = visiveis.filter((i) => i.stage === 'precisa_de_voce').length;
  const fontesForaDoAr = Object.entries(dados?.indisponivel || {})
    .filter(([, v]) => v === true)
    .map(([k]) => k);

  const abrir = (i: Caso) => {
    if (i.conversa_id) router.push(`/dashboard/atendimentos/ficha/${i.conversa_id}`);
  };

  const vazio = dados !== null && visiveis.length === 0;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="mx-auto w-full max-w-[100rem] shrink-0 space-y-3 px-4 pt-6 sm:px-6 sm:pt-10">
        <DetailHeader
          icon={icons.conversas}
          title="Fila de Atendimentos"
          subtitle="O que está acontecendo agora — o quadro se atualiza sozinho."
          breadcrumb={[
            { label: 'Atendimentos', href: '/dashboard/atendimentos' },
            { label: 'Fila' },
          ]}
        />

        {/* A BARRA. No celular ela quebra em duas alturas em vez de espremer os
            controles: um seletor de 28px de altura não se acerta com o polegar. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <p className="text-xs text-muted-foreground">
            {dados === null ? (
              'Carregando…'
            ) : (
              <>
                <strong className="font-semibold text-foreground">{emAndamento}</strong> em
                andamento
                {precisamDeVoce > 0 && (
                  <>
                    {' · '}
                    <strong className="font-semibold text-danger">{precisamDeVoce}</strong> precisa
                    de você
                  </>
                )}
                {' · '}
                {dados.semana?.terminaram ?? 0} encerrado(s) nesta semana
              </>
            )}
          </p>

          <span className="hidden flex-1 sm:block" />

          {/* Quadro × Lista — o segmentado, no tamanho do polegar. */}
          <div className="inline-flex rounded-lg border border-border bg-surface p-0.5">
            {(
              [
                ['quadro', 'Quadro', Columns3],
                ['lista', 'Lista', List],
              ] as const
            ).map(([v, rot, Icone]) => (
              <button
                key={v}
                onClick={() => escolherLeitura(v)}
                aria-pressed={leitura === v}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                  leitura === v
                    ? 'bg-brand-soft text-primary'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icone className="h-3.5 w-3.5" />
                {rot}
              </button>
            ))}
          </div>

          {donos.length > 0 && (
            <select
              value={responsavel}
              onChange={(e) => setResponsavel(e.target.value)}
              aria-label="Filtrar por quem cuida"
              className="rounded-lg border border-border bg-surface px-2.5 py-2 text-xs text-muted-foreground focus:border-primary focus:outline-none"
            >
              <option value="todos">Todo mundo</option>
              <option value="ninguem">Sem ninguém cuidando</option>
              {donos.map(([id, nome]) => (
                <option key={id} value={id}>
                  {nome}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => load(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2.5 py-2 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {refreshing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Atualizar
          </button>
        </div>

        {/* ⛔ O zero DECLARADO. Uma tela que mostra "nenhum" num dia em que
            ninguém conseguiu olhar é pior que uma tela sem número. */}
        {fontesForaDoAr.length > 0 && (
          <p className="flex items-center gap-1.5 rounded-lg border border-warning/40 px-3 py-2 text-xs text-warning">
            <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
            Parte das informações não carregou agora — o que está no quadro pode estar incompleto.
          </p>
        )}

        {vazio && (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Headphones className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">Está tudo sob controle</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              {responsavel === 'todos'
                ? 'Nenhum atendimento em andamento agora. Quando um segurado chamar no WhatsApp, ele aparece aqui na hora.'
                : 'Ninguém com esse filtro tem atendimento agora. Escolha "Todo mundo" para ver o quadro inteiro.'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-3 min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[100rem] px-4 pb-10 sm:px-6">
          {/* ───────────────────────── O QUADRO ───────────────────────── */}
          {leitura === 'quadro' && !vazio && (
            <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-3 sm:snap-none">
              {COLUNAS.map((stage) => {
                const grupo = visiveis.filter((i) => i.stage === stage);
                if (grupo.length === 0) return null;
                const meta = STAGE_META[stage];
                return (
                  <section
                    key={stage}
                    className={cn(
                      'flex w-[84vw] max-w-[19rem] shrink-0 snap-start flex-col rounded-xl',
                      'border border-border bg-surface-2/40 sm:w-[19rem]',
                      'sm:max-h-[calc(100vh-15rem)]',
                    )}
                  >
                    {/* O CABEÇALHO COM A CONTAGEM — grudado no topo enquanto a
                        coluna rola, senão a pessoa perde de vista onde está. */}
                    <header className="sticky top-0 z-10 rounded-t-xl border-b border-border/60 bg-surface-2/95 px-3 py-2.5 backdrop-blur">
                      <div className="flex items-center gap-2">
                        <span
                          aria-hidden
                          className={cn(
                            'h-2 w-2 shrink-0 rounded-full',
                            REGUA_DO_TOM[meta.tone] || 'bg-border',
                          )}
                        />
                        <h2 className="min-w-0 flex-1 truncate text-xs font-semibold tracking-[-0.01em] text-foreground">
                          {TITULO_DA_COLUNA[stage]}
                        </h2>
                        <span className="shrink-0 rounded-full border border-border bg-surface px-1.5 py-0.5 font-mono text-[10px] leading-none text-muted-foreground">
                          {grupo.length}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-[11px] leading-snug text-faint">
                        {meta.desc}
                      </p>
                    </header>

                    <div className="min-h-0 space-y-2 overflow-y-auto p-2.5">
                      {grupo.slice(0, CARDS_POR_COLUNA).map((i) => (
                        <CardDoCaso key={i.key} item={i} onOpen={abrir} />
                      ))}
                      {grupo.length > CARDS_POR_COLUNA && (
                        <p className="px-0.5 pt-1 text-[11px] text-muted-foreground">
                          e mais {grupo.length - CARDS_POR_COLUNA} —{' '}
                          <a href="/dashboard/atendimentos/casos" className="text-primary">
                            ver todos os casos
                          </a>
                        </p>
                      )}
                    </div>
                  </section>
                );
              })}
            </div>
          )}

          {/* ───────────────────────── A LISTA ───────────────────────── */}
          {leitura === 'lista' && !vazio && (
            <div className="mx-auto max-w-3xl space-y-2">
              {emOrdem.map((i) => (
                <LinhaDoCaso key={i.key} item={i} onOpen={abrir} />
              ))}
            </div>
          )}

          <p className="mt-3 text-[11px] text-muted-foreground">
            A lista completa, com busca por nome, telefone ou protocolo, está em{' '}
            <a href="/dashboard/atendimentos/casos" className="text-primary">
              Casos
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
