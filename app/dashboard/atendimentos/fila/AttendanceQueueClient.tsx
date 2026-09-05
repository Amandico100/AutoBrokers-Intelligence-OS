'use client';

// ─────────────────────────────────────────────────────────────────────────────
// A FILA — o QUADRO do que está acontecendo agora (SPEC-097 · U1.1/U5.2/R10).
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
// ⚠️ LINGUAGEM: nada de nome de campo, status técnico ou id nesta tela. O card
// diz "esperando a seguradora há 2 dias", "Ana está atendendo", "parado há 3
// dias — ninguém encerrou". Se não dá para ler em voz alta para o corretor, não
// entra.
//
// 📱 MOBILE-FIRST: as colunas rolam na horizontal, uma por vez (`snap`), com o
// card compacto — segurado, o que foi pedido, há quanto tempo, quem cuida e UM
// chip de atenção. No desktop as mesmas colunas ficam lado a lado.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Headphones, Loader2, RefreshCw, TriangleAlert } from 'lucide-react';

import { DetailHeader, StatusPill } from '@/components/patterns';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import type { Caso } from '@/lib/atendimento/casos';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface Payload {
  items: Caso[];
  counts?: Record<Stage, number>;
  semana?: { terminaram: number; ainda_esperam: number; morreram_esperando: number; indisponivel: boolean };
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
  precisa_de_voce: 'Precisa de você',
  esperando: 'Esperando resposta',
  acionando: 'Acionando a seguradora',
  monitorando: 'Acompanhando o prestador',
  protocolo: 'Protocolo garantido',
  em_conversa: 'Em conversa',
  com_equipe: 'Com a equipe',
  observacao: 'Atendimento da equipe',
  parado: 'Parado',
  concluido: 'Encerrados nesta semana',
};

const COLUNAS = (Object.keys(ORDEM_NO_QUADRO) as Stage[])
  .sort((a, b) => ORDEM_NO_QUADRO[a] - ORDEM_NO_QUADRO[b]);

/** Um chip só. Dois chips num card de celular viram ruído. */
const CHIP_DE_ATENCAO: Record<string, { label: string; tone: 'danger' | 'warning' }> = {
  pediu_pessoa: { label: 'pediu uma pessoa', tone: 'danger' },
  trabalho_falhou: { label: 'o acionamento parou', tone: 'danger' },
  espera_vencida: { label: 'prazo vencido', tone: 'warning' },
  parado: { label: 'ninguém encerrou', tone: 'warning' },
};
const PRIORIDADE_DO_CHIP = ['pediu_pessoa', 'trabalho_falhou', 'espera_vencida', 'parado'];

function fmtPhone(p: string | null): string {
  if (!p) return '';
  const d = p.replace(/\D/g, '');
  if (d.length >= 12) return `(${d.slice(2, 4)}) ${d.slice(4, -4)}-${d.slice(-4)}`;
  return p;
}

/** "há 3 dias" · "há 2 horas" · "agora há pouco" — nunca "2026-09-05T12:00Z". */
function haQuantoTempo(item: Caso): string {
  const bruto = item.agora?.ha_quanto_tempo;
  if (!bruto) return '';
  const dias = /^(\d+)d/.exec(bruto);
  if (dias) return `há ${dias[1]} ${dias[1] === '1' ? 'dia' : 'dias'}`;
  const horas = /^(\d+)h/.exec(bruto);
  if (horas) return `há ${horas[1]} ${horas[1] === '1' ? 'hora' : 'horas'}`;
  const min = /^(\d+)min/.exec(bruto);
  if (min && Number(min[1]) > 5) return `há ${min[1]} minutos`;
  return 'agora há pouco';
}

/** A frase do card. É ela que o corretor lê primeiro. */
function oQueEstaAcontecendo(item: Caso): string {
  const quando = haQuantoTempo(item);
  if (item.stage === 'concluido') {
    return item.agora?.situacao || 'Encerrado.';
  }
  if (item.dono) return `${item.dono.nome} está atendendo${quando ? ` · ${quando}` : ''}`;
  if (item.esperando) {
    const dequem = item.esperando.kind === 'esperando_cliente' ? 'o segurado'
      : item.esperando.kind === 'esperando_humano' ? 'alguém da equipe'
        : 'a seguradora';
    return `esperando ${dequem}${quando ? ` ${quando}` : ''}`;
  }
  if (item.stage === 'parado') return `parado ${quando} — ninguém encerrou`;
  if (item.stage === 'precisa_de_voce') {
    return item.agora?.proxima_acao?.regra === 'passo_do_trabalho'
      ? `o acionamento parou ${quando} e precisa de uma pessoa`
      : `pediu uma pessoa ${quando}`;
  }
  return `${item.agora?.situacao || 'Em andamento.'}${quando ? ` · ${quando}` : ''}`;
}

function CardDoCaso({ item, onOpen }: { item: Caso; onOpen: (i: Caso) => void }) {
  const razao = PRIORIDADE_DO_CHIP.find((r) => (item.agora?.atencao || []).includes(r as never));
  const chip = razao ? CHIP_DE_ATENCAO[razao] : null;
  const abre = Boolean(item.conversa_id);
  return (
    <button
      onClick={() => onOpen(item)}
      disabled={!abre}
      className={cn(
        'w-full rounded-lg border border-border bg-surface p-3 text-left transition-colors',
        abre ? 'hover:border-primary/40 hover:bg-surface-2' : 'cursor-default',
        item.stage === 'precisa_de_voce' && 'border-danger/40',
      )}
    >
      <p className="truncate text-sm font-semibold leading-tight text-foreground">
        {item.cliente || fmtPhone(item.telefone) || 'Segurado'}
      </p>
      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {oQueEstaAcontecendo(item)}
      </p>
      {(chip || item.protocolo || item.sem_conversa_vinculada) && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {chip && <StatusPill tone={chip.tone} label={chip.label} />}
          {item.protocolo && (
            <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              {item.protocolo}
            </span>
          )}
          {item.sem_conversa_vinculada && (
            <span className="text-[10px] text-faint">sem conversa vinculada</span>
          )}
        </div>
      )}
    </button>
  );
}

export default function AttendanceQueueClient() {
  const router = useRouter();
  const [dados, setDados] = useState<Payload | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [responsavel, setResponsavel] = useState('todos');

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
    return Array.from(mapa.entries());
  }, [items]);

  const visiveis = useMemo(() => items.filter((i) => {
    if (responsavel === 'todos') return true;
    if (responsavel === 'ninguem') return !i.dono;
    return i.dono?.id === responsavel;
  }), [items, responsavel]);

  const emAndamento = visiveis.filter((i) => i.stage !== 'concluido').length;
  const fontesForaDoAr = Object.entries(dados?.indisponivel || {})
    .filter(([, v]) => v === true)
    .map(([k]) => k);

  const abrir = (i: Caso) => {
    if (i.conversa_id) router.push(`/dashboard/atendimentos/ficha/${i.conversa_id}`);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="mx-auto w-full max-w-7xl shrink-0 space-y-4 px-4 pt-6 sm:px-6 sm:pt-10">
        <DetailHeader
          icon={icons.conversas}
          title="Fila de Atendimentos"
          subtitle="O que está acontecendo agora — o quadro se atualiza sozinho."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Fila' }]}
        />

        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs text-muted-foreground">
            {dados === null
              ? 'Carregando…'
              : `${emAndamento} em andamento · ${dados.semana?.terminaram ?? 0} encerrado(s) nesta semana`}
          </p>
          <span className="hidden flex-1 sm:block" />
          {donos.length > 0 && (
            <select
              value={responsavel}
              onChange={(e) => setResponsavel(e.target.value)}
              className="rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-muted-foreground focus:border-primary focus:outline-none"
            >
              <option value="todos">Todo mundo</option>
              <option value="ninguem">Sem ninguém cuidando</option>
              {donos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
            </select>
          )}
          <button
            onClick={() => load(true)}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
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

        {dados !== null && visiveis.length === 0 && (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Headphones className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium text-foreground">Está tudo sob controle</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Nenhum atendimento em andamento agora. Quando um segurado chamar no WhatsApp,
              ele aparece aqui na hora.
            </p>
          </div>
        )}
      </div>

      {/* O QUADRO. No celular as colunas rolam na horizontal, uma por vez; no
          desktop elas ficam lado a lado. Sem arrastar: o estágio é derivado do
          que aconteceu, não de onde alguém soltou o card. */}
      <div className="mt-4 min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-7xl px-4 pb-10 sm:px-6">
          <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-3">
            {COLUNAS.map((stage) => {
              const grupo = visiveis.filter((i) => i.stage === stage);
              if (grupo.length === 0) return null;
              const meta = STAGE_META[stage];
              return (
                <section
                  key={stage}
                  className="w-[84vw] max-w-xs shrink-0 snap-start rounded-xl border border-border bg-surface-2/40 p-2.5 sm:w-72"
                >
                  <header className="mb-2 flex items-baseline gap-2 px-0.5">
                    <StatusPill tone={meta.tone} label={`${TITULO_DA_COLUNA[stage]} · ${grupo.length}`} />
                  </header>
                  <p className="mb-2 px-0.5 text-[11px] leading-snug text-faint">{meta.desc}</p>
                  <div className="space-y-2">
                    {grupo.slice(0, 50).map((i) => (
                      <CardDoCaso key={i.key} item={i} onOpen={abrir} />
                    ))}
                    {grupo.length > 50 && (
                      <p className="px-0.5 pt-1 text-[11px] text-muted-foreground">
                        e mais {grupo.length - 50} —{' '}
                        <a href="/dashboard/atendimentos/casos" className="text-primary">ver todos os casos</a>
                      </p>
                    )}
                  </div>
                </section>
              );
            })}
          </div>

          <p className="mt-2 text-[11px] text-muted-foreground">
            A lista completa, com busca por nome, telefone ou protocolo, está em{' '}
            <a href="/dashboard/atendimentos/casos" className="text-primary">Casos</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
