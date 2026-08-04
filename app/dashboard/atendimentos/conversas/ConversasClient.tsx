'use client';

// Central de conversas (SPEC-017 S17-13) — o "WhatsApp da corretora" no dashboard.
// Duas colunas: lista (aguardando humano primeiro + espelho da seguradora) e
// thread com a LINHA DE POSSE — quem está com a conversa agora (IA / fila /
// você / colega) — e ações Assumir / Devolver à IA / Encerrar.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Bot,
  ChevronLeft,
  Headphones,
  Loader2,
  MessageCircle,
  Search,
  Send,
  ShieldCheck,
  Undo2,
  UserRound,
  X,
} from 'lucide-react';

import { StatusPill, type StatusTone } from '@/components/patterns/StatusPill';
import { dispatchStateMeta } from '@/lib/attendance/dispatch-states';
import { cn } from '@/lib/utils';

interface Conversation {
  id: string;
  session_id: string | null;
  channel: string | null;
  status: string | null;
  user_phone: string | null;
  user_name: string | null;
  unread_count: number | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  claimed_by: string | null;
  claimed_by_name: string | null;
}

interface Message {
  id: string;
  role: string;
  content: string | null;
  type: string | null;
  image_url: string | null;
  audio_url: string | null;
  sender_user_id: string | null;
  created_at: string;
}

interface DispatchSession {
  insurer_phone: string;
  case_id: string | null;
  state: string | null;
  subservice: string | null;
  client_phone: string | null;
  captured: Record<string, unknown>;
  transcript: { direction: string; text: string; at: string; dry_run?: boolean }[];
  created_at: string | null;
}

const SUBSERVICE_LABEL: Record<string, string> = {
  eletricista: 'Eletricista',
  chaveiro: 'Chaveiro',
  encanador: 'Hidráulica',
  eletrodomesticos: 'Eletrodomésticos',
  guincho: 'Guincho',
  bateria: 'Bateria',
  pneu: 'Pneu',
};

const INSURER_LABEL: Record<string, string> = {
  allianz: 'Allianz Assistência 24h',
  porto: 'Porto Assistência 24h',
  hdi: 'HDI Assistência 24h',
  yelum: 'Yelum Assistência 24h',
  tokio: 'Tokio Assistência 24h',
  alfa: 'Alfa Assistência 24h',
  azul: 'Azul Assistência 24h',
  bradesco: 'Bradesco Assistência 24h',
  mapfre: 'Mapfre Assistência 24h',
  zurich: 'Zurich Assistência 24h',
};

// O nome da seguradora vem do playbook_ref ("yelum-auto-whatsapp@v2") — nunca
// mostrar seguradora errada (incidente 2026-07-10: rótulo fixo "Allianz").
const insurerLabelFromRef = (ref?: string | null): string => {
  const key = String(ref || '').split('-')[0];
  return INSURER_LABEL[key] || 'Seguradora · Assistência 24h';
};

// `DISPATCH_STATE_LABEL` morava aqui com QUATRO dos dez estados. Os outros seis
// — inclusive `encaminhado` e `resolvido` — caíam no fallback e apareciam para
// o corretor como a string crua do motor ("resolvido", cinza). Os rótulos deste
// arquivo eram os mesmos da lista canônica, então não há razão para um mapa
// local: `dispatchStateMeta` é a fonte, e ela cobre os dez por tipo.

function ownership(c: Conversation, me: string | null) {
  if (c.status === 'closed') return { tone: 'neutral' as StatusTone, label: 'Encerrada' };
  if (c.claimed_by && me && c.claimed_by === me) return { tone: 'info' as StatusTone, label: 'Você está atendendo' };
  if (c.claimed_by) return { tone: 'neutral' as StatusTone, label: `${c.claimed_by_name || 'Colega'} atendendo` };
  if (c.status === 'HUMAN_REQUESTED') return { tone: 'approval' as StatusTone, label: 'Aguardando humano' };
  return { tone: 'success' as StatusTone, label: 'Atendente IA' };
}

function displayName(c: Conversation) {
  return c.user_name?.trim() || c.user_phone || 'Sem identificação';
}

function fmtTime(iso: string | null) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function dayLabel(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return 'Hoje';
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return 'Ontem';
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long' });
}

export function ConversasClient() {
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [dispatches, setDispatches] = useState<DispatchSession[]>([]);
  const [me, setMe] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDispatch, setSelectedDispatch] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loadingThread, setLoadingThread] = useState(false);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState('');
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const selectedIdRef = useRef<string | null>(null);
  selectedIdRef.current = selectedId;

  const loadList = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/conversas', { cache: 'no-store' });
      if (!res.ok) return;
      const j = await res.json();
      setConversations(j.conversations || []);
      setDispatches(j.dispatches || []);
      setMe(j.me || null);
    } catch {
      /* silencioso — próximo poll tenta de novo */
    }
  }, []);

  const loadThread = useCallback(async (id: string, opts?: { quiet?: boolean }) => {
    if (!opts?.quiet) setLoadingThread(true);
    try {
      const res = await fetch(`/api/dashboard/conversas/${id}`, { cache: 'no-store' });
      if (!res.ok) return;
      const j = await res.json();
      if (selectedIdRef.current !== id) return; // trocou de conversa durante o fetch
      setConversation(j.conversation || null);
      setMessages(j.messages || []);
    } catch {
      /* silencioso */
    } finally {
      if (!opts?.quiet) setLoadingThread(false);
    }
  }, []);

  useEffect(() => {
    loadList();
    const t = setInterval(loadList, 8000);
    return () => clearInterval(t);
  }, [loadList]);

  // SPEC-043: deep-link ?open=<conversa_id> (Fila/Histórico/Segurados abrem
  // direto a thread — no mobile, já em tela cheia).
  useEffect(() => {
    try {
      const id = new URLSearchParams(window.location.search).get('open');
      if (id) setSelectedId(id);
    } catch {
      /* sem query — segue normal */
    }
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    loadThread(selectedId);
    const t = setInterval(() => loadThread(selectedId, { quiet: true }), 4000);
    return () => clearInterval(t);
  }, [selectedId, loadThread]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, selectedId]);

  const act = async (action: string, text?: string) => {
    if (!selectedId) return;
    setNotice('');
    if (action === 'send') setSending(true);
    try {
      const res = await fetch(`/api/dashboard/conversas/${selectedId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, text }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        setNotice(j.error || 'Não foi possível concluir a ação.');
        return;
      }
      if (action === 'send') setDraft('');
      await Promise.all([loadThread(selectedId, { quiet: true }), loadList()]);
    } catch {
      setNotice('Falha de conexão. Tente de novo.');
    } finally {
      setSending(false);
    }
  };

  const q = query.trim().toLowerCase();
  const filtered = (conversations || []).filter(
    (c) => !q || displayName(c).toLowerCase().includes(q) || (c.user_phone || '').includes(q),
  );
  const activeDispatch = dispatches.find((d) => d.insurer_phone === selectedDispatch) || null;
  const own = conversation ? ownership(conversation, me) : null;
  const mine = Boolean(conversation?.claimed_by && me && conversation.claimed_by === me);
  const claimedByOther = Boolean(conversation?.claimed_by && me && conversation.claimed_by !== me);
  const closed = conversation?.status === 'closed';

  const composerPlaceholder = closed
    ? 'Conversa encerrada'
    : claimedByOther
      ? `Assumida por ${conversation?.claimed_by_name || 'colega'}`
      : mine
        ? 'Escreva sua mensagem…'
        : 'Escreva para assumir a conversa…';

  const threadOpen = Boolean(selectedId || selectedDispatch);

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden rounded-xl border border-border bg-surface">
      {/* ===== Lista (mobile: some quando uma thread está aberta) ===== */}
      <aside
        className={cn(
          'w-full shrink-0 flex-col md:flex md:max-w-[340px] md:border-r md:border-border',
          threadOpen ? 'hidden' : 'flex',
        )}
      >
        <div className="border-b border-border p-3">
          <div className="flex items-center gap-2 rounded-md border border-border bg-surface-2 px-2.5 py-1.5">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por nome ou telefone"
              className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {dispatches.length > 0 && (
            <div className="border-b border-border">
              <p className="px-3 pb-1 pt-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Seguradora · acionamentos ativos
              </p>
              {dispatches.map((d) => {
                const st = dispatchStateMeta(d.state);
                return (
                  <button
                    key={d.insurer_phone + (d.case_id || '')}
                    onClick={() => { setSelectedDispatch(d.insurer_phone); setSelectedId(null); }}
                    className={cn(
                      'flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-surface-2',
                      selectedDispatch === d.insurer_phone && !selectedId && 'bg-surface-2',
                    )}
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-brand-soft text-primary">
                      <ShieldCheck className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-foreground">
                        {insurerLabelFromRef((d as { playbook_ref?: string }).playbook_ref)} · {SUBSERVICE_LABEL[d.subservice || ''] || d.subservice}
                      </span>
                      <StatusPill tone={st.tone} label={st.label} className="mt-0.5" />
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {conversations === null ? (
            <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando conversas…
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-6 text-center">
              <MessageCircle className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium text-foreground">Nenhuma conversa ainda</p>
              <p className="mx-auto mt-1 max-w-[220px] text-xs text-muted-foreground">
                Quando um segurado chamar no WhatsApp, a conversa aparece aqui.
              </p>
            </div>
          ) : (
            filtered.map((c) => {
              const o = ownership(c, me);
              const active = selectedId === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => { setSelectedId(c.id); setSelectedDispatch(null); setNotice(''); }}
                  className={cn(
                    'flex w-full items-start gap-3 border-b border-border/60 px-3 py-2.5 text-left transition-colors hover:bg-surface-2',
                    active && 'bg-surface-2',
                  )}
                >
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 text-sm font-semibold text-muted-foreground">
                    {displayName(c).charAt(0).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-sm font-medium text-foreground">{displayName(c)}</span>
                      <span className="shrink-0 text-[11px] text-muted-foreground">{fmtTime(c.last_message_at)}</span>
                    </span>
                    <span className="mt-0.5 flex items-center justify-between gap-2">
                      <span className="truncate text-xs text-muted-foreground">{c.last_message_preview || '—'}</span>
                      {(c.unread_count || 0) > 0 && (
                        <span className="flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
                          {c.unread_count}
                        </span>
                      )}
                    </span>
                    <StatusPill tone={o.tone} label={o.label} className="mt-1" />
                  </span>
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* ===== Thread (mobile: tela cheia quando aberta) ===== */}
      <section
        className={cn(
          'min-w-0 flex-1 flex-col bg-background/40 md:flex',
          threadOpen ? 'flex' : 'hidden',
        )}
      >
        {activeDispatch && !selectedId ? (
          <DispatchThread dispatch={activeDispatch} onClose={() => setSelectedDispatch(null)} />
        ) : !selectedId ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
            <MessageCircle className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">Selecione uma conversa</p>
            <p className="max-w-xs text-xs text-muted-foreground">
              Acompanhe o atendente IA em tempo real e assuma quando quiser — é só escrever.
            </p>
          </div>
        ) : (
          <>
            {/* Header + linha de posse */}
            <div className="flex items-center justify-between gap-2 border-b border-border bg-surface px-3 py-3 sm:gap-3 sm:px-4">
              <button
                onClick={() => { setSelectedId(null); setSelectedDispatch(null); }}
                className="-ml-1 shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:text-foreground md:hidden"
                aria-label="Voltar para a lista"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">
                  {conversation ? displayName(conversation) : '…'}
                </p>
                <p className="truncate text-xs text-muted-foreground">{conversation?.user_phone || ''}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {own && <StatusPill tone={own.tone} label={own.label} />}
                {!closed && !mine && !claimedByOther && (
                  <button
                    onClick={() => act('claim')}
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
                  >
                    <UserRound className="h-3.5 w-3.5" /> Assumir
                  </button>
                )}
                {!closed && (mine || claimedByOther || conversation?.status === 'HUMAN_REQUESTED') && (
                  <button
                    onClick={() => act('release')}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface"
                    title="A IA volta a responder este cliente"
                  >
                    <Bot className="h-3.5 w-3.5" /> Devolver à IA
                  </button>
                )}
                {closed ? (
                  <button
                    onClick={() => act('release')}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface"
                  >
                    <Undo2 className="h-3.5 w-3.5" /> Reabrir (IA)
                  </button>
                ) : (
                  <button
                    onClick={() => act('close')}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" /> Encerrar
                  </button>
                )}
              </div>
            </div>

            {/* Mensagens */}
            <div className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
              {loadingThread ? (
                <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Carregando mensagens…
                </div>
              ) : (
                messages.map((m, i) => {
                  const prev = messages[i - 1];
                  const newDay = !prev || new Date(prev.created_at).toDateString() !== new Date(m.created_at).toDateString();
                  const isClient = m.role === 'user';
                  const isHuman = !isClient && Boolean(m.sender_user_id);
                  return (
                    <div key={m.id}>
                      {newDay && (
                        <div className="my-3 flex items-center gap-3">
                          <span className="h-px flex-1 bg-border" />
                          <span className="text-[11px] text-muted-foreground">{dayLabel(m.created_at)}</span>
                          <span className="h-px flex-1 bg-border" />
                        </div>
                      )}
                      <div className={cn('flex', isClient ? 'justify-start' : 'justify-end')}>
                        <div
                          className={cn(
                            'max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed shadow-sm',
                            isClient
                              ? 'rounded-bl-sm border border-border bg-surface text-foreground'
                              : isHuman
                                ? 'rounded-br-sm border border-primary/50 bg-brand-soft text-foreground'
                                : 'rounded-br-sm border border-primary/25 bg-brand-soft text-foreground',
                          )}
                        >
                          {!isClient && (
                            <p className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
                              {isHuman ? <UserRound className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                              {isHuman ? 'Atendimento humano' : 'Atendente IA'}
                            </p>
                          )}
                          {m.image_url && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={m.image_url} alt="Imagem enviada" className="mb-1 max-h-56 rounded-lg" />
                          )}
                          {m.audio_url && <audio controls src={m.audio_url} className="mb-1 max-w-full" />}
                          {m.content && <p className="whitespace-pre-wrap break-words">{m.content}</p>}
                          <p className="mt-1 text-right text-[10px] text-muted-foreground">
                            {fmtTime(m.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={bottomRef} />
            </div>

            {/* Composer */}
            <div className="border-t border-border bg-surface p-3">
              {notice && <p className="mb-2 text-xs text-danger">{notice}</p>}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (draft.trim() && !sending && !claimedByOther && !closed) act('send', draft.trim());
                }}
                className="flex items-end gap-2"
              >
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      if (draft.trim() && !sending && !claimedByOther && !closed) act('send', draft.trim());
                    }
                  }}
                  placeholder={composerPlaceholder}
                  disabled={sending || claimedByOther || closed}
                  rows={1}
                  className="max-h-32 min-h-[42px] flex-1 resize-y rounded-md border border-border bg-surface-2 px-3 py-2.5 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={!draft.trim() || sending || claimedByOther || closed}
                  className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  aria-label="Enviar mensagem"
                >
                  {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </button>
              </form>
              {!mine && !claimedByOther && !closed && (
                <p className="mt-1.5 text-[11px] text-muted-foreground">
                  Ao enviar, você assume a conversa e a IA pausa. Use &quot;Devolver à IA&quot; quando terminar.
                </p>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function DispatchThread({ dispatch, onClose }: { dispatch: DispatchSession; onClose: () => void }) {
  const st = dispatchStateMeta(dispatch.state);
  const captured = dispatch.captured || {};
  return (
    <>
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-3 py-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <button
            onClick={onClose}
            className="-ml-1 shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:text-foreground md:hidden"
            aria-label="Voltar para a lista"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <ShieldCheck className="h-5 w-5 shrink-0 text-primary" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">
              {insurerLabelFromRef((dispatch as { playbook_ref?: string }).playbook_ref)} · {SUBSERVICE_LABEL[dispatch.subservice || ''] || dispatch.subservice}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              Acionamento automático em andamento — somente leitura
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <StatusPill tone={st.tone} label={st.label} />
          <button
            onClick={onClose}
            className="rounded-md border border-border bg-surface-2 p-1.5 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Fechar espelho"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
        {(dispatch.transcript || []).map((t, i) => {
          const inbound = t.direction === 'in';
          return (
            <div key={i} className={cn('flex', inbound ? 'justify-start' : 'justify-end')}>
              <div
                className={cn(
                  'max-w-[78%] rounded-2xl px-3 py-2 text-sm leading-relaxed',
                  inbound
                    ? 'rounded-bl-sm border border-border bg-surface text-foreground'
                    : 'rounded-br-sm border border-primary/30 bg-brand-soft text-foreground',
                )}
              >
                <p className="mb-0.5 flex items-center gap-1 text-[10px] font-medium text-primary">
                  {inbound ? <Headphones className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                  {inbound ? 'Seguradora' : 'AutoBrokers (automático)'}
                </p>
                <p className="whitespace-pre-wrap break-words">{t.text}</p>
                <p className="mt-1 text-right text-[10px] text-muted-foreground">{fmtTime(t.at)}</p>
              </div>
            </div>
          );
        })}
      </div>

      {Object.keys(captured).length > 0 && (
        <div className="border-t border-border bg-surface px-4 py-3">
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Capturado</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(captured).map(([k, v]) => (
              <span key={k} className="rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-foreground">
                {k}: {typeof v === 'object' ? JSON.stringify(v) : String(v)}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
