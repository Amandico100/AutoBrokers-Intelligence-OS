'use client';

// SPEC-046 — Ficha do Atendimento (mobile-first, linguagem humana).
// Tudo que o corretor precisa saber do caso SEM abrir a conversa crua:
// resumo, estágio, apólice, linha do tempo, anexos e o dossiê real.

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight, Car, Check, Copy, FileText, Headphones, Loader2,
  MessageCircle, Mic, Paperclip, ShieldCheck, UserRound,
} from 'lucide-react';

import { DetailHeader, StatusPill, type StatusTone } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';

type Stage =
  | 'precisa_de_voce' | 'acionando' | 'protocolo' | 'monitorando'
  | 'em_conversa' | 'com_equipe' | 'concluido';

interface TimelineEvent { at: string | null; label: string; detail: string | null; done: boolean }
interface Anexo { id: string; tipo: 'imagem' | 'audio' | 'arquivo'; url: string; quando: string | null; de: 'cliente' | 'atendente' }

interface Ficha {
  conversa_id: string;
  tipo: 'atendimento' | 'acionamento';
  cliente: { nome: string | null; telefone: string | null };
  stage: Stage;
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
  assumido_por: string | null;
  mensagens_total: number;
}

const STAGE_META: Record<Stage, { label: string; tone: StatusTone }> = {
  precisa_de_voce: { label: 'Precisa de você', tone: 'danger' },
  acionando: { label: 'Acionando a seguradora', tone: 'info' },
  protocolo: { label: 'Protocolo garantido', tone: 'success' },
  monitorando: { label: 'Acompanhando o prestador', tone: 'success' },
  em_conversa: { label: 'Em conversa', tone: 'info' },
  com_equipe: { label: 'Com a equipe', tone: 'warning' },
  concluido: { label: 'Concluído', tone: 'neutral' },
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

function Section({ title, icon: Icon, children }: {
  title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
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
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando a ficha…
      </div>
    );
  }

  const meta = STAGE_META[ficha.stage] || STAGE_META.em_conversa;
  const titulo = ficha.cliente.nome || fmtPhone(ficha.cliente.telefone) || 'Atendimento';

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-4 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.conversas}
          title={titulo}
          subtitle={ficha.tipo === 'acionamento' ? 'Ficha do acionamento' : 'Ficha do atendimento'}
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Ficha' }]}
        />

        {/* Cabeçalho: estágio + contato + ações principais */}
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={meta.tone} label={meta.label} />
            {ficha.acionamento?.protocolo && (
              <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                protocolo {ficha.acionamento.protocolo}
              </span>
            )}
            <span className="flex-1" />
            <span className="text-[11px] text-muted-foreground">{fmtWhen(ficha.quando)}</span>
          </div>
          {ficha.cliente.telefone && (
            <p className="mt-2 font-mono text-xs text-muted-foreground">{fmtPhone(ficha.cliente.telefone)}</p>
          )}
          {ficha.assumido_por && (
            <p className="mt-1 text-xs text-muted-foreground">Assumido por {ficha.assumido_por}.</p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => router.push(`/dashboard/atendimentos/conversas?open=${ficha.conversa_id}`)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-brand-soft"
            >
              <MessageCircle className="h-3.5 w-3.5" />
              Abrir conversa ({ficha.mensagens_total})
            </button>
            {ficha.pode_assumir && !ficha.assumido_por && (
              <button
                onClick={assumir}
                disabled={claiming}
                className="inline-flex items-center gap-1.5 rounded-md border border-primary/40 bg-brand-soft px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:border-primary/70"
              >
                {claiming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Headphones className="h-3.5 w-3.5" />}
                Assumir atendimento
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
        </div>

        {/* Resumo mastigado */}
        <Section title="O que aconteceu" icon={FileText}>
          <p className="text-sm leading-relaxed text-foreground">{ficha.resumo}</p>
          {ficha.acionamento && (
            <p className="mt-2 text-xs text-muted-foreground">
              {ficha.acionamento.servico} · {ficha.acionamento.seguradora}
            </p>
          )}
        </Section>

        {/* Segurado, veículo e apólice (InfoCap read-only) */}
        {(ficha.apolice || ficha.veiculo) && (
          <Section title="Segurado e apólice" icon={ShieldCheck}>
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

        {/* Linha do tempo de eventos (não a conversa) */}
        <Section title="Acompanhamento" icon={UserRound}>
          <ol className="space-y-0">
            {ficha.timeline.map((ev, i) => (
              <li key={`${ev.label}-${i}`} className="relative flex gap-3 pb-4 last:pb-0">
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
                  {ev.at && <p className="mt-0.5 text-[11px] text-muted-foreground">{fmtWhen(ev.at)}</p>}
                </div>
              </li>
            ))}
          </ol>
        </Section>

        {/* Anexos */}
        {ficha.anexos.length > 0 && (
          <Section title={`Anexos (${ficha.anexos.length})`} icon={Paperclip}>
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
                    <img src={a.url} alt="Anexo do atendimento" className="h-20 w-full object-cover transition-opacity group-hover:opacity-90" />
                  ) : (
                    <span className="flex h-20 w-full flex-col items-center justify-center gap-1 text-muted-foreground">
                      {a.tipo === 'audio' ? <Mic className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                      <span className="text-[10px]">{a.tipo === 'audio' ? 'Áudio' : 'Arquivo'}</span>
                    </span>
                  )}
                  <span className="block truncate px-1.5 py-1 text-[10px] text-muted-foreground">
                    {a.de === 'cliente' ? 'do cliente' : 'do atendente'} · {fmtWhen(a.quando)}
                  </span>
                </a>
              ))}
            </div>
          </Section>
        )}

        {/* Dossiê real de handoff */}
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
