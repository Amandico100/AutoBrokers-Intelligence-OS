'use client';

// ─────────────────────────────────────────────────────────────────────────────
// A PÁGINA DO CASO — a ficha do atendimento (SPEC-097 · U6.1/U6.2).
// ─────────────────────────────────────────────────────────────────────────────
//
// É a tela mais importante do produto: é aqui que uma pessoa decide o que fazer.
// A ordem da página é a ordem das perguntas de quem abre:
//
//   1. O AGORA        o que está acontecendo · quem cuida · de quem se espera ·
//                     há quanto tempo · o que merece atenção · a próxima ação.
//   2. O que foi pedido
//   3. O que aconteceu   linha do tempo com HORA — 📊 E16: 6 dos 9 tipos
//                        chegavam com hora nenhuma.
//   4. Documentos     o que EXISTE (anexos das mensagens). Sem gaveta vazia.
//   5. Conversa       o link, não o despejo.
//   6. Dados          apólice, seguradora, serviço, veículo.
//
// ⚠️ Quando está tudo sob controle, a página diz isso em UMA linha. Quando
// precisa de gente, diz o QUE e POR QUÊ — nunca um código de estado.

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight, Car, Check, CircleCheck, Clock, Copy, FileText, Headphones, Loader2,
  MessageCircle, Mic, Paperclip, ShieldCheck, TriangleAlert, UserRound,
} from 'lucide-react';

import { DetailHeader, StatusPill } from '@/components/patterns';
import { STAGE_META, type Stage } from '@/lib/attendance/dispatch-states';
import type { Agora } from '@/lib/atendimento/casos';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface TimelineEvent {
  at: string; label: string; detail: string | null; done: boolean;
  fonte: string; fonte_id: string;
}
interface Anexo { id: string; tipo: 'imagem' | 'audio' | 'arquivo'; url: string; quando: string | null; de: 'cliente' | 'atendente' }

interface Ficha {
  conversa_id: string;
  tipo: 'atendimento' | 'acionamento';
  cliente: { nome: string | null; telefone: string | null };
  stage: Stage;
  agora: Agora | null;
  parado_ha: string | null;
  resolvido_em: string | null;
  desfecho_em_portugues: string | null;
  quando: string | null;
  resumo: string;
  resumo_fonte: 'espelho' | 'regras';
  acionamento: {
    seguradora: string; servico: string | null; protocolo: string | null;
    estado: string | null; espelho_conversa_id: string | null;
  } | null;
  veiculo: { placa: string | null; descricao: string | null } | null;
  apolice: {
    titular: string | null; documento: string | null; numero: string | null;
    seguradora: string | null; produto: string | null; vigencia_de: string | null;
    vigencia_ate: string | null; ativa: boolean | null; situacao: string | null;
  } | null;
  timeline: TimelineEvent[];
  anexos: Anexo[];
  dossier: string | null;
  pode_assumir: boolean;
  pode_encerrar: boolean;
  assumido_por: string | null;
  mensagens_total: number;
}

/** ⛔ Os CINCO do CHECK do banco, ditos como uma pessoa diria. Encerrar sem
 *  motivo era o que fazia "a atendente encerrou" e "o cliente desistiu" serem
 *  o mesmo estado para o banco — e a pergunta da sexta-feira ficar sem resposta. */
const MOTIVOS_DE_ENCERRAMENTO: { id: string; label: string; ajuda: string }[] = [
  { id: 'acionamento_concluido', label: 'O serviço foi prestado', ajuda: 'a assistência chegou e resolveu' },
  { id: 'encaminhado', label: 'A seguradora encaminhou', ajuda: 'entregamos o formulário ou a orientação ao segurado' },
  { id: 'resolvido_pelo_segurado', label: 'O segurado resolveu por conta', ajuda: 'ele mesmo deu um jeito' },
  { id: 'fechado_por_humano', label: 'A equipe encerrou', ajuda: 'o assunto acabou aqui' },
  { id: 'expirou', label: 'O prazo expirou sem resposta', ajuda: 'ninguém voltou a falar' },
];

/** Um chip só, e ele diz o PROBLEMA — não o nome do campo. */
const CHIP_DE_ATENCAO: Record<string, { label: string; tone: 'danger' | 'warning' }> = {
  pediu_pessoa: { label: 'o segurado pediu uma pessoa', tone: 'danger' },
  trabalho_falhou: { label: 'o acionamento parou', tone: 'danger' },
  espera_vencida: { label: 'o prazo da espera venceu', tone: 'warning' },
  parado: { label: 'parado, e ninguém encerrou', tone: 'warning' },
};

function fmtWhen(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
    + ' às ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function fmtPhone(p: string | null): string {
  if (!p) return '';
  const d = p.replace(/\D/g, '');
  if (d.length >= 12) return `(${d.slice(2, 4)}) ${d.slice(4, -4)}-${d.slice(-4)}`;
  return p;
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso.length <= 10 ? `${iso}T12:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('pt-BR');
}

/** "3d 4h" vira "3 dias". Duração de máquina não vai para a tela. */
function emPortugues(bruto: string | null | undefined): string {
  if (!bruto) return '';
  const dias = /^(\d+)d/.exec(bruto);
  if (dias) return `${dias[1]} ${dias[1] === '1' ? 'dia' : 'dias'}`;
  const horas = /^(\d+)h/.exec(bruto);
  if (horas) return `${horas[1]} ${horas[1] === '1' ? 'hora' : 'horas'}`;
  const min = /^(\d+)min/.exec(bruto);
  if (min) return `${min[1]} minutos`;
  return bruto;
}

function Section({ title, icon: Icon, children, aside }: {
  title: string; icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode; aside?: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <span className="flex-1" />
        {aside}
      </div>
      {children}
    </section>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null;
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="shrink-0 text-xs text-muted-foreground">{label}</span>
      <span className="min-w-0 text-right text-sm text-foreground">{value}</span>
    </div>
  );
}

export default function FichaClient({ conversaId }: { conversaId: string }) {
  const router = useRouter();
  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [claiming, setClaiming] = useState(false);
  const [copied, setCopied] = useState(false);
  const [perguntandoMotivo, setPerguntandoMotivo] = useState(false);
  const [encerrando, setEncerrando] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/dashboard/atendimentos/ficha/${conversaId}`, { cache: 'no-store' });
      if (!res.ok) {
        setErro(res.status === 404 ? 'Atendimento não encontrado.' : 'Não foi possível carregar a ficha.');
        return;
      }
      setFicha((await res.json()).ficha);
    } catch {
      setErro('Não foi possível carregar a ficha.');
    }
  }, [conversaId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, [load]);

  const assumir = async () => {
    if (!ficha || claiming) return;
    if (!window.confirm('Assumir este atendimento? O atendente IA pausa e a conversa passa a ser sua.')) return;
    setClaiming(true);
    try {
      const res = await fetch(`/api/dashboard/conversas/${ficha.conversa_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'claim' }),
      });
      if (res.ok) {
        router.push(`/dashboard/atendimentos/conversas?open=${ficha.conversa_id}`);
        return;
      }
      const j = await res.json().catch(() => ({}));
      window.alert(j.error || 'Não foi possível assumir agora.');
    } finally {
      setClaiming(false);
    }
  };

  // 🔴 E3/E4 — a Ficha ganha o botão Encerrar, e ele PERGUNTA o motivo.
  const encerrar = async (motivo: string) => {
    if (!ficha || encerrando) return;
    setEncerrando(true);
    try {
      const res = await fetch(`/api/dashboard/conversas/${ficha.conversa_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'close', motivo }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        window.alert(j.error || 'Não foi possível encerrar agora.');
        return;
      }
      setPerguntandoMotivo(false);
      await load();
    } finally {
      setEncerrando(false);
    }
  };

  const copiarDossie = async () => {
    if (!ficha?.dossier) return;
    try {
      await navigator.clipboard.writeText(ficha.dossier);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard indisponível — sem drama */
    }
  };

  if (erro) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="rounded-xl border border-border bg-surface p-8 text-center">
          <p className="text-sm text-foreground">{erro}</p>
          <button
            onClick={() => router.push('/dashboard/atendimentos')}
            className="mt-3 text-xs text-primary"
          >
            ← Voltar para Atendimentos
          </button>
        </div>
      </div>
    );
  }

  if (!ficha) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando o caso…
      </div>
    );
  }

  const meta = STAGE_META[ficha.stage] || STAGE_META.em_conversa;
  const titulo = ficha.cliente.nome || fmtPhone(ficha.cliente.telefone) || 'Atendimento';
  const agora = ficha.agora;
  const atencao = (agora?.atencao || []).filter((r) => CHIP_DE_ATENCAO[r]);
  const souAssistencia = ficha.acionamento?.servico && ficha.acionamento.servico !== 'Sinistro';
  const tipoDoCaso = ficha.acionamento
    ? (souAssistencia ? 'Assistência 24h' : 'Sinistro')
    : null;
  const tudoSobControle = atencao.length === 0 && !ficha.resolvido_em
    && (ficha.stage === 'em_conversa' || ficha.stage === 'com_equipe'
      || ficha.stage === 'monitorando' || ficha.stage === 'protocolo');

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-4 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.conversas}
          title={titulo}
          subtitle={tipoDoCaso ? `${tipoDoCaso} · ${ficha.acionamento?.seguradora}` : 'Atendimento'}
          breadcrumb={[
            { label: 'Atendimentos', href: '/dashboard/atendimentos' },
            { label: 'Casos', href: '/dashboard/atendimentos/casos' },
            { label: 'O caso' },
          ]}
        />

        {/* ───────────────────── 1. O AGORA ───────────────────── */}
        <section className="rounded-xl border border-border bg-surface p-4">
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={meta.tone} label={meta.label} />
            {atencao.slice(0, 2).map((r) => (
              <StatusPill key={r} tone={CHIP_DE_ATENCAO[r].tone} label={CHIP_DE_ATENCAO[r].label} />
            ))}
            {ficha.acionamento?.protocolo && (
              <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                protocolo {ficha.acionamento.protocolo}
              </span>
            )}
          </div>

          <p className="mt-3 text-base font-medium leading-snug text-foreground">
            {agora?.situacao || ficha.resumo}
          </p>

          <div className="mt-2 space-y-1 text-sm text-muted-foreground">
            {agora?.dono
              ? <p>{agora.dono.nome} está cuidando deste caso.</p>
              : !ficha.resolvido_em && <p>Ninguém da equipe assumiu este caso ainda.</p>}
            {agora?.esperando && (
              <p>
                Esperando{' '}
                {agora.esperando.kind === 'esperando_cliente' ? 'o segurado'
                  : agora.esperando.kind === 'esperando_humano' ? 'alguém da equipe'
                    : 'a seguradora'}
                {agora.esperando.desde ? ` desde ${fmtWhen(agora.esperando.desde)}` : ''}
                {agora.esperando.vencida ? ' — e o prazo já venceu.' : '.'}
              </p>
            )}
            {agora?.ha_quanto_tempo && (
              <p className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                {ficha.resolvido_em
                  ? `Encerrado ${ficha.desfecho_em_portugues ? `— ${ficha.desfecho_em_portugues}` : ''} em ${fmtWhen(ficha.resolvido_em)}.`
                  : `Última movimentação há ${emPortugues(agora.ha_quanto_tempo)}.`}
              </p>
            )}
          </div>

          {/* A PRÓXIMA AÇÃO. Quando não há uma, a página DIZ que não há —
              inventar um próximo passo é pior que não ter nenhum. */}
          <div className={cn(
            'mt-3 flex items-start gap-2 rounded-lg border px-3 py-2 text-sm',
            atencao.length ? 'border-danger/40 text-foreground' : 'border-border bg-surface-2 text-muted-foreground',
          )}>
            {atencao.length
              ? <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
              : <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" />}
            <span>
              <strong className="font-medium text-foreground">Próximo passo: </strong>
              {agora?.proxima_acao?.regra === 'sem_proxima_acao_declarada' && tudoSobControle
                ? 'nada a fazer agora — está tudo sob controle.'
                : agora?.proxima_acao?.texto || 'Sem próxima ação declarada.'}
            </span>
          </div>

          {ficha.cliente.telefone && (
            <p className="mt-3 font-mono text-xs text-muted-foreground">{fmtPhone(ficha.cliente.telefone)}</p>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => router.push(`/dashboard/atendimentos/conversas?open=${ficha.conversa_id}`)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-brand-soft"
            >
              <MessageCircle className="h-3.5 w-3.5" />
              Abrir a conversa ({ficha.mensagens_total})
            </button>
            {ficha.pode_assumir && !ficha.assumido_por && (
              <button
                onClick={assumir}
                disabled={claiming}
                className="inline-flex items-center gap-1.5 rounded-md border border-primary/40 bg-brand-soft px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:border-primary/70"
              >
                {claiming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Headphones className="h-3.5 w-3.5" />}
                Assumir o atendimento
              </button>
            )}
            {ficha.pode_encerrar && (
              <button
                onClick={() => setPerguntandoMotivo(true)}
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-brand-soft"
              >
                <CircleCheck className="h-3.5 w-3.5" />
                Encerrar
              </button>
            )}
            {ficha.acionamento?.espelho_conversa_id && (
              <button
                onClick={() => router.push(`/dashboard/atendimentos/conversas?open=${ficha.acionamento?.espelho_conversa_id}`)}
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-brand-soft"
              >
                <ArrowRight className="h-3.5 w-3.5" />
                Conversa com a seguradora
              </button>
            )}
          </div>

          {/* ⛔ Encerrar PERGUNTA. Cravar um motivo seria inventar o desfecho —
              e é esse dado que a corretora usa para saber o que deu certo. */}
          {perguntandoMotivo && (
            <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3">
              <p className="text-sm font-medium text-foreground">Como este atendimento terminou?</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                O motivo fica registrado no caso — é ele que responde, na sexta-feira,
                quantos atendimentos terminaram de verdade.
              </p>
              <div className="mt-2 space-y-1.5">
                {MOTIVOS_DE_ENCERRAMENTO.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => encerrar(m.id)}
                    disabled={encerrando}
                    className="w-full rounded-md border border-border bg-surface px-3 py-2 text-left transition-colors hover:border-primary/40 hover:bg-brand-soft"
                  >
                    <span className="block text-sm text-foreground">{m.label}</span>
                    <span className="block text-[11px] text-muted-foreground">{m.ajuda}</span>
                  </button>
                ))}
              </div>
              <button
                onClick={() => setPerguntandoMotivo(false)}
                className="mt-2 text-xs text-muted-foreground hover:text-foreground"
              >
                Cancelar
              </button>
            </div>
          )}
        </section>

        {/* ───────────────────── 2. O QUE FOI PEDIDO ───────────────────── */}
        <Section
          title="O que foi pedido"
          icon={FileText}
          aside={tipoDoCaso ? <StatusPill tone="neutral" label={tipoDoCaso} /> : undefined}
        >
          <p className="text-sm leading-relaxed text-foreground">{ficha.resumo}</p>
          {ficha.acionamento && (
            <p className="mt-2 text-xs text-muted-foreground">
              {[ficha.acionamento.servico, ficha.acionamento.seguradora].filter(Boolean).join(' · ')}
            </p>
          )}
        </Section>

        {/* ───────────────────── 3. O QUE ACONTECEU ───────────────────── */}
        <Section title="O que aconteceu" icon={UserRound}>
          {ficha.timeline.length === 0 ? (
            <p className="text-xs text-muted-foreground">Ainda não há passos registrados neste caso.</p>
          ) : (
            <ol className="space-y-0">
              {ficha.timeline.map((ev, i) => (
                <li key={`${ev.fonte}-${ev.fonte_id}-${i}`} className="relative flex gap-3 pb-4 last:pb-0">
                  {i < ficha.timeline.length - 1 && (
                    <span className="absolute left-[7px] top-5 h-full w-px bg-border" aria-hidden />
                  )}
                  <span
                    className={cn(
                      'mt-1 flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border',
                      ev.done ? 'border-primary/60 bg-brand-soft' : 'border-border bg-surface-2',
                    )}
                  >
                    {ev.done && <Check className="h-2.5 w-2.5 text-primary" />}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">{ev.label}</p>
                    {ev.detail && <p className="text-xs text-muted-foreground">{ev.detail}</p>}
                    <p className="mt-0.5 text-[11px] text-muted-foreground">{fmtWhen(ev.at)}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Section>

        {/* ───────────── 4. DOCUMENTOS — só o que EXISTE ───────────── */}
        {ficha.anexos.length > 0 && (
          <Section title={`Documentos e fotos (${ficha.anexos.length})`} icon={Paperclip}>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {ficha.anexos.map((a) => (
                <a
                  key={a.id}
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group overflow-hidden rounded-lg border border-border bg-surface-2"
                >
                  {a.tipo === 'imagem' ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={a.url} alt="Documento enviado no atendimento" className="h-20 w-full object-cover transition-opacity group-hover:opacity-90" />
                  ) : (
                    <span className="flex h-20 w-full flex-col items-center justify-center gap-1 text-muted-foreground">
                      {a.tipo === 'audio' ? <Mic className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                      <span className="text-[10px]">{a.tipo === 'audio' ? 'Áudio' : 'Arquivo'}</span>
                    </span>
                  )}
                  <span className="block truncate px-1.5 py-1 text-[10px] text-muted-foreground">
                    {a.de === 'cliente' ? 'do segurado' : 'da equipe'} · {fmtWhen(a.quando)}
                  </span>
                </a>
              ))}
            </div>
          </Section>
        )}

        {/* ───────────────────── 5. DADOS ───────────────────── */}
        {(ficha.apolice || ficha.veiculo) && (
          <Section title="Dados do segurado" icon={ShieldCheck}>
            <div className="divide-y divide-border/60">
              <Row label="Titular" value={ficha.apolice?.titular} />
              <Row label="Apólice" value={ficha.apolice?.numero ? <span className="font-mono">{ficha.apolice.numero}</span> : null} />
              <Row label="Seguradora" value={ficha.apolice?.seguradora} />
              <Row label="Produto" value={ficha.apolice?.produto} />
              <Row
                label="Vigência"
                value={(ficha.apolice?.vigencia_de || ficha.apolice?.vigencia_ate)
                  ? `${fmtDate(ficha.apolice?.vigencia_de || null)} → ${fmtDate(ficha.apolice?.vigencia_ate || null)}`
                  : null}
              />
              <Row
                label="Situação"
                value={ficha.apolice?.ativa === true ? 'Vigente' : (ficha.apolice?.situacao || null)}
              />
              {ficha.veiculo && (
                <Row
                  label="Veículo"
                  value={
                    <span className="inline-flex items-center gap-1.5">
                      <Car className="h-3.5 w-3.5 text-muted-foreground" />
                      {[ficha.veiculo.descricao, ficha.veiculo.placa].filter(Boolean).join(' · ')}
                    </span>
                  }
                />
              )}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Dados consultados no sistema da corretora (somente leitura).
            </p>
          </Section>
        )}

        {/* O dossiê real de handoff — o mesmo texto que foi entregue à equipe. */}
        {ficha.dossier && (
          <Section title="Dossiê para a equipe" icon={Headphones}>
            <pre className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-2 p-3 text-xs leading-relaxed text-foreground">
              {ficha.dossier}
            </pre>
            <button
              onClick={copiarDossie}
              className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-primary" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? 'Copiado!' : 'Copiar dossiê'}
            </button>
          </Section>
        )}
      </div>
    </div>
  );
}
