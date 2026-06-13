'use client';

import { useEffect, useState } from 'react';

import { DetailHeader, StatusPill, type StatusTone } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

type CaseRow = {
  id: string;
  case_number: string;
  status: string;
  priority: string;
  channel: string;
  customer_name: string | null;
  customer_phone: string | null;
  intent: string | null;
  insurer_key: string | null;
  line_kind: string | null;
  macro_service: string | null;
  selected_corridor_key: string | null;
  selected_subcorridor_key: string | null;
  verification_status: string | null;
  risk_level: string | null;
  summary: string | null;
  next_step: string | null;
  created_at: string | null;
  updated_at: string | null;
  conversation_id: string | null;
  assigned_agent_id: string | null;
};

const COLUMNS: { key: string; title: string; statuses: string[] }[] = [
  { key: 'primeiro_contato', title: 'Primeiro contato', statuses: ['new', 'triage'] },
  { key: 'coletando_dados', title: 'Coletando dados', statuses: ['collecting', 'collecting_slots', 'policy_check', 'corridor_selected'] },
  { key: 'acionando', title: 'Acionando seguradora', statuses: ['ready_for_dispatch', 'awaiting_approval', 'action_prepared'] },
  { key: 'aguardando', title: 'Aguardando retorno', statuses: ['following_up'] },
  { key: 'concluido', title: 'Concluído', statuses: ['closed'] },
  { key: 'atencao', title: 'Atenção', statuses: ['handoff', 'blocked', 'cancelled'] },
];

const SUBCORRIDOR_LABEL: Record<string, string> = {
  electrician: 'Eletricista',
  plumber: 'Encanador',
  residential_locksmith: 'Chaveiro',
  unclogging: 'Desentupimento',
  home_appliances: 'Eletrodomésticos',
};

function columnForStatus(status: string): string {
  const col = COLUMNS.find((c) => c.statuses.includes(status));
  return col ? col.key : 'atencao'; // status desconhecido → Atenção
}

function priorityPill(p: string): { tone: StatusTone; label: string } {
  switch (p) {
    case 'urgent':
      return { tone: 'danger', label: 'Prioridade urgente' };
    case 'high':
      return { tone: 'warning', label: 'Prioridade alta' };
    default:
      return { tone: 'neutral', label: `Prioridade ${p || 'normal'}` };
  }
}

function verificationPill(v: string | null): { tone: StatusTone; label: string } | null {
  if (!v) return null;
  if (v.startsWith('verified')) return { tone: 'success', label: 'Apólice verificada' };
  if (v === 'pending_human') return { tone: 'info', label: 'Apólice pendente' };
  if (v === 'not_applicable') return null;
  return { tone: 'warning', label: 'Apólice não verificada' };
}

function riskTone(r: string | null): StatusTone {
  if (r === 'critical' || r === 'high') return 'danger';
  if (r === 'medium') return 'warning';
  return 'neutral';
}

function fmtDate(s: string | null): string {
  if (!s) return '';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

const TEST_PAYLOAD = {
  customer_name: 'Cliente Teste UI',
  customer_phone: '5547999999999',
  problem_description: 'Estou sem luz só na cozinha',
  channel: 'dashboard',
  priority: 'normal',
  selected_subcorridor_key: 'electrician',
  create_conversation: true,
};

export default function AttendanceQueueClient() {
  const [cases, setCases] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState('');

  const [detail, setDetail] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);

  const load = async () => {
    setError(false);
    try {
      const res = await fetch('/api/attendance/cases?limit=100');
      if (!res.ok) throw new Error('fetch failed');
      const data = await res.json();
      setCases(data.cases || []);
    } catch {
      setError(true);
      setCases(null);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openDetail = async (id: string) => {
    setDetailOpen(true);
    setDetail(null);
    setDetailLoading(true);
    try {
      const res = await fetch(`/api/attendance/cases/${id}`);
      if (!res.ok) throw new Error('detail failed');
      setDetail(await res.json());
    } catch {
      setDetail({ error: true });
    } finally {
      setDetailLoading(false);
    }
  };

  const createTestCase = async () => {
    setCreating(true);
    setNotice('');
    try {
      const res = await fetch('/api/attendance/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(TEST_PAYLOAD),
      });
      if (!res.ok) throw new Error('create failed');
      setNotice('Caso de teste (sandbox) criado.');
      await load();
    } catch {
      setNotice('Não foi possível criar o caso de teste.');
    } finally {
      setCreating(false);
    }
  };

  const q = query.trim().toLowerCase();
  const filtered = (cases || []).filter((c) => {
    if (!q) return true;
    return [c.customer_name, c.customer_phone, c.case_number, c.summary, c.selected_subcorridor_key]
      .filter(Boolean)
      .some((v) => String(v).toLowerCase().includes(q));
  });

  const buckets: Record<string, CaseRow[]> = Object.fromEntries(COLUMNS.map((c) => [c.key, []]));
  for (const c of filtered) buckets[columnForStatus(c.status)].push(c);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-[1400px] space-y-5 px-4 py-8 sm:px-6">
        <DetailHeader
          icon={icons.fila}
          title="Fila de Atendimentos"
          subtitle="Casos do atendimento ao segurado — modo sandbox / dry-run (nenhuma ação externa é executada)."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Fila' }]}
          status={{ tone: 'info', label: 'MVP ativo' }}
          actions={
            <>
              <button
                onClick={createTestCase}
                disabled={creating}
                className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-primary/50 bg-brand-soft px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-brand-soft/70 disabled:opacity-60"
              >
                <Icon icon={icons.novaConversa} size={14} /> {creating ? 'Criando…' : 'Criar caso teste'}
              </button>
              <button
                onClick={load}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-2/70"
              >
                <Icon icon={icons.renovacao} size={14} /> Atualizar
              </button>
            </>
          }
        />

        {/* Busca */}
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            <Icon icon={icons.buscar} size={16} />
          </span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por atendimento, cliente, telefone, protocolo ou canal"
            className="w-full rounded-lg border border-border bg-background py-2.5 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
          />
        </div>

        {notice && (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
            <span>{notice}</span>
            <button onClick={() => setNotice('')} className="text-muted-foreground hover:text-foreground">
              <Icon icon={icons.negado} size={14} />
            </button>
          </div>
        )}

        {/* Estados */}
        {error ? (
          <div className="rounded-xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">
            Não foi possível carregar a fila agora. Tente <button onClick={load} className="text-primary hover:underline">novamente</button>.
          </div>
        ) : cases === null ? (
          <div className="flex items-center justify-center gap-2 rounded-xl border border-border bg-card p-10 text-sm text-muted-foreground">
            <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando fila…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card p-12 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
              <Icon icon={icons.fila} size={18} />
            </span>
            <p className="text-sm font-medium text-foreground">
              {q ? 'Nenhum caso corresponde à busca.' : 'Nenhum caso na fila ainda.'}
            </p>
            {!q && (
              <p className="max-w-sm text-xs text-muted-foreground">
                Crie um caso de teste (sandbox) para ver o fluxo de Atendimento residencial Allianz / Eletricista.
              </p>
            )}
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-3">
            {COLUMNS.map((col) => (
              <div key={col.key} className="flex w-[300px] min-w-[300px] flex-col">
                <div className="mb-2 flex items-center justify-between px-1">
                  <span className="text-sm font-medium text-foreground">{col.title}</span>
                  <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                    {buckets[col.key].length}
                  </span>
                </div>
                <div className="space-y-2">
                  {buckets[col.key].length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border/70 px-3 py-6 text-center text-xs text-faint">
                      Sem itens nesta coluna.
                    </div>
                  ) : (
                    buckets[col.key].map((c) => {
                      const vp = verificationPill(c.verification_status);
                      const pri = priorityPill(c.priority);
                      const isAttention = col.key === 'atencao' || c.risk_level === 'high' || c.risk_level === 'critical';
                      const sub = c.selected_subcorridor_key
                        ? SUBCORRIDOR_LABEL[c.selected_subcorridor_key] || c.selected_subcorridor_key
                        : null;
                      return (
                        <button
                          key={c.id}
                          onClick={() => openDetail(c.id)}
                          className={`w-full rounded-lg border bg-card p-3 text-left transition-colors hover:border-primary/40 ${
                            isAttention ? 'border-danger/40' : 'border-border'
                          }`}
                        >
                          <p className="truncate text-sm font-medium text-foreground">
                            {c.customer_name || 'Segurado não informado'}
                          </p>
                          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{c.case_number}</p>
                          {c.summary && (
                            <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">{c.summary}</p>
                          )}
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                              Assistência
                            </span>
                            {c.insurer_key && (
                              <span className="rounded-full border border-border px-2 py-0.5 text-[10px] capitalize text-muted-foreground">
                                {c.insurer_key}
                              </span>
                            )}
                            {sub && (
                              <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                                {sub}
                              </span>
                            )}
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-1.5">
                            {vp && <StatusPill tone={vp.tone} label={vp.label} />}
                            <StatusPill tone={pri.tone} label={pri.label} />
                            {c.risk_level && c.risk_level !== 'low' && (
                              <StatusPill tone={riskTone(c.risk_level)} label={`Risco ${c.risk_level}`} />
                            )}
                          </div>
                          {c.updated_at && (
                            <p className="mt-2 font-mono text-[10px] text-faint">atualizado {fmtDate(c.updated_at)}</p>
                          )}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Drawer de detalhe */}
      {detailOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={() => setDetailOpen(false)}>
          <div
            className="h-full w-full max-w-md overflow-y-auto border-l border-border bg-card p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">Detalhe do caso</h2>
              <button onClick={() => setDetailOpen(false)} className="text-muted-foreground hover:text-foreground">
                <Icon icon={icons.negado} size={16} />
              </button>
            </div>

            {detailLoading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
                <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…
              </div>
            ) : !detail || detail.error ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Não foi possível carregar o detalhe.</p>
            ) : (
              <CaseDetail detail={detail} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-right text-xs font-medium text-foreground">{value ?? '—'}</span>
    </div>
  );
}

function CaseDetail({ detail }: { detail: any }) {
  const c = detail.case || {};
  const run = detail.corridor_run || null;
  const tpl = detail.corridor_template || null;
  const slots = (run?.slots || {}) as { filled?: Record<string, unknown>; missing?: string[] };
  const filledKeys = Object.keys(slots.filled || {});
  const missing = Array.isArray(slots.missing) ? slots.missing : [];
  const packets = Array.isArray(detail.dispatch_packets) ? detail.dispatch_packets : [];

  return (
    <div className="space-y-4">
      <section>
        <p className="text-sm font-medium text-foreground">{c.customer_name || 'Segurado não informado'}</p>
        <p className="font-mono text-[11px] text-muted-foreground">{c.case_number}</p>
        {c.summary && <p className="mt-2 text-xs text-muted-foreground">{c.summary}</p>}
      </section>

      <section className="rounded-lg border border-border p-3">
        <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">Caso</p>
        <Field label="Status" value={c.status} />
        <Field label="Prioridade" value={c.priority} />
        <Field label="Canal" value={c.channel} />
        <Field label="Seguradora" value={c.insurer_key} />
        <Field label="Subcorredor" value={c.selected_subcorridor_key ? SUBCORRIDOR_LABEL[c.selected_subcorridor_key] || c.selected_subcorridor_key : '—'} />
        <Field label="Apólice" value={c.verification_status} />
        <Field label="Risco" value={c.risk_level} />
        <Field label="Handoff" value={c.handoff_required ? `sim${c.handoff_reason ? ` — ${c.handoff_reason}` : ''}` : 'não'} />
        {c.next_step && <Field label="Próximo passo" value={c.next_step} />}
      </section>

      {run && (
        <section className="rounded-lg border border-border p-3">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">Corredor</p>
          <Field label="Fase" value={run.phase} />
          <Field label="Status" value={run.status} />
          <Field label="Ação externa" value={run?.diagnostics?.external_action_allowed ? 'permitida' : 'bloqueada (HITL)'} />
          {run.next_step && <Field label="Próximo passo" value={run.next_step} />}
          <div className="mt-2">
            <p className="text-[11px] text-muted-foreground">Dados coletados ({filledKeys.length})</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {filledKeys.length === 0 ? (
                <span className="text-xs text-faint">—</span>
              ) : (
                filledKeys.map((k) => (
                  <span key={k} className="rounded-full border border-success/40 px-2 py-0.5 text-[10px] text-success">
                    {k}
                  </span>
                ))
              )}
            </div>
          </div>
          <div className="mt-2">
            <p className="text-[11px] text-muted-foreground">Dados faltantes ({missing.length})</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {missing.length === 0 ? (
                <span className="text-xs text-faint">—</span>
              ) : (
                missing.map((k) => (
                  <span key={k} className="rounded-full border border-warning/40 px-2 py-0.5 text-[10px] text-warning">
                    {k}
                  </span>
                ))
              )}
            </div>
          </div>
        </section>
      )}

      {tpl && (
        <section className="rounded-lg border border-border p-3">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">Template do corredor</p>
          <Field label="Nome" value={tpl.display_name} />
          <Field label="Readiness" value={tpl.readiness} />
          <Field label="Fases" value={Array.isArray(tpl.phases) ? tpl.phases.length : '—'} />
          <Field label="Guardrails" value={Array.isArray(tpl.guardrails) ? tpl.guardrails.length : '—'} />
          <Field label="Golden tests" value={Array.isArray(tpl.golden_tests) ? tpl.golden_tests.length : '—'} />
        </section>
      )}

      <section className="rounded-lg border border-border p-3">
        <Field label="Dispatch packets" value={packets.length} />
        <p className="mt-1 text-[10px] text-faint">
          Modo sandbox/dry-run: nenhuma mensagem ou acionamento externo é enviado sem aprovação humana.
        </p>
      </section>
    </div>
  );
}
