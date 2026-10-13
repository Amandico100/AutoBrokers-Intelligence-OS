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
//
// ⚠️ SPEC-131-B · G2: o quadro, a lista, a alternância salva e o teto de
// pintura foram EXTRAÍDOS para `components/aplicativos/QuadroOuLista.tsx` — a
// mesma peça que a aba Renovações usa. O que é desta tela fica aqui: o polling,
// o filtro de quem cuida, a ordem e os títulos das colunas, e o `abrir`.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Headphones, Loader2, RefreshCw, TriangleAlert } from 'lucide-react';

import { DetailHeader } from '@/components/patterns';
import {
  QuadroOuLista,
  SeletorDeLeitura,
  useLeituraSalva,
  type ColunaDoQuadro,
} from '@/components/aplicativos/QuadroOuLista';
import { CardDoCaso, LinhaDoCaso, ROTULO_DO_ESTAGIO } from '@/components/atendimento/caso-visual';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import type { Caso } from '@/lib/atendimento/casos';
import { icons } from '@/lib/icons';

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

/** As colunas do quadro: rótulo, tom e descrição vêm da lista canônica; uma
 *  coluna sem caso não aparece (como sempre foi nesta tela). */
const COLUNAS_DO_QUADRO: ColunaDoQuadro[] = COLUNAS.map((stage) => ({
  id: stage,
  titulo: TITULO_DA_COLUNA[stage],
  descricao: STAGE_META[stage]?.desc,
  tom: STAGE_META[stage]?.tone,
  esconderSeVazia: true,
}));

const PREFERENCIA_DE_LEITURA = 'autobrokers.atendimentos.fila.leitura';

export default function AttendanceQueueClient() {
  const router = useRouter();
  const [dados, setDados] = useState<Payload | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [responsavel, setResponsavel] = useState('todos');
  // A leitura escolhida sobrevive ao refresh (salva no aparelho, em try/catch).
  const [leitura, escolherLeitura] = useLeituraSalva(PREFERENCIA_DE_LEITURA, 'quadro');

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
          <SeletorDeLeitura leitura={leitura} onEscolher={escolherLeitura} />

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
          {/* ──────────────────── O QUADRO · A LISTA ──────────────────── */}
          {!vazio && (
            <QuadroOuLista
              leitura={leitura}
              // o quadro preserva a ordem da rota dentro de cada coluna; a
              // LISTA usa a mesma ordem do quadro: urgência primeiro
              itens={leitura === 'quadro' ? visiveis : emOrdem}
              colunas={COLUNAS_DO_QUADRO}
              colunaDe={(i) => i.stage}
              chave={(i) => i.key}
              Card={(i) => <CardDoCaso item={i} onOpen={abrir} />}
              Linha={(i) => <LinhaDoCaso item={i} onOpen={abrir} />}
              maisNaColuna={(restantes) => (
                <p className="px-0.5 pt-1 text-[11px] text-muted-foreground">
                  e mais {restantes} —{' '}
                  <a href="/dashboard/atendimentos/casos" className="text-primary">
                    ver todos os casos
                  </a>
                </p>
              )}
            />
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
